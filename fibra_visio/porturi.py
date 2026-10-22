"""Porturile (banda galbenă cu 1…N din CTA / ODF / BTS) și tragerea fibrelor de la un port la altul, în stilul schemelor voastre:
fiecare fibră e o linie separată, cu colțuri drepte; fibra nouă – roșie / întreruptă (după alegerea din program)."""
import math, re
import xml.etree.ElementTree as ET
from vsdx_doc import V, Forma, norm, fnum
from desen import _cell, STIL_CABLU_NOU
import desen

PAS = 0.0787                      # 2 mm între fibre
CULORI_CMD = {"rosu": "#FF0000", "rosie": "#FF0000", "albastru": "#0000FF", "albastra": "#0000FF", "verde": "#00A050",
              "negru": "#000000", "neagra": "#000000", "portocaliu": "#FF8C00", "galben": "#FFC000", "violet": "#8000C0", "maro": "#8B4513"}


def _rgb(v):
    if v and v.startswith("#") and len(v) == 7: return tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))
    return None


class Nod:
    def __init__(self, nume, eticheta, banda, numere, n):
        self.nume, self.eticheta, self.banda, self.numere, self.n = nume, eticheta, banda, numere, n

    def __repr__(self): return f"{self.nume} ({self.n} porturi)"


def benzi(S):
    """benzile de porturi: dreptunghiuri subțiri, umplute cu galben"""
    out = []
    for f in S.p.forme():
        if f.e1d or f.text_tot(): continue
        c = _rgb(f.cell("FillForegnd"))
        if f.cell("FillPattern", "1") == "0" or c is None or not (c[0] > 200 and c[1] > 190 and c[2] < 210): continue
        x0, y0, x1, y1 = f.cutie(); w, h = x1 - x0, y1 - y0
        if max(w, h) > 3.5 * max(min(w, h), 0.01) and max(w, h) > 0.3: out.append(f)
    return out


def noduri(S):
    """CTA / ODF / BTS cu bandă de porturi, cu numele luat din eticheta cea mai apropiată"""
    forme = S.p.forme(); txt = [(f, f.text_tot()) for f in forme if not f.e1d and f.text_tot()]
    out = []
    for b in benzi(S):
        x0, y0, x1, y1 = b.cutie(); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        numere, n = None, 0
        for f, t in txt:                                       # textul cu 1…N peste bandă
            lin = [l.strip() for l in t.split("\n") if l.strip()]
            if len(lin) >= 2 and all(l.isdigit() for l in lin):
                a = f.cutie()
                if a[0] <= x1 and a[2] >= x0 and a[1] <= y1 and a[3] >= y0: numere, n = f, max(int(l) for l in lin)
        if not n: n = max(1, round(max(x1 - x0, y1 - y0) / 0.082))
        best, bd = None, 2.0                                   # eticheta: cel mai apropiat titlu (font mare, nerotit), nu număr / FO-…
        for f, t in txt:
            l0 = t.split("\n")[0].strip()
            if not l0 or l0.isdigit() or re.match(r"(?i)^(FO|CLO)[-\s]", l0) or len(l0) > 40: continue
            if fnum(f.sectiune("Character", "Size"), 0.11) < 0.1 or abs(math.sin(f.num("Angle", 0))) > 0.5: continue
            a = f.cutie(); d = math.hypot((a[0] + a[2]) / 2 - cx, (a[1] + a[3]) / 2 - cy)
            if d < bd: best, bd = f, d
        nume = best.text_tot().split("\n")[0].strip() if best else f"Bandă {len(out) + 1}"
        out.append(Nod(nume, best, b, numere, n))
    return out


def gaseste_nod(S, nume):
    ns = noduri(S); q = norm(nume)
    for nd in ns:
        if norm(nd.nume) == q: return nd
    pot = [nd for nd in ns if q and q in norm(nd.nume)]
    if len(pot) == 1: return pot[0]
    if len(pot) > 1: raise ValueError(f"„{nume}” se potrivește la mai multe: " + ", ".join(p.nume for p in pot))
    raise ValueError(f"nu găsesc „{nume}” cu bandă de porturi. Am: " + ", ".join(nd.nume for nd in ns))


def cutie_nod(S, nume):
    """dreptunghiul (manșon, CTA, bloc…) al unui nume: cel mai mic chenar fără text care conține eticheta sau stă chiar sub / peste ea"""
    q = norm(nume); forme = S.p.forme(); et = None
    for f in forme:
        t = f.text_tot()
        if not f.e1d and t and (norm(t.split("\n")[0]) == q or norm(t) == q): et = f; break
    if et is None:
        pot = [f for f in forme if not f.e1d and f.text_tot() and q and q in norm(f.text_tot())]
        if len(pot) == 1: et = pot[0]
        elif len(pot) > 1: raise ValueError(f"„{nume}” se potrivește la mai multe: " + ", ".join(p.text_tot().split(chr(10))[0] for p in pot))
    if et is None: raise ValueError(f"nu găsesc „{nume}” pe pagină")
    a = et.cutie(); cx, cy = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2; best, ba = None, 1e9
    for f in forme:
        if f.e1d or f.text_tot() or f.id == et.id: continue
        x0, y0, x1, y1 = f.cutie(); w, h = x1 - x0, y1 - y0
        if w < 0.2 or h < 0.2: continue
        inauntru = x0 <= cx <= x1 and y0 <= cy <= y1
        langa = x0 - 0.1 <= cx <= x1 + 0.1 and (0 <= a[1] - y1 < 0.4 or 0 <= y0 - a[3] < 0.4)
        if (inauntru or langa) and w * h < ba: best, ba = f, w * h
    if best is None: raise ValueError(f"nu găsesc chenarul lui „{nume}”")
    return best.cutie()


def punct_sudura(S, x, y, r=0.0217):
    sh = S.p.shapes_el()
    el = ET.SubElement(sh, V + "Shape", {"ID": str(S.p.id_nou()), "Type": "Shape", "LineStyle": "0", "FillStyle": "0", "TextStyle": "0"})
    for n, v in (("PinX", x), ("PinY", y), ("Width", 2 * r), ("Height", 2 * r), ("LocPinX", r), ("LocPinY", r), ("Angle", 0.0)): _cell(el, n, float(v))
    _cell(el, "FillForegnd", "#FF0000"); _cell(el, "FillPattern", "1"); _cell(el, "LineColor", "#000000"); _cell(el, "LineWeight", "0.00694444")
    desen._geom(el, [("Ellipse", {"X": r, "Y": r, "A": 2 * r, "B": r, "C": r, "D": 2 * r})])


def porturi_xy(S, nd):
    """pozițiile porturilor 1…N pe bandă (din fibrele existente care pleacă din bandă, sau la 2 mm)"""
    x0, y0, x1, y1 = nd.banda.cutie(); vert = (y1 - y0) > (x1 - x0); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    cap = set()
    for f in S.p.forme():
        if not f.e1d: continue
        for px, py in ((f.num("BeginX"), f.num("BeginY")), (f.num("EndX"), f.num("EndY"))):
            if vert and y0 - 0.02 <= py <= y1 + 0.02 and min(abs(px - x0), abs(px - x1)) < 0.12: cap.add(round(py, 2))
            if not vert and x0 - 0.02 <= px <= x1 + 0.02 and min(abs(py - y0), abs(py - y1)) < 0.12: cap.add(round(px, 2))
    cap = sorted(cap, reverse=vert)                             # vertical: 1 sus; orizontal: 1 în stânga
    if len(cap) == nd.n: poz = cap
    else:
        s = min(PAS, (max(y1 - y0, x1 - x0)) / max(nd.n, 1))
        poz = [(cy + ((nd.n + 1) / 2 - k) * s) if vert else (cx - ((nd.n + 1) / 2 - k) * s) for k in range(1, nd.n + 1)]
    return vert, (x0, y0, x1, y1), poz


def _linie(S, a, b, culoare, intrerupt, gros=0.01666667):
    (ax, ay), (bx, by) = a, b
    sh = S.p.shapes_el(); nid = S.p.id_nou(); L = math.hypot(bx - ax, by - ay) or 0.001
    el = ET.SubElement(sh, V + "Shape", {"ID": str(nid), "Type": "Shape", "LineStyle": "0", "FillStyle": "0", "TextStyle": "0"})
    for n, v, f in (("PinX", (ax + bx) / 2, "(BeginX+EndX)/2"), ("PinY", (ay + by) / 2, "(BeginY+EndY)/2"),
                    ("Width", L, "SQRT((EndX-BeginX)^2+(EndY-BeginY)^2)"), ("Height", 0.0, None), ("LocPinX", L / 2, "Width*0.5"),
                    ("LocPinY", 0.0, "Height*0.5"), ("Angle", math.atan2(by - ay, bx - ax), "ATAN2(EndY-BeginY,EndX-BeginX)"),
                    ("BeginX", ax, None), ("BeginY", ay, None), ("EndX", bx, None), ("EndY", by, None)):
        _cell(el, n, float(v), f)
    _cell(el, "ObjType", "2"); _cell(el, "LineWeight", "%.8g" % gros); _cell(el, "LineColor", culoare or "#000000")
    _cell(el, "LinePattern", "9" if intrerupt else "1")
    desen._geom(el, [("MoveTo", {"X": 0, "Y": 0}), ("LineTo", {"X": L, "Y": 0})], nofill=True)
    return el


def trage(S, A, pa, B, pb, culoare=None, intrerupt=None, decalaj=0, sudura=None):
    """o fibră de la portul pa al lui A la portul pb al lui B, cu colțuri drepte; întoarce numărul de segmente"""
    if not 1 <= pa <= A.n: raise ValueError(f"{A.nume} are porturile 1–{A.n}, nu {pa}")
    if not 1 <= pb <= B.n: raise ValueError(f"{B.nume} are porturile 1–{B.n}, nu {pb}")
    va, ba, poza = porturi_xy(S, A); vb, bb, pozb = porturi_xy(S, B)
    ca = ((ba[0] + ba[2]) / 2, (ba[1] + ba[3]) / 2); cb = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)

    def iesire(vert, box, poz, k, spre):
        if vert:                                               # banda verticală: fibra iese la dreapta / stânga
            x = box[2] if spre[0] >= (box[0] + box[2]) / 2 else box[0]
            return (x, poz[k - 1]), "h"
        y = box[3] if spre[1] >= (box[1] + box[3]) / 2 else box[1]
        return (poz[k - 1], y), "v"
    a, da = iesire(va, ba, poza, pa, cb); b, db = iesire(vb, bb, pozb, pb, ca)
    st = dict(STIL_CABLU_NOU)
    if culoare: st["culoare"] = culoare
    if intrerupt is not None: st["intrerupt"] = intrerupt
    col = st.get("culoare") or "#000000"; dash = bool(st.get("intrerupt"))
    pct = [a]; cut = cutie_nod(S, sudura) if sudura else None; dot = None
    if da == "h" and db == "h":
        xm = ((cut[0] + cut[2]) / 2 if cut else (a[0] + b[0]) / 2) + decalaj
        if abs(a[1] - b[1]) > 0.005: pct += [(xm, a[1]), (xm, b[1])]
        dot = (xm, a[1])
    elif da == "v" and db == "v":
        ym = ((cut[1] + cut[3]) / 2 if cut else (a[1] + b[1]) / 2) + decalaj
        if abs(a[0] - b[0]) > 0.005: pct += [(a[0], ym), (b[0], ym)]
        dot = (a[0], ym)
    elif da == "h": pct.append((b[0], a[1])); dot = pct[-1]
    else: pct.append((a[0], b[1])); dot = pct[-1]
    pct.append(b)
    n = 0
    for p, q in zip(pct, pct[1:]):
        if math.hypot(q[0] - p[0], q[1] - p[1]) > 0.001: _linie(S, p, q, col, dash); n += 1
    if sudura and dot: punct_sudura(S, *dot)                  # punctul roșu de sudură, în manșon
    return n


def interval(s):
    m = re.fullmatch(r"\s*(\d+)\s*(?:-|–|\.\.|pana la)\s*(\d+)\s*", s)
    if m: a, b = int(m.group(1)), int(m.group(2)); return list(range(a, b + 1)) if a <= b else list(range(a, b - 1, -1))
    return [int(x) for x in re.findall(r"\d+", s)]


# ---------- înțelegerea liberă a comenzii (ordinea cuvintelor, spații lipsă, nume incomplete, greșeli de tastare) ----------
GENERICE = {"CTA", "FL", "ODF", "CLO", "BTS", "OLT", "RRU", "BBU", "NOU", "NOUA", "STATIA", "STATIE"}
CUVINTE_SUDURA = re.compile(r"sudur|sudat|sudez|sudeaz|prin|manson|mufa|in m\d")


def _compact(t):
    """literele și cifrele, fără spații/liniuțe; harta pozițiilor către textul original"""
    out, harta = [], []
    for i, ch in enumerate(t):
        if ch.isalnum(): out.append(ch.upper()); harta.append(i)
    return "".join(out), harta


def _gaseste_aprox(cheie, tc, ocupat, limite=None):
    """(start, sfârșit, scor) în textul compact: exact, început de cuvânt (incomplet) sau cu o greșeală de tastare.
    limite: pozițiile unde începe / se termină un cuvânt (potrivirile aproximative trebuie să se oprească la capăt de cuvânt)"""
    import difflib
    L = len(cheie); rez = []
    ok = lambda st, en: limite is None or ((en in limite or en == len(tc)) and (st in limite or st == 0))
    for m in re.finditer(re.escape(cheie), tc):
        if not any(o[0] < m.end() and m.start() < o[1] for o in ocupat): rez.append((m.start(), m.end(), 1.0))
    if rez or L < 3: return rez
    for k in range(L - 1, max(3, (L + 1) // 2) - 1, -1):                        # incomplet: „popov”, „raut”
        for m in re.finditer(re.escape(cheie[:k]), tc):
            if not any(o[0] < m.end() and m.start() < o[1] for o in ocupat) and ok(m.start(), m.end()):
                rez.append((m.start(), m.end(), 0.6 + 0.3 * k / L))
        if rez: return rez
    if L >= 5:                                                                    # o literă greșită / lipsă / în plus
        for w in (L - 1, L, L + 1):
            for st in range(0, max(0, len(tc) - w) + 1):
                if any(o[0] < st + w and st < o[1] for o in ocupat) or not ok(st, st + w): continue
                r = difflib.SequenceMatcher(None, cheie, tc[st:st + w]).ratio()
                if r >= 0.8: rez.append((st, st + w, r * 0.9))
        rez.sort(key=lambda x: -x[2])
        return rez[:1]
    return rez


def _candidati(S):
    """numele de pe pagină: noduri cu porturi + manșoane / chenare cu titlu"""
    ns = noduri(S); out = [(n.nume, n) for n in ns]; vazut = {norm(n.nume) for n in ns}
    for f in S.p.forme():
        t = f.text_tot()
        if f.e1d or not t: continue
        l0 = t.split("\n")[0].strip()
        if not l0 or re.fullmatch(r"[\d,.\s]+", l0) or len(l0) > 30 or re.match(r"(?i)^(FO|CLO)[-\s]", l0): continue
        if fnum(f.sectiune("Character", "Size"), 0.11) < 0.1: continue
        if norm(l0) not in vazut: vazut.add(norm(l0)); out.append((l0, None))
    return out


def mentiuni(S, t):
    """numele pomenite în comandă, în ordinea în care apar: [(start, sfârșit, nume, Nod|None)]"""
    tc, harta = _compact(t); cand = _candidati(S); gasite = []; ocupat = []
    limite = {k for k in range(1, len(tc)) if harta[k] - harta[k - 1] > 1 or tc[k].isdigit() != tc[k - 1].isdigit()}
    chei = []
    for nume, nod in cand:
        tok = [x for x in re.split(r"[\s_\-./]+", nume) if x]
        chei.append((norm(nume).upper(), nume, nod, 3))
        for x in tok:
            X = norm(x).upper()
            if X in GENERICE or len(X) < 3 or X.isdigit(): continue
            chei.append((X, nume, nod, 2))
        for x in tok:
            if norm(x).upper() in GENERICE: chei.append((norm(x).upper(), nume, nod, 1))
    chei.sort(key=lambda c: (-c[3], -len(c[0])))
    for trecere in (0, 1):                                    # întâi potrivirile exacte, apoi cele aproximative
        for cheie, nume, nod, forta in chei:
            if not cheie or (trecere == 1 and forta < 2): continue
            if trecere == 0:
                gas = [(m.start(), m.end(), 1.0) for m in re.finditer(re.escape(cheie), tc)
                       if not any(o[0] < m.end() and m.start() < o[1] for o in ocupat)]
            else:
                gas = [g for g in _gaseste_aprox(cheie, tc, ocupat, limite) if g[2] < 1.0]
            for st, en, sc in gas:
                if len(cheie) <= 2 and en < len(tc) and tc[en].isdigit(): continue
                if en < len(tc) and tc[en].isalpha() and sc == 1.0 and forta >= 2 and len(cheie) < 6: continue   # „RAUTEL” din „RAUTELSAT”
                gasite.append([st, en, nume, nod, forta, sc])
                if forta >= 2: ocupat.append((st, en))
    # numele generice („CTA”): dacă se potrivesc la mai multe, alege-l pe cel nepomenit altfel
    tari = {g[2] for g in gasite if g[4] >= 2}; rez = []
    grup = {}
    for g in gasite:
        if g[4] == 1: grup.setdefault((g[0], g[1]), []).append(g)
        else: rez.append(g)
    for (st, en), gs in grup.items():
        if any(r[0] <= st < r[1] or st <= r[0] < en for r in rez): continue
        ramase = [g for g in gs if g[2] not in tari]
        if len(ramase) == 1: rez.append(ramase[0])
        elif len(gs) == 1: rez.append(gs[0])
        else: raise ValueError("„" + t[harta[st]:harta[en - 1] + 1] + "” poate fi: " + ", ".join(g[2] for g in (ramase or gs)) + ". Scrie numele întreg.")
    rez.sort(key=lambda g: g[0])
    unic = []
    for g in rez:
        if unic and unic[-1][2] == g[2] and g[0] - unic[-1][1] <= 1: unic[-1][1] = g[1]; continue
        unic.append(g)
    return [(harta[g[0]], harta[g[1] - 1] + 1, g[2], g[3]) for g in unic]


def numere_in(seg):
    seg = re.sub(r"(?<=\d)\s*(?:-|–|\.\.|pana la)\s*(?=\d)", "-", seg)
    out = []
    for m in re.finditer(r"(\d+)-(\d+)|(\d+)", seg):
        out += interval(m.group(0))
    return out


def comanda(S, t):
    """t: comanda fără diacritice, litere mici. -> mesaj sau None dacă nu e o comandă de fibră între porturi"""
    if re.fullmatch(r"(porturi|benzi|lista porturi|noduri)", t.strip()):
        ns = noduri(S)
        return ("Benzi de porturi pe pagină: " + ", ".join(f"{n.nume} ({n.n})" for n in ns)) if ns else "Nu găsesc benzi de porturi (galbene) pe pagină."
    if not re.search(r"\d", t) or not noduri(S): return None
    if re.match(r"\s*(sterge|muta|redenumeste|schimba|anuleaza|lista|pagina)\b", t): return None
    men = mentiuni(S, t)
    capete = [m for m in men if m[3] is not None]
    if len(capete) < 2: return None
    (a0, a1, an, A), (b0, b1, bn, B) = capete[0], capete[1]
    # porturile: „A port 5 la B port 3” (numerele după nume) sau „portul 5 din A la portul 3 din B” (înainte)
    urm = lambda x: ([m[0] for m in men if m[0] > x] + [len(t)])[0]
    inainte_a = numere_in(t[:a0])
    if inainte_a:
        la, lb = inainte_a, numere_in(t[a1:b0])
    else:
        la, lb = numere_in(t[a1:urm(a1)]), numere_in(t[b1:urm(b1)])
    if not la or not lb:
        raise ValueError(f"spune și porturile, de ex.: „{A.nume} port 1 la {B.nume} port 2”")
    if len(la) != len(lb):
        if len(la) == 1 and len(lb) > 1: la = list(range(la[0], la[0] + len(lb)))
        elif len(lb) == 1 and len(la) > 1: lb = list(range(lb[0], lb[0] + len(la)))
        else: raise ValueError(f"număr diferit de porturi: {len(la)} la {A.nume} și {len(lb)} la {B.nume}")
    sud = None
    for m in men:
        if m[3] is None and (CUVINTE_SUDURA.search(t) or True): sud = m[2]; break
    col = next((CULORI_CMD[w] for w in re.findall(r"[a-z]+", t) if w in CULORI_CMD), None)
    intr = True if re.search(r"intrerup|punctat|linie noua", t) else (False if re.search(r"continu", t) else None)
    seg = 0
    for i, (pa, pb) in enumerate(zip(la, lb)):
        seg += trage(S, A, pa, B, pb, col, intr, decalaj=(i - (len(la) - 1) / 2) * PAS if not sud else 0, sudura=sud)
    pp = lambda l: (f"portul {l[0]}" if len(l) == 1 else f"porturile {l[0]}–{l[-1]}")
    return (f"Am tras {len(la)} {'fibră' if len(la) == 1 else 'fibre'}: {A.nume} {pp(la)} → {B.nume} {pp(lb)}"
            + (f", cu sudură în {sud}." if sud else "."))


def analiza(S, nume_fisier=""):
    """ce e pe pagină, spus pe scurt – la deschidere, ca omul să știe ce nume poate folosi în chat"""
    from collections import Counter
    ns = noduri(S); nume_noduri = {norm(n.nume) for n in ns}; lin = []
    mans = []
    for nume, nod in _candidati(S):
        if nod is not None or norm(nume) in nume_noduri: continue
        try: cutie_nod(S, nume); mans.append(nume)
        except Exception: pass
    cab = Counter()
    for f in S.p.forme():
        t = f.text_tot()
        if t and re.match(r"(?i)^FO[-\s]?\d+", t.strip()): cab[" ".join(t.split())] += 1
    linii = [f for f in S.p.forme() if f.e1d]
    col = Counter(); intr = 0
    for f in linii:
        c = (f.cell("LineColor") or "").upper()
        if c in ("#FF0000", "2"): col["roșii"] += 1
        elif c in ("#0000FF", "4"): col["albastre"] += 1
        if (f.cell("LinePattern", "1") or "1") not in ("0", "1"): intr += 1
    L = [f"Am analizat „{nume_fisier or 'schema'}”, pagina „{S.p.nume}”:"]
    if ns: L.append("• Noduri cu porturi: " + ", ".join(f"{n.nume} ({n.n} porturi)" for n in ns))
    if mans: L.append("• Manșoane / chenare: " + ", ".join(mans))
    if cab: L.append("• Cabluri: " + ", ".join(f"{k}" + (f" ×{v}" if v > 1 else "") for k, v in cab.most_common()))
    if linii:
        L.append(f"• Linii / fibre: {len(linii)}" + (" (" + ", ".join(f"{v} {k}" for k, v in col.items()) + ")" if col else "")
                 + (f", {intr} întrerupte" if intr else ""))
    if not ns and not mans: L.append("• Nu am găsit noduri cu bandă de porturi; merg comenzile simple (scrie „ajutor”).")
    if len(ns) >= 2:
        a, b = ns[0], ns[1]; m = mans[0].split()[0] if mans else None
        L.append(f"Gata de lucru. Exemple: „{a.nume} port 1 la {b.nume} port 2”"
                 + (f", „{a.nume} 3-4 la {b.nume} 3-4 prin {m}”" if m else "") + ", „anuleaza”, „salveaza”.")
    else:
        L.append("Gata de lucru. Scrie „ajutor” pentru exemple.")
    return "\n".join(L)
