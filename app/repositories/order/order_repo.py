from uuid import UUID
from sqlalchemy.orm import Session, joinedload

from app.models.booking import Booking, BookingItem, Event
from app.models.order import Order, OrderStatus

def _with_order_details(query):
    return query.options(
        joinedload(Order.user),
        joinedload(Order.payments),
        joinedload(Order.booking)
        .joinedload(Booking.event)
        .joinedload(Event.film),
        joinedload(Order.booking)
        .joinedload(Booking.booking_items)
        .joinedload(BookingItem.seat),
        joinedload(Order.booking)
        .joinedload(Booking.booking_items)
        .joinedload(BookingItem.ticket),
    )


def get_all_orders(db: Session, skip:int = 0, limit:int = 100):
    """Lấy tất cả danh sách đơn hàng"""
    return (
        _with_order_details(db.query(Order))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_order_by_id(db: Session, order_id: UUID):
    """Lấy đơn hàng theo id"""
    return _with_order_details(
        db.query(Order).filter(Order.id == order_id)
    ).first()

def create_order(db: Session, order_data: dict):
    """Tạo mới đơn hàng"""
    new_order = Order(**order_data)
    db.add(new_order)
    db.flush()
    db.refresh(new_order)
    
    return new_order

def get_order_by_booking_id(db: Session, booking_id: UUID):
    """Lấy đưn hàng theo booking id"""
    return db.query(Order).filter(
        Order.booking_id == booking_id
    ).first()


def get_order_by_order_code(db: Session, order_code: int):
    """Lấy đơn hàng hteo mã đơn hàng"""
    return db.query(Order).filter(
        Order.order_code == order_code
    ).first()

def get_order_by_id_and_user_id(
    db: Session,
    order_id: UUID,
    user_id: UUID,
):
    return (
        _with_order_details(db.query(Order))
        .filter(
            Order.id == order_id,
            Order.user_id == user_id,
        )
        .first()
    )
    
def get_orders_by_user_id(
    db: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
):
    """Lấy đơng hàng theo user id"""
    return (
        _with_order_details(db.query(Order))
        .filter(
            Order.user_id == user_id,
            Order.status.in_(
                [
                    OrderStatus.PENDING,
                    OrderStatus.PAID,
                ]
            ),
        )
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_order_for_update(db: Session, order_id: UUID):
    """Webhook cập nhật đồng thời"""
    return (
        db.query(Order)
        .filter(Order.id == order_id)
        .with_for_update()
        .first()
    )


def get_order_by_order_code_for_update(db: Session, order_code: int):
    """Khóa đơn hàng khi xử lý webhook theo mã đơn hàng."""
    return (
        db.query(Order)
        .filter(Order.order_code == order_code)
        .with_for_update()
        .first()
    )
