# InvoiceTrail — Multi-Tenant Invoicing & Payment Tracker

InvoiceTrail is a multi-tenant SaaS application built for freelancers and micro-agencies to track invoices, record partial and full payments, monitor overdue balances in real time, and automate overdue reminder emails.

**Live Architecture:**
- **Frontend:** React 18, Vite, React Router, Custom Context API (`useAuth`), Pure CSS Design System.
- **Backend:** Flask REST API, Flask-SQLAlchemy, MySQL 8 / SQLite (for testing), Flask-JWT-Extended, Flask-Mail.
- **Background Tasks:** Idempotent Daily Reminder Job (`cron_job.py`).

---

## Quickstart Guide (< 10 Minutes)

### 1. Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Set up your `.env` (a `.env.example` is provided):
```ini
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-prod
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-prod
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/invoicetrail
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=2525
MAIL_USE_TLS=true
MAIL_USERNAME=your_mailtrap_user
MAIL_PASSWORD=your_mailtrap_password
MAIL_DEFAULT_SENDER=no-reply@invoicetrail.app
CORS_ORIGINS=http://localhost:5173
```

Seed the database with sample data:
```powershell
python seed.py
```

Run the backend API:
```powershell
python run.py
```
Backend API will be running at `http://localhost:5000`.

---

### 2. Frontend Setup

In a separate terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Seed Accounts

The `seed.py` script automatically creates two test accounts:

1. **User 1 (Free Plan - Freelancer)**
   - **Email:** `freelancer@example.com`
   - **Password:** `Password123!`
   - **Data:** 3 clients, 6 invoices (draft, sent, overdue, partially_paid, paid, cancelled), partial payments recorded.

2. **User 2 (Pro Plan - Agency)**
   - **Email:** `agency@example.com`
   - **Password:** `Password123!`
   - **Data:** 2 clients, 2 invoices. Re-uses `INV-2026-001` to demonstrate per-user invoice number uniqueness.

---

## Automated Test Suite

Run the full pytest suite (32 tests):
```powershell
cd backend
.\venv\Scripts\pytest -v
```
All 32 tests run against an in-memory SQLite database (`sqlite:///:memory:`) with zero external database configuration required.

---

## The 6 Core Specification Edge Cases

| # | Edge Case | Handled By | Tested In |
|---|---|---|---|
| **1** | Duplicate invoice number for the same user | `UNIQUE(user_id, invoice_number)` constraint caught as 409 Conflict | `tests/test_edge_cases.py` |
| **2** | Payment exceeding remaining balance | Balance check in `payments.py` returning 422 Unprocessable Entity | `tests/test_edge_cases.py` |
| **3** | Deleting payment on paid invoice | Automatic status recalculation reverting status to `partially_paid` or `sent` | `tests/test_edge_cases.py` |
| **4** | Daily reminder job run twice in one day | Atomic `UNIQUE(user_id, sent_on)` on `reminder_log` prevents duplicate emails | `tests/test_edge_cases.py` |
| **5** | Invoice due today at 23:59 | Consistent rule: `due_date < date.today()` (not overdue until tomorrow) | `tests/test_edge_cases.py` |
| **6** | Deleting client who has invoices | Explicit count check returning 409 Conflict with friendly explanation | `tests/test_edge_cases.py` |

---

## Project Structure

```
PROJECT {4}/
├── invoicetrail-intern-project-spec (1).md   # Project specification
├── README.md                                 # Root documentation
├── backend/
│   ├── app/
│   │   ├── models/                           # User, Client, Invoice, Payment, ReminderLog
│   │   ├── routes/                           # auth, clients, invoices, payments, dashboard, settings
│   │   ├── utils/                            # error_response, scoping, validators
│   │   ├── config.py                         # Dev, Prod, Test configurations
│   │   ├── extensions.py                     # db, migrate, jwt, mail, cors
│   │   └── __init__.py                       # Application factory
│   ├── tests/                                # 32 automated tests (conftest + 7 test modules)
│   ├── cron_job.py                           # Idempotent daily reminder script
│   ├── seed.py                               # Database seed script
│   ├── run.py                                # Entry point
│   ├── requirements.txt                      # Dependencies
│   ├── DECISIONS.md                          # Architectural decisions documentation
│   └── invoicetrail_api_collection.json      # Postman/Thunder Client collection
└── frontend/
    ├── src/
    │   ├── context/AuthContext.jsx           # useAuth hook & persistent session
    │   ├── components/Layout.jsx             # Topbar navigation & user menu
    │   ├── pages/
    │   │   ├── Auth.jsx                      # Screen 1: Login / Signup toggle
    │   │   ├── Dashboard.jsx                 # Screen 2: Metrics, overdue table, chart
    │   │   ├── Invoices.jsx                  # Screen 3: Table, search, filters, pagination, CSV
    │   │   ├── InvoiceDetail.jsx             # Screen 4: Breakdown, payments history, remind button
    │   │   ├── Clients.jsx                   # Screen 5: Clients table, create/edit, detail modal
    │   │   └── Settings.jsx                  # Screen 6: Profile, email toggle, plan usage
    │   ├── api.js                            # Unified fetch client with JWT & 401 handling
    │   ├── index.css                         # Pure CSS design system
    │   ├── App.jsx                           # Router & protected routes
    │   └── main.jsx                          # App entry point
    ├── vite.config.js                        # Vite config with backend proxy
    └── package.json                          # Frontend dependencies
```
