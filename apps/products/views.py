"""Product views — thin controllers."""
import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from apps.products.serializers import (
    ProductDetailSerializer,
    ProductListSerializer,
    ProductWriteSerializer,
)
from apps.products.services import CategoryService, ProductService
from core.pagination import StandardResultsPagination
from core.permissions.roles import IsManagerOrAbove
from core.response import created_response, no_content_response, success_response

logger = logging.getLogger(__name__)
product_service = ProductService()
category_service = CategoryService()


class ProductListView(APIView):
    """GET /products/ — list products (public)."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        status_filter = request.query_params.get("status", Product.Status.ACTIVE)
        category_id = request.query_params.get("category")
        is_featured = request.query_params.get("is_featured")

        if is_featured is not None:
            is_featured = is_featured.lower() == "true"

        qs = product_service.get_products_queryset(
            status=status_filter if request.user.is_authenticated else Product.Status.ACTIVE,
            category_id=category_id,
            is_featured=is_featured,
        )

        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class ProductDetailView(APIView):
    """GET /products/<slug>/ — product detail (public)."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        product = product_service.get_product_by_slug(slug)
        return success_response(data=ProductDetailSerializer(product).data)


class ProductCreateView(APIView):
    """POST /products/ — create product (manager+)."""

    permission_classes = [IsAuthenticated, IsManagerOrAbove]

    def post(self, request: Request) -> Response:
        serializer = ProductWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = product_service.create_product(
            validated_data=serializer.validated_data,
            created_by=request.user,
        )
        return created_response(
            data=ProductDetailSerializer(product).data,
            message="Product created successfully.",
        )


class ProductUpdateView(APIView):
    """PATCH /products/<id>/ — update product (manager+)."""

    permission_classes = [IsAuthenticated, IsManagerOrAbove]

    def patch(self, request: Request, product_id: str) -> Response:
        serializer = ProductWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        product = product_service.update_product(
            product_id=product_id,
            validated_data=serializer.validated_data,
            updated_by=request.user,
        )
        return success_response(
            data=ProductDetailSerializer(product).data,
            message="Product updated successfully.",
        )

    def delete(self, request: Request, product_id: str) -> Response:
        product_service.delete_product(product_id=product_id, deleted_by=request.user)
        return no_content_response(message="Product deleted successfully.")


class FeaturedProductsView(APIView):
    """GET /products/featured/ — featured products (cached)."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        products = product_service.get_featured_products()
        return success_response(data=ProductListSerializer(products, many=True).data)
