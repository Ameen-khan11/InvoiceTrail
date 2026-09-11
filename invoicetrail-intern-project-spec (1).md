# InvoiceTrail — Intern Project Specification (Beginner Level)

**Project type:** Multi-tenant SaaS web application
**Duration:** 6 weeks (~25–30 hrs/week, one intern)
**Stack (fixed):** React (Vite) · Flask REST API · MySQL

---

## 1. Problem Statement

Freelancers and small agencies send invoices and then forget about them. There is no system telling them "Client X owes you ₹40,000 and it's been 47 days." The invoice sits in a sent-mail folder, the freelancer feels awkward chasing it, and eventually writes it off.

**InvoiceTrail** is a simple invoice tracker. You add your clients, log each invoice you send, and the app tells you every morning what is overdue and how much money is sitting uncollected. One click sends the client a polite reminder email.

### Why this is a good beginner project
- The domain is obvious — no need to research a regulated industry to understand it.
- The data model is four tables. Nothing clever.
- It still has every real SaaS ingredient: signup, per-user data isolation, a dashboard, a scheduled job, transactional email, and plan limits.
- It is genuinely useful. The intern can use it themselves.

### Target user
Freelance designers, developers, writers, photographers, consultants, and 2–5 person agencies. Single user per account.

---

## 2. Technology Requirements

| Layer | Required | Notes |
|---|---|---|
| Frontend | React 18 + Vite, React Router, plain `fetch` | **No Redux, no Next.js, no component library beyond a CSS framework.** `useState` + `useEffect` + one custom `useAuth` hook is enough. |
| Styling | Plain CSS or Tailwind — pick one and stay | He already knows CSS. Do not let him fight a design system. |
| Backend | Flask + Flask-SQLAlchemy + Flask-CORS | Blueprints for route grouping. Marshmallow or manual dict serialization, either is fine. |
| Database | MySQL 8 | SQLAlchemy models, Alembic for migrations. |
| Auth | JWT via Flask-JWT-Extended | Access token in memory + refresh token, or a single 24h token. Either is acceptable at this level. |
| Passwords | `werkzeug.security` `generate_password_hash` / `check_password_hash` | Never `md5`, never plaintext. |
| Scheduled job | APScheduler inside Flask, **or** a standalone `cron_job.py` run by cron | No Celery, no Redis, no queue. |
| Email | SMTP via Flask-Mail, Gmail app password or Mailtrap in dev | Mailtrap is safer for a learner. |
| Deployment | Render / Railway / PythonAnywhere + Vercel/Netlify for the React build | Must be publicly reachable. |

**Architecture:** React is a separate app that talks to Flask over JSON. Flask serves **no HTML templates at all**. This separation is a core learning goal — he must feel the difference between the server-rendered Flask he knows and an API backend.

---

## 3. Scope

### 3.1 Must build
1. Signup, login, logout (JWT)
2. Per-user data isolation — every row belongs to one user
3. Client management (CRUD)
4. Invoice management (CRUD) with status lifecycle
5. Record payments against invoices, including partial payments
6. Dashboard with totals and an overdue list
7. Daily scheduled job that emails the user a summary of overdue invoices
8. Manual "Send reminder to client" button that emails the client
9. Search and filter on the invoice list
10. CSV export of invoices
11. Free plan limits with a manual upgrade flag
12. Deployed, seeded, documented, with a README

### 3.2 Do not build
- Teams, roles, invitations (single user per account)
- Real payment processing or Stripe
- PDF invoice generation (stretch goal only)
- File uploads
- Password reset by email (stretch goal)
- Recurring invoices
- Any AI feature

---

## 4. Functional Requirements

Each item below is testable. "AC" = acceptance criterion.

### FR-1 — Signup and login
> As a freelancer, I create an account and only ever see my own data.

- **AC-1.1** Signup takes name, email, password, and optional business name. Email must be unique.
- **AC-1.2** Password minimum 8 characters, hashed with `werkzeug.security`. Never returned by any endpoint, never logged.
- **AC-1.3** Login returns a JWT. The React app stores it and attaches `Authorization: Bearer <token>` to every request.
- **AC-1.4** Every protected endpoint uses `@jwt_required()`. An expired or missing token returns **401**, and the React app redirects to `/login`.
- **AC-1.5** Refreshing the browser must not log the user out. Restoring the session on page load is part of the requirement.
- **AC-1.6** Signup with an existing email returns a clear 409 error, not a 500.

### FR-2 — Data isolation *(most important backend requirement)*
- **AC-2.1** `clients`, `invoices`, and `payments` all carry a `user_id`.
- **AC-2.2** **Every single query filters by the JWT's user ID.** No endpoint may fetch by primary key alone.

  ```python
  # WRONG — this is the bug the whole project is designed to teach
  invoice = Invoice.query.get(invoice_id)

  # RIGHT
  invoice = Invoice.query.filter_by(id=invoice_id, user_id=current_user_id).first()
  ```
- **AC-2.3** Requesting another user's invoice ID returns **404**, not 403 and not the invoice.
- **AC-2.4** The intern must demonstrate this live: log in as User A, copy an invoice ID, log in as User B, hit the API with that ID, show the 404.

### FR-3 — Clients
- **AC-3.1** Fields: `name` (required), `email` (required, valid format), `company`, `phone`, `notes`.
- **AC-3.2** List, create, edit, delete. Delete is blocked if the client has invoices — show "This client has 4 invoices. Delete or reassign them first."
- **AC-3.3** The client detail page shows their invoices and total amount billed vs. total received.

### FR-4 — Invoices
- **AC-4.1** Fields: `invoice_number` (required, unique per user), `client_id` (required), `issue_date` (required), `due_date` (required), `amount` (required, > 0), `currency` (default INR), `description`, `status`.
- **AC-4.2** Status values: `draft`, `sent`, `partially_paid`, `paid`, `cancelled`. Plus a **derived** `overdue` state — an invoice is overdue when status is `sent` or `partially_paid` **and** `due_date < today`. Do not store `overdue` as a column; compute it.
- **AC-4.3** `due_date` must be on or after `issue_date`. Reject with a clear message otherwise.
- **AC-4.4** `amount` stored as `DECIMAL(12,2)`. **Never `FLOAT`** — money and floating point don't mix, and this is worth a five-minute conversation with him.
- **AC-4.5** Invoice list supports: search by invoice number or client name, filter by status and by client, sort by due date or amount, and pagination at 20 per page (server-side, using `LIMIT`/`OFFSET`).
- **AC-4.6** Editing a `paid` invoice's amount is blocked. Cancel and reissue instead.
- **AC-4.7** Deleting is a soft delete (`is_deleted` flag). Deleted invoices vanish from all lists and totals.

### FR-5 — Payments
- **AC-5.1** Record a payment against an invoice: `amount`, `paid_on`, `method` (cash/bank/UPI/card/other), `reference`.
- **AC-5.2** Multiple partial payments per invoice are allowed.
- **AC-5.3** Total payments may not exceed the invoice amount. Reject the excess with a clear error.
- **AC-5.4** Invoice status updates automatically: some payments → `partially_paid`; sum equals amount → `paid`.
- **AC-5.5** Deleting a payment recalculates the status correctly (a `paid` invoice can drop back to `partially_paid`).
- **AC-5.6** The invoice detail page shows amount, total paid, and balance due.

### FR-6 — Dashboard
- **AC-6.1** Four cards: **Total outstanding**, **Overdue amount**, **Paid this month**, **Invoice count by status**.
- **AC-6.2** An "Overdue" table sorted by days overdue, descending, showing client, amount, due date, and days late.
- **AC-6.3** A simple bar chart of monthly income for the last 6 months. Recharts is fine, or hand-rolled CSS bars.
- **AC-6.4** All totals computed in SQL with `SUM()` and `GROUP BY`, **not** by fetching every invoice into Python and looping. This is a deliberate teaching point — ask to see the query.
- **AC-6.5** A new account with zero data shows a helpful empty state, not blank boxes or `NaN`.

### FR-7 — Reminders
> The feature that makes this a product rather than a form.

- **AC-7.1** A scheduled job runs once daily at 09:00 server time.
- **AC-7.2** For each user with overdue invoices, it sends **one** summary email: total overdue amount and a list of overdue invoices with client, amount, and days late.
- **AC-7.3** Users with no overdue invoices get **no email**. Silence is a feature.
- **AC-7.4** The job writes a row to a `reminder_log` table (`user_id`, `sent_on`, `invoice_count`, `status`). Before sending, it checks whether a reminder already went out for that user on that date. **Running the job twice in one day must not send two emails.** This is the single most important line of logic in the project.
- **AC-7.5** If SMTP throws, the job logs the failure and continues to the next user. One bad address must not kill the batch.
- **AC-7.6** A "Send reminder" button on any unpaid invoice emails the **client** a polite message: invoice number, amount, due date, and the freelancer's name. The send is recorded on the invoice (`last_reminder_sent_at`) and shown in the UI.
- **AC-7.7** The client reminder button is disabled for 24 hours after use, to prevent accidental spam.
- **AC-7.8** A settings toggle to turn off the daily summary email.

### FR-8 — Export and plan limits
- **AC-8.1** Export the currently filtered invoice list to CSV using Python's `csv` module, streamed as a download.
- **AC-8.2** Free plan limits: **5 clients** and **20 invoices**. Enforced server-side in the create endpoints, returning **403** with a clear message.
- **AC-8.3** The `users` table has an `is_pro` boolean. Setting it to `1` in MySQL removes the limits. No payment integration — this teaches limit enforcement without the Stripe rabbit hole.
- **AC-8.4** The UI shows current usage ("12 of 20 invoices used") and a clear message at the limit, never a silent failure or a 500.

---

## 5. Data Model

```sql
users (
  id, name, email UNIQUE, password_hash, business_name,
  is_pro TINYINT DEFAULT 0, email_reminders_enabled TINYINT DEFAULT 1,
  created_at
)

clients (
  id, user_id FK, name, email, company, phone, notes, created_at,
  INDEX (user_id)
)

invoices (
  id, user_id FK, client_id FK, invoice_number, issue_date, due_date,
  amount DECIMAL(12,2), currency VARCHAR(3) DEFAULT 'INR', description,
  status ENUM('draft','sent','partially_paid','paid','cancelled'),
  last_reminder_sent_at, is_deleted TINYINT DEFAULT 0, created_at,
  UNIQUE (user_id, invoice_number),
  INDEX (user_id, status),
  INDEX (user_id, due_date)
)

payments (
  id, user_id FK, invoice_id FK, amount DECIMAL(12,2), paid_on,
  method, reference, created_at,
  INDEX (invoice_id)
)

reminder_log (
  id, user_id FK, sent_on DATE, invoice_count, status,
  UNIQUE (user_id, sent_on)   -- this constraint IS the deduplication
)
```

Note the `UNIQUE (user_id, sent_on)` on `reminder_log`. Ask him why that constraint is better than an `if` statement in Python. The answer — that two job runs racing each other can both pass the `if` check, but only one can win the unique index — is a real database lesson worth more than the rest of the CRUD combined.

---

## 6. API Endpoints

Hand him this list; it removes a lot of blank-page paralysis.

```
POST   /api/auth/signup
POST   /api/auth/login
GET    /api/auth/me

GET    /api/clients                 ?search=
POST   /api/clients
GET    /api/clients/<id>
PUT    /api/clients/<id>
DELETE /api/clients/<id>

GET    /api/invoices                ?status=&client_id=&search=&sort=&page=
POST   /api/invoices
GET    /api/invoices/<id>
PUT    /api/invoices/<id>
DELETE /api/invoices/<id>
POST   /api/invoices/<id>/remind
GET    /api/invoices/export         → CSV

POST   /api/invoices/<id>/payments
DELETE /api/payments/<id>

GET    /api/dashboard/summary
GET    /api/dashboard/monthly-income

GET    /api/settings
PUT    /api/settings
```

Conventions to enforce: JSON only, `snake_case` keys, correct status codes (200/201/400/401/403/404/409/422), and a consistent error shape:

```json
{ "error": "Invoice number already exists", "field": "invoice_number" }
```

---

## 7. Screens (6 total)

1. **Login / Signup** — one page, toggle between the two
2. **Dashboard** — cards, overdue table, chart
3. **Invoices** — table with search, filters, pagination; modal for create/edit
4. **Invoice detail** — details, payment history, add-payment form, remind button
5. **Clients** — table with modal for create/edit; client detail with their invoices
6. **Settings** — profile, email toggle, plan usage

Requirements for all screens: a loading state, an error state, an empty state, and mobile-usable layout. "It looks fine on my laptop" is not done.

---

## 8. Edge Cases He Must Handle

Only six, but ask about every one in review.

1. Two invoices, same number, same user → rejected with a 409, not a MySQL crash.
2. Payment of ₹5,000 recorded against an invoice with a ₹3,000 balance → rejected cleanly.
3. Deleting a payment on a fully paid invoice → status drops back to `partially_paid` correctly.
4. The daily job is run twice by accident → the second run sends zero emails.
5. Invoice due today at 23:59 → is it overdue? Pick a rule, document it, be consistent between the dashboard and the reminder job.
6. Deleting a client who has invoices → blocked with an explanation, never a foreign-key error page.

---

## 9. Six-Week Plan

| Week | Focus | Demo checkpoint |
|---|---|---|
| **1** | React fundamentals + project setup. Build the static UI with dummy data — no backend. Components, props, `useState`, React Router. | Clickable UI with fake data |
| **2** | Flask API skeleton, MySQL schema, models, migrations. Auth endpoints. Connect React login to real Flask. | Real login works end to end |
| **3** | Clients + invoices CRUD, both ends. Data isolation enforced everywhere. | Live cross-user 404 demo |
| **4** | Payments, status logic, search, filters, pagination. | Partial payment flow works |
| **5** | Dashboard queries, scheduled reminder job, both email types, CSV export, plan limits. | Reminder email lands in Mailtrap |
| **6** | Deploy, seed data, polish empty/error states, write README and docs, demo video. | Public URL, final presentation |

**Week 1 is deliberately backend-free.** He knows Flask. He does not know React. Let him struggle with components in isolation before adding network calls to the confusion.

**If he falls behind:** cut CSV export, then the chart, then plan limits. **Never cut** data isolation (FR-2) or the reminder job (FR-7) — those are the two things that make this a real project instead of a CRUD exercise.

---

## 10. Definition of Done

- [ ] Deployed at a public URL, frontend and backend both live
- [ ] `README.md` gets a fresh machine running in under 15 minutes
- [ ] Seed script creates 2 users with clients, invoices in every status, and some overdue
- [ ] All six edge cases handled and demonstrable
- [ ] No secrets in the repo — `.env` is gitignored, `.env.example` is committed
- [ ] No `SELECT *` without a `user_id` filter anywhere in the codebase
- [ ] Postman/Thunder Client collection covering every endpoint
- [ ] A short document listing every decision made and why
- [ ] 5-minute demo video

---

## 11. Grading

| Area | Weight |
|---|---|
| Data isolation done correctly everywhere | 25% |
| Reminder job: correct, idempotent, failure-tolerant | 20% |
| Working React frontend with proper state and loading/error handling | 20% |
| Database design, money as DECIMAL, sensible indexes, SQL aggregation | 15% |
| Error handling and UX polish | 10% |
| Documentation and deployment | 10% |

---

## 12. Stretch Goals (only after everything above ships)

1. PDF invoice generation with ReportLab or WeasyPrint
2. Password reset by email
3. Recurring invoices — auto-create monthly
4. A public read-only invoice link the client can open without an account
5. Dark mode
6. Multi-currency with a stored conversion rate

---

## 13. Questions to Ask Him in Week 1

His answers tell you whether he's thinking or copying.

1. Why do we return 404 instead of 403 when someone requests another user's invoice?
2. Why is `amount` a `DECIMAL` and not a `FLOAT`?
3. If the reminder job runs twice in one morning, what stops the second run from emailing everyone again? Where does that guarantee live?
4. Why compute the dashboard totals in SQL instead of looping in Python? At what number of invoices does the difference start to matter?
5. Why does `overdue` not exist as a column in the database?
