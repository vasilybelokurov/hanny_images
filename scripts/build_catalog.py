#!/usr/bin/env python3
"""Build the catalogue of spectroscopically confirmed Hanny's Voorwerp analogues.

Sources (tables parsed from arXiv LaTeX sources in data/raw/):
- Keel et al. 2012, MNRAS 420, 878 (arXiv:1110.6921), table "Results of long-slit
  spectroscopy", section "Confirmed AGN-ionized": 19 systems.
- Keel et al. 2017, ApJ 835, 256 (arXiv:1612.06006), Table 1: adds IC 2497 itself.
- Keel et al. 2024, MNRAS 530, 1624 (arXiv:2403.04898), Table 5: the TELPERION distant
  EELRs (Mkn 266 duplicates Keel 2012). Positions resolved with NED.

Writes data/voorwerp_analogues.csv.
"""
from __future__ import annotations

import io
import json
import re
import tarfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

SDSS_RE = re.compile(r"SDSS J(\d{2})(\d{2})(\d{2}\.\d+)([+-])(\d{2})(\d{2})(\d{2}\.\d+)")

# TELPERION distant-EELR hosts not already in Keel 2012: (NED name, z, R_proj kpc, fading?)
TELPERION = [
    ("Mkn 1", 0.016, 13, "no"),
    ("NGC 7252", 0.016, 13, "yes"),
    ("NGC 235", 0.022, 26, "ambiguous"),
    ("NGC 5514", 0.024, 75, "yes"),
    ("NGC 5278", 0.025, 29, "yes"),  # NGC 5278/9 pair; one cutout covers both
    ("UGC 5941", 0.024, 35, "candidate"),
]


def sdss_name_to_radec(name: str) -> tuple[float, float]:
    """Convert 'SDSS Jhhmmss.ss+ddmmss.s' to (ra, dec) in degrees."""
    h, m, s, sign, d, dm, ds = SDSS_RE.search(name).groups()
    ra = 15.0 * (int(h) + int(m) / 60 + float(s) / 3600)
    dec = int(d) + int(dm) / 60 + float(ds) / 3600
    return ra, -dec if sign == "-" else dec


def ned_radec(name: str) -> tuple[float, float]:
    url = "https://ned.ipac.caltech.edu/srs/ObjectLookup?name=" + quote(name)
    pos = json.load(urlopen(url, timeout=60))["Preferred"]["Position"]
    return pos["RA"], pos["Dec"]


def arxiv_tex(arxiv_id: str) -> str:
    """Return the LaTeX source of an arXiv paper, downloading it to data/raw/ if missing."""
    src = RAW / f"src_{arxiv_id}"
    if not list(src.glob("*.tex")):
        src.mkdir(parents=True, exist_ok=True)
        payload = urlopen(f"https://arxiv.org/e-print/{arxiv_id}", timeout=120).read()
        tarfile.open(fileobj=io.BytesIO(payload)).extractall(src, filter="data")
    return next(src.glob("*.tex")).read_text()


def keel2012_confirmed() -> list[dict]:
    tex = arxiv_tex("1110.6921")
    block = tex.split("Confirmed AGN-ionized:")[1].split("Other cloud types:")[0]
    rows = []
    for line in block.splitlines():
        if "SDSS J" not in line:
            continue
        cols = [c.strip() for c in line.split("%")[0].rstrip("\\ ").split("&")]
        ra, dec = sdss_name_to_radec(cols[0])
        rows.append(dict(name=cols[4] or cols[0].replace("SDSS ", ""), sdss_name=cols[0],
                         ra=ra, dec=dec, z=float(re.sub(r"\$.*", "", cols[2])),
                         nucleus=re.sub(r"\$.*", "", cols[3]).strip(), source="Keel2012"))
    return rows


def main() -> None:
    rows = keel2012_confirmed()
    ra, dec = sdss_name_to_radec("SDSS J094104.11+344358.4")  # Keel 2017 Table 1
    rows.insert(0, dict(name="IC 2497", sdss_name="SDSS J094104.11+344358.4", ra=ra, dec=dec,
                        z=0.0502, nucleus="Sy 2", source="Keel2017 (Hanny's Voorwerp)"))
    for name, z, rproj, fading in TELPERION:
        ra, dec = ned_radec(name)
        rows.append(dict(name=name, ra=ra, dec=dec, z=z, source="TELPERION (Keel2024)",
                         eelr_rproj_kpc=rproj, fading=fading))
    df = pd.DataFrame(rows)
    out = ROOT / "data" / "voorwerp_analogues.csv"
    df.to_csv(out, index=False, float_format="%.6f")
    print(df[["name", "ra", "dec", "z", "source"]].to_string())
    print(f"Wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
