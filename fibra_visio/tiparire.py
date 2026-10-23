"""Formatele de foaie (A1…A5) și tipărirea pe imprimantă (Windows, fără Visio).
Desenul paginii e înregistrat (linii, suprafețe, texte) cu același desenator ca pe ecran, apoi redat pe imprimantă."""
import math

MM = 1 / 25.4
FORMATE = {"A1": (841, 594), "A2": (594, 420), "A3": (420, 297), "A4": (297, 210), "A5": (210, 148)}   # mm, culcat
IMPLICIT = "A3"
DMPAPER = {"A2": 66, "A3": 8, "A4": 9, "A5": 11}          # A1 nu are cod standard: îl dau ca mărime proprie


def marime(fmt, culcat=True):
    """-> (lățime, înălțime) în inch, ca în Visio"""
    w, h = FORMATE[fmt]
    if not culcat: w, h = h, w
    return w * MM, h * MM


def recunoaste(w, h):
    """(lățime, înălțime) în inch -> („A3”, culcat) sau (None, culcat) dacă e altă mărime"""
    culcat = w >= h
    a, b = max(w, h) / MM, min(w, h) / MM
    for k, (x, y) in FORMATE.items():
        if abs(a - x) < 4 and abs(b - y) < 4: return k, culcat
    return None, culcat


# ---------------------------------------------------------------- înregistrarea desenului
class Inregistrare:
    """se dă drept Canvas pentru desenator: ține minte ce s-a desenat, ca să-l redau pe imprimantă"""

    def __init__(self): self.op = []

    def create_polygon(self, *xy, fill="", outline="", **k): self.op.append(("poligon", _perechi(xy), fill)); return len(self.op)

    def create_line(self, *xy, fill="#000000", width=1, dash=None, **k): self.op.append(("linie", _perechi(xy), fill, width, dash)); return len(self.op)

    def create_rectangle(self, x0, y0, x1, y1, fill="", outline="", width=1, dash=None, **k):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        if fill: self.op.append(("poligon", pts[:4], fill))
        if outline: self.op.append(("linie", pts, outline, width, dash))
        return len(self.op)

    def create_oval(self, *a, **k): return 0

    def create_text(self, x, y, text="", font=("Arial", -10, ""), fill="#000000", justify="center", angle=0.0, width=None, **k):
        self.op.append(("text", x, y, text, font, fill, justify, angle or 0.0, width)); return len(self.op)

    def bbox(self, *a): return None

    def tag_lower(self, *a): pass

    def delete(self, *a): pass


def _perechi(xy):
    if len(xy) == 1: xy = xy[0]
    xy = list(xy)
    if xy and isinstance(xy[0], (tuple, list)): return [tuple(p) for p in xy]
    return [(xy[i], xy[i + 1]) for i in range(0, len(xy) - 1, 2)]


# ---------------------------------------------------------------- imprimantele
def imprimante():
    import win32print
    try: implicita = win32print.GetDefaultPrinter()
    except Exception: implicita = None
    nume = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
    if implicita in nume: nume.remove(implicita); nume.insert(0, implicita)
    return nume


def _rgb(c):
    c = (c or "#000000").lstrip("#")
    if len(c) != 6: return 0
    r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    return r | (g << 8) | (b << 16)


def deschide_dc(imprimanta, fmt, culcat, copii=1):
    """contextul imprimantei, cu foaia aleasă (A1…A5) și orientarea"""
    import win32print, win32gui, win32ui, win32con
    h = win32print.OpenPrinter(imprimanta)
    try: dm = win32print.GetPrinter(h, 2)["pDevMode"]
    finally: win32print.ClosePrinter(h)
    if fmt in DMPAPER:
        dm.PaperSize = DMPAPER[fmt]; dm.Fields |= win32con.DM_PAPERSIZE
    else:                                                          # A1: mărime proprie (zecimi de mm)
        w, l = FORMATE[fmt][1], FORMATE[fmt][0]
        dm.PaperSize = 256; dm.PaperWidth = w * 10; dm.PaperLength = l * 10
        dm.Fields |= win32con.DM_PAPERSIZE | win32con.DM_PAPERWIDTH | win32con.DM_PAPERLENGTH
    dm.Orientation = 2 if culcat else 1; dm.Copies = max(1, int(copii))
    dm.Fields |= win32con.DM_ORIENTATION | win32con.DM_COPIES
    hdc = win32gui.CreateDC("WINSPOOL", imprimanta, dm)
    return win32ui.CreateDCFromHandle(hdc)


def tipareste(pagini, imprimanta, fmt=IMPLICIT, culcat=True, copii=1, titlu="Fibra Visio"):
    """pagini: [(lățime_inch, înălțime_inch, deseneaza(rec, zoom, ox, oy))] -> o foaie pentru fiecare pagină, potrivită pe foaie"""
    import win32ui
    dc = deschide_dc(imprimanta, fmt, culcat, copii)
    HR, VR = dc.GetDeviceCaps(8), dc.GetDeviceCaps(10)            # HORZRES, VERTRES: zona tipăribilă, în puncte
    dc.StartDoc(titlu)
    try:
        for W, H, deseneaza in pagini:
            z = min(HR / W, VR / H)                                 # potrivit pe foaie, păstrând proporțiile
            ox, oy = (HR - W * z) / 2, (VR - H * z) / 2
            rec = Inregistrare(); deseneaza(rec, z, ox, oy)
            dc.StartPage(); reda(dc, rec.op, z); dc.EndPage()
        dc.EndDoc()
    except Exception:
        try: dc.AbortDoc()
        except Exception: pass
        raise
    finally:
        try: dc.DeleteDC()
        except Exception: pass


# ---------------------------------------------------------------- redarea pe imprimantă (GDI)
def _liniute(pts, model):
    """linia întreruptă împărțită în bucăți (pixelii modelului sunt la scara ecranului: îi măresc)"""
    out = []; i = 0; rest = model[0]; desen = True; cur = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1]); pos = 0.0
        while L - pos > rest:
            pos += rest; p = (a[0] + (b[0] - a[0]) * pos / L, a[1] + (b[1] - a[1]) * pos / L)
            if desen: cur.append(p); out.append(cur)
            cur = [p]; desen = not desen; i = (i + 1) % len(model); rest = model[i]
        rest -= L - pos
        if desen: cur.append(b)
        else: cur = [b]
    if desen and len(cur) > 1: out.append(cur)
    return out


def reda(dc, op, z):
    import win32ui
    dc.SetBkMode(1)
    nul = win32ui.CreatePen(5, 0, 0)
    k = max(1.0, z / 50.0)                                          # ecranul desenează la ~50 px/inch: liniuțele cresc proporțional
    for o in op:
        if o[0] == "poligon":
            _, pts, fill = o
            if not fill or len(pts) < 3: continue
            br = win32ui.CreateBrush(0, _rgb(fill), 0); vb = dc.SelectObject(br); vp = dc.SelectObject(nul)
            dc.Polygon([(int(x), int(y)) for x, y in pts]); dc.SelectObject(vb); dc.SelectObject(vp)
        elif o[0] == "linie":
            _, pts, fill, width, dash = o
            if not fill or len(pts) < 2: continue
            pen = win32ui.CreatePen(0, max(1, int(round(width))), _rgb(fill)); vp = dc.SelectObject(pen)
            bucati = _liniute(pts, [d * k for d in dash]) if dash else [pts]
            for b in bucati:
                dc.MoveTo((int(b[0][0]), int(b[0][1])))
                for x, y in b[1:]: dc.LineTo((int(x), int(y)))
            dc.SelectObject(vp)
        elif o[0] == "text":
            _text(dc, *o[1:])


def _text(dc, x, y, text, font, fill, justify, angle, width):
    import win32ui
    fn, px, stil = (list(font) + ["", "", ""])[:3]
    px = abs(int(px)) or 10
    f = win32ui.CreateFont({"name": fn, "height": -px, "weight": 700 if "bold" in stil else 400, "italic": 1 if "italic" in stil else 0,
                            "underline": 1 if "underline" in stil else 0, "escapement": int(round(angle * 10)), "orientation": int(round(angle * 10))})
    vf = dc.SelectObject(f); dc.SetTextColor(_rgb(fill))
    lh = dc.GetTextMetrics()["tmHeight"]
    randuri = []
    for r in str(text).split("\n"):                                # rânduri, cu împachetare la lățimea chenarului
        if width and dc.GetTextExtent(r)[0] > width:
            cur = ""
            for w in r.split(" "):
                t = (cur + " " + w).strip()
                if cur and dc.GetTextExtent(t)[0] > width: randuri.append(cur); cur = w
                else: cur = t
            randuri.append(cur)
        else: randuri.append(r)
    lat = max((dc.GetTextExtent(r)[0] for r in randuri), default=0)
    a = math.radians(angle); ca, sa = math.cos(a), math.sin(a)
    for i, r in enumerate(randuri):
        w = dc.GetTextExtent(r)[0]
        lx = {"left": -lat / 2, "right": lat / 2 - w}.get(justify, -w / 2); ly = -len(randuri) * lh / 2 + i * lh
        dc.TextOut(int(x + lx * ca + ly * sa), int(y - lx * sa + ly * ca), r)
    dc.SelectObject(vf)
