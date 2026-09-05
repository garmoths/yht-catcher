import os
import getpass
import logging
import unicodedata
from datetime import datetime

from settings import ALLOWED_CLASSES, normalize_classes, update_env, validate_settings
from tcdd_checker import TCDDTicketChecker

# Terminal Renkleri ve Biçimlendirme
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RED = "\033[31m"
BRIGHT_WHITE = "\033[97m"


def divider(char="─", length=56):
    print(f"{DIM}{char * length}{RESET}")


def _ask(label, default):
    prompt_text = f"{label} {DIM}[{default}]{RESET}: "
    value = input(prompt_text).strip()
    return value or str(default)


def _normalize(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def choose_station(label, current, stations):
    """Güncel listede arama yaptırıp istasyonu numarayla seçtirir."""
    while True:
        prompt_text = f"{label} için ara {DIM}[{current}]{RESET}: "
        query = input(prompt_text).strip()
        if not query:
            return current
        normalized_query = _normalize(query)
        matches = [station for station in stations if normalized_query in _normalize(station)]
        if not matches:
            print(f"{YELLOW}⚠️  Eşleşme bulunamadı. Şehir veya istasyon adının bir kısmını yazın.{RESET}")
            continue
        shown = matches[:30]
        print()
        for index, station in enumerate(shown, 1):
            print(f"  {CYAN}{index:>2}){RESET} {station}")
        if len(matches) > len(shown):
            print(f"{DIM}  ... {len(matches) - len(shown)} sonuç daha var; aramayı daraltabilirsiniz.{RESET}")
        print()
        selection = input(f"{BOLD}Numara seç{RESET} {DIM}(yeniden aramak için Enter){RESET}: ").strip()
        if not selection:
            continue
        try:
            return shown[int(selection) - 1]
        except (ValueError, IndexError):
            print(f"{RED}Geçersiz numara! Listedeki numaralardan birini girin.{RESET}")


def load_current_stations():
    print(f"\n{YELLOW}⏳ Güncel istasyon listesi TCDD'den alınıyor... (birkaç saniye sürebilir){RESET}")
    prev_level = logging.getLogger("tcdd_checker").level
    logging.getLogger("tcdd_checker").setLevel(logging.WARNING)
    try:
        stations = TCDDTicketChecker(headless=True).get_stations()
        print(f"{GREEN}✓ {len(stations)} istasyon başarıyla yüklendi.{RESET}")
        return stations
    except Exception as exc:
        print(f"{RED}✗ İstasyon listesi otomatik alınamadı: {exc}{RESET}")
        print(f"{DIM}İstasyon adını elle girebilirsiniz.{RESET}")
        return None
    finally:
        logging.getLogger("tcdd_checker").setLevel(prev_level)


def choose_classes(current):
    current_classes = normalize_classes(current)
    print(f"\n{BOLD}Takip Edilecek Vagon Bölümleri:{RESET}")
    print(f"  {CYAN}1){RESET} Ekonomi")
    print(f"  {CYAN}2){RESET} Business")
    print(f"  {CYAN}3){RESET} Loca")
    print(f"{DIM}  * Tekerlekli sandalye kontenjanı hesaba katılmaz.{RESET}")
    default_text = ", ".join(current_classes)
    while True:
        prompt_text = f"\nSeçim {DIM}(örn. 1, 1 2, 2 3 veya hepsi){RESET} [{default_text}]: "
        selection = input(prompt_text).strip()
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
        print(f"{RED}Geçersiz seçim! Lütfen 1, 2, 3 veya 'hepsi' yazın.{RESET}")


def choose_times(times, current):
    print(f"\n{BOLD}Bu gün için bulunan YHT seferleri:{RESET}")
    for index, departure_time in enumerate(times, 1):
        print(f"  {GREEN}{index:>2}){RESET} {BOLD}{departure_time}{RESET}")
    default_text = " ".join(current)
    while True:
        prompt_text = f"\nSeçim {DIM}(örn. 1, 1 3 veya hepsi){RESET} [{default_text}]: "
        selection = input(prompt_text).strip()
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
        print(f"{RED}Geçersiz seçim! Listedeki sefer numaralarını girin.{RESET}")


def load_journey_times(binis, inis, tarih):
    print(f"\n{YELLOW}⏳ {tarih} tarihindeki sefer saatleri TCDD'den alınıyor...{RESET}")
    prev_level = logging.getLogger("tcdd_checker").level
    logging.getLogger("tcdd_checker").setLevel(logging.WARNING)
    try:
        formatted_date = datetime.strptime(tarih, "%Y-%m-%d").strftime("%d.%m.%Y")
        result = TCDDTicketChecker(headless=True).check_tickets(
            binis, inis, formatted_date, saat=None
        )
        if result.get("success"):
            return result["times"]
        print(f"{RED}✗ Seferler alınamadı: {result.get('error', 'Bilinmeyen hata')}{RESET}")
    except Exception as exc:
        print(f"{RED}✗ Seferler alınamadı: {exc}{RESET}")
    finally:
        logging.getLogger("tcdd_checker").setLevel(prev_level)
    return None


def configure_interactively():
    """Kullanıcıyı tek, anlaşılır ve ferah bir takip ayarı akışında yönlendirir."""
    print(f"\n{BOLD}{CYAN}══════════════════ 🛠️  TAKİP AYARLARI ══════════════════{RESET}")
    print(f"{DIM}İstasyon adını yazıp listeden numarayla seçebilirsiniz.{RESET}")
    print(f"{DIM}Enter'a basarsanız köşeli parantez içindeki mevcut değer korunur.{RESET}\n")

    current_binis = os.getenv("BINIS_ISTASYONU", "Ankara Gar")
    current_inis = os.getenv("INIS_ISTASYONU", "SELÇUKLU YHT (KONYA)")
    stations = load_current_stations()

    divider()
    if stations:
        binis = choose_station(f"{CYAN}{BOLD}1/6{RESET} {BOLD}Nereden bineceksin?{RESET}", current_binis, stations)
    else:
        binis = _ask(f"{CYAN}{BOLD}1/6{RESET} {BOLD}Nereden bineceksin?{RESET}", current_binis)

    divider()
    if stations:
        inis = choose_station(f"{CYAN}{BOLD}2/6{RESET} {BOLD}Nereye gideceksin?{RESET}", current_inis, stations)
    else:
        inis = _ask(f"{CYAN}{BOLD}2/6{RESET} {BOLD}Nereye gideceksin?{RESET}", current_inis)

    divider()
    tarih = _ask(f"{CYAN}{BOLD}3/6{RESET} {BOLD}Yolculuk tarihi (YYYY-AA-GG){RESET}", os.getenv("TARIH", datetime.now().strftime("%Y-%m-%d")))

    divider()
    current_times = os.getenv("SAAT", "15:10").split()
    available_times = load_journey_times(binis, inis, tarih)
    if available_times:
        saatler = choose_times(available_times, current_times)
        saat_text = " ".join(saatler)
    else:
        saat_text = _ask(f"{CYAN}{BOLD}4/6{RESET} {BOLD}Takip edilecek saatler (boşlukla ayır){RESET}", " ".join(current_times))
        saatler = saat_text.split()

    divider()
    aralik = _ask(f"{CYAN}{BOLD}5/6{RESET} {BOLD}Kaç saniyede bir kontrol edilsin?{RESET}", os.getenv("KONTROL_SIKLIGI", "180"))

    divider()
    current_classes = os.getenv("VAGON_SINIFLARI", os.getenv("VAGON_SINIFI", "EKONOMİ"))
    print(f"{CYAN}{BOLD}6/6{RESET} {BOLD}Vagon bölümlerini ve koltuk sayısını belirle:{RESET}")
    classes = choose_classes(current_classes)
    minimum = _ask(f"\n{BOLD}En az kaç boş koltuk olsun?{RESET}", os.getenv("MINIMUM_KOLTUK", "1"))

    validate_settings(binis, inis, tarih, saatler, aralik, classes, minimum)
    update_env({
        "BINIS_ISTASYONU": binis, "INIS_ISTASYONU": inis, "TARIH": tarih,
        "SAAT": saat_text, "KONTROL_SIKLIGI": str(int(aralik)),
        "VAGON_SINIFLARI": ",".join(classes), "MINIMUM_KOLTUK": str(int(minimum)),
    })

    divider("═")
    print(f"{GREEN}{BOLD}✓ Takip ayarları başarıyla kaydedildi!{RESET}")
    print(f"  📍 {BOLD}Güzergâh :{RESET} {binis} → {inis}")
    print(f"  📅 {BOLD}Tarih    :{RESET} {tarih}")
    print(f"  🕐 {BOLD}Saatler  :{RESET} {', '.join(saatler)}")
    print(f"  💺 {BOLD}Bölümler :{RESET} {', '.join(classes)} (Min {minimum} koltuk)")
    print(f"  ⏱️  {BOLD}Aralık   :{RESET} {aralik} sn")
    divider("═")
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
    print(f"\n{BOLD}{MAGENTA}════════════════ 📱 TWILIO WHATSAPP AYARLARI ════════════════{RESET}")
    print(f"{DIM}Bilgiler Twilio Console > Account Info ve WhatsApp Sandbox sayfasında bulunur.{RESET}")
    print(f"{DIM}Auth Token ekranda gösterilmez ve yazarken terminalde görünmez.{RESET}\n")

    divider()
    sid = _ask(f"{MAGENTA}{BOLD}1/4{RESET} {BOLD}Twilio Account SID{RESET}", os.getenv("TWILIO_ACCOUNT_SID", ""))
    current_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    token = getpass.getpass(f"{MAGENTA}{BOLD}2/4{RESET} {BOLD}Twilio Auth Token{RESET} {DIM}[mevcutu korumak için Enter]{RESET}: ").strip() or current_token
    divider()
    sender = _ask(f"{MAGENTA}{BOLD}3/4{RESET} {BOLD}Twilio WhatsApp Numarası (Sandbox){RESET}", os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886"))
    divider()
    recipient = _ask(f"{MAGENTA}{BOLD}4/4{RESET} {BOLD}Bildirim Alacak Telefon Numarası{RESET}", os.getenv("KULLANICI_WHATSAPP_NUMARASI", "whatsapp:+90"))

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
    divider("═")
    print(f"{GREEN}{BOLD}✓ WhatsApp bildirim ayarları başarıyla kaydedildi!{RESET}")
    print(f"  Ana menüden 4'ü (Test et) seçerek test mesajı gönderebilirsiniz.")
    divider("═")


def show_help():
    print(f"\n{BOLD}{BLUE}════════════════════ ❓ YARDIM VE BİLGİ ════════════════════{RESET}")
    print(f"""
  {BOLD}1. Takip Ayarları:{RESET}
     Biniş, iniş istasyonunu, tarih ve takip etmek istediğin sefer saatlerini seç.

  {BOLD}2. Bildirim Ayarları:{RESET}
     Twilio WhatsApp bilgilerini gir (bir kerelik kurulum).

  {BOLD}3. Test Et:{RESET}
     WhatsApp test mesajı veya tek seferlik kontrol ile doğrula.

  {BOLD}4. Takibi Başlat:{RESET}
     Sürekli kontrol botunu çalıştır. Durdurmak için {BOLD}Ctrl+C{RESET} yapabilirsin.
""")
    divider("═")


def choose_test_mode():
    while True:
        divider()
        print(f"{BOLD}{YELLOW}🧪  TEST SEÇENEKLERİ{RESET}")
        divider()
        print(f"  {YELLOW}{BOLD}1){RESET} ✉️  WhatsApp bildirim testi {DIM}(Mesaj iletimini test eder){RESET}")
        print(f"  {BLUE}{BOLD}2){RESET} 🔍 Tek seferlik kontrol testi {DIM}(Bilet durumunu 1 kez tarar){RESET}")
        print(f"  {DIM}{BOLD}0){RESET} ↩️  Ana menüye dön")
        divider()
        choice = input(f"{BOLD}Test seçimin (1 veya 2):{RESET} ").strip()
        if choice in {"0", "1", "2"}:
            return choice
        print(f"{RED}Geçersiz seçim! Lütfen 1, 2 veya 0 girin.{RESET}")


def main_menu():
    while True:
        divider()
        print(f"{BOLD}{CYAN}📌  NE YAPMAK İSTİYORSUN?{RESET}")
        divider()
        print(f"  {CYAN}{BOLD}1){RESET} 🛠️  Takip ayarları {DIM}(Kur / Değiştir){RESET}")
        print(f"  {MAGENTA}{BOLD}2){RESET} 📱 Bildirim ayarları {DIM}(WhatsApp){RESET}")
        print(f"  {GREEN}{BOLD}3){RESET} ▶️  Takibi başlat {DIM}(Sürekli kontrol){RESET}")
        print(f"  {YELLOW}{BOLD}4){RESET} 🧪 Test et {DIM}(WhatsApp veya tek kontrol){RESET}")
        print(f"  {CYAN}{BOLD}5){RESET} 📋 Mevcut ayarları göster")
        print(f"  {BLUE}{BOLD}6){RESET} ❓ Yardım")
        print(f"  {RED}{BOLD}0){RESET} 🚪 Çıkış")
        divider()
        choice = input(f"{BOLD}Seçimin:{RESET} ").strip()
        if choice in {"0", "1", "2", "3", "4", "5", "6"}:
            return choice
        print(f"{RED}Geçersiz seçim! Lütfen menüdeki rakamlardan birini girin.{RESET}")
