"""Scene 04 · Cinematic 3D Pikachu Emergence (ASCII Lab & Javed Khan Labs).

Converts the photorealistic 3D cinematic video of Pikachu emerging from a Pokéball
into high-contrast, high-definition ASCII art:
  - 1080x1920 9:16 vertical video with 22pt Consolas font and 15x22 cell size.
  - Saturated Poké-yellow, crimson electric cheek pouches, and crackling lightning bolts.
  - Multi-pass optical bloom, anamorphic light streaks, and volumetric shading.
  - Javed Khan Labs in-grid ASCII watermark badge and status HUD.
  - Bottom live telemetry panel with discharge voltage, electro-flux, and shader pipeline code.
  - Original AAC master audio multiplexed and synchronized.
"""

import argparse
import math
import os
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---- Canvas & Grid Configuration ---------------------------------------------------
HANDLE = "JAVED KHAN LABS"
SCENE_TITLE = "04 : PIKACHU CINEMATIC EMERGENCE"

W, H, FPS = 1080, 1920, 25
CW, CH = 15, 22  # High visibility 15x22 cells
COLS = W // CW   # 72 columns
ROWS_SCENE = 68  # 1496 pixels
ROWS_PANEL = 19  # 418 pixels
ROWS_FULL = ROWS_SCENE + ROWS_PANEL

FONT_PATHS = (
    "consola.ttf",
    "DejaVuSansMono.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "C:/Windows/Fonts/consola.ttf",
    "C:/Windows/Fonts/lucon.ttf",
)

def glyph_id(ch):
    val = ord(ch) - 32
    return val if 0 <= val < 95 else 0

_font_cache = {}
def get_font(size):
    if size not in _font_cache:
        override = os.environ.get("ASCII_LAB_FONT")
        if override and os.path.exists(override):
            _font_cache[size] = ImageFont.truetype(override, size)
        else:
            for path in FONT_PATHS:
                try:
                    _font_cache[size] = ImageFont.truetype(path, size)
                    break
                except OSError:
                    continue
            else:
                _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]

_atlas = None
def glyph_atlas():
    global _atlas
    if _atlas is None:
        atlas = np.zeros((96, CH, CW), dtype=np.float32)
        f = get_font(22)
        for i in range(95):
            im = Image.new("L", (CW, CH), 0)
            ch = chr(32 + i)
            lift = 4 if ch == "_" else 2
            ImageDraw.Draw(im).text((1, -lift), ch, font=f, fill=255)
            atlas[i] = np.asarray(im, dtype=np.float32) / 255.0
        _atlas = atlas
    return _atlas

# High-contrast natural ASCII ramp
RAMP = "  ..:-=+*oa#%8@$"
RAMP_G = np.array([glyph_id(c) for c in RAMP])

def frame_to_ascii(frame_img, t, duration=10.04):
    """Transforms a raw 720x1280 video frame into an ASCII character grid and color map."""
    # 1. Scale and crop to 1080x1496 (centering Pikachu and cleanly removing corner watermarks)
    im_scaled = frame_img.resize((1080, 1920), Image.LANCZOS)
    top = 170
    im_cropped = im_scaled.crop((0, top, 1080, top + 1496))

    # 2. Downsample for grid cell colors
    grid_img = im_cropped.resize((COLS, ROWS_SCENE), Image.BOX)
    grid_rgb = np.array(grid_img, dtype=np.float32) / 255.0

    # 3. High-res grayscale for gradient/contour detection
    gray_hires = im_cropped.convert("L")
    gray_arr = np.array(gray_hires, dtype=np.float32) / 255.0

    # Smooth luminance curve for deep moody background and punchy foreground
    lum_raw = 0.299 * grid_rgb[..., 0] + 0.587 * grid_rgb[..., 1] + 0.114 * grid_rgb[..., 2]
    lum = np.clip((lum_raw - 0.10) / (0.88 - 0.10), 0.0, 1.0) ** 1.15

    # Sobel gradient on cell scale
    dy = np.diff(gray_arr[::CH, :], axis=0)[:, :COLS*CW:CW]
    dx = np.diff(gray_arr[:, ::CW], axis=1)[:ROWS_SCENE*CH:CH, :]
    grad_y = np.pad(dy, ((0, ROWS_SCENE - dy.shape[0]), (0, COLS - dy.shape[1])), mode='edge')
    grad_x = np.pad(dx, ((0, ROWS_SCENE - dx.shape[0]), (0, COLS - dx.shape[1])), mode='edge')
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    chars = np.zeros((ROWS_SCENE, COLS), dtype=int)
    ink = np.zeros((ROWS_SCENE, COLS, 3), dtype=np.float32)

    ramp_len = len(RAMP)
    ramp_idx = np.clip(lum * (ramp_len - 1), 0, ramp_len - 1).astype(int)

    for r in range(ROWS_SCENE):
        for c in range(COLS):
            l = lum[r, c]
            l_orig = lum_raw[r, c]
            col = grid_rgb[r, c].copy()
            g = grad_mag[r, c]

            # Saturation boost for glowing colors
            c_max = np.max(col)
            c_min = np.min(col)
            delta = c_max - c_min
            if delta > 0.08:
                col = np.clip(col + (col - np.mean(col)) * 0.45, 0.0, 1.0)

            # Detect electric lightning sparks (pure bright energy)
            is_spark = l_orig > 0.85 and (col[0] > 0.75 and col[1] > 0.75)
            # Detect sharp silhouette contour
            is_contour = g > 0.32 and 0.2 < l_orig < 0.85

            if is_spark:
                # Crackling lightning bolt characters
                spark_glyphs = [glyph_id("*"), glyph_id("+"), glyph_id("x"), glyph_id("#"), glyph_id("@")]
                chars[r, c] = spark_glyphs[(r * 5 + c * 11) % len(spark_glyphs)]
                ink[r, c] = np.array([1.0, 0.98, 0.80]) # brilliant electric spark gold
            elif is_contour:
                chars[r, c] = glyph_id("#" if (r + c) % 2 == 0 else "8")
                ink[r, c] = col * 1.15
            else:
                idx = ramp_idx[r, c]
                chars[r, c] = RAMP_G[idx]
                if idx <= 2:
                    ink[r, c] = col * 0.55
                else:
                    ink[r, c] = col * (0.85 + 0.25 * l)

    # In-Grid Javed Khan Labs Watermark Badge
    badge = [
        "+------------------------------------+",
        "|         JAVED KHAN LABS            |",
        "|   04 : PIKACHU CINEMATIC LAB       |",
        "+------------------------------------+",
    ]
    b_h = len(badge)
    b_w = len(badge[0])
    start_col = COLS - b_w - 3

    # Clear region behind badge for flawless readability
    for br in range(1, 2 + b_h + 1):
        for bc in range(start_col - 1, start_col + b_w + 2):
            if 0 <= br < ROWS_SCENE and 0 <= bc < COLS:
                chars[br, bc] = 0
                ink[br, bc] = 0.0

    for r_idx, line in enumerate(badge):
        r = 2 + r_idx
        for c_idx, ch in enumerate(line):
            c = start_col + c_idx
            if 0 <= r < ROWS_SCENE and 0 <= c < COLS:
                chars[r, c] = glyph_id(ch)
                ink[r, c] = np.array([1.0, 0.88, 0.45]) * (1.0 if ch not in "+-|" else 0.7)

    # In-Grid Status Tag at bottom of scene
    tag = f"[ JAVED KHAN LABS * PIKACHU CINEMATIC * T+{t:05.2f}s / {duration:05.2f}s * 25 FPS ]"
    for c in range(1, COLS - 1):
        chars[ROWS_SCENE - 2, c] = 0
        ink[ROWS_SCENE - 2, c] = 0.0

    for c_idx, ch in enumerate(tag):
        if 2 + c_idx < COLS:
            chars[ROWS_SCENE - 2, 2 + c_idx] = glyph_id(ch)
            ink[ROWS_SCENE - 2, 2 + c_idx] = np.array([1.0, 0.82, 0.35])

    return chars, ink

def render_glow(chars, ink):
    """Applies multi-pass optical phosphor bloom and anamorphic light streaks."""
    height, width = chars.shape[0] * CH, chars.shape[1] * CW
    mask = glyph_atlas()[chars].transpose(0, 2, 1, 3).reshape(height, width)
    col = np.repeat(np.repeat(ink.astype(np.float32), CH, 0), CW, 1)
    base = mask[..., None] * col

    small = Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).resize(
        (width // 4, height // 4), Image.BOX
    )
    near = np.asarray(small.filter(ImageFilter.GaussianBlur(2.2)).resize((width, height), Image.BILINEAR), np.float32)
    far = np.asarray(small.filter(ImageFilter.GaussianBlur(8.5)).resize((width, height), Image.BILINEAR), np.float32)

    STREAK = 70
    run = np.cumsum(np.pad(base, ((STREAK, STREAK), (0, 0), (0, 0))), 0)
    rays = (run[2 * STREAK :] - run[: -2 * STREAK]) / (2 * STREAK)

    composite = np.clip(
        base * 255.0 + 0.45 * near + 0.35 * far + 0.12 * 255.0 * rays, 0, 255
    ).astype(np.uint8)
    return composite

def make_panel(t, duration=10.04):
    """Creates the bottom Javed Khan Labs live telemetry and shader code panel."""
    hh = ROWS_PANEL * CH
    im = Image.new("RGB", (W, hh), (10, 12, 18))
    d = ImageDraw.Draw(im)
    f_bold = get_font(20)
    f_regular = get_font(16)
    f_code = get_font(14)

    # Top gold separator line
    d.line([(40, 24), (W - 40, 24)], fill=(75, 62, 35), width=2)
    d.text((44, 34), "◈ JAVED KHAN LABS", font=f_bold, fill=(255, 225, 90))
    d.text((290, 37), "·  SCENE 04 : PIKACHU CINEMATIC EMERGENCE (POKÉMON #025)", font=f_regular, fill=(230, 210, 140))
    d.text((W - 270, 37), f"TIMESTAMP: {t:05.2f}s / {duration:05.2f}s", font=f_regular, fill=(255, 235, 120))
    d.line([(40, 68), (W - 40, 68)], fill=(75, 62, 35), width=1)

    volt = 240000 + int(35000 * math.sin(t * 5.2))
    telemetry = [
        ("LIGHTNING DISCHARGE", f"{volt:,} VOLTS"),
        ("ELECTRO-FLUX DENSITY", "2.14 TESLA (PEAK)"),
        ("CINEMATIC MOTION", "25 FPS · DYNAMIC 3D"),
        ("NEURAL ASCII SHADER", "JKL-OPTICAL-BLOOM"),
    ]
    card_w = (W - 80) // 4
    for i, (title, val) in enumerate(telemetry):
        x = 44 + i * card_w
        d.text((x, 82), title, font=get_font(12), fill=(155, 140, 95))
        d.text((x, 102), val, font=f_regular, fill=(255, 240, 180))

    d.line([(40, 134), (W - 40, 134)], fill=(55, 45, 28), width=1)

    code_lines = [
        "# Cinematic 3D Pikachu ASCII Lab Neural Shader Pipeline",
        "frame_src    = decode_stream(frame_idx);  crop = center_crop(1080, 1496)",
        "lum_field    = rgb_to_luminance(frame_src);  sobel = gradient_tensor(lum_field)",
        "ascii_grid   = map_ascii_density(lum_field, RAMP='  ..:-=+*oa#%8@$', edges=sobel)",
        "bloom_pass   = optical_glow(near=0.45, far=0.35, anamorphic_streak=70)  # 240kV",
        "composite    = render_atlas(ascii_grid, font='Consolas 22pt')  # Javed Khan Labs",
    ]
    y_code = 150
    for line in code_lines:
        fill_col = (255, 215, 80) if line.startswith("#") else (210, 200, 165)
        d.text((50, y_code), line, font=f_code, fill=fill_col)
        y_code += 24

    watermark = "CREATED WITH ASCII LAB ENGINE ◈ JAVED KHAN LABS"
    d.text(((W - d.textlength(watermark, font=get_font(13))) // 2, hh - 30), watermark, font=get_font(13), fill=(145, 125, 70))
    return im

def compose_full_frame(frame_img, t, duration=10.04):
    chars, ink = frame_to_ascii(frame_img, t, duration=duration)
    scene_pixels = render_glow(chars, ink)
    scene_img = Image.fromarray(scene_pixels)

    final_img = Image.new("RGB", (W, H), (8, 9, 14))
    final_img.paste(scene_img, (0, 0))
    panel_img = make_panel(t, duration=duration)
    final_img.paste(panel_img, (0, ROWS_SCENE * CH))
    return final_img

def process_video(source_video_path, output_mp4_path):
    """Processes entire input video through ASCII Lab engine and encodes to MP4 with original audio."""
    src_path = str(source_video_path)
    out_path = str(output_mp4_path)

    # 1. Inspect source video with ffprobe
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_frames,duration,r_frame_rate",
        "-of", "csv=p=0",
        src_path,
    ]
    probe_res = subprocess.check_output(probe_cmd).decode("utf-8").strip().split(",")
    src_w, src_h = int(probe_res[0]), int(probe_res[1])
    try:
        duration = float(probe_res[3])
    except (IndexError, ValueError):
        duration = 10.04

    # Decoder process: outputs raw rgb24 frames
    decode_cmd = [
        "ffmpeg",
        "-v", "error",
        "-i", src_path,
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-",
    ]

    # Encoder process: reads raw rgb24 frames from stdin and copies audio from original video
    encode_cmd = [
        "ffmpeg",
        "-v", "error",
        "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}",
        "-r", str(FPS),
        "-i", "-",
        "-i", src_path,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-shortest",
        out_path,
    ]

    frame_bytes = src_w * src_h * 3
    print(f"Streaming and processing '{src_path}' ({src_w}x{src_h}, {duration:.2f}s)...", flush=True)
    start_time = time.time()
    frame_idx = 0

    with subprocess.Popen(decode_cmd, stdout=subprocess.PIPE) as decoder, \
         subprocess.Popen(encode_cmd, stdin=subprocess.PIPE) as encoder:
        try:
            while True:
                raw = decoder.stdout.read(frame_bytes)
                if not raw or len(raw) < frame_bytes:
                    break

                t = frame_idx / FPS
                raw_img = Image.frombytes("RGB", (src_w, src_h), raw)
                final_img = compose_full_frame(raw_img, t, duration=duration)
                encoder.stdin.write(final_img.tobytes())

                frame_idx += 1
                if frame_idx % 15 == 0:
                    elapsed = time.time() - start_time
                    fps_real = frame_idx / max(elapsed, 1e-4)
                    print(f"  Frame {frame_idx:03d} (T={t:05.2f}s) | Speed: {fps_real:.1f} fps", flush=True)
        finally:
            if encoder.stdin:
                encoder.stdin.close()
            decoder.wait()
            encoder.wait()

    elapsed = time.time() - start_time
    print(f"Render complete: {frame_idx} frames in {elapsed:.1f}s ({frame_idx/max(elapsed, 1e-4):.1f} fps)")
    print(f"Saved: {out_path}")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_png = sub.add_parser("png", help="Render single preview PNG frame")
    p_png.add_argument("time", type=float, default=5.0, help="Video timestamp in seconds")
    p_png.add_argument("output", type=Path, help="Output PNG path")
    p_png.add_argument("--source", type=Path, default=None, help="Source video path")

    p_mp4 = sub.add_parser("mp4", help="Render full MP4 video")
    p_mp4.add_argument("output", type=Path, help="Output MP4 path")
    p_mp4.add_argument("--source", type=Path, default=None, help="Source video path")

    args = parser.parse_args()

    default_src = Path(__file__).parent / "source_video.mp4"
    if not default_src.exists():
        default_src = Path("C:/Users/javed/.gemini/antigravity/brain/5c0b23e8-2332-4954-a6fa-b1ae28567c3c/.user_uploaded/media_1795533075302_52a59398.mp4")
    src = args.source if args.source else default_src

    if args.cmd == "png":
        # Extract single frame at time t
        temp_img = Path(__file__).parent / "temp_frames" / f"extracted_{args.time:.1f}s.jpg"
        temp_img.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y", "-ss", str(args.time),
            "-i", str(src),
            "-vframes", "1", "-update", "1",
            str(temp_img)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        raw_img = Image.open(temp_img)
        out_img = compose_full_frame(raw_img, args.time)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        out_img.save(args.output)
        print(f"Saved preview frame to {args.output}")
    elif args.cmd == "mp4":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        process_video(src, args.output)

if __name__ == "__main__":
    main()
