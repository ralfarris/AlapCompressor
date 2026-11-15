import io
import json
import mimetypes
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
import zipfile
from email.parser import BytesParser
from email.policy import default as email_default_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import imageio_ffmpeg
import numpy as np
import pypdf
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMP_JOBS_DIR = BASE_DIR / "temp_jobs"
TEMP_JOBS_DIR.mkdir(exist_ok=True)

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

TIER_ORDER = ("minim", "balanced", "light")

TIER_META = {
    "minim": {
        "id": "minim",
        "title": "Ukuran Paling Minim",
        "badge": "Paling Kecil",
        "desc": "Kompresi maksimal hingga ukuran terkecil tanpa merusak struktur & keterbacaan file.",
    },
    "balanced": {
        "id": "balanced",
        "title": "Balanced (Seimbang)",
        "badge": "Rekomendasi",
        "desc": "Keseimbangan ideal antara penghematan ruang penyimpanan & ketajaman kualitas visual.",
    },
    "light": {
        "id": "light",
        "title": "Kompres Sedikit",
        "badge": "Mendekati Asli",
        "desc": "Hanya memangkas beban berlebih agar ukuran sedikit lebih ringan dengan kualitas mendekati file utama.",
    },
}

# In-memory job store
JOBS = {}
JOBS_LOCK = threading.Lock()


def update_job(job_id, **kwargs):
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(kwargs)


def get_job(job_id):
    with JOBS_LOCK:
        return dict(JOBS.get(job_id, {}))


def cleanup_old_jobs(max_age_seconds=3600):
    now = time.time()
    with JOBS_LOCK:
        expired = [
            jid for jid, data in JOBS.items()
            if now - data.get("created_at", now) > max_age_seconds
        ]
        for jid in expired:
            job_dir = TEMP_JOBS_DIR / jid
            shutil.rmtree(job_dir, ignore_errors=True)
            del JOBS[jid]


# ---------------------------------------------------------------------------
# Sample File Generators (so user can test MP4, PDF, and Word immediately)
# ---------------------------------------------------------------------------
def generate_sample_pdf() -> bytes:
    """Create a multi-page colorful PDF with high-resolution embedded images."""
    pages_pil = []
    palettes = [
        ((238, 246, 244), (42, 157, 143), (231, 111, 81)),
        ((242, 244, 251), (69, 123, 157), (244, 162, 97)),
        ((252, 243, 238), (224, 109, 83), (42, 157, 143)),
    ]
    rng = np.random.default_rng(42)
    for bg, c1, c2 in palettes:
        noise = rng.integers(0, 28, (1600, 1200, 3), dtype=np.uint8)
        base = np.full((1600, 1200, 3), bg, dtype=np.uint8)
        arr = np.clip(base.astype(np.int16) - noise.astype(np.int16), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr, mode="RGB")
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([80, 80, 1120, 420], radius=36, fill=c1)
        draw.rounded_rectangle([80, 480, 1120, 980], radius=36, fill=c2)
        draw.rounded_rectangle([80, 1040, 1120, 1500], radius=36, fill=(255, 255, 255))
        for r in range(6):
            x0 = 140 + r * 160
            draw.ellipse([x0, 1150, x0 + 110, 1260], fill=c1 if r % 2 == 0 else c2)
        pages_pil.append(img)

    buf = io.BytesIO()
    pages_pil[0].save(
        buf,
        format="PDF",
        save_all=True,
        append_images=pages_pil[1:],
        resolution=150.0,
    )
    return buf.getvalue()


def generate_sample_docx() -> bytes:
    """Create a valid Microsoft Word (.docx) document containing high-res uncompressed PNG media."""
    rng = np.random.default_rng(99)
    img_buffers = []
    colors = [((69, 123, 157), (168, 218, 220)), ((224, 109, 83), (244, 162, 97))]
    for c1, c2 in colors:
        grad = np.zeros((700, 1000, 3), dtype=np.uint8)
        for y in range(700):
            ratio = y / 700.0
            grad[y, :, 0] = int(c1[0] * (1 - ratio) + c2[0] * ratio)
            grad[y, :, 1] = int(c1[1] * (1 - ratio) + c2[1] * ratio)
            grad[y, :, 2] = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        noise = rng.integers(0, 35, (700, 1000, 3), dtype=np.uint8)
        arr = np.clip(grad.astype(np.int16) + noise.astype(np.int16), 0, 255).astype(np.uint8)
        pil_img = Image.fromarray(arr, mode="RGB")
        ibuf = io.BytesIO()
        pil_img.save(ibuf, format="PNG", compress_level=1)
        img_buffers.append(ibuf.getvalue())

    content_types_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="jpeg" ContentType="image/jpeg"/>
  <Default Extension="jpg" ContentType="image/jpeg"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdImg1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
  <Relationship Id="rIdImg2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/>
</Relationships>"""

    paragraphs = "\n".join(
        f'    <w:p><w:r><w:t>AlapCompressor Sample Word Document — Bagian #{i}: '
        f'Dokumen ini memiliki gambar beresolusi tinggi dan struktur XML untuk menguji 3 opsi kompresi Word secara nyata.</w:t></w:r></w:p>'
        for i in range(1, 25)
    )

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Laporan Visual AlapCompressor (Sample .DOCX)</w:t></w:r></w:p>
{paragraphs}
  </w:body>
</w:document>"""

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("[Content_Types].xml", content_types_xml)
        zf.writestr("_rels/.rels", rels_xml)
        zf.writestr("word/_rels/document.xml.rels", doc_rels_xml)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/media/image1.png", img_buffers[0])
        zf.writestr("word/media/image2.png", img_buffers[1])
    return out.getvalue()


def generate_sample_mp4() -> bytes:
    """Create a high-bitrate 3-second colorful MP4 video using FFmpeg testsrc2."""
    tmp_path = TEMP_JOBS_DIR / f"sample_{uuid.uuid4().hex[:8]}.mp4"
    try:
        cmd = [
            FFMPEG_EXE,
            "-y",
            "-loglevel", "error",
            "-f", "lavfi",
            "-i", "testsrc2=size=1280x720:rate=30:duration=3",
            "-f", "lavfi",
            "-i", "sine=frequency=440:duration=3",
            "-c:v", "libx264",
            "-crf", "14",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(tmp_path),
        ]
        subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True,
        )
        return tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Single-Tier Compression Helpers for MP4, PDF, and Word
# ---------------------------------------------------------------------------
def compress_mp4_single_tier(
    input_path: Path,
    output_path: Path,
    tier: str,
    duration_sec: float,
    orig_size: int,
    progress_cb=None,
):
    # Calculate original bitrate so we can guarantee distinct, well-spaced sizes across all 3 options
    orig_total_bps = int((orig_size * 8) / max(duration_sec, 0.5)) if duration_sec > 0 else 1_500_000

    if tier == "minim":
        # Smallest safe size (~22-30% of original, 480p widescreen max)
        scale_filter = "scale='min(854,iw)':-2"
        audio_br = "64k"
        audio_bps = 64_000
        ratio_cap = 0.25
    elif tier == "balanced":
        # Balanced middle ground (~50-55% of original, 720p HD max)
        scale_filter = "scale='min(1280,iw)':-2"
        audio_br = "112k"
        audio_bps = 112_000
        ratio_cap = 0.52
    else:  # light (Mendekati Ukuran Utama / Kompres Sedikit ~78-85% of original)
        scale_filter = "scale='min(1920,iw)':-2"
        audio_br = "160k"
        audio_bps = 160_000
        ratio_cap = 0.80

    target_total_bps = max(audio_bps + 45_000, int(orig_total_bps * ratio_cap))
    target_video_bps = max(45_000, target_total_bps - audio_bps)

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-loglevel", "error",
        "-i", str(input_path),
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-b:v", str(target_video_bps),
        "-maxrate", str(int(target_video_bps * 1.08)),
        "-bufsize", str(target_video_bps * 2),
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", audio_br,
        "-progress", "pipe:1",
        "-nostats",
        str(output_path),
    ]

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    )

    last_lines = []
    for line in proc.stdout:
        line = line.strip()
        if line:
            last_lines.append(line)
            if len(last_lines) > 10:
                last_lines.pop(0)
        if line.startswith("out_time_ms=") and duration_sec > 0 and progress_cb:
            try:
                out_ms = int(line.split("=", 1)[1])
                frac = min(1.0, max(0.0, out_ms / (duration_sec * 1_000_000)))
                progress_cb(frac)
            except ValueError:
                pass

    proc.wait()
    if proc.returncode != 0 or not output_path.exists():
        err_text = " | ".join(last_lines)
        raise RuntimeError(f"Gagal memproses file MP4 ({tier}): {err_text}")

    # If the input video was low-bitrate and CRF produced something smaller than expected for 'light' or larger than original:
    new_size = output_path.stat().st_size
    if new_size >= orig_size and duration_sec > 0:
        tight_video_bps = max(40_000, int(orig_total_bps * ratio_cap * 0.78))
        alt_path = output_path.with_name(f"tight_{tier}_{output_path.name}")
        cmd_tight = [
            FFMPEG_EXE,
            "-y",
            "-loglevel", "error",
            "-i", str(input_path),
            "-vf", scale_filter,
            "-c:v", "libx264",
            "-b:v", str(tight_video_bps),
            "-maxrate", str(int(tight_video_bps * 1.1)),
            "-bufsize", str(int(tight_video_bps * 2)),
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-c:a", "aac",
            "-b:a", "64k",
            str(alt_path),
        ]
        subprocess.run(
            cmd_tight,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if alt_path.exists() and alt_path.stat().st_size < new_size:
            shutil.move(str(alt_path), str(output_path))
        elif alt_path.exists():
            alt_path.unlink(missing_ok=True)


def compress_pdf_single_tier(input_path: Path, output_path: Path, tier: str, progress_cb=None):
    cfg = {
        "minim": {"max_dim": 720, "quality": 28, "deflate": 9, "strip_meta": True},
        "balanced": {"max_dim": 1220, "quality": 54, "deflate": 9, "strip_meta": False},
        "light": {"max_dim": 1520, "quality": 70, "deflate": 6, "strip_meta": False},
    }[tier]

    writer = pypdf.PdfWriter(clone_from=str(input_path))
    total_pages = max(1, len(writer.pages))

    for idx, page in enumerate(writer.pages):
        if progress_cb:
            progress_cb((idx + 1) / total_pages)
        try:
            for img_file in page.images:
                try:
                    pil_img = img_file.image
                    if pil_img is None:
                        continue
                    w, h = pil_img.size
                    max_d = cfg["max_dim"]
                    if max(w, h) > max_d:
                        scale = max_d / float(max(w, h))
                        pil_img = pil_img.resize(
                            (max(1, int(w * scale)), max(1, int(h * scale))),
                            Image.Resampling.LANCZOS,
                        )
                    if pil_img.mode not in ("RGB", "L"):
                        pil_img = pil_img.convert("RGB")
                    img_file.replace(pil_img, quality=cfg["quality"])
                except Exception:
                    continue
        except Exception:
            pass

        try:
            page.compress_content_streams(level=cfg["deflate"])
        except Exception:
            pass

    if cfg["strip_meta"]:
        try:
            writer.metadata = {}
        except Exception:
            pass

    try:
        if tier in ("minim", "balanced"):
            writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
        else:
            writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=False)
    except TypeError:
        writer.compress_identical_objects()

    with open(output_path, "wb") as f_out:
        writer.write(f_out)

    if output_path.stat().st_size > input_path.stat().st_size:
        shutil.copyfile(input_path, output_path)


def compress_word_single_tier(input_path: Path, output_path: Path, tier: str, progress_cb=None):
    cfg = {
        "minim": {"max_dim": 680, "quality": 30, "colors": 32, "zip_level": 9, "clean_xml": True},
        "balanced": {"max_dim": 1250, "quality": 58, "colors": 128, "zip_level": 7, "clean_xml": True},
        "light": {"max_dim": 1950, "quality": 88, "colors": None, "zip_level": 3, "clean_xml": False},
    }[tier]

    if not zipfile.is_zipfile(input_path):
        raise ValueError("Format file Word harus berupa dokumen .docx yang valid.")

    with zipfile.ZipFile(input_path, "r") as zin:
        infos = zin.infolist()
        total_items = max(1, len(infos))

        with zipfile.ZipFile(
            output_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=cfg["zip_level"],
        ) as zout:
            for idx, item in enumerate(infos):
                if progress_cb:
                    progress_cb((idx + 1) / total_items)
                raw_data = zin.read(item.filename)
                lower_name = item.filename.lower()

                if lower_name.startswith("word/media/") and lower_name.endswith(
                    (".png", ".jpg", ".jpeg", ".bmp", ".tiff")
                ):
                    try:
                        pil_img = Image.open(io.BytesIO(raw_data))
                        w, h = pil_img.size
                        if max(w, h) > cfg["max_dim"]:
                            scale = cfg["max_dim"] / float(max(w, h))
                            pil_img = pil_img.resize(
                                (max(1, int(w * scale)), max(1, int(h * scale))),
                                Image.Resampling.LANCZOS,
                            )
                        out_buf = io.BytesIO()
                        if lower_name.endswith((".jpg", ".jpeg")):
                            if pil_img.mode != "RGB":
                                pil_img = pil_img.convert("RGB")
                            pil_img.save(
                                out_buf,
                                format="JPEG",
                                quality=cfg["quality"],
                                optimize=True,
                            )
                        elif lower_name.endswith(".png"):
                            if cfg["colors"] is not None:
                                if pil_img.mode not in ("RGB", "RGBA", "P"):
                                    pil_img = pil_img.convert("RGBA")
                                quantized = pil_img.quantize(
                                    colors=cfg["colors"],
                                    method=Image.Quantize.FASTOCTREE,
                                )
                                quantized.save(
                                    out_buf,
                                    format="PNG",
                                    optimize=True,
                                    compress_level=cfg["zip_level"],
                                )
                            else:
                                # Light tier: gentle lossless PNG re-save without aggressive palette reduction
                                pil_img.save(
                                    out_buf,
                                    format="PNG",
                                    compress_level=2,
                                )
                        else:
                            pil_img.save(out_buf, format=pil_img.format or "PNG", optimize=True)

                        candidate = out_buf.getvalue()
                        if len(candidate) < len(raw_data):
                            raw_data = candidate
                    except Exception:
                        pass
                elif cfg["clean_xml"] and (lower_name.endswith(".xml") or lower_name.endswith(".rels")):
                    try:
                        xml_text = raw_data.decode("utf-8")
                        cleaned = re.sub(r">\s+<", "><", xml_text.strip())
                        raw_data = cleaned.encode("utf-8")
                    except Exception:
                        pass

                zout.writestr(item.filename, raw_data)


# ---------------------------------------------------------------------------
# Multi-Tier Job Runner (Generates all 3 options: minim, balanced, light)
# ---------------------------------------------------------------------------
def run_compression_worker(job_id: str, file_type: str, selected_tier: str, input_path: Path, job_dir: Path, orig_filename: str):
    start_time = time.time()
    try:
        orig_size = input_path.stat().st_size
        stem = Path(orig_filename).stem
        out_ext = {"mp4": ".mp4", "pdf": ".pdf", "word": ".docx"}.get(file_type, Path(orig_filename).suffix or ".bin")

        update_job(
            job_id,
            status="processing",
            progress=8,
            stage="Menganalisis struktur file & menyiapkan 3 opsi kompresi...",
        )

        duration_sec = 0.0
        if file_type == "mp4":
            probe = subprocess.run(
                [FFMPEG_EXE, "-i", str(input_path)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
            )
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr)
            if m:
                duration_sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

        variants = {}
        tier_ranges = {
            "minim": (10, 42, "Meracik Opsi 1/3: Ukuran Paling Minim (Kompresi Maksimal Aman)..."),
            "balanced": (42, 72, "Meracik Opsi 2/3: Balanced (Seimbang Kualitas & Ukuran)..."),
            "light": (72, 95, "Meracik Opsi 3/3: Kompres Sedikit (Mendekati Ukuran Utama)..."),
        }

        for tier in TIER_ORDER:
            p_start, p_end, stage_msg = tier_ranges[tier]
            update_job(job_id, progress=p_start, stage=stage_msg)

            tier_filename = f"{stem}-{tier}{out_ext}"
            tier_out_path = job_dir / tier_filename

            def make_cb(ps, pe, msg):
                def _cb(frac):
                    pct = int(ps + frac * (pe - ps))
                    update_job(job_id, progress=min(96, max(ps, pct)), stage=msg)
                return _cb

            cb = make_cb(p_start, p_end, stage_msg)

            if file_type == "mp4":
                compress_mp4_single_tier(input_path, tier_out_path, tier, duration_sec, orig_size, cb)
            elif file_type == "pdf":
                compress_pdf_single_tier(input_path, tier_out_path, tier, cb)
            elif file_type == "word":
                compress_word_single_tier(input_path, tier_out_path, tier, cb)
            else:
                raise ValueError(f"Tipe kompresi tidak dikenali: {file_type}")

            c_size = tier_out_path.stat().st_size
            saved_b = max(0, orig_size - c_size)
            saved_p = round((saved_b / orig_size) * 100, 1) if orig_size > 0 else 0.0

            variants[tier] = {
                "tier": tier,
                "title": TIER_META[tier]["title"],
                "badge": TIER_META[tier]["badge"],
                "desc": TIER_META[tier]["desc"],
                "compressed_size": c_size,
                "saved_bytes": saved_b,
                "saved_percent": saved_p,
                "download_name": tier_filename,
                "output_path": str(tier_out_path),
            }

        elapsed = round(time.time() - start_time, 2)
        chosen = variants.get(selected_tier) or variants["balanced"]

        update_job(
            job_id,
            status="done",
            progress=100,
            stage="Selesai! Ketiga opsi kompresi siap dipilih & diunduh.",
            original_size=orig_size,
            compressed_size=chosen["compressed_size"],
            saved_bytes=chosen["saved_bytes"],
            saved_percent=chosen["saved_percent"],
            download_name=chosen["download_name"],
            output_path=chosen["output_path"],
            selected_tier=selected_tier if selected_tier in variants else "balanced",
            variants=variants,
            elapsed_seconds=elapsed,
        )
    except Exception as exc:
        update_job(
            job_id,
            status="error",
            progress=100,
            stage="Terjadi kendala saat mengompresi file.",
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Multipart Parser Helper
# ---------------------------------------------------------------------------
def parse_multipart_form(headers, body: bytes):
    content_type = headers.get("Content-Type", "")
    raw_msg = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
    msg = BytesParser(policy=email_default_policy).parsebytes(raw_msg)
    fields = {}
    files = {}
    if msg.is_multipart():
        for part in msg.iter_parts():
            cd = part.get("Content-Disposition", "")
            name_m = re.search(r'name="([^"]+)"', cd)
            if not name_m:
                continue
            field_name = name_m.group(1)
            fn_m = re.search(r'filename="([^"]*)"', cd)
            payload = part.get_payload(decode=True) or b""
            if fn_m:
                files[field_name] = {
                    "filename": fn_m.group(1),
                    "content": payload,
                    "content_type": part.get_content_type(),
                }
            else:
                fields[field_name] = payload.decode("utf-8", errors="replace")
    return fields, files


# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------
class AlapCompressorHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data: dict, status: int = 200):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/status/"):
            job_id = path.split("/api/status/", 1)[1].strip("/")
            job = get_job(job_id)
            if not job:
                return self._send_json({"error": "Job tidak ditemukan"}, status=404)
            return self._send_json(job)

        if path.startswith("/api/download/"):
            parts = path.split("/api/download/", 1)[1].strip("/").split("/")
            job_id = parts[0]
            requested_tier = parts[1].lower() if len(parts) > 1 else None

            job = get_job(job_id)
            if not job or job.get("status") != "done":
                return self._send_json({"error": "File belum siap atau tidak ditemukan"}, status=404)

            variants = job.get("variants") or {}
            if requested_tier and requested_tier in variants:
                target_info = variants[requested_tier]
                out_path = Path(target_info["output_path"])
                dl_name = target_info["download_name"]
            else:
                out_path = Path(job["output_path"])
                dl_name = job.get("download_name", out_path.name)

            if not out_path.exists():
                return self._send_json({"error": "File hasil kompresi tidak ditemukan"}, status=404)

            data = out_path.read_bytes()
            mime, _ = mimetypes.guess_type(dl_name)
            self.send_response(200)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Content-Disposition", f'attachment; filename="{dl_name}"')
            self.end_headers()
            self.wfile.write(data)
            return

        if path.startswith("/api/sample/"):
            kind = path.split("/api/sample/", 1)[1].strip("/").lower()
            try:
                if kind == "pdf":
                    content = generate_sample_pdf()
                    filename = "Sample-Brosur-AlapCompressor.pdf"
                    mime = "application/pdf"
                elif kind == "word":
                    content = generate_sample_docx()
                    filename = "Sample-Laporan-AlapCompressor.docx"
                    mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif kind == "mp4":
                    content = generate_sample_mp4()
                    filename = "Sample-Video-AlapCompressor.mp4"
                    mime = "video/mp4"
                else:
                    return self._send_json({"error": "Tipe sample tidak valid"}, status=400)

                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.end_headers()
                self.wfile.write(content)
                return
            except Exception as exc:
                return self._send_json({"error": str(exc)}, status=500)

        # Serve static files
        if path == "/" or path == "":
            file_path = STATIC_DIR / "index.html"
        else:
            rel = path.lstrip("/")
            file_path = (STATIC_DIR / rel).resolve()
            if not str(file_path).startswith(str(STATIC_DIR.resolve())):
                self.send_error(403)
                return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        mime, _ = mimetypes.guess_type(str(file_path))
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/compress":
            return self._send_json({"error": "Endpoint tidak ditemukan"}, status=404)

        cleanup_old_jobs()
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            fields, files = parse_multipart_form(self.headers, body)

            if "file" not in files or not files["file"]["content"]:
                return self._send_json({"error": "Mohon pilih file terlebih dahulu."}, status=400)

            file_info = files["file"]
            orig_filename = Path(file_info["filename"] or "document").name
            file_bytes = file_info["content"]
            file_type = fields.get("file_type", "pdf").lower().strip()
            raw_level = fields.get("level", "balanced").lower().strip()
            # Map legacy level names if any
            level_map = {
                "extreme": "minim",
                "minim": "minim",
                "recommended": "balanced",
                "balanced": "balanced",
                "light": "light",
            }
            selected_tier = level_map.get(raw_level, "balanced")

            job_id = uuid.uuid4().hex[:12]
            job_dir = TEMP_JOBS_DIR / job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            input_path = job_dir / f"input_{orig_filename}"
            input_path.write_bytes(file_bytes)

            with JOBS_LOCK:
                JOBS[job_id] = {
                    "job_id": job_id,
                    "status": "queued",
                    "progress": 4,
                    "stage": "Menyiapkan ruang kerja kompresi...",
                    "original_name": orig_filename,
                    "download_name": orig_filename,
                    "original_size": len(file_bytes),
                    "compressed_size": None,
                    "saved_bytes": 0,
                    "saved_percent": 0,
                    "file_type": file_type,
                    "selected_tier": selected_tier,
                    "variants": {},
                    "output_path": "",
                    "created_at": time.time(),
                }

            worker = threading.Thread(
                target=run_compression_worker,
                args=(job_id, file_type, selected_tier, input_path, job_dir, orig_filename),
                daemon=True,
            )
            worker.start()

            return self._send_json({"job_id": job_id, "status": "queued"})
        except Exception as exc:
            return self._send_json({"error": f"Gagal memproses permintaan: {exc}"}, status=500)


def main():
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("127.0.0.1", port), AlapCompressorHandler)
    print(f"AlapCompressor server running on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
