import os
import threading
import tkinter as tk
from tkinter import filedialog, ttk
import yt_dlp

class DownloadCancelled(Exception): pass

class YtdlpGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("yt-dlp Desktop Client")
        self.root.geometry("700x520")
        self.root.minsize(550, 480)
        self.root.configure(bg="#f8f9fa")

        self.style = ttk.Style()
        self.style.theme_use("clam")

        BG_COLOR, CARD_COLOR, PRIMARY_COLOR, PRIMARY_HOVER, TEXT_DARK = "#f8f9fa", "#edf2f7", "#0066cc", "#0052a3", "#212529"
        
        self.style.configure(".", background=BG_COLOR, foreground=TEXT_DARK, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=BG_COLOR)
        self.style.configure("Card.TFrame", background=CARD_COLOR)
        
        self.style.configure("TLabel", font=("Segoe UI", 11))
        self.style.configure("Heading.TLabel", font=("Segoe UI", 11, "bold"), foreground=PRIMARY_COLOR)
        self.style.configure("Metadata.TLabel", font=("Segoe UI", 10), foreground="#555555", background=CARD_COLOR)
        self.style.configure("Status.TLabel", font=("Segoe UI", 10, "italic"), foreground="#666666")
        self.style.configure("Success.TLabel", font=("Segoe UI", 11, "bold"), foreground="#2e7d32")
        self.style.configure("Error.TLabel", font=("Segoe UI", 11, "bold"), foreground="#c62828")
        
        self.style.configure("TEntry", borderwidth=1, relief="flat", font=("Segoe UI", 10))
        self.style.configure("Readonly.TEntry", fieldbackground=CARD_COLOR, borderwidth=0, relief="flat")
        self.style.configure("TCombobox", arrowsize=12, font=("Segoe UI", 10))

        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), borderwidth=0, relief="flat", padding=(15, 7))
        self.style.configure("Primary.TButton", background=PRIMARY_COLOR, foreground="white", focuscolor="")
        self.style.map("Primary.TButton", background=[("active", PRIMARY_HOVER), ("disabled", "#cccccc")])
        self.style.configure("Secondary.TButton", background="#e2e8f0", foreground=TEXT_DARK, focuscolor="")
        self.style.map("Secondary.TButton", background=[("active", "#cbd5e1"), ("disabled", "#f1f5f9")])

        self.style.configure("Horizontal.TProgressbar", troughcolor="#e2e8f0", background=PRIMARY_COLOR, borderwidth=0, thickness=8)
        self.style.configure("Success.Horizontal.TProgressbar", troughcolor="#e2e8f0", background="#2e7d32", borderwidth=0, thickness=8)

        self.url_var = tk.StringVar()
        self.save_dir_var = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.res_var = tk.StringVar(value="Best Quality")
        
        self._cancel_requested = self._download_active = False
        self._last_previewed_url = self._preview_after_id = None
        self._current_video_info = None 

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Video URL", style="Heading.TLabel").pack(anchor=tk.W, pady=(0, 5))
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=(0, 10))
        
        #url entry and paste button
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)
        self.url_entry.focus()
        ttk.Button(url_frame, text="Paste", style="Secondary.TButton", command=self.paste_url).pack(side=tk.RIGHT)
        self.url_entry.bind("<Return>", lambda _: self.fetch_preview_async())

        #preview card
        self.preview_card = ttk.Frame(main_frame, padding=12, style="TFrame")
        self.preview_card.pack(fill=tk.X, pady=(0, 15))
        self.preview_label = ttk.Label(self.preview_card, text="", justify="left", style="Metadata.TLabel")
        self.preview_label.pack(anchor=tk.W, fill=tk.X, expand=True)
        
        self.url_var.trace_add("write", lambda *_: self._schedule_preview())

        middle_frame = ttk.Frame(main_frame)
        middle_frame.pack(fill=tk.X, pady=(0, 20))
        
        res_frame = ttk.Frame(middle_frame)
        res_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))
        ttk.Label(res_frame, text="Preferred Resolution", style="Heading.TLabel").pack(anchor=tk.W, pady=(0, 5))
        self.res_combo = ttk.Combobox(res_frame, textvariable=self.res_var, state="readonly", values=["Best Quality"])
        self.res_combo.pack(fill=tk.X, ipady=4)
        self.res_combo.bind("<<ComboboxSelected>>", lambda _: self._update_preview_text())

        #save location frame
        dir_outer_frame = ttk.Frame(middle_frame)
        dir_outer_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        ttk.Label(dir_outer_frame, text="Save Location", style="Heading.TLabel").pack(anchor=tk.W, pady=(0, 5))
        dir_frame = ttk.Frame(dir_outer_frame)
        dir_frame.pack(fill=tk.X)
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.save_dir_var, state="readonly", style="Readonly.TEntry")
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)
        ttk.Button(dir_frame, text="Browse...", style="Secondary.TButton", command=self.browse_location).pack(side=tk.RIGHT)

        #status and progress
        self.status_label = ttk.Label(main_frame, text="Ready", style="Status.TLabel")
        self.status_label.pack(anchor=tk.W, pady=(0, 5))
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate", style="Horizontal.TProgressbar")
        self.progress_bar.pack(fill=tk.X, pady=(0, 25))

        #bottom button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(anchor=tk.CENTER)
        self.download_btn = ttk.Button(button_frame, text="Download Video", style="Primary.TButton", command=self.start_download_thread)
        self.download_btn.pack(side=tk.LEFT, padx=8)
        self.cancel_btn = ttk.Button(button_frame, text="Cancel", style="Secondary.TButton", command=self.cancel_download, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=8)

    def paste_url(self):
        try: self.url_var.set(self.root.clipboard_get().strip())
        except tk.TclError: return
        self.fetch_preview_async()

    def _schedule_preview(self, delay_ms=600):
        if self._preview_after_id: self.root.after_cancel(self._preview_after_id)
        self._preview_after_id = self.root.after(delay_ms, self.fetch_preview_async)

    #fetches video metadata in a separate thread to avoid blocking the UI, then updates the preview card with the info
    def fetch_preview_async(self):
        self._preview_after_id = None
        if self._download_active: return
        url = self.url_var.get().strip()
        
        self.status_label.configure(style="Status.TLabel", text="Ready")
        self.progress_bar.configure(style="Horizontal.TProgressbar", value=0)
        
        if not url or "://" not in url or url == self._last_previewed_url:
            if not url: 
                self.preview_label.config(text="")
                self.preview_card.configure(style="TFrame")
                self.res_combo.configure(values=["Best Quality"])
                self.res_var.set("Best Quality")
                self._current_video_info = None
                setattr(self, '_last_previewed_url', None)
            return
        self._last_previewed_url = url
        self.status_label.config(text="Fetching video metadata...")
        threading.Thread(target=self._fetch_preview, args=(url,), daemon=True).start()

    def _fetch_preview(self, url):
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception: info = None
        self.root.after(0, self._show_preview, info)

    def _show_preview(self, info):
        self._current_video_info = info 

        if not info:
            self.preview_label.config(text="(Could not read video info)")
            self.preview_card.configure(style="TFrame")
            self.status_label.configure(style="Error.TLabel", text="❌ Verification failed.")
            return

        self.preview_card.configure(style="Card.TFrame")
        self.status_label.configure(style="Status.TLabel", text="Ready to download")
        
        available_heights = set()
        for f in info.get("formats", []):
            h = f.get("height")
            if h and f.get("vcodec") != "none":
                available_heights.add(h)
        
        sorted_res = [f"{h}p" for h in sorted(available_heights, reverse=True)]
        self.res_combo.configure(values=["Best Quality"] + sorted_res)
        self.res_var.set("Best Quality")

        self._update_preview_text()

    #calculates an estimated file size based on the selected resolution and available metadata, then updates the preview card text with the video info and size estimate
    def _update_preview_text(self):
        info = self._current_video_info
        if not info: return

        selected_res = self.res_var.get()
        title = info.get("title", "Unknown")
        uploader = info.get("uploader") or info.get("channel", "Unknown")
        duration = info.get("duration", 0)

        calculated_size = 0
        is_approx = False

        if selected_res == "Best Quality":
            formats = info.get("requested_formats") or [info]
            calculated_size = sum(f.get("filesize") or f.get("filesize_approx") or 0 for f in formats)
            is_approx = any(f.get("filesize_approx") is not None for f in formats) or any(f.get("filesize") is None for f in formats)
            
            #absolute fallback if best quality doesn't expose pre-calculated values upfront
            if calculated_size == 0 and duration:
                best_video = max([f for f in info.get("formats", []) if f.get("vcodec") != "none" and f.get("tbr")], key=lambda x: x.get("tbr", 0), default=None)
                best_audio = max([f for f in info.get("formats", []) if f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("tbr")], key=lambda x: x.get("tbr", 0), default=None)
                v_tbr = best_video.get("tbr", 0) if best_video else 0
                a_tbr = best_audio.get("tbr", 0) if best_audio else 0
                if v_tbr or a_tbr:
                    calculated_size = ((v_tbr + a_tbr) * 1000 * duration) / 8
                    is_approx = True
        else:
            target_height = int(selected_res.replace("p", ""))
            
            best_video_stream = None
            for f in info.get("formats", []):
                if f.get("vcodec") != "none" and f.get("height") == target_height:
                    if best_video_stream is None or f.get("filesize") or f.get("filesize_approx") or f.get("tbr", 0) > best_video_stream.get("tbr", 0):
                        best_video_stream = f

            best_audio_stream = None
            for f in info.get("formats", []):
                if f.get("acodec") != "none" and f.get("vcodec") == "none":
                    if best_audio_stream is None or f.get("asr", 0) > best_audio_stream.get("asr", 0):
                        best_audio_stream = f

            # try to get filesize directly, if not available use bitrate and duration to estimate
            v_size = v_approx = a_size = a_approx = 0
            
            if best_video_stream:
                v_size = best_video_stream.get("filesize") or best_video_stream.get("filesize_approx")
                if v_size:
                    v_approx = best_video_stream.get("filesize_approx") is not None
                elif best_video_stream.get("tbr") and duration:
                    #formula: size (in bytes) = (bitrate in kbps * 1000 / 8) * duration in seconds
                    v_size = (best_video_stream.get("tbr") * 1000 * duration) / 8
                    v_approx = True

            if best_audio_stream:
                a_size = best_audio_stream.get("filesize") or best_audio_stream.get("filesize_approx")
                if a_size:
                    a_approx = best_audio_stream.get("filesize_approx") is not None
                elif best_audio_stream.get("tbr") and duration:
                    a_size = (best_audio_stream.get("tbr") * 1000 * duration) / 8
                    a_approx = True

            is_approx = v_approx or a_approx or (v_size == 0 or a_size == 0)
            calculated_size = (v_size or 0) + (a_size or 0)

        lines = [f"🎬  {title}", f"👤  by {uploader}"]
        if duration: lines.append(f"⏱️  Duration: {self.format_eta(duration)}")
        
        if calculated_size > 0:
            prefix = "~" if is_approx else ""
            lines.append(f"📦  Size: {prefix}{self.format_bytes(calculated_size)}")
        else:
            lines.append("📦  Size: Size Unknown")

        self.preview_label.config(text="\n".join(lines))

    @staticmethod
    def format_bytes(b, suffix="B"):
        for unit in ["", "Ki", "Mi", "Gi", "Ti"]:
            if b < 1024.0: return f"{b:.1f} {unit}{suffix}"
            b /= 1024.0
        return f"{b:.1f} Pi{suffix}"

    def cancel_download(self):
        self._cancel_requested = True
        self.status_label.config(text="Cancelling...")
        self.cancel_btn.config(state=tk.DISABLED)

    def browse_location(self):
        d = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if d: self.save_dir_var.set(d)

    def start_download_thread(self):
        url = self.url_var.get().strip()
        if not url:
            self.status_label.configure(style="Error.TLabel", text="⚠️ Please enter a valid video URL.")
            return

        self._cancel_requested, self._download_active = False, True
        self.download_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.status_label.configure(style="Status.TLabel", text="Extracting video info...")
        self.progress_bar.configure(style="Horizontal.TProgressbar", value=0)

        threading.Thread(target=self.actual_download, args=(url,), daemon=True).start()

    def ytdlp_hook(self, d):
        if self._cancel_requested: raise DownloadCancelled()
        info = d.get("info_dict") or {}
        v, a = info.get("vcodec", "none"), info.get("acodec", "none")
        phase = "video+audio" if v != "none" and a != "none" else ("video" if v != "none" else ("audio" if a != "none" else "file"))

        if d["status"] == "downloading":
            downloaded = d.get("downloaded_bytes") or 0
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
            percent = (downloaded / total * 100)
            speed = self.format_bytes(d.get("speed") or 0, suffix="B/s")
            eta = self.format_eta(d.get("eta"))
            self.root.after(0, self.update_progress, percent, f"Downloading {phase}... {percent:.1f}% at {speed} (ETA: {eta})")
        elif d["status"] == "finished":
            msg = "Video done, getting audio..." if phase == "video" else ("Audio done, merging..." if phase == "audio" else "Finishing up...")
            self.root.after(0, self.update_progress, 100, msg)

    @staticmethod
    def format_eta(seconds):
        if not seconds: return "--:--"
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"

    def update_progress(self, percent, status_text):
        self.progress_bar["value"] = percent
        self.status_label.config(text=status_text)

    def actual_download(self, url):
        selected_res = self.res_var.get()
        if selected_res == "Best Quality":
            fmt_setting = "bestvideo+bestaudio/best"
        else:
            height = selected_res.replace("p", "")
            fmt_setting = f"bestvideo[height<={height}]+bestaudio/best"

        ydl_opts = {
            "outtmpl": os.path.join(self.save_dir_var.get(), "%(title)s.%(ext)s"),
            "progress_hooks": [self.ytdlp_hook],
            "format": fmt_setting
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.root.after(0, self.download_complete, True, "✅ Download Finished Successfully!")
        except (DownloadCancelled, Exception) as e:
            msg = "💡 Download cancelled." if (self._cancel_requested or isinstance(e, DownloadCancelled)) else f"❌ Error: {str(e)}"
            self.root.after(0, self.download_complete, False, msg)

    def download_complete(self, success, message):
        self._download_active = False
        self.download_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
        self.status_label.configure(style="Success.TLabel" if success else "Error.TLabel", text=message)
        self.progress_bar.configure(style="Success.Horizontal.TProgressbar" if success else "Horizontal.TProgressbar", value=100 if success else 0)

if __name__ == "__main__":
    root = tk.Tk()
    app = YtdlpGuiApp(root)
    root.mainloop()