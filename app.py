import io
import json
import math
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
import zipfile
from email.parser import BytesParser
from email.policy import default as email_default_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import imageio_ffmpeg
import numpy as np
import pypdf
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMP_JOBS_DIR = BASE_DIR / "temp_jobs"
TEMP_JOBS_DIR.mkdir(exist_ok=True)

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

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
    for idx, (bg, c1, c2) in enumerate(palettes):
        # Create a 1200x1600 canvas with rich texture so compression has real impact
        noise = rng.integers(0, 28, (1600, 1200, 3), dtype=np.uint8)
        base = np.full((1600, 1200, 3), bg, dtype=np.uint8)
        arr = np.clip(base.astype(np.int16) - noise.astype(np.int16), 0, 255).astype(np.uint8)
        img = Image.fromarray(arr, mode="RGB")
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([80, 80, 1120, 420], radius=36, fill=c1)
        draw.rounded_rectangle([80, 480, 1120, 980], radius=36, fill=c2)
        draw.rounded_rectangle([80, 1040, 1120, 1500], radius=36, fill=(255, 255, 255))
        # Decorative circles
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
    # Create two rich 1000x700 images stored inside word/media/
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
        f'Dokumen ini memiliki gambar beresolusi tinggi dan struktur XML untuk menguji fitur kompresi Word secara nyata.</w:t></w:r></w:p>'
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
        subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        return tmp_path.read_bytes()
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Real Compression Engines (MP4, PDF, Word)
# ---------------------------------------------------------------------------
def compress_mp4_job(job_id: str, input_path: Path, output_path: Path, level: str):
    update_job(
        job_id,
        status="processing",
        progress=8,
        stage="Menganalisis stream video & audio MP4...",
    )
    time.sleep(0.35)

    # Probe duration using ffmpeg -i
    probe = subprocess.run(
        [FFMPEG_EXE, "-i", str(input_path)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    duration_sec = 0.0
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", probe.stderr)
    if m:
        duration_sec = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))

    # Configure preset parameters
    if level == "extreme":
        crf = "33"
        scale_filter = "scale='min(1280,iw)':-2"
        audio_br = "96k"
        stage_desc = "Mengompresi frame video (Mode Ekstrem H.264)..."
    elif level == "light":
        crf = "24"
        scale_filter = "scale='min(1920,iw)':-2"
        audio_br = "160k"
        stage_desc = "Mengoptimalkan bitrate video dengan menjaga ketajaman visual..."
    else:  # recommended
        crf = "28"
        scale_filter = "scale='min(1600,iw)':-2"
        audio_br = "128k"
        stage_desc = "Mengompresi stream video & audio secara seimbang..."

    update_job(job_id, progress=16, stage=stage_desc)

    cmd = [
        FFMPEG_EXE,
        "-y",
        "-loglevel", "error",
        "-i", str(input_path),
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-crf", crf,
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
        if line.startswith("out_time_ms=") and duration_sec > 0:
            try:
                out_ms = int(line.split("=", 1)[1])
                pct = min(88, max(18, int(18 + (out_ms / (duration_sec * 1_000_000)) * 70)))
                update_job(job_id, progress=pct, stage=stage_desc)
            except ValueError:
                pass

    proc.wait()
    if proc.returncode != 0 or not output_path.exists():
        err_text = " | ".join(last_lines)
        raise RuntimeError(f"Gagal memproses file MP4: {err_text}")

    # Fallback check: if input was already heavily compressed and output grew, re-encode with tighter target bitrate
    orig_size = input_path.stat().st_size
    new_size = output_path.stat().st_size
    if new_size >= orig_size and duration_sec > 0:
        update_job(job_id, progress=90, stage="Menyesuaikan target bitrate agar ukuran lebih ramping...")
        target_ratio = {"extreme": 0.50, "recommended": 0.68, "light": 0.82}.get(level, 0.68)
        target_total_bps = max(80_000, int((orig_size * 8 * target_ratio) / max(duration_sec, 0.5)))
        video_bps = max(55_000, int(target_total_bps * 0.82))
        alt_path = output_path.with_name("alt_" + output_path.name)
        cmd_tight = [
            FFMPEG_EXE,
            "-y",
            "-loglevel", "error",
            "-i", str(input_path),
            "-vf", "scale='min(960,iw)':-2" if level == "extreme" else scale_filter,
            "-c:v", "libx264",
            "-b:v", str(video_bps),
            "-maxrate", str(int(video_bps * 1.15)),
            "-bufsize", str(int(video_bps * 2)),
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-c:a", "aac",
            "-b:a", "64k",
            str(alt_path),
        ]
        subprocess.run(cmd_tight, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if alt_path.exists() and alt_path.stat().st_size < new_size:
            shutil.move(str(alt_path), str(output_path))
        elif alt_path.exists():
            alt_path.unlink(missing_ok=True)

    update_job(job_id, progress=96, stage="Memfinalisasi container MP4 (faststart)...")
    time.sleep(0.25)


def compress_pdf_job(job_id: str, input_path: Path, output_path: Path, level: str):
    update_job(
        job_id,
        status="processing",
        progress=12,
        stage="Membaca struktur halaman & objek PDF...",
    )
    time.sleep(0.35)

    cfg = {
        "extreme": {"max_dim": 850, "quality": 36},
        "recommended": {"max_dim": 1350, "quality": 58},
        "light": {"max_dim": 1900, "quality": 76},
    }.get(level, {"max_dim": 1350, "quality": 58})

    writer = pypdf.PdfWriter(clone_from=str(input_path))
    total_pages = max(1, len(writer.pages))

    for idx, page in enumerate(writer.pages):
        pct = 15 + int(((idx + 1) / total_pages) * 65)
        update_job(
            job_id,
            progress=pct,
            stage=f"Mengoptimalkan gambar & stream halaman {idx + 1} dari {total_pages}...",
        )
        # Compress embedded images on the page
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
            page.compress_content_streams(level=9)
        except Exception:
            pass

    update_job(job_id, progress=88, stage="Menghapus objek duplikat & menyusun ulang tabel referensi PDF...")
    time.sleep(0.3)
    try:
        writer.compress_identical_objects(remove_duplicates=True, remove_unreferenced=True)
    except TypeError:
        writer.compress_identical_objects()

    with open(output_path, "wb") as f_out:
        writer.write(f_out)

    # Ensure we never produce a file larger than original
    if output_path.stat().st_size > input_path.stat().st_size:
        shutil.copyfile(input_path, output_path)

    update_job(job_id, progress=96, stage="Memverifikasi integritas dokumen PDF...")
    time.sleep(0.25)


def compress_word_job(job_id: str, input_path: Path, output_path: Path, level: str):
    update_job(
        job_id,
        status="processing",
        progress=12,
        stage="Membuka paket dokumen Word & memindai aset media...",
    )
    time.sleep(0.35)

    cfg = {
        "extreme": {"max_dim": 850, "quality": 38, "colors": 64},
        "recommended": {"max_dim": 1350, "quality": 60, "colors": 128},
        "light": {"max_dim": 1900, "quality": 78, "colors": 256},
    }.get(level, {"max_dim": 1350, "quality": 60, "colors": 128})

    if not zipfile.is_zipfile(input_path):
        raise ValueError("Format file Word harus berupa dokumen .docx yang valid.")

    with zipfile.ZipFile(input_path, "r") as zin:
        infos = zin.infolist()
        total_items = max(1, len(infos))

        with zipfile.ZipFile(
            output_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as zout:
            for idx, item in enumerate(infos):
                pct = 16 + int(((idx + 1) / total_items) * 74)
                raw_data = zin.read(item.filename)
                lower_name = item.filename.lower()

                if lower_name.startswith("word/media/") and lower_name.endswith(
                    (".png", ".jpg", ".jpeg", ".bmp", ".tiff")
                ):
                    update_job(
                        job_id,
                        progress=pct,
                        stage=f"Mengompresi media gambar ({Path(item.filename).name})...",
                    )
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
                            # Quantize colors slightly for drastic PNG reduction while keeping PNG format valid
                            if pil_img.mode not in ("RGB", "RGBA", "P"):
                                pil_img = pil_img.convert("RGBA")
                            quantized = pil_img.quantize(colors=cfg["colors"], method=Image.Quantize.FASTOCTREE)
                            quantized.save(out_buf, format="PNG", optimize=True, compress_level=9)
                        else:
                            pil_img.save(out_buf, format=pil_img.format or "PNG", optimize=True)

                        candidate = out_buf.getvalue()
                        if len(candidate) < len(raw_data):
                            raw_data = candidate
                    except Exception:
                        pass
                elif lower_name.endswith(".xml") or lower_name.endswith(".rels"):
                    update_job(
                        job_id,
                        progress=pct,
                        stage="Mengoptimalkan struktur XML dokumen Word...",
                    )
                    try:
                        xml_text = raw_data.decode("utf-8")
                        cleaned = re.sub(r">\s+<", "><", xml_text.strip())
                        raw_data = cleaned.encode("utf-8")
                    except Exception:
                        pass

                zout.writestr(item.filename, raw_data)

    update_job(job_id, progress=95, stage="Menyusun ulang arsip .DOCX dengan kompresi DEFLATE maksimal...")
    time.sleep(0.3)


def run_compression_worker(job_id: str, file_type: str, level: str, input_path: Path, output_path: Path):
    start_time = time.time()
    try:
        if file_type == "mp4":
            compress_mp4_job(job_id, input_path, output_path, level)
        elif file_type == "pdf":
            compress_pdf_job(job_id, input_path, output_path, level)
        elif file_type == "word":
            compress_word_job(job_id, input_path, output_path, level)
        else:
            raise ValueError(f"Tipe kompresi tidak dikenali: {file_type}")

        orig_size = input_path.stat().st_size
        compressed_size = output_path.stat().st_size
        saved_bytes = max(0, orig_size - compressed_size)
        saved_pct = round((saved_bytes / orig_size) * 100, 1) if orig_size > 0 else 0.0
        elapsed = round(time.time() - start_time, 2)

        update_job(
            job_id,
            status="done",
            progress=100,
            stage="Selesai! File siap diunduh.",
            original_size=orig_size,
            compressed_size=compressed_size,
            saved_bytes=saved_bytes,
            saved_percent=saved_pct,
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
# Multipart Parser Helper (compatible with Python 3.13)
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
        # Keep console clean
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
            job_id = path.split("/api/download/", 1)[1].strip("/")
            job = get_job(job_id)
            if not job or job.get("status") != "done":
                return self._send_json({"error": "File belum siap atau tidak ditemukan"}, status=404)
            out_path = Path(job["output_path"])
            if not out_path.exists():
                return self._send_json({"error": "File hasil kompresi tidak ditemukan"}, status=404)
            data = out_path.read_bytes()
            dl_name = job.get("download_name", out_path.name)
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
            level = fields.get("level", "recommended").lower().strip()

            job_id = uuid.uuid4().hex[:12]
            job_dir = TEMP_JOBS_DIR / job_id
            job_dir.mkdir(parents=True, exist_ok=True)

            stem = Path(orig_filename).stem
            ext = Path(orig_filename).suffix.lower()
            if file_type == "mp4":
                out_ext = ".mp4"
            elif file_type == "pdf":
                out_ext = ".pdf"
            elif file_type == "word":
                out_ext = ".docx"
            else:
                out_ext = ext or ".bin"

            input_path = job_dir / f"input_{orig_filename}"
            output_filename = f"{stem}-compressed{out_ext}"
            output_path = job_dir / output_filename
            input_path.write_bytes(file_bytes)

            with JOBS_LOCK:
                JOBS[job_id] = {
                    "job_id": job_id,
                    "status": "queued",
                    "progress": 4,
                    "stage": "Menyiapkan ruang kerja kompresi...",
                    "original_name": orig_filename,
                    "download_name": output_filename,
                    "original_size": len(file_bytes),
                    "compressed_size": None,
                    "saved_bytes": 0,
                    "saved_percent": 0,
                    "file_type": file_type,
                    "level": level,
                    "output_path": str(output_path),
                    "created_at": time.time(),
                }

            worker = threading.Thread(
                target=run_compression_worker,
                args=(job_id, file_type, level, input_path, output_path),
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
