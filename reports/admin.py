from django.contrib import admin
from .models import Report, AdminPrompt


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__email", "user__username", "openai_response_id")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        ("Identification", {"fields": ("id", "user", "status")}),
        ("Data", {"fields": ("diabetic_values", "pdf_file")}),
        (
            "AI Analysis",
            {
                "fields": (
                    "ai_summary_text",
                    "ai_raw",
                    "openai_response_id",
                    "error_message",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(AdminPrompt)
class AdminPromptAdmin(admin.ModelAdmin):
    list_display = ("is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("custom_instructions",)
    readonly_fields = ("created_at", "updated_at")
