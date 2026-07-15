from rest_framework.routers import DefaultRouter

from .views import AdminApplicationViewSet, AdminCreditProductViewSet, AdminUserViewSet

router = DefaultRouter(trailing_slash=False)
router.register("admin/credit-products", AdminCreditProductViewSet, basename="admin-credit-product")
router.register("admin/applications", AdminApplicationViewSet, basename="admin-application")
router.register("admin/users", AdminUserViewSet, basename="admin-user")

urlpatterns = router.urls
