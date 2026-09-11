# InvoiceTrail: System Architecture, Phased Implementation & Interview Guide

> **Project**: InvoiceTrail (SaaS Invoicing & Payment Tracking Platform for Freelancers & Micro-Agencies)  
> **Tech Stack**: Python (Flask 3), SQLAlchemy ORM, MySQL 8 / SQLite, JWT, ReportLab, React 18, Vite, Docker, Nginx, GitHub Actions CI.

---

## 1. System Architecture Overview

InvoiceTrail is architected as a decoupled, multi-tenant Single-Page Application (SPA) backed by a RESTful Flask API, designed around **strict multi-tenant data isolation**, **atomic database transactions**, and **deterministic business logic**.

```
                           ┌──────────────────────────────────────────────┐
                           │               Client Browsers                │
                           └──────────────────────┬───────────────────────┘
                                                  │ HTTP (Port 80)
                                                  ▼
                           ┌──────────────────────────────────────────────┐
                           │            Nginx Reverse Proxy               │
                           │  - Serves React 18 SPA (Vite Static Build)   │
                           │  - Gzip compression & static asset caching   │
                           │  - Reverse-proxies /api/ to backend Gunicorn │
                           └──────────────────────┬───────────────────────┘
                                                  │ Proxy Pass (Port 5000)
                                                  ▼
                           ┌──────────────────────────────────────────────┐
                           │          Flask 3 REST API (Gunicorn)         │
                           │  - JWT Bearer Authentication                 │
                           │  - Scoped multi-tenant data layer            │
                           │  - Financial calculation engine              │
                           │  - ReportLab PDF generator service           │
                           │  - Mailer & template service                 │
                           └──────────────┬───────────────────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
   ┌──────────────────────────────┐                ┌──────────────────────────────┐
   │    Primary Database Layer    │                │  Scheduled Jobs & Services   │
   │  MySQL 8.0 / SQLite (Test)   │                │  - cron_job.py (09:00 Daily) │
   │  - Users, Clients, Invoices  │                │  - Database Idempotency Lock │
   │  - Payments, Reminder Logs   │                │  - SMTP / Mailtrap Gateway   │
   │  - Composite Unique Indexes  │                └──────────────────────────────┘
   └──────────────────────────────┘
```

---

## 2. Complete Phased Roadmap (Phases 1 to 9)

### Phase 1: Database Architecture & Core Models
- **Flask App Factory Pattern**: `create_app(config_name)` encapsulates application instantiation, separating configuration across `development`, `testing`, and `production`.
- **SQLAlchemy 2.x ORM**:
  - `User`: Handles account identity, bcrypt password hash, business profile (`business_name`), plan tier (`is_pro`), and email reminder preference (`email_reminders_enabled`).
  - `Client`: Belongs to a single user (`user_id` foreign key). Contains contact info and notes.
  - `Invoice`: Foreign keys to `User` and `Client`. Stores financial amounts in high-precision `Numeric(12, 2)`, tracks lifecycle status (`draft`, `sent`, `partially_paid`, `paid`, `cancelled`), and soft-delete flag (`is_deleted`).
  - `Payment`: Records discrete payment transactions against invoices (`amount`, `paid_on`, `notes`).
  - `ReminderLog`: Tracks daily automated digest logs per user with a database-level unique constraint: `UNIQUE(user_id, sent_on)`.

### Phase 2: Authentication & Security
- **JWT (JSON Web Tokens)** via `flask_jwt_extended`:
  - `POST /api/auth/signup`: Validates email format, enforces strong passwords (minimum 8 characters), prevents duplicate emails (409 Conflict), hashes passwords using `werkzeug.security.generate_password_hash`.
  - `POST /api/auth/login`: Authenticates credentials and returns a signed JWT access token.
  - `GET /api/auth/me`: Protected endpoint (`@jwt_required()`) returning authenticated user profile.
- **Multi-Tenant Data Scoping Helper** (`app/utils/scoping.py`):
  - `scoped_or_404(Model, id, user_id=None)`: Resolves any record while strictly verifying `Model.user_id == current_user_id()`. If a record belongs to another user or doesn't exist, it returns a 404 Not Found (never 403, preventing IDOR information leakage).

### Phase 3: Client Management & Tier Enforcement
- **Scoped CRUD API** (`/api/clients`):
  - List, create, get, update, delete clients.
- **Free Tier Plan Limit (Business Rule)**:
  - Free users can have a maximum of **5 clients**. Exceeding this triggers an HTTP 403 Forbidden with `{ "error": "Free plan is limited to 5 clients. Upgrade to Pro for unlimited clients." }`.
- **Referential Integrity & Delete Guard**:
  - `DELETE /api/clients/<id>` checks if the client has existing non-deleted invoices. If so, deletion is blocked with an HTTP 409 Conflict (`Cannot delete client with active invoices.`), preventing orphaned accounting records.

### Phase 4: Invoice Engine & Date Validation
- **Lifecycle Management** (`/api/invoices`):
  - Supports status transitions: `draft` -> `sent` -> `partially_paid` -> `paid` -> `cancelled`.
- **Business Rule Validations**:
  - `due_date >= issue_date`: Due date cannot precede issue date.
  - `amount > 0`: Zero or negative invoice totals rejected (422).
  - Editing amount on a `paid` invoice is strictly blocked (409 Conflict).
  - Manual edits cannot arbitrarily set system-managed statuses (`paid`, `partially_paid`).
- **Scoped Uniqueness**:
  - `uq_user_invoice_number` composite constraint: A user cannot reuse an invoice number (e.g. `INV-001`), returning 409 Conflict. However, User B *can* have `INV-001`, ensuring multi-tenant flexibility.
- **Soft Deletion (`is_deleted`)**:
  - Invoices are never hard-deleted; `is_deleted = True` preserves audit trails and financial history.

### Phase 5: Payments Recording & Status Transitions
- **Payment Workflow** (`/api/invoices/<id>/payments`):
  - Recording a payment verifies `amount > 0` and ensures `total_paid + payment.amount <= invoice.amount`.
  - **Overpayment Guard**: If payment exceeds remaining balance, returns HTTP 422 Unprocessable Entity.
  - **Automatic Status Progression**:
    - If `total_paid == invoice.amount` -> `invoice.status = "paid"`.
    - If `0 < total_paid < invoice.amount` -> `invoice.status = "partially_paid"`.
- **Payment Deletion & Status Rollback** (`DELETE /api/payments/<id>`):
  - Deleting a payment recalculates total payments:
    - If remaining paid is 0 -> reverts to `sent` (or `draft`).
    - If remaining paid < amount -> reverts to `partially_paid`.
    - If remaining paid == amount -> stays `paid`.

### Phase 6: Financial Analytics, CSV Streaming & React SPA Frontend
- **High-Performance SQL Aggregations** (`/api/dashboard/summary`):
  - Calculates Total Outstanding, Overdue Amount, Paid This Month, and invoice breakdown by status in single optimized SQL queries using `SUM()` and `COUNT()` with `GROUP BY`.
  - Monthly income endpoint (`/api/dashboard/monthly-income`): 6-month historical revenue breakdown.
  - Empty state resilience: Never returns `null` or `NaN`; defaults to 0.00 and empty collections.
- **CSV Export Streaming** (`GET /api/invoices/export`):
  - Streams filtered invoices directly as CSV with proper `Content-Disposition: attachment; filename=invoices.csv`.
- **Full React 18 + Vite SPA**:
  - Responsive custom UI design system (`src/index.css`) with 6 primary views: Auth, Dashboard, Invoices, Invoice Detail, Clients, and Settings.

### Phase 7: Reminders & Notification Hardening
- **Single-Click Client Reminder** (`POST /api/invoices/<id>/remind`):
  - Allows freelancers to remind clients with one click.
  - **24-Hour Rate Limit**: Inspects `invoice.last_reminder_sent_at`. If less than 24 hours elapsed, returns HTTP 429 Too Many Requests (`A reminder was already sent in the last 24 hours.`).
- **Daily Scheduled Job** (`cron_job.py`):
  - Runs once daily at 09:00 server time.
  - Scans users with `email_reminders_enabled=True`.
  - **Database-Level Idempotency**: Inserts `ReminderLog(user_id, sent_on=today)` before sending. Any duplicate run on the same date hits the `UNIQUE(user_id, sent_on)` constraint, immediately aborting without sending duplicate emails.
  - Exception isolation: SMTP errors per user are caught and logged without aborting the batch.
- **Mailer Service Abstraction** (`app/services/mailer.py`):
  - Decoupled mailer handling both rich HTML and text emails with automatic simulation fallback when offline.

### Phase 8: Production Readiness, Containerization & CI/CD
- **Docker Containerization**:
  - `backend/Dockerfile`: Lightweight Python 3.11-slim container running Gunicorn WSGI server with 4 worker processes and healthchecks.
  - `frontend/Dockerfile`: Multi-stage build (Node 20 Alpine compiles Vite SPA -> Nginx Alpine serves static files).
  - `frontend/nginx.conf`: Gzip compression, SPA client-side routing fallback (`try_files $uri $uri/ /index.html`), and reverse proxy to backend `/api/`.
  - `docker-compose.yml`: Coordinates `db` (MySQL 8 with healthchecks and named volume persistence), `api`, and `web`.
- **Continuous Integration (CI/CD)**:
  - `.github/workflows/ci.yml`: Automated pipeline running on GitHub pull requests/commits, testing Python backend (`pytest -v`) and validating frontend build (`npm run build`).

### Phase 9: PDF Generation, Public Portal & Client Share Links
- **ReportLab PDF Generator Service** (`app/services/pdf_generator.py`):
  - Generates crisp, print-ready PDF invoices in memory (`io.BytesIO`) without temporary disk files.
  - Features company header, client billing details, status pill, itemized services table, payment history table, and bold balance due block.
  - Endpoints: `GET /api/invoices/<id>/pdf` (authenticated) and `GET /api/public/invoices/<token>/pdf` (public).
- **Public Client Portal & Share Links**:
  - Every invoice is automatically assigned a cryptographically secure URL-safe token: `public_token` (e.g. `secrets.token_urlsafe(32)`).
  - `GET /api/public/invoices/<token>`: Unauthenticated endpoint allowing clients to inspect invoice details, payment records, and business info without logging in.
  - Frontend standalone view: `/public/invoice/:token` (`PublicInvoice.jsx`) with no sidebar, responsive invoice view, and one-click "Download PDF" button.
  - "Copy Public Link" button in `InvoiceDetail.jsx` with instant clipboard copy and visual feedback.

---

## 3. The 6 Critical Edge Cases: Deep Dive

| # | Edge Case | Business Risk | Technical Solution | Test Verification |
|---|-----------|---------------|-------------------|-------------------|
| **1** | **Duplicate Invoice Numbers** | Accounting confusion, duplicate billing. | Composite DB constraint: `UNIQUE(user_id, invoice_number)`. Flask returns 409 Conflict if same user tries duplicate; allowed across different users. | `test_edge_case_1_duplicate_invoice_number` |
| **2** | **Overpayment Guard** | Inconsistent ledger, negative balance due. | Checked in `payments.py`: `total_paid + new_amount <= invoice.amount`. Returns 422 Unprocessable Entity if exceeded. | `test_edge_case_2_excess_payment_rejected` |
| **3** | **Payment Deletion Status Recalculation** | Invoice remains marked `paid` after a payment is deleted. | In `payments.py:delete_payment`: Automatically recalculates `total_paid` from remaining payments and updates `status` (`paid` -> `partially_paid` -> `sent`). | `test_edge_case_3_delete_payment_on_paid_invoice` |
| **4** | **Cron Job Double Run (Idempotency)** | Spamming users with multiple emails if cron triggers twice. | Atomic DB constraint `ReminderLog.UNIQUE(user_id, sent_on)`. Second run catches `IntegrityError`, logs, and skips. | `test_edge_case_4_daily_job_double_run_idempotency` |
| **5** | **Overdue Date Boundary** | Incorrectly flagging an invoice due today as overdue. | Unified rule in DB queries and model property: `due_date < date.today()`. If `due_date == today`, it is NOT overdue until tomorrow. | `test_edge_case_5_invoice_due_today_not_overdue` |
| **6** | **Client Deletion with Invoices** | Orphaned financial records or cascade data loss. | In `clients.py:delete_client`: Queries for non-deleted invoices associated with client. If count > 0, aborts with 409 Conflict. | `test_edge_case_6_delete_client_with_invoices_blocked` |

---

## 4. Top 25 Interview / Viva Questions & Model Answers

### Q1: Why did you choose Flask over Django or FastAPI for InvoiceTrail?
**Answer**: Flask was chosen for its minimalist, unopinionated architecture which gives us full granular control over our application layers. For a multi-tenant micro-SaaS, we wanted precise control over SQLAlchemy sessions, custom scoping utilities (`scoped_or_404`), lightweight JWT lifecycle management, and minimal runtime overhead. Django brings heavy built-in assumptions (such as an admin site and session-based auth) that aren't optimal for headless REST APIs, while FastAPI's async capabilities were unnecessary since standard database drivers (like PyMySQL) are synchronous.

### Q2: How do you prevent Insecure Direct Object Reference (IDOR) vulnerabilities?
**Answer**: In many naive implementations, endpoints accept an ID and query `Model.query.get(id)`. If an attacker changes the ID in the URL, they can access another user's private financial data. In InvoiceTrail, every database query passes through our `scoped_or_404` helper, which appends `filter_by(user_id=current_user_id)` to every lookup. If the ID belongs to another tenant, it returns a 404 Not Found rather than a 403 Forbidden. This ensures an attacker cannot even probe for the existence of other tenants' records.

### Q3: Why is financial currency stored as `Numeric(12, 2)` instead of `Float`?
**Answer**: Floats use IEEE 754 binary floating-point representation, which cannot precisely represent base-10 decimal fractions like `0.1` or `0.01`. In financial arithmetic, accumulating float errors leads to off-by-one-cent rounding discrepancies (e.g. `0.1 + 0.2 = 0.30000000000000004`). By using `Numeric(12, 2)` in SQLAlchemy (mapping to `DECIMAL(12, 2)` in MySQL and Python's `decimal.Decimal`), all additions, subtractions, and balance comparisons are exact.

### Q4: How is the invoice status lifecycle modeled, and why shouldn't a user manually edit status to `paid`?
**Answer**: Invoices follow a state machine: `draft -> sent -> partially_paid -> paid -> cancelled`. We explicitly designate `paid` and `partially_paid` as **system-managed statuses**. If a user could manually set an invoice to `paid` without recording a payment record, the accounting ledger would be broken: the invoice would say paid, but total payments would be 0, causing balance due discrepancies. Therefore, `PUT /api/invoices/<id>` rejects manual edits that specify `paid` or `partially_paid`, requiring users to record actual payments through the `/payments` API.

### Q5: How did you ensure the daily reminder cron job is idempotent?
**Answer**: Application-level checks (`if existing_record: skip`) are vulnerable to race conditions if two worker instances execute simultaneously. In InvoiceTrail, idempotency is enforced at the database schema level using `ReminderLog(user_id, sent_on)` with a `UNIQUE(user_id, sent_on)` constraint. Before sending an email, the job commits a `ReminderLog` row for `(user.id, today)`. If a concurrent or subsequent execution attempts the same insertion, MySQL rejects it with an `IntegrityError`, preventing duplicate emails.

### Q6: What is the difference between hard delete and soft delete, and why did you choose soft delete for invoices?
**Answer**: A hard delete runs `DELETE FROM invoices WHERE id = ...`, permanently removing the record. In financial accounting and compliance, deleting invoices erases audit trails and corrupts payment references. We implemented soft deletion via `is_deleted = db.Column(db.Boolean, default=False)`. All queries automatically filter `is_deleted == False`. This preserves historical transactions, allows invoice recovery if necessary, and ensures payment records maintain their foreign key integrity.

### Q7: Why does `DELETE /api/clients/<id>` return a 409 Conflict instead of cascading delete?
**Answer**: In our schema, `Invoice` has a foreign key to `Client`. If we enabled `ON DELETE CASCADE`, deleting a client would inadvertently delete all of their invoices and payments, destroying historical revenue records. Returning a 409 Conflict with a clear error message forces the user to resolve or archive the client's financial history first, protecting critical business data.

### Q8: Explain how you prevent race conditions when two users submit payments concurrently.
**Answer**: In payment processing, concurrent requests could both check `total_paid + amount <= invoice.amount`, see that space remains, and both commit, causing an overpayment. To prevent this, we execute the payment insertion and invoice status update inside a single atomic database transaction (`db.session.commit()`). In high-concurrency environments, this can be further guarded using `with_for_update()` (pessimistic locking) on the `Invoice` row during payment calculation.

### Q9: How do you handle public invoice sharing without exposing internal API endpoints?
**Answer**: We introduced a `public_token` field on the `Invoice` model generated with Python's cryptographically secure `secrets.token_urlsafe(32)`. We exposed dedicated public endpoints: `GET /api/public/invoices/<token>` and `GET /api/public/invoices/<token>/pdf`. These endpoints do not accept or require JWT authorization headers and return only the sanitized public view of that specific invoice and client name, completely isolating user account credentials and private dashboard data.

### Q10: How does your test suite test database interactions without polluting production or development databases?
**Answer**: In `tests/conftest.py`, pytest initializes the Flask application with `TestingConfig`, which configures `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"`. For every test session or function, `db.create_all()` builds the entire schema in RAM, runs the test assertions, and `db.drop_all()` destroys it. This provides instantaneous test execution (<8 seconds for 37 tests) with zero side-effects on local MySQL instances.

### Q11: How do you generate PDFs in Python, and why generate them in memory?
**Answer**: We use `ReportLab`'s `SimpleDocTemplate` and `Platypus` flowables (Paragraphs, Tables, Spacers). Instead of writing the generated PDF to a temporary file on the server's disk (which causes disk I/O bottlenecks, disk-space leaks, and multi-worker file permission issues), we write directly into an `io.BytesIO` in-memory stream and return it via Flask's `send_file(buffer, mimetype="application/pdf")`.

### Q12: How does the 24-hour reminder cooldown work?
**Answer**: `Invoice` has a `last_reminder_sent_at` timestamp. When `POST /api/invoices/<id>/remind` is triggered, the server checks `(datetime.now(timezone.utc) - last_sent).total_seconds() < 86400`. If less than 24 hours have passed, it immediately returns HTTP 429 Too Many Requests. The frontend also disables the "Send Reminder" button and displays a "Reminded recently" cooldown label.

### Q13: What happens if the SMTP server goes down during the daily reminder cron job?
**Answer**: The cron job wraps each individual user's email dispatch in a `try...except` block. If SMTP fails (e.g. timeout or auth error), the failure is logged, the `ReminderLog.status` is set to `"failed"`, and the loop continues to the next user. A failure on one user does not crash the script or prevent other users from receiving their digests.

### Q14: How are dates validated to prevent invalid chronological ranges?
**Answer**: During invoice creation and editing, the API parses `issue_date` and `due_date` using `datetime.strptime(val, "%Y-%m-%d")`. If `due_date < issue_date`, the API returns HTTP 422 with `{ "error": "Due date cannot be before issue date.", "field": "due_date" }`. The frontend also performs pre-submit client-side validation.

### Q15: Why use Nginx in front of Gunicorn in Docker?
**Answer**: Gunicorn is an application server optimized for running Python WSGI workers, but it is not designed to handle slow clients, SSL termination, static file caching, or malicious HTTP request buffering. Nginx serves as a battle-tested reverse proxy that handles TCP connection pooling, gzip compression, static asset serving, and request forwarding to Gunicorn over an internal Docker network.

### Q16: How do you support multi-tenancy in a single database?
**Answer**: InvoiceTrail uses **logical multi-tenancy (row-level isolation)**. Every tenant-specific table (`clients`, `invoices`, `payments`, `reminder_log`) has a foreign key to `users.id`. All queries are strictly scoped to the authenticated user ID extracted from the verified JWT claims. Composite unique indexes (such as `(user_id, invoice_number)`) ensure tenant uniqueness without collisions.

### Q17: How does the dashboard query calculate metrics efficiently?
**Answer**: Rather than loading thousands of invoice objects into Python memory and computing sums with Python loops, the dashboard executes native SQL aggregation queries:
`SELECT SUM(amount - COALESCE(payments_sum, 0)) FROM invoices WHERE user_id = :uid AND is_deleted = 0`.
This pushes all computation to the database engine, utilizing composite indexes on `(user_id, status)` and `(user_id, due_date)` to execute in sub-millisecond time.

### Q18: What is CORS, and how is it configured in InvoiceTrail?
**Answer**: Cross-Origin Resource Sharing (CORS) is a browser security mechanism that restricts web pages from making requests to a different domain/port than the one that served the page. We use `flask_cors.CORS` configured with `app.config["CORS_ORIGINS"]`, allowing explicit origins (e.g. `http://localhost:5173` in development, or the production domain) while rejecting unauthorized third-party origins.

### Q19: Why use React Router instead of multi-page server-side rendering (SSR)?
**Answer**: Invoicing dashboards are high-interaction tools where users constantly filter tables, toggle modals, record partial payments, and inspect metrics. A client-side SPA built with React Router provides instantaneous page transitions without full page reloads, smooth modal states, and efficient client-side caching of session tokens.

### Q20: How does the application prevent duplicate invoice numbers?
**Answer**: We declare a table argument `db.UniqueConstraint("user_id", "invoice_number", name="uq_user_invoice_number")` on `Invoice`. If a user attempts to create an invoice with an existing number, SQLAlchemy raises an `IntegrityError` upon `commit()`. The API catches this and returns a user-friendly HTTP 409 Conflict with `{ "field": "invoice_number", "error": "This invoice number already exists" }`.

### Q21: What is the purpose of the `.env.example` file?
**Answer**: Secret keys, database passwords, and SMTP credentials must never be committed to source control (Git). `.env.example` acts as a developer blueprint showing all required environment variables with sanitized placeholder values, allowing any engineer to configure their local environment in seconds by copying it to `.env`.

### Q22: How do you format CSV streaming without loading the entire dataset into memory?
**Answer**: In `export_invoices()`, we stream the output using `io.StringIO` and Python's `csv.writer`, returning Flask's `Response(csv_data, mimetype="text/csv")`. For multi-million row datasets, this can be adapted to a Python generator function yielding chunks with `Response(stream_with_context(generate()))`.

### Q23: How are passwords hashed and verified?
**Answer**: Passwords are never stored in plain text. When a user signs up, `user.set_password(password)` runs `werkzeug.security.generate_password_hash(password, method="scrypt")`, generating a cryptographically salted one-way hash. Upon login, `user.check_password(password)` verifies the input against the stored hash in constant time to prevent timing attacks.

### Q24: How does the system handle an invoice that is due today? Is it overdue?
**Answer**: By strict business definition, an invoice is due at the end of its due date. Therefore, an invoice is overdue **only if `due_date < date.today()`**. If `due_date == date.today()`, it is still active. This exact logic is enforced uniformly across the ORM property (`Invoice.is_overdue`), the dashboard SQL queries, and the reminder job.

### Q25: How would you scale InvoiceTrail to 1,000,000 active invoices?
**Answer**:
1. **Read Replicas**: Direct all dashboard aggregations and export queries to MySQL read replicas, keeping the primary instance dedicated to writes.
2. **Redis Caching**: Cache user dashboard summaries (`/api/dashboard/summary`) with a 5-minute TTL, invalidating the cache key only when new invoices or payments are committed.
3. **Asynchronous Distributed Cron**: Migrate `cron_job.py` from a single script to a distributed task queue (Celery + Redis), chunking users across parallel worker pods.
4. **Database Partitioning**: Partition the `invoices` and `payments` tables by `user_id` or date range to maintain index performance at scale.
