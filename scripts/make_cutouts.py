#!/usr/bin/env python3
"""Download Legacy Survey g,r,z FITS cutouts for data/voorwerp_analogues.csv and build RGB PNGs.

Uses fetch_cutout_set from ../decals_cutout/fetch_decals_cube.py. The field of view is a
fixed physical box (BOX_KPC on a side, Planck18), clipped to [MIN_ARCSEC, MAX_ARCSEC];
the pixel scale is coarsened so that no cutout exceeds MAX_PIX pixels.

Usage: python scripts/make_cutouts.py [--layer ls-dr9]   (falls back to ls-dr10 off-footprint)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.error import HTTPError

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from astropy.cosmology import Planck18
from astropy.io import fits
from astropy.visualization import make_lupton_rgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "decals_cutout"))
from fetch_decals_cube import fetch_cutout_set, sanitize_name  # noqa: E402

BOX_KPC = 160.0  # covers the most distant known cloud (NGC 5514, 75 kpc)
MIN_ARCSEC, MAX_ARCSEC = 60.0, 600.0
NATIVE_PIXSCALE, MAX_PIX = 0.262, 800


def field_of_view(z: float) -> tuple[float, float]:
    """Return (size_arcsec, pixscale) for a BOX_KPC box at redshift z."""
    kpc_per_arcsec = Planck18.kpc_proper_per_arcmin(z).value / 60.0
    size = float(np.clip(BOX_KPC / kpc_per_arcsec, MIN_ARCSEC, MAX_ARCSEC))
    return size, max(NATIVE_PIXSCALE, size / MAX_PIX)


def rgb_image(g: np.ndarray, r: np.ndarray, z: np.ndarray, q: float = 8.0) -> np.ndarray:
    """Lupton asinh RGB (z->R, r->G, g->B) in units of the r-band sky noise."""
    bands = [np.nan_to_num(b) for b in (z, r, g)]
    bands = [b - np.median(b) for b in bands]
    sigma = 1.4826 * np.median(np.abs(bands[1]))  # MAD of r, sky-dominated
    scale = (1.0, 1.0, 1.5)  # mild g boost, close to Legacy viewer colour balance
    return make_lupton_rgb(*[s * b / sigma for s, b in zip(scale, bands)],
                           minimum=-1.0, stretch=30.0, Q=q)


def fetch_grz(layers: tuple[str, ...] = ("ls-dr9", "ls-dr10"), **kw) -> tuple[dict, str]:
    """fetch_cutout_set for g,r,z, trying layers in order (DR9 returns HTTP 500 off-footprint)."""
    for layer in layers:
        try:
            return fetch_cutout_set(layer=layer, bands=("g", "r", "z"), verbose=False, **kw), layer
        except HTTPError as exc:
            if exc.code != 500 or layer == layers[-1]:
                raise


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", default="ls-dr9")
    args = ap.parse_args()

    cat = pd.read_csv(ROOT / "data" / "voorwerp_analogues.csv")
    fits_dir, rgb_dir = ROOT / "data" / "cutouts_fits", ROOT / "data" / "cutouts_rgb"
    rgb_dir.mkdir(parents=True, exist_ok=True)

    for row in cat.itertuples():
        size, pixscale = field_of_view(row.z)
        paths, layer = fetch_grz(layers=tuple(dict.fromkeys((args.layer, "ls-dr10"))),
                                 ra=row.ra, dec=row.dec, name=row.name, size_arcsec=size,
                                 pixscale=pixscale, output_dir=fits_dir)
        g, r, z = (fits.getdata(paths[b]).astype(float) for b in "grz")
        if not all(np.any(b) for b in (g, r, z)):
            print(f"{row.name}: empty band(s), skipped")
            continue
        out = rgb_dir / f"{sanitize_name(row.name)}_{layer}_rgb.png"
        plt.imsave(out, rgb_image(g, r, z), origin="lower")
        print(f"{row.name}: {size:.0f}\" at {pixscale:.3f}\"/pix -> {out.name}")


if __name__ == "__main__":
    main()
