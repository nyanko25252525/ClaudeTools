#!/usr/bin/env python3
"""Wood Workshop – Realistic wood texture generator with GUI."""

import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Ensure the package is importable when run directly
_here = Path(__file__).resolve().parent
if str(_here.parent) not in sys.path:
    sys.path.insert(0, str(_here.parent))

from wood_workshop.generator import WoodParams, generate_texture
from wood_workshop.ui.controls import ControlPanel
from wood_workshop.ui.preview import PreviewPanel, PresetPanel

PRESETS_DIR = _here / "presets"


class WoodWorkshop(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("Wood Workshop")
        self.geometry("900x700")
        self.minsize(800, 600)

        self._debounce_id = None
        self._generating = False

        self._build_menu()
        self._build_toolbar()
        self._build_layout()
        self._load_presets()
        self._trigger_update()

    # ── Menu ────────────────────────────────────────────
    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Export PNG...", command=self._export_png)
        file_menu.add_separator()
        file_menu.add_command(label="Save Preset...", command=self._save_preset)
        file_menu.add_command(label="Load Preset...", command=self._load_preset_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Reset to Defaults", command=self._reset_defaults)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        render_menu = tk.Menu(menubar, tearoff=0)
        render_menu.add_command(label="Render Preview", command=self._trigger_update)
        menubar.add_cascade(label="Render", menu=render_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

    # ── Toolbar ─────────────────────────────────────────
    def _build_toolbar(self):
        toolbar = ttk.Frame(self, padding=2)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        ttk.Label(toolbar, text="Render Resolution:").pack(side=tk.LEFT, padx=(8, 4))
        self._res_var = tk.StringVar(value="256 x 256")
        res_combo = ttk.Combobox(
            toolbar, textvariable=self._res_var,
            values=["256 x 256", "512 x 512", "1024 x 1024", "2048 x 2048"],
            state="readonly", width=12,
        )
        res_combo.pack(side=tk.LEFT)

        self._status = ttk.Label(toolbar, text="Ready", anchor="e")
        self._status.pack(side=tk.RIGHT, padx=8)

    # ── Layout ──────────────────────────────────────────
    def _build_layout(self):
        main = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        # Left: preview stages
        self._preview = PreviewPanel(main, size=130)
        main.add(self._preview, weight=0)

        # Centre: controls
        self._controls = ControlPanel(main, on_change=self._on_param_change)
        self._controls.set_render_callback(self._render_full)
        main.add(self._controls, weight=1)

        # Right: preset thumbnails
        self._presets_panel = PresetPanel(main, on_select=self._on_preset_select)
        main.add(self._presets_panel, weight=0)

    # ── Preset management ───────────────────────────────
    def _load_presets(self):
        """Load all JSON presets from the presets directory."""
        self._preset_data = {}
        if not PRESETS_DIR.exists():
            return
        for f in sorted(PRESETS_DIR.glob("*.json")):
            try:
                with open(f, "r") as fp:
                    data = json.load(fp)
                name = data.get("name", f.stem)
                self._preset_data[name] = data
                self._presets_panel.add_preset(name)
            except Exception:
                pass

        # Generate thumbnails for presets in background
        self.after(200, self._generate_preset_thumbnails)

    def _generate_preset_thumbnails(self):
        def _gen():
            for name, data in self._preset_data.items():
                try:
                    p = WoodParams.from_dict(data.get("params", {}))
                    _, _, final = generate_texture(p, 80)
                    self.after(0, lambda n=name, img=final:
                               self._presets_panel.update_thumbnail(n, img))
                except Exception:
                    pass
        threading.Thread(target=_gen, daemon=True).start()

    def _on_preset_select(self, name):
        data = self._preset_data.get(name)
        if data:
            p = WoodParams.from_dict(data.get("params", {}))
            self._controls.set_params(p)
            self._trigger_update()

    def _save_preset(self):
        path = filedialog.asksaveasfilename(
            initialdir=str(PRESETS_DIR),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        params = self._controls.get_params()
        name = Path(path).stem.replace("_", " ").title()
        data = {"name": name, "params": params.to_dict()}
        with open(path, "w") as fp:
            json.dump(data, fp, indent=2)
        messagebox.showinfo("Saved", f"Preset saved to {path}")

    def _load_preset_file(self):
        path = filedialog.askopenfilename(
            initialdir=str(PRESETS_DIR),
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        with open(path, "r") as fp:
            data = json.load(fp)
        p = WoodParams.from_dict(data.get("params", {}))
        self._controls.set_params(p)
        self._trigger_update()

    # ── Generation ──────────────────────────────────────
    def _on_param_change(self):
        """Debounced parameter change handler (300ms)."""
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(300, self._trigger_update)

    def _trigger_update(self):
        """Generate preview at small size."""
        if self._generating:
            return
        self._generating = True
        self._status.config(text="Generating...")
        params = self._controls.get_params()

        def _gen():
            try:
                base, effects, final = generate_texture(params, 256)
                self.after(0, lambda: self._update_previews(base, effects, final))
            except Exception as e:
                self.after(0, lambda: self._status.config(text=f"Error: {e}"))
            finally:
                self._generating = False

        threading.Thread(target=_gen, daemon=True).start()

    def _update_previews(self, base, effects, final):
        self._preview.update_previews(base, effects, final)
        self._status.config(text="Ready")

    def _render_full(self, size=None):
        """Render at full resolution and export."""
        if size is None:
            res_str = self._res_var.get()
            size = int(res_str.split("x")[0].strip())
        self._export_png(size)

    def _export_png(self, size=None):
        if size is None:
            res_str = self._res_var.get()
            size = int(res_str.split("x")[0].strip())

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            initialfile=f"wood_texture_{size}x{size}.png",
        )
        if not path:
            return

        self._status.config(text=f"Rendering {size}x{size}...")
        params = self._controls.get_params()

        def _gen():
            try:
                _, _, final = generate_texture(params, size)
                final.save(path, "PNG")
                self.after(0, lambda: messagebox.showinfo(
                    "Exported", f"Saved {size}x{size} to\n{path}"))
                self.after(0, lambda: self._status.config(text="Ready"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, lambda: self._status.config(text="Ready"))

        threading.Thread(target=_gen, daemon=True).start()

    # ── Misc ────────────────────────────────────────────
    def _reset_defaults(self):
        self._controls.set_params(WoodParams())
        self._trigger_update()

    def _show_about(self):
        messagebox.showinfo(
            "About Wood Workshop",
            "Wood Workshop\n\n"
            "Realistic wood texture generator\n"
            "Built with Python, tkinter, NumPy & Pillow",
        )


def main():
    app = WoodWorkshop()
    app.mainloop()


if __name__ == "__main__":
    main()
