from rest_framework.routers import DefaultRouter

from .views import LoanViewSet

router = DefaultRouter(trailing_slash=False)
router.register("loans", LoanViewSet, basename="loan")

urlpatterns = router.urls
