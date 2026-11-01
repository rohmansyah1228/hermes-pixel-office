# Hermes Pixel Office

Kantor pixel bertingkat untuk agent Hermes: satu divisi = satu lantai, meja/kursi/komputer mengikuti jumlah agent, klik agent untuk melihat tugas dan komputasinya, hasil bisa diunduh atau diunggah ke GitHub.

## Menjalankan
- Lokal dengan data nyata: `python3 hermes_bridge.py`, buka `http://127.0.0.1:8114/?feed=/feed` (butuh agent-office berjalan di :8113).
- GitHub Pages: Settings > Pages > Source: GitHub Actions. Mode demo jalan tanpa data.

## Chat dengan agent
Tombol **Chat** (kanan bawah, pintasan `C`) membuka panel untuk bertanya atau memberi instruksi ke agent terpilih (default: agent pertama). Mode demo membalas dengan jawaban contoh. Untuk Hermes sungguhan isi **Pengaturan > Endpoint chat (URL)**:
- `/chat` bila halaman dibuka lewat `hermes_bridge.py` dengan `CHAT_URL=<endpoint chat Hermes>`.
- URL berakhiran `/chat/completions` dikirim dalam format OpenAI; URL lain menerima `{"agent","agent_id","division","message","history"}` dan membalas `{"reply": "..."}`.

## Catatan lisensi
`index.html` memuat aset Modern Interiors/Office (LimeZu) dan peta dari hermes-town. Jaga repo ini private atau pastikan lisensi aset mengizinkan redistribusi.
