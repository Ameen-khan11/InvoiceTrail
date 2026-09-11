# InvoiceTrail — Architectural & Engineering Decisions (DECISIONS.md)

This document captures the core architectural, database, security, and algorithmic decisions made during the design and implementation of InvoiceTrail.

---

### 1. Cross-User Data Isolation: Returning 404 Instead of 403
**Decision:** When an authenticated user requests an ID belonging to another user, the API responds with **`404 Not Found`**, never `403 Forbidden`.

**Rationale:**
- Returning `403 Forbidden` reveals that the resource exists and leaks sensitive ID enumeration to unauthorized parties.
- Returning `404 Not Found` completely hides the existence of the resource. To User B, an invoice belonging to User A simply does not exist.
- Implemented uniformly in `app/utils/scoping.py` via `scoped_or_404(Model, record_id)`:
  ```python
  def scoped_or_404(model, record_id, user_id=None):
      uid = user_id if user_id is not None else current_user_id()
      return model.query.filter_by(id=record_id, user_id=uid).first()
  ```

---

### 2. Monetary Amounts: `DECIMAL(12, 2)` Never `FLOAT`
**Decision:** All currency values (`Invoice.amount`, `Payment.amount`) are stored in SQL as `DECIMAL(12, 2)` (SQLAlchemy `Numeric(12, 2)`) and manipulated in Python using the `decimal.Decimal` class.

**Rationale:**
- IEEE 754 floating point numbers cannot represent decimal fractions (like `0.10` or `0.01`) exactly, leading to rounding discrepancies like `0.1 + 0.2 = 0.30000000000000004`.
- In financial and invoicing systems, off-by-one-cent bugs corrupt balance calculations and tax compliance. `DECIMAL(12, 2)` provides exact fixed-point arithmetic up to ₹9,999,999,999.99.

---

### 3. Reminder Job Idempotency: `UNIQUE(user_id, sent_on)`
**Decision:** The guarantee that a user will not receive multiple daily summary emails in a single day lives in the database schema via `UNIQUE(user_id, sent_on)` on `reminder_log`, not purely in an `if` check in Python.

**Rationale:**
- In distributed environments or accidental parallel cron runs, two processes can both execute `if not already_sent:` at the exact same millisecond before either records the send.
- The unique index is atomic at the database transaction layer. Only one insert can commit; concurrent attempts trigger an `IntegrityError` that is rolled back safely, guaranteeing zero duplicate emails.

---

### 4. SQL Aggregation vs. In-Memory Python Loops
**Decision:** Dashboard metrics (`total_outstanding`, `overdue_amount`, `paid_this_month`, `counts_by_status`, and `monthly_income`) are computed strictly using SQL aggregate functions (`SUM`, `COUNT`, `GROUP BY`) with subqueries.

**Rationale:**
- Fetching thousands of invoice rows and their related payments into Python memory to compute sums causes high memory footprint, network bandwidth bottlenecks, and slow response times.
- Relational database engines execute indexed aggregates on disk pages in milliseconds with minimal data transfer.

---

### 5. `overdue` as a Derived State, Not a Stored Column
**Decision:** Invoices do not store an `overdue` status in the database. Overdue is derived dynamically:
```python
is_overdue = status in ("sent", "partially_paid") and due_date < date.today()
```

**Rationale:**
- If `overdue` were a stored column, every midnight a database job would have to find and update all past-due rows. If that job failed or lagged, data would become stale and incorrect.
- Computing it dynamically against `date.today()` ensures that an invoice is always 100% accurate at the moment of inspection.
- The rule is strictly defined: an invoice due on `2026-09-07` is **not** overdue on `2026-09-07`; it becomes overdue the following day (`due_date < today`).

---

### 6. Foreign Key Protection on Client Deletion
**Decision:** Deleting a client who has existing invoices (including soft-deleted invoices) is explicitly blocked with a **`409 Conflict`** and a human-friendly error message, rather than allowing an unhandled foreign key database exception or cascading deletion.

**Rationale:**
- Silently cascading client deletion would destroy financial records and invoice audit trails.
- Blocking with a clear message ("This client has 4 invoices. Delete or reassign them first.") preserves data integrity and informs the user clearly.

---

### 7. Soft Delete for Invoices
**Decision:** Invoices use an `is_deleted = Column(Boolean, default=False)` flag for deletion.

**Rationale:**
- Freelancers and agencies need historical audit records for tax and accounting purposes.
- Soft-deleted invoices are filtered out of regular lists, dashboard metrics, and client totals, but their transaction references remain intact.
