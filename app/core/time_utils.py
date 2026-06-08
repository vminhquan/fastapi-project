from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def app_now_naive() -> datetime:
    return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).replace(tzinfo=None)


def app_datetime_to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(settings.APP_TIMEZONE))
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def app_datetime_to_local_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(
        ZoneInfo(settings.APP_TIMEZONE)
    ).replace(tzinfo=None)


def effective_expiry_utc(
    *,
    created_at: datetime,
    hold_expires_at: datetime,
    order_created_at: datetime | None,
) -> datetime:
    """
    Dữ liệu cũ có thể lưu giờ local hoặc UTC. Khoảng thời gian giữ ghế vẫn
    chính xác, nên neo khoảng đó vào order.created_at do PostgreSQL lưu UTC.
    """
    hold_duration = hold_expires_at - created_at
    if (
        order_created_at is not None
        and _is_valid_hold_duration(hold_duration.total_seconds())
    ):
        if order_created_at.tzinfo is not None:
            order_created_at = order_created_at.astimezone(
                timezone.utc
            ).replace(tzinfo=None)
        return order_created_at + hold_duration

    if hold_expires_at.tzinfo is not None:
        return hold_expires_at.astimezone(timezone.utc).replace(tzinfo=None)
    return hold_expires_at


def _is_valid_hold_duration(seconds: float) -> bool:
    return 0 <= seconds <= 24 * 60 * 60
