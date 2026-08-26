import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Candle, Cart, CartItem, Order, OrderItem


class CheckoutError(Exception):
    def __init__(self, message, status_code=400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


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


def homepage(request):
    candles = Candle.objects.all().order_by("id")
    featured_candles = candles[:4]
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
        for candle in featured_candles
    ]
    return render(request, "home/candle.html", {
        "products_json": json.dumps(products_data),
        "is_shop": False
    })


def products(request):
    candles = Candle.objects.all().order_by("id")
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
    return render(request, "home/candle.html", {
        "products_json": json.dumps(products_data),
        "is_shop": True
    })


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

    return JsonResponse({
        "success": True,
        "cart_items": _cart_payload(cart),
        "items": _cart_payload(cart),
        "count": sum(i.quantity for i in _cart_items(cart))
    })


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

    return JsonResponse({
        "success": True,
        "cart_items": _cart_payload(cart),
        "items": _cart_payload(cart),
        "count": sum(i.quantity for i in _cart_items(cart))
    })


@_auth_json_required
@require_POST
def clear_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    _cart_items(cart).delete()
    return JsonResponse({
        "success": True,
        "cart_items": [],
        "items": [],
        "count": 0
    })


def get_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({"success": True, "items": [], "cart_items": [], "count": 0})
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return JsonResponse({
        "success": True,
        "items": _cart_payload(cart),
        "cart_items": _cart_payload(cart),
        "count": sum(i.quantity for i in _cart_items(cart))
    })


@_auth_json_required
@require_POST
def remove_from_cart(request, product_id):
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        CartItem.objects.filter(cart=cart, candle_id=product_id).delete()
    else:
        cart, _ = Cart.objects.get_or_create(user=request.user)
    return JsonResponse({
        "success": True,
        "cart_items": _cart_payload(cart),
        "items": _cart_payload(cart),
        "count": sum(i.quantity for i in _cart_items(cart))
    })


@_auth_json_required
@require_POST
def checkout(request):
    data = _json_body(request)

    required = ["firstName", "email", "phone", "address1", "city", "pincode", "state", "paymentMethod"]
    missing = [field for field in required if not str(data.get(field, "")).strip()]
    if missing:
        return JsonResponse({"success": False, "message": "Please complete all required delivery details."}, status=400)

    payment_method = str(data.get("paymentMethod")).strip()
    if payment_method not in dict(Order.PAYMENT_CHOICES) and payment_method != "WhatsApp":
        return JsonResponse({"success": False, "message": "Invalid payment method."}, status=400)

    try:
        with transaction.atomic():
            # 1. Lock user's Cart using select_for_update() to prevent duplicate checkout submissions
            try:
                cart = Cart.objects.select_for_update().get(user=request.user)
            except Cart.DoesNotExist:
                raise CheckoutError("Your cart is empty.", status_code=400)

            # 2. Only AFTER acquiring the Cart lock, query its CartItems
            cart_items = list(CartItem.objects.filter(cart=cart).select_related("candle"))

            # 3. Empty-cart check
            if not cart_items:
                raise CheckoutError("Your cart is empty.", status_code=400)

            # 4. Collect unique Candle IDs and sort them deterministically to prevent deadlocks
            candle_ids = sorted(list(set(item.candle_id for item in cart_items)))

            # 5. Lock Candle rows in sorted order using select_for_update().order_by("id")
            candles_queryset = Candle.objects.select_for_update().filter(id__in=candle_ids).order_by("id")
            candles_map = {c.id: c for c in candles_queryset}

            # 6. Stock validation & server-side pricing
            locked_items = []
            subtotal = Decimal("0.00")
            for item in cart_items:
                candle = candles_map.get(item.candle_id)
                if not candle:
                    raise CheckoutError("One or more items in your cart no longer exist.", status_code=400)
                
                # Check for zero/negative quantity or out of stock
                if item.quantity <= 0:
                    raise CheckoutError("Invalid item quantity.", status_code=400)

                if item.quantity > candle.stock:
                    raise CheckoutError(
                        f"Only {candle.stock} of '{candle.name}' are available.",
                        status_code=400
                    )
                subtotal += candle.price * item.quantity
                locked_items.append((item, candle))

            # 7. Server-side totals calculation (ignoring client values)
            shipping = Decimal("0.00") if subtotal >= FREE_SHIPPING_THRESHOLD else STANDARD_SHIPPING
            
            if payment_method == "WhatsApp":
                # Generate WhatsApp Message & URL
                import urllib.parse
                WHATSAPP_NUMBER = "918302249136" # Business WhatsApp placeholder
                
                order_lines = []
                for item, candle in locked_items:
                    line_total = candle.price * item.quantity
                    order_lines.append(f"• {candle.name} × {item.quantity} — ₹{line_total}")
                
                items_text = "\n".join(order_lines)
                total = subtotal + shipping
                
                first_name = str(data.get("firstName")).strip()
                last_name = str(data.get("lastName", "")).strip()
                name = f"{first_name} {last_name}".strip()
                phone = str(data.get("phone")).strip()
                address1 = str(data.get("address1")).strip()
                address2 = str(data.get("address2", "")).strip()
                city = str(data.get("city")).strip()
                state = str(data.get("state")).strip()
                pincode = str(data.get("pincode")).strip()
                
                address_lines = [address1]
                if address2:
                    address_lines.append(address2)
                address_lines.extend([city, state, pincode])
                address_text = "\n".join(address_lines)
                
                message_text = (
                    f"Hello Moonlight Flame 👋\n\n"
                    f"I would like to place an order.\n\n"
                    f"Order Items:\n{items_text}\n\n"
                    f"Subtotal: \u20b9{subtotal}\n"
                    f"Shipping: \u20b9{shipping}\n"
                    f"Total: \u20b9{total}\n\n"
                    f"Customer Details:\n"
                    f"Name: {name}\n"
                    f"Phone: {phone}\n\n"
                    f"Delivery Address:\n{address_text}\n\n"
                    f"Payment Method: WhatsApp Order\n\n"
                    f"Please confirm my order.\n\n"
                    f"Thank you!\n"
                    f"Moonlight Flame"
                )
                
                encoded_msg = urllib.parse.quote(message_text)
                whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded_msg}"
                
                return JsonResponse({
                    "success": True,
                    "paymentMethod": "WhatsApp",
                    "whatsapp_url": whatsapp_url,
                    "message": "Opening WhatsApp to confirm order... 📱"
                })
            
            # If payment_method is COD:
            cod_fee = COD_FEE
            total = subtotal + shipping + cod_fee

            # 8. Order creation
            order = Order.objects.create(
                user=request.user,
                subtotal=subtotal,
                shipping_cost=shipping + cod_fee,
                total_price=total,
                payment_method="COD",
                payment_status="Pending",
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

            # 9. OrderItems + stock updates
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

            # 10. Clear cart items
            CartItem.objects.filter(cart=cart).delete()

        # Return success response outside the transaction block
        order_items_payload = []
        for o_item in order.items.select_related("candle").all():
            order_items_payload.append({
                "name": o_item.candle_name,
                "price": float(o_item.unit_price),
                "qty": o_item.quantity,
                "img": o_item.candle.image.url if (o_item.candle and o_item.candle.image) else "",
            })

        return JsonResponse({
            "success": True,
            "order_id": order.id,
            "subtotal": float(order.subtotal),
            "shipping": float(order.shipping_cost - Decimal("30.00")),
            "cod_fee": 30.0,
            "total": float(order.total_price),
            "paymentMethod": "COD",
            "customer_name": f"{order.first_name} {order.last_name}".strip(),
            "customer_phone": order.phone,
            "customer_address": f"{order.address1}, {order.address2 + ', ' if order.address2 else ''}{order.city}, {order.state} - {order.pincode}",
            "items": order_items_payload,
            "message": f"Order #{order.id} placed successfully!",
        })

    except CheckoutError as e:
        return JsonResponse({"success": False, "message": e.message}, status=e.status_code)


@login_required
def orders(request):
    user_orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )
    total_spent = user_orders.aggregate(Sum("total_price"))["total_price__sum"] or 0
    return render(request, "home/orders.html", {"orders": user_orders, "total_spent": total_spent})
