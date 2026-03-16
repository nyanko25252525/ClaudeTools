"""Wood texture generation engine using OpenSimplex noise and ring patterns."""

import numpy as np
from PIL import Image, ImageFilter
import opensimplex


def _noise_grid(width, height, scale, seed, octaves=4, persistence=0.5):
    """Generate a 2D OpenSimplex noise grid with fractal octaves."""
    result = np.zeros((height, width), dtype=np.float64)
    if scale <= 0:
        scale = 0.001

    opensimplex.seed(seed)
    base_offset = seed * 17.31

    amp = 1.0
    freq = 1.0
    max_amp = 0.0
    for _ in range(octaves):
        for y in range(height):
            ny = (y / (height * scale) + base_offset) * freq
            for x in range(width):
                nx = (x / (width * scale) + base_offset) * freq
                result[y, x] += opensimplex.noise2(nx, ny) * amp
        max_amp += amp
        amp *= persistence
        freq *= 2.0

    if max_amp > 0:
        result /= max_amp

    return result


def _normalize(arr):
    """Normalize array to 0-1 range."""
    mn, mx = arr.min(), arr.max()
    if mx - mn < 1e-10:
        return np.zeros_like(arr)
    return (arr - mn) / (mx - mn)


# ──────────────────────────────────────────────────────────
# Frequency multipliers for ring frequency dropdown
# ──────────────────────────────────────────────────────────
RING_FREQ_MAP = {
    "Quarter": 0.25,
    "Half": 0.5,
    "Normal": 1.0,
    "Double": 2.0,
}

# ──────────────────────────────────────────────────────────
# Board patterns
# ──────────────────────────────────────────────────────────
BOARD_PATTERNS = [
    "Horizontal",
    "Vertical",
    "Herringbone",
    "Brick",
    "Parquet",
]


class WoodParams:
    """All parameters for wood texture generation."""

    def __init__(self):
        # Colors & Grooves
        self.color1 = (200, 150, 80)   # RGB
        self.color2 = (120, 70, 30)    # RGB
        self.groove_depth = 15.0       # 0-50

        # Select Rings
        self.scale = 1.0               # 0.0-5.0
        self.seed = 0                  # integer
        self.ring_frequency = "Normal"   # Quarter/Half/Normal/Double
        self.ring_phase = 15.0         # 0-360
        self.ring_slant = 5.0          # -90 to 90
        self.ring_bias = -10.0         # -100 to 100
        self.ring_definition = 55.0    # 0-100
        self.fade_areas = 5.0          # 0-100
        self.streak_away = 40.0        # 0-100
        self.dissolve = 20.0           # 0-100

        # Effects
        self.shade_effect1 = False
        self.shade_strength1 = 50.0
        self.shade_effect2 = False
        self.shade_strength2 = 50.0
        self.shade_effect3 = False
        self.shade_strength3 = 50.0
        self.weather_effect = False
        self.weather_strength = 50.0

        # Boards
        self.boards_on = False
        self.board_pattern = "Horizontal"
        self.board_distort = 0.0       # 0-100
        self.mortar_width = 2.0        # 0-20
        self.color_blocks = 0.0        # 0-100
        self.bevel = 0.0               # 0-20
        self.shade_edges = 0.0         # 0-100
        self.mortar_material = 0.0     # 0-100

        # Output
        self.resolution = 256

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    @classmethod
    def from_dict(cls, d):
        p = cls()
        for k, v in d.items():
            if hasattr(p, k):
                setattr(p, k, v)
                # Ensure colour tuples
                if k in ("color1", "color2") and isinstance(v, list):
                    setattr(p, k, tuple(v))
        return p


# ──────────────────────────────────────────────────────────
# Generator
# ──────────────────────────────────────────────────────────

def generate_base_wood(params: WoodParams, size: int = 256) -> np.ndarray:
    """Generate a plank-style wood grain pattern (returns float array 0-1, shape HxW).

    The grain runs vertically (along Y axis) like sawn lumber, using
    Y-stretched elliptical coordinates so that the ring arcs curve gently
    across the board rather than forming concentric circles.
    """
    w = h = size
    scale = max(params.scale, 0.01)
    freq_mult = RING_FREQ_MAP.get(params.ring_frequency, 1.0)

    # ── Noise layers ──
    # noise1: large-scale grain distortion
    noise1 = _noise_grid(w, h, scale * 2.0, params.seed, octaves=4)
    # noise2: fine detail / dissolve
    noise2 = _noise_grid(w, h, scale * 4.0, params.seed + 1, octaves=2)
    # noise_streak: elongated noise for vertical streaks (sampled with
    # compressed Y so features stretch along the grain direction)
    noise_streak = _noise_grid(w, h, scale * 1.0, params.seed + 2, octaves=3,
                               persistence=0.45)

    # ── Normalised coordinates (-1..1) ──
    nx = np.linspace(-1.0, 1.0, w)[np.newaxis, :]  # 1×W
    ny = np.linspace(-1.0, 1.0, h)[:, np.newaxis]  # H×1
    # Broadcast to full grids
    nx = np.broadcast_to(nx, (h, w)).copy()
    ny = np.broadcast_to(ny, (h, w)).copy()

    # ── Ring slant – rotate the coordinate system ──
    slant_rad = np.radians(params.ring_slant)
    cos_s, sin_s = np.cos(slant_rad), np.sin(slant_rad)
    rx = nx * cos_s - ny * sin_s
    ry = nx * sin_s + ny * cos_s

    # ── Ring bias – shift the ellipse centre horizontally ──
    bias = params.ring_bias / 100.0
    rx += bias * 1.0  # shift left/right within -1..1 space

    # ── Y-stretch: the key to plank grain ──
    # A large stretch value makes ring arcs nearly horizontal lines that
    # curve gently, mimicking how a flat-sawn board looks.
    y_stretch = 8.0 * scale
    dist = np.sqrt(rx ** 2 + (ry / y_stretch) ** 2)

    # ── Streak Away – add X-biased noise for vertical grain streaks ──
    streak = params.streak_away / 100.0
    # noise_streak naturally has some vertical coherence; we scale its
    # contribution so the grain gets long wispy streaks along Y.
    streak_contrib = noise_streak * streak * 0.8
    # Also add large-scale distortion from noise1
    grain_noise = noise1 * (0.5 + streak * 1.5) + streak_contrib

    # ── Ring pattern via sin() ──
    phase_offset = np.radians(params.ring_phase)
    ring_val = np.sin(
        dist * freq_mult * np.pi * 6.0
        + grain_noise * 3.0
        + phase_offset
    )

    # ── Ring definition (sharpness) ──
    definition = params.ring_definition / 100.0
    if definition > 0.5:
        power = 1.0 + (definition - 0.5) * 6.0
        ring_val = np.sign(ring_val) * np.abs(ring_val) ** (1.0 / power)
    elif definition < 0.5:
        power = 1.0 + (0.5 - definition) * 4.0
        ring_val = np.sign(ring_val) * np.abs(ring_val) ** power

    # ── Fade areas ──
    fade = params.fade_areas / 100.0
    if fade > 0:
        fade_noise = _normalize(_noise_grid(w, h, scale * 8.0, params.seed + 3,
                                            octaves=2))
        ring_val *= (1.0 - fade * fade_noise)

    # ── Dissolve (fine noise) ──
    dissolve = params.dissolve / 100.0
    if dissolve > 0:
        ring_val += noise2 * dissolve * 1.5

    # ── Normalize to 0-1 ──
    base = _normalize(ring_val)

    # ── Groove depth – darken the troughs ──
    groove = params.groove_depth / 50.0
    if groove > 0:
        base = base ** (1.0 + groove * 0.5)

    return base


def colorize(base: np.ndarray, params: WoodParams) -> np.ndarray:
    """Apply color1/color2 to base wood pattern. Returns HxWx3 uint8."""
    c1 = np.array(params.color1, dtype=np.float64)
    c2 = np.array(params.color2, dtype=np.float64)
    t = base[:, :, np.newaxis]
    rgb = c1 * t + c2 * (1.0 - t)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def apply_effects(img_array: np.ndarray, params: WoodParams, base: np.ndarray) -> np.ndarray:
    """Apply shade and weather effects. Returns HxWx3 uint8."""
    result = img_array.astype(np.float64)
    h, w = result.shape[:2]

    # Shade effects – directional lighting simulation
    if params.shade_effect1:
        strength = params.shade_strength1 / 100.0
        yy = np.linspace(0, 1, h)[:, np.newaxis]
        shade = 1.0 - yy * 0.3 * strength
        result *= shade[:, :, np.newaxis]

    if params.shade_effect2:
        strength = params.shade_strength2 / 100.0
        xx = np.linspace(0, 1, w)[np.newaxis, :]
        shade = 1.0 - xx * 0.25 * strength
        result *= shade[:, :, np.newaxis]

    if params.shade_effect3:
        strength = params.shade_strength3 / 100.0
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
        cx, cy = w / 2, h / 2
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (w * 0.7)
        vignette = 1.0 - np.clip(dist, 0, 1) * 0.4 * strength
        result *= vignette[:, :, np.newaxis]

    # Weather effect – desaturate + noise
    if params.weather_effect:
        strength = params.weather_strength / 100.0
        gray = np.mean(result, axis=2, keepdims=True)
        result = result * (1.0 - strength * 0.4) + gray * strength * 0.4
        rng = np.random.RandomState(params.seed + 99)
        weather_noise = rng.normal(0, 8 * strength, result.shape)
        result += weather_noise

    return np.clip(result, 0, 255).astype(np.uint8)


def _generate_board_mask(w, h, params: WoodParams):
    """Generate board layout: returns (board_ids HxW int, mortar_mask HxW bool)."""
    pattern = params.board_pattern
    mortar_px = max(1, int(params.mortar_width))
    board_ids = np.zeros((h, w), dtype=np.int32)
    mortar = np.zeros((h, w), dtype=bool)

    if pattern == "Vertical":
        board_w = max(20, w // 6)
        for x in range(w):
            bx = x // board_w
            board_ids[:, x] = bx
            if x % board_w < mortar_px:
                mortar[:, x] = True

    elif pattern == "Herringbone":
        tile = max(20, w // 4)
        for y in range(h):
            for x in range(w):
                bx = x // tile
                by = y // tile
                if (bx + by) % 2 == 0:
                    board_ids[y, x] = (y // tile) * 20 + (x // tile)
                else:
                    board_ids[y, x] = (y // tile) * 20 + (x // tile) + 100
                if x % tile < mortar_px or y % tile < mortar_px:
                    mortar[y, x] = True

    elif pattern == "Brick":
        board_h = max(15, h // 8)
        board_w = max(30, w // 4)
        for y in range(h):
            row = y // board_h
            offset = (row % 2) * (board_w // 2)
            for x in range(w):
                bx = (x + offset) // board_w
                board_ids[y, x] = row * 20 + bx
                if y % board_h < mortar_px or (x + offset) % board_w < mortar_px:
                    mortar[y, x] = True

    elif pattern == "Parquet":
        tile = max(20, w // 4)
        for y in range(h):
            for x in range(w):
                tx = (x // tile) % 2
                ty = (y // tile) % 2
                if (tx + ty) % 2 == 0:
                    sub = x % tile
                else:
                    sub = y % tile
                board_ids[y, x] = (y // tile) * 20 + (x // tile) * 3 + sub // (tile // 3 + 1)
                if x % tile < mortar_px or y % tile < mortar_px:
                    mortar[y, x] = True

    else:  # Horizontal (default)
        board_h = max(20, h // 6)
        for y in range(h):
            by = y // board_h
            board_ids[y, :] = by
            if y % board_h < mortar_px:
                mortar[y, :] = True

    return board_ids, mortar


def apply_boards(img_array: np.ndarray, params: WoodParams) -> np.ndarray:
    """Apply board pattern overlay. Returns HxWx3 uint8."""
    if not params.boards_on:
        return img_array

    h, w = img_array.shape[:2]
    result = img_array.astype(np.float64)
    board_ids, mortar = _generate_board_mask(w, h, params)

    # Color blocks – shift hue per board
    if params.color_blocks > 0:
        strength = params.color_blocks / 100.0
        rng = np.random.RandomState(params.seed + 50)
        unique_ids = np.unique(board_ids)
        color_shift = {}
        for bid in unique_ids:
            color_shift[bid] = rng.uniform(-20, 20, 3) * strength
        for bid in unique_ids:
            mask = board_ids == bid
            result[mask] += color_shift[bid]

    # Bevel / shade edges
    if params.bevel > 0 or params.shade_edges > 0:
        bevel_px = max(1, int(params.bevel))
        shade_str = params.shade_edges / 100.0
        # Simple edge darkening using distance from mortar
        from scipy.ndimage import distance_transform_edt
        try:
            dist_from_edge = distance_transform_edt(~mortar)
        except Exception:
            # Fallback without scipy
            dist_from_edge = np.ones((h, w), dtype=np.float64) * 10.0

        edge_factor = np.clip(dist_from_edge / max(bevel_px, 1), 0, 1)
        darken = 1.0 - (1.0 - edge_factor) * shade_str * 0.6
        result *= darken[:, :, np.newaxis]

    # Mortar fill
    mortar_color = np.array([40, 30, 20], dtype=np.float64)
    material = params.mortar_material / 100.0
    # Blend mortar color with slightly lighter version based on material
    light_mortar = mortar_color + 40 * material
    result[mortar] = light_mortar

    # Distort (simple horizontal jitter per row)
    if params.board_distort > 0:
        dist_amount = int(params.board_distort / 100.0 * 10)
        if dist_amount > 0:
            rng = np.random.RandomState(params.seed + 70)
            for y in range(h):
                shift = rng.randint(-dist_amount, dist_amount + 1)
                result[y] = np.roll(result[y], shift, axis=0)

    return np.clip(result, 0, 255).astype(np.uint8)


def generate_texture(params: WoodParams, size: int = 256):
    """
    Full pipeline. Returns (base_img, effects_img, final_img) as PIL Images.
    """
    base = generate_base_wood(params, size)
    base_rgb = colorize(base, params)
    base_img = Image.fromarray(base_rgb, "RGB")

    effects_rgb = apply_effects(base_rgb, params, base)
    effects_img = Image.fromarray(effects_rgb, "RGB")

    final_rgb = apply_boards(effects_rgb, params)
    final_img = Image.fromarray(final_rgb, "RGB")

    return base_img, effects_img, final_img
