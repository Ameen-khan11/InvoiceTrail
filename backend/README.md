# InvoiceTrail — Backend API

InvoiceTrail is a multi-tenant SaaS backend for freelancers and micro-agencies to track invoices, record partial/full payments, view financial summaries via SQL aggregations, and automate overdue invoice email reminders with idempotent guarantees.

Built with **Flask**, **SQLAlchemy**, **MySQL** (and SQLite for automated testing), **Flask-JWT-Extended**, and **Flask-Mail**.

---

## Quickstart (Up and Running in < 10 Minutes)

### 1. Prerequisites
- Python 3.10+ installed
- MySQL 8.0+ running (or use SQLite test mode)

### 2. Virtual Environment Setup
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Copy the example configuration:
```powershell
cp .env.example .env
```
Update `.env` with your MySQL credentials and Mailtrap/SMTP settings:
```ini
FLASK_ENV=development
SECRET_KEY=dev-secret-key-please-change-in-prod
JWT_SECRET_KEY=dev-jwt-secret-key-please-change-in-prod
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/invoicetrail
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=2525
MAIL_USE_TLS=true
MAIL_USERNAME=your_mailtrap_user
MAIL_PASSWORD=your_mailtrap_password
MAIL_DEFAULT_SENDER=no-reply@invoicetrail.app
CORS_ORIGINS=http://localhost:5173
```

### 4. Seed the Database
Populate the database with 2 complete test accounts across all invoice statuses:
```powershell
python seed.py
```
This sets up:
- **User 1 (Free tier)**: `freelancer@example.com` / `Password123!`
  - 3 clients, 6 invoices (draft, sent, overdue, partially_paid, paid, cancelled), and payments.
- **User 2 (Pro tier)**: `agency@example.com` / `Password123!`
  - 2 clients, 2 invoices. Uses the same invoice number (`INV-2026-001`) to demonstrate per-user scoping.

### 5. Run the Server
```powershell
python run.py
```
Server runs at `http://localhost:5000`.

---

## Running the Automated Test Suite

The comprehensive test suite uses an in-memory SQLite database, requiring zero external database configuration:
```powershell
pytest -v
```
All tests verify:
- Authentication & JWT token security
- Client and Invoice CRUD operations
- Strict cross-user 404 data isolation
- Payment processing & status transitions (`sent` -> `partially_paid` -> `paid`)
- Payment deletion status rollback
- Dashboard SQL aggregation queries
- 24-hour rate-limiting on manual client reminders
- Cron job idempotency via unique constraint deduplication
- All 6 specification edge cases

---

## The 6 Specification Edge Cases Handled

1. **Duplicate invoice number for same user**: Handled via `UNIQUE(user_id, invoice_number)` constraint and caught cleanly as `409 Conflict`.
2. **Excess payment**: Recording a payment exceeding the remaining balance is rejected with `422 Unprocessable Entity`.
3. **Payment deletion on paid invoice**: Recalculates status and drops back to `partially_paid` or `sent`.
4. **Daily cron job run twice**: Backed by `UNIQUE(user_id, sent_on)` on `reminder_log`; duplicate runs send zero duplicate emails.
5. **Invoice due today at 23:59**: Overdue is strictly defined as `due_date < date.today()`. It is NOT overdue on its due date.
6. **Deleting client with invoices**: Blocked with `409 Conflict` and a human-friendly message, preventing foreign key crashes.

---

## Daily Reminder Cron Job

To run the scheduled reminder batch:
```powershell
python cron_job.py
```
Dispatches overdue invoice summaries to eligible users once per day.

---

## API Endpoints Reference

### Auth
- `POST /api/auth/signup` — Register new user
- `POST /api/auth/login` — Login & receive JWT access token
- `GET /api/auth/me` — Current user profile

### Clients
- `GET /api/clients?search=` — List clients with optional search
- `POST /api/clients` — Create client (enforces free plan limit of 5)
- `GET /api/clients/<id>` — Client details with invoice history and billed vs received totals
- `PUT /api/clients/<id>` — Update client details
- `DELETE /api/clients/<id>` — Delete client (blocked with 409 if invoices exist)

### Invoices
- `GET /api/invoices?status=&client_id=&search=&sort=&page=` — Paginated invoice listing
- `POST /api/invoices` — Create invoice (enforces free plan limit of 20)
- `GET /api/invoices/<id>` — Invoice detail with payment history
- `PUT /api/invoices/<id>` — Update invoice (blocks amount edits if paid)
- `DELETE /api/invoices/<id>` — Soft-delete invoice
- `POST /api/invoices/<id>/remind` — Send client reminder email (24-hour cooldown)
- `GET /api/invoices/export` — Stream filtered invoices to CSV download

### Payments
- `POST /api/invoices/<id>/payments` — Record payment (auto-updates invoice status)
- `DELETE /api/payments/<id>` — Delete payment (recalculates invoice status)

### Dashboard
- `GET /api/dashboard/summary` — SQL-aggregated metrics (total outstanding, overdue, paid this month, status counts, overdue table)
- `GET /api/dashboard/monthly-income` — 6-month monthly income breakdown in SQL

### Settings
- `GET /api/settings` — User profile, reminder preference, and plan usage counters
- `PUT /api/settings` — Update profile & reminder preference
