"""Citirea și modificarea fișierelor Visio (.vsdx) fără Visio.
Un .vsdx e o arhivă zip cu XML: paginile (visio/pages/pageN.xml), formele de bază (visio/masters) etc.
Desenul existent rămâne neatins; se adaugă / se schimbă doar formele cerute."""
import copy, io, math, os, re, sys, zipfile
import xml.etree.ElementTree as ET

NS = "http://schemas.microsoft.com/office/visio/2012/main"
NR = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
ET.register_namespace("", NS)
ET.register_namespace("r", NR)
V = "{%s}" % NS
REL_PAGE = "http://schemas.microsoft.com/visio/2010/relationships/page"
CT_PAGE = "application/vnd.ms-visio.page+xml"


def date_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def fnum(v, d=0.0):
    try: return float(v)
    except (TypeError, ValueError): return d


def norm(s):
    """nume comparabil: fără diacritice, spații, liniuțe; litere mari"""
    s = (s or "").strip().split("\n")[0]
    for a, b in zip("ăâîșşțţĂÂÎȘŞȚŢ", "aaisstt" + "AAISSTT"): s = s.replace(a, b)
    return re.sub(r"[\s\-_.]", "", s).upper()


def text_forma(sh):
    t = sh.find(V + "Text")
    return "".join(t.itertext()).strip() if t is not None else ""


class Forma:
    """o formă de pe pagină (vedere peste elementul XML), cu moștenirea din forma de bază (master)"""

    def __init__(self, doc, el, parinte=None, master=None):
        self.doc, self.el, self.parinte = doc, el, parinte
        mid = el.get("Master")
        if mid is not None: master = doc.master_forma(mid, el.get("MasterShape"))
        elif master is not None and el.get("MasterShape") is not None:
            master = doc.master_forma(master[0], el.get("MasterShape"))
        self.master = master                                   # (id master, element Shape din master) sau None
        self.copii = [Forma(doc, c, self, (self.master[0], None) if self.master and mid else self.master)
                      for c in (el.find(V + "Shapes") if el.find(V + "Shapes") is not None else [])]

    @property
    def id(self): return int(self.el.get("ID"))

    def _surse(self):
        return [s for s in (self.el, self.master[1] if self.master and self.master[1] is not None else None) if s is not None]

    def _stil(self, tip):
        for s in self._surse():
            if s.get(tip) is not None: return s.get(tip)
        return None

    def cell(self, n, d=None):
        """valoarea celulei: din formă, din forma de bază (master), apoi din stilul documentului"""
        for src in self._surse():
            c = src.find(V + "Cell[@N='%s']" % n)
            if c is not None: return c.get("V")
        tip = "LineStyle" if n.startswith(("Line", "Rounding", "BeginArrow", "EndArrow")) else \
              "FillStyle" if n.startswith(("Fill", "Shdw")) else "TextStyle"
        v = self.doc.cell_stil(self._stil(tip), n, tip)
        return d if v is None else v

    def sectiune(self, sec, n, d=None):
        """celula din rândul 0 al unei secțiuni (Character, Paragraph): formă, master, stil text"""
        for src in self._surse():
            c = src.find(V + "Section[@N='%s']/%sRow/%sCell[@N='%s']" % (sec, V, V, n))
            if c is not None: return c.get("V")
        v = self.doc.cell_stil(self._stil("TextStyle"), n, "TextStyle", sec)
        return d if v is None else v

    def num(self, n, d=0.0): return fnum(self.cell(n), d)

    @property
    def text(self):
        t = text_forma(self.el)
        if not t and self.master and self.master[1] is not None: t = text_forma(self.master[1])
        return t

    def text_tot(self):
        """textul formei sau, la grupuri, primul text găsit în interior"""
        if self.text: return self.text
        for c in self.copii:
            t = c.text_tot()
            if t: return t
        return ""

    @property
    def e1d(self): return self.cell("BeginX") is not None

    def geometrie(self):
        """secțiunile Geometry (rândurile din instanță peste cele din master)"""
        secs = {}
        for src in (self.master[1] if self.master and self.master[1] is not None else None, self.el):
            if src is None: continue
            for s in src.findall(V + "Section[@N='Geometry']"):
                ix = s.get("IX", "0"); d = secs.setdefault(ix, {"rows": {}, "nofill": False, "noline": False, "noshow": False})
                for c in s.findall(V + "Cell"):
                    if c.get("N") in ("NoFill", "NoLine", "NoShow"): d[c.get("N").lower()] = c.get("V") == "1"
                for r in s.findall(V + "Row"):
                    ix2 = int(r.get("IX", "0"))
                    if r.get("Del") == "1": d["rows"].pop(ix2, None); continue
                    vals = dict(d["rows"].get(ix2, {}).get("v", {}))
                    for c in r.findall(V + "Cell"): vals[c.get("N")] = fnum(c.get("V"))
                    d["rows"][ix2] = {"t": r.get("T") or d["rows"].get(ix2, {}).get("t"), "v": vals}
        return [secs[k] for k in sorted(secs, key=lambda x: int(x))]

    def transforma(self):
        """funcția care duce un punct din coordonatele locale ale formei în coordonatele paginii"""
        px, py = self.num("PinX"), self.num("PinY"); lx, ly = self.num("LocPinX"), self.num("LocPinY")
        a = self.num("Angle"); fx, fy = self.cell("FlipX") == "1", self.cell("FlipY") == "1"
        w, h = self.num("Width"), self.num("Height")
        ca, sa = math.cos(a), math.sin(a)
        sus = self.parinte.transforma() if self.parinte else (lambda x, y: (x, y))

        def f(x, y):
            if fx: x = w - x
            if fy: y = h - y
            dx, dy = x - lx, y - ly
            return sus(px + dx * ca - dy * sa, py + dx * sa + dy * ca)
        return f

    def contur(self):
        """liniile formei pe pagină: listă de (puncte, umplut, cerc?)"""
        w, h = self.num("Width"), self.num("Height"); T = self.transforma(); out = []
        if self.e1d and not self.geometrie():
            return [([(self.num("BeginX"), self.num("BeginY")), (self.num("EndX"), self.num("EndY"))], False)] if not self.parinte else []
        for g in self.geometrie():
            if g["noshow"]: continue
            pts = []; cur = (0, 0)
            for ix in sorted(g["rows"]):
                r = g["rows"][ix]; t = r["t"] or ""; v = r["v"]
                x, y = v.get("X", cur[0]), v.get("Y", cur[1])
                if t.startswith("Rel"): x, y = x * w, y * h
                if t in ("MoveTo", "RelMoveTo"):
                    if len(pts) > 1: out.append((pts, not g["nofill"]))
                    pts = [T(x, y)]; cur = (x, y)
                elif t == "Ellipse":
                    cx, cy = v.get("X", 0), v.get("Y", 0); ax, ay = v.get("A", 0) - cx, v.get("B", 0) - cy
                    bx, by = v.get("C", 0) - cx, v.get("D", 0) - cy
                    out.append(([T(cx + ax * math.cos(k / 24 * 2 * math.pi) + bx * math.sin(k / 24 * 2 * math.pi),
                                   cy + ay * math.cos(k / 24 * 2 * math.pi) + by * math.sin(k / 24 * 2 * math.pi)) for k in range(25)],
                                not g["nofill"]))
                elif t in ("InfiniteLine",): continue
                else:                                          # LineTo, ArcTo, PolylineTo, NURBSTo... (aproximat cu segment)
                    if not pts: pts = [T(*cur)]
                    pts.append(T(x, y)); cur = (x, y)
            if len(pts) > 1: out.append((pts, not g["nofill"]))
        if not out and not self.copii and w > 0 and h > 0 and not self.e1d:
            out.append(([T(0, 0), T(w, 0), T(w, h), T(0, h), T(0, 0)], True))
        return out

    def cutie(self):
        """dreptunghiul formei pe pagină (x0, y0, x1, y1)"""
        pts = [p for c, _ in self.contur() for p in c]
        for c in self.copii: pts += [(b[0], b[1]) for b in [c.cutie()] if b] + [(b[2], b[3]) for b in [c.cutie()] if b]
        if not pts:
            T = self.transforma(); pts = [T(0, 0), T(self.num("Width"), self.num("Height"))]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    def centru(self):
        x0, y0, x1, y1 = self.cutie(); return (x0 + x1) / 2, (y0 + y1) / 2


class Pagina:
    def __init__(self, doc, nume, part, el_page):
        self.doc, self.nume, self.part, self.el_page = doc, nume, part, el_page
        self.root = ET.fromstring(doc.parts[part])

    def shapes_el(self):
        s = self.root.find(V + "Shapes")
        if s is None:
            s = ET.Element(V + "Shapes"); self.root.insert(0, s)
        return s

    def forme(self):
        return [Forma(self.doc, el) for el in self.shapes_el().findall(V + "Shape")]

    def toate(self):
        def rec(fs):
            for f in fs:
                yield f; yield from rec(f.copii)
        return list(rec(self.forme()))

    def connects(self):
        c = self.root.find(V + "Connects")
        if c is None:
            c = ET.SubElement(self.root, V + "Connects")
        return c

    def dimensiune(self):
        ps = self.el_page.find(V + "PageSheet")
        w = h = None
        if ps is not None:
            for c in ps.findall(V + "Cell"):
                if c.get("N") == "PageWidth": w = fnum(c.get("V"))
                if c.get("N") == "PageHeight": h = fnum(c.get("V"))
        return w or 11.69, h or 8.27

    def id_nou(self):
        ids = [int(e.get("ID")) for e in self.root.iter(V + "Shape") if e.get("ID", "").isdigit()]
        return max(ids, default=0) + 1

    def serializeaza(self):
        self.doc.parts[self.part] = ET.tostring(self.root, encoding="utf-8", xml_declaration=True)


class Document:
    def __init__(self, path=None):
        self.path = path
        src = path or os.path.join(date_dir(), "sablon", "gol.vsdx")
        with zipfile.ZipFile(src) as z:
            self.ordine = z.namelist(); self.parts = {n: z.read(n) for n in self.ordine}
        self._masters = None
        self.incarca_pagini()
        if path is None: self.format_pagina(self.pagini[0], 16.5354, 11.6929)        # schemă nouă: A3 culcat

    def format_pagina(self, p, w, h):
        ps = p.el_page.find(V + "PageSheet")
        for c in ps.findall(V + "Cell"):
            if c.get("N") == "PageWidth": c.set("V", "%.10g" % w)
            if c.get("N") == "PageHeight": c.set("V", "%.10g" % h)

    # ---------- structura ----------
    def rels(self, part):
        d, b = os.path.split(part); rp = (d + "/_rels/" + b + ".rels").lstrip("/")
        if rp not in self.parts: return {}
        out = {}
        for m in re.finditer(r"<Relationship\b([^>]*)/?>", self.parts[rp].decode("utf-8")):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
            out[a.get("Id")] = (a.get("Type"), os.path.normpath(os.path.join(d, a.get("Target", ""))).replace("\\", "/"))
        return out

    def part_tip(self, tip_sfarsit):
        for _, (t, p) in self.rels("visio/document.xml").items():
            if t.endswith(tip_sfarsit): return p
        return None

    def incarca_pagini(self):
        self.pages_part = self.part_tip("/pages") or "visio/pages/pages.xml"
        self.pages_root = ET.fromstring(self.parts[self.pages_part]); rel = self.rels(self.pages_part)
        self.pagini = []
        for p in self.pages_root.findall(V + "Page"):
            if p.get("Background") == "1": continue
            r = p.find(V + "Rel"); rid = r.get("{%s}id" % NR) if r is not None else None
            if rid in rel: self.pagini.append(Pagina(self, p.get("Name") or p.get("NameU"), rel[rid][1], p))

    def cell_stil(self, sid, n, tip, sec=None, adanc=0):
        """celula dintr-o foaie de stil (cu moștenirea stilurilor părinte)"""
        if sid is None or adanc > 10: return None
        if not hasattr(self, "_stiluri"):
            self._stiluri = {}
            try:
                for st in ET.fromstring(self.parts["visio/document.xml"]).iter(V + "StyleSheet"): self._stiluri[st.get("ID")] = st
            except Exception: pass
        st = self._stiluri.get(sid)
        if st is None: return None
        c = st.find(V + "Section[@N='%s']/%sRow/%sCell[@N='%s']" % (sec, V, V, n)) if sec else st.find(V + "Cell[@N='%s']" % n)
        if c is not None: return c.get("V")
        par = st.get(tip)
        return None if par == sid else self.cell_stil(par, n, tip, sec, adanc + 1)

    def master_forma(self, mid, shape_id=None):
        if self._masters is None:
            self._masters = {}
            mp = self.part_tip("/masters")
            if mp and mp in self.parts:
                rel = self.rels(mp)
                for m in ET.fromstring(self.parts[mp]).findall(V + "Master"):
                    r = m.find(V + "Rel"); rid = r.get("{%s}id" % NR) if r is not None else None
                    if rid in rel and rel[rid][1] in self.parts:
                        self._masters[m.get("ID")] = (m, ET.fromstring(self.parts[rel[rid][1]]))
        if mid not in self._masters: return (mid, None)
        sh = self._masters[mid][1].find(V + "Shapes")
        if sh is None: return (mid, None)
        if shape_id is None:
            first = sh.find(V + "Shape"); return (mid, first)
        for e in self._masters[mid][1].iter(V + "Shape"):
            if e.get("ID") == shape_id: return (mid, e)
        return (mid, None)

    def nume_master(self, mid):
        self.master_forma(mid)
        m = self._masters.get(mid)
        return (m[0].get("NameU") or m[0].get("Name") or "") if m else ""

    # ---------- pagini noi ----------
    def pagina_noua(self, nume):
        for p in self.pagini:
            if p.nume == nume: return p
        model = self.pagini[0]
        k = 1
        while f"visio/pages/page{k}.xml" in self.parts: k += 1
        part = f"visio/pages/page{k}.xml"
        self.parts[part] = (f"<?xml version='1.0' encoding='utf-8' ?>\n<PageContents xmlns='{NS}' xmlns:r='{NR}' "
                            f"xml:space='preserve'><Shapes/></PageContents>").encode()
        self.ordine.append(part)
        # relația din pages.xml
        rp = os.path.dirname(self.pages_part) + "/_rels/" + os.path.basename(self.pages_part) + ".rels"
        s = self.parts[rp].decode("utf-8"); ids = [int(x) for x in re.findall(r'Id="rId(\d+)"', s)]
        rid = f"rId{max(ids, default=0) + 1}"
        s = s.replace("</Relationships>", f'<Relationship Id="{rid}" Type="{REL_PAGE}" Target="page{k}.xml"/></Relationships>')
        self.parts[rp] = s.encode()
        ct = self.parts["[Content_Types].xml"].decode("utf-8")
        ct = ct.replace("</Types>", f'<Override PartName="/{part}" ContentType="{CT_PAGE}"/></Types>')
        self.parts["[Content_Types].xml"] = ct.encode()
        pid = max([int(p.get("ID")) for p in self.pages_root.findall(V + "Page")], default=0) + 1
        pe = ET.SubElement(self.pages_root, V + "Page", {"ID": str(pid), "NameU": nume, "Name": nume})
        ps = model.el_page.find(V + "PageSheet")
        if ps is not None: pe.append(copy.deepcopy(ps))
        ET.SubElement(pe, V + "Rel", {"{%s}id" % NR: rid})
        pg = Pagina(self, nume, part, pe); self.pagini.append(pg)
        return pg

    # ---------- salvare / anulare ----------
    def instantaneu(self):
        for p in self.pagini: p.serializeaza()
        self.parts[self.pages_part] = ET.tostring(self.pages_root, encoding="utf-8", xml_declaration=True)
        return (dict(self.parts), list(self.ordine))

    def restaureaza(self, st):
        self.parts, self.ordine = dict(st[0]), list(st[1]); self._masters = None; self.incarca_pagini()

    def salveaza(self, path, pastreaza_cale=False):
        self.instantaneu()
        tmp = path + ".tmp"
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for n in ["[Content_Types].xml"] + [n for n in self.ordine if n != "[Content_Types].xml"]:
                if n in self.parts and not n.endswith("/"): z.writestr(n, self.parts[n])
        os.replace(tmp, path)
        if not pastreaza_cale: self.path = path
