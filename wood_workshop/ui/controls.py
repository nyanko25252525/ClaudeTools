"""UI control widgets for Wood Workshop – sliders, color pickers, dropdowns."""

import tkinter as tk
from tkinter import ttk, colorchooser


class LabeledSlider(ttk.Frame):
    """A slider with label and numeric readout."""

    def __init__(self, parent, label, from_, to, resolution=0.1,
                 initial=0, command=None, **kw):
        super().__init__(parent)
        self._command = command

        self._label = ttk.Label(self, text=label, width=16, anchor="w")
        self._label.pack(side=tk.LEFT, padx=(0, 4))

        self._var = tk.DoubleVar(value=initial)
        self._slider = ttk.Scale(
            self, from_=from_, to=to, orient=tk.HORIZONTAL,
            variable=self._var, command=self._on_change, length=140,
        )
        self._slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._readout = ttk.Label(self, width=7, anchor="e")
        self._readout.pack(side=tk.LEFT, padx=(4, 0))
        self._resolution = resolution
        self._update_readout()

    def _on_change(self, _=None):
        self._update_readout()
        if self._command:
            self._command()

    def _update_readout(self):
        v = self._var.get()
        if self._resolution >= 1:
            self._readout.config(text=f"{int(v)}")
        else:
            self._readout.config(text=f"{v:.1f}")

    def get(self):
        return self._var.get()

    def set(self, val):
        self._var.set(val)
        self._update_readout()


class ColorButton(ttk.Frame):
    """A button showing the current colour that opens a colour chooser."""

    def __init__(self, parent, label, initial_color=(200, 150, 80), command=None):
        super().__init__(parent)
        self._command = command
        self._color = initial_color

        ttk.Label(self, text=label, width=16, anchor="w").pack(side=tk.LEFT)
        self._canvas = tk.Canvas(self, width=60, height=20, bd=1, relief="sunken",
                                 highlightthickness=0)
        self._canvas.pack(side=tk.LEFT, padx=4)
        self._canvas.bind("<Button-1>", self._pick)
        self._btn = ttk.Button(self, text="Color...", width=7, command=self._pick)
        self._btn.pack(side=tk.LEFT)
        self._draw()

    def _draw(self):
        hex_c = "#{:02x}{:02x}{:02x}".format(*self._color)
        self._canvas.delete("all")
        self._canvas.create_rectangle(0, 0, 62, 22, fill=hex_c, outline="")

    def _pick(self, _=None):
        hex_c = "#{:02x}{:02x}{:02x}".format(*self._color)
        result = colorchooser.askcolor(color=hex_c, title="Choose Color")
        if result and result[0]:
            self._color = tuple(int(c) for c in result[0])
            self._draw()
            if self._command:
                self._command()

    def get(self):
        return self._color

    def set(self, rgb_tuple):
        self._color = tuple(rgb_tuple)
        self._draw()


class DropdownSelector(ttk.Frame):
    """Label + Combobox."""

    def __init__(self, parent, label, values, initial=None, command=None):
        super().__init__(parent)
        self._command = command

        ttk.Label(self, text=label, width=16, anchor="w").pack(side=tk.LEFT)
        self._var = tk.StringVar(value=initial or values[0])
        self._combo = ttk.Combobox(
            self, textvariable=self._var, values=values,
            state="readonly", width=12,
        )
        self._combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._combo.bind("<<ComboboxSelected>>", self._on_select)

    def _on_select(self, _=None):
        if self._command:
            self._command()

    def get(self):
        return self._var.get()

    def set(self, val):
        self._var.set(val)


class IntEntry(ttk.Frame):
    """Label + integer entry field."""

    def __init__(self, parent, label, initial=0, command=None):
        super().__init__(parent)
        self._command = command

        ttk.Label(self, text=label, width=16, anchor="w").pack(side=tk.LEFT)
        self._var = tk.IntVar(value=initial)
        self._entry = ttk.Entry(self, textvariable=self._var, width=10)
        self._entry.pack(side=tk.LEFT)
        self._entry.bind("<Return>", self._on_change)
        self._entry.bind("<FocusOut>", self._on_change)

    def _on_change(self, _=None):
        if self._command:
            self._command()

    def get(self):
        try:
            return self._var.get()
        except tk.TclError:
            return 0

    def set(self, val):
        self._var.set(int(val))


class ToggleWithSlider(ttk.Frame):
    """Checkbox toggle + strength slider."""

    def __init__(self, parent, label, initial_on=False, initial_strength=50,
                 command=None):
        super().__init__(parent)
        self._command = command

        self._on_var = tk.BooleanVar(value=initial_on)
        self._chk = ttk.Checkbutton(self, text=label, variable=self._on_var,
                                     command=self._on_change, width=18)
        self._chk.pack(side=tk.LEFT)

        self._strength_var = tk.DoubleVar(value=initial_strength)
        self._slider = ttk.Scale(
            self, from_=0, to=100, orient=tk.HORIZONTAL,
            variable=self._strength_var, command=self._on_change, length=100,
        )
        self._slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._readout = ttk.Label(self, width=5, anchor="e")
        self._readout.pack(side=tk.LEFT, padx=(4, 0))
        self._update_readout()

    def _on_change(self, _=None):
        self._update_readout()
        if self._command:
            self._command()

    def _update_readout(self):
        self._readout.config(text=f"{int(self._strength_var.get())}")

    def get_on(self):
        return self._on_var.get()

    def get_strength(self):
        return self._strength_var.get()

    def set_on(self, val):
        self._on_var.set(val)

    def set_strength(self, val):
        self._strength_var.set(val)
        self._update_readout()


class ControlPanel(ttk.Frame):
    """The main control panel assembling all parameter widgets."""

    def __init__(self, parent, on_change=None):
        super().__init__(parent)
        self._on_change = on_change
        self._build()

    def _cb(self):
        """Callback wrapper for parameter changes."""
        if self._on_change:
            self._on_change()

    def _build(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ── Tab: Start ──
        start_frame = ttk.Frame(notebook, padding=8)
        notebook.add(start_frame, text="Start")
        ttk.Label(start_frame, text="Welcome to Wood Workshop",
                  font=("TkDefaultFont", 11, "bold")).pack(pady=10)
        ttk.Label(start_frame, text="Adjust parameters in the Texture tab\n"
                  "to generate wood textures.\n\n"
                  "Use presets on the right panel\n"
                  "for quick starting points.").pack()

        # ── Tab: Texture ──
        tex_frame = ttk.Frame(notebook, padding=4)
        notebook.add(tex_frame, text="Texture")

        canvas = tk.Canvas(tex_frame)
        scrollbar = ttk.Scrollbar(tex_frame, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux(event):
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        canvas.bind_all("<Button-4>", _on_mousewheel_linux)
        canvas.bind_all("<Button-5>", _on_mousewheel_linux)

        self._build_texture_controls(scroll_frame)

        # ── Tab: Render ──
        render_frame = ttk.Frame(notebook, padding=8)
        notebook.add(render_frame, text="Render")

        ttk.Label(render_frame, text="Render Resolution:").pack(anchor="w", pady=(8, 4))
        self.resolution_var = tk.StringVar(value="256 x 256")
        res_combo = ttk.Combobox(
            render_frame, textvariable=self.resolution_var,
            values=["256 x 256", "512 x 512", "1024 x 1024", "2048 x 2048"],
            state="readonly", width=14,
        )
        res_combo.pack(anchor="w")

        self._render_btn = ttk.Button(render_frame, text="Render & Export PNG",
                                       command=self._on_render)
        self._render_btn.pack(pady=16, anchor="w")
        self._render_callback = None

    def set_render_callback(self, cb):
        self._render_callback = cb

    def _on_render(self):
        if self._render_callback:
            res_str = self.resolution_var.get()
            size = int(res_str.split("x")[0].strip())
            self._render_callback(size)

    def _build_texture_controls(self, parent):
        # ── Wood section header ──
        ttk.Label(parent, text="Wood", font=("TkDefaultFont", 10, "bold")).pack(
            anchor="w", pady=(8, 4))

        # Colors & Grooves
        ttk.Label(parent, text="Colors & Grooves",
                  font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(4, 2))
        self.color1 = ColorButton(parent, "Color 1:", (200, 150, 80), self._cb)
        self.color1.pack(fill=tk.X)
        self.color2 = ColorButton(parent, "Color 2:", (120, 70, 30), self._cb)
        self.color2.pack(fill=tk.X)
        self.groove_depth = LabeledSlider(parent, "Groove Depth:", 0, 50, 0.1, 15.0, self._cb)
        self.groove_depth.pack(fill=tk.X)

        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, pady=6)

        # Select Rings
        ttk.Label(parent, text="Select Rings",
                  font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(4, 2))
        self.scale = LabeledSlider(parent, "Scale:", 0.0, 5.0, 0.001, 1.0, self._cb)
        self.scale.pack(fill=tk.X)
        self.seed = IntEntry(parent, "Seed:", 0, self._cb)
        self.seed.pack(fill=tk.X)
        self.ring_frequency = DropdownSelector(
            parent, "Ring Frequency:",
            ["Quarter", "Half", "Normal", "Double"], "Quarter", self._cb)
        self.ring_frequency.pack(fill=tk.X)
        self.ring_phase = LabeledSlider(parent, "Ring Phase:", 0, 360, 0.1, 30.0, self._cb)
        self.ring_phase.pack(fill=tk.X)
        self.ring_slant = LabeledSlider(parent, "Ring Slant:", -90, 90, 0.1, 10.0, self._cb)
        self.ring_slant.pack(fill=tk.X)
        self.ring_bias = LabeledSlider(parent, "Ring Bias:", -100, 100, 0.1, -30.7, self._cb)
        self.ring_bias.pack(fill=tk.X)
        self.ring_definition = LabeledSlider(parent, "Ring Definition:", 0, 100, 0.1, 50.0, self._cb)
        self.ring_definition.pack(fill=tk.X)
        self.fade_areas = LabeledSlider(parent, "Fade Areas:", 0, 100, 0.1, 0.0, self._cb)
        self.fade_areas.pack(fill=tk.X)
        self.streak_away = LabeledSlider(parent, "Streak Away:", 0, 100, 0.1, 30.0, self._cb)
        self.streak_away.pack(fill=tk.X)
        self.dissolve = LabeledSlider(parent, "Dissolve:", 0, 100, 0.1, 40.0, self._cb)
        self.dissolve.pack(fill=tk.X)

        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, pady=6)

        # Effects
        ttk.Label(parent, text="Effects",
                  font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(4, 2))
        self.shade1 = ToggleWithSlider(parent, "Shade Effect 1", False, 50, self._cb)
        self.shade1.pack(fill=tk.X)
        self.shade2 = ToggleWithSlider(parent, "Shade Effect 2", False, 50, self._cb)
        self.shade2.pack(fill=tk.X)
        self.shade3 = ToggleWithSlider(parent, "Shade Effect 3", False, 50, self._cb)
        self.shade3.pack(fill=tk.X)
        self.weather = ToggleWithSlider(parent, "Weather Effect", False, 50, self._cb)
        self.weather.pack(fill=tk.X)

        ttk.Separator(parent, orient="horizontal").pack(fill=tk.X, pady=6)

        # Boards
        ttk.Label(parent, text="Boards",
                  font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(4, 2))

        boards_toggle = ttk.Frame(parent)
        boards_toggle.pack(fill=tk.X)
        self.boards_on_var = tk.BooleanVar(value=False)
        ttk.Radiobutton(boards_toggle, text="On", variable=self.boards_on_var,
                        value=True, command=self._cb).pack(side=tk.LEFT)
        ttk.Radiobutton(boards_toggle, text="Off", variable=self.boards_on_var,
                        value=False, command=self._cb).pack(side=tk.LEFT)

        self.board_pattern = DropdownSelector(
            parent, "Select Pattern:",
            ["Horizontal", "Vertical", "Herringbone", "Brick", "Parquet"],
            "Horizontal", self._cb)
        self.board_pattern.pack(fill=tk.X)
        self.board_distort = LabeledSlider(parent, "Distort:", 0, 100, 0.1, 0.0, self._cb)
        self.board_distort.pack(fill=tk.X)
        self.mortar_width = LabeledSlider(parent, "Mortar Width:", 0, 20, 0.1, 2.0, self._cb)
        self.mortar_width.pack(fill=tk.X)
        self.color_blocks = LabeledSlider(parent, "Color Blocks:", 0, 100, 0.1, 0.0, self._cb)
        self.color_blocks.pack(fill=tk.X)
        self.bevel = LabeledSlider(parent, "Bevel:", 0, 20, 0.1, 0.0, self._cb)
        self.bevel.pack(fill=tk.X)
        self.shade_edges = LabeledSlider(parent, "Shade Edges:", 0, 100, 0.1, 0.0, self._cb)
        self.shade_edges.pack(fill=tk.X)
        self.mortar_material = LabeledSlider(parent, "Mortar Material:", 0, 100, 0.1, 0.0, self._cb)
        self.mortar_material.pack(fill=tk.X)

    def get_params(self):
        """Read all widgets and return a WoodParams-compatible dict."""
        from wood_workshop.generator import WoodParams
        p = WoodParams()
        p.color1 = self.color1.get()
        p.color2 = self.color2.get()
        p.groove_depth = self.groove_depth.get()
        p.scale = self.scale.get()
        p.seed = self.seed.get()
        p.ring_frequency = self.ring_frequency.get()
        p.ring_phase = self.ring_phase.get()
        p.ring_slant = self.ring_slant.get()
        p.ring_bias = self.ring_bias.get()
        p.ring_definition = self.ring_definition.get()
        p.fade_areas = self.fade_areas.get()
        p.streak_away = self.streak_away.get()
        p.dissolve = self.dissolve.get()
        p.shade_effect1 = self.shade1.get_on()
        p.shade_strength1 = self.shade1.get_strength()
        p.shade_effect2 = self.shade2.get_on()
        p.shade_strength2 = self.shade2.get_strength()
        p.shade_effect3 = self.shade3.get_on()
        p.shade_strength3 = self.shade3.get_strength()
        p.weather_effect = self.weather.get_on()
        p.weather_strength = self.weather.get_strength()
        p.boards_on = self.boards_on_var.get()
        p.board_pattern = self.board_pattern.get()
        p.board_distort = self.board_distort.get()
        p.mortar_width = self.mortar_width.get()
        p.color_blocks = self.color_blocks.get()
        p.bevel = self.bevel.get()
        p.shade_edges = self.shade_edges.get()
        p.mortar_material = self.mortar_material.get()
        return p

    def set_params(self, p):
        """Load a WoodParams into the widgets."""
        self.color1.set(p.color1)
        self.color2.set(p.color2)
        self.groove_depth.set(p.groove_depth)
        self.scale.set(p.scale)
        self.seed.set(p.seed)
        self.ring_frequency.set(p.ring_frequency)
        self.ring_phase.set(p.ring_phase)
        self.ring_slant.set(p.ring_slant)
        self.ring_bias.set(p.ring_bias)
        self.ring_definition.set(p.ring_definition)
        self.fade_areas.set(p.fade_areas)
        self.streak_away.set(p.streak_away)
        self.dissolve.set(p.dissolve)
        self.shade1.set_on(p.shade_effect1)
        self.shade1.set_strength(p.shade_strength1)
        self.shade2.set_on(p.shade_effect2)
        self.shade2.set_strength(p.shade_strength2)
        self.shade3.set_on(p.shade_effect3)
        self.shade3.set_strength(p.shade_strength3)
        self.weather.set_on(p.weather_effect)
        self.weather.set_strength(p.weather_strength)
        self.boards_on_var.set(p.boards_on)
        self.board_pattern.set(p.board_pattern)
        self.board_distort.set(p.board_distort)
        self.mortar_width.set(p.mortar_width)
        self.color_blocks.set(p.color_blocks)
        self.bevel.set(p.bevel)
        self.shade_edges.set(p.shade_edges)
        self.mortar_material.set(p.mortar_material)
