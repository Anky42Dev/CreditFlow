from rest_framework.routers import DefaultRouter

from .views import CreditProductViewSet

router = DefaultRouter(trailing_slash=False)
router.register("credit-products", CreditProductViewSet, basename="credit-product")

urlpatterns = router.urls
