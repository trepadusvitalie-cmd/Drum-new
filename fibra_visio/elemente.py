"""Elemente noi desenate în stilul schemelor de fibră: ODF / cutie cu bandă de porturi, manșon, clădire.
Locul îl caută singur pe pagină (fără să acopere nimic); dacă nu încape, propune o pagină nouă."""
import math
import xml.etree.ElementTree as ET
from vsdx_doc import V
from desen import _cell, _geom, _text, STIL_CABLU_NOU

PAS = 0.0787          # 2 mm între porturi / fibre
MARGINE = 0.35        # cât lăsăm liber față de marginea foii și de alte desene
K = 1.0               # scara: pe schemele mici (porturi mai dese) desenez totul mai mic, ca să arate la fel


def potriveste_scara(S):
    """scara după benzile de porturi existente: pasul lor față de 2 mm (0.4 … 1.5)"""
    global K
    try:
        import porturi
        pasi = []
        for nd in porturi.noduri(S):
            b = nd.banda.cutie(); L = max(b[2] - b[0], b[3] - b[1])
            if nd.n: pasi.append(L / nd.n)
        if pasi:
            pasi.sort(); K = max(0.4, min(1.5, pasi[len(pasi) // 2] / PAS)); return K
    except Exception: pass
    K = 1.0; return K


def _forma(S, x, y, w, h, angle=0.0):
    sh = S.p.shapes_el()
    el = ET.SubElement(sh, V + "Shape", {"ID": str(S.p.id_nou()), "Type": "Shape", "LineStyle": "0", "FillStyle": "0", "TextStyle": "0"})
    for n, v in (("PinX", x), ("PinY", y), ("Width", w), ("Height", h), ("LocPinX", w / 2), ("LocPinY", h / 2), ("Angle", angle)):
        _cell(el, n, float(v))
    return el


def _dreptunghi(el):
    _geom(el, [("RelMoveTo", {"X": 0, "Y": 0}), ("RelLineTo", {"X": 1, "Y": 0}), ("RelLineTo", {"X": 1, "Y": 1}),
               ("RelLineTo", {"X": 0, "Y": 1}), ("RelLineTo", {"X": 0, "Y": 0})])


def _font(el, pt, bold=True, culoare="#000000"):
    ch = ET.SubElement(el, V + "Section", {"N": "Character"}); r = ET.SubElement(ch, V + "Row", {"IX": "0"})
    for n, v in (("Font", "Arial"), ("Size", "%.10g" % (pt / 72)), ("Style", "1" if bold else "0"), ("Color", culoare)):
        ET.SubElement(r, V + "Cell", {"N": n, "V": v})


def text(S, x, y, s, pt=10, bold=True, w=1.4, culoare="#000000", angle=0.0):
    el = _forma(S, x, y, w, pt / 72 * 1.6 * max(1, s.count("\n") + 1), angle)
    _cell(el, "LinePattern", "0"); _cell(el, "FillPattern", "0"); _font(el, pt, bold, culoare); _dreptunghi(el); _text(el, s)
    return el


def chenar(S, x0, y0, x1, y1, intrerupt=False, rotunjit=0.0, gros=0.01666667, culoare="#000000"):
    el = _forma(S, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0)
    _cell(el, "LinePattern", "2" if intrerupt else "1"); _cell(el, "FillPattern", "0"); _cell(el, "LineWeight", "%.8g" % gros)
    _cell(el, "LineColor", culoare)
    if rotunjit: _cell(el, "Rounding", "%.6g" % rotunjit)
    _dreptunghi(el)
    return el


# ---------------------------------------------------------------- mărimi
def marime_odf(n, orient="v"):
    L = n * PAS
    return ((0.65 * K, (L + 0.35) * K) if orient == "v" else ((L + 0.45) * K, 0.6 * K))


def marime_manson():
    import simboluri
    sim = simboluri.simbol("manson")
    return (sim["w"], sim["h"]) if sim else (1.1 * K, 0.75 * K)


def marime_cladire(cutii, orient="h"):
    """cutiile stau una lângă alta, pe un rând (așa fibrele vin la fiecare fără să treacă prin alta)"""
    if not cutii: return 2.2 * K, 1.4 * K
    ms = [marime_odf(n, orient) for n in cutii]
    return sum(w + 0.45 * K for w, h in ms) + 0.25 * K, max(h for w, h in ms) + 1.0 * K


# ---------------------------------------------------------------- desen
def odf(S, nume, n, cx, cy, orient="v", nou=True):
    """chenar + nume deasupra + banda galbenă cu porturile 1…n (aceeași construcție ca în schemele voastre)"""
    import simboluri
    sim = simboluri.simbol(f"odf{n}{orient}")
    if sim: return simboluri.deseneaza(S, sim, cx, cy, nume)          # ODF învățat cu același număr de porturi
    w, h = marime_odf(n, orient)
    stil = STIL_CABLU_NOU if nou else {}
    chenar(S, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, intrerupt=bool(nou and stil.get("intrerupt")))
    text(S, cx, cy + h / 2 + 0.13 * K, nume, pt=10 * K, w=max(1.3, len(nume) * 0.1) * K)
    L = n * PAS * K
    if orient == "v":
        b = _forma(S, cx, cy - 0.05 * K, 0.13 * K, L)
    else:
        b = _forma(S, cx, cy - 0.08 * K, L, 0.13 * K)
    _cell(b, "FillForegnd", "#FFFF99"); _cell(b, "FillPattern", "1"); _cell(b, "LineWeight", "0.01")
    _cell(b, "LineColor", (stil.get("culoare") or "#000000") if nou else "#000000")
    if nou and stil.get("culoare"): _cell(b, "LinePattern", "23")
    _dreptunghi(b)
    num = "\n".join(str(k) for k in range(1, n + 1))
    if orient == "v":
        t = _forma(S, cx, cy - 0.05 * K, 0.28 * K, L)
    else:
        t = _forma(S, cx, cy - 0.08 * K, 0.28 * K, L, angle=math.pi / 2)
    _cell(t, "LinePattern", "0"); _cell(t, "FillPattern", "0"); _cell(t, "LeftMargin", "0"); _cell(t, "RightMargin", "0")
    _cell(t, "TopMargin", "0"); _cell(t, "BottomMargin", "0"); _font(t, 72 * PAS * K / 1.2, True); _dreptunghi(t); _text(t, num)
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2 + 0.25 * K)


def manson(S, nume, cx, cy, nou=True):
    import simboluri
    sim = simboluri.simbol("manson")
    if sim: return simboluri.deseneaza(S, sim, cx, cy, nume)          # simbolul învățat de la utilizator
    w, h = marime_manson()
    chenar(S, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, intrerupt=bool(nou and STIL_CABLU_NOU.get("intrerupt")), rotunjit=0.118 * K)
    text(S, cx, cy + h / 2 + 0.13 * K, nume, pt=10 * K, w=max(1.2, len(nume) * 0.1) * K)
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2 + 0.25 * K)


def cladire(S, nume, x0, y0, x1, y1, nou=True):
    import simboluri
    sim = simboluri.simbol("cladire")
    if sim:                                                           # chenarul învățat, întins pe mărimea nouă: doar dacă e un singur chenar
        pass
    chenar(S, x0, y0, x1, y1, intrerupt=True, gros=0.02083333)
    text(S, (x0 + x1) / 2, y1 - 0.18 * K, nume, pt=11 * K, w=x1 - x0 - 0.2 * K)
    return (x0, y0, x1, y1)


# ---------------------------------------------------------------- loc liber pe foaie
def ocupate(S):
    W, H = S.p.dimensiune(); out = []
    for f in S.p.forme():
        try: b = f.cutie()
        except Exception: continue
        if (b[2] - b[0]) * (b[3] - b[1]) > 0.5 * W * H: continue          # ramele mari ale foii nu contează
        out.append(b)
    return out


def _libere(S, w, h, occ=None, pas=0.1):
    """toate centrele (x, y) unde încape un dreptunghi w×h fără să atingă nimic (rând cu rând, rapid)"""
    W, H = S.p.dimensiune(); occ = ocupate(S) if occ is None else occ; m = MARGINE; out = []
    y = h / 2 + m
    while y <= H - h / 2 - m:
        ya, yb = y - h / 2 - m, y + h / 2 + m
        rand = sorted((b[0], b[2]) for b in occ if ya < b[3] and yb > b[1])
        x = w / 2 + m
        while x <= W - w / 2 - m:
            xa, xb = x - w / 2 - m, x + w / 2 + m
            sar = None
            for a0, a1 in rand:
                if a0 >= xb: break
                if a1 > xa: sar = a1 if sar is None else max(sar, a1)
            if sar is None: out.append((x, y)); x += pas
            else: x = max(x + pas, sar + m + w / 2)
        y += pas
    return out


def loc_liber(S, w, h, langa=None):
    """centrul unui dreptunghi w×h liber pe pagină (cât mai aproape de „langa”), sau None dacă nu încape"""
    W, H = S.p.dimensiune(); tx, ty = langa if langa else (W / 2, H / 2)
    lib = _libere(S, w, h)
    return min(lib, key=lambda p: math.hypot(p[0] - tx, p[1] - ty)) if lib else None


ZONE = [("sus-stânga", 0.2, 0.8), ("sus-dreapta", 0.8, 0.8), ("jos-stânga", 0.2, 0.2), ("jos-dreapta", 0.8, 0.2), ("la mijloc", 0.5, 0.5)]


def variante_loc(S, w, h, tinte=(), n=4):
    """câteva așezări diferite pe pagină, de ales: [(cx, cy, descriere)]. tinte: [(x, y, „lângă X”)] puse primele."""
    W, H = S.p.dimensiune(); lib = _libere(S, w, h, pas=0.15)
    if not lib: return []
    out = []
    def adauga(tx, ty, desc):
        p = min(lib, key=lambda q: math.hypot(q[0] - tx, q[1] - ty))
        if all(math.hypot(p[0] - a, p[1] - b) > max(w, h) * 0.9 for a, b, _ in out): out.append((p[0], p[1], desc))
    for tx, ty, desc in tinte: adauga(tx, ty, desc)
    for desc, fx, fy in ZONE:
        if len(out) >= n: break
        adauga(W * fx, H * fy, desc)
    return out[:n]
