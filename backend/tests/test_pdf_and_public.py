from datetime import date, timedelta
from decimal import Decimal
from app.extensions import db
from app.models import Client, Invoice


def test_authenticated_invoice_pdf_download(client, create_user):
    user, headers = create_user(email="pdf_user@example.com")
    c = Client(user_id=user.id, name="PDF Client", email="pdf_client@example.com")
    db.session.add(c)
    db.session.commit()

    inv = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="INV-PDF-001",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=14),
        amount=Decimal("15000.00"),
        description="Full stack development & deployment",
        status="sent",
    )
    db.session.add(inv)
    db.session.commit()

    # Authenticated user can download their invoice PDF
    res = client.get(f"/api/invoices/{inv.id}/pdf", headers=headers)
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert res.data.startswith(b"%PDF-")
    assert f"filename=Invoice-{inv.invoice_number}.pdf" in res.headers.get("Content-Disposition", "")


def test_cross_user_pdf_download_isolation(client, create_user):
    user_a, _ = create_user(email="user_a@example.com")
    user_b, headers_b = create_user(email="user_b@example.com")

    c = Client(user_id=user_a.id, name="User A Client", email="ua_client@example.com")
    db.session.add(c)
    db.session.commit()

    inv = Invoice(
        user_id=user_a.id,
        client_id=c.id,
        invoice_number="INV-SECRET-01",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=7),
        amount=Decimal("8000.00"),
        status="sent",
    )
    db.session.add(inv)
    db.session.commit()

    # User B attempting to download User A's invoice PDF must get 404 (Data Isolation)
    res = client.get(f"/api/invoices/{inv.id}/pdf", headers=headers_b)
    assert res.status_code == 404


def test_public_invoice_access_without_token(client, create_user):
    user, _ = create_user(email="public_owner@example.com", business_name="Apex Studios")
    c = Client(user_id=user.id, name="Client Apex", email="apex_client@example.com")
    db.session.add(c)
    db.session.commit()

    inv = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="INV-PUB-101",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=10),
        amount=Decimal("4500.00"),
        description="Logo & Branding Design",
        status="sent",
    )
    db.session.add(inv)
    db.session.commit()

    assert inv.public_token is not None
    token = inv.public_token

    # Public client access (no Authorization header provided)
    res = client.get(f"/api/public/invoices/{token}")
    assert res.status_code == 200
    data = res.get_json()

    assert data["invoice"]["invoice_number"] == "INV-PUB-101"
    assert data["invoice"]["amount"] == "4500.00"
    assert data["client"]["name"] == "Client Apex"
    assert data["business"]["name"] == "Apex Studios"


def test_public_invoice_invalid_token(client):
    # Invalid or forged token returns 404
    res = client.get("/api/public/invoices/non-existent-token-xyz")
    assert res.status_code == 404
    assert "Invoice not found or invalid link" in res.get_json()["error"]


def test_public_invoice_pdf_download(client, create_user):
    user, _ = create_user(email="public_pdf@example.com")
    c = Client(user_id=user.id, name="Pub Client", email="pub_client@example.com")
    db.session.add(c)
    db.session.commit()

    inv = Invoice(
        user_id=user.id,
        client_id=c.id,
        invoice_number="INV-PUB-PDF-99",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=5),
        amount=Decimal("2000.00"),
        status="sent",
    )
    db.session.add(inv)
    db.session.commit()

    # Public PDF download with valid token
    res = client.get(f"/api/public/invoices/{inv.public_token}/pdf")
    assert res.status_code == 200
    assert res.content_type == "application/pdf"
    assert res.data.startswith(b"%PDF-")
