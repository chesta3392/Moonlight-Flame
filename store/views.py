import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Candle, Cart, CartItem, Order, OrderItem


FREE_SHIPPING_THRESHOLD = Decimal("499.00")
STANDARD_SHIPPING = Decimal("49.00")
COD_FEE = Decimal("30.00")


def _cart_items(cart):
    return CartItem.objects.filter(cart=cart).select_related("candle")


def _cart_payload(cart):
    items = []
    for item in _cart_items(cart):
        items.append({
            "id": item.candle.id,
            "name": item.candle.name,
            "price": float(item.candle.price),
            "img": item.candle.image.url if item.candle.image else "",
            "qty": item.quantity,
            "stock": item.candle.stock,
        })
    return items


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _auth_json_required(view):
    """Return JSON 401 for AJAX/API requests instead of Django's 302 login redirect."""
    from functools import wraps

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "message": "Please login to continue.", "login_url": "/accounts/login/"},
                status=401,
            )
        return view(request, *args, **kwargs)

    return wrapper


def products(request):
    candles = Candle.objects.all().order_by("-id")
    products_data = [
        {
            "id": candle.id,
            "name": candle.name,
            "sub": candle.category,
            "type": candle.category,
            "category": candle.category.lower(),
            "img": candle.image.url if candle.image else "",
            "price": float(candle.price),
            "desc": candle.description,
            "stock": candle.stock,
            "badge": "New",
            "badgeClass": "new-badge",
        }
        for candle in candles
    ]
    return render(request, "home/candle.html", {"products_json": json.dumps(products_data)})


@_auth_json_required
@require_POST
def add_to_cart(request, product_id):
    candle = get_object_or_404(Candle, id=product_id)
    if candle.stock < 1:
        return JsonResponse({"success": False, "message": "This candle is currently out of stock."}, status=400)

    data = _json_body(request)
    requested_qty = max(1, int(data.get("quantity", 1))) if str(data.get("quantity", "1")).isdigit() else 1

    cart, _ = Cart.objects.get_or_create(user=request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, candle=candle)
    new_quantity = requested_qty if created else item.quantity + requested_qty

    if new_quantity > candle.stock:
        return JsonResponse(
            {"success": False, "message": f"Only {candle.stock} item(s) are available in stock."},
            status=400,
        )

    item.quantity = new_quantity
    item.save(update_fields=["quantity"])

    return JsonResponse({"success": True, "count": sum(i.quantity for i in _cart_items(cart))})


@_auth_json_required
@require_POST
def update_cart(request, product_id):
    candle = get_object_or_404(Candle, id=product_id)
    data = _json_body(request)
    try:
        quantity = int(data.get("quantity", 1))
    except (TypeError, ValueError):
        return JsonResponse({"success": False, "message": "Invalid quantity."}, status=400)

    cart = Cart.objects.filter(user=request.user).first()
    if not cart:
        return JsonResponse({"success": False, "message": "Your cart is empty."}, status=400)

    item = CartItem.objects.filter(cart=cart, candle=candle).first()
    if not item:
        return JsonResponse({"success": False, "message": "Item is not in your cart."}, status=404)

    if quantity <= 0:
        item.delete()
    elif quantity > candle.stock:
        return JsonResponse(
            {"success": False, "message": f"Only {candle.stock} item(s) are available in stock."},
            status=400,
        )
    else:
        item.quantity = quantity
        item.save(update_fields=["quantity"])

    return JsonResponse({"success": True, "items": _cart_payload(cart)})


@_auth_json_required
@require_POST
def clear_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    _cart_items(cart).delete()
    return JsonResponse({"success": True})


def get_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": True, "items": []})
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return JsonResponse({"success": True, "items": _cart_payload(cart)})


@_auth_json_required
@require_POST
def remove_from_cart(request, product_id):
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        CartItem.objects.filter(cart=cart, candle_id=product_id).delete()
    return JsonResponse({"success": True})


@_auth_json_required
@require_POST
def checkout(request):
    data = _json_body(request)

    required = ["firstName", "email", "phone", "address1", "city", "pincode", "state", "paymentMethod"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return JsonResponse({"success": False, "message": "Please complete all required delivery details."}, status=400)

    payment_method = str(data.get("paymentMethod")).strip()
    if payment_method not in dict(Order.PAYMENT_CHOICES):
        return JsonResponse({"success": False, "message": "Invalid payment method."}, status=400)

    cart = Cart.objects.filter(user=request.user).first()
    if not cart:
        return JsonResponse({"success": False, "message": "Your cart is empty."}, status=400)

    with transaction.atomic():
        cart_items = list(_cart_items(cart))
        if not cart_items:
            return JsonResponse({"success": False, "message": "Your cart is empty."}, status=400)

        # Lock product rows during checkout to prevent overselling.
        locked_items = []
        subtotal = Decimal("0.00")
        for item in cart_items:
            candle = Candle.objects.select_for_update().get(pk=item.candle_id)
            if item.quantity > candle.stock:
                return JsonResponse(
                    {"success": False, "message": f"Only {candle.stock} of '{candle.name}' are available."},
                    status=400,
                )
            subtotal += candle.price * item.quantity
            locked_items.append((item, candle))

        shipping = Decimal("0.00") if subtotal >= FREE_SHIPPING_THRESHOLD else STANDARD_SHIPPING
        cod_fee = COD_FEE if payment_method == "COD" else Decimal("0.00")
        total = subtotal + shipping + cod_fee

        order = Order.objects.create(
            user=request.user,
            subtotal=subtotal,
            shipping_cost=shipping + cod_fee,
            total_price=total,
            payment_method=payment_method,
            payment_status="Pending" if payment_method != "COD" else "Pending",
            first_name=str(data.get("firstName")).strip(),
            last_name=str(data.get("lastName", "")).strip(),
            email=str(data.get("email")).strip(),
            phone=str(data.get("phone")).strip(),
            address1=str(data.get("address1")).strip(),
            address2=str(data.get("address2", "")).strip(),
            city=str(data.get("city")).strip(),
            state=str(data.get("state")).strip(),
            pincode=str(data.get("pincode")).strip(),
        )

        for item, candle in locked_items:
            OrderItem.objects.create(
                order=order,
                candle=candle,
                candle_name=candle.name,
                unit_price=candle.price,
                quantity=item.quantity,
            )
            candle.stock -= item.quantity
            candle.save(update_fields=["stock"])

        CartItem.objects.filter(cart=cart).delete()

    return JsonResponse({
        "success": True,
        "order_id": order.id,
        "total": float(order.total_price),
        "message": f"Order #{order.id} placed successfully!",
    })


@login_required
def orders(request):
    user_orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )
    total_spent = user_orders.aggregate(Sum("total_price"))["total_price__sum"] or 0
    return render(request, "home/orders.html", {"orders": user_orders, "total_spent": total_spent})
