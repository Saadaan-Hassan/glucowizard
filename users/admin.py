from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "is_staff", "is_superuser")
    fieldsets = UserAdmin.fieldsets + (
        ("Profile Information", {"fields": ("avatar_url",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Profile Information", {"fields": ("avatar_url",)}),
    )
