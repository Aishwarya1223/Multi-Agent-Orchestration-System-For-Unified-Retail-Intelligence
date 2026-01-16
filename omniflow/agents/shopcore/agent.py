from shopcore.services import (
    get_user_by_email,
    get_product_by_name,
    get_order_for_user_and_product,
)


def shopcore_agent(user_email: str, product_name: str):
    """
    Resolves user, product, and latest order context.
    """

    user = get_user_by_email(user_email)
    if not user:
        return None

    product = get_product_by_name(product_name)
    if not product:
        return None

    order = get_order_for_user_and_product(user.id, product.id)
    if not order:
        return None

    return {
        "user_id": user.id,
        "product_id": product.id,
        "order_id": order.id,
        "order_date": str(order.order_date),
        "order_status": order.status,
        "product_name": product.name,
    }