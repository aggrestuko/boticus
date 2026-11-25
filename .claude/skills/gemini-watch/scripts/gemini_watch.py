#!/usr/bin/env python3
"""Ask Gemini about a video. Gemini ingests YouTube URLs natively (audio + visuals),
so nothing is downloaded locally. Local files up to ~20 MB are sent inline.

Usage:
  gemini_watch.py <youtube-url-or-local-file> [--prompt "..."] [--start 1:30] [--end 3:00]
                  [--fps 1] [--model gemini-2.5-flash] [--out answer.md]

Key: GEMINI_API_KEY (or GOOGLE_API_KEY) from the environment, or from
~/.config/gemini/.env. Free key: https://aistudio.google.com/apikey
Pure stdlib.
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
INLINE_LIMIT = 20 * 1024 * 1024
DEFAULT_PROMPT = (
    "Watch this video carefully, using both the audio and the visuals. Produce:\n"
    "1. A one-paragraph summary.\n"
    "2. A timestamped (MM:SS) breakdown of every distinct step, technique or idea.\n"
    "3. Anything shown on screen but not said aloud (settings, menus, values, shortcuts, text overlays).\n"
    "4. A checklist of concrete, reusable rules someone could apply without rewatching."
)


def load_key() -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(name, "").strip():
            return os.environ[name].strip()
    env = Path.home() / ".config" / "gemini" / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            k, _, v = line.strip().partition("=")
            if k.strip() in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and v.strip():
                return v.strip().strip("'\"")
    return None


def to_seconds(t: str | None) -> str | None:
    if not t:
        return None
    secs = 0
    for part in t.split(":"):
        secs = secs * 60 + int(float(part))
    return f"{secs}s"


def video_part(source: str, start: str | None, end: str | None, fps: float | None) -> dict:
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        part: dict = {"file_data": {"file_uri": source}}
    else:
        p = Path(source).expanduser().resolve()
        if not p.exists():
            raise SystemExit(f"File not found: {p}")
        if p.stat().st_size > INLINE_LIMIT:
            raise SystemExit(
                f"{p.name} is over 20 MB. Upload it to YouTube (unlisted is fine) and pass the URL, "
                "or use the /watch skill, which works on local files of any size."
            )
        mime = mimetypes.guess_type(p.name)[0] or "video/mp4"
        part = {"inline_data": {"mime_type": mime, "data": base64.b64encode(p.read_bytes()).decode()}}
    meta = {}
    if to_seconds(start):
        meta["start_offset"] = to_seconds(start)
    if to_seconds(end):
        meta["end_offset"] = to_seconds(end)
    if fps:
        meta["fps"] = fps
    if meta:
        part["video_metadata"] = meta
    return part


def ask(source: str, prompt: str, model: str, start=None, end=None, fps=None) -> str:
    key = load_key()
    if not key:
        raise SystemExit(
            "No GEMINI_API_KEY found. Get a free key at https://aistudio.google.com/apikey and set it "
            "as GEMINI_API_KEY (environment) or in ~/.config/gemini/.env."
        )
    body = json.dumps({
        "contents": [{"parts": [video_part(source, start, end, fps), {"text": prompt}]}],
    }).encode()
    req_url = f"{API_ROOT}/{model}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": key}

    for attempt in range(4):
        try:
            with urlopen(Request(req_url, data=body, headers=headers, method="POST"), timeout=600) as r:
                data = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:600]
            if exc.code in (429, 500, 503) and attempt < 3:
                delay = 5 * (2 ** attempt)
                print(f"[gemini-watch] HTTP {exc.code}, retrying in {delay}s", file=sys.stderr)
                time.sleep(delay)
                continue
            raise SystemExit(f"Gemini request failed: HTTP {exc.code}: {detail}")

    candidates = data.get("candidates") or []
    if not candidates:
        raise SystemExit(f"Gemini returned no answer: {json.dumps(data)[:600]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise SystemExit(f"Gemini returned an empty answer (finishReason={candidates[0].get('finishReason')})")
    return text


def main() -> int:
    ap = argparse.ArgumentParser(prog="gemini_watch", description=__doc__.splitlines()[0])
    ap.add_argument("source", help="YouTube URL or local video file (<20 MB)")
    ap.add_argument("--prompt", default=DEFAULT_PROMPT, help="What to ask about the video")
    ap.add_argument("--start", help="Clip start (SS, MM:SS, HH:MM:SS)")
    ap.add_argument("--end", help="Clip end (SS, MM:SS, HH:MM:SS)")
    ap.add_argument("--fps", type=float, help="Frame sampling rate (default 1; raise for fast cuts)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model (default {DEFAULT_MODEL})")
    ap.add_argument("--out", help="Also write the answer to this file")
    args = ap.parse_args()

    answer = ask(args.source, args.prompt, args.model, args.start, args.end, args.fps)
    if args.out:
        Path(args.out).write_text(answer + "\n", encoding="utf-8")
    print(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
