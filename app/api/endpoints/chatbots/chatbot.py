from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas import chatbot as chatbot_schema
from app.services import chatbot_service
from app.core.database import get_db

router = APIRouter()
@router.post("/", response_model=chatbot_schema.ChatResponse)
def chat_with_qtik_bot(
    request: chatbot_schema.ChatRequest,
    db: Session = Depends(get_db)
):
    """
    API để Frontend gửi tin nhắn của User lên và nhận câu trả lời từ AI
    """
    ai_reply = chatbot_service.get_bot_response_logic(db, request.message)
    
    return {"reply": ai_reply}
