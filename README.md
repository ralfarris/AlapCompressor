# AlapCompressor

**AlapCompressor** adalah aplikasi web kompresi file multi-format (*all-in-one*) bergaya *soft pastel editorial* yang terinspirasi dari kemudahan **iLovePDF**, dirancang dengan palet warna hangat yang ramah di mata.

## Fitur Utama

1. **Tiga Mesin Kompresi Nyata (100% Lokal & Privat)**:
   - **Compress PDF (`.pdf`)**: Mengoptimalkan gambar tertanam di setiap halaman, memadatkan *content streams* (DEFLATE level 9), serta menghapus objek duplikat menggunakan `pypdf` & `Pillow`.
   - **Compress MP4 (`.mp4`)**: Mengompresi stream video & audio menggunakan `FFmpeg` (`libx264` + `aac`) dengan pelacakan progres *real-time*.
   - **Compress Word (`.docx`)**: Merampingkan ukuran dokumen Microsoft Word dengan mengoptimalkan media gambar di dalam `word/media/`, merapikan struktur XML, dan mengemas ulang arsip dengan kompresi maksimal.
2. **3 Opsi Hasil Kompresi Sekaligus (Bisa Dipilih & Dibandingkan *Before-After*)**:
   - **Ukuran Paling Minim (`minim`)**: Kompresi maksimal ke ukuran terkecil yang memungkinkan tanpa merusak isi & keterbacaan file.
   - **Balanced (`balanced`)**: Keseimbangan ideal antara penghematan ruang penyimpanan & ketajaman kualitas visual.
   - **Kompres Sedikit (`light`)**: Hanya memangkas beban berlebih agar ukuran mendekati ukuran utama dengan kualitas penuh.
   - Ketiga opsi diracik sekaligus untuk semua format (**PDF**, **MP4**, **Word**) sehingga pada halaman hasil kompresi pengguna dapat langsung membandingkan *Before vs After* tiap opsi dan mengunduh salah satu maupun ketiganya.
3. **Animasi Loading Screen & Animasi Proses Kompresi Estetik**:
   - **Splash Loading Screen**: Animasi tumpukan format file (*MP4, PDF, DOCX*) dengan efek *layered press* dan transisi halus saat aplikasi dibuka.
   - **Compression Theater**: Animasi *orbital ring*, partikel konvergen, *hydraulic squeeze core*, *circular SVG progress gauge*, dan *pipeline tracker* 3 tahap selama file sedang dikompresi.
4. **File Contoh Instan (1-Klik Test)**:
   - Tersedia tombol **Coba File Contoh** pada masing-masing mode (PDF, MP4, Word) untuk langsung mencoba kompresi tanpa harus menyiapkan file terlebih dahulu.

## Cara Menjalankan

```bash
python app.py
```

Kemudian buka **`http://127.0.0.1:8080`** di browser.
