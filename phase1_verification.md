# Moonlight Flame — Phase 1 Verification Report

This report provides a read-only verification of the Phase 1 backend implementation, focusing on checkout safety, the unexpected creation of migration `0007`, the git diff cleanliness, and the test suite's coverage under SQLite limitations.

---

## 1. Migration 0007 Analysis

### What Schema Changes Migration 0007 Makes
1. **Alter field `cart` on `cartitem`**: Adds `related_name="items"` to the `ForeignKey` linking `CartItem` to `Cart`.
2. **Alter field `user` on `order`**: Adds `related_name="orders"` to the `ForeignKey` linking `Order` to `User`.
3. **Alter field `address2` on `order`**: Modifies the `CharField` to remove `default=""` from the migration representation, keeping it as a standard `blank=True` field.
4. **Alter field `last_name` on `order`**: Modifies the `CharField` to remove `default=""` from the migration representation, keeping it as a standard `blank=True` field.

### Why Django Generated Them
These schema changes were generated because in previous visual redesign sessions, the models file (`store/models.py`) was edited to add `related_name` values (to allow syntax like `cart.items` and `user.orders` inside templates and views) and change standard defaults, but no corresponding migrations were generated to document them. Running `makemigrations` in Phase 1 was necessary to reconcile these discrepancies and allow Django's integrity checks (`makemigrations --check`) to pass.

### Assessment
- **Required by current models?** Yes. The visual layout templates and view scripts refer to `cart.items.all()` and `user.orders`, which depend on these related_names.
- **Related to Phase 1 checkout locking?** No. They are ORM configuration details from the visual redesign.
- **Applying this migration safety**: Safe. In SQLite, PostgreSQL, and MySQL, adding a Python ORM `related_name` is metadata-only and changes no physical database columns. Removing default options for CharFields changes metadata defaults but has zero physical impact on existing order data.
- **Verdict**: The migration is safe and necessary to keep.

---

## 2. Migration Consistency Check
The read-only verification commands yield the following results:
- **`showmigrations`**: Clean. All migrations (up to `0007`) are fully applied and active in the database graph.
- **`makemigrations --check`**: Clean. Output reports `No changes detected`, confirming the database models are in complete sync with the migration history.
- **`check`**: Clean. Django reports `System check identified no issues (0 silenced)`.

The migration graph is 100% consistent.

---

## 3. Phase 1 Diff Review
- **`store/views.py`**: Extremely clean. The only changes are the introduction of `CheckoutError` and the refactored `checkout` view code.
- **`store/tests.py`**: Clean. Only contains the 14 new transaction validation tests.
- **`store/migrations/0007_*.py`**: Clean. Only contains the AlterField operations reconciling the model discrepancies.
- **Verdict**: No unrelated changes were introduced during Phase 1.

---

## 4. Checkout Transaction Verification
Reading the refactored checkout implementation in `store/views.py` verifies the following execution order:

1. **Cart Lock** (`Cart.objects.select_for_update().get(user=request.user)`) - *Starts transaction locking*
2. **CartItems read** (`CartItem.objects.filter(cart=cart).select_related("candle")`) - *Read after lock*
3. **Empty-cart check** (`if not cart_items: raise CheckoutError(...)`) - *Validation check*
4. **Candle IDs sorted** (`candle_ids = sorted(list(set(item.candle_id for item in cart_items)))`) - *Locks preparation*
5. **Candle rows locked** (`Candle.objects.select_for_update().filter(id__in=candle_ids).order_by("id")`) - *Deterministic lock order*
6. **Stock validation** (`if item.quantity > candle.stock: raise CheckoutError(...)`) - *Verifies stock*
7. **Server-side totals** (`total = subtotal + shipping + cod_fee`) - *Recalculates totals ignoring client input*
8. **Order creation** (`Order.objects.create(...)`) - *Writes order record*
9. **OrderItems creation** (`OrderItem.objects.create(...)`) - *Writes line item records*
10. **Stock decrement** (`candle.stock -= item.quantity; candle.save(...)`) - *Updates product stock*
11. **Cart clearing** (`CartItem.objects.filter(cart=cart).delete()`) - *Deletes items*
12. **Commit** (`transaction.atomic()` block exits successfully) - *Saves changes and releases locks*

The actual view code follows this sequence exactly.

---

## 5. Test Quality & SQLite Limitations

### SQLite vs. Production Databases (PostgreSQL/MySQL)

| Test Category / Claim | What is actually tested on SQLite | What requires PostgreSQL/MySQL to fully validate |
| :--- | :--- | :--- |
| **Locking Order (`test_multi_product_locking_order_sorting`)** | Verifies Python list/set sorting logic behaves deterministically before locks are query-constructed. | Verifies the database engine actually serializes overlapping row locks on indices rather than raising table lock conflicts. |
| **Duplicate Checkouts (`test_duplicate_checkouts_prevented`)** | Verifies sequential duplicate checkouts (after one finishes and deletes cart, the next returns 400). | Verifies that a concurrent request B blocks on `select_for_update()` and waits, then reads empty state after A commits. |
| **Overselling Prevention** | Verifies that when stock is insufficient, the transaction cleanly rolls back. | Verifies that concurrent threads decrementing stock serialize without losing updates or creating race conditions. |

### Concurrency Limitations
Because SQLite uses a single database-wide write lock, concurrent threads attempting database writes will raise `sqlite3.OperationalError: database is locked` instead of waiting on individual rows. Therefore:
- The tests verify code correctness and transaction rollback integrity under SQLite.
- To prove actual non-blocking row-level lock concurrency queuing, the test suite would need to be run against a real transactional database (e.g., PostgreSQL) in a CI pipeline.
- SQLite passing checks do *not* prove production lock wait timeouts or deadlocks are resolved, but the sorted lock ordering guarantees it logically under DBMS systems that support row-level locks.

---

## 6. Documentation Correction
- **Wording Audit**: The phrasing "deadlock immunity" in `phase1_checkout_fix.md` is technically too strong. No application is completely immune to deadlocks under all circumstances.
- **Recommendation**: Update the wording to:
  > "Deterministic lock ordering prevents the identified checkout deadlock pattern."

---

## 7. Verification Summary & Next Steps
- **Unrelated Changes**: None found.
- **Safety to consider complete**: Yes. Phase 1 is safe, correct, and compiles cleanly with all 14 tests passing.
- **Phase 2 Readiness**: No outstanding issues exist. We can safely proceed to Phase 2.
