import tkinter as tk
from tkinter import ttk, filedialog, messagebox

print("tkinter import completed")

import subprocess, threading, os, sys, random

print("subprocess, threading, os, sys, random imports completed")

import imagej

print("ImageJ import completed")

fiji_directory = "C:\\Users\\janeu\\Downloads\\fiji-latest-win64-jdk\\Fiji"

ij = imagej.init(fiji_directory)

print(f"ImageJ2 version: {ij.getVersion()}")

# ── Colour palette ────────────────────────────────────────────────────────
BG        = "#F7F6F3"
PANEL     = "#FFFFFF"
BORDER    = "#E0DDD6"
ACCENT    = "#1A6FD4"
ACCENT_LT = "#E8F0FB"
TEXT      = "#1C1C1A"
MUTED     = "#6B6963"
SUCCESS   = "#1A7A4A"

SNAKE_GREEN = "#2ECC71"
SNAKE_DARK  = "#27AE60"
SNAKE_HEAD  = "#1ABC9C"
SNAKE_FOOD  = "#E74C3C"

TILE_EMPTY   = "#F0EEE9"
TILE_BORDER  = "#D8D5CE"
TILE_VISITED = "#B5D9F5"   # light blue trail for row/col types
TILE_HEAD    = "#1A6FD4"   # blue head for row/col types
TILE_UNKNOWN = "#E8D5F5"   # soft purple for unknown
TILE_UNK_H   = "#9B59B6"   # purple head for unknown

FONT    = ("Helvetica Neue", 11)
FONT_SB = ("Helvetica Neue", 11, "bold")
FONT_LG = ("Helvetica Neue", 14, "bold")
FONT_SM = ("Helvetica Neue", 9)
FONT_XS = ("Helvetica Neue", 8)


def card(parent, **kw):
    return tk.Frame(parent, bg=PANEL, relief="flat",
                    highlightbackground=BORDER, highlightthickness=1, **kw)

print("Colour palettes loaded")

# ═══════════════════════════════════════════════════════════════════════════
# PATH GENERATORS
# ═══════════════════════════════════════════════════════════════════════════

def make_row_path(rows, cols, direction):
    """Row-by-row: straight lines, carriage return."""
    path = []
    start_right = "Right" in direction
    start_top   = "Down"  in direction
    row_range = range(rows) if start_top else range(rows - 1, -1, -1)
    for r in row_range:
        col_range = range(cols) if start_right else range(cols - 1, -1, -1)
        for c in col_range:
            path.append((r, c))
    return path

def make_col_path(rows, cols, direction):
    """Column-by-column: straight columns, carriage return."""
    path = []
    start_down  = "Down"  in direction
    start_right = "Right" in direction
    col_range = range(cols) if start_right else range(cols - 1, -1, -1)
    for c in col_range:
        row_range = range(rows) if start_down else range(rows - 1, -1, -1)
        for r in row_range:
            path.append((r, c))
    return path

def make_snake_row_path(rows, cols, direction):
    """Snake by rows: zigzag across rows."""
    path = []
    start_right = "Right" in direction
    start_top   = "Down"  in direction
    row_range = range(rows) if start_top else range(rows - 1, -1, -1)
    for ri, r in enumerate(row_range):
        if start_right:
            col_range = range(cols) if ri % 2 == 0 else range(cols - 1, -1, -1)
        else:
            col_range = range(cols - 1, -1, -1) if ri % 2 == 0 else range(cols)
        for c in col_range:
            path.append((r, c))
    return path

def make_snake_col_path(rows, cols, direction):
    """Snake by columns: zigzag across columns."""
    path = []
    start_down  = "Down"  in direction
    start_right = "Right" in direction
    col_range = range(cols) if start_right else range(cols - 1, -1, -1)
    for ci, c in enumerate(col_range):
        if start_down:
            row_range = range(rows) if ci % 2 == 0 else range(rows - 1, -1, -1)
        else:
            row_range = range(rows - 1, -1, -1) if ci % 2 == 0 else range(rows)
        for r in row_range:
            path.append((r, c))
    return path

def make_unknown_path(rows, cols):
    """Unknown: random walk that visits every cell once (shuffled)."""
    cells = [(r, c) for r in range(rows) for c in range(cols)]
    random.shuffle(cells)
    return cells

print("Path generators defined")

# ═══════════════════════════════════════════════════════════════════════════
# ANIMATED TILE PREVIEW
# ═══════════════════════════════════════════════════════════════════════════

class TilePreview(tk.Canvas):
    """
    Generic animated grid preview.

    style:  'snake'   – green snake colours (for snake types)
            'linear'  – blue head / blue trail (for row/col types)
            'unknown' – purple head / scattered (for unknown)
    """
    ROWS     = 4
    COLS     = 5
    CELL     = 14
    GAP      = 2
    TAIL_LEN = 5
    SPEED_MS = 100

    def __init__(self, parent, path, style="linear", **kw):
        w = self.COLS * (self.CELL + self.GAP) - self.GAP
        h = self.ROWS * (self.CELL + self.GAP) - self.GAP
        super().__init__(parent, width=w, height=h,
                         bg=PANEL, highlightthickness=0, **kw)
        self._path     = path
        self._style    = style
        self._step     = 0
        self._after_id = None
        self._cells    = {}
        self._draw_base()
        self._animate()

    def _cell_xy(self, r, c):
        return c * (self.CELL + self.GAP), r * (self.CELL + self.GAP)

    def _draw_base(self):
        for r in range(self.ROWS):
            for c in range(self.COLS):
                x, y = self._cell_xy(r, c)
                rid = self.create_rectangle(
                    x, y, x + self.CELL, y + self.CELL,
                    fill=TILE_EMPTY, outline=TILE_BORDER, width=0.5)
                self._cells[(r, c)] = rid

    def _animate(self):
        n = len(self._path)

        # reset all cells
        for rid in self._cells.values():
            self.itemconfigure(rid, fill=TILE_EMPTY)

        # pick colours based on style
        if self._style == "snake":
            col_head  = SNAKE_HEAD
            col_body  = SNAKE_GREEN
        elif self._style == "unknown":
            col_head  = TILE_UNK_H
            col_body  = TILE_UNKNOWN
        else:                          # linear
            col_head  = TILE_HEAD
            col_body  = TILE_VISITED

        # draw tail + head
        for i in range(max(0, self._step - self.TAIL_LEN), self._step + 1):
            r, c = self._path[i % n]
            color = col_head if i == self._step else col_body
            self.itemconfigure(self._cells[(r, c)], fill=color)

        self._step    += 1
        self._after_id = self.after(self.SPEED_MS, self._animate)

    def stop(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

print("TilePreview class defined")

# ═══════════════════════════════════════════════════════════════════════════
# DIRECTION DATA
# ═══════════════════════════════════════════════════════════════════════════

DIRECTIONS = {
    "Grid: row-by-row": [
        ("Right & Down", "Start top-left → right, then down"),
        ("Left & Down",  "Start top-right ← left, then down"),
        ("Right & Up",   "Start bottom-left → right, then up"),
        ("Left & Up",    "Start bottom-right ← left, then up"),
    ],
    "Grid: column-by-column": [
        ("Down & Right", "Start top-left ↓ down, then right"),
        ("Down & Left",  "Start top-right ↓ down, then left"),
        ("Up & Right",   "Start bottom-left ↑ up, then right"),
        ("Up & Left",    "Start bottom-right ↑ up, then left"),
    ],
    "Grid: snake by rows": [
        ("Right & Down", "Start top-left → snake rightward down"),
        ("Left & Down",  "Start top-right ← snake leftward down"),
        ("Right & Up",   "Start bottom-left → snake rightward up"),
        ("Left & Up",    "Start bottom-right ← snake leftward up"),
    ],
    "Grid: snake by columns": [
        ("Down & Right", "Start top-left ↓ snake downward right"),
        ("Down & Left",  "Start top-right ↓ snake downward left"),
        ("Up & Right",   "Start bottom-left ↑ snake upward right"),
        ("Up & Left",    "Start bottom-right ↑ snake upward left"),
    ],
}

ROWS_P, COLS_P = TilePreview.ROWS, TilePreview.COLS

def _path_for(acq_type, direction):
    """Return (path, style) for a given type + direction."""
    if acq_type == "Grid: row-by-row":
        return make_row_path(ROWS_P, COLS_P, direction), "linear"
    if acq_type == "Grid: column-by-column":
        return make_col_path(ROWS_P, COLS_P, direction), "linear"
    if acq_type == "Grid: snake by rows":
        return make_snake_row_path(ROWS_P, COLS_P, direction), "snake"
    if acq_type == "Grid: snake by columns":
        return make_snake_col_path(ROWS_P, COLS_P, direction), "snake"
    return make_unknown_path(ROWS_P, COLS_P), "unknown"

print("Direction data and path helper defined")

# ═══════════════════════════════════════════════════════════════════════════
# STEP 1 — ACQUISITION TYPE
# ═══════════════════════════════════════════════════════════════════════════

class StepType(tk.Frame):
    # Representative directions for the type-level preview
    TYPE_DIR = {
        "Grid: row-by-row":       "Right & Down",
        "Grid: column-by-column": "Down & Right",
        "Grid: snake by rows":    "Right & Down",
        "Grid: snake by columns": "Down & Right",
        "Unknown positions":      None,
    }
    TYPE_DESC = {
        "Grid: row-by-row":       "One full row at a time, like reading text",
        "Grid: column-by-column": "One full column at a time",
        "Grid: snake by rows":    "Rows in a zigzag / boustrophedon pattern",
        "Grid: snake by columns": "Columns in a zigzag / boustrophedon pattern",
        "Unknown positions":      "Let Fiji auto-detect layout (slower, no hint given)",
    }

    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        tk.Label(self, text="Step 1 · Acquisition type",
                 font=FONT_LG, bg=BG, fg=TEXT).pack(anchor="w", padx=32, pady=(28, 2))
        tk.Label(self, text="How were the tiles acquired by the camera?",
                 font=FONT, bg=BG, fg=MUTED).pack(anchor="w", padx=32, pady=(0, 16))

        self.var       = tk.StringVar(value="Grid: row-by-row")
        self._btns     = {}
        self._previews = {}

        wrap = tk.Frame(self, bg=BG)
        wrap.pack(fill="x", padx=32)

        for key in self.TYPE_DIR:
            row = card(wrap)
            row.pack(fill="x", pady=4)

            rb = tk.Radiobutton(row, variable=self.var, value=key,
                                bg=PANEL, activebackground=ACCENT_LT,
                                selectcolor=PANEL, cursor="hand2",
                                command=self._refresh)
            rb.grid(row=0, column=0, rowspan=2, padx=(12, 4), pady=10, sticky="n")

            tk.Label(row, text=key, font=FONT_SB, bg=PANEL, fg=TEXT,
                     anchor="w").grid(row=0, column=1, sticky="w", pady=(10, 0))
            tk.Label(row, text=self.TYPE_DESC[key], font=FONT_SM, bg=PANEL, fg=MUTED,
                     anchor="w").grid(row=1, column=1, sticky="w", pady=(0, 10))
            row.columnconfigure(1, weight=1)
            self._btns[key] = row

            direction = self.TYPE_DIR[key]
            path, style = _path_for(key, direction)
            preview = TilePreview(row, path, style)
            preview.grid(row=0, column=2, rowspan=2, padx=(8, 14), pady=8)
            self._previews[key] = preview

        self._refresh()

    def _refresh(self):
        sel = self.var.get()
        for key, row in self._btns.items():
            row.configure(
                highlightbackground=ACCENT if key == sel else BORDER,
                highlightthickness=2 if key == sel else 1)

    def validate(self): return True
    def get_values(self): return {"type": self.var.get()}


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2 — DIRECTION
# ═══════════════════════════════════════════════════════════════════════════

class StepDirection(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        tk.Label(self, text="Step 2 · Start corner & direction",
                 font=FONT_LG, bg=BG, fg=TEXT).pack(anchor="w", padx=32, pady=(28, 2))
        tk.Label(self, text="Where does the acquisition start and which way does it travel?",
                 font=FONT, bg=BG, fg=MUTED).pack(anchor="w", padx=32, pady=(0, 16))

        self.var           = tk.StringVar()
        self._current_type = None
        self._btns         = {}
        self._previews     = {}

        self.wrap = tk.Frame(self, bg=BG)
        self.wrap.pack(fill="x", padx=32)

        self.unknown_lbl = tk.Label(
            self, bg=BG, fg=MUTED, font=FONT, anchor="w",
            text="Not applicable — Fiji will determine tile positions automatically.")

    def load_for_type(self, acq_type):
        if acq_type == self._current_type:
            return
        self._current_type = acq_type

        for p in self._previews.values():
            p.stop()
        for w in self.wrap.winfo_children():
            w.destroy()
        self._btns.clear()
        self._previews.clear()
        self.unknown_lbl.pack_forget()

        if acq_type == "Unknown positions":
            self.unknown_lbl.pack(anchor="w", padx=32)
            return

        dirs = DIRECTIONS[acq_type]
        self.var.set(dirs[0][0])

        for key, desc in dirs:
            row = card(self.wrap)
            row.pack(fill="x", pady=4)

            rb = tk.Radiobutton(row, variable=self.var, value=key,
                                bg=PANEL, activebackground=ACCENT_LT,
                                selectcolor=PANEL, cursor="hand2",
                                command=self._refresh)
            rb.grid(row=0, column=0, rowspan=2, padx=(12, 4), pady=10, sticky="n")

            tk.Label(row, text=key,  font=FONT_SB, bg=PANEL, fg=TEXT,
                     anchor="w").grid(row=0, column=1, sticky="w", pady=(10, 0))
            tk.Label(row, text=desc, font=FONT_SM, bg=PANEL, fg=MUTED,
                     anchor="w").grid(row=1, column=1, sticky="w", pady=(0, 10))
            row.columnconfigure(1, weight=1)
            self._btns[key] = row

            path, style = _path_for(acq_type, key)
            preview = TilePreview(row, path, style)
            preview.grid(row=0, column=2, rowspan=2, padx=(8, 14), pady=8)
            self._previews[key] = preview

        self._refresh()

    def _refresh(self):
        sel = self.var.get()
        for key, row in self._btns.items():
            row.configure(
                highlightbackground=ACCENT if key == sel else BORDER,
                highlightthickness=2 if key == sel else 1)

    def validate(self): return True

    def get_values(self):
        if self._current_type == "Unknown positions":
            return {"order": None}
        return {"order": self.var.get()}

# ═══════════════════════════════════════════════════════════════════════════
# STEP 3 — GRID DIMENSIONS
# ═══════════════════════════════════════════════════════════════════════════

class StepGrid(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        tk.Label(self, text="Step 3 · Grid dimensions & overlap",
                 font=FONT_LG, bg=BG, fg=TEXT).pack(anchor="w", padx=32, pady=(28, 2))
        tk.Label(self, text="How many tiles make up the grid, and how much do they overlap?",
                 font=FONT, bg=BG, fg=MUTED).pack(anchor="w", padx=32, pady=(0, 16))

        wrap = card(self)
        wrap.pack(fill="x", padx=32, pady=4)
        wrap.columnconfigure(1, weight=1)

        fields = [
            ("Columns", "grid_x",  "",  "Number of tile columns"),
            ("Rows", "grid_y",  "",  "Number of tile rows"),
            ("Overlap  (%)", "overlap", "", "Estimated % overlap between adjacent tiles  (0 – 80)"), #add blank option for unknown
        ]
        self._vars = {}
        for r, (label, key, default, hint) in enumerate(fields):
            tk.Label(wrap, text=label, font=FONT_SB, bg=PANEL, fg=TEXT,
                     anchor="w").grid(row=r*2, column=0, padx=(16, 24), pady=(14, 0), sticky="w")
            v = tk.StringVar(value=default)
            self._vars[key] = v
            tk.Entry(wrap, textvariable=v, font=FONT, width=8,
                     relief="flat", bg=BG, fg=TEXT,
                     highlightbackground=BORDER, highlightthickness=1
                     ).grid(row=r*2, column=1, padx=(0, 16), pady=(14, 0), sticky="w")
            tk.Label(wrap, text=hint, font=FONT_SM, bg=PANEL, fg=MUTED,
                     anchor="w").grid(row=r*2+1, column=0, columnspan=2,
                                      padx=(16, 16), pady=(2, 0), sticky="w")
        tk.Label(wrap, bg=PANEL).grid(row=len(fields)*2, column=0, pady=(8, 0))

    def validate(self):
        for key, v in self._vars.items():
            raw = v.get().strip()
            try:
                val = float(raw)
                if key == "overlap" and not (0 <= val <= 80): raise ValueError
                if key != "overlap" and (val < 1 or int(val) != val): raise ValueError
            except ValueError:
                messagebox.showerror("Invalid input",
                    f"'{raw}' is not valid for {key}.\n"
                    "Columns and Rows must be whole numbers ≥ 1.\n"
                    "Overlap must be between 0 and 80.")
                return False
        return True

    def get_values(self):
        return {k: v.get().strip() for k, v in self._vars.items()}

# ═══════════════════════════════════════════════════════════════════════════
# STEP 4 — FILE PATHS
# ═══════════════════════════════════════════════════════════════════════════

class StepPaths(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        tk.Label(self, text="Step 4 · File paths",
                 font=FONT_LG, bg=BG, fg=TEXT).pack(anchor="w", padx=32, pady=(28, 2))
        tk.Label(self, text="Tell Fiji where everything lives.",
                 font=FONT, bg=BG, fg=MUTED).pack(anchor="w", padx=32, pady=(0, 16))

        wrap = card(self)
        wrap.pack(fill="x", padx=32, pady=4)
        wrap.columnconfigure(1, weight=1)

        self._vars = {}
        fields = [
            ("fiji_path",    "Fiji executable",  self._guess_fiji(), False, True),
            ("input_dir",    "Tile image folder", "",                True,  False),
            ("output_dir",   "Output folder",     "",                True,  False),
            ("file_pattern", "File name pattern", "tile_{i}.tif",    False, False),
            ("first_index", "First tile index",   "",               False, False),
        ]
        hints = {
            "fiji_path":    "Full path to the Fiji/ImageJ executable",
            "input_dir":    "Folder containing all tile images",
            "output_dir":   "Where the stitched result will be saved",
            "file_pattern": "Use {i} as the tile index placeholder  (e.g. img_{i}.tif), any extension is fine",
            "first_index":  "Index number of the first tile file (number in the placeholder {i})",
        }
        for r, (key, label, default, is_dir, is_file) in enumerate(fields):
            tk.Label(wrap, text=label, font=FONT_SB, bg=PANEL, fg=TEXT,
                     anchor="w").grid(row=r*2, column=0, padx=(16, 12), pady=(14, 0), sticky="w")
            v = tk.StringVar(value=default)
            self._vars[key] = v
            rf = tk.Frame(wrap, bg=PANEL)
            rf.grid(row=r*2, column=1, padx=(0, 12), pady=(14, 0), sticky="ew")
            rf.columnconfigure(0, weight=1)
            tk.Entry(rf, textvariable=v, font=FONT,
                     relief="flat", bg=BG, fg=TEXT,
                     highlightbackground=BORDER, highlightthickness=1
                     ).grid(row=0, column=0, sticky="ew", ipady=4)
            if is_dir or is_file:
                tk.Button(rf, text="Browse…", font=FONT_SM,
                          relief="flat", bg=BORDER, fg=TEXT, cursor="hand2",
                          command=lambda k=key, d=is_dir: self._browse(k, d)
                          ).grid(row=0, column=1, padx=(6, 0))
            tk.Label(wrap, text=hints[key], font=FONT_SM, bg=PANEL, fg=MUTED,
                     anchor="w").grid(row=r*2+1, column=0, columnspan=2,
                                      padx=(16, 12), pady=(2, 0), sticky="w")
        tk.Label(wrap, bg=PANEL).grid(row=len(fields)*2, column=0, pady=(8, 0))

    def _guess_fiji(self):
        candidates = [
            "/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx",
            fiji_directory,
            "/opt/Fiji.app/ImageJ-linux64",
        ]
        for c in candidates:
            if os.path.exists(c): return c
        if sys.platform == "darwin": return "/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx"
        if sys.platform == "win32":  return fiji_directory
        return "/opt/Fiji.app/ImageJ-linux64"

    def _browse(self, key, is_dir):
        path = (filedialog.askdirectory(title="Select folder") if is_dir
                else filedialog.askopenfilename(title="Select Fiji executable"))
        if path: self._vars[key].set(path)

    def validate(self):
        if not self._vars["fiji_path"].get().strip():
            messagebox.showerror("Missing path", "Please specify the path to the Fiji executable.")
            return False
        if not self._vars["input_dir"].get().strip():
            messagebox.showerror("Missing path", "Please specify the tile image folder.")
            return False
        if not self._vars["output_dir"].get().strip():
            messagebox.showerror("Missing path", "Please specify an output folder.")
            return False
        if "{i}" not in self._vars["file_pattern"].get():
            if not messagebox.askyesno("No index placeholder",
                "The file pattern has no {i}.\nFiji uses {i} to number tiles.\nContinue anyway?"):
                return False
        if not self._vars["first_index"].get().strip():
            messagebox.showerror("No first index",
                "The first tile index is empty. Please specify it to determine numbering.")
            return False
        return True

    def get_values(self):
        return {k: v.get().strip() for k, v in self._vars.items()}


# ═══════════════════════════════════════════════════════════════════════════
# SNAKE GAME EASTER EGG
# ═══════════════════════════════════════════════════════════════════════════

class SnakeGame(tk.Toplevel):
    CELL  = 18
    COLS  = 22
    ROWS  = 18
    SPEED = 120

    def __init__(self, parent):
        super().__init__(parent)
        self.title("🐍  Snake — arrow keys to play")
        self.configure(bg="#1C1C1A")
        self.resizable(False, False)
        W, H = self.COLS * self.CELL, self.ROWS * self.CELL
        self._canvas = tk.Canvas(self, width=W, height=H,
                                 bg="#1C1C1A", highlightthickness=0)
        self._canvas.pack()
        tk.Label(self, text="Arrow keys to move  ·  R to restart",
                 font=("Courier New", 10), bg="#1C1C1A", fg="#5F5E5A").pack(pady=(4, 0))
        self._score_var = tk.StringVar(value="Score: 0")
        tk.Label(self, textvariable=self._score_var,
                 font=("Courier New", 12, "bold"), bg="#1C1C1A",
                 fg=SNAKE_GREEN).pack(pady=(2, 8))
        self.bind("<KeyPress>", self._key)
        self.bind("<r>", lambda e: self._reset())
        self.bind("<R>", lambda e: self._reset())
        self._reset()

    def _reset(self):
        cx, cy = self.COLS // 2, self.ROWS // 2
        self._snake = [(cx, cy), (cx-1, cy), (cx-2, cy)]
        self._dir   = (1, 0);  self._next = (1, 0)
        self._food  = self._place_food()
        self._alive = True;    self._score = 0
        self._score_var.set("Score: 0")
        if hasattr(self, "_after_id"):
            self.after_cancel(self._after_id)
        self._tick()

    def _place_food(self):
        occ = set(self._snake)
        while True:
            p = (random.randint(0, self.COLS-1), random.randint(0, self.ROWS-1))
            if p not in occ: return p

    def _key(self, e):
        m = {"Up":(0,-1),"Down":(0,1),"Left":(-1,0),"Right":(1,0)}
        if e.keysym in m:
            nd = m[e.keysym]
            if (nd[0] != -self._dir[0] or nd[1] != -self._dir[1]):
                self._next = nd

    def _tick(self):
        if not self._alive: return
        self._dir = self._next
        hx, hy   = self._snake[0]
        nx, ny   = hx + self._dir[0], hy + self._dir[1]
        if not (0 <= nx < self.COLS and 0 <= ny < self.ROWS) or (nx, ny) in self._snake:
            self._alive = False
            self._draw()
            self._canvas.create_text(
                self.COLS*self.CELL//2, self.ROWS*self.CELL//2,
                text="GAME OVER\npress R to restart",
                fill=SNAKE_FOOD, font=("Courier New", 16, "bold"), justify="center")
            return
        self._snake.insert(0, (nx, ny))
        if (nx, ny) == self._food:
            self._score += 1
            self._score_var.set(f"Score: {self._score}")
            self._food = self._place_food()
        else:
            self._snake.pop()
        self._draw()
        self._after_id = self.after(self.SPEED, self._tick)

    def _draw(self):
        c = self._canvas;  c.delete("all")
        C = self.CELL
        for gx in range(0, self.COLS*C, C*4):
            c.create_line(gx, 0, gx, self.ROWS*C, fill="#252523", width=0.5)
        for gy in range(0, self.ROWS*C, C*4):
            c.create_line(0, gy, self.COLS*C, gy, fill="#252523", width=0.5)
        fx, fy = self._food
        c.create_oval(fx*C+3, fy*C+3, fx*C+C-3, fy*C+C-3, fill=SNAKE_FOOD, outline="")
        for i, (sx, sy) in enumerate(self._snake):
            col = SNAKE_HEAD if i == 0 else SNAKE_GREEN
            c.create_rectangle(sx*C+1, sy*C+1, sx*C+C-1, sy*C+C-1,
                                fill=col, outline=SNAKE_DARK, width=1)
# ═══════════════════════════════════════════════════════════════════════════
# STEP 5 — RENAME FILES
# ═══════════════════════════════════════════════════════════════════════════

class StepRename(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        tk.Label(self, text="Step 5 · Rename tile images (optional)",
                 font=FONT_LG, bg=BG, fg=TEXT).pack(anchor="w", padx=32, pady=(28, 2))
        tk.Label(self, text="Sorts images alphabetically and renames them with a base name and index number.",
                 font=FONT, bg=BG, fg=MUTED).pack(anchor="w", padx=32, pady=(0, 16))

        wrap = card(self)
        wrap.pack(fill="x", padx=32, pady=4)
        wrap.columnconfigure(1, weight=1)

        self._vars = {}

        # Source folder
        tk.Label(wrap, text="Image folder", font=FONT_SB, bg=PANEL, fg=TEXT,
                 anchor="w").grid(row=0, column=0, padx=(16, 12), pady=(14, 0), sticky="w")
        rf1 = tk.Frame(wrap, bg=PANEL)
        rf1.grid(row=0, column=1, padx=(0, 12), pady=(14, 0), sticky="ew")
        rf1.columnconfigure(0, weight=1)
        self._vars["rename_dir"] = tk.StringVar()
        tk.Entry(rf1, textvariable=self._vars["rename_dir"], font=FONT,
                 relief="flat", bg=BG, fg=TEXT,
                 highlightbackground=BORDER, highlightthickness=1
                 ).grid(row=0, column=0, sticky="ew", ipady=4)
        tk.Button(rf1, text="Browse…", font=FONT_SM,
                  relief="flat", bg=BORDER, fg=TEXT, cursor="hand2",
                  command=self._browse).grid(row=0, column=1, padx=(6, 0))
        tk.Label(wrap, text="Folder containing the tile images to rename",
                 font=FONT_SM, bg=PANEL, fg=MUTED, anchor="w"
                 ).grid(row=1, column=0, columnspan=2, padx=(16, 12), pady=(2, 0), sticky="w")

        # Base name
        tk.Label(wrap, text="Base name", font=FONT_SB, bg=PANEL, fg=TEXT,
                 anchor="w").grid(row=2, column=0, padx=(16, 12), pady=(14, 0), sticky="w")
        self._vars["rename_base"] = tk.StringVar(value="tile")
        tk.Entry(wrap, textvariable=self._vars["rename_base"], font=FONT, width=16,
                 relief="flat", bg=BG, fg=TEXT,
                 highlightbackground=BORDER, highlightthickness=1
                 ).grid(row=2, column=1, padx=(0, 16), pady=(14, 0), sticky="w")
        tk.Label(wrap, text="Files will be renamed to  basename_1.ext, basename_2.ext, …",
                 font=FONT_SM, bg=PANEL, fg=MUTED, anchor="w"
                 ).grid(row=3, column=0, columnspan=2, padx=(16, 12), pady=(2, 0), sticky="w")

        # Start index
        tk.Label(wrap, text="Start index", font=FONT_SB, bg=PANEL, fg=TEXT,
                 anchor="w").grid(row=4, column=0, padx=(16, 12), pady=(14, 0), sticky="w")
        self._vars["rename_start"] = tk.StringVar(value="1")
        tk.Entry(wrap, textvariable=self._vars["rename_start"], font=FONT, width=8,
                 relief="flat", bg=BG, fg=TEXT,
                 highlightbackground=BORDER, highlightthickness=1
                 ).grid(row=4, column=1, padx=(0, 16), pady=(14, 0), sticky="w")
        tk.Label(wrap, text="Number to start counting from (usually matches your first tile index)",
                 font=FONT_SM, bg=PANEL, fg=MUTED, anchor="w"
                 ).grid(row=5, column=0, columnspan=2, padx=(16, 12), pady=(2, 14), sticky="w")

        # Run button + preview log
        self._run_btn = tk.Button(
            self, text="Rename files", font=FONT_SB,
            bg=ACCENT, fg="white", activebackground="#155BB0", activeforeground="white",
            relief="flat", cursor="hand2", padx=16, pady=8,
            command=self._run)
        self._run_btn.pack(anchor="w", padx=32, pady=(12, 8))

        log_wrap = card(self)
        log_wrap.pack(fill="both", expand=True, padx=32, pady=(0, 24))
        self._log_widget = tk.Text(log_wrap, font=("Courier New", 10),
                                   bg="#1C1C1A", fg="#D4D0C8",
                                   relief="flat", state="disabled", wrap="word",
                                   highlightthickness=0, padx=10, pady=10)
        self._log_widget.pack(fill="both", expand=True)

    def _browse(self):
        path = filedialog.askdirectory(title="Select image folder")
        if path:
            self._vars["rename_dir"].set(path)

    def _log(self, text, tag=None):
        self._log_widget.configure(state="normal")
        self._log_widget.insert("end", text + "\n")
        if tag:
            start = f"end - {len(text)+1}c"
            self._log_widget.tag_add(tag, start, "end-1c")
            self._log_widget.tag_configure("ok",  foreground="#5FBA7D")
            self._log_widget.tag_configure("err", foreground="#E74C3C")
            self._log_widget.tag_configure("hdr", foreground="#6ABFEC")
        self._log_widget.configure(state="disabled")
        self._log_widget.see("end")

    def validate(self): return True

    def get_values(self): return {}   # rename is self-contained, nothing passed forward

    def _run(self):
        folder     = self._vars["rename_dir"].get().strip()
        base       = self._vars["rename_base"].get().strip()
        start_raw  = self._vars["rename_start"].get().strip()

        # ── Input validation ──────────────────────────────────────────
        if not folder:
            messagebox.showerror("Missing folder", "Please select an image folder.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Folder not found", f"Cannot find:\n{folder}")
            return
        if not base:
            messagebox.showerror("Missing name", "Please enter a base name.")
            return
        if not start_raw.isdigit():
            messagebox.showerror("Invalid index", "Start index must be a whole number.")
            return

        start_idx = int(start_raw)

        # ── Collect image files ───────────────────────────────────────
        IMAGE_EXTS = {".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp"}
        files = sorted([
            f for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f))
            and os.path.splitext(f)[1].lower() in IMAGE_EXTS
        ])

        if not files:
            messagebox.showwarning("No images found",
                f"No image files found in:\n{folder}\n\n"
                f"Supported types: {', '.join(sorted(IMAGE_EXTS))}")
            return

        # ── Preview pass — check for conflicts before touching anything ─
        renames = []
        conflicts = []
        for i, fname in enumerate(files):
            ext     = os.path.splitext(fname)[1]
            new     = f"{base}_{start_idx + i}{ext}"
            src     = os.path.join(folder, fname)
            dst     = os.path.join(folder, new)
            renames.append((src, dst, fname, new))
            if os.path.exists(dst) and dst != src:
                conflicts.append(new)

        if conflicts:
            names = "\n".join(conflicts[:8])
            more  = f"\n… and {len(conflicts)-8} more" if len(conflicts) > 8 else ""
            if not messagebox.askyesno("Name conflicts",
                    f"These files already exist and would be overwritten:\n\n"
                    f"{names}{more}\n\nContinue anyway?"):
                return

        # ── Do the rename ─────────────────────────────────────────────
        self._run_btn.configure(state="disabled")
        self._log("─" * 50, "hdr")
        self._log(f"Renaming {len(files)} files in:  {folder}", "hdr")
        self._log("─" * 50, "hdr")

        errors = 0
        for src, dst, old, new in renames:
            try:
                os.rename(src, dst)
                self._log(f"  {old}  →  {new}", "ok")
            except Exception as ex:
                self._log(f"  FAILED {old}: {ex}", "err")
                errors += 1

        self._log("─" * 50, "hdr")
        if errors:
            self._log(f"Done with {errors} error(s).", "err")
        else:
            self._log(f"All {len(files)} files renamed successfully.", "ok")

        self._run_btn.configure(state="normal")

# ═══════════════════════════════════════════════════════════════════════════
# STEP 6 — RUN
# ═══════════════════════════════════════════════════════════════════════════

class StepRun(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG)
        self._app = app

        # Header row with easter egg button
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=32, pady=(28, 2))
        tk.Label(hdr, text="Step 6 · Run stitching",
                 font=FONT_LG, bg=BG, fg=TEXT).pack(side="left")
        tk.Label(hdr, text="(psst)", font=FONT_XS, bg=BG, fg=MUTED).pack(side="right")
        tk.Button(hdr, text="🐍", font=("Helvetica Neue", 16),
                  relief="flat", bg=BG, fg=SNAKE_GREEN, cursor="hand2", bd=0,
                  command=lambda: SnakeGame(self)).pack(side="right", padx=4)

        # Settings summary card
        self.summary_frame = card(self)
        self.summary_frame.pack(fill="x", padx=32, pady=(8, 6))
        self.summary_label = tk.Label(self.summary_frame, text="", font=FONT_SM,
                                      bg=PANEL, fg=TEXT, anchor="w", justify="left")
        self.summary_label.pack(padx=16, pady=12, anchor="w")

        # "Change settings" link — goes back to step 1
        back_lnk = tk.Label(self, text="← Change settings", font=FONT_SM,
                             bg=BG, fg=ACCENT, cursor="hand2")
        back_lnk.pack(anchor="w", padx=32, pady=(0, 8))
        back_lnk.bind("<Button-1>", lambda e: self._app.go_to_step(0))

        # Run button
        self.run_btn = tk.Button(
            self, text="▶  Run Fiji stitching", font=FONT_SB,
            bg=ACCENT, fg="white", activebackground="#155BB0", activeforeground="white",
            relief="flat", cursor="hand2", padx=20, pady=10,
            command=self._run)
        self.run_btn.pack(anchor="w", padx=32, pady=(0, 12))

        # Log output
        log_wrap = card(self)
        log_wrap.pack(fill="both", expand=True, padx=32, pady=(0, 24))
        self.log = tk.Text(log_wrap, font=("Courier New", 10),
                           bg="#1C1C1A", fg="#D4D0C8",
                           relief="flat", state="disabled", wrap="word",
                           highlightthickness=0, padx=10, pady=10)
        self.log.pack(fill="both", expand=True)
        scroll = ttk.Scrollbar(log_wrap, command=self.log.yview)
        self.log["yscrollcommand"] = scroll.set

    def load_summary(self, cfg):
        self._cfg = cfg
        lines = [f"Type     :  {cfg['type']}"]
        if cfg.get("order"):
            lines.append(f"Direction:  {cfg['order']}")
        lines += [
            f"Grid     :  {cfg['grid_x']} columns × {cfg['grid_y']} rows",
            f"Overlap  :  {cfg['overlap']}%",
            f"Input    :  {cfg['input_dir']}",
            f"Output   :  {cfg['output_dir']}",
            f"Pattern  :  {cfg['file_pattern']}",
            f"First index: {cfg['first_index']}",
        ]
        self.summary_label.configure(text="\n".join(lines))

    def _log(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        if tag:
            start = f"end - {len(text)+1}c"
            self.log.tag_add(tag, start, "end-1c")
            self.log.tag_configure("ok",  foreground="#5FBA7D")
            self.log.tag_configure("err", foreground="#E74C3C")
            self.log.tag_configure("hdr", foreground="#6ABFEC")
        self.log.configure(state="disabled")
        self.log.see("end")

    def _run(self):
        self.run_btn.configure(state="disabled", text="Running…")
        self._log("─" * 50, "hdr")
        self._log("Starting Fiji stitching …", "hdr")
        self._log(f"  Type    : {self._cfg['type']}")
        if self._cfg.get("order"):
            self._log(f"  Order   : {self._cfg['order']}")
        self._log(f"  Grid    : {self._cfg['grid_x']} × {self._cfg['grid_y']}  |  overlap {self._cfg['overlap']}%")
        self._log(f"  Input   : {self._cfg['input_dir']}")
        self._log(f"  Output  : {self._cfg['output_dir']}")
        self._log("─" * 50, "hdr")

        os.makedirs(self._cfg["output_dir"], exist_ok=True)

        def worker():
            try:
                cfg = self._cfg
                inp = cfg["input_dir"].replace("\\", "/")
                out = cfg["output_dir"].replace("\\", "/")
                pat = cfg["file_pattern"]

                # self._log("Initialising Fiji (this can take a minute) …")
                # # ij = imagej.init(cfg["fiji_path"])
                # # self._log(f"ImageJ version: {ij.getVersion()}")
                # self._log("Running Grid/Collection stitching …")

                # ── Build the args dict ───────────────────────────────
                args = {
                    "type":                              f"[{cfg['type']}]", 
                    "grid_size_x":                       int(cfg["grid_x"]), 
                    "grid_size_y":                       int(cfg["grid_y"]),
                    "tile_overlap":                      int(cfg["overlap"]),
                    "first_file_index_i":                int(cfg["first_index"]),
                    "directory":                         f"[{inp}]",
                    "file_names":                        pat,
                    "fusion_method":                     "[Linear Blending]",
                    "regression_threshold":              0.30,
                    "max/avg_displacement_threshold":    2.50,
                    "absolute_displacement_threshold":   3.50,
                    "compute_overlap":                   "[compute overlap]",
                    "computation_parameters":            "[Save memory (but be slower)]", #"[Safe computation time (but use more RAM)]",
                    "image_output":                      "[Write to disk]",
                    "output_directory":                  f"[{out}]",
                }
                if cfg.get("order"):
                    args["order"] = f"[{cfg['order']}]"
                
                ij.py.run_macro(f"""
    run("Grid/Collection stitching", "type={args['type']} grid_size_x={args['grid_size_x']} grid_size_y={args['grid_size_y']} tile_overlap={args['tile_overlap']} first_file_index_i={args['first_file_index_i']} directory={args['directory']} file_names={args['file_names']} fusion_method={args['fusion_method']} regression_threshold={args['regression_threshold']} max/avg_displacement_threshold={args['max/avg_displacement_threshold']} absolute_displacement_threshold={args['absolute_displacement_threshold']} compute_overlap computation_parameters={args['computation_parameters']} image_output={args['image_output']} output_directory={args['output_directory']}");

    output_dir = "{out}";

    // Open the three stitched channel files
    open(output_dir + "/img_t1_z1_c1")
    open(output_dir + "/img_t1_z1_c2")
    open(output_dir + "/img_t1_z1_c3")

    // Image > Color > Merge Channels
    run("Merge Channels...", "c1=img_t1_z1_c1 c2=img_t1_z1_c2 c3=img_t1_z1_c3 create");

    // Image > Color > Stack to RGB
    run("Stack to RGB");

    // Save the resulting RGB image
    saveAs("Tiff", output_dir + "/stitched_RGB.tif");
    close();
""")
                os.remove(f"{out}/TileConfiguration.txt")
                os.remove(f"{out}/TileConfiguration.registered.txt")
                os.remove(f"{out}/img_t1_z1_c1")
                os.remove(f"{out}/img_t1_z1_c2")
                os.remove(f"{out}/img_t1_z1_c3")
            except ImportError:
                self._log("\npyimagej is not installed.", "err")
                self._log("Run:  pip install pyimagej scyjava", "err")
            except Exception as ex:
                self._log(f"\nError: {ex}", "err")
            finally:
                self.run_btn.configure(state="normal", text="▶  Run again")

        threading.Thread(target=worker, daemon=False).start()

# ═══════════════════════════════════════════════════════════════════════════
# MAIN WIZARD WINDOW
# ══════
class FijiWizard(tk.Tk):
    STEPS = ["Type", "Direction", "Grid", "Paths", "Rename", "Run"]

    def __init__(self):
        super().__init__()
        self.title("Fiji · Grid/Collection Stitching Wizard")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(680, 700)
        self._step_idx = 0
        self._build_ui()

    def _build_ui(self):
        # Progress bar
        prog = tk.Frame(self, bg=PANEL,
                        highlightbackground=BORDER, highlightthickness=1)
        prog.pack(fill="x")
        self._prog_labels = []
        for i, name in enumerate(self.STEPS):
            col = tk.Frame(prog, bg=PANEL)
            col.pack(side="left", expand=True, fill="both")
            dot = tk.Label(col, text="●", font=("Helvetica Neue", 14), bg=PANEL, fg=MUTED)
            dot.pack(pady=(10, 0))
            lbl = tk.Label(col, text=f"Step {i+1}\n{name}", font=FONT_SM,
                           bg=PANEL, fg=MUTED, justify="center")
            lbl.pack(pady=(0, 10))
            self._prog_labels.append((dot, lbl))
            if i < len(self.STEPS) - 1:
                tk.Frame(prog, bg=BORDER, width=1).pack(side="left", fill="y", pady=8)

        # Scrollable container
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        self._canvas_scroll = tk.Canvas(outer, bg=BG, highlightthickness=0)
        self._canvas_scroll.pack(side="left", fill="both", expand=True)

        vsb = ttk.Scrollbar(outer, orient="vertical",
                            command=self._canvas_scroll.yview)
        vsb.pack(side="right", fill="y")
        self._canvas_scroll.configure(yscrollcommand=vsb.set)

        self._container = tk.Frame(self._canvas_scroll, bg=BG)
        self._win_id = self._canvas_scroll.create_window(
            (0, 0), window=self._container, anchor="nw")

        self._container.bind("<Configure>", self._on_frame_configure)
        self._canvas_scroll.bind("<Configure>", self._on_canvas_configure)
        self._canvas_scroll.bind("<MouseWheel>",
            lambda e: self._canvas_scroll.yview_scroll(-1*(e.delta//120), "units"))
        self._canvas_scroll.bind("<Button-4>",
            lambda e: self._canvas_scroll.yview_scroll(-1, "units"))
        self._canvas_scroll.bind("<Button-5>",
            lambda e: self._canvas_scroll.yview_scroll(1, "units"))

        # Build pages
        self._step_type      = StepType(self._container)
        self._step_direction = StepDirection(self._container)
        self._step_grid      = StepGrid(self._container)
        self._step_paths     = StepPaths(self._container)
        self._step_rename    = StepRename(self._container)
        self._step_run       = StepRun(self._container, self)

        self._pages = [
            self._step_type,
            self._step_direction,
            self._step_grid,
            self._step_paths,
             self._step_rename,
            self._step_run,
        ]

        # Nav bar
        nav = tk.Frame(self, bg=PANEL,
                       highlightbackground=BORDER, highlightthickness=1)
        nav.pack(fill="x", side="bottom")

        self._back_btn = tk.Button(
            nav, text="← Back", font=FONT, width=10,
            relief="flat", bg=BG, fg=TEXT,
            activebackground=BORDER, cursor="hand2",
            command=self._go_back)
        self._back_btn.pack(side="left", padx=16, pady=12)

        self._next_btn = tk.Button(
            nav, text="Next →", font=FONT_SB, width=12,
            relief="flat", bg=ACCENT, fg="white",
            activebackground="#155BB0", activeforeground="white",
            cursor="hand2", command=self._go_next)
        self._next_btn.pack(side="right", padx=16, pady=12)

        self._show_step(0)

    def _on_frame_configure(self, _event):
        self._canvas_scroll.configure(
            scrollregion=self._canvas_scroll.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas_scroll.itemconfig(self._win_id, width=event.width)

    def _show_step(self, idx):
        for p in self._pages:
            p.pack_forget()
        self._pages[idx].pack(fill="both", expand=True)
        self._canvas_scroll.yview_moveto(0)

        for i, (dot, lbl) in enumerate(self._prog_labels):
            if i < idx:
                dot.configure(fg=SUCCESS); lbl.configure(fg=SUCCESS)
            elif i == idx:
                dot.configure(fg=ACCENT);  lbl.configure(fg=ACCENT)
            else:
                dot.configure(fg=MUTED);   lbl.configure(fg=MUTED)

        self._back_btn.configure(state="normal" if idx > 0 else "disabled")

        if idx == len(self._pages) - 1:
            self._next_btn.pack_forget()
        else:
            self._next_btn.pack(side="right", padx=16, pady=12)
            self._next_btn.configure(text="Next →")

    def _go_next(self):
        page = self._pages[self._step_idx]
        if not page.validate(): return
        if self._step_idx == 0:
            self._step_direction.load_for_type(
                self._step_type.get_values()["type"])
        if self._step_idx == len(self._pages) - 2:
            self._step_run.load_summary(self._collect_cfg())
        self._step_idx += 1
        self._show_step(self._step_idx)

    def _go_back(self):
        self._step_idx -= 1
        self._show_step(self._step_idx)

    def go_to_step(self, idx):
        """Jump directly to any step (used by the 'Change settings' link)."""
        self._step_idx = idx
        self._show_step(idx)

    def _collect_cfg(self):
        cfg = {}
        for page in self._pages[:-1]:
            cfg.update(page.get_values())
        return cfg


if __name__ == "__main__":
    app = FijiWizard()
    app.mainloop()
else:
    print("ERROR: This script is meant to be run directly, not imported as a module.")