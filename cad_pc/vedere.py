"""Desenarea pe ecran (pe un Canvas Tk): entitățile din DXF transformate în linii/poligoane/texte în coordonate de lume,
apoi desenate cu zoom și deplasare. Blocurile și cotele se desfac în entitățile lor (virtual_entities)."""
import math, os
import tkinter as tk
from ezdxf import colors as ezcolors, path as ezpath
from stil import *

SARITE = {"ATTDEF", "WIPEOUT", "VIEWPORT", "OLE2FRAME", "XLINE", "RAY"}


def _hex(rgb): return "#%02x%02x%02x" % tuple(int(v) for v in rgb)


class Vedere:
    def __init__(self, cv):
        self.cv = cv; self.doc = None; self.layout = None
        self.ph = {}                      # handle -> [("p", [x,y,…], culoare, handle, umplut, strat) / ("t", x, y, text, h, rot, culoare, handle, ancora, strat)]
        self.s = 1.0; self.cx = 0.0; self.cy = 0.0
        self.grila = True; self.ascunse = set(); self._dupa = None
        self.selectie = set(); self.bbox = {}
        self.img = {}; self.dosar = ""; self._foto = []   # handle -> (fișier, x0, y0, x1, y1) pentru imaginile raster
        from imagini import CachePreviz
        self.previz = CachePreviz(cv, lambda: self._mai_tarziu(10))
        self.foaie = None; self.sf = 1.0; self.fx = 0.0; self.fy = 0.0; self._img = None; self._cheie = None; self.versiune = 0

    # ---------------------------------------------------------------- încărcare
    def incarca(self, doc, layout="Model", gata=None):
        self.doc = doc; self.layout = doc.modelspace() if layout == "Model" else doc.layouts.get(layout)
        if gata is not None and gata.doc is doc:          # pregătit deja în fundal (vezi pregateste)
            self.ph, self.bbox, self._lay, self.versiune = gata.ph, gata.bbox, gata._lay, self.versiune + 1
        else: self.reconstruieste()
        self.zoom_extinde()

    def pregateste(self, doc):
        """calculează desenul pe firul de fundal, fără să atingă ecranul"""
        import copy
        pv = copy.copy(self); pv.doc = doc; pv.layout = doc.modelspace(); pv.reconstruieste(); return pv

    def straturi(self):
        return {l.dxf.name: l for l in self.doc.layers} if self.doc else {}

    # ---------------------------------------------------------------- foi (Layout): hârtia albă cu desenul randat
    def arata_foaie(self, nume):
        self.foaie = None if nume in (None, "Model") else nume
        if self.foaie:
            import tiparire
            self.hartie = tiparire.dimensiune_foaie(self.doc, self.foaie); W, H = self.wh()
            self.sf = min(W * 0.85 / self.hartie[0], H * 0.85 / self.hartie[1]); self.fx, self.fy = W / 2, H / 2
        self.deseneaza()

    def _deseneaza_foaie(self):
        import tiparire
        cv = self.cv; cv.delete("e"); cv.delete("g"); W, H = self.wh()
        cv.create_rectangle(0, 0, W, H, fill="#4a4f57", outline="", tags="g")
        w, h = self.hartie[0] * self.sf, self.hartie[1] * self.sf; x0, y0 = self.fx - w / 2, self.fy - h / 2
        cv.create_rectangle(x0 + 6, y0 + 6, x0 + w + 6, y0 + h + 6, fill="#2a2d33", outline="", tags="e")
        dpi = int(max(10, min(self.sf * 25.4, 5000 / max(self.hartie) * 25.4)))
        cheie = (self.foaie, round(dpi), self.versiune)
        if cheie != self._cheie:
            try:
                self._img = tk.PhotoImage(data=tiparire.png_foaie(self.doc, self.foaie, dpi)); self._cheie = cheie
            except Exception:
                import traceback; traceback.print_exc(); self._img = None
        if self._img is not None:
            k = w / max(1, self._img.width())
            img = self._img if abs(k - 1) < 0.02 else (self._img.zoom(max(1, round(k))) if k > 1 else self._img.subsample(max(1, round(1 / k))))
            self._vizibil = img; cv.create_image(self.fx, self.fy, image=img, tags="e")
        else:
            cv.create_rectangle(x0, y0, x0 + w, y0 + h, fill="white", outline="", tags="e")
        cv.create_rectangle(x0, y0, x0 + w, y0 + h, outline="#9aa0a8", tags="e")
        cv.create_rectangle(x0 + 10 * self.sf, y0 + 10 * self.sf, x0 + w - 10 * self.sf, y0 + h - 10 * self.sf, outline="#b0b0b0", dash=(4, 3), tags="e")
        cv.tag_raise("ov"); cv.tag_raise("cur")

    def reconstruieste(self):
        """recalculează primitivele (după o modificare a desenului sau a straturilor)"""
        self.versiune += 1
        self.ph = {}; self._lay = self.straturi(); self.bbox = {}; self.img = {}
        if self.layout is None: return
        for e in self.layout: self._adauga(e)

    @property
    def prim(self):
        return [p for l in self.ph.values() for p in l]

    def _adauga(self, e):
        h = e.dxf.handle; self._curent = []
        try: self._entitate(e, h, None, None, 0)
        except Exception: pass
        self.ph[h] = self._curent; self._cutie(h)

    def actualizeaza(self, handles):
        """refă doar entitățile schimbate (rapid și pe desene mari)"""
        self._lay = self.straturi(); self.versiune += 1
        for h in handles:
            self.ph.pop(h, None); self.bbox.pop(h, None); self.img.pop(h, None)
            try: e = self.doc.entitydb[h]
            except Exception: e = None
            if e is not None and e.is_alive and e.dxf.owner == self.layout.layout_key: self._adauga(e)

    def _cutie(self, h0):
        bb = self.bbox                                    # cutia fiecărei entități (pentru selecția cu fereastră)
        for p in self.ph.get(h0, ()):
            if p[0] == "t":
                h = p[7]; x, y, hg = p[1], p[2], p[4]; n = max(len(l) for l in p[3].split("\n")) * hg * 0.7
                box = (x - n * 0.1, y - hg * 0.3, x + n, y + hg * (p[3].count("\n") + 1.2))
            else:
                h = p[3]; xs = p[1][0::2]; ys = p[1][1::2]; box = (min(xs), min(ys), max(xs), max(ys))
            o = bb.get(h0)
            bb[h0] = box if o is None else (min(o[0], box[0]), min(o[1], box[1]), max(o[2], box[2]), max(o[3], box[3]))

    def strat_vizibil(self, nume):
        l = self._lay.get(nume)
        return l is None or (l.is_on() and not l.is_frozen())

    def _culoare(self, e, strat, cul_parinte):
        if e.dxf.hasattr("true_color"): return _hex(ezcolors.int2rgb(e.dxf.true_color))
        c = e.dxf.get("color", 256)
        if c == 0: return cul_parinte or "#ffffff"
        if c == 256:
            l = self._lay.get(strat)
            if l is None: return "#ffffff"
            if l.dxf.hasattr("true_color"): return _hex(ezcolors.int2rgb(l.dxf.true_color))
            c = abs(l.dxf.get("color", 7))
        if c in (7, 255): return "#ffffff"
        return _hex(ezcolors.aci2rgb(c))

    def _entitate(self, e, h, strat_p, cul_p, adanc):
        t = e.dxftype()
        if t in SARITE: return
        strat = e.dxf.get("layer", "0")
        if strat == "0" and strat_p: strat = strat_p              # în blocuri, stratul „0” ia stratul blocului
        cul = self._culoare(e, strat, cul_p)
        if t == "IMAGE": return self._imagine(e, h, strat, cul, adanc)
        if t in ("INSERT", "DIMENSION", "ARC_DIMENSION", "LARGE_RADIAL_DIMENSION", "LEADER", "MLEADER", "MULTILEADER", "ACAD_TABLE") and adanc < 6:
            try:
                for v in e.virtual_entities(): self._entitate(v, h, strat, cul, adanc + 1)
            except Exception: pass
            if t == "INSERT":
                for a in e.attribs:
                    if not a.dxf.get("flags", 0) & 1: self._text(a, h, strat, self._culoare(a, strat, cul))
            return
        if t in ("TEXT", "ATTRIB"): return self._text(e, h, strat, cul)
        if t == "MTEXT": return self._mtext(e, h, strat, cul)
        if t == "POINT":
            x, y = e.dxf.location.x, e.dxf.location.y; self._curent.append(("pt", [x, y], cul, h, False, strat)); return
        if t in ("SOLID", "TRACE", "3DFACE"):
            v = [e.dxf.vtx0, e.dxf.vtx1, e.dxf.vtx3, e.dxf.vtx2] if t != "3DFACE" else [e.dxf.vtx0, e.dxf.vtx1, e.dxf.vtx2, e.dxf.vtx3]
            self._curent.append(("p", [c for p in v for c in (p.x, p.y)], cul, h, True, strat)); return
        if t == "HATCH":
            plin = e.dxf.get("solid_fill", 0) == 1
            for p in ezpath.from_hatch(e):
                pts = list(p.flattening(self._prec(p)))
                if len(pts) > 1: self._curent.append(("p", [c for q in pts for c in (q.x, q.y)], cul, h, plin, strat))
            return
        try:
            p = ezpath.make_path(e)
        except Exception:
            try:
                for v in e.virtual_entities(): self._entitate(v, h, strat, cul, adanc + 1)
            except Exception: pass
            return
        for sp in (p.sub_paths() if p.has_sub_paths else [p]):
            pts = list(sp.flattening(self._prec(sp)))
            if len(pts) > 1: self._curent.append(("p", [c for q in pts for c in (q.x, q.y)], cul, h, False, strat))

    def _imagine(self, e, h, strat, cul, adanc):
        """rama imaginii (pentru selecție) + imaginea propriu-zisă, dacă fișierul se găsește"""
        try: col = [(v.x, v.y) for v in e.boundary_path_wcs()]
        except Exception: return
        if len(col) < 3: return
        if col[0] != col[-1]: col.append(col[0])
        self._curent.append(("p", [c for q in col for c in q], cul, h, False, strat))
        if adanc: return
        idef = e.image_def
        if idef is None: return
        cale = self.cauta_fisier(idef.dxf.filename)
        u, v, ins = e.dxf.u_pixel, e.dxf.v_pixel, e.dxf.insert; pw, ph = e.dxf.image_size.x, e.dxf.image_size.y
        if abs(u.y) > 1e-9 or abs(v.x) > 1e-9: return            # imagine rotită: doar rama
        x0, y0 = ins.x, ins.y; x1, y1 = x0 + u.x * pw, y0 + v.y * ph
        self.img[h] = (cale, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), u.x < 0, v.y < 0)

    def cauta_fisier(self, f):
        if not f: return None
        if os.path.isfile(f): return f
        for c in (os.path.join(self.dosar, f), os.path.join(self.dosar, os.path.basename(f.replace("\\", "/")))):
            if self.dosar and os.path.isfile(c): return c
        return None

    def _deseneaza_imagini(self, W, H):
        """decupează din copia micșorată exact partea vizibilă și o întinde pe ecran"""
        from PIL import Image, ImageTk
        self._foto = []
        for h, (cale, x0, y0, x1, y1, inv_x, inv_y) in self.img.items():
            if cale is None or not self.strat_vizibil(self._strat_ent(h)): continue
            sx0, sy1 = self.ecran(x0, y0); sx1, sy0 = self.ecran(x1, y1)
            vx0, vy0, vx1, vy1 = max(sx0, 0), max(sy0, 0), min(sx1, W), min(sy1, H)
            if vx1 - vx0 < 1 or vy1 - vy0 < 1: continue
            r = self.previz.ia(cale)
            if not r: continue
            im, _ = r; iw, ih = im.size
            kx, ky = iw / (sx1 - sx0), ih / (sy1 - sy0)
            box = ((vx0 - sx0) * kx, (vy0 - sy0) * ky, (vx1 - sx0) * kx, (vy1 - sy0) * ky)
            if inv_x: box = (iw - box[2], box[1], iw - box[0], box[3])
            if inv_y: box = (box[0], ih - box[3], box[2], ih - box[1])
            dw, dh = max(1, int(round(vx1 - vx0))), max(1, int(round(vy1 - vy0)))
            try:
                bucata = im.resize((dw, dh), Image.BILINEAR if dw < (box[2] - box[0]) else Image.NEAREST, box=box)
                if inv_x: bucata = bucata.transpose(Image.FLIP_LEFT_RIGHT)
                if inv_y: bucata = bucata.transpose(Image.FLIP_TOP_BOTTOM)
                f = ImageTk.PhotoImage(bucata)
            except Exception: continue
            self._foto.append(f); self.cv.create_image(vx0, vy0, image=f, anchor="nw", tags=("e", "img", "h" + h))
        if self._foto: self.cv.tag_lower("img"); self.cv.tag_lower("g")

    def _strat_ent(self, h):
        for p in self.ph.get(h, ()): return p[-1]
        return "0"

    def zoom_fereastra(self, x0, y0, x1, y1):
        W, H = self.wh(); self.cx, self.cy = (x0 + x1) / 2, (y0 + y1) / 2
        self.s = min(W * 0.92 / max(x1 - x0, 1e-9), H * 0.88 / max(y1 - y0, 1e-9)); self.deseneaza()

    @staticmethod
    def _prec(p):
        try:
            cps = list(p.control_vertices())
            xs = [v.x for v in cps]; ys = [v.y for v in cps]
            return max(1e-6, max(max(xs) - min(xs), max(ys) - min(ys)) * 0.004)
        except Exception: return 0.01

    def _text(self, e, h, strat, cul):
        txt = e.plain_text() if hasattr(e, "plain_text") else e.dxf.text
        if not txt.strip(): return
        ha, va = e.dxf.get("halign", 0), e.dxf.get("valign", 0)
        p = e.dxf.align_point if (ha or va) and e.dxf.hasattr("align_point") else e.dxf.insert
        anc = {0: "sw", 1: "s", 2: "se", 3: "sw", 4: "center", 5: "sw"}.get(ha, "sw")
        if va == 3: anc = {"sw": "nw", "s": "n", "se": "ne"}.get(anc, anc)
        elif va == 2 and ha != 4: anc = {"sw": "w", "s": "center", "se": "e"}.get(anc, anc)
        self._curent.append(("t", p.x, p.y, txt, e.dxf.get("height", 2.5), e.dxf.get("rotation", 0.0), cul, h, anc, strat))

    def _mtext(self, e, h, strat, cul):
        txt = e.plain_text()
        if not txt.strip(): return
        ap = e.dxf.get("attachment_point", 1)
        anc = {1: "nw", 2: "n", 3: "ne", 4: "w", 5: "center", 6: "e", 7: "sw", 8: "s", 9: "se"}.get(ap, "nw")
        try: rot = e.get_rotation()
        except Exception: rot = e.dxf.get("rotation", 0.0)
        self._curent.append(("t", e.dxf.insert.x, e.dxf.insert.y, txt, e.dxf.get("char_height", 2.5), rot, cul, h, anc, strat))

    # ---------------------------------------------------------------- transformări
    def wh(self):
        return max(1, self.cv.winfo_width()), max(1, self.cv.winfo_height())

    def ecran(self, x, y):
        W, H = self.wh(); return (x - self.cx) * self.s + W / 2, H / 2 - (y - self.cy) * self.s

    def lume(self, sx, sy):
        W, H = self.wh(); return (sx - W / 2) / self.s + self.cx, (H / 2 - sy) / self.s + self.cy

    def limite(self):
        xs, ys = [], []
        for p in (q for l in self.ph.values() for q in l):
            if not self.strat_vizibil(p[-1]): continue
            if p[0] == "t": xs.append(p[1]); ys.append(p[2])
            else: xs += p[1][0::2]; ys += p[1][1::2]
        if not xs: return None
        return min(xs), min(ys), max(xs), max(ys)

    def zoom_extinde(self):
        if self.foaie: return self.arata_foaie(self.foaie)
        b = self.limite(); W, H = self.wh()
        if not b: self.s, self.cx, self.cy = 1.0, 0, 0
        else:
            x0, y0, x1, y1 = b; self.cx, self.cy = (x0 + x1) / 2, (y0 + y1) / 2
            self.s = min(W * 0.92 / max(x1 - x0, 1e-9), H * 0.88 / max(y1 - y0, 1e-9))
        self.deseneaza()

    def zoom(self, f, sx, sy):
        if self.foaie:
            if not (0.3 < self.sf * f) or self.sf * f * max(self.hartie) > 5000: return
            self.sf *= f; self.fx = sx + (self.fx - sx) * f; self.fy = sy + (self.fy - sy) * f; self._mai_tarziu(); return
        wx, wy = self.lume(sx, sy); self.s *= f
        W, H = self.wh(); self.cx = wx - (sx - W / 2) / self.s; self.cy = wy + (sy - H / 2) / self.s
        self.cv.scale("e", sx, sy, f, f); self.cv.delete("g")       # imediat (rapid), apoi redesenare completă
        self._mai_tarziu()

    def deplaseaza(self, dx, dy):
        if self.foaie: self.fx += dx; self.fy += dy; self.cv.move("e", dx, dy); return
        self.cx -= dx / self.s; self.cy += dy / self.s; self.cv.move("e", dx, dy); self.cv.move("g", dx, dy)

    def _mai_tarziu(self, ms=140):
        if self._dupa: self.cv.after_cancel(self._dupa)
        self._dupa = self.cv.after(ms, self.deseneaza)

    # ---------------------------------------------------------------- desenare
    def deseneaza(self):
        self._dupa = None
        if self.foaie: return self._deseneaza_foaie()
        cv = self.cv; cv.delete("e"); cv.delete("g")
        W, H = self.wh()
        if self.grila: self._grila(W, H)
        s, cx, cy = self.s, self.cx, self.cy; W2, H2 = W / 2, H / 2
        x0w, y0w = self.lume(-50, H + 50); x1w, y1w = self.lume(W + 50, -50)
        sel = self.selectie; vis = {}
        for p in (q for l in self.ph.values() for q in l):
            st = p[-1]
            if st not in vis: vis[st] = self.strat_vizibil(st)
            if not vis[st]: continue
            tag = ("e", "h" + (p[7] if p[0] == "t" else p[3]))
            if p[0] == "t":
                _, x, y, txt, hgt, rot, cul, h, anc, _ = p
                if not (x0w - hgt * 40 <= x <= x1w + hgt * 40 and y0w - hgt * 40 <= y <= y1w + hgt * 40): continue
                px = hgt * s * 1.38
                if px < 3: continue
                if px > 900: px = 900
                cv.create_text((x - cx) * s + W2, H2 - (y - cy) * s, text=txt, fill=SELECT if h in sel else cul, anchor=anc,
                               angle=rot, font=(F, -int(px)), tags=tag)
                continue
            c = p[1]; xs = c[0::2]; ys = c[1::2]
            if max(xs) < x0w or min(xs) > x1w or max(ys) < y0w or min(ys) > y1w: continue
            pts = []
            for i in range(0, len(c), 2): pts += ((c[i] - cx) * s + W2, H2 - (c[i + 1] - cy) * s)
            col = SELECT if p[3] in sel else p[2]
            if p[0] == "pt": cv.create_oval(pts[0] - 2, pts[1] - 2, pts[0] + 2, pts[1] + 2, outline=col, tags=tag)
            elif p[4] and len(pts) >= 6: cv.create_polygon(pts, fill=col, outline=col, tags=tag)
            else: cv.create_line(pts, fill=col, width=2 if p[3] in sel else 1, dash=(6, 3) if p[3] in sel else None, tags=tag)
        if self.img: self._deseneaza_imagini(W, H)
        cv.tag_raise("ov"); cv.tag_raise("cur")

    def _grila(self, W, H):
        pas = 10 ** math.ceil(math.log10(14 / self.s)) if self.s > 0 else 1
        if pas * self.s > 70: pas /= 5
        x0, y1 = self.lume(0, 0); x1, y0 = self.lume(W, H)
        if (x1 - x0) / pas > 400: return
        k = math.floor(x0 / pas)
        while k * pas <= x1:
            sx, _ = self.ecran(k * pas, 0)
            self.cv.create_line(sx, 0, sx, H, fill=GRILA2 if k % 5 == 0 else GRILA, tags="g"); k += 1
        k = math.floor(y0 / pas)
        while k * pas <= y1:
            _, sy = self.ecran(0, k * pas)
            self.cv.create_line(0, sy, W, sy, fill=GRILA2 if k % 5 == 0 else GRILA, tags="g"); k += 1
        self.cv.tag_lower("g")
