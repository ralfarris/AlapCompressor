/* ==========================================================================
   AlapCompressor — Interactive Client Controller
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
  },
  mp4: {
    id: "mp4",
    badge: "MP4",
    accept: ".mp4,.mov,.mkv,.webm,video/mp4",
    heroBadge: "Kompresor Video H.264 Cepat",
    heroTitle: "Kompres Video MP4 TanpaRibet & Tetap Jernih",
    heroDesc:
      "Kurangi ukuran file video MP4 secara drastis menggunakan encoding H.264 adaptif yang menjaga kelancaran frame dan kualitas suara.",
    dropTitle: "Tarik & Lepaskan Video MP4 di Sini",
    dropSub: "Mendukung file video .MP4 — siap dikompresi dengan akselerasi FFmpeg.",
    browseLabel: "Pilih Video MP4",
    sampleLabel: "Coba Video Contoh MP4",
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
  },
};

const state = {
  activeTool: "pdf",
  selectedFile: null,
  compressionLevel: "recommended",
  currentJobId: null,
  pollTimer: null,
  displayedProgress: 0,
  history: [],
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
const changeFileBtn = document.getElementById("change-file-btn");
const startCompressBtn = document.getElementById("start-compress-btn");

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
const resultSavedBytesText = document.getElementById("result-saved-bytes-text");
const resultRatioFill = document.getElementById("result-ratio-fill");
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
    { at: 0, text: "Menyiapkan ruang kerja kompresi pastel..." },
    { at: 35, text: "Memuat modul kompresi PDF, MP4 & Word (.DOCX)..." },
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
  fileInput.setAttribute("accept", cfg.accept);

  if (!keepFile) {
    resetToSetupView();
  }
}

function detectToolFromFilename(filename) {
  const lower = (filename || "").toLowerCase();
  if (lower.endsWith(".pdf")) return "pdf";
  if (lower.endsWith(".mp4") || lower.endsWith(".mov") || lower.endsWith(".mkv") || lower.endsWith(".webm")) {
    return "mp4";
  }
  if (lower.endsWith(".docx") || lower.endsWith(".doc")) return "word";
  return null;
}

// ---------------------------------------------------------------------------
// 3. File Selection & Sample File Loader
// ---------------------------------------------------------------------------
function handleChosenFile(file) {
  if (!file) return;

  const detected = detectToolFromFilename(file.name);
  if (detected && detected !== state.activeTool) {
    selectTool(detected, true);
    showToast(`Otomatis beralih ke mode Compress ${TOOL_CONFIG[detected].badge}`);
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
    const extMap = { pdf: "pdf", mp4: "mp4", word: "docx" };
    const sampleName = `Sample-${TOOL_CONFIG[tool].badge}-AlapCompressor.${extMap[tool]}`;
    const sampleFile = new File([blob], sampleName, { type: blob.type });
    handleChosenFile(sampleFile);
    showToast(`File contoh ${sampleName} siap dikompresi!`);
  } catch (err) {
    showToast(err.message || "Gagal memuat file contoh");
  } finally {
    sampleFileBtn.disabled = false;
    sampleBtnLabel.textContent = originalLabel;
  }
}

// ---------------------------------------------------------------------------
// 4. Compression Execution & In-Compression Animation Updates
// ---------------------------------------------------------------------------
function setCircularProgress(percent) {
  const pct = Math.max(0, Math.min(100, percent));
  const circumference = 414.69; // 2 * PI * 66
  const offset = circumference - (pct / 100) * circumference;
  progressRingFill.style.strokeDashoffset = `${offset}`;
  compressingPercent.textContent = `${Math.round(pct)}%`;
  linearProgressFill.style.width = `${Math.max(6, pct)}%`;

  // Update 3-step pipeline tracker
  pipeStep1.classList.toggle("active", pct < 35);
  pipeStep1.classList.toggle("done", pct >= 35);

  pipeStep2.classList.toggle("active", pct >= 35 && pct < 82);
  pipeStep2.classList.toggle("done", pct >= 82);

  pipeStep3.classList.toggle("active", pct >= 82 && pct < 100);
  pipeStep3.classList.toggle("done", pct >= 100);
}

async function startCompression() {
  if (!state.selectedFile) {
    showToast("Pilih file terlebih dahulu sebelum memulai kompresi.");
    return;
  }

  // Switch UI to In-Compression Theater View
  viewSetup.classList.add("hidden");
  viewResult.classList.add("hidden");
  viewCompressing.classList.remove("hidden");

  const cfg = TOOL_CONFIG[state.activeTool];
  compressingBadge.textContent = cfg.badge;
  compressingFilename.textContent = state.selectedFile.name;
  compressingStageText.textContent = "Mengunggah & menganalisis struktur file...";
  state.displayedProgress = 6;
  setCircularProgress(6);

  const formData = new FormData();
  formData.append("file", state.selectedFile);
  formData.append("file_type", state.activeTool);
  formData.append("level", state.compressionLevel);

  const animStartTime = performance.now();

  try {
    const res = await fetch("/api/compress", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok || data.error) {
      throw new Error(data.error || "Gagal memulai kompresi");
    }

    state.currentJobId = data.job_id;
    pollJobStatus(state.currentJobId, animStartTime);
  } catch (err) {
    showToast(err.message || "Terjadi kesalahan saat mengompresi file");
    resetToSetupView();
  }
}

function pollJobStatus(jobId, animStartTime) {
  clearInterval(state.pollTimer);

  state.pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/api/status/${jobId}`);
      if (!res.ok) throw new Error("Gagal memeriksa status kompresi");
      const job = await res.json();

      if (job.stage) {
        compressingStageText.textContent = job.stage;
      }

      if (job.status === "processing" || job.status === "queued") {
        const target = Math.max(state.displayedProgress, job.progress || 15);
        state.displayedProgress = Math.min(95, state.displayedProgress + (target - state.displayedProgress) * 0.45 + 2);
        setCircularProgress(state.displayedProgress);
      } else if (job.status === "done") {
        clearInterval(state.pollTimer);
        // Ensure the user enjoys at least ~1.4s of smooth compression animation even for fast files
        const elapsedAnim = performance.now() - animStartTime;
        const remainingWait = Math.max(250, 1400 - elapsedAnim);

        setCircularProgress(100);
        compressingStageText.textContent = "Selesai! Menyiapkan hasil kompresi...";

        setTimeout(() => {
          showCompressionResult(job);
        }, remainingWait);
      } else if (job.status === "error") {
        clearInterval(state.pollTimer);
        showToast(job.error || "Gagal mengompresi file.");
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
// 5. Result Display & Session History
// ---------------------------------------------------------------------------
function showCompressionResult(job) {
  viewCompressing.classList.add("hidden");
  viewSetup.classList.add("hidden");
  viewResult.classList.remove("hidden");

  resultFilename.textContent = job.download_name;
  resultElapsed.textContent = `${job.elapsed_seconds || 0.8} detik`;
  resultOrigSize.textContent = formatBytes(job.original_size);
  resultNewSize.textContent = formatBytes(job.compressed_size);

  const savedPct = job.saved_percent || 0;
  resultSavingsPill.textContent = savedPct > 0 ? `-${savedPct}%` : "Optimal";
  resultSavedBytesText.textContent =
    job.saved_bytes > 0
      ? `Hemat ${formatBytes(job.saved_bytes)} (${savedPct}% lebih ringan)`
      : "File sudah berada pada ukuran paling optimal";

  const newRatioWidth =
    job.original_size > 0
      ? Math.max(8, Math.min(100, Math.round((job.compressed_size / job.original_size) * 100)))
      : 50;
  resultRatioFill.style.width = `${newRatioWidth}%`;

  const dlUrl = `/api/download/${job.job_id}`;
  downloadResultBtn.href = dlUrl;
  downloadResultBtn.setAttribute("download", job.download_name);

  // Add to session history
  state.history.unshift({
    jobId: job.job_id,
    name: job.download_name,
    tool: job.file_type,
    origSize: job.original_size,
    newSize: job.compressed_size,
    savedPct: savedPct,
    dlUrl: dlUrl,
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
  selectedFilePanel.classList.add("hidden");
  viewCompressing.classList.add("hidden");
  viewResult.classList.add("hidden");
  viewSetup.classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// 6. Event Listeners Initialization
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  // Run initial splash screen animation
  runSplashAnimation(1500);

  // Replay splash screen button
  document.getElementById("replay-splash-btn").addEventListener("click", () => {
    runSplashAnimation(1600);
  });

  // Theme toggle (Warm Light <-> Warm Dark)
  document.getElementById("theme-toggle-btn").addEventListener("click", () => {
    const current = htmlEl.getAttribute("data-theme") || "light";
    const next = current === "light" ? "dark" : "light";
    htmlEl.setAttribute("data-theme", next);
    showToast(next === "dark" ? "Mode Teduh diaktifkan" : "Mode Pastel Terang diaktifkan");
  });

  // Tool selector cards & nav pills
  document.querySelectorAll("[data-select-tool]").forEach((btn) => {
    btn.addEventListener("click", () => selectTool(btn.getAttribute("data-select-tool")));
  });

  document.querySelectorAll("[data-tool-card]").forEach((card) => {
    card.addEventListener("click", () => selectTool(card.getAttribute("data-tool-card")));
  });

  // Browse & Dropzone events
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

  // Compression preset radio cards
  document.querySelectorAll("[data-level-card]").forEach((label) => {
    label.addEventListener("click", () => {
      const level = label.getAttribute("data-level-card");
      state.compressionLevel = level;
      document.querySelectorAll("[data-level-card]").forEach((el) => {
        el.classList.toggle("selected", el.getAttribute("data-level-card") === level);
      });
    });
  });

  // Start compression & reset buttons
  startCompressBtn.addEventListener("click", startCompression);
  compressAnotherBtn.addEventListener("click", resetToSetupView);
});
