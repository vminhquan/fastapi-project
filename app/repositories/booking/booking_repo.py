from datetime import datetime, timedelta
from typing import Sequence
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.booking import (
    Booking,
    BookingItem,
    BookingStatus,
    Event,
    Seat,
    Ticket,
    TicketStatus,
)
from app.models.order import Order


def _with_booking_details(query):
    return query.options(
        joinedload(Booking.event).joinedload(Event.film),
        joinedload(Booking.event).joinedload(Event.room),
        joinedload(Booking.booking_items).joinedload(BookingItem.seat),
        joinedload(Booking.booking_items).joinedload(BookingItem.ticket),
    )


def create_booking(db: Session, booking_data: dict) -> Booking:
    booking = Booking(**booking_data)
    db.add(booking)
    db.flush()
    db.refresh(booking)
    return booking


def create_booking_items(
    db: Session,
    booking_items_data: list[dict],
) -> list[BookingItem]:
    booking_items = [
        BookingItem(**item_data)
        for item_data in booking_items_data
    ]
    db.add_all(booking_items)
    db.flush()
    return booking_items


def get_booking_by_id(db: Session, booking_id: UUID):
    return _with_booking_details(
        db.query(Booking).filter(Booking.id == booking_id)
    ).first()


def get_booking_for_update(db: Session, booking_id: UUID):
    return (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .with_for_update()
        .first()
    )


def get_bookings_by_user_id(
    db: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Booking]:
    return (
        _with_booking_details(db.query(Booking))
        .join(Order, Order.booking_id == Booking.id)
        .filter(Order.user_id == user_id)
        .order_by(Booking.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_booking_by_id_and_user_id(
    db: Session,
    booking_id: UUID,
    user_id: UUID,
):
    return (
        _with_booking_details(db.query(Booking))
        .join(Order, Order.booking_id == Booking.id)
        .filter(
            Booking.id == booking_id,
            Order.user_id == user_id,
        )
        .first()
    )


def get_all_bookings(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[Booking]:
    return (
        _with_booking_details(db.query(Booking))
        .order_by(Booking.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_booking_items_by_booking_id(
    db: Session,
    booking_id: UUID,
) -> list[BookingItem]:
    return (
        db.query(BookingItem)
        .filter(BookingItem.booking_id == booking_id)
        .order_by(BookingItem.created_at.asc())
        .all()
    )


def lock_seats_for_event(
    db: Session,
    event_id: UUID,
    seat_ids: Sequence[UUID],
) -> list[Seat]:
    if not seat_ids:
        return []

    return (
        db.query(Seat)
        .filter(
            Seat.event_id == event_id,
            Seat.id.in_(seat_ids),
        )
        .order_by(Seat.id.asc())
        .with_for_update()
        .all()
    )


def get_held_bookings_for_expiry_check(
    db: Session,
    limit: int = 100,
) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.status == BookingStatus.HELD)
        .order_by(Booking.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
        .all()
    )


def get_expired_issued_tickets_for_update(
    db: Session,
    now: datetime,
    limit: int = 500,
) -> list[Ticket]:
    return (
        db.query(Ticket)
        .join(BookingItem, Ticket.booking_item_id == BookingItem.id)
        .join(Booking, BookingItem.booking_id == Booking.id)
        .join(Event, Booking.event_id == Event.id)
        .filter(
            Ticket.status == TicketStatus.ISSUED,
            Event.end_time <= now + timedelta(minutes=15),
        )
        .order_by(Event.end_time.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
        .all()
    )


def create_tickets(
    db: Session,
    tickets_data: list[dict],
) -> list[Ticket]:
    tickets = [
        Ticket(**ticket_data)
        for ticket_data in tickets_data
    ]
    db.add_all(tickets)
    db.flush()
    return tickets


def get_ticket_by_qr_token(db: Session, qr_token: str):
    return db.query(Ticket).filter(Ticket.qr_token == qr_token).first()


def get_ticket_by_qr_token_for_update(db: Session, qr_token: str):
    return (
        db.query(Ticket)
        .filter(Ticket.qr_token == qr_token)
        .with_for_update()
        .first()
    )


def get_tickets_by_booking_id(
    db: Session,
    booking_id: UUID,
) -> list[Ticket]:
    return (
        db.query(Ticket)
        .join(BookingItem, Ticket.booking_item_id == BookingItem.id)
        .filter(BookingItem.booking_id == booking_id)
        .order_by(Ticket.issued_at.asc())
        .all()
    )


def get_tickets_by_user_id(
    db: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> list[Ticket]:
    return (
        db.query(Ticket)
        .join(BookingItem, Ticket.booking_item_id == BookingItem.id)
        .join(Booking, BookingItem.booking_id == Booking.id)
        .join(Order, Order.booking_id == Booking.id)
        .options(
            joinedload(Ticket.booking_item).joinedload(BookingItem.booking),
            joinedload(Ticket.booking_item).joinedload(BookingItem.seat),
        )
        .filter(Order.user_id == user_id)
        .order_by(Ticket.issued_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
