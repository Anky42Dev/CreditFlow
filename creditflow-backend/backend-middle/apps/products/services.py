from django.core.cache import cache

from .models import CreditProduct
from .serializers import CreditProductSerializer

ACTIVE_PRODUCTS_CACHE_KEY = "products:active"
PRODUCT_DETAIL_CACHE_KEY = "product:{id}"
PRODUCTS_CACHE_TTL = 600  # seconds, Doc 3 §8


def get_active_products() -> list[dict]:
    """Doc 3 §8: `products:active`, TTL 10 min. Serialized (not raw .values())
    so the API can return it directly without re-hydrating model instances."""
    data = cache.get(ACTIVE_PRODUCTS_CACHE_KEY)
    if data is None:
        qs = CreditProduct.objects.filter(is_active=True).order_by("-created_at")
        data = CreditProductSerializer(qs, many=True).data
        cache.set(ACTIVE_PRODUCTS_CACHE_KEY, data, PRODUCTS_CACHE_TTL)
    return data


def get_product_detail(product_id) -> dict | None:
    """Doc 3 §8: `product:{id}`, TTL 10 min. Returns None if the product doesn't exist."""
    key = PRODUCT_DETAIL_CACHE_KEY.format(id=product_id)
    data = cache.get(key)
    if data is None:
        try:
            product = CreditProduct.objects.get(pk=product_id)
        except (CreditProduct.DoesNotExist, ValueError, TypeError):
            return None
        data = CreditProductSerializer(product).data
        cache.set(key, data, PRODUCTS_CACHE_TTL)
    return data


def invalidate_product_cache(product_id=None) -> None:
    """Doc 3 §8: invalidated on create/update/delete of a product.

    TODO(Промпт №3 — admin CRUD продуктов): call this from the admin
    create/update/delete views once they exist (currently there is no
    admin-CRUD endpoint for CreditProduct in this codebase).
    """
    cache.delete(ACTIVE_PRODUCTS_CACHE_KEY)
    if product_id is not None:
        cache.delete(PRODUCT_DETAIL_CACHE_KEY.format(id=product_id))
