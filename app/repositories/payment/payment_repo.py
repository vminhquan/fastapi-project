from uuid import UUID

from sqlalchemy.orm import Session

from app.models.payment import Payment


def create_payment(db: Session, payment_data: dict) -> Payment:
    payment = Payment(**payment_data)
    db.add(payment)
    db.flush()
    db.refresh(payment)
    return payment


def get_payment_by_id(db: Session, payment_id: UUID):
    return db.query(Payment).filter(Payment.id == payment_id).first()


def get_payment_by_id_for_update(db: Session, payment_id: UUID):
    return (
        db.query(Payment)
        .filter(Payment.id == payment_id)
        .with_for_update()
        .first()
    )


def get_payments_by_order_id(
    db: Session,
    order_id: UUID,
) -> list[Payment]:
    return (
        db.query(Payment)
        .filter(Payment.order_id == order_id)
        .order_by(Payment.created_at.desc())
        .all()
    )


def get_latest_payment_by_order_id(
    db: Session,
    order_id: UUID,
):
    return (
        db.query(Payment)
        .filter(Payment.order_id == order_id)
        .order_by(Payment.created_at.desc())
        .first()
    )


def get_payment_by_provider_order_code(
    db: Session,
    provider_order_code: int,
    provider: str = "payos",
):
    return (
        db.query(Payment)
        .filter(
            Payment.provider == provider,
            Payment.provider_order_code == provider_order_code,
        )
        .first()
    )


def get_payment_by_provider_order_code_for_update(
    db: Session,
    provider_order_code: int,
    provider: str = "payos",
):
    return (
        db.query(Payment)
        .filter(
            Payment.provider == provider,
            Payment.provider_order_code == provider_order_code,
        )
        .with_for_update()
        .first()
    )


def get_payment_by_payment_link_id(
    db: Session,
    payment_link_id: str,
    provider: str = "payos",
):
    return (
        db.query(Payment)
        .filter(
            Payment.provider == provider,
            Payment.payment_link_id == payment_link_id,
        )
        .first()
    )


def get_payment_by_payment_link_id_for_update(
    db: Session,
    payment_link_id: str,
    provider: str = "payos",
):
    return (
        db.query(Payment)
        .filter(
            Payment.provider == provider,
            Payment.payment_link_id == payment_link_id,
        )
        .with_for_update()
        .first()
    )


def get_payment_by_transaction_reference(
    db: Session,
    transaction_reference: str,
    provider: str = "payos",
):
    return (
        db.query(Payment)
        .filter(
            Payment.provider == provider,
            Payment.transaction_reference == transaction_reference,
        )
        .first()
    )
