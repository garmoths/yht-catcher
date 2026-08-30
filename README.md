# YHT Catcher 🚄

TCDD YHT seferlerinde boş koltukları düzenli aralıklarla kontrol eden ve uygunluk doğrulandığında WhatsApp bildirimi gönderen terminal uygulaması.

> TCDD Taşımacılık ile resmî bağlantısı yoktur. Makul kontrol aralıklarıyla ve kişisel kullanım amacıyla kullanın.

## Özellikler

- Terminalden adım adım kurulum ve yönetim
- TCDD’den alınan güncel istasyon listesinde arama ve numaralı seçim
- Güzergâh ve tarihe göre sefer saatlerini otomatik getirme
- Bir veya birden fazla seferi aynı anda takip etme
- Ekonomi, Business ve Loca için tekli/çoklu seçim
- Tekerlekli sandalye kontenjanını normal koltuk hesabından hariç tutma
- Minimum boş koltuk sayısı belirleme
- Yanlış alarmı azaltmak için iki aşamalı doğrulama
- Sefer bazlı, yeniden başlatmalarda korunan bildirim cooldown’u
- Art arda hata eşiği ve sistem düzeldi bildirimi
- Twilio mesajının gerçek teslim durumunu kontrol etme
- Hatalarda otomatik yavaşlayan kontrol aralığı
- macOS, Linux ve Windows kurulum scriptleri

## Gereksinimler

- Python 3.9 veya üzeri
- Google Chrome ya da Chromium
- İnternet bağlantısı
- WhatsApp bildirimleri için Twilio hesabı ve WhatsApp Sandbox

## Kurulum

### macOS / Linux

```bash
git clone https://github.com/garmoths/yht-catcher.git
cd yht-catcher
chmod +x yukle.sh
./yukle.sh
```

### Windows

Projeyi indirdikten sonra `yukle.bat` dosyasına çift tıklayın veya Komut İstemi’nde:

```bat
yukle.bat
```

PowerShell ile doğrudan çalıştırmak için:

```powershell
powershell -ExecutionPolicy Bypass -File .\yukle.ps1
```

Kurulum scriptleri:

- Python sürümünü kontrol eder.
- `.venv` sanal ortamını oluşturur.
- Gerekli paketleri kurup doğrular.
- `.env` yoksa güvenli `.env.example` üzerinden oluşturur.
- Var olan `.env` ve gizli bilgileri değiştirmez.
- Chrome/Chromium kurulumunu kontrol eder.

## İlk çalıştırma

macOS / Linux:

```bash
.venv/bin/python main.py
```

Windows:

```bat
.venv\Scripts\python.exe main.py
```

Ana menü:

```text
1) Ayarları göster
2) Ayarları değiştir
3) Botu başlat
4) Tek kontrol yap
5) WhatsApp testi gönder
6) WhatsApp ayarları
7) Kurulum yardımı
0) Çıkış
```

## Takip ayarları

`2) Ayarları değiştir` seçildiğinde:

1. Güncel istasyonlar TCDD’den alınır.
2. Biniş ve iniş istasyonu isimle aranıp numarayla seçilir.
3. Tarih girilir.
4. O günün sefer saatleri otomatik getirilir.
5. Bir veya birden fazla sefer seçilir.
6. Takip edilecek bölümler ve minimum koltuk sayısı belirlenir.

Saat seçimi örnekleri:

```text
1      Yalnızca birinci sefer
1 3    Birinci ve üçüncü sefer
hepsi  Listelenen tüm seferler
```

Bölüm seçimi:

```text
1) Ekonomi
2) Business
3) Loca
```

`1`, `1 2`, `2 3` veya `hepsi` yazılabilir. Tekerlekli sandalye kontenjanı menüde gösterilmez ve uygunluk hesabına katılmaz.

## WhatsApp kurulumu

1. [Twilio Console](https://console.twilio.com/) üzerinden bir hesap oluşturun.
2. WhatsApp Sandbox sayfasını açın.
3. Sayfadaki `join <sandbox-kodu>` mesajını alıcı WhatsApp numarasından Sandbox numarasına gönderin.
4. Bot menüsünde `6) WhatsApp ayarları` seçeneğini açın.
5. Account SID, Auth Token, gönderen ve alıcı numaralarını girin.
6. `5) WhatsApp testi gönder` ile teslimatı doğrulayın.

Auth Token terminalde görünmeden alınır. `05...` biçiminde yazılan Türkiye numarası otomatik olarak `whatsapp:+905...` biçimine çevrilir.

Twilio Sandbox katılımı zaman aşımına uğrayabilir. `63015` hatasında güncel `join` kodunu aynı alıcı WhatsApp hesabından yeniden gönderin.

## Komut satırı modları

Tek kontrol:

```bash
.venv/bin/python main.py once
```

Sürekli takip:

```bash
.venv/bin/python main.py daemon
```

WhatsApp testi:

```bash
.venv/bin/python main.py test
```

Arka planda Linux/macOS kullanımı:

```bash
nohup .venv/bin/python main.py daemon > yht.log 2>&1 &
```

## Bildirim davranışı

- Koltuk ilk kontrolde bulunursa ikinci kez doğrulanır.
- İkinci kontrol de olumluysa WhatsApp bildirimi gönderilir.
- Cooldown güzergâh, tarih, saat ve bölüm seçimine göre ayrı tutulur.
- Cooldown yalnızca mesaj gerçekten gönderilebilirse başlatılır.
- İlk geçici hatalar loglanır; belirlenen ardışık hata eşiğinde WhatsApp uyarısı gönderilir.
- Sistem yeniden sağlıklı çalıştığında iyileşme bildirimi gönderilir.

## Güvenlik

Gerçek kimlik bilgileri yalnızca `.env` dosyasında tutulmalıdır. Aşağıdaki dosyalar Git tarafından dışlanır:

```text
.env
.venv/
.bot_state.json
debug_page.html
screenshot.png
*.log
```

- Auth Token veya kişisel telefon numarasını kaynak koda yazmayın.
- `.env.example` yalnızca örnek değerler içermelidir.
- GitHub push protection ve secret scanning özelliklerini etkin tutun.
- Yanlışlıkla paylaşılan token’ı silmekle yetinmeyin; sağlayıcı panelinden yenileyin.

Gitleaks ile yerel tarama:

```bash
gitleaks git --redact --no-banner .
```

Bu komut Git geçmişindeki ve commit edilmiş dosyalardaki sırları tarar. Yerel `.env`
dosyasının sır içermesi normaldir; önemli olan bu dosyanın Git'e eklenmemesidir.

## Testler

```bash
.venv/bin/python -W error -m py_compile *.py tests/test_bot.py
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip check
```

Testler; çoklu saat/bölüm seçimi, iki aşamalı doğrulama, cooldown, hata eşiği, Twilio teslim sonucu ve tekerlekli sandalye kontenjanının dışlanmasını kapsar.

## Sınırlamalar

- TCDD arayüzü tamamen değişirse seçicilerin güncellenmesi gerekebilir.
- Sandbox üretim ortamı değildir ve katılım süresi dolabilir.
- Otomasyon bilet satın almaz; yalnızca uygunluk bildirimi gönderir.
- Aynı anda tek güzergâh ve birden fazla sefer takip edilir.

## Lisans

MIT
