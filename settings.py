import os
from datetime import datetime


APP_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(APP_DIR, ".env")

ALLOWED_CLASSES = ("EKONOMİ", "BUSINESS", "LOCA")


def normalize_classes(value):
    raw_values = value.replace(" ", ",").split(",") if isinstance(value, str) else value
    aliases = {"BUSİNESS": "BUSINESS", "TÜMÜ": "HEPSİ", "TUMU": "HEPSİ", "HEPSI": "HEPSİ"}
    normalized = []
    for item in raw_values:
        name = aliases.get(str(item).strip().upper(), str(item).strip().upper())
        if not name:
            continue
        if name == "HEPSİ":
            return list(ALLOWED_CLASSES)
        if name not in ALLOWED_CLASSES:
            raise ValueError(f"Geçersiz sınıf: {item}")
        if name not in normalized:
            normalized.append(name)
    if not normalized:
        raise ValueError("En az bir sınıf seçilmeli")
    return normalized


def validate_settings(binis, inis, tarih, saatler, kontrol_sikligi, sinif="EKONOMİ", minimum_koltuk=1):
    if not binis.strip() or not inis.strip():
        raise ValueError("Biniş ve iniş istasyonu boş olamaz")
    datetime.strptime(tarih, "%Y-%m-%d")
    if not saatler:
        raise ValueError("En az bir sefer saati gerekli")
    for saat in saatler:
        datetime.strptime(saat, "%H:%M")
    if int(kontrol_sikligi) < 30:
        raise ValueError("Kontrol aralığı en az 30 saniye olmalı")
    normalize_classes(sinif)
    if int(minimum_koltuk) < 1:
        raise ValueError("Minimum koltuk en az 1 olmalı")


def update_env(updates, path=ENV_PATH):
    """Mevcut sırayı ve gizli alanları koruyarak .env değerlerini günceller."""
    try:
        with open(path, encoding="utf-8") as env_file:
            lines = env_file.readlines()
    except FileNotFoundError:
        lines = []

    remaining = dict(updates)
    output = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0]
            if key in remaining:
                output.append(f"{key}={remaining.pop(key)}\n")
                continue
        output.append(line)
    if output and output[-1].strip():
        output.append("\n")
    output.extend(f"{key}={value}\n" for key, value in remaining.items())
    with open(path, "w", encoding="utf-8") as env_file:
        env_file.writelines(output)
