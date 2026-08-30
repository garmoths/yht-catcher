import os
import getpass
import unicodedata
from datetime import datetime

from settings import ALLOWED_CLASSES, normalize_classes, update_env, validate_settings
from tcdd_checker import TCDDTicketChecker


def _ask(label, default):
    value = input(f"{label} [{default}]: ").strip()
    return value or str(default)


def _normalize(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def choose_station(label, current, stations):
    """Güncel listede arama yaptırıp istasyonu numarayla seçtirir."""
    while True:
        query = input(f"{label} için ara [{current}]: ").strip()
        if not query:
            return current
        normalized_query = _normalize(query)
        matches = [station for station in stations if normalized_query in _normalize(station)]
        if not matches:
            print("Eşleşme bulunamadı. İlçe, şehir veya istasyon adının bir bölümünü yazın.")
            continue
        shown = matches[:30]
        print()
        for index, station in enumerate(shown, 1):
            print(f"{index:>2}) {station}")
        if len(matches) > len(shown):
            print(f"... {len(matches) - len(shown)} sonuç daha var; aramayı daraltın.")
        selection = input("Numara seç (yeniden aramak için Enter): ").strip()
        if not selection:
            continue
        try:
            return shown[int(selection) - 1]
        except (ValueError, IndexError):
            print("Geçersiz numara.")


def load_current_stations():
    print("\nGüncel istasyon adları TCDD'den alınıyor; bu işlem birkaç saniye sürebilir...")
    try:
        stations = TCDDTicketChecker(headless=True).get_stations()
        print(f"{len(stations)} istasyon yüklendi.")
        return stations
    except Exception as exc:
        print(f"İstasyon listesi alınamadı: {exc}")
        print("İstasyon adlarını elle girebilirsiniz.")
        return None


def choose_classes(current):
    current_classes = normalize_classes(current)
    print("\nTakip edilecek bölümler:")
    print("1) Ekonomi")
    print("2) Business")
    print("3) Loca")
    print("Tekerlekli sandalye kontenjanı takip edilmez.")
    default_text = ", ".join(current_classes)
    while True:
        selection = input(f"Seçim (örn. 1, 1 2, 2 3 veya hepsi) [{default_text}]: ").strip()
        if not selection:
            return current_classes
        if selection.casefold() in {"hepsi", "tümü", "tumu"}:
            return list(ALLOWED_CLASSES)
        try:
            selected = []
            for number in selection.replace(",", " ").split():
                class_name = ALLOWED_CLASSES[int(number) - 1]
                if class_name not in selected:
                    selected.append(class_name)
            if selected:
                return selected
        except (ValueError, IndexError):
            pass
        print("Geçersiz seçim. 1, 2 ve 3 numaralarını kullanın.")


def choose_times(times, current):
    print("\nBu gün için bulunan seferler:")
    for index, departure_time in enumerate(times, 1):
        print(f"{index:>2}) {departure_time}")
    default_text = " ".join(current)
    while True:
        selection = input(f"Seçim (örn. 1, 1 3 veya hepsi) [{default_text}]: ").strip()
        if not selection:
            existing = [value for value in current if value in times]
            return existing or [times[0]]
        if selection.casefold() in {"hepsi", "tümü", "tumu"}:
            return list(times)
        try:
            selected = []
            for number in selection.replace(",", " ").split():
                value = times[int(number) - 1]
                if value not in selected:
                    selected.append(value)
            if selected:
                return selected
        except (ValueError, IndexError):
            pass
        print("Geçersiz seçim; listedeki numaraları kullanın.")


def load_journey_times(binis, inis, tarih):
    print("\nSeçilen günün seferleri TCDD'den alınıyor...")
    try:
        formatted_date = datetime.strptime(tarih, "%Y-%m-%d").strftime("%d.%m.%Y")
        result = TCDDTicketChecker(headless=True).check_tickets(
            binis, inis, formatted_date, saat=None
        )
        if result.get("success"):
            return result["times"]
        print("Seferler alınamadı:", result.get("error", "Bilinmeyen hata"))
    except Exception as exc:
        print("Seferler alınamadı:", exc)
    return None


def configure_interactively():
    """Kullanıcıyı dosya düzenletmeden güvenli biçimde yapılandırır."""
    print("\nYHT BOT AYARLARI")
    print("Enter'a basarsan mevcut değer korunur.\n")
    current_binis = os.getenv("BINIS_ISTASYONU", "Ankara Gar")
    current_inis = os.getenv("INIS_ISTASYONU", "SELÇUKLU YHT (KONYA)")
    stations = load_current_stations()
    if stations:
        binis = choose_station("1) Biniş istasyonu", current_binis, stations)
        inis = choose_station("2) İniş istasyonu", current_inis, stations)
    else:
        binis = _ask("1) Biniş istasyonu", current_binis)
        inis = _ask("2) İniş istasyonu", current_inis)
    tarih = _ask("3) Tarih (YYYY-AA-GG)", os.getenv("TARIH", datetime.now().strftime("%Y-%m-%d")))
    current_times = os.getenv("SAAT", "15:10").split()
    available_times = load_journey_times(binis, inis, tarih)
    if available_times:
        saatler = choose_times(available_times, current_times)
        saat_text = " ".join(saatler)
    else:
        saat_text = _ask("4) Saatler (boşlukla ayır)", " ".join(current_times))
        saatler = saat_text.split()
    aralik = _ask("5) Kontrol aralığı (saniye)", os.getenv("KONTROL_SIKLIGI", "180"))
    current_classes = os.getenv("VAGON_SINIFLARI", os.getenv("VAGON_SINIFI", "EKONOMİ"))
    classes = choose_classes(current_classes)
    minimum = _ask("7) Minimum boş koltuk", os.getenv("MINIMUM_KOLTUK", "1"))
    validate_settings(binis, inis, tarih, saatler, aralik, classes, minimum)
    update_env({
        "BINIS_ISTASYONU": binis,
        "INIS_ISTASYONU": inis,
        "TARIH": tarih,
        "SAAT": " ".join(saatler),
        "KONTROL_SIKLIGI": str(int(aralik)),
        "VAGON_SINIFLARI": ",".join(classes),
        "MINIMUM_KOLTUK": str(int(minimum)),
    })
    print("\nAyarlar kaydedildi.")
    return {"binis": binis, "inis": inis, "tarih": tarih, "saatler": saatler}


def is_placeholder(value):
    normalized = (value or "").strip().casefold()
    return not normalized or normalized.startswith("your_") or "xxxx" in normalized


def configuration_issues():
    issues = []
    required = {
        "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN"),
        "TWILIO_WHATSAPP_NUMBER": os.getenv("TWILIO_WHATSAPP_NUMBER"),
        "KULLANICI_WHATSAPP_NUMARASI": os.getenv("KULLANICI_WHATSAPP_NUMARASI"),
    }
    for key, value in required.items():
        if is_placeholder(value):
            issues.append(f"{key} eksik")
    if required["TWILIO_ACCOUNT_SID"] and not required["TWILIO_ACCOUNT_SID"].startswith("AC"):
        issues.append("TWILIO_ACCOUNT_SID biçimi hatalı")
    for key in ("TWILIO_WHATSAPP_NUMBER", "KULLANICI_WHATSAPP_NUMARASI"):
        value = required[key] or ""
        if not is_placeholder(value) and not value.startswith("whatsapp:+"):
            issues.append(f"{key} whatsapp:+90... biçiminde olmalı")
    return issues


def configure_whatsapp():
    print("\nTWILIO WHATSAPP AYARLARI")
    print("Bilgiler Twilio Console > Account Info ve WhatsApp Sandbox sayfasında bulunur.")
    print("Auth Token ekranda gösterilmez ve yazarken terminalde görünmez.\n")
    sid = _ask("Account SID", os.getenv("TWILIO_ACCOUNT_SID", ""))
    current_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    token = getpass.getpass("Auth Token [mevcut değeri korumak için Enter]: ").strip() or current_token
    sender = _ask("Sandbox gönderen numarası", os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"))
    recipient = _ask("Alıcı numarası", os.getenv("KULLANICI_WHATSAPP_NUMARASI", "whatsapp:+90"))
    if recipient.startswith("0"):
        recipient = "whatsapp:+90" + recipient[1:]
    elif recipient.startswith("+"):
        recipient = "whatsapp:" + recipient
    if not sid.startswith("AC") or is_placeholder(token):
        raise ValueError("Geçerli Account SID ve Auth Token gerekli")
    if not sender.startswith("whatsapp:+") or not recipient.startswith("whatsapp:+"):
        raise ValueError("WhatsApp numaraları whatsapp:+90... biçiminde olmalı")
    update_env({
        "TWILIO_ACCOUNT_SID": sid,
        "TWILIO_AUTH_TOKEN": token,
        "TWILIO_WHATSAPP_NUMBER": sender,
        "KULLANICI_WHATSAPP_NUMARASI": recipient,
    })
    print("WhatsApp ayarları kaydedildi. Menüden test mesajı gönderebilirsiniz.")


def show_help():
    print("""
HIZLI BAŞLANGIÇ
1. 'Ayarları değiştir' ile istasyon, tarih ve saati seçin.
2. 'WhatsApp ayarları' ile Twilio Sandbox bilgilerini girin.
3. WhatsApp'tan Sandbox sayfasındaki 'join <kod>' mesajını gönderin.
4. 'WhatsApp testi' ile teslimatı doğrulayın.
5. 'Botu başlat' seçeneğini kullanın; durdurmak için Ctrl+C.

Not: Sandbox üyeliği yaklaşık 3 gün sonra bitebilir. 63015 hatasında güncel
join kodunu aynı alıcı WhatsApp numarasından yeniden gönderin.
""")


def main_menu():
    while True:
        print("\n1) Ayarları göster")
        print("2) Ayarları değiştir")
        print("3) Botu başlat")
        print("4) Tek kontrol yap")
        print("5) WhatsApp testi gönder")
        print("6) WhatsApp ayarları")
        print("7) Kurulum yardımı")
        print("0) Çıkış")
        choice = input("Seçimin: ").strip()
        if choice in {"0", "1", "2", "3", "4", "5", "6", "7"}:
            return choice
        print("Geçersiz seçim.")
