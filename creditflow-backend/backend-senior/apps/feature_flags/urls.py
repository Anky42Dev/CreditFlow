from django.urls import path

from .views import FeatureFlagDetailView, FeatureFlagListView

urlpatterns = [
    path(
        "admin/feature-flags",
        FeatureFlagListView.as_view(),
        name="admin-feature-flag-list",
    ),
    path(
        "admin/feature-flags/<str:name>",
        FeatureFlagDetailView.as_view(),
        name="admin-feature-flag-detail",
    ),
]
