#!/usr/bin/env python3
"""
nb-image — generate or edit images with Google's Gemini image models ("Nano Banana").

Approach: a single stdlib-only call to the Generative Language REST API. No SDK, no
pip install, so the script works from any machine that has Python 3. The API key is
read from a file outside every git repo (never from a tracked file, never from argv,
so it stays out of shell history and out of `ps` output).

Image-to-image ("--ref") matters more than it looks: passing a reference image is how
you get the SAME synthetic face across several generations, which is what you need for
a consistent demo character rather than five unrelated strangers.

Exit codes: 0 ok, 1 usage/config error, 2 API error.
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-3.1-flash-image"
KEY_PATH = os.path.expanduser("~/.config/gemini/api_key")


def load_key():
    """Env var wins; otherwise the 600-mode file. Never accepted on the command line."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    if not os.path.exists(KEY_PATH):
        sys.exit(
            f"error: no API key.\n"
            f"  Create one at https://aistudio.google.com/apikey (attach it to your GCP\n"
            f"  project so you are on paid terms), then:\n"
            f"    mkdir -p ~/.config/gemini\n"
            f"    printf '%s' 'YOUR_KEY' > {KEY_PATH}\n"
            f"    chmod 600 {KEY_PATH}"
        )
    with open(KEY_PATH) as fh:
        return fh.read().strip()


def inline_image(path):
    """Read a local image into the inlineData part shape the API expects."""
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as fh:
        return {"inlineData": {"mimeType": mime, "data": base64.b64encode(fh.read()).decode()}}


def generate(key, model, prompt, refs):
    parts = [inline_image(p) for p in refs]
    parts.append({"text": prompt})
    req = urllib.request.Request(
        API.format(model=model),
        data=json.dumps({"contents": [{"parts": parts}]}).encode(),
        headers={"Content-Type": "application/json", "X-goog-api-key": key},
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            msg = json.loads(raw)["error"]["message"]
        except Exception:
            msg = raw[:400]
        # 429 here is almost never rate limiting — it is usually an empty prepaid balance.
        hint = ""
        if exc.code == 429 and "credit" in msg.lower():
            hint = "\n  hint: top up prepaid credits at https://ai.studio/projects"
        sys.exit(f"error: API returned {exc.code}\n  {msg}{hint}")


def save_images(payload, out, quiet):
    """Write every inlineData part. Multi-image responses get -1, -2 suffixes."""
    stem, ext = os.path.splitext(out)
    ext = ext or ".png"
    images, notes = [], []
    for cand in payload.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            if "inlineData" in part:
                images.append(part["inlineData"])
            elif part.get("text"):
                notes.append(part["text"].strip())

    if not images:
        why = " ".join(notes)[:300] or "no inlineData parts in response"
        sys.exit(f"error: model returned no image.\n  {why}")

    written = []
    for idx, data in enumerate(images):
        path = out if len(images) == 1 else f"{stem}-{idx + 1}{ext}"
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(data["data"]))
        written.append(path)
        if not quiet:
            print(f"{path}  {data.get('mimeType', '?')}  {os.path.getsize(path)} bytes")
    return written


def main():
    ap = argparse.ArgumentParser(
        description="Generate or edit images with Gemini image models (Nano Banana)."
    )
    ap.add_argument("prompt", help="what to generate; be specific about subject, framing, lighting")
    ap.add_argument("-o", "--out", default="out.png", help="output path (default: out.png)")
    ap.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"default: {DEFAULT_MODEL}")
    ap.add_argument("--ref", action="append", default=[],
                    help="reference image to edit or keep consistent; repeatable")
    ap.add_argument("-q", "--quiet", action="store_true")
    ap.add_argument("--list-models", action="store_true", help="show image-capable models and exit")
    args = ap.parse_args()

    key = load_key()

    if args.list_models:
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
            headers={"X-goog-api-key": key},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            for m in json.load(resp).get("models", []):
                name = m["name"].replace("models/", "")
                if "image" in name.lower():
                    print(name)
        return

    for path in args.ref:
        if not os.path.exists(path):
            sys.exit(f"error: reference image not found: {path}")

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)

    payload = generate(key, args.model, args.prompt, args.ref)
    save_images(payload, args.out, args.quiet)


if __name__ == "__main__":
    main()
