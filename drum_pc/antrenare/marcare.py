"""Marcarea cadrelor pentru antrenare. Fiecare cadru vine cu chenarele găsite de program (model + împărțirea
pe trunchiuri); tu doar corectezi:

  tragi cu mouse-ul (click stânga)   = chenar nou, de la vârful copacului până JOS, unde trunchiul atinge solul
  click dreapta pe un chenar         = șterge chenarul
  1 / 2 / 3                          = tipul chenarului nou: 1 copac, 2 groapă, 3 indicator
  săgeată dreapta / Enter            = salvează și trece la cadrul următor
  săgeată stânga                     = salvează și înapoi
  Delete                             = cadrul nu e bun (neclar, fără drum): se sare la antrenare
  Ctrl+Z                             = anulează ultima modificare

La copaci: marginea de JOS a chenarului = locul unde trunchiul intră în pământ (de acolo se calculează
poziția pe hartă). Nu pune copaci pe carosabil și nu pune același copac de două ori.
Etichetele se scriu în date/etichete/<cadru>.txt (format YOLO)."""
import glob, os, sys, tkinter as tk
import cv2
import numpy as np
from PIL import Image, ImageTk

AICI = os.path.dirname(os.path.abspath(__file__))
DRUM = os.path.dirname(AICI)
IMG = os.path.join(AICI, "date", "imagini")
ETI = os.path.join(AICI, "date", "etichete")
CLASE = ["groapa", "copac", "semn"]                 # aceeași ordine ca în model/labels.txt
CUL = {"groapa": "#e03c31", "copac": "#2ea043", "semn": "#2f6fd6"}
TASTA = {"1": "copac", "2": "groapa", "3": "semn"}


def precalcul(img):
    """Chenarele propuse de programul actual: modelul + împărțirea rândurilor pe trunchiuri."""
    global _model
    sys.path.insert(0, DRUM)
    import analiza, trunchiuri
    analiza.log = lambda *a: None
    if "_model" not in globals():
        _model = analiza.Model(os.path.join(DRUM, "model"))
    H = img.shape[0]; rez = []
    for x0, y0, x1, y1, s, lab in trunchiuri.imparte(img, _model(img), analiza.PRAG_RAND):
        k = analiza.tip(lab)
        if s < analiza.PRAG[k]: continue
        if k == "copac" and y1 >= H - 3: continue
        rez.append([k, x0, y0, x1, y1])
    return rez


def citeste(nume, W, H):
    p = os.path.join(ETI, nume + ".txt")
    if not os.path.exists(p): return None
    out = []
    for l in open(p):
        v = l.split()
        if len(v) != 5: continue
        c, cx, cy, w, h = int(v[0]), *map(float, v[1:])
        out.append([CLASE[c], (cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H])
    return out


def scrie(nume, boxes, W, H):
    os.makedirs(ETI, exist_ok=True)
    with open(os.path.join(ETI, nume + ".txt"), "w") as f:
        for k, x0, y0, x1, y1 in boxes:
            x0, x1 = sorted((max(0, x0), min(W, x1))); y0, y1 = sorted((max(0, y0), min(H, y1)))
            if x1 - x0 < 2 or y1 - y0 < 2: continue
            f.write(f"{CLASE.index(k)} {(x0 + x1) / 2 / W:.6f} {(y0 + y1) / 2 / H:.6f} {(x1 - x0) / W:.6f} {(y1 - y0) / H:.6f}\n")


class Marcare:
    def __init__(self, root):
        self.root = root; self.fis = sorted(glob.glob(os.path.join(IMG, "*.jpg")))
        if not self.fis:
            raise SystemExit(f"Nu sunt cadre în {IMG}. Pornește întâi SCOATE_CADRE.bat.")
        self.i = next((k for k, f in enumerate(self.fis) if not os.path.exists(os.path.join(ETI, self._n(f) + ".txt"))), 0)
        self.tip = "copac"; self.istoric = []
        self.c = tk.Canvas(root, bg="#222", highlightthickness=0); self.c.pack(fill="both", expand=True)
        self.st = tk.Label(root, anchor="w", font=("Segoe UI", 11)); self.st.pack(fill="x")
        self.c.bind("<ButtonPress-1>", self.start); self.c.bind("<B1-Motion>", self.trage); self.c.bind("<ButtonRelease-1>", self.gata)
        self.c.bind("<Button-3>", self.sterge); root.bind("<Right>", lambda e: self.mergi(1)); root.bind("<Return>", lambda e: self.mergi(1))
        root.bind("<Left>", lambda e: self.mergi(-1)); root.bind("<Delete>", self.sari); root.bind("<Control-z>", self.anuleaza)
        for t in TASTA: root.bind(t, lambda e, t=t: self.alege(TASTA[t]))
        root.bind("<Configure>", lambda e: self.deseneaza())
        self.incarca()

    @staticmethod
    def _n(f): return os.path.splitext(os.path.basename(f))[0]

    def incarca(self):
        f = self.fis[self.i]; self.img = cv2.imread(f); H, W = self.img.shape[:2]; self.W, self.H = W, H
        b = citeste(self._n(f), W, H)
        if b is None:
            self.st.config(text="se calculează chenarele propuse…"); self.root.update()
            b = precalcul(self.img)
        self.boxes = b; self.istoric = []; self.deseneaza()

    def deseneaza(self):
        if not hasattr(self, "boxes"): return
        cw, ch = max(200, self.c.winfo_width()), max(200, self.c.winfo_height())
        self.s = min(cw / self.W, ch / self.H)
        rgb = cv2.cvtColor(cv2.resize(self.img, (int(self.W * self.s), int(self.H * self.s))), cv2.COLOR_BGR2RGB)
        self.tkimg = ImageTk.PhotoImage(Image.fromarray(rgb))
        self.c.delete("all"); self.c.create_image(0, 0, image=self.tkimg, anchor="nw")
        for k, x0, y0, x1, y1 in self.boxes:
            s = self.s; self.c.create_rectangle(x0 * s, y0 * s, x1 * s, y1 * s, outline=CUL[k], width=2)
            if k == "copac":
                cx = (x0 + x1) / 2 * s; self.c.create_oval(cx - 4, y1 * s - 4, cx + 4, y1 * s + 4, fill="red", outline="")
        n = sum(1 for b in self.boxes if b[0] == "copac"); gata = len(glob.glob(os.path.join(ETI, "*.txt")))
        self.st.config(text=f"cadrul {self.i + 1}/{len(self.fis)}  ·  {self._n(self.fis[self.i])}  ·  copaci: {n}  ·  "
                            f"tip nou: {self.tip} (1 copac, 2 groapă, 3 indicator)  ·  cadre marcate: {gata}")

    def alege(self, t): self.tip = t; self.deseneaza()

    def start(self, e): self.p0 = (e.x, e.y); self.r = self.c.create_rectangle(e.x, e.y, e.x, e.y, outline=CUL[self.tip], width=2, dash=(4, 2))
    def trage(self, e): self.c.coords(self.r, *self.p0, e.x, e.y)

    def gata(self, e):
        x0, y0 = self.p0; s = self.s
        if abs(e.x - x0) > 4 and abs(e.y - y0) > 4:
            self.istoric.append([b[:] for b in self.boxes])
            self.boxes.append([self.tip, min(x0, e.x) / s, min(y0, e.y) / s, max(x0, e.x) / s, max(y0, e.y) / s])
        self.deseneaza()

    def sterge(self, e):
        x, y = e.x / self.s, e.y / self.s
        sub = [b for b in self.boxes if b[1] <= x <= b[3] and b[2] <= y <= b[4]]
        if sub:
            self.istoric.append([b[:] for b in self.boxes])
            self.boxes.remove(min(sub, key=lambda b: (b[3] - b[1]) * (b[4] - b[2])))   # cel mai mic chenar de sub mouse
        self.deseneaza()

    def anuleaza(self, e=None):
        if self.istoric: self.boxes = self.istoric.pop(); self.deseneaza()

    def mergi(self, d):
        scrie(self._n(self.fis[self.i]), self.boxes, self.W, self.H)
        self.i = max(0, min(len(self.fis) - 1, self.i + d)); self.incarca()

    def sari(self, e=None):
        f = self.fis.pop(self.i); os.makedirs(os.path.join(AICI, "date", "sarite"), exist_ok=True)
        os.replace(f, os.path.join(AICI, "date", "sarite", os.path.basename(f)))
        if not self.fis: self.root.destroy(); return
        self.i = min(self.i, len(self.fis) - 1); self.incarca()


if __name__ == "__main__":
    r = tk.Tk(); r.title("Drum – marcarea copacilor pentru antrenare"); r.geometry("1400x900")
    Marcare(r); r.mainloop()
