#!/usr/bin/env bash
# Pasang Hermes Pixel Office sebagai layanan systemd.  Jalankan:  sudo ./install.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Jalankan dengan sudo: sudo ./install.sh"; exit 1; }
DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_USER="${SUDO_USER:-root}"
HOME_DIR="$(getent passwd "$RUN_USER" | cut -d: -f6)"
command -v python3 >/dev/null || { echo "python3 tidak ditemukan"; exit 1; }
if [ ! -f /etc/hermes-pixel-office.env ]; then
  sed -e "s|/home/USER|$HOME_DIR|" "$DIR/deploy/hermes-pixel-office.env.example" > /etc/hermes-pixel-office.env
  chmod 600 /etc/hermes-pixel-office.env
  echo "Dibuat /etc/hermes-pixel-office.env"
fi
sed -e "s|__USER__|$RUN_USER|g" -e "s|__DIR__|$DIR|g" "$DIR/deploy/hermes-pixel-office.service" > /etc/systemd/system/hermes-pixel-office.service
if ! grep -q '^BRIDGE_PASSWORD' /etc/hermes-pixel-office.env; then
  read -r -p "Buat password untuk halaman ini? (y/N) " ans
  if [ "$ans" = "y" ] || [ "$ans" = "Y" ]; then
    LINE="$(python3 "$DIR/hermes_bridge.py" --hash)" && echo "$LINE" >> /etc/hermes-pixel-office.env && echo "Password disimpan."
  fi
fi
systemctl daemon-reload
systemctl enable hermes-pixel-office
systemctl restart hermes-pixel-office
sleep 1
PORT="$(grep -E '^BRIDGE_PORT=' /etc/hermes-pixel-office.env | cut -d= -f2)"; PORT="${PORT:-8114}"
echo "--- cek ---"
curl -fsS "http://127.0.0.1:$PORT/health" && echo || { echo "GAGAL. Lihat: journalctl -u hermes-pixel-office -n 30"; exit 1; }
echo "OK. Buka http://127.0.0.1:$PORT/ atau domain tunnel Anda. Pengaturan di /etc/hermes-pixel-office.env"
