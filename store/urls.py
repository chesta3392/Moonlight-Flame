from django.urls import path
from .views import (
    homepage, products, add_to_cart, update_cart, clear_cart,
    get_cart, remove_from_cart, checkout, orders,
)

urlpatterns = [
    path("", homepage, name="homepage"),
    path("products/", products, name="products"),
    path("add-to-cart/<int:product_id>/", add_to_cart, name="add_to_cart"),
    path("update-cart/<int:product_id>/", update_cart, name="update_cart"),
    path("get-cart/", get_cart, name="get_cart"),
    path("clear-cart/", clear_cart, name="clear_cart"),
    path("remove-from-cart/<int:product_id>/", remove_from_cart, name="remove_from_cart"),
    path("checkout/", checkout, name="checkout"),
    path("orders/", orders, name="orders"),
]
