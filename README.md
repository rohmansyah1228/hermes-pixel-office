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

## Kelola divisi dan agent dari halaman
Buka panel **Kelola divisi dan agent** di sisi kanan:
- **Divisi:** tambah, ganti nama, ubah urutan lantai, dan hapus. Saat menghapus divisi yang berisi agent, pilih divisi tujuan untuk agent-nya.
- **Agent:** klik agent lalu tombol **Atur** untuk mengganti nama, peran, dan memindahkannya ke divisi lain (atau divisi baru). Agent bisa disembunyikan dari kantor dan ditampilkan lagi dari panel yang sama. **Tambah agent** membuat agent manual (hanya penanda, selalu istirahat); agent Hermes yang asli tetap muncul otomatis dari profilnya.
- Agent Hermes tidak dihapus dari Hermes; "hapus" hanya menyembunyikannya dari kantor.

Pengaturan disimpan di server (`~/.hermes/hermes-pixel-office/layout.json`) sehingga sama di semua perangkat. Menyimpan ke server butuh password (`python3 install.py --set-password`), atau akses dari komputer server itu sendiri; di luar itu pengaturan hanya tersimpan di browser. `BRIDGE_ALLOW_EDIT=1` mengizinkan edit tanpa password (tidak disarankan untuk domain publik).

## Menu Atur agent (seperti dashboard Hermes)
Klik agent lalu **Atur**. Setiap halaman punya tombol **Kembali**.

| Menu | Yang terjadi |
|---|---|
| Jadikan aktif * | `hermes profile use <profil>` |
| Ganti model * | `hermes -p <profil> config set model.default <model>` |
| Edit deskripsi | Mengubah peran yang tampil di kantor (disimpan di `layout.json`) |
| Edit SOUL.md * | Membaca dan menulis `SOUL.md` profil (cadangan `SOUL.md.bak`) |
| Kelola skill & tool | Membuka dashboard Hermes di tab baru (isi URL di Pengaturan atau `HERMES_DASHBOARD_URL`) |
| Salin perintah CLI | Menyalin `hermes -p <profil>` |
| Ganti nama * | Nama tampilan di kantor, atau `hermes profile rename` (ID profil; pemetaan divisi ikut dipindahkan) |
| Divisi dan tampilan | Pindah divisi, kembalikan bawaan |
| Hapus | Sembunyikan dari kantor, atau `hermes profile delete <profil> --yes` (harus mengetik nama profil) |

Menu bertanda `*` mengubah server Hermes, jadi **mati secara bawaan**. Aktifkan dengan `BRIDGE_ADMIN=1` di `~/.hermes/hermes-pixel-office/config.env` (wajib punya password atau akses dari komputer server), lalu mulai ulang Hermes. Bila perintah `hermes` tidak ada di PATH layanan, isi `HERMES_BIN=/path/ke/hermes`. Agent manual dan subagent hanya punya menu kantor (deskripsi, nama tampilan, divisi, hapus).

## Chat
Isi **Endpoint chat (URL)** dengan `/chat`. Bila halaman dibuka lewat server Anda, kolom ini terisi otomatis. Server meneruskan pesan ke API server Hermes, dan kunci API tidak pernah sampai ke browser. Agar chat membalas, aktifkan API server Hermes:

1. Di `~/.hermes/.env` tambahkan `API_SERVER_ENABLED=true` dan `API_SERVER_KEY=<kunci acak>`, lalu mulai ulang gateway (`hermes gateway`).
2. Di `~/.hermes/hermes-pixel-office/config.env` tambahkan `HERMES_API_URL=http://127.0.0.1:8642` dan `HERMES_API_KEY=<kunci yang sama>`.
3. Mulai ulang Hermes. Tanpa password, chat tetap mati (lihat bagian password).

Satu API server melayani satu profil. Agar chat sampai ke profil yang dipilih, beri tiap profil port API server sendiri, lalu buat `~/.hermes/hermes-pixel-office/chat_targets.json`:
```json
{"content-manager": {"url": "http://127.0.0.1:8643", "key": "KUNCI_PROFIL_INI"},
 "*": {"url": "http://127.0.0.1:8642", "key": "KUNCI_DEFAULT"}}
```
Profil yang tidak tercantum memakai entri `"*"` atau `HERMES_API_URL`. Jalankan `chmod 600` pada berkas ini karena berisi kunci.

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
