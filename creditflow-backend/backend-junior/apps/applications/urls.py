from rest_framework.routers import DefaultRouter

from .views import CreditApplicationViewSet

router = DefaultRouter(trailing_slash=False)
router.register("credit-applications", CreditApplicationViewSet, basename="credit-application")

urlpatterns = router.urls
