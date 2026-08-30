import os
from dotenv import load_dotenv

load_dotenv()


def _positive_int(name, default):
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} tam sayı olmalı: {raw_value!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} sıfırdan büyük olmalı")
    return value

class Config:
    # TCDD Ayarları
    BINIS_ISTASYONU = os.getenv('BINIS_ISTASYONU', 'ERYAMAN YHT')
    INIS_ISTASYONU = os.getenv('INIS_ISTASYONU', 'Konya (Selçuklu YHT)')
    TARIH = os.getenv('TARIH', '2026-04-26')
    SAAT = os.getenv('SAAT', '16:44 18:24')
    SAAT_KONTROL = os.getenv('SAAT_KONTROL', 'true').lower() == 'true'

    # WhatsApp Twilio Ayarları
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
    TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
    KULLANICI_WHATSAPP_NUMARASI = os.getenv('KULLANICI_WHATSAPP_NUMARASI')

    # Kontrol Sıklığı
    KONTROL_SIKLIGI = _positive_int('KONTROL_SIKLIGI', 180)
