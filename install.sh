#!/usr/bin/env bash
# Pasang Hermes Pixel Office sebagai layanan systemd.  Jalankan:  sudo ./install.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Jalankan dengan sudo: sudo ./install.sh"; exit 1; }
DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_USER="${SUDO_USER:-root}"
HOME_DIR="$(getent passwd "$RUN_USER" | cut -d: -f6)"
command -v python3 >/dev/null || { echo "python3 tidak ditemukan"; exit 1; }
if [ ! -f /etc/hermes-pixel-office.env ]; then
  TOKEN="$(python3 -c 'import secrets;print(secrets.token_hex(24))')"
  sed -e "s|GANTI_DENGAN_TOKEN_ACAK|$TOKEN|" -e "s|/home/USER|$HOME_DIR|" "$DIR/deploy/hermes-pixel-office.env.example" > /etc/hermes-pixel-office.env
  chmod 600 /etc/hermes-pixel-office.env
  echo "Dibuat /etc/hermes-pixel-office.env  (token akses: $TOKEN)"
fi
sed -e "s|__USER__|$RUN_USER|g" -e "s|__DIR__|$DIR|g" "$DIR/deploy/hermes-pixel-office.service" > /etc/systemd/system/hermes-pixel-office.service
systemctl daemon-reload
systemctl enable hermes-pixel-office
systemctl restart hermes-pixel-office
sleep 1
PORT="$(grep -E '^BRIDGE_PORT=' /etc/hermes-pixel-office.env | cut -d= -f2)"; PORT="${PORT:-8114}"
echo "--- cek ---"
curl -fsS "http://127.0.0.1:$PORT/health" && echo || { echo "GAGAL. Lihat: journalctl -u hermes-pixel-office -n 30"; exit 1; }
echo "OK. Token ada di /etc/hermes-pixel-office.env (BRIDGE_TOKEN). Buka sekali: https://DOMAIN-ANDA/?token=TOKEN"
