"""Products app URLs."""
from django.urls import path

from apps.products.views import (
    FeaturedProductsView,
    ProductCreateView,
    ProductDetailView,
    ProductListView,
    ProductUpdateView,
)

app_name = "products"

urlpatterns = [
    path("", ProductListView.as_view(), name="product-list"),
    path("create/", ProductCreateView.as_view(), name="product-create"),
    path("featured/", FeaturedProductsView.as_view(), name="product-featured"),
    path("<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
    path("<uuid:product_id>/update/", ProductUpdateView.as_view(), name="product-update"),
]
