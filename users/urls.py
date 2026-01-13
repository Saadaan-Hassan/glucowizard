from django.urls import path
from .views import (
    register, login, refresh_token, 
    forgot_password, update_password, change_password,
    upload_avatar, google_auth, google_callback, me
)

urlpatterns = [
    path("me/", me),
    path("google-callback/", google_callback),
    path("register/", register),
    path("login/", login),
    path("refresh-token/", refresh_token),
    path("forgot-password/", forgot_password),
    path("update-password/", update_password),
    path("change-password/", change_password),
    path("upload-avatar/", upload_avatar),
    path("google-auth/", google_auth),
]
