"""InvoiceTrail — Database Seed Script.

Creates two realistic test accounts:
1. freelancer@example.com / Password123! (Free Plan)
   - 3 Clients
   - Invoices covering all statuses: draft, sent, partially_paid, paid, cancelled, overdue
   - Payments demonstrating partial payment and full payment
2. agency@example.com / Password123! (Pro Plan)
   - 2 Clients
   - Re-uses invoice number INV-2026-001 to prove unique-per-user constraint
   - Ready for live demonstration of cross-user 404 data isolation

Usage:
    python seed.py
"""

from datetime import date, timedelta
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models import User, Client, Invoice, Payment, ReminderLog


def seed_database():
    app = create_app()

    with app.app_context():
        # Ensure all tables exist without dropping existing customer data
        db.create_all()

        existing = User.query.filter_by(email="freelancer@example.com").first()
        if existing:
            print("Database already contains seed data. Skipping seed.")
            return

        print("Creating User 1 (Freelancer - Free Plan)...")
        u1 = User(
            name="https_ameen",
            email="freelancer@example.com",
            business_name="https_ameen",
            is_pro=False,
            email_reminders_enabled=True,
        )
        u1.set_password("Password123!")
        db.session.add(u1)
        db.session.flush()

        print("Creating User 2 (Agency - Pro Plan)...")
        u2 = User(
            name="Rahul Verma",
            email="agency@example.com",
            business_name="Apex Media Agency",
            is_pro=True,
            email_reminders_enabled=True,
        )
        u2.set_password("Password123!")
        db.session.add(u2)
        db.session.flush()

        # Clients for User 1
        c1_acme = Client(
            user_id=u1.id,
            name="Acme Corp",
            email="contact@acme.com",
            company="Acme Corporation Ltd",
            phone="+91 98765 43210",
            notes="Quarterly branding and UI design client. Pays on 30-day terms.",
        )
        c1_stark = Client(
            user_id=u1.id,
            name="Stark Media",
            email="finance@starkmedia.io",
            company="Stark Media Pvt Ltd",
            phone="+91 98234 56789",
            notes="Marketing agency partner. Requires detailed descriptions on invoices.",
        )
        c1_bluewave = Client(
            user_id=u1.id,
            name="BlueWave Tech",
            email="invoicing@bluewave.in",
            company="BlueWave Technologies",
            phone="+91 97111 22334",
            notes="SaaS product consultancy client.",
        )
        c1_zenith = Client(
            user_id=u1.id,
            name="Zenith Logistics",
            email="billing@zenithlogistics.pk",
            company="Zenith Global Freight Ltd",
            phone="+92 345 5551234",
            notes="Logistics tracking portal contract.",
        )
        c1_orion = Client(
            user_id=u1.id,
            name="Orion Creative Labs",
            email="accounts@orionlabs.io",
            company="Orion Interactive Studio",
            phone="+92 312 4448899",
            notes="Mobile game UI design retainer.",
        )
        db.session.add_all([c1_acme, c1_stark, c1_bluewave, c1_zenith, c1_orion])
        db.session.flush()

        # Clients for User 2 (6 Enterprise Clients)
        c2_nexus = Client(
            user_id=u2.id,
            name="Nexus Retail",
            email="accounts@nexusretail.com",
            company="Nexus Retail Networks",
            phone="+92 301 9900112",
            notes="Enterprise omni-channel retail client.",
        )
        c2_cloudscale = Client(
            user_id=u2.id,
            name="CloudScale Inc",
            email="billing@cloudscale.net",
            company="CloudScale Cloud Solutions",
            phone="+92 315 8899001",
            notes="Cloud migration and DevOps consultancy.",
        )
        c2_hyperion = Client(
            user_id=u2.id,
            name="Hyperion Global",
            email="finance@hyperionglobal.com",
            company="Hyperion Enterprise Systems",
            phone="+92 334 7766554",
            notes="ERP integration & enterprise software audit.",
        )
        c2_solaris = Client(
            user_id=u2.id,
            name="Solaris Energy",
            email="invoices@solarisenergy.io",
            company="Solaris Renewable Power Corp",
            phone="+92 322 3344556",
            notes="Clean energy dashboard and IoT monitoring UI.",
        )
        c2_vanguard = Client(
            user_id=u2.id,
            name="Vanguard FinTech",
            email="payables@vanguardfintech.com",
            company="Vanguard Financial Technologies",
            phone="+92 308 1122334",
            notes="Payment gateway compliance & mobile banking redesign.",
        )
        c2_lumina = Client(
            user_id=u2.id,
            name="Lumina Health",
            email="procurement@luminahealth.org",
            company="Lumina Healthcare Systems",
            phone="+92 340 6677889",
            notes="Hospital patient portal & telemetry dashboard.",
        )
        db.session.add_all([c2_nexus, c2_cloudscale, c2_hyperion, c2_solaris, c2_vanguard, c2_lumina])
        db.session.flush()

        today = date.today()

        # Invoices for User 1
        # 1. Overdue sent invoice
        inv1 = Invoice(
            user_id=u1.id,
            client_id=c1_acme.id,
            invoice_number="INV-2026-001",
            issue_date=today - timedelta(days=45),
            due_date=today - timedelta(days=15),
            amount=Decimal("25000.00"),
            currency="PKR",
            description="Website Redesign & Figma Design System delivery",
            status="sent",
        )

        # 2. Overdue partially paid invoice
        inv2 = Invoice(
            user_id=u1.id,
            client_id=c1_stark.id,
            invoice_number="INV-2026-002",
            issue_date=today - timedelta(days=40),
            due_date=today - timedelta(days=10),
            amount=Decimal("40000.00"),
            currency="PKR",
            description="Mobile Application UI Kit and Prototyping",
            status="partially_paid",
        )

        # 3. Sent (not overdue yet)
        inv3 = Invoice(
            user_id=u1.id,
            client_id=c1_bluewave.id,
            invoice_number="INV-2026-003",
            issue_date=today - timedelta(days=5),
            due_date=today + timedelta(days=15),
            amount=Decimal("18000.00"),
            currency="PKR",
            description="Consultancy for Dashboard UX Improvements",
            status="sent",
        )

        # 4. Paid in full
        inv4 = Invoice(
            user_id=u1.id,
            client_id=c1_acme.id,
            invoice_number="INV-2026-004",
            issue_date=today - timedelta(days=60),
            due_date=today - timedelta(days=30),
            amount=Decimal("30000.00"),
            currency="PKR",
            description="Logo and Brand Identity Guidelines",
            status="paid",
        )

        # 5. Draft invoice
        inv5 = Invoice(
            user_id=u1.id,
            client_id=c1_stark.id,
            invoice_number="INV-2026-005",
            issue_date=today,
            due_date=today + timedelta(days=30),
            amount=Decimal("12000.00"),
            currency="PKR",
            description="Social Media Graphics Bundle (10 Assets)",
            status="draft",
        )

        # 6. Cancelled invoice
        inv6 = Invoice(
            user_id=u1.id,
            client_id=c1_bluewave.id,
            invoice_number="INV-2026-006",
            issue_date=today - timedelta(days=70),
            due_date=today - timedelta(days=40),
            amount=Decimal("15000.00"),
            currency="PKR",
            description="Exploratory workshop (project cancelled by client)",
            status="cancelled",
        )

        # 7. Sent (active, due soon)
        inv7 = Invoice(
            user_id=u1.id,
            client_id=c1_zenith.id,
            invoice_number="INV-2026-007",
            issue_date=today - timedelta(days=10),
            due_date=today + timedelta(days=7),
            amount=Decimal("55000.00"),
            currency="PKR",
            description="Fleet Tracking Interface Architecture & Wireframes",
            status="sent",
        )

        # 8. Partially paid (active)
        inv8 = Invoice(
            user_id=u1.id,
            client_id=c1_zenith.id,
            invoice_number="INV-2026-008",
            issue_date=today - timedelta(days=18),
            due_date=today + timedelta(days=12),
            amount=Decimal("90000.00"),
            currency="PKR",
            description="Dispatcher Dashboard Development & React Components",
            status="partially_paid",
        )

        # 9. Paid in full (recent)
        inv9 = Invoice(
            user_id=u1.id,
            client_id=c1_orion.id,
            invoice_number="INV-2026-009",
            issue_date=today - timedelta(days=25),
            due_date=today - timedelta(days=5),
            amount=Decimal("42000.00"),
            currency="PKR",
            description="Game UI Icon Pack and Inventory Screen Layouts",
            status="paid",
        )

        # 10. Draft
        inv10 = Invoice(
            user_id=u1.id,
            client_id=c1_orion.id,
            invoice_number="INV-2026-010",
            issue_date=today,
            due_date=today + timedelta(days=21),
            amount=Decimal("38000.00"),
            currency="PKR",
            description="HUD Animation Specs & Texture Atlas Optimization",
            status="draft",
        )

        db.session.add_all([inv1, inv2, inv3, inv4, inv5, inv6, inv7, inv8, inv9, inv10])
        db.session.flush()

        # Payments for User 1
        p1 = Payment(
            user_id=u1.id,
            invoice_id=inv2.id,
            amount=Decimal("15000.00"),
            paid_on=today - timedelta(days=12),
            method="upi",
            reference="EP/20260824/987123",
        )
        p2 = Payment(
            user_id=u1.id,
            invoice_id=inv4.id,
            amount=Decimal("10000.00"),
            paid_on=today - timedelta(days=45),
            method="bank",
            reference="HBL-00192837",
        )
        p3 = Payment(
            user_id=u1.id,
            invoice_id=inv4.id,
            amount=Decimal("20000.00"),
            paid_on=today - timedelta(days=32),
            method="bank",
            reference="HBL-00195521",
        )
        p4 = Payment(
            user_id=u1.id,
            invoice_id=inv8.id,
            amount=Decimal("50000.00"),
            paid_on=today - timedelta(days=8),
            method="bank",
            reference="MEZN-88771122",
        )
        p5 = Payment(
            user_id=u1.id,
            invoice_id=inv9.id,
            amount=Decimal("42000.00"),
            paid_on=today - timedelta(days=7),
            method="card",
            reference="STRIPE-CH-994411",
        )
        db.session.add_all([p1, p2, p3, p4, p5])

        # ==========================================
        # 12 Invoices for User 2 (Agency Pro Plan)
        # ==========================================
        inv_u2_1 = Invoice(
            user_id=u2.id,
            client_id=c2_nexus.id,
            invoice_number="INV-2026-001",
            issue_date=today - timedelta(days=10),
            due_date=today + timedelta(days=20),
            amount=Decimal("180000.00"),
            currency="PKR",
            description="Full-stack E-commerce checkout integration & speed optimization",
            status="sent",
        )

        inv_u2_2 = Invoice(
            user_id=u2.id,
            client_id=c2_cloudscale.id,
            invoice_number="INV-2026-002",
            issue_date=today - timedelta(days=25),
            due_date=today - timedelta(days=5),
            amount=Decimal("350000.00"),
            currency="PKR",
            description="Enterprise AWS infrastructure automation & Kubernetes cluster setup",
            status="partially_paid",
        )

        inv_u2_3 = Invoice(
            user_id=u2.id,
            client_id=c2_hyperion.id,
            invoice_number="INV-2026-003",
            issue_date=today - timedelta(days=50),
            due_date=today - timedelta(days=20),
            amount=Decimal("500000.00"),
            currency="PKR",
            description="Quarterly SAP ERP integration, data synchronization & custom ETL",
            status="paid",
        )

        inv_u2_4 = Invoice(
            user_id=u2.id,
            client_id=c2_solaris.id,
            invoice_number="INV-2026-004",
            issue_date=today - timedelta(days=12),
            due_date=today + timedelta(days=18),
            amount=Decimal("275000.00"),
            currency="PKR",
            description="Solar Grid Telemetry Dashboard & Real-time WebSockets Architecture",
            status="sent",
        )

        inv_u2_5 = Invoice(
            user_id=u2.id,
            client_id=c2_vanguard.id,
            invoice_number="INV-2026-005",
            issue_date=today - timedelta(days=42),
            due_date=today - timedelta(days=12),
            amount=Decimal("420000.00"),
            currency="PKR",
            description="FinTech Payment Security Audit & Biometric Auth Flow Implementation",
            status="sent",
        )

        inv_u2_6 = Invoice(
            user_id=u2.id,
            client_id=c2_lumina.id,
            invoice_number="INV-2026-006",
            issue_date=today - timedelta(days=60),
            due_date=today - timedelta(days=30),
            amount=Decimal("310000.00"),
            currency="PKR",
            description="Hospital EHR System Frontend & HIPAA Compliance Overhaul",
            status="paid",
        )

        inv_u2_7 = Invoice(
            user_id=u2.id,
            client_id=c2_nexus.id,
            invoice_number="INV-2026-007",
            issue_date=today,
            due_date=today + timedelta(days=30),
            amount=Decimal("125000.00"),
            currency="PKR",
            description="Black Friday promotional landing pages & load test benchmark",
            status="draft",
        )

        inv_u2_8 = Invoice(
            user_id=u2.id,
            client_id=c2_cloudscale.id,
            invoice_number="INV-2026-008",
            issue_date=today - timedelta(days=3),
            due_date=today + timedelta(days=27),
            amount=Decimal("290000.00"),
            currency="PKR",
            description="Multi-region disaster recovery and continuous backup pipelines",
            status="sent",
        )

        inv_u2_9 = Invoice(
            user_id=u2.id,
            client_id=c2_hyperion.id,
            invoice_number="INV-2026-009",
            issue_date=today - timedelta(days=15),
            due_date=today + timedelta(days=15),
            amount=Decimal("600000.00"),
            currency="PKR",
            description="Supply chain predictive analytics module & machine learning pipeline",
            status="partially_paid",
        )

        inv_u2_10 = Invoice(
            user_id=u2.id,
            client_id=c2_solaris.id,
            invoice_number="INV-2026-010",
            issue_date=today - timedelta(days=35),
            due_date=today - timedelta(days=5),
            amount=Decimal("195000.00"),
            currency="PKR",
            description="Energy consumption forecasting algorithm & customer portal widgets",
            status="paid",
        )

        inv_u2_11 = Invoice(
            user_id=u2.id,
            client_id=c2_vanguard.id,
            invoice_number="INV-2026-011",
            issue_date=today,
            due_date=today + timedelta(days=45),
            amount=Decimal("480000.00"),
            currency="PKR",
            description="Microservices architecture migration phase 2 delivery",
            status="draft",
        )

        inv_u2_12 = Invoice(
            user_id=u2.id,
            client_id=c2_lumina.id,
            invoice_number="INV-2026-012",
            issue_date=today - timedelta(days=80),
            due_date=today - timedelta(days=50),
            amount=Decimal("150000.00"),
            currency="PKR",
            description="Legacy server migration (cancelled in favor of native cloud overhaul)",
            status="cancelled",
        )

        db.session.add_all([
            inv_u2_1, inv_u2_2, inv_u2_3, inv_u2_4, inv_u2_5, inv_u2_6,
            inv_u2_7, inv_u2_8, inv_u2_9, inv_u2_10, inv_u2_11, inv_u2_12,
        ])
        db.session.flush()

        # Payments for User 2
        p_u2_1 = Payment(
            user_id=u2.id,
            invoice_id=inv_u2_2.id,
            amount=Decimal("150000.00"),
            paid_on=today - timedelta(days=8),
            method="bank",
            reference="RTGS-99008811",
        )
        p_u2_2 = Payment(
            user_id=u2.id,
            invoice_id=inv_u2_3.id,
            amount=Decimal("200000.00"),
            paid_on=today - timedelta(days=35),
            method="bank",
            reference="WIRE-PK-554411",
        )
        p_u2_3 = Payment(
            user_id=u2.id,
            invoice_id=inv_u2_3.id,
            amount=Decimal("300000.00"),
            paid_on=today - timedelta(days=22),
            method="bank",
            reference="WIRE-PK-554499",
        )
        p_u2_4 = Payment(
            user_id=u2.id,
            invoice_id=inv_u2_6.id,
            amount=Decimal("310000.00"),
            paid_on=today - timedelta(days=31),
            method="bank",
            reference="RTGS-77221199",
        )
        p_u2_5 = Payment(
            user_id=u2.id,
            invoice_id=inv_u2_9.id,
            amount=Decimal("250000.00"),
            paid_on=today - timedelta(days=5),
            method="bank",
            reference="RTGS-33118800",
        )
        p_u2_6 = Payment(
            user_id=u2.id,
            invoice_id=inv_u2_10.id,
            amount=Decimal("195000.00"),
            paid_on=today - timedelta(days=6),
            method="card",
            reference="AMEX-CORP-9922",
        )
        db.session.add_all([p_u2_1, p_u2_2, p_u2_3, p_u2_4, p_u2_5, p_u2_6])

        db.session.commit()

        print("\nDatabase seeded successfully with expanded datasets!")
        print("-" * 60)
        print("User 1 (Freelancer - Free tier):")
        print("  Email:    freelancer@example.com")
        print("  Password: Password123!")
        print("  Clients:  5 (Acme Corp, Stark Media, BlueWave Tech, Zenith Logistics, Orion Creative Labs)")
        print("  Invoices: 10 (INV-2026-001 to INV-2026-010: draft, sent, overdue, partial, paid, cancelled)")
        print("  Payments: 5 payments recorded across partial and paid invoices")
        print("-" * 60)
        print("User 2 (Agency - Pro tier):")
        print("  Email:    agency@example.com")
        print("  Password: Password123!")
        print("  Clients:  6 (Nexus, CloudScale, Hyperion, Solaris, Vanguard, Lumina)")
        print("  Invoices: 12 (INV-2026-001 to INV-2026-012: large enterprise scale)")
        print("  Payments: 6 enterprise RTGS/wire payments recorded")
        print("-" * 60)
        print("Ready for testing! All data uses PKR currency and realistic relative dates.")


if __name__ == "__main__":
    seed_database()
