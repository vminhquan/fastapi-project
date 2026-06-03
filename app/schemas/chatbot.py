from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., description="Tin nhắn khách hàng chat với bot")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Câu trả lời của Bot")