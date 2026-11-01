#!/usr/bin/env python3
"""Pasang Hermes Pixel Office sebagai plugin Hermes.

    python3 install.py              pasang + aktifkan plugin
    python3 install.py --dry-run    hanya tampilkan apa yang akan dilakukan
    python3 install.py --port 8114  ganti port (disimpan di config.env)
    python3 install.py --set-password  buat/ganti password halaman (disarankan untuk domain publik)
Bisa dijalankan ulang kapan saja.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "hermes-pixel-office"


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or "~/.hermes").expanduser()


def main(argv=()) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--set-password", action="store_true")
    args = ap.parse_args(argv)
    if args.set_password:
        sys.path.insert(0, str(HERE))
        import hermes_bridge
        return hermes_bridge.cli_set_password() or 0
    home = hermes_home()
    have_hermes = bool(shutil.which("hermes")) or (home / "config.yaml").is_file()
    dest = home / "plugins" / NAME
    print("Hermes Pixel Office install")
    print("hermes   :", "ditemukan" if have_hermes else "TIDAK ditemukan (pasang Hermes dulu, atau set HERMES_HOME)")
    print("plugin   :", dest)
    if not have_hermes:
        return 1
    if args.dry_run:
        print("Dry run: tidak ada yang diubah.")
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    mode = "tautan ke repo ini (git pull otomatis memperbarui)"
    if dest.resolve() != HERE:
        if dest.is_symlink():
            dest.unlink()
        if dest.exists():
            shutil.rmtree(dest)
        try:
            dest.symlink_to(HERE, target_is_directory=True)
        except OSError:
            mode = "salinan"
            ignore = shutil.ignore_patterns(".git", "__pycache__", "deploy", ".github")
            shutil.copytree(HERE, dest, ignore=ignore)
    print("pasang   :", mode)
    cfg = home / NAME / "config.env"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    if not cfg.exists():
        cfg.write_text(
            "# Pengaturan Hermes Pixel Office (KEY=VALUE). Mulai ulang Hermes setelah mengubah.\n"
            f"BRIDGE_PORT={args.port or 8114}\n"
            "# Password halaman: jalankan  python3 install.py --set-password\n"
            "#BRIDGE_SESSION_MINUTES=120\n"
            "# Izinkan halaman mengubah SOUL.md, model, nama, dan menghapus profil (wajib password):\n"
            "#BRIDGE_ADMIN=1\n#HERMES_DASHBOARD_URL=http://127.0.0.1:9119\n", encoding="utf-8")
        print("config   :", cfg)
    elif args.port:
        lines = [l for l in cfg.read_text(encoding="utf-8").splitlines() if not l.startswith("BRIDGE_PORT=")]
        cfg.write_text("\n".join(lines + [f"BRIDGE_PORT={args.port}"]) + "\n", encoding="utf-8")
    div = home / NAME / "divisions.json"
    ex = HERE / "deploy" / "divisions.example.json"
    if not div.exists() and ex.is_file():
        shutil.copy2(ex, div)
        print("divisi   :", div, "(ubah sesuai profil Anda; 'hidden' menyembunyikan profil)")
    try:
        r = subprocess.run(["hermes", "plugins", "enable", NAME], capture_output=True, text=True, timeout=30)
        print("enable   :", "plugin diaktifkan" if r.returncode == 0 else f"gagal ({(r.stderr or r.stdout).strip()[:120]})")
        if r.returncode != 0:
            print("           jalankan manual: hermes plugins enable", NAME)
    except Exception:
        print("enable   : jalankan manual: hermes plugins enable", NAME)
    print()
    print("Selesai. Mulai ulang Hermes agar plugin dimuat (mis. `hermes gateway restart`, atau tutup dan buka lagi `hermes`).")
    print("Buka    : http://127.0.0.1:%s/  (aktif saat Hermes berjalan)" % (args.port or 8114))
    print("Cek     : curl http://127.0.0.1:%s/health" % (args.port or 8114))
    print("Password: python3 install.py --set-password   (disarankan bila dibuka lewat domain publik)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
