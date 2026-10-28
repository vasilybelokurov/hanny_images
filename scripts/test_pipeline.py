"""Run: python -m pytest -q scripts/test_pipeline.py"""
import numpy as np

from build_catalog import sdss_name_to_radec
from make_cutouts import field_of_view, rgb_image


def test_sdss_name_ic2497():
    ra, dec = sdss_name_to_radec("SDSS J094104.11+344358.4")
    assert abs(ra - 145.267125) < 1e-6 and abs(dec - 34.732889) < 1e-6


def test_sdss_name_negative_dec():
    ra, dec = sdss_name_to_radec("SDSS J033013.26-053235.9")
    assert dec < 0 and abs(dec + (5 + 32 / 60 + 35.9 / 3600)) < 1e-6


def test_field_of_view_limits():
    size, pix = field_of_view(0.05)  # ~1 kpc/arcsec -> ~160 arcsec at native scale
    assert 140 < size < 180 and pix == 0.262
    size, pix = field_of_view(0.0086)  # NGC 4388: clipped, coarser pixels
    assert size == 600 and size / pix <= 800 + 1e-6


def test_rgb_shape_and_colour():
    rng = np.random.default_rng(1)
    noise = lambda: rng.normal(0, 1, (64, 64))
    g, r, z = noise(), noise(), noise()
    g[30:34, 30:34] += 200  # a g-only "[O III]" blob must come out blue
    img = rgb_image(g, r, z)
    assert img.shape == (64, 64, 3) and img.dtype == np.uint8
    pix = img[32, 32].astype(int)
    assert pix[2] > pix[0] + 50 and pix[2] > pix[1] + 50


def test_layer_fallback_outside_dr9(monkeypatch):
    """NGC 7252 (Dec -24.7) is outside DR9: the viewer returns HTTP 500, DR10 works."""
    from urllib.error import HTTPError
    import make_cutouts

    def fake_fetch(*, layer, **kw):
        if layer == "ls-dr9":
            raise HTTPError("url", 500, "Internal Server Error", {}, None)
        return {b: f"{layer}_{b}.fits" for b in "grz"}

    monkeypatch.setattr(make_cutouts, "fetch_cutout_set", fake_fetch)
    paths, layer = make_cutouts.fetch_grz(ra=335.19, dec=-24.68, name="NGC 7252",
                                          size_arcsec=400, pixscale=0.5, output_dir=".")
    assert layer == "ls-dr10" and paths["g"] == "ls-dr10_g.fits"
