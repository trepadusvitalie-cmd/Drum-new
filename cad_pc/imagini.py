"""Import de imagini raster (TIFF / GeoTIFF, JPG, PNG) în coordonate reale.
Poziția se ia din fișierul de georeferențiere (.tfw / .tifw / .jgw / .pgw / .wld) sau din etichetele GeoTIFF
(ModelPixelScale + ModelTiepoint, ori ModelTransformation). Imaginea intră în desen ca entitate IMAGE
(se salvează în DWG/DXF cu legătura la fișier, la fel ca în AutoCAD: „Присоединить”)."""
import os, threading
import tkinter as tk
from tkinter import filedialog, messagebox
from stil import *

try:
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None               # ortofotoplanurile au zeci de mii de pixeli
except Exception: Image = None

TIPURI = [("Растровые изображения", "*.tif *.tiff *.jpg *.jpeg *.png *.bmp"), ("TIFF / GeoTIFF", "*.tif *.tiff"), ("Все файлы", "*.*")]
PREVIZ = 4096                                   # latura maximă a copiei ținute în RAM pentru ecran


def _fisier_world(cale):
    baza, ext = os.path.splitext(cale); ext = ext.lower().lstrip(".")
    cand = [baza + "." + ext[0] + ext[-1] + "w", baza + "." + ext + "w", baza + ".wld", cale + "w"]
    for c in cand + [x.upper() for x in cand] + [baza + "." + (ext[0] + ext[-1] + "w").upper()]:
        if os.path.isfile(c): return c
    return None


def georef(cale):
    """-> dict(x, y = colțul stânga-jos, px, py = mărimea pixelului, w, h, sursa, rot) sau doar w, h dacă nu e georeferențiată"""
    with Image.open(cale) as im:
        w, h = im.size; tag = getattr(im, "tag_v2", {}) or {}
        gt_scale, gt_tie, gt_mat = tag.get(33550), tag.get(33922), tag.get(34264)
    r = {"w": w, "h": h, "sursa": None, "rot": False}
    wf = _fisier_world(cale)
    if wf:
        try:
            v = [float(l.strip().replace(",", ".")) for l in open(wf, encoding="latin-1").read().split("\n") if l.strip()][:6]
            a, d, b, e, c, f = v                    # c, f = centrul pixelului din stânga-sus
            r.update(px=abs(a), py=abs(e), x=c - a / 2, y=f - e / 2 + e * h, sursa=os.path.basename(wf), rot=abs(b) > 1e-12 or abs(d) > 1e-12)
            return r
        except Exception: pass
    try:
        if gt_scale and gt_tie:
            sx, sy = float(gt_scale[0]), float(gt_scale[1]); i, j, _, X, Y = [float(t) for t in gt_tie[:5]]
            x0, y0 = X - i * sx, Y + j * sy             # colțul stânga-sus
            r.update(px=sx, py=sy, x=x0, y=y0 - h * sy, sursa="GeoTIFF"); return r
        if gt_mat and len(gt_mat) >= 8:
            m = [float(t) for t in gt_mat]
            r.update(px=abs(m[0]), py=abs(m[5]), x=m[3], y=m[7] + m[5] * h, sursa="GeoTIFF", rot=abs(m[1]) > 1e-12 or abs(m[4]) > 1e-12); return r
    except Exception: pass
    return r


def previzualizare(cale):
    """copie micșorată (max PREVIZ px) în RGBA; întoarce (imagine, factor de micșorare)"""
    im = Image.open(cale)
    try:
        if im.mode in ("I;16", "I;16B", "I;16L", "I"):
            lo, hi = im.getextrema() if im.mode == "I" else (0, 65535)
            im = im.point(lambda v: (v - lo) * 255 / max(hi - lo, 1)).convert("L")
        k = max(1, -(-max(im.size) // PREVIZ))
        if k > 1:
            try: im.draft(im.mode, (im.size[0] // k, im.size[1] // k))
            except Exception: pass
            im = im.reduce(max(1, -(-max(im.size) // PREVIZ)))
        im = im.convert("RGBA"); im.load()
        return im, k
    except Exception:
        im.close(); raise


class Imagini:
    def __init__(self, app): self.app = app

    @property
    def doc(self): return self.app.doc

    def importa(self, cale=None):
        if self.doc is None: return self.app.mesaj("Сначала откройте или создайте чертеж.")
        if Image is None: return messagebox.showerror("Изображение", "Нет модуля Pillow для изображений.")
        cale = cale or filedialog.askopenfilename(title="Присоединить растровое изображение", filetypes=TIPURI)
        if not cale: return
        try: g = georef(cale)
        except Exception as ex: return messagebox.showerror("Изображение", f"Не удалось открыть изображение:\n{ex}")
        self._dialog(cale, g)

    def _dialog(self, cale, g):
        d = tk.Toplevel(self.app.root); d.title("Изображение: " + os.path.basename(cale)); d.configure(bg=CORP); d.transient(self.app.root)
        ref = g.get("sursa")
        txt = f"Привязка: {ref} – координаты взяты из файла." if ref else "Привязки нет (.tfw / GeoTIFF не найден) – укажите координаты."
        tk.Label(d, text=txt, bg=CORP, fg="#8fd18f" if ref else "#f0c040", font=F_MIC).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 4), sticky="w")
        tk.Label(d, text=f"Размер: {g['w']} × {g['h']} пикс.", bg=CORP, fg=GRI, font=F_MIC).grid(row=1, column=0, columnspan=2, padx=10, sticky="w")
        if g.get("rot"): tk.Label(d, text="Поворот в файле привязки не поддерживается – вставлено без поворота.", bg=CORP, fg="#f0c040", font=F_MIC).grid(row=2, column=0, columnspan=2, padx=10, sticky="w")
        campuri = [("Левый нижний угол X:", "x", 0.0), ("Левый нижний угол Y:", "y", 0.0), ("Размер пикселя X:", "px", 1.0), ("Размер пикселя Y:", "py", 1.0)]
        intr = {}
        for i, (et, k, impl) in enumerate(campuri, 3):
            tk.Label(d, text=et, bg=CORP, fg=TEXT, font=F_MIC).grid(row=i, column=0, padx=10, pady=3, sticky="e")
            w = tk.Entry(d, bg="#2b313a", fg=TEXT, insertbackground=TEXT, relief="flat", width=22); w.grid(row=i, column=1, padx=10, pady=3)
            w.insert(0, repr(round(g.get(k, impl), 6))); intr[k] = w
        def ok(ev=None):
            try: val = {k: float(w.get().replace(",", ".")) for k, w in intr.items()}
            except ValueError: return messagebox.showerror("Изображение", "Неверное число.", parent=d)
            if val["px"] <= 0 or val["py"] <= 0: return messagebox.showerror("Изображение", "Размер пикселя должен быть > 0.", parent=d)
            d.destroy(); self.adauga(cale, g["w"], g["h"], val)
        b = tk.Label(d, text="OK", bg=ALBASTRU, fg="white", font=F_MIC, padx=16, pady=4); b.grid(row=8, column=1, sticky="e", padx=10, pady=10)
        b.bind("<Button-1>", ok); d.bind("<Return>", ok)

    def adauga(self, cale, w, h, val):
        app = self.app; app.ed.instantaneu([])
        idef = self.doc.add_image_def(filename=os.path.abspath(cale), size_in_pixel=(w, h))
        img = self.doc.modelspace().add_image(idef, insert=(val["x"], val["y"]), size_in_units=(w * val["px"], h * val["py"]), rotation=0,
                                              dxfattribs={"layer": app.strat_curent()})
        img.dxf.flags = 1 | 2 | 8                    # afișează imaginea, și când nu e aliniată; cu decupare
        app.ed.gata_modificare(); app.modificat = True; app._titlu()
        x0, y0, x1, y1 = val["x"], val["y"], val["x"] + w * val["px"], val["y"] + h * val["py"]
        app.v.zoom_fereastra(x0, y0, x1, y1)
        app.mesaj(f"Изображение {os.path.basename(cale)} вставлено: X {x0:.3f} … {x1:.3f}, Y {y0:.3f} … {y1:.3f}.")


class CachePreviz:
    """copiile micșorate ale imaginilor, încărcate pe fir de fundal ca să nu blocheze ecranul"""
    def __init__(self, cv, dupa): self.cv = cv; self.dupa = dupa; self.c = {}

    def ia(self, cale):
        if cale in self.c: return self.c[cale]
        self.c[cale] = None
        def lucru():
            try: r = previzualizare(cale)
            except Exception: r = False
            self.c[cale] = r
        threading.Thread(target=lucru, daemon=True).start()
        def verifica():                             # pe firul ecranului: redesenez când s-a încărcat
            if self.c.get(cale) is None: self.cv.after(150, verifica)
            else: self.dupa()
        self.cv.after(150, verifica)
        return None
