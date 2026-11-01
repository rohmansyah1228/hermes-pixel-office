# Hermes Pixel Office v1.0

Kantor pixel bertingkat untuk agent Hermes: satu divisi = satu lantai, meja/kursi/komputer mengikuti jumlah agent, klik agent untuk melihat tugas dan komputasinya, hasil bisa diunduh atau diunggah ke GitHub, dan ada chat untuk memberi instruksi.

Tanpa server, halaman jalan dalam **mode demo**. Untuk data nyata, jalankan `hermes_bridge.py` di server Hermes Anda.

## Pasang di server Hermes (Linux)
```bash
git clone https://github.com/rohmansyah1228/hermes-pixel-office.git
cd hermes-pixel-office
sudo ./install.sh
```
Skrip ini membuat token akses acak di `/etc/hermes-pixel-office.env`, memasang layanan systemd, dan mengecek `/health`. Lalu buka `http://127.0.0.1:8114/?token=TOKEN` dari server itu sendiri, atau lewat Cloudflare Tunnel / Tailscale (lihat bawah).

## Dari mana datanya?
Bridge memilih sumber otomatis (atur di `/etc/hermes-pixel-office.env`):

| Sumber | Pengaturan | Catatan |
|---|---|---|
| Database sesi Hermes | `HERMES_DB=/home/USER/.hermes/state.db` | Paling mudah, tanpa API key. Dibuka read-only. |
| API server Hermes | `HERMES_API_URL=http://127.0.0.1:8642` + `HERMES_API_KEY` | Perlu `API_SERVER_ENABLED=true` dan `API_SERVER_KEY` di `~/.hermes/.env`, lalu `hermes gateway`. |
| agent-office | `AGENT_OFFICE_URL=http://127.0.0.1:8113` | Opsional. |

Pemetaan: satu sesi Hermes = satu agent; `source` (cli, telegram, cron, ...) = divisi/lantai; sesi dengan aktivitas dalam 90 detik terakhir = "bekerja". Bisa diatur lewat `HERMES_ACTIVE_SECONDS`, `HERMES_RECENT_HOURS`, `HERMES_MAX_AGENTS`.

## Chat
Butuh `HERMES_API_URL` dan `HERMES_API_KEY` (API server Hermes). Pesan dikirim ke `/v1/chat/completions`; kunci tidak pernah sampai ke browser. Chat **dimatikan** bila `BRIDGE_TOKEN` kosong.

## Domain publik (Cloudflare Tunnel)
Arahkan tunnel ke `http://127.0.0.1:8114`. Untuk keamanan:
1. Wajib isi `BRIDGE_TOKEN`. Buka sekali `https://domain-anda/?token=TOKEN`; browser menyimpannya.
2. Disarankan menambah Cloudflare Access di depan domain.

Error 502 dari Cloudflare berarti tunnel tidak bisa menjangkau bridge: cek `systemctl status hermes-pixel-office`, `curl http://127.0.0.1:8114/health`, dan port tujuan di konfigurasi tunnel.

## Tailscale
`tailscale serve --bg 8114`, lalu buka `https://nama-server.tailnet.ts.net/?token=TOKEN`.

## Pemeliharaan
```bash
cd ~/hermes-pixel-office && git pull && sudo systemctl restart hermes-pixel-office
journalctl -u hermes-pixel-office -n 30
```

## Catatan lisensi
`index.html` memuat aset Modern Interiors/Office (LimeZu) dan peta dari hermes-town. Jaga repo ini private atau pastikan lisensi aset mengizinkan redistribusi.
