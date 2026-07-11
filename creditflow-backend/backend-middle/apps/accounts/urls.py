from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import AvatarUploadView, ProfileView, RegisterView

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", TokenObtainPairView.as_view(), name="auth-login"),
    path("auth/refresh", TokenRefreshView.as_view(), name="auth-refresh"),
    path("profile", ProfileView.as_view(), name="profile"),
    path("profile/avatar", AvatarUploadView.as_view(), name="profile-avatar"),
]
