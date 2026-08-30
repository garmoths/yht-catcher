import time
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import logging
import re
import json
from settings import normalize_classes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TCDDTicketChecker:
    def __init__(self, headless=True, debug_file=None):
        self.headless = headless
        self.driver = None
        self.base_url = "https://ebilet.tcddtasimacilik.gov.tr/"
        self.debug_file = debug_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "debug_page.html"
        )

    def setup_driver(self):
        """Chrome driver'ı kurar"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-dev-tools')
        chrome_options.add_argument('--remote-debugging-port=0')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        # Linux sunucuların yanında macOS ve Chromium kurulumlarını da destekle.
        chrome_candidates = (
            os.getenv("CHROME_BINARY"),
            shutil.which("google-chrome"),
            shutil.which("google-chrome-stable"),
            shutil.which("chromium"),
            shutil.which("chromium-browser"),
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )
        for candidate in chrome_candidates:
            if candidate and os.path.exists(candidate):
                chrome_options.binary_location = candidate
                break

        # Önce Selenium Manager'ı kullan; yalnızca gerekirse webdriver-manager'a dön.
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except Exception as selenium_error:
            logger.warning("Selenium Manager sürücüyü başlatamadı: %s", selenium_error)
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def close_driver(self):
        """Driver'ı kapatır"""
        if self.driver:
            try:
                self.driver.quit()
            finally:
                self.driver = None

    def _select_station(self, input_id, station_name):
        """İstasyon alanını doldurup görünür ve en yakın eşleşmeyi seçer."""
        station_input = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.ID, input_id))
        )
        station_input.click()
        station_input.send_keys(Keys.CONTROL, "a")
        station_input.send_keys(station_name)

        normalized = station_name.casefold().strip()
        search_tokens = [token for token in re.findall(r"\w+", normalized) if len(token) > 2]

        def matches_station(element):
            if not element.is_displayed():
                return False
            candidate_text = (element.text or element.get_attribute("textContent") or "").casefold()
            return bool(candidate_text.strip()) and all(token in candidate_text for token in search_tokens)

        WebDriverWait(self.driver, 10).until(
            lambda driver: any(
                matches_station(element)
                for element in driver.find_elements(
                    By.CSS_SELECTOR, "button.dropdown-item.station, [role='option'], li"
                )
            )
        )
        candidates = self.driver.find_elements(
            By.CSS_SELECTOR, "button.dropdown-item.station, [role='option'], li"
        )
        matches = [
            element for element in candidates if matches_station(element)
        ]
        if not matches:
            raise RuntimeError(f"İstasyon seçeneği bulunamadı: {station_name}")
        exact = next((item for item in matches if normalized in item.text.casefold()), matches[0])
        selected_text = " ".join(exact.text.split())
        self.driver.execute_script("arguments[0].click();", exact)
        logger.info("İstasyon seçildi: %s", selected_text)

    def get_stations(self):
        """TCDD arayüzündeki güncel istasyon adlarını döndürür."""
        try:
            if self.driver is None:
                self.setup_driver()
            self.driver.get(self.base_url)
            WebDriverWait(self.driver, 15).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            station_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "fromTrainInput"))
            )
            self.driver.execute_script("arguments[0].click();", station_input)
            WebDriverWait(self.driver, 10).until(
                lambda driver: driver.find_elements(By.CSS_SELECTOR, "button.dropdown-item.station")
            )
            names = []
            seen = set()
            for button in self.driver.find_elements(By.CSS_SELECTOR, "button.dropdown-item.station"):
                labels = button.find_elements(By.CSS_SELECTOR, ".textLocation")
                name = (labels[0].text if labels else button.text).strip()
                name = " ".join(name.split())
                key = name.casefold()
                if name and key not in seen:
                    seen.add(key)
                    names.append(name)
            if not names:
                raise RuntimeError("TCDD istasyon listesi boş döndü")
            return sorted(names, key=str.casefold)
        finally:
            self.close_driver()

    def check_tickets(self, binis_istasyonu, inis_istasyonu, tarih, saat=None,
                      sinif="EKONOMİ", minimum_koltuk=1, keep_driver=False):
        """
        TCDD web sitesi ile bilet sorgulaması yapar

        Args:
            binis_istasyonu: Binış istasyonu adı
            inis_istasyonu: İniş istasyonu adı
            tarih: Tarih (DD.MM.YYYY formatında)
            saat: İsteğe bağlı saat filtresi

        Returns:
            dict: Boş yer bilgileri
        """
        failed = False
        try:
            if self.driver is None:
                self.setup_driver()
            logger.info(f"TCDD bilet kontrolü başlatılıyor: {binis_istasyonu} -> {inis_istasyonu}, {tarih}")

            self.driver.get(self.base_url)
            time.sleep(3)

            # JavaScript'in yüklenmesini bekle
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(1)

            # Tüm popup'ları ve reklamları kapat
            try:
                # Cookie kabul
                cookie_accept = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                )
                cookie_accept.click()
                logger.info("Cookie kabul edildi")
            except Exception:
                logger.info("Cookie popup bulunamadı")

            # Sağ üstteki çarpı reklamını kapat - ekran kenarına tıkla
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                # Ekranın sağına tıkla
                actions.move_by_offset(500, 0).click().perform()
                logger.info("Ekran kenarına tıklandı")
                time.sleep(1)
            except Exception:
                try:
                    # Ekranın soluna tıkla
                    actions = ActionChains(self.driver)
                    actions.move_by_offset(-500, 0).click().perform()
                    logger.info("Ekran sol kenarına tıklandı")
                    time.sleep(1)
                except Exception:
                    pass

            time.sleep(1)

            self._select_station("fromTrainInput", binis_istasyonu)
            self._select_station("toTrainInput", inis_istasyonu)

            time.sleep(1)

            # Güncel sayfada tarih input'u placeholder taşımıyor.
            tarih_input = None
            date_selectors = (".departureDate input", ".datePickerInput.departureDate input")
            for selector in date_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    tarih_input = elements[0]
                    logger.info("Tarih input bulundu: %s", selector)
                    break

            if not tarih_input:
                logger.error("Tarih input'u bulunamadı")
                return {"success": False, "error": "Tarih input bulunamadı"}

            try:
                target_date = time.strptime(tarih, "%d.%m.%Y")
                target_iso = time.strftime("%Y-%m-%d", target_date)
            except ValueError as exc:
                return {"success": False, "error": f"Geçersiz tarih: {tarih}"}
            logger.info("Seçilecek takvim tarihi: %s", target_iso)

            # JavaScript ile tıkla ve takvimi aç
            try:
                self.driver.execute_script("arguments[0].click();", tarih_input)
                time.sleep(1)
                logger.info("Tarih takvimi açıldı")

                # data-date tam tarihi içerir; aynı gün numarasının başka aydan
                # yanlışlıkla seçilmesini önler. Gerekirse takvimi ileri taşı.
                selected = False
                for _ in range(13):
                    days = self.driver.find_elements(By.CSS_SELECTOR, f'td[data-date="{target_iso}"]')
                    available = [day for day in days if day.is_displayed() and "disabled" not in (day.get_attribute("class") or "")]
                    if available:
                        self.driver.execute_script("arguments[0].click();", available[-1])
                        logger.info("Tarih seçildi: %s", target_iso)
                        selected = True
                        break
                    next_buttons = self.driver.find_elements(By.CSS_SELECTOR, "th.next.available")
                    visible_next = [button for button in next_buttons if button.is_displayed()]
                    if not visible_next:
                        break
                    visible_next[-1].click()
                    time.sleep(0.3)
                if not selected:
                    return {"success": False, "error": f"Tarih seçilemiyor veya satışta değil: {tarih}"}
            except Exception as exc:
                return {"success": False, "error": f"Tarih takvimi açılamadı: {exc}"}

            time.sleep(1)

            # "Bilet Ara" butonunu bul
            search_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.btnSearch")
            ara_button = search_buttons[0] if search_buttons else None
            if ara_button is None:
                ara_button = next(
                    (
                        button for button in self.driver.find_elements(By.TAG_NAME, "button")
                        if "sefer ara" in (button.text or "").casefold()
                    ),
                    None,
                )

            if not ara_button:
                logger.error("Bilet ara butonu bulunamadı")
                return {"success": False, "error": "Bilet ara butonu bulunamadı"}

            # Butona tıkla
            self.driver.execute_script("arguments[0].click();", ara_button)
            logger.info("Bilet ara butonuna tıklandı")

            # Sonuçların yüklenmesini bekle
            time.sleep(5)

            if saat is None:
                departure_times = []
                for element in self.driver.find_elements(By.CSS_SELECTOR, 'time[datetime]'):
                    value = (element.get_attribute("datetime") or "").strip()
                    title = (element.get_attribute("title") or "").casefold()
                    if re.fullmatch(r"\d{2}:\d{2}", value) and "gidiş" in title:
                        if value not in departure_times:
                            departure_times.append(value)
                departure_times.sort()
                if not departure_times:
                    return {"success": False, "error": "Bu tarih için sefer saati bulunamadı"}
                logger.info("%s sefer saati bulundu", len(departure_times))
                return {"success": True, "times": departure_times}

            # Seferin üzerine tıklayıp koltuk bilgilerini al - JS ile datetime attribute kullan
            try:
                clicked = self.driver.execute_script("""
                    var saat = arguments[0];
                    var timeEls = document.querySelectorAll('time[datetime]');
                    for (var i = 0; i < timeEls.length; i++) {
                        if (timeEls[i].getAttribute('datetime') === saat) {
                            timeEls[i].click();
                            return true;
                        }
                    }
                    return false;
                """, saat)
                if clicked:
                    logger.info(f"İstenen sefer JS ile tıklandı: {saat}")
                    time.sleep(2)
                else:
                    logger.warning(f"Sefer elementi bulunamadı: {saat}")
                    return {"success": False, "error": f"İstenen sefer bulunamadı: {saat}"}
            except Exception as e:
                logger.warning(f"Sefer tıklanamadı: {e}")

            # Sonuçları analiz et
            return self.analyze_results(saat, sinif=sinif, minimum_koltuk=minimum_koltuk)

        except Exception as e:
            failed = True
            logger.exception("Bilet kontrolünde hata")
            detail = str(e).strip() or e.__class__.__name__
            return {"success": False, "error": detail}
        finally:
            if failed or not keep_driver:
                self.close_driver()

    def analyze_results(self, saat=None, sinif="EKONOMİ", minimum_koltuk=1):
        """Sefer sonuçlarını analiz eder"""
        try:
            requested_classes = normalize_classes(sinif)
            # Sayfa kaynağını kaydet
            with open(self.debug_file, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.info(f"Sayfa kaynağı {self.debug_file} dosyasına kaydedildi")

            # Tıklanan seferin saatini bul
            tıklanan_saat = ""
            if saat:
                tıklanan_saat = f" ({saat})"
                logger.info(f"Tıklanan sefer saati: {saat}")

            # Ekonomi sınıfı kontrolü - açık olan (.collapse.show) sefer kartından al
            try:
                # Sefer tıklandıktan sonra .collapse.show olan bölüm = tıklanan seferin detayı
                js_script = """
                var expanded = Array.from(document.querySelectorAll('.collapse.show')).find(
                    function (element) { return element.querySelector('button[id*="vagonType"]'); }
                );
                if (!expanded) return 'NO_EXPANDED';
                var wanted = arguments[0];
                var buttons = expanded.querySelectorAll('button.btnTicketType');
                var result = {};
                var typeMap = {'1': 'BUSINESS', '2': 'EKONOMİ', '11': 'LOCA'};
                for (var j = 0; j < buttons.length; j++) {
                    var btn = buttons[j];
                    var id = btn.id || '';
                    var match = id.match(/-vagonType-([0-9]+)-/);
                    if (!match || !typeMap[match[1]]) continue;
                    var className = typeMap[match[1]];
                    if (wanted.indexOf(className) === -1) continue;
                    var emptySeat = btn.querySelector('.emptySeat');
                    var parsed = emptySeat
                        ? parseInt(emptySeat.textContent.replace(/[^0-9]/g, ''), 10)
                        : 0;
                    result[className] = Math.max(result[className] || 0, isNaN(parsed) ? 0 : parsed);
                }
                return Object.keys(result).length ? JSON.stringify(result) : 'NO_CLASS';
                """
                js_result = self.driver.execute_script(js_script, requested_classes)
                logger.info(f"JS sonucu: {js_result}")
                if js_result and js_result not in ('NO_EXPANDED', 'NO_CLASS', None):
                    class_seats = {name: int(count) for name, count in json.loads(js_result).items()}
                    available = {name: count for name, count in class_seats.items() if count >= int(minimum_koltuk)}
                    if available:
                        details = ", ".join(f"{name}: {count}" for name, count in available.items())
                        return {
                            "success": True, "found_seats": True,
                            "seats": max(available.values()), "classes": available,
                            "message": f"Boş yer bulundu — {details}{tıklanan_saat}",
                        }
                    return {
                        "success": True, "found_seats": False,
                        "classes": class_seats, "message": f"Boş yer yok{tıklanan_saat}",
                    }
                else:
                    logger.warning(f"JS genişletilmiş bölüm bulunamadı: {js_result}, fallback deneniyor")
            except Exception as e:
                logger.error(f"JavaScript hatası: {e}")

            # Fallback - datetime anchor ile doğru seferin bölümünü bul
            page_source = self.driver.page_source
            search_area = page_source
            if saat:
                anchor = page_source.find(f'datetime="{saat}"')
                if anchor != -1:
                    search_area = page_source[anchor:anchor + 12000]
                    logger.info(f"datetime anchor bulundu, {len(search_area)} char aranıyor")
                else:
                    logger.warning(f'datetime="{saat}" bulunamadı, tüm sayfa taranıyor')
            type_map = {"1": "BUSINESS", "2": "EKONOMİ", "11": "LOCA"}
            class_seats = {}
            wagon_buttons = re.findall(
                r'<button[^>]+id="[^"]*-vagonType-(\d+)-[^"]*"[^>]*>(.*?)</button>',
                search_area,
                re.IGNORECASE | re.DOTALL,
            )
            for type_id, button_html in wagon_buttons:
                class_name = type_map.get(type_id)
                if class_name not in requested_classes:
                    continue
                seat_match = re.search(r'class="emptySeat">\((\d+)\)', button_html)
                count = int(seat_match.group(1)) if seat_match else 0
                class_seats[class_name] = max(class_seats.get(class_name, 0), count)
            if class_seats:
                available = {name: count for name, count in class_seats.items() if count >= int(minimum_koltuk)}
                if available:
                    details = ", ".join(f"{name}: {count}" for name, count in available.items())
                    return {
                        "success": True, "found_seats": True,
                        "seats": max(available.values()), "classes": available,
                        "message": f"Boş yer bulundu — {details}{tıklanan_saat}",
                    }
                return {"success": True, "found_seats": False, "classes": class_seats, "message": f"Boş yer yok{tıklanan_saat}"}

            logger.info("Ekonomi sınıfında boş yer bulunamadı")
            return {"success": True, "found_seats": False, "message": "Boş yer yok"}

        except Exception as e:
            logger.error(f"Sonuç analizinde hata: {e}")
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    checker = TCDDTicketChecker(headless=False)
    result = checker.check_tickets(
        binis_istasyonu="Eryaman YHT",
        inis_istasyonu="Konya (Selçuklu YHT)",
        tarih="26.04.2026"
    )
    print(result)
