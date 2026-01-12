import base64
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status as http_status

from .models import Report
from .serializers import ReportCreateSerializer, ReportDetailSerializer
from .openai_client import get_client

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def create_report(request):
    # Expect multipart with:
    # - diabetic_values: JSON (either real JSON body or stringified JSON from form-data)
    # - pdf_file: file
    diabetic_values = request.data.get("diabetic_values")

    # If it came as a string in multipart form-data, try to json-load it
    if isinstance(diabetic_values, str):
        import json
        try:
            diabetic_values = json.loads(diabetic_values)
        except Exception:
            return Response({"error": "diabetic_values must be valid JSON"}, status=http_status.HTTP_400_BAD_REQUEST)

    pdf = request.FILES.get("pdf_file")

    report = Report.objects.create(
        user=request.user,
        diabetic_values=diabetic_values or {},
        pdf_file=pdf,
        status="processing",
    )

    try:
        client = get_client()

        content_parts = []
        # 1) Add diabetic values context
        content_parts.append({
            "type": "input_text",
            "text": (
                "You are a clinical assistant. Summarize the patient's diabetic readings and the PDF.\n"
                "Return:\n"
                "1) a short summary\n"
                "2) key abnormalities\n"
                "3) recommendations\n"
                "Also return a JSON object with fields: summary, abnormalities[], recommendations[].\n\n"
                f"Diabetic JSON:\n{report.diabetic_values}"
            ),
        })

        # 2) Add the PDF if provided (base64 approach works even if your media URL isn't public)
        if report.pdf_file:
            pdf_bytes = report.pdf_file.read()
            b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            content_parts.append({
                "type": "input_file",
                "filename": report.pdf_file.name.split("/")[-1],
                "file_data": f"data:application/pdf;base64,{b64}",
            })

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
        report.save(update_fields=["openai_response_id","ai_summary_text","ai_raw","status","updated_at"])

    except Exception as e:
        report.status = "error"
        report.error_message = str(e)
        report.save(update_fields=["status","error_message","updated_at"])
        return Response(ReportDetailSerializer(report).data, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(ReportDetailSerializer(report).data, status=http_status.HTTP_201_CREATED)
