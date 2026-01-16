from .models import User, Product, Order


def get_user_by_email(email: str):
    return User.objects.filter(email=email).first()


def get_product_by_name(product_name: str):
    return Product.objects.filter(name__icontains=product_name).first()


def get_order_for_user_and_product(user_id: int, product_id: int):
    return (
        Order.objects
        .filter(user_id=user_id, product_id=product_id)
        .order_by("-order_date")
        .first()
    )
