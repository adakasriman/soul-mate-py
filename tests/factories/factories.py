"""
Test factories using factory_boy.

Usage:
    user = UserFactory()
    admin = UserFactory(role=UserRole.ADMIN)
    product = ProductFactory(status=Product.Status.ACTIVE)
    order = OrderFactory(customer=user)
"""
import factory
from factory.django import DjangoModelFactory
from django.utils.text import slugify

from apps.users.constants import UserRole, UserStatus
from apps.users.models import User
from apps.products.models import Category, Product
from apps.orders.models import Order


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = UserRole.CUSTOMER
    status = UserStatus.ACTIVE
    is_email_verified = True
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "TestPass123!")
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, password=password, **kwargs)


class AdminFactory(UserFactory):
    role = UserRole.ADMIN
    is_staff = True


class SuperAdminFactory(UserFactory):
    role = UserRole.SUPER_ADMIN
    is_staff = True
    is_superuser = True


class ManagerFactory(UserFactory):
    role = UserRole.MANAGER
    is_staff = True


class CategoryFactory(DjangoModelFactory):
    class Meta:
        model = Category

    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    description = factory.Faker("sentence")
    is_active = True


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    sku = factory.Sequence(lambda n: f"SKU{n:06d}")
    category = factory.SubFactory(CategoryFactory)
    price = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    status = Product.Status.ACTIVE
    description = factory.Faker("paragraph")


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    customer = factory.SubFactory(UserFactory)
    status = Order.Status.PENDING
    payment_status = Order.PaymentStatus.PENDING
    subtotal = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    tax_amount = factory.LazyAttribute(lambda o: o.subtotal * 18 / 100)
    shipping_amount = 50
    discount_amount = 0
    total_amount = factory.LazyAttribute(lambda o: o.subtotal + o.tax_amount + o.shipping_amount)
    shipping_address = factory.LazyFunction(lambda: {
        "full_name": "Test User",
        "address_line1": "123 Test Street",
        "city": "Hyderabad",
        "state": "Telangana",
        "postal_code": "500001",
        "country": "IN",
        "phone": "+91 9999999999",
    })
