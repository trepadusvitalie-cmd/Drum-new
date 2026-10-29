"""Cadrele de marcat: din arhivele filmărilor (.zip cu video.mp4 + traseu.csv) se scoate un cadru la
fiecare ~PAS_M metri parcurși (mașina oprită nu dă cadre noi). Cadrele merg în antrenare/date/imagini.

Folosire:  python scoate_cadre.py <arhiva.zip | folder cu arhive | folder cu poze> [pas_m]
Pozele .jpg/.png/.webp dintr-un folder se copiază direct (de ex. capturi de ecran cu alei)."""
import csv, glob, io, math, os, shutil, sys, zipfile
import cv2
import numpy as np

AICI = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(AICI, "date", "imagini")
PAS_M = 8.0


def distante(rows):
    """Distanța parcursă (m) la fiecare poziție din traseu.csv (aproximare locală, suficientă pentru pas)."""
    d = [0.0]
    for a, b in zip(rows, rows[1:]):
        k = 111320.0
        dx = (b["lon"] - a["lon"]) * k * math.cos(math.radians(a["lat"])); dy = (b["lat"] - a["lat"]) * k
        d.append(d[-1] + math.hypot(dx, dy))
    return np.array(d)


def din_arhiva(zp, pas):
    nume = os.path.splitext(os.path.basename(zp))[0]
    with zipfile.ZipFile(zp) as z:
        vid = next((n for n in z.namelist() if n.lower().endswith(".mp4")), None)
        trs = next((n for n in z.namelist() if n.lower().endswith("traseu.csv")), None)
        if not vid: print(f"  {nume}: fără video.mp4"); return 0
        tmp = os.path.join(AICI, "date", "_tmp.mp4")
        with z.open(vid) as f, open(tmp, "wb") as g: shutil.copyfileobj(f, g)
        rows = []
        if trs:
            for r in csv.DictReader(io.TextIOWrapper(z.open(trs), encoding="utf-8")):
                try: rows.append({k: float(r[k]) for k in ("t_ms", "lon", "lat")})
                except (KeyError, ValueError): pass
    rows.sort(key=lambda r: r["t_ms"])
    cap = cv2.VideoCapture(tmp); fps = cap.get(cv2.CAP_PROP_FPS) or 30
    t = np.array([r["t_ms"] for r in rows]) if len(rows) > 1 else None
    d = distante(rows) if t is not None else None
    ultim, fi, n = -1e9, -1, 0
    while True:
        if not cap.grab(): break
        fi += 1; tms = fi * 1000.0 / fps
        if t is not None:
            if tms < t[0] or tms > t[-1]: continue
            dist = float(np.interp(tms, t, d))
        else:
            dist = tms / 1000.0 * 10                     # fără traseu: ~un cadru la fiecare secundă
        if dist - ultim < pas: continue
        ultim = dist
        ok, img = cap.retrieve()
        if ok:
            cv2.imwrite(os.path.join(IMG, f"{nume}_{fi:06d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92]); n += 1
    cap.release(); os.remove(tmp)
    print(f"  {nume}: {n} cadre")
    return n


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    os.makedirs(IMG, exist_ok=True)
    src = sys.argv[1]; pas = float(sys.argv[2]) if len(sys.argv) > 2 else PAS_M
    zips = [src] if src.lower().endswith(".zip") else sorted(glob.glob(os.path.join(src, "*.zip")))
    total = sum(din_arhiva(z, pas) for z in zips)
    if os.path.isdir(src):
        for p in sorted(glob.glob(os.path.join(src, "*"))):
            if os.path.splitext(p)[1].lower() in (".jpg", ".jpeg", ".png", ".webp"):
                im = cv2.imread(p)
                if im is not None:
                    cv2.imwrite(os.path.join(IMG, os.path.splitext(os.path.basename(p))[0] + ".jpg"), im); total += 1
    print(f"Gata: {total} cadre în {IMG}. Urmează MARCHEAZA.bat.")


if __name__ == "__main__":
    main()
