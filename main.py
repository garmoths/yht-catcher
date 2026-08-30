import os
import sys
import time
from dotenv import load_dotenv
from tcdd_checker import TCDDTicketChecker
from config import Config
from whatsapp_notifier import WhatsAppNotifier
import logging
from datetime import datetime
from bot_state import BotState
from settings import normalize_classes, validate_settings
from terminal_ui import (
    configuration_issues,
    configure_interactively,
    configure_whatsapp,
    main_menu,
    show_help,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BANNER = r"""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║                    ^~^  ,                                        ║
║                   ('Y') )                                         ║
║                   /   \/                                         ║
║                  (\|||/)  TCDD BİLET BULUCU                        ║
║                   (o o)                                          ║
║                   ( = )                                          ║
║                   (" ")                                          ║
║                    ~W~                                           ║
║                                                                  ║
║              (\_/)                                               ║
║              (o.o)                                               ║
║              (> <)                                               ║
║              ( \ )                                               ║
║               'ww'                                               ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""


class YHTCatcher:
    def __init__(self, binis_istasyonu=None, inis_istasyonu=None,
                 tarih=None, saatler=None, headless=True, kontrol_sikligi=None,
                 sinif="EKONOMİ", minimum_koltuk=1, confirmation_checks=2,
                 error_threshold=3, state_path=None, sleep_fn=time.sleep):
        self.binis_istasyonu = binis_istasyonu
        self.inis_istasyonu = inis_istasyonu
        self.tarih = tarih
        self.saatler = saatler  # Liste: ["16:44", "18:24"]
        if not all((self.binis_istasyonu, self.inis_istasyonu, self.tarih)):
            raise ValueError("Biniş, iniş ve tarih ayarları boş bırakılamaz")
        if not self.saatler:
            raise ValueError("En az bir sefer saati tanımlanmalı")
        self.kontrol_sikligi = int(kontrol_sikligi or Config.KONTROL_SIKLIGI)
        self.classes = normalize_classes(sinif)
        self.sinif = ",".join(self.classes)
        self.minimum_koltuk = int(minimum_koltuk)
        self.confirmation_checks = max(1, int(confirmation_checks))
        self.error_threshold = max(1, int(error_threshold))
        validate_settings(
            self.binis_istasyonu, self.inis_istasyonu, self.tarih,
            self.saatler, self.kontrol_sikligi, self.classes, self.minimum_koltuk,
        )
        self.checker = TCDDTicketChecker(headless=headless)
        self.notifier = WhatsAppNotifier()
        self.notifier.setup()
        self.notification_cooldown = 3600  # 1 saat
        app_dir = os.path.dirname(os.path.abspath(__file__))
        self.state = BotState(state_path or os.path.join(app_dir, ".bot_state.json"))
        self.sleep = sleep_fn

    def _notification_key(self, saat):
        return "|".join((
            self.binis_istasyonu.casefold(), self.inis_istasyonu.casefold(),
            self.tarih, saat, self.sinif,
        ))

    def _check(self, saat):
        try:
            formatted_date = datetime.strptime(self.tarih, "%Y-%m-%d").strftime("%d.%m.%Y")
        except (TypeError, ValueError):
            formatted_date = self.tarih
        return self.checker.check_tickets(
            binis_istasyonu=self.binis_istasyonu,
            inis_istasyonu=self.inis_istasyonu,
            tarih=formatted_date,
            saat=saat,
            sinif=self.sinif,
            minimum_koltuk=self.minimum_koltuk,
            keep_driver=True,
        )

    def run_once(self, saat=None):
        """Tek seferlik bilet kontrolü yapar"""
        check_saat = saat or (self.saatler[0] if self.saatler else None)

        logger.info(f"Güzergah: {self.binis_istasyonu} -> {self.inis_istasyonu}, Tarih: {self.tarih}, Saat: {check_saat}")

        result = self._check(check_saat)

        if result.get("success") and result.get("found_seats"):
            notification_key = self._notification_key(check_saat)
            if not self.state.can_notify(notification_key, self.notification_cooldown):
                logger.info("Bu sefer için bildirim cooldown süresi dolmadı")
                self.state.record_success()
                return result
            for attempt in range(1, self.confirmation_checks):
                logger.info("Koltuk sonucu doğrulanıyor (%s/%s)...", attempt + 1, self.confirmation_checks)
                self.sleep(2)
                confirmation = self._check(check_saat)
                if not confirmation.get("success") or not confirmation.get("found_seats"):
                    logger.warning("Koltuk ikinci kontrolde doğrulanamadı; bildirim gönderilmiyor")
                    return {**confirmation, "confirmation_failed": True}
                result = confirmation

        if result.get('success'):
            if result.get('found_seats'):
                if self.state.can_notify(notification_key, self.notification_cooldown):
                    logger.info(f"BOŞ YER BULUNDU! WhatsApp bildirimi gönderiliyor...")
                    notification_result = {
                        **result,
                        "binis_istasyonu": self.binis_istasyonu,
                        "inis_istasyonu": self.inis_istasyonu,
                        "tarih": self.tarih,
                    }
                    sent = self.notifier.send_ticket_found_notification(notification_result)
                    if sent:
                        self.state.mark_notified(notification_key)
                    else:
                        logger.error("Bildirim gönderilemedi; cooldown başlatılmadı")
                else:
                    logger.info("Boş yer bulundu ama bildirim cooldown süresi dolmadı")
            else:
                logger.info(f"Boş yer yok: {result.get('message', 'Bilinmeyen mesaj')}")
        else:
            logger.error(f"Hata: {result.get('error', 'Bilinmeyen hata')}")
            streak = self.state.record_error()
            if streak >= self.error_threshold and not self.state.error_alerted:
                if self.notifier.send_error_notification(result.get('error', 'Bilinmeyen hata')):
                    self.state.mark_error_alerted()

        if result.get("success"):
            if self.state.record_success():
                self.notifier.send_recovery_notification()

        return result

    def run_continuous(self):
        """Sürekli bilet kontrolü yapar - tüm saatleri kontrol eder"""
        logger.info("="*60)
        logger.info("Sürekli Bilet Kontrolü Başlatılıyor")
        logger.info(f"Her {self.kontrol_sikligi} saniyede bir kontrol edilecek")
        logger.info(f"İstenen saatler: {', '.join(self.saatler)}")
        logger.info("="*60)

        current_interval = self.kontrol_sikligi
        try:
            while True:
                cycle_success = True
                found_any = False
                try:
                    for saat in self.saatler:
                        logger.info(f"--- Saat {saat} kontrol ediliyor ---")
                        result = self.run_once(saat=saat)
                        cycle_success = cycle_success and bool(result.get("success"))
                        found_any = found_any or bool(result.get("found_seats"))
                        self.sleep(2)

                    if not cycle_success:
                        current_interval = min(max(self.kontrol_sikligi, 900), current_interval * 2)
                    elif found_any:
                        current_interval = max(60, min(self.kontrol_sikligi, 60))
                    else:
                        current_interval = self.kontrol_sikligi
                    logger.info("Bir sonraki kontrol %s saniye sonra...", current_interval)
                    self.sleep(current_interval)

                except KeyboardInterrupt:
                    logger.info("Kullanıcı tarafından durduruldu.")
                    break
                except Exception as e:
                    logger.exception("Sürekli kontrolde beklenmeyen hata: %s", e)
                    current_interval = min(900, max(60, current_interval * 2))
                    self.sleep(current_interval)
        finally:
            self.checker.close_driver()


def interactive_setup():
    """Interaktif kurulum - kullanıcıdan bilgileri al"""
    print(BANNER)
    print()

    # .env'den varsayılan değerleri yükle
    load_dotenv()
    default_binis = os.getenv('BINIS_ISTASYONU', 'ERYAMAN YHT')
    default_inis = os.getenv('INIS_ISTASYONU', 'Konya (Selçuklu YHT)')
    default_tarih = os.getenv('TARIH', datetime.now().strftime("%Y-%m-%d"))
    default_saat = os.getenv('SAAT', '16:44 18:24')
    default_kontrol_sikligi = os.getenv('KONTROL_SIKLIGI', '180')

    print("┌─────────────────────────────────────────────────────────────┐")
    print("│                  🚂 YHT TREN BULUCU KURULUM                │")
    print("└─────────────────────────────────────────────────────────────┘")
    print()

    # Biniş istasyonu
    print(f"  1️⃣  Biniş istasyonu giriniz")
    print(f"      Örnek: ERYAMAN YHT, Ankara Gar, İstanbul(Söğütlüçeşme)")
    binis = input(f"      [{default_binis}]: ").strip()
    if not binis:
        binis = default_binis

    # İniş istasyonu
    print()
    print(f"  2️⃣  İniş istasyonu giriniz")
    print(f"      Örnek: Konya (Selçuklu YHT), Ankara Gar, Eskişehir")
    inis = input(f"      [{default_inis}]: ").strip()
    if not inis:
        inis = default_inis

    # Tarih
    print()
    print(f"  3️⃣  Seyahat tarihini giriniz (YYYY-AA-GG)")
    print(f"      Örnek: 2026-04-26")
    tarih = input(f"      [{default_tarih}]: ").strip()
    if not tarih:
        tarih = default_tarih

    # Saatler
    print()
    print(f"  4️⃣  Sefer saatlerini giriniz (boşluk ile ayırın)")
    print(f"      Örnek: 16:44 18:24 09:14")
    saatler_input = input(f"      [{default_saat}]: ").strip()
    if not saatler_input:
        saatler_input = default_saat
    saatler = saatler_input.split()

    try:
        datetime.strptime(tarih, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Tarih YYYY-AA-GG formatında ve geçerli olmalı") from exc
    for saat in saatler:
        try:
            datetime.strptime(saat, "%H:%M")
        except ValueError as exc:
            raise ValueError(f"Geçersiz saat: {saat} (SS:DD bekleniyor)") from exc

    # Çalışma dizinine değil, uygulamanın yanındaki .env dosyasına yaz.
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    with open(env_path, 'w', encoding="utf-8") as f:
        f.write(f"# TCDD Ayarları\n")
        f.write(f"BINIS_ISTASYONU={binis}\n")
        f.write(f"INIS_ISTASYONU={inis}\n")
        f.write(f"TARIH={tarih}\n")
        f.write(f"SAAT={saatler_input}\n")
        f.write(f"SAAT_KONTROL=true\n\n")
        f.write(f"# WhatsApp Twilio Ayarları\n")
        f.write(f"TWILIO_ACCOUNT_SID={os.getenv('TWILIO_ACCOUNT_SID', '')}\n")
        f.write(f"TWILIO_AUTH_TOKEN={os.getenv('TWILIO_AUTH_TOKEN', '')}\n")
        f.write(f"TWILIO_WHATSAPP_NUMBER={os.getenv('TWILIO_WHATSAPP_NUMBER', '')}\n")
        f.write(f"KULLANICI_WHATSAPP_NUMARASI={os.getenv('KULLANICI_WHATSAPP_NUMARASI', '')}\n\n")
        f.write(f"# Kontrol Sıklığı (saniye)\n")
        f.write(f"KONTROL_SIKLIGI={default_kontrol_sikligi}\n")

    # Özet
    print()
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│                    ✅ KURULUM TAMAMLANDI                    │")
    print("├─────────────────────────────────────────────────────────────┤")
    print(f"│  🚉 Biniş:  {binis:<45} │")
    print(f"│  🏁 İniş:   {inis:<45} │")
    print(f"│  📅 Tarih:  {tarih:<45} │")
    print(f"│  🕐 Saat:   {', '.join(saatler):<45} │")
    print("└─────────────────────────────────────────────────────────────┘")
    print()

    return binis, inis, tarih, saatler


def create_catcher_from_env():
    load_dotenv(override=True)
    return YHTCatcher(
        binis_istasyonu=os.getenv('BINIS_ISTASYONU'),
        inis_istasyonu=os.getenv('INIS_ISTASYONU'),
        tarih=os.getenv('TARIH'),
        saatler=os.getenv('SAAT', '').split(),
        headless=True,
        kontrol_sikligi=int(os.getenv('KONTROL_SIKLIGI', '180')),
        sinif=os.getenv('VAGON_SINIFLARI', os.getenv('VAGON_SINIFI', 'EKONOMİ')),
        minimum_koltuk=int(os.getenv('MINIMUM_KOLTUK', '1')),
        confirmation_checks=int(os.getenv('DOGRULAMA_SAYISI', '2')),
        error_threshold=int(os.getenv('HATA_BILDIRIM_ESIGI', '3')),
    )


def show_settings():
    load_dotenv(override=True)
    print("\nMevcut ayarlar")
    print("- Güzergâh:", os.getenv('BINIS_ISTASYONU'), "→", os.getenv('INIS_ISTASYONU'))
    print("- Tarih:", os.getenv('TARIH'))
    print("- Saatler:", os.getenv('SAAT'))
    print("- Bölümler:", os.getenv('VAGON_SINIFLARI', os.getenv('VAGON_SINIFI', 'EKONOMİ')))
    print("- Minimum koltuk:", os.getenv('MINIMUM_KOLTUK', '1'))
    print("- Kontrol aralığı:", os.getenv('KONTROL_SIKLIGI', '180'), "saniye")


def main():
    # Komut satırı argümanlarını kontrol et
    mode = "interactive"  # varsayılan: interaktif mod

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

    if mode == "test":
        print(BANNER)
        load_dotenv()
        notifier = WhatsAppNotifier()
        notifier.setup()
        logger.info("Test modu çalıştırılıyor...")
        notifier.send_test_notification()
        return

    if mode == "once":
        # .env'den ayarları oku, tek seferlik kontrol
        load_dotenv()
        binis = os.getenv('BINIS_ISTASYONU')
        inis = os.getenv('INIS_ISTASYONU')
        tarih = os.getenv('TARIH')
        saatler = os.getenv('SAAT', '').split()

        catcher = create_catcher_from_env()
        logger.info("Tek seferlik kontrol çalıştırılıyor...")
        for saat in saatler:
            catcher.run_once(saat=saat)
        return

    if mode == "daemon":
        # Sunucu modu - .env'den ayarları oku, arka planda sürekli çalış
        load_dotenv()
        binis = os.getenv('BINIS_ISTASYONU')
        inis = os.getenv('INIS_ISTASYONU')
        tarih = os.getenv('TARIH')
        saatler = os.getenv('SAAT', '').split()

        catcher = create_catcher_from_env()
        logger.info("Daemon modu başlatılıyor (sunucu)...")
        catcher.run_continuous()
        return

    print(BANNER)
    load_dotenv(override=True)
    issues = configuration_issues()
    if issues:
        print("⚠️  Kurulum tamamlanmamış:")
        for issue in issues:
            print("   -", issue)
        print("Menüden 'WhatsApp ayarları' ve 'Kurulum yardımı' seçeneklerini kullanın.")
    while True:
        choice = main_menu()
        if choice == "0":
            return
        if choice == "1":
            show_settings()
        elif choice == "2":
            configure_interactively()
            load_dotenv(override=True)
        elif choice == "3":
            load_dotenv(override=True)
            issues = configuration_issues()
            if issues:
                print("Bot başlatılamadı:", "; ".join(issues))
                print("Önce 6 numaralı WhatsApp ayarlarını tamamlayın.")
                continue
            show_settings()
            print("\nSürekli kontrol başlatılıyor... (Ctrl+C ile durdur)")
            create_catcher_from_env().run_continuous()
        elif choice == "4":
            catcher = create_catcher_from_env()
            try:
                for saat in catcher.saatler:
                    catcher.run_once(saat)
            finally:
                catcher.checker.close_driver()
        elif choice == "5":
            load_dotenv(override=True)
            issues = configuration_issues()
            if issues:
                print("WhatsApp testi yapılamadı:", "; ".join(issues))
                continue
            notifier = WhatsAppNotifier()
            notifier.setup()
            notifier.send_test_notification()
        elif choice == "6":
            try:
                configure_whatsapp()
                load_dotenv(override=True)
            except ValueError as exc:
                print("WhatsApp ayarı kaydedilemedi:", exc)
        elif choice == "7":
            show_help()


if __name__ == "__main__":
    main()
