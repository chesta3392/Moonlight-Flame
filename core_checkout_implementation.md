# Moonlight Flame — Core Checkout & WhatsApp/COD Implementation Report

This report summarizes the implementation details, verification results, and transactional changes made to establish Cash on Delivery (COD) and WhatsApp click-to-chat order methods on Moonlight Flame.

---

## 1. Current Customer Flow
The end-to-end shopping experience is structured as follows:
```
Register ➔ Login ➔ Browse Products ➔ Add to Cart ➔ Update Qty / Remove Items ➔ Checkout ➔ Fill Delivery Details ➔ Select COD or WhatsApp ➔ Submit
```

---

## 2. Authentication Flow
- Authenticated customers can browse, manage carts, and checkout normally.
- If an unauthenticated user attempts state-changing endpoints (such as `add-to-cart` or `checkout`), the custom `@_auth_json_required` wrapper blocks the request, returning a `401 Unauthorized` JSON response.
- Django's built-in login, registration, and logout forms are fully operational.

---

## 3. Cart Flow
- Users can add items, increase/decrease quantities, remove products, and clear their cart.
- Cart items and quantities are mapped to the active user's session, securing other users' carts from unauthorized manipulation.
- Subtotals, counts, and item costs update in real-time on the client but are validated and recalculated dynamically by the server before any order is submitted.

---

## 4. COD Flow
Selecting **Cash on Delivery** and clicking **Place Order with COD** executes the following transaction sequence:
1. Validation of required delivery fields.
2. Inside a `transaction.atomic()` block:
   - Acquire a `select_for_update()` write lock on the user's `Cart` row.
   - Fetch the cart items *after* locking.
   - Sort unique `candle_id` keys in ascending order.
   - Lock target `Candle` records in sorted order via `select_for_update().order_by("id")`.
   - Validate stock levels (raise `CheckoutError` if requested quantity > stock).
   - Recalculate subtotals, standard shipping costs, and the ₹30 COD handling fee on the server.
   - Create the `Order` record (with `payment_status="Pending"` and `status="Processing"`).
   - Create `OrderItem` snapshots, decrement Candle stocks, and save Candle objects.
   - Delete all associated `CartItem` records.
3. Commit transaction.
4. Show successful order confirmation overlay containing order numbers, subtotals, shipping costs, COD fee details, and overall total costs.

---

## 5. WhatsApp Flow
Selecting **Order on WhatsApp** and clicking **Place Order on WhatsApp** executes the following:
1. Validates delivery fields and checks that the cart is not empty.
2. Inside `transaction.atomic()`:
   - Acquires the `Cart` write lock and queries cart items.
   - Validates that stock levels are sufficient (prevents generating messages for out-of-stock items).
   - Recalculates subtotals and shipping costs on the server.
   - Does **NOT** write any `Order` record to the database, does **NOT** decrement stock, and does **NOT** clear the user's cart. This prevents false order creation or inventory reduction before manual confirmation with the business occurs.
3. Formats a structured, professional WhatsApp order text.
4. Encodes the text and constructs a standard click-to-chat URL pointing to the business contact: `https://wa.me/919999999999?text=[encoded_msg]`.
5. Returns a JSON response with `"whatsapp_url"`.
6. The frontend opens this URL in a new window/tab, allowing the customer to send their order details to the business contact.

---

## 6. Payment Methods Removed
The following have been completely deactivated and removed from both the checkout UI and backend validation checks:
- Card / Credit Card / Debit Card payment
- UPI payment options
- Net banking
- Fake payment gateway SDKs or "Pay Now" interfaces.

---

## 7. Stock Behavior
- **COD Orders:** Stock decreases immediately by the requested amount when the checkout transaction commits.
- **WhatsApp Orders:** No stock deduction is made, as the order is uncommitted and pending manual validation.
- **Failed Checkouts:** Any stock validation or connection failures roll back the entire transaction, leaving stock counts unchanged.

---

## 8. Order Creation Behavior
- **COD Orders:** Creates a physical record in the database with standard line item snapshots (`OrderItem`).
- **WhatsApp Orders:** Creates no database records.
- **Payment Status:** COD orders are saved as `Pending` payment status, as the customer will pay on delivery.

---

## 9. Order History Behavior
- Successfully placed COD orders appear immediately under **My Orders** with all fields correctly populated (Order #, Date, Items, Qty, Price, Subtotal, Shipping Cost, COD Fee, Total, and Order/Payment status).

---

## 10. Tests Added (`store/tests.py`)
Thirty-five comprehensive test assertions have been added covering:
- **Authentication (1-5):** Register, login, logout, invalid login, and blocked unauthenticated checkouts.
- **Cart (6-10):** Add item, update quantity, remove item, clear cart, and cart ownership isolation.
- **COD (11-20):** Successful COD, subtotal, shipping boundaries, COD fee check, final total, pending status, stock reductions, cart clearance, and history updates.
- **Failures (21-25):** Empty carts, insufficient stock, invalid quantities, cart preservation, and stock rollback checks.
- **Price Integrity (26-28):** Ignoring tampered client prices, ignoring tampered client totals, and database price authority.
- **WhatsApp (29-35):** Correct message generation, item inclusions, totals inclusions, address details, zero order writes, stock preservation, and cart preservation checks.

---

## 11. Test Results
All 35 tests pass successfully:
```
System check identified no issues (0 silenced).
Creating test database for alias 'default'...
...................................
----------------------------------------------------------------------
Ran 35 tests in 24.902s

OK
Destroying test database for alias 'default'...
Found 35 test(s).
```

---

## 12. Files Modified
- **Views:** [`store/views.py`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/store/views.py) (Added WhatsApp message generator, refactored checkout view checks)
- **Tests:** [`store/tests.py`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/store/tests.py) (Implemented 35 flow tests)
- **HTML:** [`Templates/home/candle.html`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/Templates/home/candle.html) (Updated payment buttons UI, placeOrder scripts, and success page detail breakdowns)

---

## 13. Migration Required?
- **No**. WhatsApp ordering and COD flow are supported using the existing `Order` model choices and custom checks. No migrations were generated or applied in this phase.

---

## 14. Known Limitations
- **SQLite Concurrency:** SQLite promotes row-level locking to database-level file locks. While transaction safety is fully operational on staging/production (e.g. PostgreSQL), concurrent multi-user write loads in SQLite will raise database-locked errors.
- **WhatsApp Contact:** The business phone number is currently set to a configuration placeholder (`919999999999`). This should be replaced with the client's real business contact phone number prior to production deployment.

---

## 15. Future Online Payment Integration
- Gateway structures (Razorpay/Stripe) can be added as Option 3 under the `pay-btn-row` in the future, reusing the existing `transaction.atomic()` stock locks.
