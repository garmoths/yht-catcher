#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"

info() {
  printf '\n[%s] %s\n' "YHT" "$1"
}

fail() {
  printf '\n[HATA] %s\n' "$1" >&2
  exit 1
}

find_python() {
  local candidate
  for candidate in python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      if "${candidate}" -c 'import sys; raise SystemExit(sys.version_info < (3, 9))'; then
        printf '%s' "${candidate}"
        return 0
      fi
    fi
  done
  return 1
}

PYTHON_BIN="$(find_python)" || fail "Python 3.9 veya daha yenisi bulunamadı. Önce Python kurun."

info "Python bulundu: $("${PYTHON_BIN}" --version 2>&1)"

if [[ ! -d "${VENV_DIR}" ]]; then
  info "Sanal ortam oluşturuluyor..."
  "${PYTHON_BIN}" -m venv "${VENV_DIR}" || fail "Sanal ortam oluşturulamadı. Python venv paketini kontrol edin."
else
  info "Mevcut sanal ortam kullanılacak."
fi

info "Python paketleri yükleniyor..."
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${SCRIPT_DIR}/requirements.txt"
"${VENV_DIR}/bin/python" -m pip check

if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
  cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
  info ".env dosyası örnek ayarlardan oluşturuldu. Twilio bilgilerini girmeniz gerekiyor."
else
  info "Mevcut .env dosyası korundu."
fi

if command -v google-chrome >/dev/null 2>&1 \
  || command -v google-chrome-stable >/dev/null 2>&1 \
  || command -v chromium >/dev/null 2>&1 \
  || command -v chromium-browser >/dev/null 2>&1 \
  || [[ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]]; then
  info "Chrome/Chromium bulundu."
else
  printf '\n[UYARI] Chrome veya Chromium bulunamadı. Botu çalıştırmadan önce kurun.\n' >&2
fi

printf '\nKurulum tamamlandı. Botu başlatmak için:\n\n'
printf '  cd %q\n' "${SCRIPT_DIR}"
printf '  .venv/bin/python main.py\n\n'
