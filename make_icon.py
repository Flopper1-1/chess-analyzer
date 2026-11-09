"""Process fluent.png (cropped + transparent corners), sounds, and annotations from Assets.zip."""
import os
import shutil
import struct
import subprocess
from PIL import Image, ImageDraw, ImageChops

EXTRACT_DIR = r"C:\Users\pierr\.gemini\antigravity\brain\53efb74e-39bb-4e51-aa2e-1159a153d275\scratch\assets_extracted"
REPO_DIR = r"C:\Users\pierr\.gemini\antigravity\scratch\chess-analyzer"

# 1. Process fluent.png -> cropped, square, transparent corners
fluent_src = os.path.join(EXTRACT_DIR, "App Icons", "fluent.png")
im = Image.open(fluent_src).convert("RGBA")

# Find exact bounding box of the green icon (excluding black outer margin)
import numpy as np
arr = np.array(im)
# Green/white pixels have G > 28 or R > 28 or B > 28
non_black = (arr[:, :, 1] > 28) | (arr[:, :, 0] > 28) | (arr[:, :, 2] > 28)
rows = np.any(non_black, axis=1)
cols = np.any(non_black, axis=0)
ymin, ymax = np.where(rows)[0][[0, -1]]
xmin, xmax = np.where(cols)[0][[0, -1]]
print(f"Detected icon bounds: x={xmin}..{xmax}, y={ymin}..{ymax}")

# Crop tightly to the green squircle and resize to 512x512
cropped = im.crop((xmin, ymin, xmax + 1, ymax + 1)).resize((512, 512), Image.Resampling.LANCZOS)

# Create supersampled anti-aliased rounded rectangle mask (2048x2048 -> 512x512)
# Also zero out any remaining dark/black pixels near the outer corners
ss = 4
mask_hi = Image.new("L", (512 * ss, 512 * ss), 0)
draw = ImageDraw.Draw(mask_hi)
# Corner radius of the fluent icon is ~22.5% of width
radius = int(512 * ss * 0.225)
pad = int(2 * ss)  # 2px inset to cleanly trim any dark halo at the edge
draw.rounded_rectangle(
    (pad, pad, 512 * ss - 1 - pad, 512 * ss - 1 - pad),
    radius=radius,
    fill=255,
)
mask = mask_hi.resize((512, 512), Image.Resampling.LANCZOS)

# Also refine corner alpha using green intensity so no black pixels ever bleed through
c_arr = np.array(cropped, dtype=np.float32)
m_arr = np.array(mask, dtype=np.float32) / 255.0

# Brightness of pixel (green channel is dominant on the icon border)
lum = np.maximum(c_arr[:, :, 1], np.maximum(c_arr[:, :, 0], c_arr[:, :, 2]))
# Smooth ramp from lum=15 (0 alpha) to lum=55 (1 alpha) for outer edge pixels
edge_alpha = np.clip((lum - 15.0) / 40.0, 0.0, 1.0)
final_alpha = np.minimum(m_arr, edge_alpha)

# Un-premultiply color slightly on semi-transparent edge pixels so edges are pure green, not dark green
out_arr = c_arr.copy()
out_arr[:, :, 3] = (final_alpha * 255.0).astype(np.uint8)
fluent_clean_512 = Image.fromarray(out_arr.astype(np.uint8), "RGBA")
fluent_clean_256 = fluent_clean_512.resize((256, 256), Image.Resampling.LANCZOS)

# Save to repo locations
fluent_clean_256.save(os.path.join(REPO_DIR, "icon.png"))
fluent_clean_512.save(os.path.join(REPO_DIR, "assets", "fluent.png"))
fluent_clean_512.save(os.path.join(REPO_DIR, "assets", "icon.png"))
fluent_clean_512.save(os.path.join(REPO_DIR, "showcase", "public", "icon.png"))

# Build multi-size icon.ico
SIZES = [16, 24, 32, 48, 64, 128, 256]
png_blobs = []
import io
for sz in SIZES:
    resized = fluent_clean_512.resize((sz, sz), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    png_blobs.append((sz, buf.getvalue()))

ico_header = struct.pack("<HHH", 0, 1, len(png_blobs))
offset = 6 + 16 * len(png_blobs)
ico_body = b""
for sz, blob in png_blobs:
    ico_header += struct.pack(
        "<BBBBHHII",
        0 if sz >= 256 else sz,
        0 if sz >= 256 else sz,
        0,
        0,
        1,
        32,
        len(blob),
        offset + len(ico_body),
    )
    ico_body += blob

with open(os.path.join(REPO_DIR, "icon.ico"), "wb") as f:
    f.write(ico_header + ico_body)
print("Saved icon.png, icon.ico, assets/fluent.png, showcase/public/icon.png")

# 2. Process Sounds
sounds_src = os.path.join(EXTRACT_DIR, "Sounds", "Default")
sounds_dst = os.path.join(REPO_DIR, "assets", "sounds")
os.makedirs(sounds_dst, exist_ok=True)
for fname in ("brilliant.mp3", "Castle.mp3", "Check.mp3", "Move.mp3"):
    s_path = os.path.join(sounds_src, fname)
    d_mp3 = os.path.join(sounds_dst, fname)
    shutil.copyfile(s_path, d_mp3)
    # Also generate wav for instant low-latency playback
    stem = os.path.splitext(fname)[0]
    d_wav = os.path.join(sounds_dst, stem + ".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", d_mp3, "-ar", "44100", "-ac", "2", d_wav],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
print("Copied and converted sounds in assets/sounds/")

# 3. Process Annotations (copy 256x256 clean PNGs to assets/icons/)
ann_src = os.path.join(EXTRACT_DIR, "Annotations")
ann_dst = os.path.join(REPO_DIR, "assets", "icons")
os.makedirs(ann_dst, exist_ok=True)
for fn in os.listdir(ann_src):
    if fn.endswith("_1024x.png"):
        stem = fn.replace("_1024x.png", "")
        src_p = os.path.join(ann_src, fn)
        im_ann = Image.open(src_p).convert("RGBA").resize((256, 256), Image.Resampling.LANCZOS)
        im_ann.save(os.path.join(ann_dst, stem + ".png"))
print("Updated annotation icons in assets/icons/")
