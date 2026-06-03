from app.core.config import settings
from fastapi import HTTPException
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from app.models.booking import Film, Event 

client = genai.Client(api_key=settings.GEMINI_API_KEY)

def get_bot_response_logic(db: Session, user_message: str) -> str:
    """Logic Chatbot có tích hợp Function Calling (Truy cập Database QTIK)"""
    
  
    # 1. ĐỊNH NGHĨA TOOLS CHO AI
    # Lưu ý: Phải có Type Hint (str) và Docstring ("""...""") rõ ràng. 
    # AI sẽ dựa 100% vào Docstring này để quyết định có gọi hàm hay không!
    def tim_lich_chieu_phim(ten_phim: str) -> str:
        """
        Dùng hàm này khi khách hàng hỏi về lịch chiếu, giờ chiếu hoặc giá vé của một bộ phim bất kỳ.
        Hàm sẽ trả về danh sách các suất chiếu thực tế trong hệ thống.
        """
        # Truy vấn Database
        film = db.query(Film).filter(Film.title.ilike(f"%{ten_phim}%")).first()
        
        if not film:
            return f"Hệ thống báo: Rạp QTIK hiện tại không chiếu bộ phim nào có tên '{ten_phim}'."
            
        # Lấy lịch chiếu của phim này (Chỉ lấy các phim chưa chiếu xong)
        from datetime import datetime
        now = datetime.now()
        events = db.query(Event).filter(Event.film_id == film.id, Event.start_time > now).all()
        
        if not events:
            return f"Hệ thống báo: Phim '{film.title}' có trong rạp nhưng hiện chưa có suất chiếu nào sắp diễn ra."
            
        # Gom data lịch chiếu lại thành text để AI đọc
        ket_qua = f"Đây là dữ liệu thực tế lịch chiếu phim '{film.title}':\n"
        for e in events:
            gio_chieu = e.start_time.strftime('%H:%M ngày %d/%m/%Y')
            ket_qua += f"- Suất chiếu lúc {gio_chieu} | Giá vé: {e.price} VND\n"
            
        return ket_qua

    # ==========================================
    # 2. CẤU HÌNH AI & CHỈ THỊ (PROMPT ENGINEERING)
    # ==========================================
    system_instruction = """
    Bạn là QTIK Bot, nhân viên tư vấn nhiệt tình của rạp chiếu phim QTIK.
    QUY TẮC BẮT BUỘC:
    1. Khi khách hỏi về phim, lịch chiếu hoặc giá vé, BẠN PHẢI DÙNG CÔNG CỤ 'tim_lich_chieu_phim' để tra cứu.
    2. Tuyệt đối không được tự bịa ra giờ chiếu hoặc giá vé. Chỉ nói dựa trên dữ liệu hệ thống trả về.
    3. Tư vấn thân thiện, tự nhiên, xưng là "QTIK Bot" và gọi khách là "bạn", dùng emoji cho sinh động.
    4. Trả lời ngắn gọn, format ngày giờ đẹp mắt.
    """
    
    try:
        # SDK mới của Google sẽ TỰ ĐỘNG nhận diện, TỰ ĐỘNG chạy hàm Python và TỰ ĐỘNG trả lời
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[tim_lich_chieu_phim],
                temperature=0.3 # Giảm nhiệt độ xuống 0.3 để bot tập trung vào sự thật (data), bớt bay bổng
            )
        )
        return response.text
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi kết nối tới AI: {str(e)}")