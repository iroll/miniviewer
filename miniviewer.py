# Minimal Photo Viewer (HEIC-friendly) for Windows/macOS/Linux
# deps: PIL, pillow_heif, tkinter, send2trash (optional)

# ---------- Dependency Check & Auto-Install ----------
# This block checks if required packages are present, and optionally installs them.
import importlib.util
import subprocess
import sys

required_packages = {
    "PIL": "Pillow",
    "pillow_heif": "pillow_heif",
    "tkinter": "tkinter",
    "send2trash": "send2trash",
}

missing = []

for import_name, display_name in required_packages.items():
    if importlib.util.find_spec(import_name) is None:
        missing.append(display_name)

if missing:
    print(f"Missing packages detected: {', '.join(missing)}")
    choice = input("Attempt to install them now with pip? (y/n): ").strip().lower()
    if choice == "y":
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("Packages installed successfully. Relaunching...")
        except subprocess.CalledProcessError:
            print("Package installation failed. Aborting.")
            sys.exit(1)
    else:
        print("Aborting due to missing packages.")
        sys.exit(1)

# ---------- Imports ----------
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import datetime

# Safe delete (if send2trash is available)
try:
    from send2trash import send2trash
    HAS_TRASH = True
except ImportError:
    HAS_TRASH = False

# Make PIL understand .heic via libheif
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception as e:
    # Still works for non-HEIC, but warn
    print("Warning: HEIC support not loaded:", e)

SUPPORTED_EXTS = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

class MiniViewer(tk.Tk):
    
    # Keys that trigger an action and conflict with typing in the rename box.
    # This list must be updated if new single-key/non-modifier shortcuts are added to _bind_keys().
    CONFLICT_BINDINGS = [
        "<Left>", "<Right>", "<space>", "<Delete>", "<BackSpace>", 
        "+", "=", "-", "0", "1", "r", "R", "t", "T", "f", "o", "O"
    ]
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
        self.rename_entry = None
        self.rename_current_path = None

        # UI
        self.status = tk.StringVar(value="Open (O) file or folder…")
        self.canvas = tk.Canvas(self, bg="#111", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        bar = tk.Frame(self, bg="#181818")
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(bar, textvariable=self.status, fg="#ddd", bg="#181818").pack(side=tk.LEFT, padx=8, pady=4)

        # Bindings
        self._bind_keys()

        # Start
        if start_path:
            self.load_path(start_path)

    # ---------- Key Bindings ----------
    
    def _bind_keys(self):
        
        # Navigation
        self.bind("<Left>", lambda e: self.prev())
        self.bind("<Right>", lambda e: self.next())
        self.bind("<space>", lambda e: self.next())
        
        # Deletion
        self.bind("<BackSpace>", lambda e: self.delete_current())
        self.bind("<Delete>", lambda e: self.delete_current())

        # Zoom/Fit
        self.bind("+", lambda e: self.zoom_by(1.25))
        self.bind("=", lambda e: self.zoom_by(1.25))
        self.bind("-", lambda e: self.zoom_by(0.8))
        self.bind("0", lambda e: self.fit())     # fit to window
        self.bind("1", lambda e: self.set_zoom(1.0))  # 100%

        # Rotation
        self.bind("r", lambda e: self.rotate(90))
        self.bind("R", lambda e: self.rotate(-90))
        
        # Rename Activation
        self.bind("t", lambda e: self.start_rename(use_date=False))
        self.bind("T", lambda e: self.start_rename(use_date=True))

        # Fullscreen/Open
        self.bind("f", lambda e: self.toggle_fullscreen())
        self.bind("o", lambda e: self.open_dialog())
        self.bind("O", lambda e: self.open_dialog())

        # Global/Window Events (These remain bound globally)
        self.bind("<Escape>", lambda e: self.cancel_rename_or_exit_fullscreen()) # New combined handler
        self.bind("<Return>", lambda e: self.do_rename()) 
        self.bind("<Configure>", lambda e: self.redraw())
        self.bind("<MouseWheel>", self._scroll_zoom)         # Windows
        self.bind("<Button-4>", lambda e: self.zoom_by(1.1)) # Linux
        self.bind("<Button-5>", lambda e: self.zoom_by(0.9)) # Linux
    
    # ---------- File loading ----------
    def _ask_open_choice(self):
        # Helper for the dialog box for selecting file or folder           
        # 1. Setup the dialog window
        dialog = tk.Toplevel(self)
        dialog.title("Open")
        dialog.resizable(False, False)
        dialog.geometry("250x100")
        
        # Center the dialog over the main window
        x = self.winfo_x() + (self.winfo_width() // 2) - 125
        y = self.winfo_y() + (self.winfo_height() // 2) - 50
        dialog.geometry(f"+{x}+{y}")

        dialog.transient(self)
        dialog.grab_set()
        
        # Use an attribute to store the choice, initialized to None
        self.open_choice = None

        tk.Label(dialog, text="Select Mode:", font=("Arial", 14)).pack(pady=10)

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=5)

        def set_choice_and_destroy(choice):
            self.open_choice = choice
            dialog.destroy()

        # Bind closing the dialog (using the 'X' button) to set choice to None
        dialog.protocol("WM_DELETE_WINDOW", lambda: set_choice_and_destroy(None))

        # 2. Create buttons
        tk.Button(button_frame, text="File", command=lambda: set_choice_and_destroy('file'), width=10).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Folder", command=lambda: set_choice_and_destroy('folder'), width=10).pack(side=tk.RIGHT, padx=10)

        # 3. Wait for the dialog to close (blocks execution until a button is pressed)
        self.wait_window(dialog)
        
        # Return the stored choice
        return self.open_choice
    
    def open_dialog(self):
        # Handler for the dialog box for selecting file or folder           
        # 1. Ask the user for their preferred action using the custom popup
        choice = self._ask_open_choice()

        if choice == 'file':
            # Option 1: User chose to open a single file
            f = filedialog.askopenfilename(
                title="Choose image file",
                filetypes=[("Images", "*.heic *.heif *.jpg *.jpeg *.png *.webp *.bmp *.tiff")]
            )
            if f:
                self.load_path(Path(f))
        
        elif choice == 'folder':
            # Option 2: User chose to open a folder
            folder = filedialog.askdirectory(title="Choose folder")
            if folder:
                self.load_path(Path(folder))

        # Cleanup the temporary attribute
        self.open_choice = None

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

    # ---------- File ops ----------

    def delete_current(self):
        if not self.files: return
        path = self.files[self.index]
        try:
            if HAS_TRASH:
                send2trash(str(path))
            else:
                path.unlink()
            self.status.set(f"Deleted: {path.name}")
            del self.files[self.index]
            if self.index >= len(self.files):
                self.index = max(0, len(self.files)-1)
            if self.files:
                self.open_index(self.index)
            else:
                self.image = None
                self.redraw()
                self.status.set("No images left.")
        except Exception as e:
            self.status.set(f"Failed to delete {path.name}: {e}")

    # ---------- Rename ops ----------
    
    def start_rename(self, use_date: bool):
        if self.image is None: return
        
        # If an entry already exists, cancel/destroy it first
        if self.rename_entry:
            self.cancel_rename() 

        for key in self.CONFLICT_BINDINGS:
            self.unbind(key)

        self.rename_current_path = self.files[self.index]
        path = self.rename_current_path
        
        if use_date:
            try:
                # Get modification time (mtime) and format YYYYMMDD
                timestamp = path.stat().st_mtime
                date_str = datetime.datetime.fromtimestamp(timestamp).strftime("%Y%m%d")
                initial_name = f"{date_str}_"
            except Exception as e:
                self.status.set(f"Error getting date for rename: {e}")
                initial_name = path.stem # Fallback
        else:
            initial_name = path.stem

        # 1. Create the Entry widget
        self.rename_entry = tk.Entry(self, width=50, bg="#333", fg="#fff", 
                                     insertbackground="#fff", font=("Arial", 14))
        self.rename_entry.insert(0, initial_name)
        
        # 2. Place it centered near the bottom
        # Use a window relative placement for the overlay
        self.rename_entry.place(relx=0.5, rely=0.9, anchor=tk.CENTER)
        
        # 3. Give it focus and select the text for quick editing
        self.rename_entry.focus_set()
        if not use_date:
            # Only select everything if we didn't pre-populate the date
            self.rename_entry.select_range(0, tk.END)

    def do_rename(self):
        if self.rename_entry is None: 
            return # Ignore Enter press if not renaming

        new_name_stem = self.rename_entry.get().strip()
        current_path = self.rename_current_path

        if not new_name_stem:
            self.status.set("Rename failed: New name cannot be empty.")
            return

        try:
            # 1. Construct the new path with the original extension
            extension = current_path.suffix
            new_path = current_path.parent / (new_name_stem + extension)

            if new_path == current_path:
                self.status.set("Name is unchanged. Aborting rename.")
                self.cancel_rename()
                return

            # 2. Check for conflicts
            if new_path.exists():
                messagebox.showerror("Conflict", f"File already exists:\n{new_path.name}")
                return # Keep the entry open for correction
            
            # 3. Execute rename
            current_path.rename(new_path)

            # 4. Update internal state
            original_index = self.index
            
            # Remove old path and insert new path, then resort and re-index
            self.files.pop(original_index)
            self.files.append(new_path)
            self.files.sort()
            
            self.index = self.files.index(new_path)
            self.rename_current_path = None

            self.open_index(self.index) # Reload image and update status bar
            self.status.set(f"Renamed to: {new_path.name}")

        except Exception as e:
            self.status.set(f"Rename failed: {e}")
        finally:
            self.cancel_rename() # Clean up Entry widget

    def cancel_rename(self):
        if self.rename_entry:
            self.rename_entry.destroy()
            self.rename_entry = None
            self.rename_current_path = None
            self.focus_set() # Return focus to the main window for navigation
            self._bind_keys() # Resore Keybinds
            
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

    def cancel_rename_or_exit_fullscreen(self):
        if self.rename_entry:
            self.cancel_rename()
        else:
            self.exit_fullscreen()
    
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
