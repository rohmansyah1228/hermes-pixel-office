# Changelog

## 1.2.0
- Satu profil Hermes = satu agent (bukan lagi satu sesi = satu agent). Token, biaya, dan aktivitas dibaca dari `state.db` tiap profil; subagent tampil sebagai agent tambahan.
- Divisi diatur lewat `divisions.json`; `python3 hermes_bridge.py --diag` untuk memeriksa deteksi; `HERMES_VIEW=sessions` memulihkan tampilan lama.

## 1.1.0
- Login dengan password (sesi habis setelah tidak aktif) menggantikan token; tombol Keluar; `python3 install.py --set-password`.
- Dipasang sebagai plugin Hermes lewat `python3 install.py` (pola yang sama dengan agent-office): `plugin.yaml`, hook sesi/tool/subagent, server web di dalam Hermes.
- Status waktu nyata dari hook (tool aktif, error, subagent) digabung dengan data sesi.
- `config.env` di `~/.hermes/hermes-pixel-office/`; `run.py` untuk menjalankan tanpa plugin.

## 1.0.0
- Tampilan retro dan responsif (menu samping kanan di desktop, satu kolom di HP).
- Bridge membaca data Hermes langsung: API server Hermes (`/api/sessions`), database sesi `~/.hermes/state.db`, atau agent-office (`/state`). Agent-office tidak lagi wajib.
- Chat ke agent lewat API server Hermes (`/v1/chat/completions`); kunci API tetap di server.
- Token akses `BRIDGE_TOKEN` (cookie) untuk domain publik; chat dimatikan tanpa token.
- Halaman otomatis memakai `/feed` dan `/chat` saat dibuka lewat bridge.
- `install.sh` dan unit systemd.
