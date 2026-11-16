using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace AlapCompressor
{
    internal static class Program
    {
        [STAThread]
        private static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            using (var server = new LocalWebServer())
            {
                server.Start();
                Application.Run(new LauncherForm(server));
            }
        }
    }

    internal sealed class LauncherForm : Form
    {
        private readonly LocalWebServer _server;
        private readonly NotifyIcon _tray;

        public LauncherForm(LocalWebServer server)
        {
            _server = server;
            Text = "AlapCompressor — Studio Kompresi PDF, MP4 & Word";
            Size = new Size(460, 270);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(246, 245, 240);
            Font = new Font("Segoe UI", 9.5f, FontStyle.Regular);

            Icon appIcon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
            if (appIcon != null) Icon = appIcon;

            var headerPanel = new Panel
            {
                Dock = DockStyle.Top,
                Height = 76,
                BackColor = Color.White,
                Padding = new Padding(20, 14, 20, 14)
            };

            var titleLbl = new Label
            {
                Text = "AlapCompressor",
                Font = new Font("Segoe UI", 15f, FontStyle.Bold),
                ForeColor = Color.FromArgb(35, 42, 49),
                AutoSize = true,
                Location = new Point(20, 14)
            };

            var subLbl = new Label
            {
                Text = "Kompresi PDF, MP4 & Word (.DOCX) — 3 Opsi Hasil Sekaligus",
                Font = new Font("Segoe UI", 9f, FontStyle.Regular),
                ForeColor = Color.FromArgb(91, 101, 113),
                AutoSize = true,
                Location = new Point(22, 44)
            };

            headerPanel.Controls.Add(titleLbl);
            headerPanel.Controls.Add(subLbl);

            var statusLbl = new Label
            {
                Text = "Status Server Lokal: Aktif (" + _server.BaseUrl + ")",
                Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                ForeColor = Color.FromArgb(42, 157, 143),
                AutoSize = true,
                Location = new Point(22, 96)
            };

            var infoLbl = new Label
            {
                Text = "Jendela antarmuka utama telah dibuka secara otomatis.\nBiarkan jendela kecil ini terbuka selama Anda mengompresi file.",
                ForeColor = Color.FromArgb(91, 101, 113),
                AutoSize = true,
                Location = new Point(22, 122)
            };

            var openBtn = new Button
            {
                Text = "Buka Antarmuka AlapCompressor",
                Size = new Size(255, 42),
                Location = new Point(22, 174),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(42, 157, 143),
                ForeColor = Color.White,
                Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            openBtn.FlatAppearance.BorderSize = 0;
            openBtn.Click += (s, e) => OpenAppUi(_server.BaseUrl);

            var quitBtn = new Button
            {
                Text = "Keluar",
                Size = new Size(135, 42),
                Location = new Point(288, 174),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.White,
                ForeColor = Color.FromArgb(91, 101, 113),
                Font = new Font("Segoe UI", 9.5f, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            quitBtn.FlatAppearance.BorderColor = Color.FromArgb(220, 216, 208);
            quitBtn.Click += (s, e) => Close();

            Controls.Add(headerPanel);
            Controls.Add(statusLbl);
            Controls.Add(infoLbl);
            Controls.Add(openBtn);
            Controls.Add(quitBtn);

            _tray = new NotifyIcon
            {
                Icon = appIcon ?? SystemIcons.Application,
                Text = "AlapCompressor (" + _server.BaseUrl + ")",
                Visible = true
            };
            var menu = new ContextMenuStrip();
            menu.Items.Add("Buka AlapCompressor", null, (s, e) => OpenAppUi(_server.BaseUrl));
            menu.Items.Add("Tampilkan Jendela Status", null, (s, e) => { Show(); WindowState = FormWindowState.Normal; Activate(); });
            menu.Items.Add("-");
            menu.Items.Add("Keluar", null, (s, e) => Close());
            _tray.ContextMenuStrip = menu;
            _tray.DoubleClick += (s, e) => OpenAppUi(_server.BaseUrl);

            Shown += (s, e) => OpenAppUi(_server.BaseUrl);
            FormClosing += (s, e) => _tray.Visible = false;
        }

        public static void OpenAppUi(string url)
        {
            try
            {
                // Try opening in standalone Edge/Chrome --app mode for a clean desktop look
                string[] browsers = new[]
                {
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), @"Microsoft\Edge\Application\msedge.exe"),
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Microsoft\Edge\Application\msedge.exe"),
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Google\Chrome\Application\chrome.exe"),
                    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), @"Google\Chrome\Application\chrome.exe")
                };

                foreach (var b in browsers)
                {
                    if (File.Exists(b))
                    {
                        Process.Start(new ProcessStartInfo
                        {
                            FileName = b,
                            Arguments = "--app=" + url + " --window-size=1140,820",
                            UseShellExecute = true
                        });
                        return;
                    }
                }
                Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
            }
            catch
            {
                try { Process.Start(url); } catch { }
            }
        }
    }

    internal sealed class JobState
    {
        public string job_id { get; set; }
        public string status { get; set; }
        public int progress { get; set; }
        public string stage { get; set; }
        public string original_name { get; set; }
        public string download_name { get; set; }
        public long original_size { get; set; }
        public long compressed_size { get; set; }
        public long saved_bytes { get; set; }
        public double saved_percent { get; set; }
        public string file_type { get; set; }
        public string selected_tier { get; set; }
        public double elapsed_seconds { get; set; }
        public string output_path { get; set; }
        public string error { get; set; }
        public Dictionary<string, VariantInfo> variants { get; set; }
    }

    internal sealed class VariantInfo
    {
        public string tier { get; set; }
        public string title { get; set; }
        public string badge { get; set; }
        public string desc { get; set; }
        public long compressed_size { get; set; }
        public long saved_bytes { get; set; }
        public double saved_percent { get; set; }
        public string download_name { get; set; }
        public string output_path { get; set; }
    }

    internal sealed class LocalWebServer : IDisposable
    {
        private TcpListener _listener;
        private volatile bool _running;
        private readonly string _tempRoot;
        private readonly ConcurrentDictionary<string, JobState> _jobs = new ConcurrentDictionary<string, JobState>();
        private readonly JavaScriptSerializer _json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };

        public int Port { get; private set; }
        public string BaseUrl { get { return "http://127.0.0.1:" + Port; } }

        public LocalWebServer()
        {
            _tempRoot = Path.Combine(Path.GetTempPath(), "AlapCompressor_Jobs");
            Directory.CreateDirectory(_tempRoot);
        }

        public void Start()
        {
            int[] candidatePorts = new[] { 8080, 8088, 8899, 0 };
            foreach (int p in candidatePorts)
            {
                try
                {
                    _listener = new TcpListener(IPAddress.Loopback, p);
                    _listener.Start();
                    Port = ((IPEndPoint)_listener.LocalEndpoint).Port;
                    break;
                }
                catch
                {
                    _listener = null;
                }
            }

            _running = true;
            var acceptThread = new Thread(AcceptLoop) { IsBackground = true };
            acceptThread.Start();
        }

        private void AcceptLoop()
        {
            while (_running)
            {
                try
                {
                    var client = _listener.AcceptTcpClient();
                    ThreadPool.QueueUserWorkItem(_ => HandleClient(client));
                }
                catch
                {
                    if (!_running) break;
                }
            }
        }

        private void HandleClient(TcpClient client)
        {
            using (client)
            using (var stream = client.GetStream())
            {
                try
                {
                    client.ReceiveTimeout = 30000;
                    client.SendTimeout = 30000;

                    string requestLine = ReadLine(stream);
                    if (string.IsNullOrEmpty(requestLine)) return;

                    string[] parts = requestLine.Split(' ');
                    if (parts.Length < 2) return;
                    string method = parts[0].ToUpperInvariant();
                    string rawPath = Uri.UnescapeDataString(parts[1].Split('?')[0]);

                    var headers = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                    string line;
                    while (!string.IsNullOrEmpty(line = ReadLine(stream)))
                    {
                        int idx = line.IndexOf(':');
                        if (idx > 0)
                        {
                            headers[line.Substring(0, idx).Trim()] = line.Substring(idx + 1).Trim();
                        }
                    }

                    if (method == "GET")
                    {
                        HandleGet(stream, rawPath);
                    }
                    else if (method == "POST" && rawPath == "/api/compress")
                    {
                        int contentLen = headers.ContainsKey("Content-Length") ? int.Parse(headers["Content-Length"]) : 0;
                        byte[] body = ReadExact(stream, contentLen);
                        string contentType = headers.ContainsKey("Content-Type") ? headers["Content-Type"] : "";
                        HandleCompressPost(stream, contentType, body);
                    }
                    else
                    {
                        WriteJson(stream, 404, new { error = "Endpoint tidak ditemukan" });
                    }
                }
                catch (Exception ex)
                {
                    try { WriteJson(stream, 500, new { error = ex.Message }); } catch { }
                }
            }
        }

        private void HandleGet(NetworkStream stream, string path)
        {
            if (path.StartsWith("/api/status/"))
            {
                string jobId = path.Substring("/api/status/".Length).Trim('/');
                JobState job;
                if (_jobs.TryGetValue(jobId, out job))
                {
                    WriteJson(stream, 200, job);
                }
                else
                {
                    WriteJson(stream, 404, new { error = "Job tidak ditemukan" });
                }
                return;
            }

            if (path.StartsWith("/api/download/"))
            {
                string[] segs = path.Substring("/api/download/".Length).Trim('/').Split('/');
                string jobId = segs[0];
                string tier = segs.Length > 1 ? segs[1].ToLowerInvariant() : null;

                JobState job;
                if (!_jobs.TryGetValue(jobId, out job) || job.status != "done")
                {
                    WriteJson(stream, 404, new { error = "File belum siap" });
                    return;
                }

                string filePath = job.output_path;
                string dlName = job.download_name;
                VariantInfo v;
                if (!string.IsNullOrEmpty(tier) && job.variants != null && job.variants.TryGetValue(tier, out v))
                {
                    filePath = v.output_path;
                    dlName = v.download_name;
                }

                if (!File.Exists(filePath))
                {
                    WriteJson(stream, 404, new { error = "File hasil tidak ditemukan" });
                    return;
                }

                byte[] bytes = File.ReadAllBytes(filePath);
                WriteResponse(stream, 200, "application/octet-stream", bytes, dlName);
                return;
            }

            if (path.StartsWith("/api/sample/"))
            {
                string kind = path.Substring("/api/sample/".Length).Trim('/').ToLowerInvariant();
                if (kind == "word")
                {
                    byte[] docx = CompressionEngine.GenerateSampleDocx();
                    WriteResponse(stream, 200, "application/vnd.openxmlformats-officedocument.wordprocessingml.document", docx, "Sample-Laporan-AlapCompressor.docx");
                    return;
                }
                if (kind == "pdf")
                {
                    byte[] pdf = CompressionEngine.GenerateSamplePdf();
                    WriteResponse(stream, 200, "application/pdf", pdf, "Sample-Brosur-AlapCompressor.pdf");
                    return;
                }
                if (kind == "mp4")
                {
                    byte[] mp4 = CompressionEngine.GenerateSampleMp4(_tempRoot);
                    WriteResponse(stream, 200, "video/mp4", mp4, "Sample-Video-AlapCompressor.mp4");
                    return;
                }
            }

            // Serve embedded web assets
            string resName = "AlapCompressor.Web.index.html";
            string mime = "text/html; charset=utf-8";
            if (path == "/css/style.css")
            {
                resName = "AlapCompressor.Web.style.css";
                mime = "text/css; charset=utf-8";
            }
            else if (path == "/js/app.js")
            {
                resName = "AlapCompressor.Web.app.js";
                mime = "application/javascript; charset=utf-8";
            }

            byte[] asset = ReadEmbeddedResource(resName);
            if (asset == null)
            {
                WriteJson(stream, 404, new { error = "Resource tidak ditemukan" });
                return;
            }
            WriteResponse(stream, 200, mime, asset, null);
        }

        private void HandleCompressPost(NetworkStream stream, string contentType, byte[] body)
        {
            MultipartData parsed = MultipartParser.Parse(contentType, body);
            if (parsed.FileBytes == null || parsed.FileBytes.Length == 0)
            {
                WriteJson(stream, 400, new { error = "Mohon pilih file terlebih dahulu." });
                return;
            }

            string origName = Path.GetFileName(string.IsNullOrEmpty(parsed.FileName) ? "dokumen.pdf" : parsed.FileName);
            string fileType = parsed.Fields.ContainsKey("file_type") ? parsed.Fields["file_type"].ToLowerInvariant() : "pdf";
            string rawLevel = parsed.Fields.ContainsKey("level") ? parsed.Fields["level"].ToLowerInvariant() : "balanced";
            string selectedTier = (rawLevel == "minim" || rawLevel == "extreme") ? "minim" : (rawLevel == "light" ? "light" : "balanced");

            string jobId = Guid.NewGuid().ToString("N").Substring(0, 12);
            string jobDir = Path.Combine(_tempRoot, jobId);
            Directory.CreateDirectory(jobDir);

            string inputPath = Path.Combine(jobDir, "input_" + origName);
            File.WriteAllBytes(inputPath, parsed.FileBytes);

            var job = new JobState
            {
                job_id = jobId,
                status = "queued",
                progress = 5,
                stage = "Menyiapkan 3 opsi kompresi...",
                original_name = origName,
                download_name = origName,
                original_size = parsed.FileBytes.Length,
                file_type = fileType,
                selected_tier = selectedTier,
                variants = new Dictionary<string, VariantInfo>()
            };
            _jobs[jobId] = job;

            ThreadPool.QueueUserWorkItem(_ => CompressionEngine.RunAllTiers(job, inputPath, jobDir));
            WriteJson(stream, 200, new { job_id = jobId, status = "queued" });
        }

        private static byte[] ReadEmbeddedResource(string name)
        {
            var asm = Assembly.GetExecutingAssembly();
            using (Stream s = asm.GetManifestResourceStream(name))
            {
                if (s == null) return null;
                using (var ms = new MemoryStream())
                {
                    s.CopyTo(ms);
                    return ms.ToArray();
                }
            }
        }

        private void WriteJson(NetworkStream stream, int statusCode, object payload)
        {
            byte[] jsonBytes = Encoding.UTF8.GetBytes(_json.Serialize(payload));
            WriteResponse(stream, statusCode, "application/json; charset=utf-8", jsonBytes, null);
        }

        private static void WriteResponse(NetworkStream stream, int statusCode, string contentType, byte[] body, string attachmentName)
        {
            string statusText = statusCode == 200 ? "OK" : (statusCode == 400 ? "Bad Request" : (statusCode == 404 ? "Not Found" : "Internal Server Error"));
            var sb = new StringBuilder();
            sb.Append("HTTP/1.1 ").Append(statusCode).Append(' ').Append(statusText).Append("\r\n");
            sb.Append("Content-Type: ").Append(contentType).Append("\r\n");
            sb.Append("Content-Length: ").Append(body.Length).Append("\r\n");
            sb.Append("Cache-Control: no-store\r\n");
            if (!string.IsNullOrEmpty(attachmentName))
            {
                sb.Append("Content-Disposition: attachment; filename=\"").Append(attachmentName).Append("\"\r\n");
            }
            sb.Append("Connection: close\r\n\r\n");

            byte[] headerBytes = Encoding.UTF8.GetBytes(sb.ToString());
            stream.Write(headerBytes, 0, headerBytes.Length);
            stream.Write(body, 0, body.Length);
            stream.Flush();
        }

        private static string ReadLine(Stream stream)
        {
            var bytes = new List<byte>();
            int b;
            while ((b = stream.ReadByte()) != -1)
            {
                if (b == '\n') break;
                if (b != '\r') bytes.Add((byte)b);
            }
            if (b == -1 && bytes.Count == 0) return null;
            return Encoding.UTF8.GetString(bytes.ToArray());
        }

        private static byte[] ReadExact(Stream stream, int length)
        {
            byte[] buf = new byte[length];
            int offset = 0;
            while (offset < length)
            {
                int read = stream.Read(buf, offset, length - offset);
                if (read <= 0) break;
                offset += read;
            }
            return buf;
        }

        public void Dispose()
        {
            _running = false;
            try { if (_listener != null) _listener.Stop(); } catch { }
        }
    }

    internal sealed class MultipartData
    {
        public Dictionary<string, string> Fields = new Dictionary<string, string>();
        public string FileName;
        public byte[] FileBytes;
    }

    internal static class MultipartParser
    {
        public static MultipartData Parse(string contentType, byte[] body)
        {
            var result = new MultipartData();
            var m = Regex.Match(contentType ?? "", "boundary=([^;]+)");
            if (!m.Success) return result;

            string boundary = "--" + m.Groups[1].Value.Trim('"');
            byte[] boundaryBytes = Encoding.ASCII.GetBytes(boundary);
            byte[] doubleCrlf = Encoding.ASCII.GetBytes("\r\n\r\n");

            List<int> positions = FindOccurrences(body, boundaryBytes);
            for (int i = 0; i < positions.Count - 1; i++)
            {
                int partStart = positions[i] + boundaryBytes.Length + 2; // skip \r\n
                int partEnd = positions[i + 1] - 2; // before \r\n--boundary
                if (partStart >= partEnd || partEnd > body.Length) continue;

                int headerEnd = IndexOfBytes(body, doubleCrlf, partStart, partEnd);
                if (headerEnd < 0) continue;

                string headersText = Encoding.UTF8.GetString(body, partStart, headerEnd - partStart);
                int contentStart = headerEnd + 4;
                int contentLen = partEnd - contentStart;
                if (contentLen < 0) continue;

                var nameMatch = Regex.Match(headersText, "name=\"([^\"]+)\"");
                if (!nameMatch.Success) continue;
                string fieldName = nameMatch.Groups[1].Value;

                var fnMatch = Regex.Match(headersText, "filename=\"([^\"]*)\"");
                if (fnMatch.Success)
                {
                    result.FileName = fnMatch.Groups[1].Value;
                    result.FileBytes = new byte[contentLen];
                    Buffer.BlockCopy(body, contentStart, result.FileBytes, 0, contentLen);
                }
                else
                {
                    result.Fields[fieldName] = Encoding.UTF8.GetString(body, contentStart, contentLen).Trim();
                }
            }
            return result;
        }

        private static List<int> FindOccurrences(byte[] haystack, byte[] needle)
        {
            var list = new List<int>();
            for (int i = 0; i <= haystack.Length - needle.Length; i++)
            {
                bool match = true;
                for (int j = 0; j < needle.Length; j++)
                {
                    if (haystack[i + j] != needle[j]) { match = false; break; }
                }
                if (match) list.Add(i);
            }
            return list;
        }

        private static int IndexOfBytes(byte[] buffer, byte[] pattern, int start, int end)
        {
            for (int i = start; i <= end - pattern.Length; i++)
            {
                bool ok = true;
                for (int j = 0; j < pattern.Length; j++)
                {
                    if (buffer[i + j] != pattern[j]) { ok = false; break; }
                }
                if (ok) return i;
            }
            return -1;
        }
    }

    internal static class CompressionEngine
    {
        private static readonly string[] Tiers = new[] { "minim", "balanced", "light" };

        public static void RunAllTiers(JobState job, string inputPath, string jobDir)
        {
            var sw = Stopwatch.StartNew();
            try
            {
                job.status = "processing";
                job.progress = 10;
                job.stage = "Menganalisis struktur file & menyiapkan 3 opsi kompresi...";

                string stem = Path.GetFileNameWithoutExtension(job.original_name);
                string ext = job.file_type == "mp4" ? ".mp4" : (job.file_type == "word" ? ".docx" : ".pdf");
                var variants = new Dictionary<string, VariantInfo>();

                for (int i = 0; i < Tiers.Length; i++)
                {
                    string tier = Tiers[i];
                    job.progress = 15 + i * 28;
                    job.stage = tier == "minim"
                        ? "Meracik Opsi 1/3: Ukuran Paling Minim (Kompresi Maksimal Aman)..."
                        : (tier == "balanced"
                            ? "Meracik Opsi 2/3: Balanced (Seimbang Kualitas & Ukuran)..."
                            : "Meracik Opsi 3/3: Kompres Sedikit (Mendekati Ukuran Utama)...");

                    string outName = stem + "-" + tier + ext;
                    string outPath = Path.Combine(jobDir, outName);

                    if (job.file_type == "word")
                    {
                        CompressWordTier(inputPath, outPath, tier);
                    }
                    else if (job.file_type == "pdf")
                    {
                        CompressPdfTier(inputPath, outPath, tier);
                    }
                    else if (job.file_type == "mp4")
                    {
                        CompressMp4Tier(inputPath, outPath, tier);
                    }

                    long cSize = new FileInfo(outPath).Length;
                    long savedB = Math.Max(0L, job.original_size - cSize);
                    double savedP = job.original_size > 0 ? Math.Round((savedB * 100.0) / job.original_size, 1) : 0.0;

                    variants[tier] = new VariantInfo
                    {
                        tier = tier,
                        title = tier == "minim" ? "Ukuran Paling Minim" : (tier == "balanced" ? "Balanced (Seimbang)" : "Kompres Sedikit"),
                        badge = tier == "minim" ? "Paling Kecil" : (tier == "balanced" ? "Rekomendasi" : "Mendekati Asli"),
                        desc = tier == "minim"
                            ? "Kompresi maksimal hingga ukuran terkecil tanpa merusak struktur & keterbacaan file."
                            : (tier == "balanced"
                                ? "Keseimbangan ideal antara penghematan ruang penyimpanan & ketajaman kualitas visual."
                                : "Hanya memangkas beban berlebih agar ukuran sedikit lebih ringan dengan kualitas mendekati file utama."),
                        compressed_size = cSize,
                        saved_bytes = savedB,
                        saved_percent = savedP,
                        download_name = outName,
                        output_path = outPath
                    };
                }

                sw.Stop();
                VariantInfo chosen = variants.ContainsKey(job.selected_tier) ? variants[job.selected_tier] : variants["balanced"];
                job.variants = variants;
                job.compressed_size = chosen.compressed_size;
                job.saved_bytes = chosen.saved_bytes;
                job.saved_percent = chosen.saved_percent;
                job.download_name = chosen.download_name;
                job.output_path = chosen.output_path;
                job.elapsed_seconds = Math.Round(sw.Elapsed.TotalSeconds, 2);
                job.progress = 100;
                job.stage = "Selesai! Ketiga opsi kompresi siap dipilih & diunduh.";
                job.status = "done";
            }
            catch (Exception ex)
            {
                job.status = "error";
                job.progress = 100;
                job.error = ex.Message;
            }
        }

        private static void CompressWordTier(string inputPath, string outputPath, string tier)
        {
            int maxDim = tier == "minim" ? 680 : (tier == "balanced" ? 1250 : 1950);
            long jpegQuality = tier == "minim" ? 28L : (tier == "balanced" ? 58L : 86L);
            CompressionLevel zipLevel = tier == "light" ? CompressionLevel.Fastest : CompressionLevel.Optimal;

            using (var fsIn = new FileStream(inputPath, FileMode.Open, FileAccess.Read))
            using (var zin = new ZipArchive(fsIn, ZipArchiveMode.Read))
            using (var fsOut = new FileStream(outputPath, FileMode.Create, FileAccess.Write))
            using (var zout = new ZipArchive(fsOut, ZipArchiveMode.Create))
            {
                foreach (var entry in zin.Entries)
                {
                    byte[] raw;
                    using (var es = entry.Open())
                    using (var ms = new MemoryStream())
                    {
                        es.CopyTo(ms);
                        raw = ms.ToArray();
                    }

                    string lower = entry.FullName.ToLowerInvariant();
                    if (lower.StartsWith("word/media/") && (lower.EndsWith(".png") || lower.EndsWith(".jpg") || lower.EndsWith(".jpeg")))
                    {
                        try
                        {
                            using (var imgIn = new MemoryStream(raw))
                            using (var bmp = new Bitmap(imgIn))
                            {
                                int w = bmp.Width, h = bmp.Height;
                                int nw = w, nh = h;
                                if (Math.Max(w, h) > maxDim)
                                {
                                    double scale = (double)maxDim / Math.Max(w, h);
                                    nw = Math.Max(1, (int)(w * scale));
                                    nh = Math.Max(1, (int)(h * scale));
                                }

                                using (var resized = new Bitmap(nw, nh))
                                using (var g = Graphics.FromImage(resized))
                                {
                                    g.Clear(Color.White);
                                    g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                                    g.DrawImage(bmp, 0, 0, nw, nh);

                                    using (var outBuf = new MemoryStream())
                                    {
                                        SaveJpegWithQuality(resized, outBuf, jpegQuality);
                                        byte[] candidate = outBuf.ToArray();
                                        if (candidate.Length < raw.Length) raw = candidate;
                                    }
                                }
                            }
                        }
                        catch { }
                    }
                    else if (tier != "light" && (lower.EndsWith(".xml") || lower.EndsWith(".rels")))
                    {
                        try
                        {
                            string xml = Encoding.UTF8.GetString(raw);
                            xml = Regex.Replace(xml, @">\s+<", "><");
                            raw = Encoding.UTF8.GetBytes(xml);
                        }
                        catch { }
                    }

                    var outEntry = zout.CreateEntry(entry.FullName, zipLevel);
                    using (var outStream = outEntry.Open())
                    {
                        outStream.Write(raw, 0, raw.Length);
                    }
                }
            }
        }

        private static void CompressPdfTier(string inputPath, string outputPath, string tier)
        {
            long jpegQuality = tier == "minim" ? 26L : (tier == "balanced" ? 54L : 76L);
            int maxDim = tier == "minim" ? 700 : (tier == "balanced" ? 1200 : 1650);

            byte[] pdfBytes = File.ReadAllBytes(inputPath);
            byte[] optimized = RecompressJpegsInsideBinary(pdfBytes, maxDim, jpegQuality);
            File.WriteAllBytes(outputPath, optimized);
        }

        private static void CompressMp4Tier(string inputPath, string outputPath, string tier)
        {
            string ffmpeg = FindFfmpeg();
            if (!string.IsNullOrEmpty(ffmpeg) && File.Exists(ffmpeg))
            {
                long origSize = new FileInfo(inputPath).Length;
                double ratio = tier == "minim" ? 0.25 : (tier == "balanced" ? 0.52 : 0.80);
                string scale = tier == "minim" ? "scale='min(854,iw)':-2" : (tier == "balanced" ? "scale='min(1280,iw)':-2" : "scale='min(1920,iw)':-2");
                string audioBr = tier == "minim" ? "64k" : (tier == "balanced" ? "112k" : "160k");
                int targetBps = Math.Max(65000, (int)((origSize * 8 / 3.0) * ratio));

                var psi = new ProcessStartInfo
                {
                    FileName = ffmpeg,
                    Arguments = string.Format("-y -loglevel error -i \"{0}\" -vf \"{1}\" -c:v libx264 -b:v {2} -maxrate {3} -bufsize {4} -preset veryfast -pix_fmt yuv420p -movflags +faststart -c:a aac -b:a {5} \"{6}\"",
                        inputPath, scale, targetBps, (int)(targetBps * 1.1), targetBps * 2, audioBr, outputPath),
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                using (var p = Process.Start(psi))
                {
                    p.WaitForExit(60000);
                }
                if (File.Exists(outputPath) && new FileInfo(outputPath).Length > 0) return;
            }
            File.Copy(inputPath, outputPath, true);
        }

        private static string FindFfmpeg()
        {
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string pyRoot = Path.Combine(localAppData, "Programs", "Python");
            if (Directory.Exists(pyRoot))
            {
                var found = Directory.GetFiles(pyRoot, "ffmpeg*.exe", SearchOption.AllDirectories).FirstOrDefault();
                if (!string.IsNullOrEmpty(found)) return found;
            }
            return "ffmpeg";
        }

        private static byte[] RecompressJpegsInsideBinary(byte[] data, int maxDim, long quality)
        {
            // Scan for embedded JPEG streams (FFD8FF ... FFD9) inside PDF/containers and recompress them
            using (var outMs = new MemoryStream(data.Length))
            {
                int i = 0;
                while (i < data.Length)
                {
                    int jpgStart = FindJpegStart(data, i);
                    if (jpgStart < 0)
                    {
                        outMs.Write(data, i, data.Length - i);
                        break;
                    }
                    int jpgEnd = FindJpegEnd(data, jpgStart + 3);
                    if (jpgEnd < 0 || jpgEnd - jpgStart < 2048)
                    {
                        outMs.Write(data, i, (jpgStart - i) + 1);
                        i = jpgStart + 1;
                        continue;
                    }

                    outMs.Write(data, i, jpgStart - i);
                    int jpgLen = (jpgEnd + 2) - jpgStart;
                    byte[] origJpg = new byte[jpgLen];
                    Buffer.BlockCopy(data, jpgStart, origJpg, 0, jpgLen);

                    byte[] smaller = TryReencodeJpeg(origJpg, maxDim, quality);
                    outMs.Write(smaller, 0, smaller.Length);
                    i = jpgEnd + 2;
                }
                return outMs.ToArray();
            }
        }

        private static int FindJpegStart(byte[] d, int from)
        {
            for (int i = from; i < d.Length - 3; i++)
            {
                if (d[i] == 0xFF && d[i + 1] == 0xD8 && d[i + 2] == 0xFF) return i;
            }
            return -1;
        }

        private static int FindJpegEnd(byte[] d, int from)
        {
            for (int i = from; i < d.Length - 1; i++)
            {
                if (d[i] == 0xFF && d[i + 1] == 0xD9) return i;
            }
            return -1;
        }

        private static byte[] TryReencodeJpeg(byte[] jpgBytes, int maxDim, long quality)
        {
            try
            {
                using (var ms = new MemoryStream(jpgBytes))
                using (var bmp = new Bitmap(ms))
                {
                    int w = bmp.Width, h = bmp.Height;
                    int nw = w, nh = h;
                    if (Math.Max(w, h) > maxDim)
                    {
                        double s = (double)maxDim / Math.Max(w, h);
                        nw = Math.Max(1, (int)(w * s));
                        nh = Math.Max(1, (int)(h * s));
                    }
                    using (var resized = new Bitmap(nw, nh))
                    using (var g = Graphics.FromImage(resized))
                    {
                        g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                        g.DrawImage(bmp, 0, 0, nw, nh);
                        using (var outBuf = new MemoryStream())
                        {
                            SaveJpegWithQuality(resized, outBuf, quality);
                            byte[] res = outBuf.ToArray();
                            if (res.Length < jpgBytes.Length) return res;
                        }
                    }
                }
            }
            catch { }
            return jpgBytes;
        }

        private static void SaveJpegWithQuality(Bitmap bmp, Stream target, long quality)
        {
            ImageCodecInfo jpgEncoder = ImageCodecInfo.GetImageDecoders().First(c => c.FormatID == ImageFormat.Jpeg.Guid);
            var encParams = new EncoderParameters(1);
            encParams.Param[0] = new EncoderParameter(System.Drawing.Imaging.Encoder.Quality, quality);
            bmp.Save(target, jpgEncoder, encParams);
        }

        public static byte[] GenerateSampleDocx()
        {
            byte[] img1 = CreateRichJpeg(1000, 700, Color.FromArgb(69, 123, 157), Color.FromArgb(244, 162, 97), 96L);
            using (var ms = new MemoryStream())
            {
                using (var zf = new ZipArchive(ms, ZipArchiveMode.Create, true))
                {
                    WriteZipText(zf, "[Content_Types].xml", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Default Extension=\"jpg\" ContentType=\"image/jpeg\"/><Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/></Types>");
                    WriteZipText(zf, "_rels/.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/></Relationships>");
                    WriteZipText(zf, "word/document.xml", "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body><w:p><w:r><w:t>Dokumen Sample Word AlapCompressor</w:t></w:r></w:p></w:body></w:document>");
                    var imgEntry = zf.CreateEntry("word/media/image1.jpg", CompressionLevel.NoCompression);
                    using (var s = imgEntry.Open()) s.Write(img1, 0, img1.Length);
                }
                return ms.ToArray();
            }
        }

        public static byte[] GenerateSamplePdf()
        {
            byte[] jpg = CreateRichJpeg(1200, 1500, Color.FromArgb(42, 157, 143), Color.FromArgb(224, 109, 83), 96L);
            using (var ms = new MemoryStream())
            {
                Action<string> w = str => { byte[] b = Encoding.ASCII.GetBytes(str); ms.Write(b, 0, b.Length); };
                w("%PDF-1.4\n");
                w("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n");
                w("2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n");
                w("3 0 obj << /Type /Page /Parent 2 0 R /Resources << /XObject << /Im0 4 0 R >> >> /MediaBox [0 0 600 750] /Contents 5 0 R >> endobj\n");
                w("4 0 obj << /Type /XObject /Subtype /Image /Width 1200 /Height 1500 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length " + jpg.Length + " >>\nstream\n");
                ms.Write(jpg, 0, jpg.Length);
                w("\nendstream\nendobj\n");
                string content = "q 600 0 0 750 0 0 cm /Im0 Do Q";
                w("5 0 obj << /Length " + content.Length + " >>\nstream\n" + content + "\nendstream\nendobj\n");
                w("trailer << /Root 1 0 R >>\n%%EOF\n");
                return ms.ToArray();
            }
        }

        public static byte[] GenerateSampleMp4(string tempRoot)
        {
            string ffmpeg = FindFfmpeg();
            string tmp = Path.Combine(tempRoot, "sample_" + Guid.NewGuid().ToString("N").Substring(0, 8) + ".mp4");
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = ffmpeg,
                    Arguments = "-y -loglevel error -f lavfi -i testsrc2=size=1280x720:rate=30:duration=3 -f lavfi -i sine=frequency=440:duration=3 -c:v libx264 -crf 15 -preset ultrafast -pix_fmt yuv420p -c:a aac -b:a 192k \"" + tmp + "\"",
                    UseShellExecute = false,
                    CreateNoWindow = true
                };
                using (var p = Process.Start(psi)) p.WaitForExit(20000);
                if (File.Exists(tmp)) return File.ReadAllBytes(tmp);
            }
            catch { }
            finally { try { if (File.Exists(tmp)) File.Delete(tmp); } catch { } }
            return new byte[0];
        }

        private static byte[] CreateRichJpeg(int w, int h, Color c1, Color c2, long quality)
        {
            var rng = new Random(42);
            using (var bmp = new Bitmap(w, h))
            {
                using (var g = Graphics.FromImage(bmp))
                using (var brush = new LinearGradientBrush(new Rectangle(0, 0, w, h), c1, c2, 45f))
                {
                    g.FillRectangle(brush, 0, 0, w, h);
                    for (int i = 0; i < 180; i++)
                    {
                        using (var p = new SolidBrush(Color.FromArgb(90, rng.Next(255), rng.Next(255), rng.Next(255))))
                        {
                            g.FillEllipse(p, rng.Next(w), rng.Next(h), rng.Next(30, 180), rng.Next(30, 180));
                        }
                    }
                }
                using (var ms = new MemoryStream())
                {
                    SaveJpegWithQuality(bmp, ms, quality);
                    return ms.ToArray();
                }
            }
        }

        private static void WriteZipText(ZipArchive zf, string entryName, string text)
        {
            var e = zf.CreateEntry(entryName, CompressionLevel.NoCompression);
            byte[] b = Encoding.UTF8.GetBytes(text);
            using (var s = e.Open()) s.Write(b, 0, b.Length);
        }
    }
}
