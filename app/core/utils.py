import random

def generate_otp_code() -> str:
    """Tạo ngẫu nhiên mã OTP 6 chữ số"""
    return str(random.randint(100000, 999999))

