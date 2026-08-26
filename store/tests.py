# -*- coding: utf-8 -*-
from decimal import Decimal
import json
import urllib.parse
from django.contrib.auth.models import User
from django.test import TransactionTestCase
from store.models import Candle, Cart, CartItem, Order, OrderItem
from store.views import FREE_SHIPPING_THRESHOLD, STANDARD_SHIPPING, COD_FEE


class CompleteEcommerceFlowTestCase(TransactionTestCase):
    """
    Comprehensive test suite containing all 35 original tests + the new bugfix & UX tests.
    Total: 49 test cases.
    """

    def setUp(self):
        # Create users
        self.user_data = {"username": "customer", "password": "password123"}
        self.user = User.objects.create_user(**self.user_data)
        
        # Create products
        self.rose = Candle.objects.create(
            name="Rose Noir",
            description="Fresh rose scent, elegant floral aroma",
            price=Decimal("150.00"),
            stock=10,
            category="Floral"
        )
        self.vanilla = Candle.objects.create(
            name="Vanilla Amber",
            description="Sweet vanilla notes with warm amber",
            price=Decimal("350.00"),
            stock=5,
            category="Vanilla"
        )
        self.oud = Candle.objects.create(
            name="Midnight Oud",
            description="Luxurious smoky oud fragrance",
            price=Decimal("500.00"),
            stock=2,
            category="Woody"
        )

        # Checkout details payload
        self.checkout_payload = {
            "firstName": "Arjun",
            "lastName": "Sharma",
            "email": "arjun@example.com",
            "phone": "9876543210",
            "address1": "123, Luxury Lane",
            "address2": "Sector 4",
            "city": "Jaipur",
            "state": "Rajasthan",
            "pincode": "302001",
            "paymentMethod": "COD"
        }

    # ==========================================
    # AUTHENTICATION TESTS (1-5)
    # ==========================================
    def test_registration_works(self):
        response = self.client.post(
            "/accounts/register/",
            data={"username": "newuser", "password": "Newuserpass123!", "password2": "Newuserpass123!"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_login_works(self):
        response = self.client.post(
            "/accounts/login/",
            data={"username": "customer", "password": "password123"}
        )
        self.assertEqual(response.status_code, 302)

    def test_logout_works(self):
        self.client.login(username="customer", password="password123")
        response = self.client.post("/accounts/logout/")
        self.assertEqual(response.status_code, 302)

    def test_invalid_login_fails(self):
        response = self.client.post(
            "/accounts/login/",
            data={"username": "customer", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)

    def test_unauthenticated_checkout_blocked(self):
        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 401)

    # ==========================================
    # CART OPERATIONS TESTS (6-17)
    # ==========================================
    # 6. Add product
    def test_add_item_to_cart(self):
        self.client.login(username="customer", password="password123")
        response = self.client.post(f"/add-to-cart/{self.rose.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    # 7. Add same product twice
    def test_add_same_product_twice(self):
        self.client.login(username="customer", password="password123")
        # Add once
        self.client.post(f"/add-to-cart/{self.rose.id}/")
        # Add twice
        response = self.client.post(f"/add-to-cart/{self.rose.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 2)

    # 8. Same product quantity becomes 2
    def test_same_product_qty_becomes_2(self):
        self.client.login(username="customer", password="password123")
        self.client.post(f"/add-to-cart/{self.rose.id}/")
        self.client.post(f"/add-to-cart/{self.rose.id}/")
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(CartItem.objects.filter(cart=cart, candle=self.rose).count(), 1)
        self.assertEqual(CartItem.objects.get(cart=cart, candle=self.rose).quantity, 2)

    # 9. Same product quantity becomes 3
    def test_same_product_qty_becomes_3(self):
        self.client.login(username="customer", password="password123")
        self.client.post(f"/add-to-cart/{self.rose.id}/")
        self.client.post(f"/add-to-cart/{self.rose.id}/")
        self.client.post(f"/add-to-cart/{self.rose.id}/")
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(CartItem.objects.get(cart=cart, candle=self.rose).quantity, 3)

    # 10. Update quantity
    def test_update_quantity_in_cart(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)
        response = self.client.post(f"/update-cart/{self.rose.id}/", data=json.dumps({"quantity": 3}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.get(cart=cart, candle=self.rose).quantity, 3)

    # 11. Remove item
    def test_remove_item_from_cart(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)
        response = self.client.post(f"/remove-from-cart/{self.rose.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)

    # 12. Clear cart
    def test_clear_cart(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)
        CartItem.objects.create(cart=cart, candle=self.vanilla, quantity=1)
        response = self.client.post("/clear-cart/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)

    # 13. Cart subtotal updates
    def test_cart_subtotal_updates(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=2) # 2 * 150 = 300
        
        # Call get-cart to see subtotal
        response = self.client.get("/get-cart/")
        items = response.json()["cart_items"]
        subtotal = sum(i["price"] * i["qty"] for i in items)
        self.assertEqual(subtotal, 300.0)

    # 14. Cart count updates
    def test_cart_count_updates(self):
        self.client.login(username="customer", password="password123")
        response = self.client.post(f"/add-to-cart/{self.rose.id}/")
        self.assertEqual(response.json()["count"], 1)
        response2 = self.client.post(f"/add-to-cart/{self.vanilla.id}/")
        self.assertEqual(response2.json()["count"], 2)

    # 15. Quantity cannot exceed stock
    def test_quantity_cannot_exceed_stock(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)
        # Try to update quantity to 11 (stock is 10)
        response = self.client.post(f"/update-cart/{self.rose.id}/", data=json.dumps({"quantity": 11}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    # 16. Cart belongs to correct user
    def test_cart_ownership_isolation(self):
        # Create other user and their cart
        other_user = User.objects.create_user(username="other", password="password123")
        other_cart = Cart.objects.create(user=other_user)
        CartItem.objects.create(cart=other_cart, candle=self.rose, quantity=2)

        # Login as main user and verify we can't see other cart items
        self.client.login(username="customer", password="password123")
        response = self.client.get("/get-cart/")
        self.assertEqual(len(response.json()["items"]), 0)

    # 17. User cannot modify another user's cart item
    def test_user_cannot_modify_another_user_cart_item(self):
        other_user = User.objects.create_user(username="otheruser", password="password123")
        other_cart = Cart.objects.create(user=other_user)
        other_item = CartItem.objects.create(cart=other_cart, candle=self.rose, quantity=1)

        self.client.login(username="customer", password="password123")
        response = self.client.post(f"/update-cart/{self.rose.id}/", data=json.dumps({"quantity": 5}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        other_item.refresh_from_db()
        self.assertEqual(other_item.quantity, 1)

    # ==========================================
    # COD CHECKOUT TESTS (18-27)
    # ==========================================
    # 18. COD order creation
    def test_successful_cod_checkout(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    # 19. Correct subtotal
    def test_correct_cod_subtotal(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=2)

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(response.json()["subtotal"], 300.0)

    # 20. Correct shipping
    def test_correct_cod_shipping(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=2)

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(response.json()["shipping"], float(STANDARD_SHIPPING))

    # 21. Correct COD fee
    def test_correct_cod_fee(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=2)

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(response.json()["cod_fee"], float(COD_FEE))

    # 22. Correct final total
    def test_correct_cod_final_total(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=2)

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(response.json()["total"], 379.0)

    # 23. Correct payment status
    def test_correct_cod_payment_status(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        order = Order.objects.get(id=response.json()["order_id"])
        self.assertEqual(order.payment_status, "Pending")

    # 24. Order status correct
    def test_correct_cod_order_status(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        order = Order.objects.get(id=response.json()["order_id"])
        self.assertEqual(order.status, "Processing")

    # 25. Stock decreases
    def test_cod_stock_decreases(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=3)

        self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.rose.refresh_from_db()
        self.assertEqual(self.rose.stock, 7)

    # 26. Cart clears
    def test_cod_cart_clears(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 0)

    # 27. Order appears in history
    def test_order_appears_in_history(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        order_id = response.json()["order_id"]

        history_response = self.client.get("/orders/")
        self.assertEqual(history_response.status_code, 200)
        self.assertContains(history_response, f"Order <span>#{order_id}</span>")

    # ==========================================
    # FAILURE CASES / PRICE INTEGRITY (28-35)
    # ==========================================
    def test_checkout_fails_empty_cart(self):
        self.client.login(username="customer", password="password123")
        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_checkout_fails_insufficient_stock(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=15)

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_checkout_fails_invalid_quantity(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        item = CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)
        item.quantity = 0
        item.save()

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_failed_checkout_preserves_cart(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=15)

        self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 1)

    def test_failed_checkout_does_not_reduce_stock(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=15)

        self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        self.rose.refresh_from_db()
        self.assertEqual(self.rose.stock, 10)

    def test_manipulated_client_price_ignored(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        tampered_payload = self.checkout_payload.copy()
        tampered_payload["price"] = "1.00"

        response = self.client.post(
            "/checkout/",
            data=json.dumps(tampered_payload),
            content_type="application/json"
        )
        order = Order.objects.get(id=response.json()["order_id"])
        self.assertEqual(order.subtotal, Decimal("150.00"))

    def test_manipulated_client_total_ignored(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        tampered_payload = self.checkout_payload.copy()
        tampered_payload["total_price"] = "5.00"

        response = self.client.post(
            "/checkout/",
            data=json.dumps(tampered_payload),
            content_type="application/json"
        )
        order = Order.objects.get(id=response.json()["order_id"])
        self.assertEqual(order.total_price, Decimal("229.00"))

    def test_database_price_authoritative(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        self.rose.price = Decimal("250.00")
        self.rose.save()

        response = self.client.post(
            "/checkout/",
            data=json.dumps(self.checkout_payload),
            content_type="application/json"
        )
        order = Order.objects.get(id=response.json()["order_id"])
        self.assertEqual(order.subtotal, Decimal("250.00"))

    # ==========================================
    # WHATSAPP ORDERS TESTS (36-43)
    # ==========================================
    # 36. Correct WhatsApp number and URL
    def test_correct_whatsapp_number_and_url(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        wa_payload = self.checkout_payload.copy()
        wa_payload["paymentMethod"] = "WhatsApp"

        response = self.client.post(
            "/checkout/",
            data=json.dumps(wa_payload),
            content_type="application/json"
        )
        url = response.json()["whatsapp_url"]
        parsed = urllib.parse.urlparse(url)
        self.assertEqual(parsed.netloc, "wa.me")
        self.assertEqual(parsed.path, "/918302249136")

    # 37. Correct order message
    def test_whatsapp_message_generation(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        wa_payload = self.checkout_payload.copy()
        wa_payload["paymentMethod"] = "WhatsApp"

        response = self.client.post(
            "/checkout/",
            data=json.dumps(wa_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("whatsapp_url", response.json())
        
        parsed_url = urllib.parse.urlparse(response.json()["whatsapp_url"])
        params = urllib.parse.parse_qs(parsed_url.query)
        self.assertIn("text", params)
        message = params["text"][0]
        self.assertIn("Hello Moonlight Flame", message)

    # 38. Message contains correct products and quantities
    def test_whatsapp_message_contains_items(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=3)

        wa_payload = self.checkout_payload.copy()
        wa_payload["paymentMethod"] = "WhatsApp"

        response = self.client.post(
            "/checkout/",
            data=json.dumps(wa_payload),
            content_type="application/json"
        )
        parsed_url = urllib.parse.urlparse(response.json()["whatsapp_url"])
        message = urllib.parse.parse_qs(parsed_url.query)["text"][0]
        self.assertIn("Rose Noir", message)
        self.assertIn("3", message)

    # 39. Message contains server-calculated totals
    def test_whatsapp_message_contains_totals(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=2)

        wa_payload = self.checkout_payload.copy()
        wa_payload["paymentMethod"] = "WhatsApp"

        response = self.client.post(
            "/checkout/",
            data=json.dumps(wa_payload),
            content_type="application/json"
        )
        parsed_url = urllib.parse.urlparse(response.json()["whatsapp_url"])
        message = urllib.parse.parse_qs(parsed_url.query)["text"][0]
        self.assertIn("Subtotal: \u20b9300.00", message)
        self.assertIn("Shipping: \u20b949.00", message)
        self.assertIn("Total: \u20b9349.00", message)

    # 40. Message contains customer delivery information
    def test_whatsapp_message_contains_delivery_info(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        wa_payload = self.checkout_payload.copy()
        wa_payload["paymentMethod"] = "WhatsApp"

        response = self.client.post(
            "/checkout/",
            data=json.dumps(wa_payload),
            content_type="application/json"
        )
        parsed_url = urllib.parse.urlparse(response.json()["whatsapp_url"])
        message = urllib.parse.parse_qs(parsed_url.query)["text"][0]
        self.assertIn("Arjun Sharma", message)
        self.assertIn("9876543210", message)
        self.assertIn("123, Luxury Lane", message)
        self.assertIn("Jaipur", message)

    # 41. No false order creation
    def test_whatsapp_does_not_create_order(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=1)

        wa_payload = self.checkout_payload.copy()
        wa_payload["paymentMethod"] = "WhatsApp"

        response = self.client.post(
            "/checkout/",
            data=json.dumps(wa_payload),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("order_id", response.json())
        self.assertEqual(Order.objects.count(), 0)

    # 42. No stock deduction
    def test_whatsapp_does_not_reduce_stock(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=2)

        wa_payload = self.checkout_payload.copy()
        wa_payload["paymentMethod"] = "WhatsApp"

        self.client.post(
            "/checkout/",
            data=json.dumps(wa_payload),
            content_type="application/json"
        )
        self.rose.refresh_from_db()
        self.assertEqual(self.rose.stock, 10)

    # 43. Cart preserved
    def test_whatsapp_does_not_clear_cart(self):
        self.client.login(username="customer", password="password123")
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, candle=self.rose, quantity=2)

        wa_payload = self.checkout_payload.copy()
        wa_payload["paymentMethod"] = "WhatsApp"

        self.client.post(
            "/checkout/",
            data=json.dumps(wa_payload),
            content_type="application/json"
        )
        self.assertEqual(CartItem.objects.filter(cart=cart).count(), 1)

    # ==========================================
    # SEARCH TESTS (44-49)
    # ==========================================
    def _search_products(self, query, category_filter='all'):
        response = self.client.get("/")
        products_json = json.loads(response.context["products_json"])
        
        list_filtered = products_json if category_filter == 'all' else [p for p in products_json if p["category"] == category_filter.lower()]
        
        if query:
            q = query.strip().lower()
            list_filtered = [
                p for p in list_filtered 
                if q in p["name"].lower() or q in p["type"].lower() or q in p["desc"].lower()
            ]
        return list_filtered

    def test_search_by_product_name(self):
        results = self._search_products("Rose Noir")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Rose Noir")

    def test_search_by_category(self):
        results = self._search_products("Floral")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Rose Noir")

    def test_search_case_insensitively(self):
        results = self._search_products("rOsE nOiR")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Rose Noir")

    def test_search_with_whitespace(self):
        results = self._search_products("  rose noir  ")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Rose Noir")

    def test_search_no_results(self):
        results = self._search_products("nonexistentcandle")
        self.assertEqual(len(results), 0)

    def test_clear_search_restores_products(self):
        results = self._search_products("")
        self.assertEqual(len(results), 3)
