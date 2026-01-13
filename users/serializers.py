from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from glucowizard.supabase_client import get_supabase

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "password2")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("Passwords do not match")
        validate_password(attrs["password"])
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password2")

        # 1. Supabase Signup
        supabase = get_supabase()
        response = supabase.auth.sign_up({
            "email": validated_data.get("email"),
            "password": password,
            "options": {
                "data": {
                    "username": validated_data["username"]
                }
            }
        })

        if not response.user:
            raise serializers.ValidationError("Supabase signup failed")

        # 2. Local Django User creation (for reference/relation)
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=password, # Keep in sync or use random if only Supabase auth is used
        )
        return user
