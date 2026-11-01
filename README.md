# Hermes Pixel Office v1.0

Kantor pixel bertingkat untuk agent Hermes: satu divisi = satu lantai, meja/kursi/komputer mengikuti jumlah agent, klik agent untuk melihat tugas dan komputasinya, hasil bisa diunduh atau diunggah ke GitHub, dan ada chat untuk memberi instruksi.

Tanpa server, halaman jalan dalam **mode demo**. Untuk data nyata, jalankan `hermes_bridge.py` di server Hermes Anda.

## Pasang sebagai plugin Hermes (disarankan, seperti agent-office)
```bash
git clone https://github.com/rohmansyah1228/hermes-pixel-office.git
cd hermes-pixel-office
python3 install.py          # mendeteksi Hermes, memasang plugin, dan mengaktifkannya
```
Lalu mulai ulang Hermes (mis. `hermes gateway restart`, atau tutup dan buka lagi `hermes`). Plugin mencatat aktivitas agent lewat hook dan menyalakan halaman di `http://127.0.0.1:8114/` selama Hermes berjalan. Cek dengan `curl http://127.0.0.1:8114/health`. Jalankan ulang `python3 install.py` kapan saja; `git pull` otomatis memperbarui karena plugin berupa tautan ke folder repo. Ganti port dengan `python3 install.py --port 9000`. Pengaturan lain ada di `~/.hermes/hermes-pixel-office/config.env`.

Bila `hermes plugins enable hermes-pixel-office` gagal di versi Hermes Anda, kirim pesan error-nya.

Catatan privasi: ringkasan perintah tool (80 karakter pertama) tampil di halaman. Jangan buka halaman ke publik tanpa pembatasan akses.

## Opsi lain: layanan sendiri (systemd)
Untuk menjalankan tanpa plugin (data dari database/API Hermes saja):
```bash
sudo ./install.sh
```
Skrip ini membuat `/etc/hermes-pixel-office.env`, memasang layanan systemd, dan mengecek `/health`. Token tidak wajib.

## Dari mana datanya?
Bridge memilih sumber otomatis (atur di `/etc/hermes-pixel-office.env`):

| Sumber | Pengaturan | Catatan |
|---|---|---|
| Database sesi Hermes | `HERMES_DB=/home/USER/.hermes/state.db` | Paling mudah, tanpa API key. Dibuka read-only. |
| API server Hermes | `HERMES_API_URL=http://127.0.0.1:8642` + `HERMES_API_KEY` | Perlu `API_SERVER_ENABLED=true` dan `API_SERVER_KEY` di `~/.hermes/.env`, lalu `hermes gateway`. |
| agent-office | `AGENT_OFFICE_URL=http://127.0.0.1:8113` | Opsional. |
| Hook plugin | otomatis setelah `python3 install.py` | Status waktu nyata (tool yang sedang dipakai, error, subagent). Ditumpuk di atas sumber lain. |

Pemetaan: satu sesi Hermes = satu agent; `source` (cli, telegram, cron, ...) = divisi/lantai; sesi dengan aktivitas dalam 90 detik terakhir = "bekerja". Bisa diatur lewat `HERMES_ACTIVE_SECONDS`, `HERMES_RECENT_HOURS`, `HERMES_MAX_AGENTS`.

## Chat
Butuh `HERMES_API_URL` dan `HERMES_API_KEY` (API server Hermes). Pesan dikirim ke `/v1/chat/completions`; kunci tidak pernah sampai ke browser. Tanpa `BRIDGE_TOKEN`, chat **mati** secara bawaan supaya orang lain tidak bisa memberi instruksi ke agent Anda. Aktifkan dengan `BRIDGE_OPEN_CHAT=1` hanya bila akses sudah dibatasi (Cloudflare Access atau Tailscale).

## Domain publik (Cloudflare Tunnel)
Arahkan tunnel ke `http://127.0.0.1:8114`. Untuk keamanan:
Tanpa token, siapa pun yang tahu alamatnya bisa melihat daftar agent dan tugasnya. Disarankan memasang **Cloudflare Access** (login email) di depan domain; itu tidak butuh token di alamat. `BRIDGE_TOKEN` tetap tersedia sebagai opsi.

Error 502 dari Cloudflare berarti tunnel tidak bisa menjangkau bridge: cek `systemctl status hermes-pixel-office`, `curl http://127.0.0.1:8114/health`, dan port tujuan di konfigurasi tunnel.

## Tailscale
`tailscale serve --bg 8114`, lalu buka `https://nama-server.tailnet.ts.net/`.

## Pemeliharaan
```bash
cd ~/hermes-pixel-office && git pull && sudo systemctl restart hermes-pixel-office
journalctl -u hermes-pixel-office -n 30
```

## Catatan lisensi
`index.html` memuat aset Modern Interiors/Office (LimeZu) dan peta dari hermes-town. Jaga repo ini private atau pastikan lisensi aset mengizinkan redistribusi.
