"""Create or update a GitHub Release for AlapCompressor (uploads AlapCompressor.exe and AlapCompressor-Windows.zip).

Usage:
    python scripts/release.py            # creates or updates release for v1.0.0
    python scripts/release.py v1.0.0     # creates or updates release for tag v1.0.0
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "ralfarris/AlapCompressor"
API_BASE = f"https://api.github.com/repos/{REPO}"
DEFAULT_TAG = "v1.0.0"


def get_github_token() -> str:
    for env_key in ("GH_TOKEN", "GITHUB_TOKEN"):
        if os.environ.get(env_key):
            return os.environ[env_key].strip()
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True,
        check=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("Could not obtain GitHub token from git credential helper or GH_TOKEN.")


def build_artifacts() -> list[Path]:
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "build.ps1")],
        cwd=ROOT,
        check=True,
    )
    exe_path = ROOT / "dist" / "AlapCompressor.exe"
    if not exe_path.exists():
        raise FileNotFoundError(f"Expected built executable at {exe_path}")

    zip_path = ROOT / "dist" / "AlapCompressor-Windows.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.write(exe_path, arcname="AlapCompressor.exe")

    return [exe_path, zip_path]


def gh_request(
    method: str,
    url: str,
    token: str,
    data: dict | bytes | None = None,
    content_type: str = "application/json",
) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "AlapCompressor-Release-Script",
    }
    body = None
    if isinstance(data, dict):
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = content_type
    elif isinstance(data, bytes):
        body = data
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    # Bypass any sandbox proxy env vars if present
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8")) if raw else {}


def ensure_tag_pushed(tag: str) -> None:
    subprocess.run(["git", "tag", "-f", tag], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "-f", "origin", tag], cwd=ROOT, check=True)


def release_notes(tag: str) -> str:
    return (
        f"## AlapCompressor {tag}\n\n"
        "Aplikasi kompresi file **PDF, MP4, dan Word (`.docx`)** super ringan untuk Windows "
        "(~140 KB single-file `.exe` dengan antarmuka studio *soft pastel editorial*, ramah di mata).\n\n"
        "### Fitur Utama\n"
        "- **Single-File Portable (`AlapCompressor.exe`)**: Cukup 1 file `.exe`, langsung jalan dengan ikon di *System Tray*.\n"
        "- **4 Fitur Utama (Kompresi & Crop Video)**:\n"
        "  - **Compress PDF (`.pdf`)**: Optimasi gambar tertanam & pemadatan *stream* dokumen.\n"
        "  - **Compress MP4 (`.mp4`)**: Kompresi video & audio H.264 adaptif.\n"
        "  - **Compress Word (`.docx`)**: Optimasi media gambar di `word/media/` & struktur XML.\n"
        "  - **Crop Video (`.mp4`)**: Potong area bingkai layar video (`1:1`, `9:16`, `16:9`, `4:3`, `Tengah 75%`, atau geser bebas) & durasi awal–akhir dengan opsi **Murni Crop Saja (*Kualitas Asli*)** tanpa harus dikompresi.\n"
        "- **3 Opsi Hasil Kompresi Sekaligus (Perbandingan *Before vs After* Interaktif)**:\n"
        "  1. **Ukuran Paling Minim (*Paling Kecil*)**\n"
        "  2. **Balanced (*Seimbang / Rekomendasi*)**\n"
        "  3. **Kompres Sedikit (*Mendekati Utama*)**\n"
        "- **Animasi Loading Screen & *Compression Theater***.\n\n"
        "### Cara Pakai\n"
        "1. Download **`AlapCompressor.exe`** (atau `AlapCompressor-Windows.zip`) di bagian **Assets** di bawah.\n"
        "2. Klik dua kali **`AlapCompressor.exe`** — antarmuka aplikasi akan otomatis terbuka.\n"
    )


def create_or_update_release(tag: str) -> str:
    token = get_github_token()
    artifacts = build_artifacts()
    ensure_tag_pushed(tag)

    payload = {
        "tag_name": tag,
        "target_commitish": "main",
        "name": f"AlapCompressor {tag}",
        "body": release_notes(tag),
        "draft": False,
        "prerelease": False,
    }

    try:
        rel = gh_request("GET", f"{API_BASE}/releases/tags/{tag}", token)
        rel = gh_request("PATCH", f"{API_BASE}/releases/{rel['id']}", token, payload)
        action = "Updated"
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        rel = gh_request("POST", f"{API_BASE}/releases", token, payload)
        action = "Created"

    existing_assets = {a.get("name"): a.get("id") for a in rel.get("assets", [])}
    for artifact in artifacts:
        if artifact.name in existing_assets:
            gh_request("DELETE", f"{API_BASE}/releases/assets/{existing_assets[artifact.name]}", token)
        upload_url = rel["upload_url"].split("{", 1)[0] + f"?name={artifact.name}"
        ctype = "application/zip" if artifact.suffix.lower() == ".zip" else "application/octet-stream"
        gh_request("POST", upload_url, token, artifact.read_bytes(), content_type=ctype)
        print(f"Uploaded asset: {artifact.name} ({artifact.stat().st_size} bytes)")

    print(f"{action} release {tag}: {rel['html_url']}")
    return rel["html_url"]


if __name__ == "__main__":
    target_tag = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TAG
    if not target_tag.startswith("v"):
        target_tag = f"v{target_tag}"
    create_or_update_release(target_tag)
