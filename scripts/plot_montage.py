#!/usr/bin/env python3
"""Montage of all RGB cutouts in data/cutouts_rgb, ordered as in data/voorwerp_analogues.csv.

Each panel is a BOX_KPC-wide field (see make_cutouts.py) unless clipped; the white bar is 20 kpc.
Usage: python scripts/plot_montage.py  -> data/montage_rgb.png
"""
import matplotlib.pyplot as plt
import pandas as pd
from astropy.cosmology import Planck18

from make_cutouts import ROOT, field_of_view  # also puts ../decals_cutout on sys.path
from fetch_decals_cube import sanitize_name

cat = pd.read_csv(ROOT / "data" / "voorwerp_analogues.csv")
ncol = 6
fig, axes = plt.subplots(-(-len(cat) // ncol), ncol, figsize=(2.6 * ncol, 2.8 * -(-len(cat) // ncol)))
for ax, row in zip(axes.flat, cat.itertuples()):
    ax.set_axis_off()
    pngs = sorted((ROOT / "data" / "cutouts_rgb").glob(f"{sanitize_name(row.name)}_ls-dr*_rgb.png"))
    if not pngs:
        ax.set_title(f"{row.name}\nmissing", fontsize=8)
        continue
    img = plt.imread(pngs[0])
    ax.imshow(img)
    size, _ = field_of_view(row.z)
    kpc_per_arcsec = Planck18.kpc_proper_per_arcmin(row.z).value / 60.0
    npix = img.shape[1]
    bar = 20.0 / kpc_per_arcsec / size * npix  # 20 kpc in pixels
    ax.plot([0.05 * npix, 0.05 * npix + bar], [0.93 * npix] * 2, color="w", lw=2)
    layer = pngs[0].name.split("_ls-")[1].split("_")[0]
    ax.set_title(f"{row.name}  z={row.z:.3f}\n{size:.0f}\" ls-{layer}", fontsize=8)
for ax in axes.flat[len(cat):]:
    ax.set_axis_off()
fig.tight_layout()
out = ROOT / "data" / "montage_rgb.png"
fig.savefig(out, dpi=110)
print(f"Wrote {out}")
