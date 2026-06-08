import hashlib
import hmac
import json
from typing import Any

import requests

from app.core.config import settings


class PayOSError(Exception):
    """Lỗi giao tiếp hoặc xác minh dữ liệu từ payOS."""


def _require_credentials() -> None:
    if not all(
        (
            settings.PAYOS_CLIENT_ID,
            settings.PAYOS_API_KEY,
            settings.PAYOS_CHECKSUM_KEY,
        )
    ):
        raise PayOSError("payOS chưa được cấu hình đầy đủ.")


def _headers() -> dict[str, str]:
    return {
        "x-client-id": settings.PAYOS_CLIENT_ID,
        "x-api-key": settings.PAYOS_API_KEY,
        "Content-Type": "application/json",
    }


def _sort_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _sort_nested(value[key])
            for key in sorted(value)
        }
    if isinstance(value, list):
        return [_sort_nested(item) for item in value]
    return value


def _stringify_signature_value(value: Any) -> str:
    if value is None or value in ("null", "NULL", "undefined"):
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(
            _sort_nested(value),
            ensure_ascii=False,
            separators=(",", ":"),
        )
    return str(value)


def create_signature(data: dict[str, Any]) -> str:
    sorted_data = sorted(data.items())
    query = "&".join(
        f"{key}={_stringify_signature_value(value)}"
        for key, value in sorted_data
    )
    return hmac.new(
        settings.PAYOS_CHECKSUM_KEY.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(data: dict[str, Any], signature: str) -> bool:
    if not settings.PAYOS_CHECKSUM_KEY or not signature:
        return False
    expected = create_signature(data)
    return hmac.compare_digest(expected.lower(), signature.lower())


def _request(method: str, path: str, **kwargs) -> dict[str, Any]:
    _require_credentials()
    url = f"{settings.PAYOS_BASE_URL.rstrip('/')}{path}"

    try:
        response = requests.request(
            method=method,
            url=url,
            headers=_headers(),
            timeout=settings.PAYOS_REQUEST_TIMEOUT,
            **kwargs,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise PayOSError("Không thể kết nối tới payOS.") from exc
    except ValueError as exc:
        raise PayOSError("payOS trả về dữ liệu không hợp lệ.") from exc

    if payload.get("code") != "00":
        raise PayOSError(payload.get("desc") or "payOS từ chối yêu cầu.")

    response_data = payload.get("data")
    response_signature = payload.get("signature")
    if response_data and response_signature:
        if not verify_signature(response_data, response_signature):
            raise PayOSError("Chữ ký phản hồi từ payOS không hợp lệ.")

    return payload


def create_payment_link(
    *,
    order_code: int,
    amount: int,
    description: str,
    expired_at: int,
    items: list[dict],
) -> dict[str, Any]:
    signed_data = {
        "amount": amount,
        "cancelUrl": settings.PAYOS_CANCEL_URL,
        "description": description,
        "orderCode": order_code,
        "returnUrl": settings.PAYOS_RETURN_URL,
    }
    payload = {
        **signed_data,
        "items": items,
        "expiredAt": expired_at,
        "signature": create_signature(signed_data),
    }
    return _request("POST", "/v2/payment-requests", json=payload)


def get_payment_link(payment_link_id_or_order_code: str | int) -> dict[str, Any]:
    return _request(
        "GET",
        f"/v2/payment-requests/{payment_link_id_or_order_code}",
    )


def cancel_payment_link(
    payment_link_id_or_order_code: str | int,
    reason: str,
) -> dict[str, Any]:
    return _request(
        "POST",
        f"/v2/payment-requests/{payment_link_id_or_order_code}/cancel",
        json={"cancellationReason": reason},
    )
