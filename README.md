# ytdlp-tk

A lightweight, dependency-free desktop client for [yt-dlp](https://github.com/yt-dlp/yt-dlp), built natively with Python's standard `tkinter` library.

## Features

- **Asynchronous Processing:** Manifest extractions and downloads run on isolated background threads to keep the UI perfectly fluid and responsive.
- **Smart Metadata Card:** Automatically fetches title, channel, duration, and dynamically recalculates expected file sizes when switching resolutions.
- **Dynamic Quality Selector:** Automatically maps available video tracks from the stream manifest into an inline resolution combobox dropdown.
- **Clean State Notification Engine:** Replaced old-fashioned modal popups with flat, color-coded inline status messages (Success/Error states).
- **Control & Utilities:** Paste-from-clipboard quick button, folder picker layout (defaults to `~/Downloads`), live progress bar tracking (with Speed/ETA matrices), and a graceful **Cancel** button.

## Prerequisites

- **Python 3.8+**
- **yt-dlp** (Python package)
- **FFmpeg** on your system path (Required by `yt-dlp` to merge split audio/video muxes)

## Installation

```bash
git clone https://github.com/piitoni/ytdlp-tk.git
cd ytdlp-tk
pip install yt-dlp
```

## Screenshots
