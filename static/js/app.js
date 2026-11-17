/* ==========================================================================
   AlapCompressor — Interactive Client Controller (PDF, MP4, Word & Video Crop)
   ========================================================================== */

const TOOL_CONFIG = {
  pdf: {
    id: "pdf",
    badge: "PDF",
    accept: ".pdf,application/pdf",
    heroBadge: "Optimasi Dokumen PDF Cerdas",
    heroTitle: "Kompres File PDF Lebih Ringan & Rapi",
    heroDesc:
      "Perkecil ukuran dokumen PDF hingga puluhan persen tanpa membuat teks pecah. Nyaman untuk lampiran email & portal dokumen.",
    dropTitle: "Tarik & Lepaskan File PDF di Sini",
    dropSub: "Mendukung semua dokumen .PDF — diproses aman 100% di perangkatmu.",
    browseLabel: "Pilih File PDF",
    sampleLabel: "Coba File Contoh PDF",
    ctaLabel: "Kompres PDF Sekarang",
  },
  mp4: {
    id: "mp4",
    badge: "MP4",
    accept: ".mp4,.mov,.mkv,.webm,video/mp4",
    heroBadge: "Kompresor Video H.264 Cepat",
    heroTitle: "Kompres Video MP4 Tanpa Ribet & Tetap Jernih",
    heroDesc:
      "Kurangi ukuran file video MP4 secara drastis menggunakan encoding H.264 adaptif yang menjaga kelancaran frame dan kualitas suara.",
    dropTitle: "Tarik & Lepaskan Video MP4 di Sini",
    dropSub: "Mendukung file video .MP4 — siap dikompresi dengan akselerasi FFmpeg.",
    browseLabel: "Pilih Video MP4",
    sampleLabel: "Coba Video Contoh MP4",
    ctaLabel: "Kompres Video Sekarang",
  },
  word: {
    id: "word",
    badge: "DOCX",
    accept: ".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    heroBadge: "Peramping Dokumen Microsoft Word",
    heroTitle: "Kompres Dokumen Word (.DOCX) Seketika",
    heroDesc:
      "Optimalkan gambar beresolusi tinggi dan struktur XML di dalam dokumen Word (.docx) agar ukuran file jauh lebih hemat.",
    dropTitle: "Tarik & Lepaskan File Word (.DOCX) di Sini",
    dropSub: "Mendukung dokumen Microsoft Word (.DOCX) dengan gambar maupun tabel.",
    browseLabel: "Pilih File Word",
    sampleLabel: "Coba Dokumen Contoh Word",
    ctaLabel: "Kompres Word Sekarang",
  },
  crop: {
    id: "crop",
    badge: "CROP",
    accept: ".mp4,.mov,.mkv,.webm,video/mp4",
    heroBadge: "Studio Crop Bingkai & Durasi Video",
    heroTitle: "Crop Area & Durasi Video Agar Ukuran Lebih Hemat",
    heroDesc:
      "Potong bagian pinggir layar video (1:1, 9:16, 16:9, atau bebas) maupun durasinya untuk mengecilkan ukuran file tanpa harus menurunkan kualitas asli.",
    dropTitle: "Tarik & Lepaskan Video yang Ingin Di-Crop",
    dropSub: "Pilih area bingkai & durasi secara interaktif — kualitas visual tetap tajam.",
    browseLabel: "Pilih Video untuk Di-Crop",
    sampleLabel: "Coba Video Contoh MP4",
    ctaLabel: "Potong (Crop) Video Sekarang",
  },
};

const state = {
  activeTool: "pdf",
  selectedFile: null,
  compressionLevel: "balanced",
  currentJobId: null,
  lastCompletedJob: null,
  pollTimer: null,
  displayedProgress: 0,
  history: [],
  crop: {
    rx: 0.125,
    ry: 0.125,
    rw: 0.75,
    rh: 0.75,
    videoWidth: 1280,
    videoHeight: 720,
    duration: 0,
    objectUrl: null,
  },
};

// DOM Elements
const htmlEl = document.documentElement;
const splashScreen = document.getElementById("splash-screen");
const splashBar = document.getElementById("splash-progress-bar");
const splashPercent = document.getElementById("splash-percent");
const splashStatusText = document.getElementById("splash-status-text");

const heroBadgeText = document.getElementById("hero-badge-text");
const heroTitle = document.getElementById("hero-title");
const heroDesc = document.getElementById("hero-desc");

const dropzone = document.getElementById("dropzone");
const dropzoneTitle = document.getElementById("dropzone-title");
const dropzoneSub = document.getElementById("dropzone-sub");
const browseBtn = document.getElementById("browse-btn");
const browseBtnLabel = document.getElementById("browse-btn-label");
const sampleFileBtn = document.getElementById("sample-file-btn");
const sampleBtnLabel = document.getElementById("sample-btn-label");
const fileInput = document.getElementById("file-input");

const selectedFilePanel = document.getElementById("selected-file-panel");
const selectedFileBadge = document.getElementById("selected-file-badge");
const selectedFileName = document.getElementById("selected-file-name");
const selectedFileSize = document.getElementById("selected-file-size");
const selectedFileStatusNote = document.getElementById("selected-file-status-note");
const changeFileBtn = document.getElementById("change-file-btn");
const startCompressBtn = document.getElementById("start-compress-btn");
const startCompressBtnLabel = document.getElementById("start-compress-btn-label");

// Video Crop Studio Elements
const videoCropStudio = document.getElementById("video-crop-studio");
const cropDimPill = document.getElementById("crop-dim-pill");
const cropVideoWrap = document.getElementById("crop-video-wrap");
const cropPreviewVideo = document.getElementById("crop-preview-video");
const cropBoxOverlay = document.getElementById("crop-box-overlay");
const cropPlayBtn = document.getElementById("crop-play-btn");
const cropPlayLabel = document.getElementById("crop-play-label");
const cropTimeReadout = document.getElementById("crop-time-readout");
const trimStartInput = document.getElementById("trim-start-input");
const trimEndInput = document.getElementById("trim-end-input");

// Level Card Dynamic Text Elements
const levelHeaderTitle = document.getElementById("level-header-title");
const levelHeaderSub = document.getElementById("level-header-sub");
const lvlTitleMinim = document.getElementById("lvl-title-minim");
const lvlChipMinim = document.getElementById("lvl-chip-minim");
const lvlDescMinim = document.getElementById("lvl-desc-minim");
const lvlTitleBalanced = document.getElementById("lvl-title-balanced");
const lvlChipBalanced = document.getElementById("lvl-chip-balanced");
const lvlDescBalanced = document.getElementById("lvl-desc-balanced");
const lvlTitleLight = document.getElementById("lvl-title-light");
const lvlChipLight = document.getElementById("lvl-chip-light");
const lvlDescLight = document.getElementById("lvl-desc-light");

const viewSetup = document.getElementById("view-setup");
const viewCompressing = document.getElementById("view-compressing");
const viewResult = document.getElementById("view-result");

const progressRingFill = document.getElementById("progress-ring-fill");
const compressingBadge = document.getElementById("compressing-badge");
const compressingPercent = document.getElementById("compressing-percent");
const compressingFilename = document.getElementById("compressing-filename");
const compressingStageText = document.getElementById("compressing-stage-text");
const linearProgressFill = document.getElementById("linear-progress-fill");
const pipeStep1 = document.getElementById("pipe-step-1");
const pipeStep2 = document.getElementById("pipe-step-2");
const pipeStep3 = document.getElementById("pipe-step-3");

const resultFilename = document.getElementById("result-filename");
const resultElapsed = document.getElementById("result-elapsed");
const resultOrigSize = document.getElementById("result-orig-size");
const resultNewSize = document.getElementById("result-new-size");
const resultSavingsPill = document.getElementById("result-savings-pill");
const resultActiveTierName = document.getElementById("result-active-tier-name");
const resultSavedBytesText = document.getElementById("result-saved-bytes-text");
const resultRatioFill = document.getElementById("result-ratio-fill");
const resultTiersGrid = document.getElementById("result-tiers-grid");
const downloadResultBtn = document.getElementById("download-result-btn");
const compressAnotherBtn = document.getElementById("compress-another-btn");

const historySection = document.getElementById("history-section");
const historyList = document.getElementById("history-list");
const historyCountBadge = document.getElementById("history-count-badge");
const toastEl = document.getElementById("toast");

// ---------------------------------------------------------------------------
// Utility Helpers
// ---------------------------------------------------------------------------
function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const val = bytes / Math.pow(k, i);
  return `${val.toFixed(i === 0 ? 0 : 2)} ${sizes[i]}`;
}

let toastTimeout = null;
function showToast(message) {
  toastEl.textContent = message;
  toastEl.classList.remove("hidden");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    toastEl.classList.add("hidden");
  }, 3400);
}

// ---------------------------------------------------------------------------
// 1. Splash Screen Animation Controller
// ---------------------------------------------------------------------------
function runSplashAnimation(durationMs = 1550) {
  splashScreen.classList.remove("fade-out");
  let start = null;

  const steps = [
    { at: 0, text: "Menyiapkan ruang kerja kompresi & studio crop pastel..." },
    { at: 35, text: "Memuat modul PDF, MP4, Word (.DOCX) & Crop Video..." },
    { at: 72, text: "Mengkalibrasi kualitas visual & rasio ukuran..." },
    { at: 95, text: "Siap digunakan!" },
  ];

  function frame(ts) {
    if (!start) start = ts;
    const elapsed = ts - start;
    const pct = Math.min(100, Math.round((elapsed / durationMs) * 100));

    splashBar.style.width = `${pct}%`;
    splashPercent.textContent = `${pct}%`;

    for (let i = steps.length - 1; i >= 0; i--) {
      if (pct >= steps[i].at) {
        splashStatusText.textContent = steps[i].text;
        break;
      }
    }

    if (pct < 100) {
      requestAnimationFrame(frame);
    } else {
      setTimeout(() => {
        splashScreen.classList.add("fade-out");
      }, 220);
    }
  }

  requestAnimationFrame(frame);
}

// ---------------------------------------------------------------------------
// 2. Tool Selection & Theme Switching
// ---------------------------------------------------------------------------
function syncLevelCardCopyForTool(toolKey) {
  if (toolKey === "crop") {
    levelHeaderTitle.textContent = "Pilih Mode Output Video Hasil Crop";
    levelHeaderSub.textContent = "Kamu bisa memilih murni crop tanpa kompresi atau sekaligus diperkecil lagi";

    lvlTitleMinim.textContent = "Crop + Ukuran Minim";
    lvlChipMinim.textContent = "Paling Kecil";
    lvlDescMinim.textContent =
      "Memotong area/durasi video ditambah kompresi maksimal aman untuk hasil ukuran terkecil.";

    lvlTitleBalanced.textContent = "Crop + Balanced";
    lvlChipBalanced.textContent = "Seimbang";
    lvlDescBalanced.textContent =
      "Memotong area/durasi video sekaligus merampingkan bitrate secara seimbang.";

    lvlTitleLight.textContent = "Murni Crop Saja";
    lvlChipLight.textContent = "Kualitas Asli";
    lvlDescLight.textContent =
      "Hanya memotong area & durasi video sesuai pilihanmu tanpa mengurangi ketajaman visual asli.";

    setCompressionLevel("light");
  } else {
    levelHeaderTitle.textContent = "Pilih Opsi Prioritas Kompresi";
    levelHeaderSub.textContent = "Ketiga opsi tetap akan disiapkan agar bisa kamu bandingkan di hasil akhir";

    lvlTitleMinim.textContent = "Ukuran Paling Minim";
    lvlChipMinim.textContent = "Paling Kecil";
    lvlDescMinim.textContent =
      "Kompresi maksimal ke ukuran terkecil yang memungkinkan tanpa merusak isi & keterbacaan file.";

    lvlTitleBalanced.textContent = "Balanced (Seimbang)";
    lvlChipBalanced.textContent = "Rekomendasi";
    lvlDescBalanced.textContent =
      "Keseimbangan ideal: ukuran file jauh lebih hemat dengan ketajaman visual yang tetap terjaga.";

    lvlTitleLight.textContent = "Kompres Sedikit";
    lvlChipLight.textContent = "Mendekati Utama";
    lvlDescLight.textContent =
      "Hanya memangkas sedikit beban berlebih agar ukuran mendekati file utama dengan kualitas penuh.";

    setCompressionLevel("balanced");
  }
}

function setCompressionLevel(level) {
  state.compressionLevel = level;
  document.querySelectorAll("[data-level-card]").forEach((el) => {
    const isMatch = el.getAttribute("data-level-card") === level;
    el.classList.toggle("selected", isMatch);
    const radio = el.querySelector('input[type="radio"]');
    if (radio) radio.checked = isMatch;
  });
}

function selectTool(toolKey, keepFile = false) {
  if (!TOOL_CONFIG[toolKey]) return;
  state.activeTool = toolKey;
  const cfg = TOOL_CONFIG[toolKey];

  htmlEl.setAttribute("data-tool", toolKey);

  // Sync top navigation pills
  document.querySelectorAll("[data-select-tool]").forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-select-tool") === toolKey);
  });

  // Sync tool cards
  document.querySelectorAll("[data-tool-card]").forEach((card) => {
    card.classList.toggle("active", card.getAttribute("data-tool-card") === toolKey);
  });

  // Update Hero & Dropzone texts
  heroBadgeText.textContent = cfg.heroBadge;
  heroTitle.textContent = cfg.heroTitle;
  heroDesc.textContent = cfg.heroDesc;

  dropzoneTitle.textContent = cfg.dropTitle;
  dropzoneSub.textContent = cfg.dropSub;
  browseBtnLabel.textContent = cfg.browseLabel;
  sampleBtnLabel.textContent = cfg.sampleLabel;
  if (startCompressBtnLabel) startCompressBtnLabel.textContent = cfg.ctaLabel;
  fileInput.setAttribute("accept", cfg.accept);

  syncLevelCardCopyForTool(toolKey);

  if (!keepFile) {
    resetToSetupView();
  }
}

function detectToolFromFilename(filename) {
  const lower = (filename || "").toLowerCase();
  if (lower.endsWith(".pdf")) return "pdf";
  if (lower.endsWith(".mp4") || lower.endsWith(".mov") || lower.endsWith(".mkv") || lower.endsWith(".webm")) {
    return state.activeTool === "crop" ? "crop" : "mp4";
  }
  if (lower.endsWith(".docx") || lower.endsWith(".doc")) return "word";
  return null;
}

// ---------------------------------------------------------------------------
// 3. Interactive Video Crop Studio Logic
// ---------------------------------------------------------------------------
function updateCropOverlayDOM() {
  const { rx, ry, rw, rh, videoWidth, videoHeight } = state.crop;
  cropBoxOverlay.style.left = `${(rx * 100).toFixed(2)}%`;
  cropBoxOverlay.style.top = `${(ry * 100).toFixed(2)}%`;
  cropBoxOverlay.style.width = `${(rw * 100).toFixed(2)}%`;
  cropBoxOverlay.style.height = `${(rh * 100).toFixed(2)}%`;

  const outW = Math.max(2, Math.floor((videoWidth * rw) / 2) * 2);
  const outH = Math.max(2, Math.floor((videoHeight * rh) / 2) * 2);
  const areaReduction = Math.max(0, Math.round((1 - rw * rh) * 100));

  cropDimPill.innerHTML = `${videoWidth} &times; ${videoHeight} px &rarr; <strong>${outW} &times; ${outH} px</strong> (-${areaReduction}% area)`;
}

function applyCropPreset(preset) {
  const vw = state.crop.videoWidth || 1280;
  const vh = state.crop.videoHeight || 720;

  let rw = 0.75;
  let rh = 0.75;

  if (preset === "free") {
    rw = 1.0;
    rh = 1.0;
  } else if (preset === "center75") {
    rw = 0.75;
    rh = 0.75;
  } else {
    const parts = preset.split(":");
    if (parts.length === 2) {
      const targetAspect = parseFloat(parts[0]) / parseFloat(parts[1]);
      const videoAspect = vw / vh;
      if (targetAspect > videoAspect) {
        rw = 0.9;
        rh = (rw * videoAspect) / targetAspect;
      } else {
        rh = 0.9;
        rw = (rh * targetAspect) / videoAspect;
      }
    }
  }

  rw = Math.max(0.15, Math.min(1.0, rw));
  rh = Math.max(0.15, Math.min(1.0, rh));
  state.crop.rw = rw;
  state.crop.rh = rh;
  state.crop.rx = (1.0 - rw) / 2;
  state.crop.ry = (1.0 - rh) / 2;

  document.querySelectorAll("[data-crop-preset]").forEach((btn) => {
    btn.classList.toggle("active", btn.getAttribute("data-crop-preset") === preset);
  });

  updateCropOverlayDOM();
}

function setupVideoCropPreview(file) {
  if (state.crop.objectUrl) {
    URL.revokeObjectURL(state.crop.objectUrl);
  }
  const url = URL.createObjectURL(file);
  state.crop.objectUrl = url;
  cropPreviewVideo.src = url;
  cropPreviewVideo.load();

  cropPreviewVideo.onloadedmetadata = () => {
    state.crop.videoWidth = cropPreviewVideo.videoWidth || 1280;
    state.crop.videoHeight = cropPreviewVideo.videoHeight || 720;
    state.crop.duration = cropPreviewVideo.duration || 0;

    trimStartInput.value = "0";
    trimEndInput.value = state.crop.duration > 0 ? state.crop.duration.toFixed(1) : "0";
    cropTimeReadout.textContent = `0.0s / ${(state.crop.duration || 0).toFixed(1)}s`;

    applyCropPreset("center75");
  };

  cropPreviewVideo.ontimeupdate = () => {
    const cur = cropPreviewVideo.currentTime || 0;
    const dur = state.crop.duration || cropPreviewVideo.duration || 0;
    cropTimeReadout.textContent = `${cur.toFixed(1)}s / ${dur.toFixed(1)}s`;

    const tEnd = parseFloat(trimEndInput.value) || 0;
    const tStart = parseFloat(trimStartInput.value) || 0;
    if (tEnd > tStart + 0.2 && cur >= tEnd) {
      cropPreviewVideo.currentTime = tStart;
    }
  };
}

function initCropBoxPointerEvents() {
  let dragMode = null; // 'move' | 'nw' | 'ne' | 'sw' | 'se'
  let startX = 0;
  let startY = 0;
  let initCrop = null;

  function onPointerDown(e) {
    e.preventDefault();
    e.stopPropagation();
    const handle = e.target.getAttribute("data-handle");
    dragMode = handle || "move";
    startX = e.clientX;
    startY = e.clientY;
    initCrop = { ...state.crop };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
  }

  function onPointerMove(e) {
    if (!dragMode) return;
    const rect = cropVideoWrap.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;

    const dx = (e.clientX - startX) / rect.width;
    const dy = (e.clientY - startY) / rect.height;
    const minSize = 0.12;

    let { rx, ry, rw, rh } = initCrop;

    if (dragMode === "move") {
      rx = Math.max(0, Math.min(1 - rw, rx + dx));
      ry = Math.max(0, Math.min(1 - rh, ry + dy));
    } else {
      if (dragMode.includes("w")) {
        const newLeft = Math.max(0, Math.min(rx + rw - minSize, rx + dx));
        rw = rx + rw - newLeft;
        rx = newLeft;
      }
      if (dragMode.includes("e")) {
        rw = Math.max(minSize, Math.min(1 - rx, rw + dx));
      }
      if (dragMode.includes("n")) {
        const newTop = Math.max(0, Math.min(ry + rh - minSize, ry + dy));
        rh = ry + rh - newTop;
        ry = newTop;
      }
      if (dragMode.includes("s")) {
        rh = Math.max(minSize, Math.min(1 - ry, rh + dy));
      }
    }

    state.crop.rx = rx;
    state.crop.ry = ry;
    state.crop.rw = rw;
    state.crop.rh = rh;
    updateCropOverlayDOM();
  }

  function onPointerUp() {
    dragMode = null;
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", onPointerUp);
  }

  cropBoxOverlay.addEventListener("pointerdown", onPointerDown);
}

// ---------------------------------------------------------------------------
// 4. File Selection & Sample File Loader
// ---------------------------------------------------------------------------
function handleChosenFile(file) {
  if (!file) return;

  const detected = detectToolFromFilename(file.name);
  if (detected && detected !== state.activeTool) {
    selectTool(detected, true);
    showToast(`Otomatis beralih ke mode ${TOOL_CONFIG[detected].badge}`);
  } else if (!detected) {
    showToast("Mohon pilih file berformat .PDF, .MP4, atau .DOCX");
    return;
  }

  if (file.name.toLowerCase().endsWith(".doc")) {
    showToast("Mohon gunakan dokumen Word format modern (.docx)");
    return;
  }

  state.selectedFile = file;
  const cfg = TOOL_CONFIG[state.activeTool];

  selectedFileBadge.textContent = cfg.badge;
  selectedFileName.textContent = file.name;
  selectedFileSize.textContent = formatBytes(file.size);
  if (selectedFileStatusNote) {
    selectedFileStatusNote.textContent =
      state.activeTool === "crop" ? "Siap diatur area crop-nya" : "Siap dikompresi";
  }

  if (state.activeTool === "crop") {
    videoCropStudio.classList.remove("hidden");
    setupVideoCropPreview(file);
  } else {
    videoCropStudio.classList.add("hidden");
  }

  selectedFilePanel.classList.remove("hidden");
  selectedFilePanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function loadSampleFile() {
  const tool = state.activeTool;
  const originalLabel = sampleBtnLabel.textContent;
  sampleFileBtn.disabled = true;
  sampleBtnLabel.textContent = "Menyiapkan File Contoh...";

  try {
    const res = await fetch(`/api/sample/${tool}`);
    if (!res.ok) throw new Error("Gagal membuat file contoh");
    const blob = await res.blob();
    const extMap = { pdf: "pdf", mp4: "mp4", crop: "mp4", word: "docx" };
    const sampleName = `Sample-${TOOL_CONFIG[tool].badge}-AlapCompressor.${extMap[tool]}`;
    const sampleFile = new File([blob], sampleName, { type: blob.type });
    handleChosenFile(sampleFile);
    showToast(`File contoh ${sampleName} siap diproses!`);
  } catch (err) {
    showToast(err.message || "Gagal memuat file contoh");
  } finally {
    sampleFileBtn.disabled = false;
    sampleBtnLabel.textContent = originalLabel;
  }
}

// ---------------------------------------------------------------------------
// 5. Compression / Crop Execution & In-Compression Animation Updates
// ---------------------------------------------------------------------------
function setCircularProgress(percent) {
  const pct = Math.max(0, Math.min(100, percent));
  const circumference = 414.69; // 2 * PI * 66
  const offset = circumference - (pct / 100) * circumference;
  progressRingFill.style.strokeDashoffset = `${offset}`;
  compressingPercent.textContent = `${Math.round(pct)}%`;
  linearProgressFill.style.width = `${Math.max(6, pct)}%`;

  pipeStep1.classList.toggle("active", pct < 35);
  pipeStep1.classList.toggle("done", pct >= 35);

  pipeStep2.classList.toggle("active", pct >= 35 && pct < 82);
  pipeStep2.classList.toggle("done", pct >= 82);

  pipeStep3.classList.toggle("active", pct >= 82 && pct < 100);
  pipeStep3.classList.toggle("done", pct >= 100);
}

async function startCompression() {
  if (!state.selectedFile) {
    showToast("Pilih file terlebih dahulu sebelum memulai proses.");
    return;
  }

  if (cropPreviewVideo && !cropPreviewVideo.paused) {
    cropPreviewVideo.pause();
  }

  viewSetup.classList.add("hidden");
  viewResult.classList.add("hidden");
  viewCompressing.classList.remove("hidden");

  const cfg = TOOL_CONFIG[state.activeTool];
  compressingBadge.textContent = cfg.badge;
  compressingFilename.textContent = state.selectedFile.name;
  compressingStageText.textContent =
    state.activeTool === "crop"
      ? "Menganalisis koordinat crop & memotong frame video..."
      : "Mengunggah & menganalisis struktur file...";
  state.displayedProgress = 6;
  setCircularProgress(6);

  const formData = new FormData();
  formData.append("file", state.selectedFile);
  formData.append("file_type", state.activeTool);
  formData.append("level", state.compressionLevel);

  if (state.activeTool === "crop") {
    formData.append("crop_rx", state.crop.rx.toFixed(4));
    formData.append("crop_ry", state.crop.ry.toFixed(4));
    formData.append("crop_rw", state.crop.rw.toFixed(4));
    formData.append("crop_rh", state.crop.rh.toFixed(4));
    formData.append("trim_start", trimStartInput.value || "0");
    formData.append("trim_end", trimEndInput.value || "0");
  }

  const animStartTime = performance.now();

  try {
    const res = await fetch("/api/compress", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || "Gagal memulai proses");
    }

    state.currentJobId = data.job_id;
    pollJobStatus(state.currentJobId, animStartTime);
  } catch (err) {
    showToast(err.message || "Terjadi kesalahan saat memproses file");
    resetToSetupView();
  }
}

function pollJobStatus(jobId, animStartTime) {
  clearInterval(state.pollTimer);

  state.pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/status/${jobId}`);
      if (!res.ok) throw new Error("Gagal memeriksa status proses");
      const job = await res.json();

      if (job.stage) {
        compressingStageText.textContent = job.stage;
      }

      if (job.status === "processing" || job.status === "queued") {
        const target = Math.max(state.displayedProgress, job.progress || 15);
        state.displayedProgress = Math.min(
          95,
          state.displayedProgress + (target - state.displayedProgress) * 0.45 + 2
        );
        setCircularProgress(state.displayedProgress);
      } else if (job.status === "done") {
        clearInterval(state.pollTimer);
        const elapsedAnim = performance.now() - animStartTime;
        const remainingWait = Math.max(250, 1400 - elapsedAnim);

        setCircularProgress(100);
        compressingStageText.textContent = "Selesai! Menyiapkan hasil akhir...";

        setTimeout(() => {
          showCompressionResult(job);
        }, remainingWait);
      } else if (job.status === "error") {
        clearInterval(state.pollTimer);
        showToast(job.error || "Gagal memproses file.");
        resetToSetupView();
      }
    } catch (err) {
      clearInterval(state.pollTimer);
      showToast(err.message || "Koneksi terputus");
      resetToSetupView();
    }
  }, 240);
}

// ---------------------------------------------------------------------------
// 6. Result Display (3 Options + Before-After Board) & Session History
// ---------------------------------------------------------------------------
function selectResultTier(job, tierKey) {
  const variants = job.variants || {};
  const chosen = variants[tierKey] || {
    tier: tierKey,
    title: tierKey,
    compressed_size: job.compressed_size,
    saved_bytes: job.saved_bytes,
    saved_percent: job.saved_percent,
    download_name: job.download_name,
  };

  resultFilename.textContent = chosen.download_name;
  resultOrigSize.textContent = formatBytes(job.original_size);
  resultNewSize.textContent = formatBytes(chosen.compressed_size);

  const savedPct = chosen.saved_percent || 0;
  resultSavingsPill.textContent = savedPct > 0 ? `-${savedPct}%` : "Optimal";
  if (resultActiveTierName) {
    resultActiveTierName.textContent = chosen.title || tierKey;
  }
  resultSavedBytesText.textContent =
    chosen.saved_bytes > 0
      ? `Hemat ${formatBytes(chosen.saved_bytes)} (${savedPct}% lebih ringan)`
      : "File sudah berada pada ukuran paling optimal";

  const newRatioWidth =
    job.original_size > 0
      ? Math.max(8, Math.min(100, Math.round((chosen.compressed_size / job.original_size) * 100)))
      : 50;
  resultRatioFill.style.width = `${newRatioWidth}%`;

  const dlUrl = `/api/download/${job.job_id}/${tierKey}`;
  downloadResultBtn.href = dlUrl;
  downloadResultBtn.setAttribute("download", chosen.download_name);

  if (resultTiersGrid) {
    resultTiersGrid.querySelectorAll("[data-result-tier]").forEach((card) => {
      const isSelected = card.getAttribute("data-result-tier") === tierKey;
      card.classList.toggle("active", isSelected);
      const stateLabel = card.querySelector(".rt-select-state");
      if (stateLabel) {
        stateLabel.textContent = isSelected ? "✓ Opsi Terpilih" : "Klik untuk Pilih";
      }
    });
  }
}

function showCompressionResult(job) {
  state.lastCompletedJob = job;
  viewCompressing.classList.add("hidden");
  viewSetup.classList.add("hidden");
  viewResult.classList.remove("hidden");

  resultElapsed.textContent = `${job.elapsed_seconds || 0.8} detik`;

  const variants = job.variants || {};
  const tierOrder = ["minim", "balanced", "light"];
  const defaultTier = job.file_type === "crop" ? "light" : "balanced";
  const initialTier =
    job.selected_tier && variants[job.selected_tier] ? job.selected_tier : defaultTier;

  if (resultTiersGrid) {
    resultTiersGrid.innerHTML = tierOrder
      .filter((t) => variants[t])
      .map((t) => {
        const v = variants[t];
        const dlUrl = `/api/download/${job.job_id}/${t}`;
        return `
          <div class="result-tier-card" data-result-tier="${t}">
            <div>
              <div class="rt-top">
                <span class="rt-title">${v.title}</span>
                <span class="rt-badge rt-badge-${t}">${v.badge}</span>
              </div>
              <div class="rt-size-row">
                <strong class="rt-size">${formatBytes(v.compressed_size)}</strong>
                <span class="rt-saved">-${v.saved_percent}%</span>
              </div>
              <p class="rt-desc">${v.desc}</p>
            </div>
            <div class="rt-footer">
              <span class="rt-select-state">Klik untuk Pilih</span>
              <a href="${dlUrl}" class="rt-quick-dl" download="${v.download_name}" title="Unduh opsi ${v.title}">Unduh</a>
            </div>
          </div>
        `;
      })
      .join("");

    resultTiersGrid.querySelectorAll("[data-result-tier]").forEach((card) => {
      card.addEventListener("click", (e) => {
        if (e.target.closest(".rt-quick-dl")) return;
        const t = card.getAttribute("data-result-tier");
        selectResultTier(job, t);
      });
    });
  }

  selectResultTier(job, initialTier);

  const chosen = variants[initialTier] || job;
  state.history.unshift({
    jobId: job.job_id,
    name: chosen.download_name,
    tool: job.file_type,
    origSize: job.original_size,
    newSize: chosen.compressed_size,
    savedPct: chosen.saved_percent || 0,
    dlUrl: `/api/download/${job.job_id}/${initialTier}`,
  });
  renderHistory();
}

function renderHistory() {
  if (state.history.length === 0) {
    historySection.classList.add("hidden");
    return;
  }
  historySection.classList.remove("hidden");
  historyCountBadge.textContent = `${state.history.length} file`;

  historyList.innerHTML = state.history
    .map((item) => {
      const tagClass = `tag-${item.tool}`;
      return `
        <div class="history-item">
          <div class="history-item-left">
            <span class="history-tag ${tagClass}">${item.tool.toUpperCase()}</span>
            <div>
              <div class="history-name">${item.name}</div>
              <div class="history-meta">${formatBytes(item.origSize)} &rarr; <strong>${formatBytes(item.newSize)}</strong> (Hemat ${item.savedPct}%)</div>
            </div>
          </div>
          <a href="${item.dlUrl}" class="history-dl" download="${item.name}">Unduh</a>
        </div>
      `;
    })
    .join("");
}

function resetToSetupView() {
  clearInterval(state.pollTimer);
  state.selectedFile = null;
  fileInput.value = "";
  if (cropPreviewVideo && !cropPreviewVideo.paused) {
    cropPreviewVideo.pause();
  }
  selectedFilePanel.classList.add("hidden");
  videoCropStudio.classList.add("hidden");
  viewCompressing.classList.add("hidden");
  viewResult.classList.add("hidden");
  viewSetup.classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// 7. Event Listeners Initialization
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  runSplashAnimation(1500);
  initCropBoxPointerEvents();

  document.getElementById("replay-splash-btn").addEventListener("click", () => {
    runSplashAnimation(1600);
  });

  document.getElementById("theme-toggle-btn").addEventListener("click", () => {
    const current = htmlEl.getAttribute("data-theme") || "light";
    const next = current === "light" ? "dark" : "light";
    htmlEl.setAttribute("data-theme", next);
    showToast(next === "dark" ? "Mode Teduh diaktifkan" : "Mode Pastel Terang diaktifkan");
  });

  document.querySelectorAll("[data-select-tool]").forEach((btn) => {
    btn.addEventListener("click", () => selectTool(btn.getAttribute("data-select-tool")));
  });

  document.querySelectorAll("[data-tool-card]").forEach((card) => {
    card.addEventListener("click", () => selectTool(card.getAttribute("data-tool-card")));
  });

  // Crop ratio preset buttons
  document.querySelectorAll("[data-crop-preset]").forEach((btn) => {
    btn.addEventListener("click", () => {
      applyCropPreset(btn.getAttribute("data-crop-preset"));
    });
  });

  // Video preview Play/Pause toggle
  if (cropPlayBtn) {
    cropPlayBtn.addEventListener("click", () => {
      if (cropPreviewVideo.paused) {
        const tStart = parseFloat(trimStartInput.value) || 0;
        if (cropPreviewVideo.currentTime < tStart) {
          cropPreviewVideo.currentTime = tStart;
        }
        cropPreviewVideo.play();
        cropPlayLabel.innerHTML = "&#10074;&#10074; Jeda Pratinjau";
      } else {
        cropPreviewVideo.pause();
        cropPlayLabel.innerHTML = "&#9654; Putar Pratinjau";
      }
    });
  }

  browseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  sampleFileBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    loadSampleFile();
  });

  dropzone.addEventListener("click", () => {
    fileInput.click();
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleChosenFile(e.target.files[0]);
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("drag-over");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleChosenFile(e.dataTransfer.files[0]);
    }
  });

  changeFileBtn.addEventListener("click", () => {
    fileInput.click();
  });

  document.querySelectorAll("[data-level-card]").forEach((label) => {
    label.addEventListener("click", () => {
      setCompressionLevel(label.getAttribute("data-level-card"));
    });
  });

  startCompressBtn.addEventListener("click", startCompression);
  compressAnotherBtn.addEventListener("click", resetToSetupView);
});
