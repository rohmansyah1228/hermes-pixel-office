# Changelog

## 1.0.0
- Tampilan retro dan responsif (menu samping kanan di desktop, satu kolom di HP).
- Bridge membaca data Hermes langsung: API server Hermes (`/api/sessions`), database sesi `~/.hermes/state.db`, atau agent-office (`/state`). Agent-office tidak lagi wajib.
- Chat ke agent lewat API server Hermes (`/v1/chat/completions`); kunci API tetap di server.
- Token akses `BRIDGE_TOKEN` (cookie) untuk domain publik; chat dimatikan tanpa token.
- Halaman otomatis memakai `/feed` dan `/chat` saat dibuka lewat bridge.
- `install.sh` dan unit systemd.
