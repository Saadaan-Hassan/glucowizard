from rest_framework import authentication
from rest_framework import exceptions
from django.contrib.auth import get_user_model
from glucowizard.supabase_client import get_supabase

User = get_user_model()

class SupabaseAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None

        try:
            # Format: "Bearer <token>"
            token = auth_header.split(' ')[1]
        except IndexError:
            raise exceptions.AuthenticationFailed('Bearer token malformed')

        supabase = get_supabase()
        try:
            # Verify the token with Supabase
            response = supabase.auth.get_user(token)
            if not response.user:
                raise exceptions.AuthenticationFailed('Invalid Supabase token')

            # Get or create the local Django user synced with this email
            email = response.user.email
            user, _ = User.objects.get_or_create(
                email=email, 
                defaults={'username': email.split('@')[0]}
            )
            
            return (user, token)
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Supabase authentication failed: {str(e)}')
