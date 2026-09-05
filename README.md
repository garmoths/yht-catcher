# YHT Catcher 🚄

TCDD Yüksek Hızlı Tren (YHT) seferlerinde boş koltuk açıldığında WhatsApp üzerinden anlık bildirim gönderen terminal tabanlı takip botu.

> ⚠️ **Yasal Uyarı (Disclaimer):** Bu araç yalnızca **kişisel kullanım ve eğitim** amacıyla geliştirilmiştir. TCDD Taşımacılık A.Ş. ile herhangi bir resmî bağı, ortaklığı veya sponsorluğu yoktur. Bot **kesinlikle bilet satın almaz, ödeme yapmaz veya koltuk bloke etmez**; yalnızca kamuya açık bilet sorgulama ekranını düzenli aralıklarla kontrol eder. Sunucuları yormayacak makul kontrol aralıkları (varsayılan 180 sn) kullanılmalıdır. Doğabilecek tüm hukuki ve teknik sorumluluk son kullanıcıya aittir.

---

## ✨ Özellikler

- **İnteraktif Terminal Menüsü:** İstasyon, tarih, saat ve vagon sınıfı seçimini terminalden adım adım yapma.
- **Çoklu Sefer ve Vagon Takibi:** Aynı gün içindeki birden fazla saati ve vagon tipini (Ekonomi, Business, Loca) eşzamanlı izleme.
- **Akıllı Doğrulama (2 Aşamalı):** Yanlış alarmları önlemek için koltuk durumunu çift kontrolden geçirir.
- **WhatsApp Bildirimi:** Twilio API entegrasyonuyla koltuk bulunduğunda anında mesaj iletir.
- **Cooldown & Hata Koruması:** Tekrarlayan bildirim spamını ve geçici ağ kesintilerini akıllıca yönetir.

---

## 🚀 Hızlı Başlangıç

### 1. Gereksinimler
- Python 3.9+
- Google Chrome veya Chromium

### 2. Kurulum

**macOS / Linux:**
```bash
git clone https://github.com/garmoths/yht-catcher.git
cd yht-catcher
chmod +x yukle.sh && ./yukle.sh
```

**Windows:**
`yukle.bat` dosyasına çift tıklayın veya PowerShell'de çalıştırın:
```powershell
powershell -ExecutionPolicy Bypass -File .\yukle.ps1
```

---

## 💻 Çalıştırma

Terminalden botu başlatmak için:

**macOS / Linux:**
```bash
.venv/bin/python main.py
```

**Windows:**
```bat
.venv\Scripts\python.exe main.py
```

### Komut Satırı Seçenekleri
- **Doğrudan Arka Planda Takip:** `.venv/bin/python main.py daemon`
- **Tek Seferlik Kontrol:** `.venv/bin/python main.py once`
- **WhatsApp Bildirim Testi:** `.venv/bin/python main.py test`

---

## 📱 WhatsApp Bildirim Ayarları

1. [Twilio Console](https://console.twilio.com/) hesabı oluşturup **WhatsApp Sandbox**'ı etkinleştirin.
2. WhatsApp üzerinden Sandbox numarasına belirtilen `join <kod>` mesajını atın.
3. Bot menüsünden `2) Bildirim ayarları` seçeneğini açıp bilgilerinizi girin.
4. `4) Test et` menüsünden `1`'i seçerek test mesajı iletimini doğrulayın.

---

## 🔒 Güvenlik

- API anahtarlarınızı ve telefon numaralarınızı kaynak koda eklemeyin; tüm gizli bilgiler `.env` dosyasında saklanır.
- `.env`, `.bot_state.json` ve log dosyaları `.gitignore` ile korunmaktadır.

---

## 🧪 Testler

```bash
.venv/bin/python -m unittest discover -s tests -v
```

---

## 📄 Lisans

Bu proje [MIT](LICENSE) lisansı altındadır.

