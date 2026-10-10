"""Clean Blender renders for the web: subtract alpha floor, feather edges, trim, export PNG+WebP.
Usage: python postprocess_renders.py <in.png> <out_dir> [name]"""
import sys, os
import numpy as np
from PIL import Image
src, outdir = sys.argv[1], sys.argv[2]; name = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(os.path.basename(src))[0]
im = np.asarray(Image.open(src).convert("RGBA")).astype(np.float32)
a = im[..., 3] / 255.0
a = np.clip((a - 0.02) / 0.98, 0, 1)                      # subtract shadow-catcher alpha floor
h, w = a.shape; m = int(min(h, w) * 0.10)                  # 10% edge vignette so shadows never show a rectangle
ramp = lambda n: np.clip(np.minimum(np.arange(n), np.arange(n)[::-1]) / m, 0, 1)
a *= np.outer(ramp(h), ramp(w)) ** 1.5
im[..., 3] = a * 255
ys, xs = np.where(a > 0.01); pad = 24
y0, y1, x0, x1 = max(ys.min() - pad, 0), min(ys.max() + pad, h), max(xs.min() - pad, 0), min(xs.max() + pad, w)
out = Image.fromarray(im[y0:y1, x0:x1].astype(np.uint8), "RGBA")
os.makedirs(outdir, exist_ok=True)
out.save(f"{outdir}/{name}.png", optimize=True); out.save(f"{outdir}/{name}.webp", quality=88, method=6)
print(name, out.size, os.path.getsize(f"{outdir}/{name}.webp") // 1024, "KB webp")
