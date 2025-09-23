# Minimal Photo Viewer (HEIC-friendly) for Windows/macOS/Linux
# deps: PIL, pillow_heif, tkinter

# ---------- Dependency Check & Auto-Install ----------
# This block checks if required packages are present, and optionally installs them.
import importlib.util
import subprocess
import sys

required_packages = ["PIL", "pillow_heif", "tkinter"]
missing = []

for pkg in required_packages:
    if importlib.util.find_spec(pkg) is None:
        missing.append(pkg)

if missing:
    print(f"Missing packages detected: {', '.join(missing)}")
    choice = input("Attempt to install them now with pip? (y/n): ").strip().lower()
    if choice == "y":
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
    else:
        print("Aborting")
        sys.exit(1)

# ---------- End Dependency Check ----------

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk

# Make PIL understand .heic via libheif
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception as e:
    # Still works for non-HEIC, but warn
    print("Warning: HEIC support not loaded:", e)

SUPPORTED_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

class MiniViewer(tk.Tk):
    def __init__(self, start_path: Path | None = None):
        super().__init__()
        self.title("MiniViewer")
        self.geometry("1100x700")
        self.configure(bg="#111")

        # State
        self.files: list[Path] = []
        self.index = 0
        self.zoom = 1.0
        self.fit_mode = True  # fit-to-window by default
        self.rotation = 0
        self.image = None           # PIL Image (full-res)
        self.render = None          # PhotoImage (for Tk)
        self.fullscreen = False

        # UI
        self.status = tk.StringVar(value="Open (O) file or folder…")
        self.canvas = tk.Canvas(self, bg="#111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        bar = tk.Frame(self, bg="#181818")
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(bar, textvariable=self.status, fg="#ddd", bg="#181818").pack(side=tk.LEFT, padx=8, pady=4)

        # Bindings
        self.bind("<Left>", lambda e: self.prev())
        self.bind("<Right>", lambda e: self.next())
        self.bind("<space>", lambda e: self.next())
        self.bind("<BackSpace>", lambda e: self.prev())
        self.bind("+", lambda e: self.zoom_by(1.25))
        self.bind("=", lambda e: self.zoom_by(1.25))
        self.bind("-", lambda e: self.zoom_by(0.8))
        self.bind("0", lambda e: self.fit())     # fit to window
        self.bind("1", lambda e: self.set_zoom(1.0))  # 100%
        self.bind("r", lambda e: self.rotate(90))
        self.bind("R", lambda e: self.rotate(90))
        self.bind("f", lambda e: self.toggle_fullscreen())
        self.bind("<Escape>", lambda e: self.exit_fullscreen())
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("o", lambda e: self.open_dialog())
        self.bind("O", lambda e: self.open_dialog())
        self.bind("<MouseWheel>", self._scroll_zoom)         # Windows
        self.bind("<Button-4>", lambda e: self.zoom_by(1.1)) # Linux
        self.bind("<Button-5>", lambda e: self.zoom_by(0.9)) # Linux

        # Start
        if start_path:
            self.load_path(start_path)

    # ---------- File loading ----------
    def open_dialog(self):
        choice = messagebox.askquestion("Open", "Open a *folder*? (No = pick a single file)")
        if choice == "yes":
            folder = filedialog.askdirectory(title="Choose folder")
            if folder:
                self.load_path(Path(folder))
        else:
            f = filedialog.askopenfilename(title="Choose image",
                                           filetypes=[("Images", "*.heic *.heif *.jpg *.jpeg *.png *.webp *.bmp *.tiff")])
            if f:
                self.load_path(Path(f))

    def load_path(self, p: Path):
        p = p.expanduser()
        if p.is_dir():
            self.files = sorted([x for x in Path(p).iterdir() if x.suffix.lower() in SUPPORTED_EXTS])
            self.index = 0
        else:
            self.files = sorted([x for x in p.parent.iterdir() if x.suffix.lower() in SUPPORTED_EXTS])
            try:
                self.index = self.files.index(p)
            except ValueError:
                self.files.append(p)
                self.files.sort()
                self.index = self.files.index(p)

        if not self.files:
            self.status.set("No images found in that location.")
            return
        self.open_index(self.index)

    def open_index(self, i: int):
        if not self.files:
            return
        self.index = i % len(self.files)
        path = self.files[self.index]
        try:
            img = Image.open(path)
            # Lazy-load full decode only when needed
            self.image = img.convert("RGB")
            self.rotation = 0
            self.fit_mode = True
            self.zoom = 1.0
            self.redraw()
            self.status.set(f"{path.name}  [{self.index+1}/{len(self.files)}]  "
                            f"{self.image.width}×{self.image.height}")
        except Exception as e:
            self.status.set(f"Failed to open: {path.name} ({e})")

    # ---------- Navigation ----------
    def next(self):
        if not self.files: return
        self.open_index(self.index + 1)

    def prev(self):
        if not self.files: return
        self.open_index(self.index - 1)

    # ---------- View ops ----------
    def rotate(self, deg: int):
        if self.image is None: return
        self.rotation = (self.rotation + deg) % 360
        self.image = self.image.rotate(-deg, expand=True)
        self.redraw()

    def set_zoom(self, z: float):
        if self.image is None: return
        self.zoom = max(0.05, min(8.0, z))
        self.fit_mode = False
        self.redraw()

    def zoom_by(self, factor: float):
        self.set_zoom(self.zoom * factor)

    def fit(self):
        self.fit_mode = True
        self.redraw()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.attributes("-fullscreen", self.fullscreen)
        self.redraw()

    def exit_fullscreen(self):
        if self.fullscreen:
            self.fullscreen = False
            self.attributes("-fullscreen", False)
            self.redraw()

    def _scroll_zoom(self, event):
        if event.delta > 0:
            self.zoom_by(1.1)
        else:
            self.zoom_by(0.9)

    # ---------- Rendering ----------
    def redraw(self, *_):
        if self.image is None:
            self.canvas.delete("all")
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        img = self.image
        if self.fit_mode:
            scale = min(cw / img.width, ch / img.height)
            scale = max(scale, 0.05)
        else:
            scale = self.zoom

        new_w = max(1, int(img.width * scale))
        new_h = max(1, int(img.height * scale))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.render = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=self.render, anchor="center")

def main():
    start = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    app = MiniViewer(start)
    app.mainloop()

if __name__ == "__main__":
    main()
