# Moonlight Flame — Phase 1 Backend Fix Report (Checkout & Inventory Integrity)

This document outlines the transaction-level modifications, concurrency guarantees, and test coverages implemented during Phase 1 to secure cart checkouts and stock allocations.

---

## 1. Exact Changes Made

### A. Cart Lock Implementation (`store/views.py`)
- Restructured the `/checkout/` POST view to open a transaction block (`transaction.atomic()`).
- Immediately locked the user's `Cart` record inside the transaction using `Cart.objects.select_for_update().get(user=request.user)`.
- Enforced that all `CartItem` record evaluations occur only *after* acquiring the `Cart` write lock.
- Introduced `CheckoutError` to gracefully handle transaction-ending validations and trigger clean rollbacks of all db changes inside the atomic scope.

### B. Deterministic Candle Locking (Deadlock Prevention)
- Collected unique `candle_id` keys from active cart items.
- Sorted the list of candle IDs in ascending order.
- Locked the `Candle` records in sorted PK order using `Candle.objects.select_for_update().filter(id__in=candle_ids).order_by("id")`.
- This ensures concurrent requests with overlapping cart items wait for locks in the exact same sequence, preventing cyclic deadlock loops.

### C. Server-Side Calculations
- Calculated cart subtotal, shipping costs, and Cash-on-Delivery (COD) fees dynamically using data from the locked database records.
- Completely ignored client-supplied prices, totals, or shipping parameters, enforcing server-side price authority.

### D. Stock Integrity
- Validated candle stock levels inside the transaction block after row-locking was completed.
- Rejected requests and rolled back all database writes if requested quantities exceeded active inventory or if invalid quantities (zero/negative) were submitted.

### E. Database Migration Reconciliations
- Generated migration `0007_alter_cartitem_cart_alter_order_address2_and_more.py` to reconcile pre-existing schema mismatches between the Django models and the migration logs from previous sessions (specifically related to user and cart `related_name` mappings).

---

## 2. Before/After Transaction Flow

### Flow Before
```
POST /checkout/
  ➔ Fetch Cart
  ➔ Query CartItems (Evaluated in memory)
  ➔ transaction.atomic()
      ↳ Loop CartItems (Unsorted locking order on Candles)
      ↳ Create Order
      ↳ Create OrderItems
      ↳ Clear CartItems
  ➔ Commit
```
*Vulnerability:* Two concurrent checkouts read the cart items simultaneously. Thread A commits and clears the cart, but Thread B processes its in-memory list, creating a duplicate order. Unsorted locks on overlapping items also trigger database deadlocks.

### Flow After
```
POST /checkout/
  ➔ Validate required body fields (firstName, email, etc.)
  ➔ transaction.atomic()
      ↳ Lock user Cart row using select_for_update() (Blocks concurrent checkout threads)
      ↳ Query CartItems AFTER lock is acquired
      ↳ Verify cart is not empty (If empty, raise CheckoutError & roll back)
      ↳ Sort unique Candle IDs in ascending order
      ↳ Lock Candle rows using select_for_update().order_by("id")
      ↳ Validate stock & calculate subtotal from locked candle rows
      ↳ Create Order record
      ↳ Create OrderItems, decrement Candle stock, and save Candles
      ↳ Delete CartItems
  ➔ Commit (Release Cart & Candle locks)
  ➔ Return JSON confirmation response
```

---

## 3. Concurrency Guarantees
- **Duplicate Checkout Prevention:** When a duplicate checkout request is fired (e.g. from rapid double-clicks), Thread B blocks trying to lock the user's `Cart` row. Once Thread A commits its order and deletes the cart items, Thread B acquires the cart lock, queries the cart items, finds an empty list, and immediately returns a clean error without writing a duplicate order.
- **Deadlock Immunity:** Sorting product locks ensures that concurrent checkouts for overlapping products (e.g. User 1 buying Candle A & B, User 2 buying Candle B & A) lock in the order `A` then `B`, serializing execution instead of causing cyclic locks.

---

## 4. Tests Added (`store/tests.py`)
Fourteen comprehensive transaction tests have been added to the test suite:
1. `test_successful_checkout`: Successful cart processing and totals recalculation.
2. `test_empty_cart_checkout`: Out-of-bounds rejection when checking out empty carts.
3. `test_insufficient_stock_checkout`: Rejects orders with quantities exceeding active stock.
4. `test_multi_item_checkout`: Multi-product calculations.
5. `test_zero_or_negative_quantity_checkout`: Rejects item counts under 1.
6. `test_stock_cannot_become_negative`: Stock count decreases cleanly down to zero.
7. `test_server_side_price_authority`: Tampered request totals are ignored in favor of database values.
8. `test_shipping_fee_boundaries`: Verification of standard standard shipping threshold logic.
9. `test_cod_handling_fee`: Validation of COD charge allocations.
10. `test_cart_cleared_after_success`: Cart items are deleted after order success.
11. `test_cart_preserved_after_failure`: Cart items remain intact if a checkout transaction rolls back.
12. `test_order_item_preserves_price`: Confirms price changes do not bleed into historical order lines.
13. `test_duplicate_checkouts_prevented`: Simulates consecutive checkouts on a single cart.
14. `test_multi_product_locking_order_sorting`: Asserts unique candle list IDs sort correctly.

---

## 5. Test Results
All Django checks and tests pass successfully:
```
System check identified no issues (0 silenced).
Creating test database for alias 'default'...
..............
----------------------------------------------------------------------
Ran 14 tests in 10.302s

OK
Destroying test database for alias 'default'...
Found 14 test(s).
```

---

## 6. Database Concurrency Limitations (SQLite)
- **SQLite Concurrency Limitation:** SQLite does not support native row-level locks via `select_for_update()`. Instead, it promotes locks to database-level write locks. Running concurrent checkout requests under SQLite will trigger database lock timeouts (`OperationalError: database is locked`) rather than row-level queuing.
- **Production Safety:** The locking sequence (Cart Lock ➔ Sorted Candle Locks) is fully structured to translate into clean, non-blocking row-level locks on relational database management systems like PostgreSQL or MySQL in staging and production.

---

## 7. Files Modified & Migration Status
- **Modified files:**
  - [`store/views.py`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/store/views.py) (Refactored checkout view, added CheckoutError exception)
  - [`store/tests.py`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/store/tests.py) (Created 14 transaction integration tests)
- **Migration files created:**
  - [`store/migrations/0007_alter_cartitem_cart_alter_order_address2_and_more.py`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/store/migrations/0007_alter_cartitem_cart_alter_order_address2_and_more.py)
- **Migration Status:** Applied to local DB. Migration check passes with `No changes detected`.

---

## 8. Remaining Audit Findings (Phase 2 & 3)
The following issues detailed in the master audit are intentionally **NOT** addressed in this phase (retaining original business rules):
1. *Authentication Rate Limiting:* Brute-force protections on sign-in pages (Phase 2).
2. *SECRET_KEY Fallbacks:* Hardcoded environment settings checks (Phase 2).
3. *Order Cascade Deletion:* Protections against user deletion cascades on historical orders (Phase 2).
4. *Delivery validation:* Email/Phone regex validation blocks (Phase 3).
