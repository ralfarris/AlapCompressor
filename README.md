# AlapCompressor

Aplikasi kompresi file **PDF, MP4, dan Word (`.docx`)** super ringan (~138 KB single-file `.exe` dengan antarmuka studio *soft pastel editorial*, tanpa perlu install Python untuk pengguna langsung). Terinspirasi dari kemudahan **iLovePDF**, dirancang dengan palet warna hangat yang ramah di mata serta menyajikan **3 opsi hasil kompresi sekaligus** lengkap dengan perbandingan *Before vs After*.

[![Download Latest Release](https://img.shields.io/github/v/release/ralfarris/AlapCompressor?label=Download%20AlapCompressor&style=for-the-badge&color=2A9D8F&cacheSeconds=60)](https://github.com/ralfarris/AlapCompressor/releases/latest)

## Cara Menggunakan (Untuk Pengguna Langsung)
1. Buka halaman [**GitHub Releases**](https://github.com/ralfarris/AlapCompressor/releases/latest) (atau klik tombol hijau di atas).
2. Download file **`AlapCompressor.exe`** (atau `AlapCompressor-Windows.zip`).
3. Langsung jalankan **`AlapCompressor.exe`** (tanpa perlu install apa pun — antarmuka aplikasi akan otomatis terbuka).
4. Pilih tab **Compress PDF**, **Compress MP4**, atau **Compress Word**, tarik & lepaskan file (atau klik **Coba File Contoh**), lalu klik **Kompres Sekarang**.

---

## Menjalankan & Build dari Source Code (Developer)

### 1. Menjalankan / Build Versi Executable (`AlapCompressor.exe`)
Dikompilasi langsung menggunakan compiler C# bawaan Windows (`.NET Framework 4.x`) tanpa perlu SDK tambahan:
```powershell
.\build.bat
```
atau:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```
Hasil executable siap pakai akan dibuat di **`dist\AlapCompressor.exe`**. Kamu juga bisa menjalankannya melalui:
```bash
python run.py
```

### 2. Menjalankan Mode Server Python (`app.py`)
```bash
python app.py
```
Lalu buka **`http://127.0.0.1:8080`** di browser.

---

## Fitur Utama

- **Single-File Portable (`AlapCompressor.exe`)** – cukup 1 file `.exe` (~138 KB) yang sudah memuat seluruh aset antarmuka di dalamnya dan berjalan dengan ikon di *System Tray*.
- **Empat Fitur Utama (Kompresi & Crop Video)**:
  - **Compress PDF (`.pdf`)** – mengoptimalkan gambar tertanam di dalam halaman & memadatkan *stream* dokumen tanpa merusak keterbacaan teks.
  - **Compress MP4 (`.mp4`)** – mengompresi video & audio H.264 adaptif secara cepat dan halus.
  - **Compress Word (`.docx`)** – merampingkan media gambar di dalam `word/media/` serta mengoptimalkan struktur XML dan arsip dokumen.
  - **Crop Video (`.mp4`)** – memotong area bingkai layar video secara interaktif (`1:1`, `9:16`, `16:9`, `4:3`, `Tengah 75%`, atau *drag & resize* bebas) serta memotong durasi awal–akhir untuk mengurangi ukuran file secara alami dengan opsi **Murni Crop Saja (*Kualitas Asli*)** tanpa harus dikompresi berlebih.
- **3 Opsi Hasil Kompresi Sekaligus (Perbandingan *Before vs After* Interaktif)**:
  1. **Ukuran Paling Minim (*Paling Kecil*)** – kompresi maksimal ke ukuran terkecil yang memungkinkan tanpa menghancurkan file.
  2. **Balanced (*Seimbang / Rekomendasi*)** – titik tengah ideal antara penghematan ukuran & ketajaman kualitas visual.
  3. **Kompres Sedikit (*Mendekati Utama*)** – hanya memangkas beban berlebih sehingga ukuran mendekati file utama dengan kualitas penuh.
- **Animasi Loading Screen & *Compression Theater*** – dilengkapi animasi *Splash Screen* tumpukan format file serta animasi proses kompresi (*orbital ring*, partikel konvergen, *hydraulic squeeze core*, *circular SVG progress gauge*, dan *pipeline tracker* 3 tahap).
- **Palet Warna *Soft Pastel* Nyaman di Mata** – latar *Warm Alabaster* (`#F6F5F0`) dengan aksen *Sage Emerald*, *Terracotta Coral*, dan *Periwinkle Indigo*, dilengkapi **Mode Teduh (*Warm Dark*)**.

## Struktur Proyek
```text
src/
  Program.cs         # launcher WinForms, System Tray, embedded HTTP server & C# compression engine
  app.manifest       # manifest High-DPI & non-admin execution
static/
  index.html         # UI utama, splash loading screen, compression theater & before-after board
  css/style.css      # sistem desain soft pastel & keyframe animasi
  js/app.js          # kontroler interaktif, drag-and-drop & pemilih 3 opsi hasil
assets/
  alapcompressor.ico # ikon aplikasi multi-resolusi
app.py               # server & mesin kompresi Python (PyPDF, Pillow, FFmpeg)
run.py               # script builder & runner cepat
build.ps1 / build.bat
.github/workflows/release.yml
```
