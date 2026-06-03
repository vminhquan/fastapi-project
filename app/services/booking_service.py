from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

# Import Models và Schemas (Điều chỉnh lại đường dẫn cho đúng với project của bạn)
from app.models.booking import Event, Seat, Booking, Ticket, SeatStatus, BookingStatus
from app.schemas.booking import BookingCreate

def _normalize_datetime(value: datetime) -> datetime:
    """Đưa datetime về cùng kiểu naive theo giờ local để so sánh ổn định"""
    if value.tzinfo is not None:
        return value.astimezone().replace(tzinfo=None)
    return value

# ==========================================
# 1. CREATE: TẠO ĐƠN HÀNG (GIỮ CHỖ)
# ==========================================
def create_booking_logic(db: Session, booking_in: BookingCreate, current_user_id: int):
    """Logic tạo hoá đơn đặt vé (Đã bọc thép chống Race Condition)"""
    
    # 1. Chốt chặn thời gian: Suất chiếu còn tồn tại và chưa chiếu không?
    event = db.query(Event).filter(Event.id == booking_in.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Không tìm thấy suất chiếu!")
    current_time = datetime.now()
    event_start_time = _normalize_datetime(event.start_time)
    if event_start_time <= current_time:
        raise HTTPException(status_code=400, detail="Suất chiếu này đã bắt đầu hoặc kết thúc, không thể đặt vé!")

    # 2. Chống Race Condition: Khóa dòng dữ liệu ghế bằng with_for_update()
    seats = db.query(Seat).filter(
        Seat.id.in_(booking_in.seat_ids),
        Seat.event_id == booking_in.event_id
    ).with_for_update().all()

    # 3. Kiểm tra tính hợp lệ của mảng ghế
    if len(seats) != len(booking_in.seat_ids):
        raise HTTPException(status_code=400, detail="Một số ghế không hợp lệ hoặc sai suất chiếu!")

    for seat in seats:
        if seat.status != SeatStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail=f"Ghế {seat.seat_code} đã bị người khác đặt. Vui lòng chọn ghế khác!")

    # 4. Tạo Hóa đơn (Giữ chỗ 5 phút)
    total_price = event.price * len(seats)
    new_booking = Booking(
        user_id=current_user_id,
        event_id=booking_in.event_id,
        total_price=total_price,
        status=BookingStatus.PENDING,
        expire_at=datetime.now() + timedelta(minutes=5)
    )
    db.add(new_booking)
    db.flush() # Đẩy tạm xuống DB để lấy ID

    # 5. Tạo Vé chi tiết & Đổi trạng thái ghế
    tickets_to_create = []
    for seat in seats:
        seat.status = SeatStatus.HELD # Tạm giữ
        tickets_to_create.append(Ticket(booking_id=new_booking.id, seat_id=seat.id, price=event.price))

    db.add_all(tickets_to_create)
    db.commit()
    db.refresh(new_booking)

    return new_booking


# ==========================================
# 2. READ: LẤY DANH SÁCH VÀ CHI TIẾT
# ==========================================
def get_my_bookings(db: Session, current_user_id: int, skip: int = 0, limit: int = 100):
    """Lịch sử mua vé của User (Sắp xếp vé mới nhất lên đầu)"""
    return db.query(Booking).filter(Booking.user_id == current_user_id)\
             .order_by(desc(Booking.created_at))\
             .offset(skip).limit(limit).all()

def get_all_bookings_logic(db: Session, skip: int = 0, limit: int = 100):
    """Lấy toàn bộ hóa đơn cho admin, sắp xếp mới nhất lên đầu"""
    return db.query(Booking)\
             .order_by(desc(Booking.created_at))\
             .offset(skip).limit(limit).all()

def get_booking_detail(db: Session, booking_id: int, current_user_id: int):
    """Xem chi tiết 1 mã vé (Để hiển thị QR Code)"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn hàng!")
        
    # Chốt chặn bảo mật IDOR (Nghiêm cấm User A xem vé của User B)
    if booking.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem vé của người khác!")
        
    return booking


# ==========================================
# 3. UPDATE: XÁC NHẬN THANH TOÁN (PAYMENT CALLBACK)
# ==========================================
def confirm_payment_logic(db: Session, booking_id: int, current_user_id: int):
    """Logic cập nhật khi User thanh toán thành công (Ví dụ VNPay gọi về)"""
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current_user_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Đơn hàng không tồn tại!")

    # Chốt chặn nghiệp vụ: Chỉ thanh toán đơn PENDING
    if booking.status == BookingStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Đơn hàng này đã được thanh toán rồi!")
    
    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Đơn hàng đã bị hủy do quá hạn. Tiền của bạn sẽ được hoàn lại (Refund).")

    # Đổi trạng thái hóa đơn
    booking.status = BookingStatus.COMPLETED
    
    # Đổi trạng thái toàn bộ ghế từ HELD -> SOLD
    for ticket in booking.tickets:
        seat = db.query(Seat).filter(Seat.id == ticket.seat_id).first()
        if seat:
            seat.status = SeatStatus.SOLD
            
    db.commit()
    db.refresh(booking)
    return booking


# ==========================================
# 4. DELETE / CANCEL: USER TỰ HỦY HOẶC HỆ THỐNG HỦY
# ==========================================
def cancel_booking_logic(db: Session, booking_id: int, current_user_id: int):
    """User đổi ý, tự bấm nút Hủy đơn hàng đang chờ thanh toán"""
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current_user_id).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Đơn hàng không tồn tại!")

    # Chỉ cho phép hủy đơn PENDING (Chưa trả tiền)
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=400, detail="Chỉ có thể hủy đơn hàng đang chờ thanh toán!")

    booking.status = BookingStatus.CANCELLED
    
    # Trả ghế về lại AVAILABLE cho người khác mua
    for ticket in booking.tickets:
        seat = db.query(Seat).filter(Seat.id == ticket.seat_id).first()
        if seat:
            seat.status = SeatStatus.AVAILABLE
            
    db.commit()
    return {"message": "Hủy vé thành công!"}


# ==========================================
# 5. SYSTEM CHORES: DỌN RÁC (CRON JOB)
# ==========================================
def cleanup_expired_bookings_logic(db: Session):
    """
    Hệ thống tự động quét và hủy các vé PENDING quá 5 phút.
    Nên gọi hàm này trước khi load sơ đồ ghế ra cho Frontend.
    """
    now = datetime.now()
    expired_bookings = db.query(Booking).filter(
        Booking.status == BookingStatus.PENDING,
        Booking.expire_at <= now
    ).all()
    
    if not expired_bookings:
        return 0
        
    for booking in expired_bookings:
        booking.status = BookingStatus.CANCELLED
        for ticket in booking.tickets:
            seat = db.query(Seat).filter(Seat.id == ticket.seat_id).first()
            if seat and seat.status == SeatStatus.HELD:
                seat.status = SeatStatus.AVAILABLE 
                
    db.commit()
    return len(expired_bookings)
