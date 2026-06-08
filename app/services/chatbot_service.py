from datetime import datetime, time, timedelta
import unicodedata

from fastapi import HTTPException
import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.booking import Event, Film
from app.models.user import User  # noqa: F401
from uuid import UUID


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


def _normalize_message(message: str) -> str:
    normalized = unicodedata.normalize("NFD", message.lower().strip())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _format_price(price: float) -> str:
    return f"{price:,.0f}".replace(",", ".")


def _format_events(events: list[Event], title: str) -> str:
    if not events:
        return "QTIK Bot chưa thấy suất chiếu phù hợp trong hệ thống. Bạn thử chọn ngày khác hoặc hỏi tên phim cụ thể nhé."

    lines = [title]
    for event in events:
        film_title = event.film.title if event.film else "Không rõ tên phim"
        room_name = f" - Phòng {event.room.name}" if event.room else ""
        start_time = event.start_time.strftime("%H:%M ngày %d/%m/%Y")
        lines.append(f"- {film_title}: {start_time}{room_name} | Giá vé: {_format_price(event.price)} VND")

    return "\n".join(lines)


def _get_today_events(db: Session) -> list[Event]:
    now = datetime.now()
    tomorrow = datetime.combine(now.date() + timedelta(days=1), time.min)
    return (
        db.query(Event)
        .filter(Event.start_time >= now, Event.start_time < tomorrow)
        .order_by(Event.start_time)
        .all()
    )


def _get_upcoming_events(db: Session) -> list[Event]:
    now = datetime.now()
    return (
        db.query(Event)
        .filter(Event.start_time >= now)
        .order_by(Event.start_time)
        .limit(20)
        .all()
    )


def _find_film_from_message(db: Session, user_message: str) -> Film | None:
    normalized_message = _normalize_message(user_message)
    films = db.query(Film).all()

    for film in films:
        if _normalize_message(film.title) in normalized_message:
            return film

    return None


def _get_events_for_film(db: Session, film_id: UUID) -> list[Event]:
    now = datetime.now()
    return (
        db.query(Event)
        .filter(Event.film_id == film_id, Event.start_time >= now)
        .order_by(Event.start_time)
        .all()
    )


def _handle_database_intent(db: Session, user_message: str) -> str | None:
    message = _normalize_message(user_message)

    if not message:
        return "QTIK Bot đây. Bạn muốn xem phim đang chiếu, lịch chiếu hôm nay hay giá vé phim nào?"

    greetings = {"hello", "hi", "xin chao", "chao", "hey"}
    if message in greetings:
        return "Xin chào, mình là QTIK Bot. Bạn muốn xem phim gì hoặc lịch chiếu hôm nay không?"

    film = _find_film_from_message(db, user_message)
    if film:
        events = _get_events_for_film(db, film.id)
        return _format_events(events, f"Lịch chiếu sắp tới của phim '{film.title}':")

    is_today_question = any(keyword in message for keyword in ["hom nay", "toi nay", "ngay nay"])
    asks_schedule = any(keyword in message for keyword in ["phim", "lich", "chieu", "suat", "ve", "gia"])
    asks_movies = "phim" in message and any(keyword in message for keyword in ["co gi", "co phim gi", "dang chieu", "lich chieu", "suat chieu", "xem gi"])

    if is_today_question and asks_schedule:
        events = _get_today_events(db)
        return _format_events(events, "Các suất chiếu còn lại hôm nay ở QTIK:")

    if asks_movies or any(keyword in message for keyword in ["lich chieu", "suat chieu", "gia ve"]):
        events = _get_upcoming_events(db)
        return _format_events(events, "Các phim/suất chiếu sắp tới ở QTIK:")

    cinema_keywords = ["phim", "lich", "chieu", "suat", "ve", "gia", "rap", "phong", "dat","ghe"]
    if not any(keyword in message for keyword in cinema_keywords):
        return "QTIK Bot chưa hiểu rõ ý bạn. Bạn có thể hỏi mình về phim đang chiếu, lịch chiếu hôm nay hoặc giá vé nhé."

    return None


def _ask_chatgpt(user_message: str) -> str:
    api_key = settings.CHATGPT_API_KEY or settings.OPENAI_API_KEY
    if not api_key:
        return "QTIK Bot chưa được cấu hình API key ChatGPT. Bạn kiểm tra lại biến CHATGPT_API_KEY trong file .env nhé."

    system_instruction = """
    Bạn là QTIK Bot, nhân viên tư vấn nhiệt tình của rạp chiếu phim QTIK.
    Chỉ trả lời trong phạm vi tư vấn phim, lịch chiếu, suất chiếu, giá vé và đặt vé.
    Nếu thiếu dữ liệu thực tế, hãy nói cần kiểm tra hệ thống thay vì tự bịa giờ chiếu hoặc giá vé.
    Trả lời ngắn gọn, thân thiện, xưng là "QTIK Bot" và gọi khách là "bạn".
    """

    payload = {
        "model": settings.OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
    except requests.RequestException:
        return "QTIK Bot đang không kết nối được tới ChatGPT. Bạn thử lại sau ít phút nhé."

    if response.status_code == 429:
        return "QTIK Bot đang bị giới hạn lượt gọi AI tạm thời. Bạn vẫn có thể hỏi mình về phim, lịch chiếu hoặc giá vé trong hệ thống nhé."

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi kết nối tới ChatGPT: {response.text}",
        )

    data = response.json()
    return data["choices"][0]["message"]["content"]


def get_bot_response_logic(db: Session, user_message: str) -> str:
    """Logic chatbot QTIK: ưu tiên dữ liệu hệ thống, chỉ gọi ChatGPT khi cần tư vấn tự nhiên."""
    database_reply = _handle_database_intent(db, user_message)
    if database_reply:
        return database_reply

    return _ask_chatgpt(user_message)
