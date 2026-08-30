from twilio.rest import Client
import logging
from config import Config
import time
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("twilio.http_client").setLevel(logging.WARNING)


class WhatsAppNotifier:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", Config.TWILIO_ACCOUNT_SID)
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", Config.TWILIO_AUTH_TOKEN)
        self.from_number = os.getenv("TWILIO_WHATSAPP_NUMBER", Config.TWILIO_WHATSAPP_NUMBER)
        self.to_number = os.getenv("KULLANICI_WHATSAPP_NUMARASI", Config.KULLANICI_WHATSAPP_NUMARASI)
        self.client = None

    def setup(self):
        """Twilio client'ı kurar"""
        if not self.account_sid or not self.auth_token:
            logger.error("Twilio credentials ayarlanmamış!")
            return False

        try:
            self.client = Client(self.account_sid, self.auth_token)
            logger.info("Twilio client başarıyla kuruldu")
            return True
        except Exception as e:
            logger.error(f"Twilio client kurulum hatası: {e}")
            return False

    def send_notification(self, message, wait_for_delivery=True):
        """
        WhatsApp mesajı gönderir

        Args:
            message: Gönderilecek mesaj

        Returns:
            bool: Gönderim başarılı mı
        """
        if not self.client:
            if not self.setup():
                return False

        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=self.to_number
            )
            logger.info("WhatsApp mesajı Twilio tarafından kabul edildi. SID: %s", message_obj.sid)
            if not wait_for_delivery:
                return True
            terminal_statuses = {"delivered", "read", "failed", "undelivered"}
            for _ in range(6):
                message_obj = self.client.messages(message_obj.sid).fetch()
                if message_obj.status in terminal_statuses:
                    break
                time.sleep(1)
            if message_obj.status in {"failed", "undelivered"}:
                logger.error(
                    "WhatsApp teslim edilemedi: status=%s error_code=%s",
                    message_obj.status,
                    message_obj.error_code,
                )
                return False
            logger.info("WhatsApp teslim durumu: %s", message_obj.status)
            return message_obj.status in {"sent", "delivered", "read"}
        except Exception as e:
            logger.error(f"WhatsApp mesajı gönderilemedi: {e}")
            return False

    def send_ticket_found_notification(self, journey_info):
        """
        Bilet bulunduğunda bildirim gönderir

        Args:
            journey_info: Sefer bilgileri dict

        Returns:
            bool: Gönderim başarılı mı
        """
        binis = journey_info.get('binis_istasyonu', Config.BINIS_ISTASYONU)
        inis = journey_info.get('inis_istasyonu', Config.INIS_ISTASYONU)
        tarih = journey_info.get('tarih', Config.TARIH)
        message = f"🚂 YHT BILET BULUNDU!\n\n{binis}->{inis}\nTarih: {tarih}\n{journey_info.get('message', '')}\n\nHemen bilet al!"
        return self.send_notification(message)

    def send_error_notification(self, error_message):
        """
        Hata durumunda bildirim gönderir

        Args:
            error_message: Hata mesajı

        Returns:
            bool: Gönderim başarılı mı
        """
        message = f"⚠️ YHT KONTROL HATASI: {error_message[:100]}"
        return self.send_notification(message)

    def send_recovery_notification(self):
        return self.send_notification("✅ YHT botu yeniden sağlıklı çalışıyor.")

    def send_test_notification(self):
        """
        Test bildirimi gönderir

        Returns:
            bool: Gönderim başarılı mı
        """
        message = "YHT Takip Sistemi Test: Sistem calisiyor!"
        return self.send_notification(message)


if __name__ == "__main__":
    notifier = WhatsAppNotifier()
    notifier.setup()
    notifier.send_test_notification()
