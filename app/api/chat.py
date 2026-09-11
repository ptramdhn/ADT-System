from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.chat_assistant import chat_assistant

router = APIRouter(prefix="/api/chat", tags=["AI Chat Assistant"])

class ChatRequest(BaseModel):
    message: str

@router.post("/ask")
def ask_chat_endpoint(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong")
    
    reply = chat_assistant.answer_query(req.message.strip())
    return {"success": True, "reply": reply}
