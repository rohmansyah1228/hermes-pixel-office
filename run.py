#!/usr/bin/env python3
"""Jalankan server sendiri (tanpa plugin), mis. untuk layanan systemd. Lihat install.sh."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).resolve().parent / "hermes_bridge.py"), run_name="__main__")
