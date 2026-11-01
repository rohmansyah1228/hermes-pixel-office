"""Plugin Hermes: Hermes Pixel Office.

Hook mencatat aktivitas agent ke ~/.hermes/hermes-pixel-office/events.jsonl dan plugin
menyalakan server web kecil (bawaan http://127.0.0.1:8114). Hook tidak pernah boleh
membuat Hermes error atau lambat, jadi semuanya dibungkus try/except.
"""
import importlib.util
import json
import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)
HERE = Path(__file__).resolve().parent
_lock = threading.Lock()
_started = False
MAX_BYTES = 5_000_000


def _home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or "~/.hermes").expanduser()


def _root() -> Path:
    h = _home()
    return h.parent.parent if h.parent.name == "profiles" else h


def _profile() -> str:
    h = _home()
    return h.name if h.parent.name == "profiles" else "default"


def _events_path() -> Path:
    return Path(os.environ.get("HERMES_EVENTS") or _root() / "hermes-pixel-office" / "events.jsonl")


def _publish(ev: dict) -> None:
    try:
        p = _events_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        ev["t"] = time.time()
        ev["profile"] = _profile()
        line = json.dumps(ev, ensure_ascii=False) + "\n"
        with _lock:
            if p.exists() and p.stat().st_size > MAX_BYTES:
                keep = p.read_bytes()[-1_000_000:]
                keep = keep[keep.find(b"\n") + 1:]
                p.write_bytes(keep)
            with open(p, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        pass


def _preview(args) -> str:
    if isinstance(args, dict):
        for k in ("command", "path", "query", "url", "goal", "pattern", "prompt"):
            if args.get(k):
                return str(args[k])[:80]
    return ""


def _on_session_start(**kw):
    _publish({"event": "session_start", "session_id": str(kw.get("session_id") or ""), "platform": kw.get("platform")})


def _on_session_end(**kw):
    _publish({"event": "session_end", "session_id": str(kw.get("session_id") or "")})


def _pre_tool_call(**kw):
    _publish({"event": "tool_start", "session_id": str(kw.get("session_id") or ""), "tool_name": kw.get("tool_name"),
              "preview": _preview(kw.get("args"))})


def _post_tool_call(**kw):
    _publish({"event": "tool_end", "session_id": str(kw.get("session_id") or ""), "tool_name": kw.get("tool_name"),
              "status": kw.get("status") or "ok", "error_message": str(kw.get("error_message") or "")[:120] or None})


def _subagent_start(**kw):
    _publish({"event": "subagent_start", "parent_session_id": str(kw.get("parent_session_id") or ""),
              "child_session_id": str(kw.get("child_session_id") or ""), "child_role": kw.get("child_role"),
              "child_goal": str(kw.get("child_goal") or "")[:120]})


def _subagent_stop(**kw):
    _publish({"event": "subagent_stop", "child_session_id": str(kw.get("child_session_id") or "")})


def _start_server() -> None:
    global _started
    if _started or os.environ.get("HPO_NO_SERVER") == "1":
        return
    _started = True
    try:
        spec = importlib.util.spec_from_file_location("hermes_pixel_office_bridge", HERE / "hermes_bridge.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        srv = mod.make_server()
    except OSError:
        logger.info("hermes-pixel-office: port sudah dipakai proses Hermes lain; server tidak dinyalakan lagi")
        return
    except Exception as exc:
        logger.warning("hermes-pixel-office: server gagal dinyalakan: %s", exc)
        return
    threading.Thread(target=srv.serve_forever, name="hermes-pixel-office", daemon=True).start()
    logger.info("hermes-pixel-office aktif: http://%s:%s/", mod.HOST, mod.PORT)


def register(ctx) -> None:
    for name, cb in (("on_session_start", _on_session_start), ("on_session_end", _on_session_end),
                     ("pre_tool_call", _pre_tool_call), ("post_tool_call", _post_tool_call),
                     ("subagent_start", _subagent_start), ("subagent_stop", _subagent_stop)):
        try:
            ctx.register_hook(name, cb)
        except Exception as exc:
            logger.warning("hermes-pixel-office: hook %s tidak terdaftar: %s", name, exc)
    _start_server()
