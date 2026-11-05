# Semnătura din numele scris: numele devine o semnătură „de mână” (font de scris de mână, înclinat, cu linie ondulată dedesubt).
import os, sys, math
from PIL import Image, ImageDraw, ImageFont

# fonturile incluse în program (folderul „fonturi” de lângă cod / din exe), apoi cele de scris de mână din Windows
INCLUSE = [("Great Vibes", "GreatVibes-Regular.ttf"), ("Alex Brush", "AlexBrush-Regular.ttf"), ("Allura", "Allura-Regular.ttf"),
           ("Marck Script", "MarckScript-Regular.ttf"), ("Caveat", "Caveat-Regular.ttf"), ("Dancing Script", "DancingScript-Regular.ttf")]
WINDOWS = [("Segoe Script", "segoesc.ttf"), ("Lucida Handwriting", "LHANDW.TTF"), ("Monotype Corsiva", "MTCORSVA.TTF"),
           ("Brush Script", "BRUSHSCI.TTF"), ("Freestyle Script", "FREESCPT.TTF"), ("Vladimir Script", "VLADIMIR.TTF"),
           ("Edwardian Script", "ITCEDSCR.TTF"), ("Kunstler Script", "KUNSTLER.TTF"), ("Gabriola", "Gabriola.ttf")]


def _dir_cod():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def fonturi():
    """[(nume, cale)] – fonturile de scris de mână găsite pe calculator"""
    out = []
    d = os.path.join(_dir_cod(), "fonturi")
    for nume, f in INCLUSE:
        p = os.path.join(d, f)
        if os.path.exists(p): out.append((nume, p))
    wf = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    for nume, f in WINDOWS:
        for p in (os.path.join(wf, f), os.path.join(wf, f.lower())):
            if os.path.exists(p): out.append((nume, p)); break
    if not out:                                            # nimic de scris de mână: măcar un font înclinat
        for p in (os.path.join(wf, "ariali.ttf"), "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"):
            if os.path.exists(p): out.append(("Înclinat", p)); break
    return out


def are_literele(font, text):
    """fontul are toate literele numelui? (o literă lipsă iese goală)"""
    try:
        f = ImageFont.truetype(font, 40)
        for ch in set(text):
            if ch.strip() and ch not in "-.'" and f.getmask(ch).getbbox() is None: return False
        return True
    except Exception:
        return False


def _rgb(c):
    c = c.lstrip("#"); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _bezier(p0, p1, p2, p3, n=60):
    out = []
    for k in range(n + 1):
        t = k / n; a, b, c, d = (1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def deseneaza(nume, font, culoare="#1f3fa0", marime=150, inclinare=8, linie=True, grosime=1.0):
    """-> imagine RGBA transparentă, tăiată pe semnătură"""
    nume = " ".join(nume.split())
    if not nume: raise ValueError("scrie numele")
    f = ImageFont.truetype(font, marime)
    try: x0, y0, x1, y1 = f.getbbox(nume)
    except AttributeError:
        w_, h_ = f.getsize(nume); x0, y0, x1, y1 = 0, 0, w_, h_
    W, H = int((x1 - x0) * 1.25 + marime), int((y1 - y0) * 2.2 + marime)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); col = _rgb(culoare) + (255,)
    ox, oy = marime // 2 - x0, int(marime * 0.35) - y0
    st = max(0, int(round((grosime - 1) * marime / 60)))   # grosimea „cernelii”
    d.text((ox, oy), nume, font=f, fill=col, stroke_width=st, stroke_fill=col)
    if linie:                                              # linia ondulată de sub nume, ca la o semnătură
        jos = oy + y1 + marime * 0.12; a = ox + x0 + (x1 - x0) * 0.05; b = ox + x1 + marime * 0.25
        pts = _bezier((a, jos + marime * 0.10), (a + (b - a) * 0.30, jos - marime * 0.30), (a + (b - a) * 0.70, jos + marime * 0.35), (b, jos - marime * 0.15), 120)
        for i, (p, q) in enumerate(zip(pts, pts[1:])):
            g = max(1, int(marime / 22 * grosime * (0.25 + math.sin(math.pi * i / len(pts)))))   # mai groasă la mijloc, subțire la capete
            d.line([p, q], fill=col, width=g)
            d.ellipse([q[0] - g / 2, q[1] - g / 2, q[0] + g / 2, q[1] + g / 2], fill=col)
    if inclinare:                                          # puțin înclinată în sus, ca scrisul de mână
        im = im.rotate(inclinare * 0.35, resample=Image.BICUBIC, expand=True)
    b = im.getbbox()
    if b: im = im.crop((max(0, b[0] - 6), max(0, b[1] - 6), min(im.width, b[2] + 6), min(im.height, b[3] + 6)))
    return im
