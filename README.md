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

Pasang password (disarankan, wajib bila lewat domain publik): `python3 install.py --set-password`, lalu mulai ulang Hermes. Anda login sekali; sesi tetap aktif selama halaman dipakai dan habis setelah 120 menit tanpa aktivitas (atur `BRIDGE_SESSION_MINUTES`), lalu harus memasukkan password lagi. Tombol **Keluar** mengakhiri sesi.

Bila `hermes plugins enable hermes-pixel-office` gagal di versi Hermes Anda, kirim pesan error-nya.

Catatan privasi: ringkasan perintah tool (80 karakter pertama) tampil di halaman. Jangan buka halaman ke publik tanpa password.

## Opsi lain: layanan sendiri (systemd)
Untuk menjalankan tanpa plugin (data dari database/API Hermes saja):
```bash
sudo ./install.sh
```
Skrip ini membuat `/etc/hermes-pixel-office.env`, memasang layanan systemd, dan mengecek `/health`. Password ditanyakan saat install (opsional).

## Apa yang dianggap "agent"?
Satu **profil Hermes** = satu agent (`~/.hermes` = agent `Hermes`, lalu tiap `~/.hermes/profiles/<nama>/`). Data tiap agent dibaca dari `state.db` profil itu: token, biaya, jumlah tool, dan aktivitas terakhir. Agent tampil "bekerja" bila ada aktivitas dalam 90 detik terakhir (atau hook plugin melaporkan tool yang sedang berjalan). Subagent (`delegate_task`) yang sedang jalan muncul sebagai agent tambahan.

**Divisi** (lantai) belum ada di Hermes, jadi semua agent masuk divisi `Hermes`. Untuk membaginya, buat `~/.hermes/hermes-pixel-office/divisions.json`:
```json
{"coder": "Engineering", "writer": "Konten", "default": "Operasional"}
```
Isi `"hidden"` untuk menyembunyikan profil (mis. `"default": "hidden"`). Contoh lengkap: `deploy/divisions.example.json`, disalin otomatis oleh `install.py` bila belum ada. Perubahan terbaca otomatis tanpa restart. Satu lantai memuat maksimal 8 agent.

Cek apa yang terdeteksi di server: `python3 hermes_bridge.py --diag`.

Kalau ingin tampilan lama (satu sesi = satu agent), isi `HERMES_VIEW=sessions` di `config.env`.

Bila Anda memakai beberapa profil, pasang plugin di tiap profil (`HERMES_HOME=~/.hermes/profiles/<nama> python3 install.py`) atau jalankan satu server sendiri (`sudo ./install.sh`). Data tetap dibaca dari semua profil.

## Sumber data lain
Kalau tidak ada folder Hermes lokal, bridge memakai sumber di bawah ini:

| Sumber | Pengaturan | Catatan |
|---|---|---|
| Database sesi Hermes | `HERMES_DB=/home/USER/.hermes/state.db` | Satu sesi = satu agent. |
| API server Hermes | `HERMES_API_URL=http://127.0.0.1:8642` + `HERMES_API_KEY` | Perlu `API_SERVER_ENABLED=true` dan `API_SERVER_KEY` di `~/.hermes/.env`, lalu `hermes gateway`. |
| agent-office | `AGENT_OFFICE_URL=http://127.0.0.1:8113` | Opsional. |
| Hook plugin | otomatis setelah `python3 install.py` | Status waktu nyata (tool yang sedang dipakai, error, subagent). |

## Chat
Butuh `HERMES_API_URL` dan `HERMES_API_KEY` (API server Hermes). Pesan dikirim ke `/v1/chat/completions`; kunci tidak pernah sampai ke browser. Tanpa password, chat **mati** secara bawaan supaya orang lain tidak bisa memberi instruksi ke agent Anda. Aktifkan dengan `BRIDGE_OPEN_CHAT=1` hanya bila akses sudah dibatasi (Cloudflare Access atau Tailscale).

## Domain publik (Cloudflare Tunnel)
Arahkan tunnel ke `http://127.0.0.1:8114`. Untuk keamanan:
Pasang password (lihat atas) supaya halaman, data agent, dan chat hanya bisa dibuka setelah login. Percobaan salah berulang dari satu IP dikunci sementara. Untuk lapisan tambahan, pasang Cloudflare Access di depan domain.

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
