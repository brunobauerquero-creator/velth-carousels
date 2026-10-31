"""Cut the comic library sheets into single assets.

People/mascot sheets: background flood-filled from the border -> transparent cutouts, one per grid cell.
Scene sheets: each panel is found by its light background rectangle and saved as an opaque crop.
"""
import pathlib
import numpy as np
from PIL import Image
from scipy import ndimage

S = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = S / "ill_new", S / "lib3"
OUT.mkdir(exist_ok=True)

PEOPLE = {
    "P1": ["meister", "meisterin", "sifa_m", "sifa_w"],
    "P2": ["geschaeftsfuehrer", "geschaeftsfuehrerin", "inspektorin", "monteur"],
    "P3": ["dachdecker", "elektrikerin", "lkw_fahrer", "saegewerker"],
    "P4": ["veranstaltungstechnikerin", "lagerist", "kfz_mechatronikerin", "malerin"],
}
MASCOTS = ["biber_stehen", "biber_zeigen", "biber_jubeln", "biber_klemmbrett",
           "schildkroete_stehen", "schildkroete_zeigen", "schildkroete_jubeln", "schildkroete_nachdenken"]


def background_mask(rgb: np.ndarray, tol: int = 28) -> np.ndarray:
    """Near-white pixels connected to the image border = background."""
    white = (rgb.min(axis=2) > 255 - tol)
    lab, _ = ndimage.label(white)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    return np.isin(lab, border[border > 0])


def cutout(cell: Image.Image, pad: int = 6) -> Image.Image:
    rgb = np.asarray(cell.convert("RGB"))
    fg = ~background_mask(rgb)
    # drop specks: keep components bigger than 0.5 % of the largest
    lab, n = ndimage.label(fg)
    if n:
        sizes = ndimage.sum(fg, lab, range(1, n + 1))
        keep = np.isin(lab, 1 + np.flatnonzero(sizes > sizes.max() * 0.005))
        fg = keep
    alpha = ndimage.gaussian_filter(fg.astype(float), 0.6)  # soften the 1px edge
    rgba = np.dstack([rgb, (np.clip(alpha * 1.4, 0, 1) * 255).astype(np.uint8)])
    ys, xs = np.nonzero(fg)
    box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, rgb.shape[1]), min(ys.max() + pad, rgb.shape[0]))
    img = Image.fromarray(rgba, "RGBA").crop(box)
    return img.resize((img.width * 2, img.height * 2), Image.LANCZOS)


def grid_cells(img: Image.Image, cols: int, rows: int):
    w, h = img.size
    for r in range(rows):
        for c in range(cols):
            yield img.crop((c * w // cols, r * h // rows, (c + 1) * w // cols, (r + 1) * h // rows))


def panels(img: Image.Image, expect: int = 4):
    """Find scene panels as large non-white rectangles."""
    rgb = np.asarray(img.convert("RGB"))
    fg = ~background_mask(rgb, tol=10)
    fg = ndimage.binary_opening(fg, iterations=3)
    lab, n = ndimage.label(fg)
    objs = ndimage.find_objects(lab)
    boxes = sorted(((s[1].stop - s[1].start) * (s[0].stop - s[0].start), s) for s in objs)[-expect:]
    boxes = [s for _, s in boxes]
    boxes.sort(key=lambda s: (round(s[0].start / 200), s[1].start))  # reading order
    for s in boxes:
        yield img.crop((s[1].start + 3, s[0].start + 3, s[1].stop - 3, s[0].stop - 3))


def sheet_cutouts(img: Image.Image, cols: int, rows: int, pad: int = 6):
    """Group foreground components into figures: the N largest are anchors, the rest join the nearest anchor.

    Grid cells alone cut figures whose shoes cross the cell line, so we segment the whole sheet instead.
    """
    n_fig = cols * rows
    rgb = np.asarray(img.convert("RGB"))
    fg = ~background_mask(rgb)
    lab, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, lab, range(1, n + 1))
    objs = ndimage.find_objects(lab)
    order = np.argsort(sizes)[::-1]
    anchors = list(order[:n_fig])
    members = {a: [a] for a in anchors}
    for i in order[n_fig:]:
        if sizes[i] < sizes.max() * 0.0005:
            continue
        def gap(a, b):
            sa, sb = objs[a], objs[b]
            dy = max(sa[0].start - sb[0].stop, sb[0].start - sa[0].stop, 0)
            dx = max(sa[1].start - sb[1].stop, sb[1].start - sa[1].stop, 0)
            return dx + dy
        members[min(anchors, key=lambda a: gap(i, a))].append(i)
    h, w = fg.shape
    result = {}
    for a, ms in members.items():
        s = objs[a]
        cy, cx = (s[0].start + s[0].stop) / 2, (s[1].start + s[1].stop) / 2
        cell = int(cy // (h / rows)) * cols + int(cx // (w / cols))
        m = np.isin(lab, [k + 1 for k in ms])
        alpha = ndimage.gaussian_filter(m.astype(float), 0.6)
        rgba = np.dstack([rgb, (np.clip(alpha * 1.4, 0, 1) * 255).astype(np.uint8)])
        ys, xs = np.nonzero(m)
        box = (max(xs.min() - pad, 0), max(ys.min() - pad, 0), min(xs.max() + pad, w), min(ys.max() + pad, h))
        im = Image.fromarray(rgba, "RGBA").crop(box)
        result[cell] = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    return [result[k] for k in sorted(result)]


if __name__ == "__main__":
    for sheet, names in PEOPLE.items():
        for name, im in zip(names, sheet_cutouts(Image.open(SRC / f"{sheet}.png"), 2, 2)):
            im.save(OUT / f"p_{name}.png")
    for name, im in zip(MASCOTS, sheet_cutouts(Image.open(SRC / "M1.png"), 4, 2)):
        im.save(OUT / f"m_{name}.png")
    for f in sorted(SRC.glob("S*.png"), key=lambda p: int(p.stem[1:])):
        for i, crop in enumerate(panels(Image.open(f)), 1):
            out = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
            out.save(OUT / f"s{int(f.stem[1:]):02d}_{i}.png")
    print(len(list(OUT.glob("*.png"))), "assets")
