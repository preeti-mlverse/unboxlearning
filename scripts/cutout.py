"""Cut characters out of a character sheet: background-flood removal + largest-component keep + soft edges.

usage: python cutout.py detect <sheet> <x0> <y0> <x1> <y1>
       python cutout.py cut <sheet> <out.png> <x0> <y0> <x1> <y1> [min_part=0.02]
"""
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

TOL = 26  # max channel distance from the paper colour that still counts as background


def load(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.int16)


def paper_color(a):
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    return np.median(border, axis=0)


def foreground(a, tol=TOL):
    bg = paper_color(a)
    diff = np.abs(a - bg).max(axis=2)
    near = diff <= tol
    # background = paper-coloured pixels connected to the crop border (enclosed white shapes stay)
    lab, _ = ndimage.label(near)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bgmask = np.isin(lab, list(edge))
    return ~bgmask


def detect(path, box):
    a = load(path)[box[1]:box[3], box[0]:box[2]]
    fg = ndimage.binary_opening(foreground(a), iterations=2)
    lab, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, lab, range(1, n + 1))
    objs = ndimage.find_objects(lab)
    for i in np.argsort(-sizes)[:12]:
        sl = objs[i]
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        print(f"size {int(sizes[i]):>7}  box x {x0 + box[0]}-{x1 + box[0]}  y {y0 + box[1]}-{y1 + box[1]}")


def cut(path, out, box, min_part=0.02):
    img = Image.open(path).convert("RGB")
    a = np.asarray(img).astype(np.int16)[box[1]:box[3], box[0]:box[2]]
    fg = foreground(a)
    lab, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s >= sizes.max() * min_part]
    mask = np.isin(lab, keep)
    mask = ndimage.binary_fill_holes(mask) & (mask | ndimage.binary_fill_holes(mask))
    alpha = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    rgba = img.crop(box).convert("RGBA")
    rgba.putalpha(alpha)
    bb = rgba.getbbox()
    rgba = rgba.crop(bb)
    rgba.save(out)
    print(out, rgba.size)


if __name__ == "__main__":
    cmd, sheet = sys.argv[1], sys.argv[2]
    if cmd == "detect":
        detect(sheet, tuple(map(int, sys.argv[3:7])))
    else:
        cut(sheet, sys.argv[3], tuple(map(int, sys.argv[4:8])), float(sys.argv[8]) if len(sys.argv) > 8 else 0.02)
