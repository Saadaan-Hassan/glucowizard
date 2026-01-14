import base64
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status as http_status

from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from glucowizard.supabase_client import get_supabase
from .models import Report
from .serializers import (
    ReportCreateSerializer,
    ReportDetailSerializer,
    ReportListSerializer,
)
from .openai_client import get_client
from .pagination import StandardResultsSetPagination


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_stats(request):
    """
    Returns aggregated stats for bolus ratio, basal rates, and correction factors.
    Query param: period=week|month (defaults to week).
    """
    period = request.query_params.get("period", "week")
    days = 7 if period == "week" else 30

    start_date = timezone.now() - timedelta(days=days)

    # Fetch reports in chronological order
    reports = Report.objects.filter(
        user=request.user, created_at__gte=start_date
    ).order_by("created_at")

    stats_data = []

    for r in reports:
        # Extract the specific diabetic metrics from the JSON field
        dv = r.diabetic_values or {}
        stats_data.append(
            {
                "id": r.id,
                "created_at": r.created_at,
                "bolus_ratio": dv.get("bolus_ratio", []),
                "basal_rates": dv.get("basal_rates", []),
                "correction_factors": dv.get("correction_factors", []),
            }
        )

    return Response({"period": period, "count": len(stats_data), "data": stats_data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_reports(request):
    """List all reports for the authenticated user and generate signed URLs with pagination."""
    reports = Report.objects.filter(user=request.user).order_by("-created_at")

    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(reports, request)

    supabase = get_supabase()
    supabase.auth.set_session(request.auth, "")

    if page is not None:
        serializer = ReportListSerializer(page, many=True)
        data = serializer.data
        # Generate signed URLs for each report in the list
        for report_data in data:
            if report_data.get("pdf_file"):
                signed_url_resp = supabase.storage.from_("reports").create_signed_url(
                    report_data["pdf_file"], 3600
                )
                report_data["pdf_url"] = signed_url_resp.get(
                    "signedURL"
                ) or signed_url_resp.get("signed_url")
        return paginator.get_paginated_response(data)

    serializer = ReportListSerializer(reports, many=True)
    data = serializer.data
    for report_data in data:
        if report_data.get("pdf_file"):
            signed_url_resp = supabase.storage.from_("reports").create_signed_url(
                report_data["pdf_file"], 3600
            )
            report_data["pdf_url"] = signed_url_resp.get(
                "signedURL"
            ) or signed_url_resp.get("signed_url")

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_report_detail(request, pk):
    """Get full details for a specific report, including a fresh signed URL."""
    report = get_object_or_404(Report, pk=pk, user=request.user)
    supabase = get_supabase()
    supabase.auth.set_session(request.auth, "")

    serializer = ReportDetailSerializer(report)
    data = serializer.data

    # Generate a signed URL for the detail view (1-hour expiry)
    if report.pdf_file:
        signed_url_resp = supabase.storage.from_("reports").create_signed_url(
            report.pdf_file, 3600
        )
        data["pdf_url"] = signed_url_resp.get("signedURL") or signed_url_resp.get(
            "signed_url"
        )

    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def create_report(request):
    # ... logic stays same ...
    # but we store the PATH in the DB, not the public URL
    diabetic_values = request.data.get("diabetic_values")
    if isinstance(diabetic_values, str):
        import json

        try:
            diabetic_values = json.loads(diabetic_values)
        except Exception:
            return Response(
                {"error": "diabetic_values must be valid JSON"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

    pdf = request.FILES.get("pdf_file")
    pdf_path = ""

    if pdf:
        supabase = get_supabase()
        supabase.auth.set_session(request.auth, "")

        pdf_path = f"{request.user.id}_{pdf.name}"
        supabase.storage.from_("reports").upload(
            pdf_path, pdf.read(), {"content-type": pdf.content_type, "upsert": "true"}
        )

    report = Report.objects.create(
        user=request.user,
        diabetic_values=diabetic_values or {},
        pdf_file=pdf_path,  # STORE PATH ONLY
        status="processing",
    )

    try:
        client = get_client()

        content_parts = []
        # 1) Add diabetic values context
        content_parts.append(
            {
                "type": "input_text",
                "text": (
                    "Analyze the following diabetes management data.\n\n"
                    "### Inputs Provided\n"
                    "- CGM report (time-series and summary statistics)\n"
                    "- Current insulin dosing parameters\n\n"
                    "### Tasks\n"
                    "1. Analyze CGM trends and glucose control patterns\n"
                    "2. Identify hyperglycemia, hypoglycemia, and variability issues\n"
                    "3. Provide clinically reasonable suggested adjustments for:\n"
                    "   - Bolus insulin ratio (insulin-to-carb)\n"
                    "   - Basal (balas) insulin rate\n"
                    "   - Correction factor (insulin sensitivity)\n\n"
                    "### Rules\n"
                    "- Suggestions must be conservative and expressed as ranges or directional changes\n"
                    "- Do NOT present recommendations as final prescriptions\n"
                    "- Clearly note when trends are uncertain or data is insufficient\n\n"
                    "Also return a JSON object with fields: summary, analysis[], recommendations[] and suggested_insulin_parameters of ballas ratio , bolousratio and correction_factor[].\n\n"
                    "### Current Insulin Parameters (JSON)\n"
                    f"{report.diabetic_values}"
                ),
            }
        )

        # 2) Add the PDF if provided
        if pdf:
            # For OpenAI, you might need to download it or pass the URL if supported
            # Here we follow the existing base64 approach but fetch the bytes from Supabase or use local 'pdf' if just uploaded
            # Since we just uploaded 'pdf', we can reuse its bytes
            pdf.seek(0)
            pdf_bytes = pdf.read()
            b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            content_parts.append(
                {
                    "type": "input_file",
                    "filename": pdf.name,
                    "file_data": f"data:application/pdf;base64,{b64}",
                }
            )

        # Use a vision-capable model that supports PDF inputs
        # (Docs: vision-capable models like gpt-4o / gpt-4o-mini / o1) :contentReference[oaicite:4]{index=4}
        resp = client.responses.create(
            model="gpt-5.2",
            input=[{"role": "user", "content": content_parts}],
        )

        report.openai_response_id = getattr(resp, "id", "") or ""
        report.ai_summary_text = resp.output_text or ""
        # store raw response if you want (careful: it can be big)
        report.ai_raw = resp.model_dump() if hasattr(resp, "model_dump") else {}
        report.status = "done"
        report.save(
            update_fields=[
                "openai_response_id",
                "ai_summary_text",
                "ai_raw",
                "status",
                "updated_at",
            ]
        )

    except Exception as e:
        report.status = "error"
        report.error_message = str(e)
        report.save(update_fields=["status", "error_message", "updated_at"])
        return Response(
            ReportDetailSerializer(report).data,
            status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        ReportDetailSerializer(report).data, status=http_status.HTTP_201_CREATED
    )
