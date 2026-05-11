"""
Products service — business logic + Redis caching strategy.

Cache keys:
  ecom:product:<slug>        -> product detail (TTL 300s)
  ecom:products:featured     -> featured products (TTL 600s)
  ecom:categories:tree       -> category tree (TTL 3600s)
"""
from __future__ import annotations

import logging
from uuid import UUID

from django.core.cache import cache
from django.db import transaction
from django.utils.text import slugify

from apps.products.models import Category, Product
from core.exceptions.exceptions import ConflictException, NotFoundException

logger = logging.getLogger(__name__)

# Cache TTLs
PRODUCT_DETAIL_TTL = 300   # 5 min
FEATURED_PRODUCTS_TTL = 600  # 10 min
CATEGORY_TREE_TTL = 3600   # 1 hour


class ProductService:
    """Business logic and caching for products."""

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_product_by_slug(self, slug: str) -> Product:
        cache_key = f"product:{slug}"
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Cache hit: product:%s", slug)
            return cached

        product = (
            Product.objects
            .select_related("category")
            .prefetch_related("images", "variants", "inventory")
            .filter(slug=slug, status=Product.Status.ACTIVE)
            .first()
        )
        if not product:
            raise NotFoundException(f"Product '{slug}' not found.")

        cache.set(cache_key, product, PRODUCT_DETAIL_TTL)
        return product

    def get_product_by_id(self, product_id: UUID | str) -> Product:
        try:
            return (
                Product.objects
                .select_related("category")
                .prefetch_related("images", "variants")
                .get(id=product_id)
            )
        except Product.DoesNotExist:
            raise NotFoundException(f"Product {product_id} not found.")

    def get_products_queryset(
        self,
        status: str | None = None,
        category_id: str | None = None,
        is_featured: bool | None = None,
    ):
        """
        Optimized product list queryset.
        Uses select_related + prefetch to avoid N+1.
        """
        qs = (
            Product.objects
            .select_related("category")
            .prefetch_related("images")
            .order_by("-created_at")
        )
        if status:
            qs = qs.filter(status=status)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if is_featured is not None:
            qs = qs.filter(is_featured=is_featured)
        return qs

    def get_featured_products(self) -> list[Product]:
        cache_key = "products:featured"
        cached = cache.get(cache_key)
        if cached:
            return cached

        products = list(
            Product.objects
            .select_related("category")
            .prefetch_related("images")
            .filter(status=Product.Status.ACTIVE, is_featured=True)
            .order_by("-updated_at")[:12]
        )
        cache.set(cache_key, products, FEATURED_PRODUCTS_TTL)
        return products

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    @transaction.atomic
    def create_product(self, validated_data: dict, created_by=None) -> Product:
        if not validated_data.get("slug"):
            validated_data["slug"] = self._unique_slug(validated_data["name"])

        product = Product(**validated_data)
        if created_by:
            product.created_by = created_by
        product.save()

        logger.info("Product created: %s by %s", product.sku, created_by)
        return product

    @transaction.atomic
    def update_product(self, product_id: UUID | str, validated_data: dict, updated_by=None) -> Product:
        product = self.get_product_by_id(product_id)

        for field, value in validated_data.items():
            setattr(product, field, value)
        if updated_by:
            product.updated_by = updated_by
        product.save()

        # Invalidate cache
        self._invalidate_product_cache(product)
        logger.info("Product updated: %s", product.sku)
        return product

    @transaction.atomic
    def delete_product(self, product_id: UUID | str, deleted_by=None) -> None:
        product = self.get_product_by_id(product_id)
        self._invalidate_product_cache(product)
        product.delete(deleted_by=deleted_by)
        logger.info("Product soft-deleted: %s", product.sku)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _unique_slug(name: str) -> str:
        base_slug = slugify(name)
        slug = base_slug
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    @staticmethod
    def _invalidate_product_cache(product: Product) -> None:
        cache.delete(f"product:{product.slug}")
        cache.delete("products:featured")
        logger.debug("Cache invalidated for product: %s", product.slug)


class CategoryService:
    """Business logic for categories."""

    def get_category_tree(self) -> list[Category]:
        cache_key = "categories:tree"
        cached = cache.get(cache_key)
        if cached:
            return cached

        categories = list(
            Category.objects
            .select_related("parent")
            .prefetch_related("children")
            .filter(is_active=True, parent__isnull=True)
            .order_by("sort_order", "name")
        )
        cache.set(cache_key, categories, CATEGORY_TREE_TTL)
        return categories

    @staticmethod
    def invalidate_cache() -> None:
        cache.delete("categories:tree")
