"""Preview panes – left 3-stage preview and right preset thumbnails."""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class PreviewStage(ttk.LabelFrame):
    """A single preview thumbnail with a title."""

    def __init__(self, parent, title, size=120):
        super().__init__(parent, text=title)
        self._size = size
        self._canvas = tk.Canvas(self, width=size, height=size,
                                 bg="#3a3a3a", highlightthickness=0)
        self._canvas.pack(padx=4, pady=4)
        self._photo = None  # prevent GC

    def update_image(self, pil_image: Image.Image):
        img = pil_image.resize((self._size, self._size), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self._canvas.delete("all")
        self._canvas.create_image(
            self._size // 2, self._size // 2, image=self._photo, anchor="center")


class PreviewPanel(ttk.Frame):
    """Left panel showing Base Wood / With Effects / Final Texture."""

    def __init__(self, parent, size=120):
        super().__init__(parent)
        ttk.Label(self, text="Texture Stages",
                  font=("TkDefaultFont", 9, "bold")).pack(pady=(4, 2))
        self.base = PreviewStage(self, "Base Wood", size)
        self.base.pack(padx=4, pady=2)
        self.effects = PreviewStage(self, "With Effects", size)
        self.effects.pack(padx=4, pady=2)
        self.final = PreviewStage(self, "Final Texture", size)
        self.final.pack(padx=4, pady=2)

    def update_previews(self, base_img, effects_img, final_img):
        self.base.update_image(base_img)
        self.effects.update_image(effects_img)
        self.final.update_image(final_img)


class PresetThumbnail(ttk.Frame):
    """A clickable preset thumbnail."""

    def __init__(self, parent, name, image=None, command=None, size=80):
        super().__init__(parent, relief="raised", borderwidth=1)
        self._command = command
        self._size = size
        self._photo = None

        self._canvas = tk.Canvas(self, width=size, height=size,
                                 bg="#4a4a3a", highlightthickness=0, cursor="hand2")
        self._canvas.pack(padx=2, pady=2)
        self._canvas.bind("<Button-1>", self._on_click)

        self._lbl = ttk.Label(self, text=name, anchor="center")
        self._lbl.pack()
        self._lbl.bind("<Button-1>", self._on_click)

        if image:
            self.set_image(image)

    def set_image(self, pil_image: Image.Image):
        img = pil_image.resize((self._size, self._size), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self._canvas.delete("all")
        self._canvas.create_image(
            self._size // 2, self._size // 2, image=self._photo, anchor="center")

    def _on_click(self, _=None):
        if self._command:
            self._command()


class PresetPanel(ttk.Frame):
    """Right panel showing preset thumbnails."""

    def __init__(self, parent, on_select=None):
        super().__init__(parent)
        self._on_select = on_select
        self._thumbnails = {}

        ttk.Label(self, text="Open Textures",
                  font=("TkDefaultFont", 9, "bold")).pack(pady=(4, 2))

        self._container = ttk.Frame(self)
        self._container.pack(fill=tk.BOTH, expand=True)

    def add_preset(self, name, image=None):
        def _select():
            if self._on_select:
                self._on_select(name)

        thumb = PresetThumbnail(self._container, name, image, _select, size=80)
        thumb.pack(padx=4, pady=4, fill=tk.X)
        self._thumbnails[name] = thumb

    def update_thumbnail(self, name, image):
        if name in self._thumbnails:
            self._thumbnails[name].set_image(image)
