# Moonlight Flame — Core Store Bug Fix & UX Pass Report

This report outlines the findings, root causes, implementation details, and verification results for the Moonlight Flame bug-fix and visual/UX pass.

---

## 1. WhatsApp Number Update
- **Old Placeholder:** `919999999999`
- **New Real Number:** `918302249136` (international Click-to-Chat format: `https://wa.me/918302249136`).
- **Files updated:** Verified that the placeholder number is completely removed from active code and replaced in [`store/views.py`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/store/views.py).

---

## 2. Cart Root Cause & Fix
### The Network Error
- **Root Cause 1 (URL Mismatch):** The frontend JavaScript was sending fetch requests to `/update-cart-qty/<int:id>/`. However, Django's [`urls.py`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/store/urls.py) defined only the `/update-cart/<int:id>/` pattern. This resulted in an HTTP 404 (Not Found) response, triggering a "Network Error" toast.
- **Root Cause 2 (JSON Schema Mismatch):** Cart update/delete endpoints were returning different JSON schemas (e.g. returning nothing or returning only `items`), whereas the JavaScript code expected `data.cart_items` in almost all responses. Setting `cart = data.cart_items` resulted in `cart = undefined`, crashing the frontend UI loops.

### The Fixes
- Standardized all cart view responses (`add_to_cart`, `update_cart`, `remove_from_cart`, `clear_cart`, `get_cart`) to return a unified schema:
  ```json
  {
    "success": true,
    "cart_items": [...],
    "items": [...],
    "count": 5
  }
  ```
- Corrected the frontend JavaScript to invoke `/update-cart/${id}/` for quantity updates.
- Verified that adding the same product multiple times updates the existing `CartItem` quantity instead of generating duplicate rows.

---

## 3. Cart Stock Limit & Ownership Isolation
- The backend validates all quantity updates against the database `Candle.stock` column. If a quantity exceeding the stock is requested, it aborts the database transaction and returns an HTTP 400 with a clean `"Only X item(s) are available in stock."` message.
- Cart ownership isolation is preserved: all operations filter by the current logged-in user (`Cart.objects.filter(user=request.user)`), ensuring User A can never manipulate User B's cart items.

---

## 4. Wishlist Heart UI
- Styled the wishlist heart overlay to render as a clean, filled icon when active:
  ```css
  .product-wishlist-overlay.wishlisted svg {
    fill: var(--color-red);
    stroke: var(--color-red);
  }
  ```
- Added micro-animations for hover states and transitions.
- Replaced the simple `✕` text button inside the wishlist grid with the elegant heart icon.
- Kept wishlist data stored fully client-side (no new database models).

---

## 5. Announcement Bar Marquee
- Changed the announcement text color to luxury gold (`#C5A880`).
- Implemented a continuous, smooth CSS marquee using duplicate flex containers inside an overflow-hidden track.
- Seamless loop with zero jumps or vertical expansions.
- Respects accessibility settings:
  ```css
  @media (prefers-reduced-motion: reduce) {
    .announcement-track {
      animation-duration: 120s; /* Substantially slower */
    }
  }
  ```

---

## 6. Coupon Code Section
- Added a "Have a Coupon Code?" input card directly above the subtotal inside the cart drawer.
- Entering a code and clicking **Apply** triggers a clean, client-side message: `"Coupons are currently unavailable."`
- The subtotal, shipping cost, and totals are not modified.

---

## 7. Product Search & Filter Alignment
- **Root Cause:** The search query reset itself whenever the input lost focus because it checked `document.activeElement === searchInput`. Clicking category tabs or the search button cleared the search.
- **The Fix:** Removed the focus check. The search input is now evaluated whenever text is present. Category tab filters and search queries are applied jointly, supporting name, category, and description matches (case-insensitive and whitespace-tolerant).

---

## 8. COD & WhatsApp Flow Verification
- **Cash on Delivery:**
  - Validates client details, locks the user's Cart and Candle tables deterministically inside a transaction, decrements stock, records the order details, clears the cart, and redirects the user to the orders page.
  - Payment is saved as `Pending` and order status as `Processing`.
- **WhatsApp Order:**
  - Generates the pre-filled message template containing totals and customer details.
  - Redirects to `https://wa.me/918302249136`.
  - Does **not** modify database records, does **not** deduct stock, and does **not** clear the user's cart.

---

## 9. Admin Developer Credentials
- Verified/created local Django superuser:
  - **Username:** `admin`
  - **Password:** `admin`
- > [!WARNING]
  > These credentials are for local development/testing only and must be changed prior to production deployment.

---

## 10. Verification & Test Results
Expanded the Django test suite to **49 tests** covering all e-commerce flows, cart operations, search filtering, WhatsApp number URLs, and COD checkout states.

```
System check identified no issues (0 silenced).
Creating test database for alias 'default'...
.................................................
----------------------------------------------------------------------
Ran 49 tests in 28.083s

OK
Destroying test database for alias 'default'...
Found 49 test(s).
```

---

## 11. Files Modified
- [`store/views.py`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/store/views.py) (Refactored cart JSON responses and WhatsApp phone number)
- [`store/tests.py`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/store/tests.py) (Extended test coverage to 49 tests)
- [`Templates/home/candle.html`](file:///c:/Users/anmol/OneDrive/Desktop/Python-new-batch/moonflame/Moonlight-Flame/Templates/home/candle.html) (Search, Wishlist heart CSS, Announcement Marquee HTML/CSS, Coupon UI)
