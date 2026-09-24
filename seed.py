import logging
import os
from datetime import date, timedelta
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import get_settings
from app.core.firestore import get_firestore_client
from app.core.security import hash_password
from app.models.batch import Batch
from app.models.prescription import Prescription, PrescriptionLine
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.user import User, UserRole
from app.services.expiry_sweeper import sweep_near_expiry_alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("medistock.seed")


def get_seed_engine():
    settings = get_settings()
    db_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    # Check if 'postgres' docker host is unreachable when running outside docker
    if "postgres:5432" in db_url:
        db_url_localhost = db_url.replace("postgres:5432", "localhost:5432")
        try:
            test_eng = create_engine(db_url_localhost, connect_args={"connect_timeout": 2})
            with test_eng.connect():
                return test_eng
        except Exception:
            logger.info("Local Postgres unavailable. Using SQLite 'sqlite:///medistock_dev.db' for seed script.")
            return create_engine("sqlite:///medistock_dev.db")
    return create_engine(db_url)


def seed_database() -> None:
    """One-command seed script for MediStock.
    Initializes database schema and populates sample domain data.
    """
    engine = get_seed_engine()
    logger.info("Initializing database tables...")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db:
        # 1. Seed Users
        existing_users = db.exec(select(User)).all()
        if not existing_users:
            logger.info("Seeding system users...")
            password_hash = hash_password("Password123!")

            pharmacist = User(
                email="pharmacist@medistock.com",
                role=UserRole.PHARMACIST,
                password_hash=password_hash,
            )
            manager = User(
                email="manager@medistock.com",
                role=UserRole.MANAGER,
                password_hash=password_hash,
            )
            doctor = User(
                email="doctor@medistock.com",
                role=UserRole.DOCTOR,
                password_hash=password_hash,
            )
            db.add_all([pharmacist, manager, doctor])
            db.commit()
            db.refresh(doctor)
            logger.info("Users seeded successfully.")
        else:
            doctor = db.exec(select(User).where(User.role == UserRole.DOCTOR)).first()
            logger.info(f"Database already has {len(existing_users)} users. Skipping user creation.")

        # 2. Seed Products
        existing_products = db.exec(select(Product)).all()
        if not existing_products:
            logger.info("Seeding products...")
            p1 = Product(name="Amoxicillin", strength="500mg")
            p2 = Product(name="Paracetamol", strength="500mg")
            p3 = Product(name="Insulin Glargine", strength="100U/ml")
            db.add_all([p1, p2, p3])
            db.commit()
            db.refresh(p1)
            db.refresh(p2)
            db.refresh(p3)
            logger.info("Products seeded successfully.")
        else:
            p1, p2, p3 = existing_products[:3]
            logger.info(f"Database already has {len(existing_products)} products. Skipping product creation.")

        # 3. Seed Batches
        existing_batches = db.exec(select(Batch)).all()
        today = date.today()

        if not existing_batches:
            logger.info("Seeding inventory batches (expired, near-expiry, and fresh FEFO candidates)...")

            # Expired batch (-5 days)
            b1 = Batch(
                product_id=p1.id,
                batch_no="BAT-AMX-EXPIRED",
                expiry_date=today - timedelta(days=5),
                qty_on_hand=50,
                cost=4.50,
            )
            # Near-expiry batch (+10 days)
            b2 = Batch(
                product_id=p1.id,
                batch_no="BAT-AMX-SOON",
                expiry_date=today + timedelta(days=10),
                qty_on_hand=150,
                cost=5.00,
            )
            # Fresh batch (+180 days)
            b3 = Batch(
                product_id=p1.id,
                batch_no="BAT-AMX-FRESH",
                expiry_date=today + timedelta(days=180),
                qty_on_hand=500,
                cost=5.00,
            )
            # Near-expiry Paracetamol (+20 days)
            b4 = Batch(
                product_id=p2.id,
                batch_no="BAT-PCT-SOON",
                expiry_date=today + timedelta(days=20),
                qty_on_hand=300,
                cost=1.50,
            )
            # Fresh Insulin (+90 days)
            b5 = Batch(
                product_id=p3.id,
                batch_no="BAT-INS-FRESH",
                expiry_date=today + timedelta(days=90),
                qty_on_hand=40,
                cost=45.00,
            )

            db.add_all([b1, b2, b3, b4, b5])
            db.commit()
            db.refresh(b1)
            db.refresh(b2)
            db.refresh(b3)
            db.refresh(b4)
            db.refresh(b5)

            # Record initial movements & Firestore timeline events
            movements = [
                StockMovement(batch_id=b1.id, delta=50, reason="Initial seed inventory", ref="SEED-001"),
                StockMovement(batch_id=b2.id, delta=150, reason="Initial seed inventory", ref="SEED-002"),
                StockMovement(batch_id=b3.id, delta=500, reason="Initial seed inventory", ref="SEED-003"),
                StockMovement(batch_id=b4.id, delta=300, reason="Initial seed inventory", ref="SEED-004"),
                StockMovement(batch_id=b5.id, delta=40, reason="Initial seed inventory", ref="SEED-005"),
            ]
            db.add_all(movements)
            db.commit()

            firestore_client = get_firestore_client()
            for b in [b1, b2, b3, b4, b5]:
                firestore_client.log_stock_event(
                    product_id=b.product_id,
                    batch_id=b.id,
                    qty_change=b.qty_on_hand,
                    reason="Initial seed inventory",
                    performed_by="seed_script",
                    metadata={"batch_no": b.batch_no, "expiry_date": str(b.expiry_date)},
                )
            logger.info("Batches & Stock Movements seeded successfully.")

        # 4. Seed Pending Prescription
        existing_prescriptions = db.exec(select(Prescription)).all()
        if not existing_prescriptions and doctor:
            logger.info("Seeding demo prescription...")
            rx = Prescription(
                doctor_id=doctor.id,
                patient_name="Jane Doe",
                status="pending",
            )
            db.add(rx)
            db.commit()
            db.refresh(rx)

            rx_line = PrescriptionLine(
                prescription_id=rx.id,
                product_id=p1.id,
                qty=50,
            )
            db.add(rx_line)
            db.commit()
            logger.info(f"Prescription #{rx.id} seeded successfully.")

        # 5. Refresh Firestore near-expiry alerts via daily sweeper
        logger.info("Running daily sweeper job to refresh Firestore expiry_alerts feed...")
        alerts = sweep_near_expiry_alerts(db, days=30)
        logger.info(f"Daily sweeper finished. {len(alerts)} alerts active in Firestore feed.")

    logger.info("\n=======================================================")
    logger.info("SEED COMPLETED SUCCESSFULLY!")
    logger.info("Demo User Credentials:")
    logger.info("  - Pharmacist: pharmacist@medistock.com / Password123!")
    logger.info("  - Store Manager: manager@medistock.com / Password123!")
    logger.info("  - Doctor: doctor@medistock.com / Password123!")
    logger.info("=======================================================\n")


if __name__ == "__main__":
    seed_database()
