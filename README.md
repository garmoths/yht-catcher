# YHT TREN BULUCU 🚂

TCDD Yüksek Hızlı Tren (YHT) biletlerini otomatik takip eden, **EKONOMİ sınıfında** boş yer bulunduğunda WhatsApp üzerinden bildirim gönderen Python aracı.

## Özellikler

- ✅ İnteraktif CLI kurulum (adım adım giriş)
- ✅ Birden fazla sefer saati desteği (boşluk ile ayır)
- ✅ Doğru sefer eşleştirme (`datetime` attribute ile)
- ✅ EKONOMİ sınıfı koltuk sayısı tespiti
- ✅ WhatsApp bildirimleri (Twilio Sandbox)
- ✅ Bildirim cooldown - 1 saatte 1 mesaj, restart'ta sıfırlanmaz
- ✅ Sefer bazlı cooldown (farklı saatler birbirini susturmaz)
- ✅ Yanlış alarmı azaltan iki aşamalı koltuk doğrulaması
- ✅ Art arda hata eşiği ve sistem düzeldi bildirimi
- ✅ WhatsApp gerçek teslim durumu kontrolü
- ✅ EKONOMİ / BUSINESS / LOCA için tekli veya çoklu seçim ve minimum koltuk sayısı
- ✅ Hatalarda otomatik yavaşlayan, normalde ayarlanan aralığa dönen kontrol
- ✅ Headless Chrome / Daemon modu (sunucuda çalışır)
- ✅ `.env` ile kolay yapılandırma

---

## Kurulum

### Gereksinimler

- Python 3.9+
- Google Chrome veya Chromium (macOS, Windows ve Linux desteklenir)
- Ubuntu sunucu için en az 1GB RAM + 1GB swap önerilir

### 1. Bağımlılıkları Yükle

Otomatik kurulum (macOS/Linux):

```bash
chmod +x yukle.sh
./yukle.sh
```

Script Python sürümünü kontrol eder, `.venv` oluşturur, bağımlılıkları kurar
ve `.env` yoksa `.env.example` üzerinden oluşturur. Var olan `.env` ve gizli
bilgiler kesinlikle değiştirilmez.

Otomatik kurulum (Windows):

Dosya Gezgini'nden `yukle.bat` dosyasına çift tıklayın veya Komut İstemi'nde:

```bat
yukle.bat
```

PowerShell üzerinden doğrudan çalıştırmak için:

```powershell
powershell -ExecutionPolicy Bypass -File .\yukle.ps1
```

Windows'ta botu daha sonra şu komutla açabilirsiniz:

```bat
.venv\Scripts\python.exe main.py
```

Elle kurulum:

```bash
pip install -r requirements.txt
```

### 2. Twilio WhatsApp Sandbox Kur

1. [twilio.com](https://www.twilio.com/) → kaydol
2. Console → Messaging → Try it out → Send a WhatsApp message
3. Sandbox keyword'ünü öğren (örn. `join green-elephant`)
4. **Kendi WhatsApp'ından** `+1 415 523 8886` numarasına `join <keyword>` yaz
5. Account SID ve Auth Token'ı kaydet

> ⚠️ Twilio Sandbox oturumu **72 saatte bir** süresi dolar. Bildirim gelmezse tekrar `join <keyword>` mesajı atman gerekir.

### 3. `.env` Dosyasını Oluştur

```env
# TCDD Ayarları
BINIS_ISTASYONU=ERYAMAN YHT
INIS_ISTASYONU=SELÇUKLU YHT (KONYA)
TARIH=2026-05-10
SAAT=18:24
SAAT_KONTROL=true

# WhatsApp Twilio Ayarları
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
KULLANICI_WHATSAPP_NUMARASI=whatsapp:+90xxxxxxxxxx

# Kontrol Sıklığı (saniye) - 300 = 5 dakika
KONTROL_SIKLIGI=300
```

> `SAAT` alanına birden fazla saat girebilirsin: `SAAT=06:44 18:24`

---

## Kullanım

### İnteraktif Mod (Varsayılan)

```bash
.venv/bin/python main.py
```

Terminal menüsünden ayarları görebilir/değiştirebilir, botu başlatabilir,
tek kontrol yapabilir veya WhatsApp testi gönderebilirsin. `.env` dosyasını
elle düzenlemek gerekmez ve Twilio bilgileri ayar değişimlerinde korunur.

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

İstasyon seçerken bot güncel listeyi doğrudan TCDD sayfasından alır. Kullanıcı
şehir veya istasyon adının bir bölümünü yazar ve eşleşen sonuçlardan numara
seçer. Böylece istasyon adının veya kelime sırasının değişmesi `.env` ayarını
elle düzeltmeyi gerektirmez. Liste alınamazsa elle giriş seçeneğine geri döner.

Bölüm seçiminde `1`, `1 2`, `2 3` veya `hepsi` yazılabilir. Ekonomi, Business
ve Loca birlikte ya da ayrı ayrı takip edilebilir. Tekerlekli sandalye kontenjanı
özel kullanım alanı olduğu için seçeneklerde gösterilmez ve boş koltuk hesabına
kesinlikle katılmaz.

Güzergâh ve tarih seçildikten sonra o günün güncel sefer saatleri TCDD'den
otomatik alınır ve numaralı gösterilir. Kullanıcı `1`, `1 3` veya `hepsi`
yazarak birden fazla sefer seçebilir. TCDD sorgusu geçici olarak başarısız olursa
manuel saat girişi otomatik yedek olarak açılır.

İlk açılışta Twilio bilgilerinin eksik veya örnek değer olduğu anlaşılırsa bot
uyarı verir. Auth Token terminalde görünmeden girilir. Telefon numarası `05...`
biçiminde yazılırsa otomatik olarak `whatsapp:+905...` biçimine çevrilir.

### Daemon Modu (Sunucu)

```bash
nohup python3 main.py daemon > yht.log 2>&1 &
```

Arka planda çalışır. Logları izlemek için:

```bash
tail -f yht.log
```

Durdurmak için:

```bash
pkill -f 'main.py daemon'
```

---

## Sunucuya Deploy

```bash
# Dosyaları gönder
scp tcdd_checker.py main.py config.py whatsapp_notifier.py .env requirements.txt root@SUNUCU_IP:/root/yht_catcher/

# Sunucuya bağlan
ssh root@SUNUCU_IP

# Bağımlılıkları kur (ilk seferinde)
cd /root/yht_catcher
pip3 install -r requirements.txt

# Google Chrome kur (ilk seferinde)
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt-get update && apt-get install -y google-chrome-stable

# Swap ekle (512MB RAM sunucular için gerekli)
dd if=/dev/zero of=/swap2 bs=1M count=1024 && chmod 600 /swap2 && mkswap /swap2 && swapon /swap2

# Daemon başlat
nohup python3 main.py daemon > yht.log 2>&1 &
```

---

## Ayar Güncelleme (`.env` değiştirince)

```bash
# Yeni ayarı gönder
scp .env root@SUNUCU_IP:/root/yht_catcher/

# Daemon'ı yeniden başlat
ssh root@SUNUCU_IP "pkill -f 'main.py daemon'; cd /root/yht_catcher && nohup python3 main.py daemon > yht.log 2>&1 &"
```

---

## İstasyon İsimleri

TCDD web sitesindeki ile birebir aynı olmalı:

- `ERYAMAN YHT`
- `Ankara Gar`
- `SELÇUKLU YHT (KONYA)`
- `İstanbul(Söğütlüçeşme)`
- `İstanbul(Pendik)`
- `Eskişehir`

---

## Bildirim Sistemi

- Boş yer bulununca WhatsApp mesajı gönderilir
- Aynı bildirim **1 saat içinde tekrar atılmaz** (cooldown)
- Cooldown bilgisi `.last_notify` dosyasına kaydedilir, daemon restart'ta sıfırlanmaz
- Bildirim gelmezse: Twilio sandbox oturumunu yenile (`join <keyword>`)

---

## Güvenlik

- ⚠️ Bu araç eğitim amaçlıdır
- ⚠️ TCDD ile resmi ilişkisi yoktur
- ⚠️ `.env` dosyasını git'e commit etme
- ⚠️ Aşırı istek göndermekten kaçın

## Lisans

MIT License
