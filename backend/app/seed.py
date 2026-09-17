"""Seed the database.

Loads:
  - two demo users (an analyst and a reviewer),
  - the 25-row existing vendor master from Appendix A4 (including the deliberate
    duplicate and partial-duplicate edge cases), which the duplicate-detection logic
    screens NEW submissions against.

Run:  python -m app.seed        (from the backend/ directory)

Idempotent: safe to re-run — it won't create duplicate users, and re-seeds the vendor
master only if it is empty.
"""
from .database import SessionLocal, engine, Base
from .models import User, Vendor
from .security import hash_password

# Appendix A4 — Vendor Master (existing vendors with edge cases).
# (name, abn, bank_account, category, note)
VENDOR_MASTER = [
    ("Acme Consulting Ltd", "12 345 678 901", "BSB 062-000 / 12345678", "Consulting", ""),
    ("Global Print Co", "98 765 432 100", "BSB 033-000 / 87654321", "Supplies", ""),
    ("FastCloud Infra", "55 444 333 222", "BSB 082-001 / 11223344", "IT", ""),
    ("Meridian Legal", "33 221 100 998", "BSB 062-000 / 99887766", "Legal", ""),
    ("OfficeHub Supplies", "77 666 555 444", "BSB 033-000 / 55443322", "Supplies", ""),
    ("TechForce Recruitment", "44 333 222 111", "BSB 082-001 / 22334455", "HR", ""),
    ("BlueSky Travel", "66 555 444 333", "BSB 062-000 / 66778899", "Travel", ""),
    ("DataBridge Analytics", "11 999 888 777", "BSB 033-000 / 33445566", "Analytics", ""),
    ("SecureVault Storage", "88 777 666 555", "BSB 082-001 / 44556677", "IT", ""),
    ("Acme Consulting Pty Ltd", "12 345 678 901", "BSB 062-000 / 12345678", "Consulting",
     "DUPLICATE - same ABN + bank as Acme Consulting Ltd"),
    ("BlueSky Travel Solutions", "66 555 444 333", "BSB 062-000 / 66778899", "Travel",
     "DUPLICATE - same ABN + bank as BlueSky Travel"),
    ("Nexus HR Partners", "22 111 000 999", "BSB 033-000 / 77889900", "HR", ""),
    ("PrimeEdge Consulting", "99 888 777 666", "BSB 082-001 / 55667788", "Consulting", ""),
    ("Global Print Company", "98 765 432 100", "BSB 019-000 / 11122233", "Supplies",
     "PARTIAL DUPLICATE - same ABN, different bank as Global Print Co"),
    ("Zenith Facilities Mgmt", "44 100 200 300", "BSB 062-000 / 88990011", "Facilities", ""),
    ("Atlas Risk Advisory", "55 200 300 400", "BSB 033-000 / 99001122", "Consulting", ""),
    ("Pinnacle Logistics", "66 300 400 500", "BSB 082-001 / 00112233", "Logistics", ""),
    ("Meridian Legal Group", "33 221 100 998", "BSB 062-000 / 99887766", "Legal",
     "DUPLICATE - same ABN + bank as Meridian Legal"),
    ("Summit Events Co", "77 400 500 600", "BSB 062-000 / 11223300", "Events", ""),
    ("ClearPath Consulting", "88 500 600 700", "BSB 033-000 / 22334400", "Consulting", ""),
    ("Vertex IT Solutions", "99 600 700 800", "BSB 082-001 / 33445500", "IT", ""),
    ("TechForce Talent", "44 333 222 111", "BSB 019-000 / 66778800", "HR",
     "PARTIAL DUPLICATE - same ABN as TechForce Recruitment, different bank"),
    ("Omega Document Services", "11 700 800 900", "BSB 062-000 / 44556600", "Supplies", ""),
    ("DataBridge Analytics Intl", "11 999 888 777", "BSB 033-000 / 33445566", "Analytics",
     "DUPLICATE - same ABN + bank as DataBridge Analytics"),
    ("Pacific FM Group", "22 800 900 100", "BSB 082-001 / 55667700", "Facilities", ""),
]

DEMO_USERS = [
    ("analyst@financeos.demo", "demo1234", "analyst"),
    ("reviewer@financeos.demo", "demo1234", "reviewer"),
]


def _contact(name: str) -> str:
    handle = name.lower().replace(" ", ".").replace(",", "")
    return f"ap@{handle}.example.com"


def seed() -> None:
    # Ensure tables exist even if the reviewer runs seed before alembic (belt and braces).
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Users
        created_users = 0
        for email, password, role in DEMO_USERS:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, password_hash=hash_password(password), role=role))
                created_users += 1
        db.commit()

        # Vendor master — only if empty (avoid duplicating on re-run).
        existing = db.query(Vendor).count()
        created_vendors = 0
        if existing == 0:
            for name, abn, bank, category, note in VENDOR_MASTER:
                db.add(
                    Vendor(
                        name=name,
                        abn=abn,
                        bank_account=bank,
                        contact=_contact(name),
                        category=category,
                        risk_tier=None,          # pre-existing, never AI-screened
                        ai_rationale=None,
                        screening_notes=None,
                        human_override=None,
                        onboarding_status="approved",  # already onboarded
                    )
                )
                created_vendors += 1
            db.commit()

        print(
            f"Seed complete: +{created_users} user(s), "
            f"+{created_vendors} vendor(s) (existing vendors already present: {existing})."
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed()
