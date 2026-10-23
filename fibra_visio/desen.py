"""Operațiile de desen pe o pagină Visio: elemente (manșon, ODF, splitter, stâlp...), cabluri, mutare, ștergere, sudură.
Când pe schemă există deja un element de același fel, cel nou e o copie a lui (același simbol, același stil)."""
import copy, math, re
import xml.etree.ElementTree as ET
from vsdx_doc import V, Forma, norm, fnum, text_forma

# simbolurile standard (dacă pe schemă nu există unul de același fel): formă, lățime, înălțime (inch), culoare
TIPURI = {
    "manson":   ("elipsa", 0.9, 0.5, "#FFF2CC", "Manșon"),
    "odf":      ("drept", 0.7, 1.3, "#DDEBF7", "ODF"),
    "splitter": ("triunghi", 0.6, 0.5, "#E2EFDA", "Splitter"),
    "stalp":    ("cerc", 0.32, 0.32, "#D9D9D9", "Stâlp"),
    "camin":    ("camin", 0.45, 0.45, "#FFFFFF", "Cămin"),
    "bloc":     ("drept", 0.9, 0.6, "#FCE4D6", "Clădire"),
    "cutie":    ("drept", 0.6, 0.45, "#EDEDED", "Cutie"),
}
CUVINTE_TIP = {"manson": "manson", "mansonul": "manson", "mufa": "manson", "mufă": "manson", "closure": "manson",
               "odf": "odf", "splitter": "splitter", "spliter": "splitter", "splitterul": "splitter", "stalp": "stalp",
               "stalpul": "stalp", "stilp": "stalp", "camin": "camin", "caminul": "camin", "camera": "camin",
               "bloc": "bloc", "blocul": "bloc", "cladire": "bloc", "cladirea": "bloc", "casa": "bloc", "abonat": "bloc",
               "client": "bloc", "cutie": "cutie", "cutia": "cutie", "box": "cutie", "fdb": "cutie", "fat": "cutie"}
PREFIX_TIP = [("ODF", "odf"), ("SP", "splitter"), ("SPL", "splitter"), ("M", "manson"), ("MF", "manson"), ("S", "stalp"),
              ("ST", "stalp"), ("C", "camin"), ("CM", "camin"), ("B", "bloc"), ("BL", "bloc"), ("FDB", "cutie"), ("FAT", "cutie")]
# culorile fibrelor / tuburilor (TIA-598): 1 albastru ... 12 aqua
CULORI = [("albastru", "#0070C0"), ("portocaliu", "#FF8C00"), ("verde", "#00A050"), ("maro", "#8B4513"),
          ("gri", "#808080"), ("alb", "#FFFFFF"), ("roșu", "#E00000"), ("negru", "#000000"), ("galben", "#FFE000"),
          ("violet", "#8000C0"), ("roz", "#FF80C0"), ("aqua", "#00E0E0")]
# cablul nou: la voi existentele sunt negre/albastre, cel nou – roșu sau linie întreruptă (se alege în program)
STIL_CABLU_NOU = {"culoare": "#FF0000", "intrerupt": False}
RE_CABLU = re.compile(r"\b\d+\s*(FO|F\.O\.|fibre|fib)\b", re.I)


def prefix(nume):
    m = re.match(r"[A-Za-zĂÂÎȘŞȚŢăâîșşțţ]+", norm(nume))
    return m.group(0) if m else ""


def tip_din_nume(nume):
    p = prefix(nume)
    for pr, t in sorted(PREFIX_TIP, key=lambda x: -len(x[0])):
        if p == pr: return t
    for pr, t in sorted(PREFIX_TIP, key=lambda x: -len(x[0])):
        if p.startswith(pr): return t
    return "cutie"


def _cell(el, n, v, f=None, u=None):
    import vsdx_doc; vsdx_doc.EPOCA[0] += 1                     # forma s-a schimbat: conturul ținut minte nu mai e bun
    c = el.find(V + "Cell[@N='%s']" % n)
    if c is None:
        c = ET.Element(V + "Cell", {"N": n}); idx = 0
        for i, ch in enumerate(list(el)):
            if ch.tag == V + "Cell": idx = i + 1
        el.insert(idx, c)
    c.set("V", ("%.10g" % v) if isinstance(v, float) else str(v))
    if f is not None: c.set("F", f)
    elif "F" in c.attrib and n in ("PinX", "PinY", "BeginX", "BeginY", "EndX", "EndY"): del c.attrib["F"]
    if u: c.set("U", u)
    return c


def _text(el, s):
    t = el.find(V + "Text")
    if t is None: t = ET.SubElement(el, V + "Text")
    for ch in list(t): t.remove(ch)
    t.text = s


def _geom(el, rows, nofill=False):
    g = ET.SubElement(el, V + "Section", {"N": "Geometry", "IX": "0"})
    ET.SubElement(g, V + "Cell", {"N": "NoFill", "V": "1" if nofill else "0"})
    ET.SubElement(g, V + "Cell", {"N": "NoLine", "V": "0"})
    for i, (t, cells) in enumerate(rows, 1):
        r = ET.SubElement(g, V + "Row", {"T": t, "IX": str(i)})
        for n, v in cells.items(): ET.SubElement(r, V + "Cell", {"N": n, "V": "%.10g" % v})
    return g


class Schema:
    """o pagină a documentului, cu operațiile de fibră"""

    def __init__(self, doc, pagina):
        self.doc, self.p = doc, pagina

    # ---------- găsire ----------
    def elemente(self):
        """formele 2D de pe pagină care au nume (text), cu forma de nivel de sus"""
        out = []
        for f in self.p.forme():
            if f.e1d: continue
            t = f.text_tot()
            if t: out.append((t, f))
        return out

    def gaseste(self, nume):
        n = norm(nume)
        if not n: return None
        el = self.elemente()
        for t, f in el:
            if norm(t) == n: return f
        for t, f in el:
            if any(norm(x) == n for x in re.split(r"[\n,;]", t)): return f
        for t, f in el:
            if norm(t).startswith(n) and not norm(t)[len(n):len(n) + 1].isdigit(): return f
        for f in self.p.forme():
            if norm(f.el.get("Name", "")) == n or norm(f.el.get("NameU", "")) == n: return f
        return None

    def model_pentru(self, nume, tip):
        """un element existent de același fel (același prefix: M1 pentru M5...), ca să copiem simbolul"""
        p = prefix(nume); best = None
        for t, f in self.elemente():
            if p and prefix(t) == p and re.fullmatch(r"[A-Z]+\d+[A-Z]?", norm(t)): return f
            if best is None and tip_din_nume(t) == tip and re.fullmatch(r"[A-Z]+\d+[A-Z]?", norm(t)) and prefix(t) == p: best = f
        return best

    def cabluri(self, doar_lipite=False):
        """cablurile (forme 1D): (forma, id început, id sfârșit) – din lipiri (Connects) sau după capete"""
        lip = {}
        for c in self.p.connects().findall(V + "Connect"):
            fc = c.get("FromCell", "")
            if fc.startswith("Begin") or fc.startswith("End"):
                lip.setdefault(c.get("FromSheet"), {})["b" if fc.startswith("Begin") else "e"] = int(c.get("ToSheet"))
        elem = [(f, f.cutie()) for _, f in self.elemente()]

        def langa(x, y):
            best, bd = None, 0.35
            for f, (x0, y0, x1, y1) in elem:
                d = math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))
                if d < bd: best, bd = f.id, d
            return best
        out = []
        for f in self.p.forme():
            if not f.e1d: continue
            l = lip.get(str(f.id), {})
            a = l.get("b") or (None if doar_lipite else langa(f.num("BeginX"), f.num("BeginY")))
            b = l.get("e") or (None if doar_lipite else langa(f.num("EndX"), f.num("EndY")))
            out.append((f, a, b))
        return out

    def cablu_intre(self, A, B):
        for f, a, b in self.cabluri():
            if {a, b} == {A.id, B.id}: return f
        return None

    def forma_id(self, i):
        for f in self.p.forme():
            if f.id == i: return f
        return None

    # ---------- așezare ----------
    def liber(self, x, y, w, h, ignor=()):
        for f in self.p.forme():
            if f.id in ignor: continue
            if f.e1d: continue
            x0, y0, x1, y1 = f.cutie()
            if x - w / 2 - 0.1 < x1 and x + w / 2 + 0.1 > x0 and y - h / 2 - 0.1 < y1 and y + h / 2 + 0.1 > y0: return False
        W, H = self.p.dimensiune()
        return 0.3 + w / 2 < x < W - 0.3 - w / 2 and 0.3 + h / 2 < y < H - 0.3 - h / 2

    def loc_langa(self, ancora, w, h, directie=None, pas=1.6):
        W, H = self.p.dimensiune()
        if ancora is None and not [f for f in self.p.forme() if not f.e1d]: return 1.2 + w / 2, H / 2   # primul element: în stânga
        cx, cy = ancora.centru() if ancora else (W / 2, H / 2)
        dirs = {"dreapta": (1, 0), "stanga": (-1, 0), "sus": (0, 1), "jos": (0, -1)}
        ordine = [dirs[directie]] if directie else [(1, 0), (0, -1), (0, 1), (-1, 0), (1, -1), (1, 1), (-1, -1), (-1, 1)]
        for k in range(1, 8):
            for dx, dy in ordine:
                x, y = cx + dx * pas * k, cy + dy * pas * k * 0.8
                if self.liber(x, y, w, h): return x, y
        for k in range(400):                                        # orice loc liber pe pagină
            x, y = 0.6 + w / 2 + (k % 20) * (W - 1.2 - w) / 19, H - 0.6 - h / 2 - (k // 20) * (H - 1.2 - h) / 19
            if self.liber(x, y, w, h): return x, y
        return cx + pas, cy

    # ---------- elemente ----------
    def adauga_element(self, nume, tip=None, x=None, y=None, ancora=None, directie=None, detalii=""):
        tip = tip or tip_din_nume(nume)
        model = self.model_pentru(nume, tip)
        sh = self.p.shapes_el()
        if model is not None:                                       # copie a simbolului existent
            el = copy.deepcopy(model.el); nid = self.p.id_nou()
            for e in el.iter(V + "Shape"):
                e.set("ID", str(nid)); nid += 1
                for a in ("UniqueID",):
                    if a in e.attrib: del e.attrib[a]
            vechi = model.text_tot()
            for e in el.iter(V + "Shape"):
                t = text_forma(e)
                if t and norm(t) == norm(vechi) or (t and t.strip() == vechi.strip()):
                    _text(e, nume + (("\n" + detalii) if detalii else ""))
            for n in ("Name", "NameU"):
                if n in el.attrib and el.attrib[n] != "": el.set(n, el.attrib[n].split(".")[0] + "." + str(el.get("ID")))
            x0, y0, x1, y1 = model.cutie(); w, h = x1 - x0, y1 - y0
            if x is None: x, y = self.loc_langa(ancora or model, w, h, directie)
            dx, dy = x - (x0 + x1) / 2, y - (y0 + y1) / 2
            _cell(el, "PinX", model.num("PinX") + dx); _cell(el, "PinY", model.num("PinY") + dy)
            sh.append(el)
            return Forma(self.doc, el)
        forma, w, h, culoare, _ = TIPURI.get(tip, TIPURI["cutie"])
        if x is None: x, y = self.loc_langa(ancora, w, h, directie)
        el = ET.SubElement(sh, V + "Shape", {"ID": str(self.p.id_nou()), "Type": "Shape", "LineStyle": "0", "FillStyle": "0", "TextStyle": "0"})
        for n, v in (("PinX", x), ("PinY", y), ("Width", w), ("Height", h), ("LocPinX", w / 2), ("LocPinY", h / 2), ("Angle", 0.0)):
            _cell(el, n, float(v))
        _cell(el, "LineColor", "#000000"); _cell(el, "LineWeight", 0.0138889); _cell(el, "FillForegnd", culoare)
        _cell(el, "FillPattern", "1"); _cell(el, "VerticalAlign", "1")
        ch = ET.SubElement(el, V + "Section", {"N": "Character"}); r = ET.SubElement(ch, V + "Row", {"IX": "0"})
        ET.SubElement(r, V + "Cell", {"N": "Size", "V": "0.1111111"}); ET.SubElement(r, V + "Cell", {"N": "Color", "V": "#000000"})
        pa = ET.SubElement(el, V + "Section", {"N": "Paragraph"}); r = ET.SubElement(pa, V + "Row", {"IX": "0"})
        ET.SubElement(r, V + "Cell", {"N": "HorzAlign", "V": "1"})
        if forma == "elipsa" or forma == "cerc":
            _geom(el, [("Ellipse", {"X": w / 2, "Y": h / 2, "A": w, "B": h / 2, "C": w / 2, "D": h})])
        elif forma == "triunghi":
            _geom(el, [("MoveTo", {"X": 0, "Y": h / 2}), ("LineTo", {"X": w, "Y": h}), ("LineTo", {"X": w, "Y": 0}), ("LineTo", {"X": 0, "Y": h / 2})])
        else:
            _geom(el, [("RelMoveTo", {"X": 0, "Y": 0}), ("RelLineTo", {"X": 1, "Y": 0}), ("RelLineTo", {"X": 1, "Y": 1}),
                       ("RelLineTo", {"X": 0, "Y": 1}), ("RelLineTo", {"X": 0, "Y": 0})])
            if forma == "camin":
                g = el.findall(V + "Section")[-1]
                for i, (t, c) in enumerate([("MoveTo", {"X": 0, "Y": 0}), ("LineTo", {"X": w, "Y": h}), ("MoveTo", {"X": 0, "Y": h}), ("LineTo", {"X": w, "Y": 0})], 6):
                    rr = ET.SubElement(g, V + "Row", {"T": t, "IX": str(i)})
                    for n, v in c.items(): ET.SubElement(rr, V + "Cell", {"N": n, "V": "%.10g" % v})
        if forma in ("cerc", "camin"):                               # stâlpul, căminul: numele sub simbol
            for n, v in (("TxtPinX", w / 2), ("TxtPinY", -0.12), ("TxtWidth", 0.9), ("TxtHeight", 0.2), ("TxtLocPinX", 0.45), ("TxtLocPinY", 0.1)):
                _cell(el, n, float(v))
        _text(el, nume + (("\n" + detalii) if detalii else ""))
        return Forma(self.doc, el)

    # ---------- cabluri ----------
    def model_cablu(self):
        for f, a, b in self.cabluri():
            if RE_CABLU.search(f.text or ""): return f
        return None

    def adauga_cablu(self, A, B, eticheta, stil_nou=None):
        ax, ay = A.centru(); bx, by = B.centru()
        model = self.model_cablu(); sh = self.p.shapes_el(); nid = self.p.id_nou()
        el = ET.Element(V + "Shape", {"ID": str(nid), "Type": "Shape", "LineStyle": "0", "FillStyle": "0", "TextStyle": "0"})
        L = math.hypot(bx - ax, by - ay) or 0.01
        for n, v, f in (("PinX", (ax + bx) / 2, "(BeginX+EndX)/2"), ("PinY", (ay + by) / 2, "(BeginY+EndY)/2"),
                        ("Width", L, "SQRT((EndX-BeginX)^2+(EndY-BeginY)^2)"), ("Height", 0.0, None), ("LocPinX", L / 2, "Width*0.5"),
                        ("LocPinY", 0.0, "Height*0.5"), ("Angle", math.atan2(by - ay, bx - ax), "ATAN2(EndY-BeginY,EndX-BeginX)"),
                        ("BeginX", ax, f"PAR(PNT(Sheet.{A.id}!PinX,Sheet.{A.id}!PinY))"), ("BeginY", ay, f"PAR(PNT(Sheet.{A.id}!PinX,Sheet.{A.id}!PinY))"),
                        ("EndX", bx, f"PAR(PNT(Sheet.{B.id}!PinX,Sheet.{B.id}!PinY))"), ("EndY", by, f"PAR(PNT(Sheet.{B.id}!PinX,Sheet.{B.id}!PinY))")):
            _cell(el, n, float(v), f)
        _cell(el, "ObjType", "2")
        stil = {"LineColor": "#000000", "LineWeight": "0.02083333", "LinePattern": "1"}
        if model is not None:
            for n in ("LineWeight", "BeginArrow", "EndArrow"):          # grosimea ca la cablurile voastre; culoarea/linia = „cablu nou”
                v = model.cell(n)
                if v is not None: stil[n] = v
        sn = STIL_CABLU_NOU if stil_nou is None else stil_nou
        if sn.get("culoare"): stil["LineColor"] = sn["culoare"]
        stil["LinePattern"] = "2" if sn.get("intrerupt") else "1"
        for n, v in stil.items(): _cell(el, n, v)
        _cell(el, "TextBkgnd", "#FFFFFF")
        ch = ET.SubElement(el, V + "Section", {"N": "Character"}); r = ET.SubElement(ch, V + "Row", {"IX": "0"})
        ET.SubElement(r, V + "Cell", {"N": "Color", "V": sn.get("culoare") or "#000000"})
        ET.SubElement(r, V + "Cell", {"N": "Size", "V": (model and model.el.find(V + "Section[@N='Character']/" + V + "Row/" + V + "Cell[@N='Size']") is not None
                                                     and model.el.find(V + "Section[@N='Character']/" + V + "Row/" + V + "Cell[@N='Size']").get("V")) or "0.0972222"})
        _geom(el, [("MoveTo", {"X": 0, "Y": 0}), ("LineTo", {"X": L, "Y": 0})], nofill=True)
        _text(el, eticheta)
        sh.insert(0, el)                                             # sub elemente (linia pleacă din marginea simbolului)
        con = self.p.connects()
        ET.SubElement(con, V + "Connect", {"FromSheet": str(nid), "FromCell": "BeginX", "FromPart": "9", "ToSheet": str(A.id), "ToCell": "PinX", "ToPart": "3"})
        ET.SubElement(con, V + "Connect", {"FromSheet": str(nid), "FromCell": "EndX", "FromPart": "12", "ToSheet": str(B.id), "ToCell": "PinX", "ToPart": "3"})
        return Forma(self.doc, el)

    def eticheta_cablu(self, cablu, text):
        _text(cablu.el, text)

    # ---------- mutare / ștergere / redenumire ----------
    def muta(self, f, dx, dy):
        """mută forma; capetele de cablu lipite de ea (în Visio: Connects) o urmează – liniile doar apropiate rămân pe loc"""
        _cell(f.el, "PinX", f.num("PinX") + dx); _cell(f.el, "PinY", f.num("PinY") + dy)
        for c, a, b in self.cabluri(doar_lipite=True):
            for capat, idc in (("Begin", a), ("End", b)):
                if idc == f.id:
                    x, y = c.num(capat + "X") + dx, c.num(capat + "Y") + dy
                    fx = c.el.find(V + "Cell[@N='%sX']" % capat).get("F"); fy = c.el.find(V + "Cell[@N='%sY']" % capat).get("F")
                    _cell(c.el, capat + "X", x, fx); _cell(c.el, capat + "Y", y, fy)
            bx, by, ex, ey = c.num("BeginX"), c.num("BeginY"), c.num("EndX"), c.num("EndY")
            if c.el.find(V + "Cell[@N='Width']") is not None and (a == f.id or b == f.id):
                L = math.hypot(ex - bx, ey - by)
                _cell(c.el, "PinX", (bx + ex) / 2, c.el.find(V + "Cell[@N='PinX']").get("F"))
                _cell(c.el, "PinY", (by + ey) / 2, c.el.find(V + "Cell[@N='PinY']").get("F"))
                if c.cell("Height") in (None, "0"):
                    _cell(c.el, "Width", L, c.el.find(V + "Cell[@N='Width']").get("F"))
                    _cell(c.el, "LocPinX", L / 2, (c.el.find(V + "Cell[@N='LocPinX']").get("F") if c.el.find(V + "Cell[@N='LocPinX']") is not None else None))
                    if c.el.find(V + "Cell[@N='Angle']") is not None:
                        _cell(c.el, "Angle", math.atan2(ey - by, ex - bx), c.el.find(V + "Cell[@N='Angle']").get("F"))
                    for r in c.el.iter(V + "Row"):
                        if r.get("T") == "LineTo":
                            cx = r.find(V + "Cell[@N='X']")
                            if cx is not None and fnum(cx.get("V")) > 0: cx.set("V", "%.10g" % L)

    def sterge(self, f):
        sh = self.p.shapes_el()
        if f.el in list(sh): sh.remove(f.el)
        con = self.p.connects()
        for c in list(con):
            if c.get("FromSheet") == str(f.id) or c.get("ToSheet") == str(f.id): con.remove(c)

    def redenumeste(self, f, nou):
        vechi = f.text_tot()
        for e in f.el.iter(V + "Shape"):
            t = text_forma(e)
            if t and t.strip() == vechi.strip():
                lin = t.split("\n"); lin[0] = nou; _text(e, "\n".join(lin)); return
        lin = vechi.split("\n"); lin[0] = nou; _text(f.el, "\n".join(lin))


def pagina_sudura(doc, nume_manson, a_nume, a_fibre, b_nume, b_fibre, per_tub=12):
    """o pagină „Sudură <manșon>”: fibrele cablului A (stânga) legate de fibrele cablului B (dreapta), pe culori"""
    p = doc.pagina_noua(f"Sudură {nume_manson}"); s = Schema(doc, p)
    W, H = p.dimensiune(); sh = p.shapes_el()
    exist = [f for f in p.forme()]
    y0 = H - 1.0                                                     # a doua sudură în același manșon: dedesubt
    if exist: y0 = min(f.cutie()[1] for f in exist) - 0.6
    titlu = s.adauga_element(f"Sudură în {nume_manson}: {a_nume} → {b_nume}", "cutie", W / 2, y0, detalii="")
    _cell(titlu.el, "Width", 4.5); _cell(titlu.el, "LocPinX", 2.25); _cell(titlu.el, "FillForegnd", "#FFFFFF"); _cell(titlu.el, "LinePattern", "0")
    xa, xb = W / 2 - 1.6, W / 2 + 1.6; dy = 0.22

    def fibra(x, y, nr, sus_eticheta):
        _, cul = CULORI[(nr - 1) % 12]; tub = (nr - 1) // per_tub
        el = ET.SubElement(sh, V + "Shape", {"ID": str(p.id_nou()), "Type": "Shape", "LineStyle": "0", "FillStyle": "0", "TextStyle": "0"})
        for n, v in (("PinX", x), ("PinY", y), ("Width", 0.55), ("Height", 0.17), ("LocPinX", 0.275), ("LocPinY", 0.085)): _cell(el, n, float(v))
        _cell(el, "FillForegnd", cul); _cell(el, "LineColor", CULORI[tub % 12][1]); _cell(el, "LineWeight", 0.03)
        chs = ET.SubElement(el, V + "Section", {"N": "Character"}); r = ET.SubElement(chs, V + "Row", {"IX": "0"})
        ET.SubElement(r, V + "Cell", {"N": "Size", "V": "0.0833333"})
        ET.SubElement(r, V + "Cell", {"N": "Color", "V": "#FFFFFF" if cul in ("#0070C0", "#8B4513", "#000000", "#8000C0", "#E00000", "#00A050") else "#000000"})
        _geom(el, [("RelMoveTo", {"X": 0, "Y": 0}), ("RelLineTo", {"X": 1, "Y": 0}), ("RelLineTo", {"X": 1, "Y": 1}), ("RelLineTo", {"X": 0, "Y": 1}), ("RelLineTo", {"X": 0, "Y": 0})])
        _text(el, f"{nr}"); return Forma(doc, el)
    n = max(len(a_fibre), len(b_fibre)); ytop = y0 - 0.5
    ha = s.adauga_element(a_nume, "cutie", xa, ytop + 0.05); _cell(ha.el, "FillForegnd", "#F2F2F2"); _cell(ha.el, "Width", 1.4); _cell(ha.el, "LocPinX", 0.7)
    hb = s.adauga_element(b_nume, "cutie", xb, ytop + 0.05); _cell(hb.el, "FillForegnd", "#F2F2F2"); _cell(hb.el, "Width", 1.4); _cell(hb.el, "LocPinX", 0.7)
    for k in range(n):
        y = ytop - 0.45 - k * dy
        fa = fibra(xa, y, a_fibre[k], True) if k < len(a_fibre) else None
        fb = fibra(xb, y, b_fibre[k], False) if k < len(b_fibre) else None
        if fa is not None and fb is not None:
            c = s.adauga_cablu(fa, fb, "", stil_nou={}); _cell(c.el, "LineColor", CULORI[(a_fibre[k] - 1) % 12][1] if a_fibre[k] % 12 != 6 else "#A0A0A0")
            _cell(c.el, "LineWeight", 0.02)
    return p, len([1 for k in range(n) if k < len(a_fibre) and k < len(b_fibre)])
