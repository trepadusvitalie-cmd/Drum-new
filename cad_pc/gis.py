"""CAD PC – unelte ca în ArcGIS Pro: galeria hărților de fundal (Basemap), selecția cu formă (dreptunghi, poligon, lasou,
cerc, linie, traseu), «Выбор по атрибутам» (Select By Attributes) și «Выбор по расположению» (Select By Location)."""
import math, threading
import tkinter as tk
from tkinter import ttk, messagebox
from stil import *
from unelte import dialog, buton, eticheta, intrare, numar, Popup, Sfat
import geo


# ================================================================ geometria obiectelor (din primitivele desenate)
def segmente(v, h):
    """segmentele și punctele obiectului: ([(x0,y0,x1,y1)…], [(x,y)…], poligoane_inchise)"""
    seg, pts, pol = [], [], []
    for p in v.ph.get(h, ()):
        if p[0] == "t": pts.append((p[1], p[2])); continue
        c = p[1]; q = list(zip(c[0::2], c[1::2])); pts.extend(q)
        for i in range(len(q) - 1): seg.append((q[i][0], q[i][1], q[i + 1][0], q[i + 1][1]))
        if len(q) >= 3 and (p[4] or (abs(q[0][0] - q[-1][0]) < 1e-9 and abs(q[0][1] - q[-1][1]) < 1e-9)): pol.append(q)
    return seg, pts, pol


def in_poligon(x, y, q):
    ins = False; j = len(q) - 1
    for i in range(len(q)):
        xi, yi = q[i]; xj, yj = q[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-300) + xi: ins = not ins
        j = i
    return ins


def _se_taie(a, b):
    (x1, y1, x2, y2), (x3, y3, x4, y4) = a, b
    d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
    if abs(d) < 1e-15: return False
    t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d; u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
    return 0 <= t <= 1 and 0 <= u <= 1


def _dist_pt_seg(px, py, s):
    x1, y1, x2, y2 = s; dx, dy = x2 - x1, y2 - y1; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L))
    return math.hypot(px - x1 - t * dx, py - y1 - t * dy)


def _dist_seg_seg(a, b):
    if _se_taie(a, b): return 0.0
    return min(_dist_pt_seg(a[0], a[1], b), _dist_pt_seg(a[2], a[3], b), _dist_pt_seg(b[0], b[1], a), _dist_pt_seg(b[2], b[3], a))


def geom(v, h):
    seg, pts, pol = segmente(v, h)
    return dict(seg=seg, pts=pts, pol=pol, bb=v.bbox.get(h))


def distanta(A, B, limita=float("inf")):
    """distanța minimă dintre două geometrii (0 dacă se ating sau una e în interiorul celeilalte)"""
    for q in B["pol"]:
        if any(in_poligon(x, y, q) for x, y in A["pts"][:200]): return 0.0
    for q in A["pol"]:
        if any(in_poligon(x, y, q) for x, y in B["pts"][:200]): return 0.0
    best = float("inf")
    sa = A["seg"] or [(x, y, x, y) for x, y in A["pts"]]; sb = B["seg"] or [(x, y, x, y) for x, y in B["pts"]]
    for a in sa:
        for b in sb:
            d = _dist_seg_seg(a, b)
            if d < best:
                best = d
                if best <= limita: return best           # criteriul e deja îndeplinit
    return best


def _bb_aproape(a, b, d=0.0):
    return a and b and not (a[2] + d < b[0] or b[2] + d < a[0] or a[3] + d < b[1] or b[3] + d < a[1])


def aplica_metoda(ed, gasite, metoda):
    if metoda == "new": ed.sel = set(gasite)
    elif metoda == "add": ed.sel |= set(gasite)
    elif metoda == "remove": ed.sel -= set(gasite)
    else: ed.sel &= set(gasite)
    ed.arata_selectia(); ed.app.dupa_selectie()


METODE = [("Новая выборка", "new"), ("Добавить к текущей выборке", "add"), ("Удалить из текущей выборки", "remove"), ("Выбрать из текущей выборки", "subset")]


class Gis:
    def __init__(self, app): self.app = app; self.metoda_forma = "new"; self._lasou = None; self._legat = False

    @property
    def doc(self): return self.app.doc

    @property
    def ed(self): return self.app.ed

    # ================================================================ Basemap: galeria
    def galerie(self, w=None):
        app = self.app
        if not self.doc: return app.mesaj("Нет открытого чертежа.")
        d = dialog(app, "Базовая карта (Basemap)"); d.configure(bg="#f3f3f3")
        tk.Label(d, text="2D Базовая карта", bg="#f3f3f3", fg="#1b1b1b", font=(F, -14, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        fr = tk.Frame(d, bg="#f3f3f3"); fr.pack(padx=8, pady=4)
        cur = app.v.harta.sursa; self._miniaturi = {}
        nume = list(geo.SURSE) + ["Без базовой карты"]
        for i, n in enumerate(nume):
            c = tk.Frame(fr, bg="#cfe3ff" if n == cur else "#f3f3f3", padx=4, pady=4); c.grid(row=i // 4, column=i % 4, padx=4, pady=4)
            cv = tk.Canvas(c, width=150, height=100, bg="#dfe3e8", highlightthickness=1, highlightbackground="#bbb"); cv.pack()
            cv.create_text(75, 50, text="…" if n in geo.SURSE else "∅", fill="#888", font=(F, -16))
            tk.Label(c, text=n.split(" (")[0], bg=c["bg"], fg="#1b1b1b", font=(F, -12), wraplength=150).pack()
            for x in (c, cv) + tuple(c.winfo_children()):
                x.bind("<Button-1>", lambda e, n=n: (d.destroy(), self.alege_harta(n)))
            if n in geo.SURSE: self._miniatura(cv, n)
        tk.Label(d, text="Нужен интернет. Карта показывается под чертежом в системе MOLDREF99 и в DWG не сохраняется.\n" + geo.ATRIBUIRE,
                 bg="#f3f3f3", fg="#555", font=(F, -11), justify="left").pack(anchor="w", padx=12, pady=(4, 10))

    def _miniatura(self, cv, n):
        """miniatura = o placă reală cu Chișinăul (descărcată în fundal, apoi din cache)"""
        x, y = geo._tile_xy(47.02, 28.84, 12)
        def lucru():
            from PIL import Image
            im = None
            for st in geo.SURSE[n]:
                p = geo.placa(st, 12, int(x), int(y), timeout=10)
                if p is not None: im = p if im is None else geo.Image_alpha(im, p)
            self._miniaturi[n] = im
        threading.Thread(target=lucru, daemon=True).start()
        def verifica():
            if not cv.winfo_exists(): return
            if n not in self._miniaturi: return cv.after(200, verifica)
            im = self._miniaturi[n]; cv.delete("all")
            if im is None: return cv.create_text(75, 50, text="нет связи", fill="#888", font=(F, -11))
            from PIL import ImageTk
            f = ImageTk.PhotoImage(im.convert("RGB").crop((53, 78, 203, 178))); cv._f = f; cv.create_image(0, 0, image=f, anchor="nw")
        cv.after(200, verifica)

    def alege_harta(self, n):
        if n in geo.SURSE: self.app.v.harta.porneste(n); self.app.mesaj(f"Базовая карта: {n}. Колесо мыши – масштаб, карта догружается.")
        else: self.app.v.harta.opreste(); self.app.mesaj("Базовая карта выключена.")

    # ================================================================ Select ▾ (formă)
    def selecteaza(self, forma):
        if not self.doc: return
        nume = {"dreptunghi": "Прямоугольник", "poligon": "Полигон", "lasou": "Лассо", "cerc": "Круг", "linie": "Линия", "traseu": "Трасса"}[forma]
        if forma == "dreptunghi": return self.app.mesaj("Выбор прямоугольником: потяните рамку мышью (слева направо – внутри, справа налево – пересечение).")
        txt = {"poligon": "Укажите вершины полигона, Enter / правая кнопка – выбрать:", "lasou": "Нажмите и ведите мышью по контуру, отпустите – выбрать:",
               "cerc": "Центр круга:", "linie": "Начало линии:", "traseu": "Точки трассы, Enter / правая кнопка – выбрать:"}[forma]
        pts = []
        def deseneaza():
            cv = self.app.cv; cv.delete("prev")
            if len(pts) < 1: return
            sc = [c for p in pts for c in self.app.v.ecran(*p)]
            if forma == "cerc" and len(pts) == 2:
                (cx, cy), (px, py) = self.app.v.ecran(*pts[0]), self.app.v.ecran(*pts[1]); r = math.hypot(px - cx, py - cy)
                cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#00b4ff", width=2, tags="prev")
            elif len(sc) >= 4:
                cv.create_line(sc + (sc[:2] if forma in ("poligon", "lasou") else []), fill="#00b4ff", width=2, tags="prev")
        def gata():
            self.app.cv.delete("prev")
            if forma == "cerc":
                if len(pts) < 2: return
                (cx, cy), (px, py) = pts[0], pts[1]; r = math.hypot(px - cx, py - cy)
                forma_pts = [(cx + r * math.cos(a / 48 * 2 * math.pi), cy + r * math.sin(a / 48 * 2 * math.pi)) for a in range(48)]
                return self._selectie_poligon(forma_pts, nume)
            if forma in ("poligon", "lasou"):
                if len(pts) < 3: return self.app.mesaj("Нужно минимум 3 точки.")
                return self._selectie_poligon(pts, nume)
            if len(pts) < 2: return
            self._selectie_linie(pts, nume)
        def cb(p):
            pts.append(p); deseneaza()
            if forma in ("cerc", "linie") and len(pts) == 2: self.ed.opreste(""); gata()
            elif forma in ("cerc", "linie"): self.app.prompt("Радиус (вторая точка):" if forma == "cerc" else "Конец линии:")
        self.ed.incepe("REPETAT", f"ВЫБРАТЬ ({nume})  {txt}", nevoie_sel=False, rep=txt, cb=cb, fin=gata)
        if forma == "lasou":
            self._lasou = (pts, deseneaza, gata)
            if not self._legat:                            # o singură legătură pentru toate lasourile
                cv = self.app.cv; self._legat = True
                def misca(e):
                    if self._lasou and self._lasou[0]: self._lasou[0].append(self.app.v.lume(e.x, e.y)); self._lasou[1]()
                def elib(e):
                    if self._lasou and len(self._lasou[0]) > 2:
                        g = self._lasou[2]; self._lasou = None; self.app.root.after(10, lambda: (self.ed.opreste(""), g()))
                cv.bind("<B1-Motion>", misca, add="+"); cv.bind("<ButtonRelease-1>", elib, add="+")

    def _candidati(self, bb):
        v = self.app.v
        for h, b in v.bbox.items():
            if _bb_aproape(b, bb):
                e = self.ed.ent(h)
                if e is not None and not self.ed.blocat(e) and v.strat_vizibil(v.ph[h][0][-1] if v.ph.get(h) else "0"): yield h

    def _selectie_poligon(self, q, nume):
        bb = (min(x for x, _ in q), min(y for _, y in q), max(x for x, _ in q), max(y for _, y in q))
        laturi = [(q[i][0], q[i][1], q[(i + 1) % len(q)][0], q[(i + 1) % len(q)][1]) for i in range(len(q))]; gasite = set()
        for h in self._candidati(bb):
            seg, pts, _ = segmente(self.app.v, h)
            if any(in_poligon(x, y, q) for x, y in pts) or any(_se_taie(s, l) for s in seg for l in laturi): gasite.add(h)
        aplica_metoda(self.ed, gasite, self.metoda_forma); self.app.mesaj(f"Выбор ({nume}): {len(gasite)} объектов, всего выбрано {len(self.ed.sel)}.")

    def _selectie_linie(self, q, nume):
        bb = (min(x for x, _ in q), min(y for _, y in q), max(x for x, _ in q), max(y for _, y in q))
        traseu = [(q[i][0], q[i][1], q[i + 1][0], q[i + 1][1]) for i in range(len(q) - 1)]; tol = 3 / max(self.app.v.s, 1e-12); gasite = set()
        for h in self._candidati((bb[0] - tol, bb[1] - tol, bb[2] + tol, bb[3] + tol)):
            seg, pts, _ = segmente(self.app.v, h)
            if any(_se_taie(s, t) for s in seg for t in traseu) or any(_dist_pt_seg(x, y, t) <= tol for x, y in pts for t in traseu): gasite.add(h)
        aplica_metoda(self.ed, gasite, self.metoda_forma); self.app.mesaj(f"Выбор ({nume}): {len(gasite)} объектов, всего выбрано {len(self.ed.sel)}.")

    # ================================================================ Select By Attributes
    def campuri(self):
        tags = []
        for e in self.doc.modelspace().query("INSERT"):
            for a in e.attribs:
                if a.dxf.tag not in tags: tags.append(a.dxf.tag)
        return ["Слой", "Тип объекта", "Цвет (индекс)", "Имя блока", "Текст", "Длина", "Площадь"] + ["Атрибут: " + t for t in tags]

    def valoare(self, e, camp):
        t = e.dxftype()
        if camp == "Слой": return e.dxf.get("layer", "0")
        if camp == "Тип объекта": return t
        if camp == "Цвет (индекс)": return str(e.dxf.get("color", 256))
        if camp == "Имя блока": return e.dxf.name if t == "INSERT" else ""
        if camp == "Текст": return e.plain_text() if t == "MTEXT" else (e.dxf.text if t == "TEXT" else "")
        if camp in ("Длина", "Площадь"):
            seg, pts, pol = segmente(self.app.v, e.dxf.handle)
            if camp == "Длина": return sum(math.hypot(s[2] - s[0], s[3] - s[1]) for s in seg)
            return sum(abs(sum(q[i][0] * q[(i + 1) % len(q)][1] - q[(i + 1) % len(q)][0] * q[i][1] for i in range(len(q)))) / 2 for q in pol)
        if camp.startswith("Атрибут: ") and t == "INSERT":
            tag = camp[9:]
            for a in e.attribs:
                if a.dxf.tag == tag: return a.dxf.text
        return ""

    @staticmethod
    def conditie(val, op, tinta):
        def num(x):
            try: return float(str(x).replace(",", "."))
            except ValueError: return None
        s = str(val); t = str(tinta)
        if op == "равно": return s.lower() == t.lower() if num(val) is None or num(t) is None else abs(num(val) - num(t)) < 1e-9
        if op == "не равно": return not Gis.conditie(val, "равно", tinta)
        if op == "содержит": return t.lower() in s.lower()
        if op == "не содержит": return t.lower() not in s.lower()
        if op == "начинается с": return s.lower().startswith(t.lower())
        if op == "заканчивается на": return s.lower().endswith(t.lower())
        if op == "пусто": return not s.strip()
        if op == "не пусто": return bool(s.strip())
        a, b = num(val), num(t)
        if a is None or b is None: return False
        return {">": a > b, "<": a < b, ">=": a >= b, "<=": a <= b}[op]

    def dupa_atribute(self):
        app = self.app
        if not self.doc: return
        d = dialog(app, "Выбор по атрибутам (Select By Attributes)"); campuri = self.campuri()
        tk.Label(d, text="Входные строки: все объекты пространства модели", bg=CORP, fg=TEXT, font=F_MIC).grid(row=0, column=0, columnspan=4, sticky="w", padx=6, pady=4)
        eticheta(d, "Тип выбора:", 1, 0); cm = ttk.Combobox(d, values=[m[0] for m in METODE], state="readonly", width=30); cm.set(METODE[0][0]); cm.grid(row=1, column=1, columnspan=3, sticky="w", padx=6)
        fr = tk.Frame(d, bg=CORP); fr.grid(row=2, column=0, columnspan=4, sticky="w", padx=6, pady=6)
        OPS = ["равно", "не равно", "содержит", "не содержит", "начинается с", "заканчивается на", ">", "<", ">=", "<=", "пусто", "не пусто"]
        clauze = []
        def adauga():
            r = len(clauze)
            leg = ttk.Combobox(fr, values=["И", "ИЛИ"], state="readonly", width=5); leg.set("И")
            if r: leg.grid(row=r, column=0, padx=2, pady=2)
            cc = ttk.Combobox(fr, values=campuri, state="readonly", width=22); cc.set(campuri[0]); cc.grid(row=r, column=1, padx=2)
            co = ttk.Combobox(fr, values=OPS, state="readonly", width=16); co.set("равно"); co.grid(row=r, column=2, padx=2)
            cv = ttk.Combobox(fr, width=26); cv.grid(row=r, column=3, padx=2)
            def valori(e=None):
                vals = sorted({str(self.valoare(x, cc.get()))[:80] for x in list(self.doc.modelspace())[:20000]} - {""})[:500]
                cv["values"] = vals
            cc.bind("<<ComboboxSelected>>", valori); cv.bind("<Button-1>", lambda e: valori() if not cv["values"] else None)
            clauze.append((leg, cc, co, cv))
        adauga()
        sql = tk.Label(d, text="", bg="#2b313a", fg="#9fd0ff", font=("Consolas", -12), anchor="w", justify="left", wraplength=560); sql.grid(row=3, column=0, columnspan=4, sticky="we", padx=6, pady=4)
        def expresie():
            return " ".join(((l.get() + " ") if i else "") + f"{c.get()} {o.get()} '{v.get()}'" for i, (l, c, o, v) in enumerate(clauze))
        def verifica_expr(): sql.config(text=expresie())
        def ruleaza(inchide):
            gasite = set()
            for e in self.doc.modelspace():
                rez = None
                for i, (l, c, o, v) in enumerate(clauze):
                    r = self.conditie(self.valoare(e, c.get()), o.get(), v.get())
                    rez = r if i == 0 else (rez and r if l.get() == "И" else rez or r)
                if rez and not self.ed.blocat(e): gasite.add(e.dxf.handle)
            metoda = dict(METODE)[cm.get()]; aplica_metoda(self.ed, gasite, metoda); verifica_expr()
            app.mesaj(f"Выбор по атрибутам: {expresie()} → найдено {len(gasite)}, выбрано {len(self.ed.sel)}.")
            if inchide: d.destroy()
        f = tk.Frame(d, bg=CORP); f.grid(row=4, column=0, columnspan=4, sticky="we", padx=6, pady=8)
        buton(f, "＋ Добавить условие", adauga).pack(side="left", padx=2); buton(f, "Проверить выражение", verifica_expr).pack(side="left", padx=2)
        buton(f, "OK", lambda: ruleaza(True), bg=ALBASTRU).pack(side="right", padx=2); buton(f, "Применить", lambda: ruleaza(False)).pack(side="right", padx=2)

    # ================================================================ Select By Location
    def dupa_locatie(self):
        app = self.app
        if not self.doc: return
        d = dialog(app, "Выбор по расположению (Select By Location)"); straturi = sorted(l.dxf.name for l in self.doc.layers)
        eticheta(d, "Входные объекты (слои):", 0, 0)
        lb_in = tk.Listbox(d, selectmode="multiple", height=8, width=34, exportselection=False, bg="#2b313a", fg=TEXT, selectbackground=ACTIV)
        lb_in.grid(row=1, column=0, padx=6, pady=2, sticky="n")
        for s in ["<Все слои>"] + straturi: lb_in.insert("end", s)
        lb_in.selection_set(0)
        eticheta(d, "Отношение:", 0, 1)
        REL = ["Пересекаются", "В пределах расстояния", "Полностью внутри", "Полностью содержат"]
        cr = ttk.Combobox(d, values=REL, state="readonly", width=26); cr.set(REL[0]); cr.grid(row=1, column=1, sticky="nw", padx=6)
        eticheta(d, "Расстояние поиска (ед. чертежа):", 2, 1); ed_d = intrare(d, 0, 3, 1)
        eticheta(d, "Выбирающие объекты:", 2, 0)
        surse = ["<Текущая выборка>"] + straturi
        cs = ttk.Combobox(d, values=surse, state="readonly", width=32); cs.set(surse[0] if self.ed.sel else (straturi[0] if straturi else "")); cs.grid(row=3, column=0, sticky="w", padx=6)
        eticheta(d, "Тип выбора:", 4, 0); cm = ttk.Combobox(d, values=[m[0] for m in METODE], state="readonly", width=30); cm.set(METODE[0][0]); cm.grid(row=4, column=1, sticky="w", padx=6)
        v_inv = tk.BooleanVar(value=False)
        tk.Checkbutton(d, text="Инвертировать пространственное отношение", variable=v_inv, bg=CORP, fg=TEXT, selectcolor="#2b313a", activebackground=CORP, font=F_MIC).grid(row=5, column=0, columnspan=2, sticky="w", padx=4)
        def ruleaza():
            v = app.v; ms = self.doc.modelspace(); alese = [lb_in.get(i) for i in lb_in.curselection()]
            toate = "<Все слои>" in alese or not alese
            if cs.get() == "<Текущая выборка>": sursa_h = set(self.ed.sel)
            else: sursa_h = {e.dxf.handle for e in ms if e.dxf.get("layer", "0") == cs.get()}
            if not sursa_h: return messagebox.showinfo("Выбор по расположению", "Нет выбирающих объектов.", parent=d)
            rel = cr.get(); dist = numar(ed_d, 0) if rel == "В пределах расстояния" else 0.0
            S = {h: geom(v, h) for h in sursa_h if v.bbox.get(h)}
            gasite = set(); intrari = [e for e in ms if (toate or e.dxf.get("layer", "0") in alese) and not self.ed.blocat(e)]
            app.root.config(cursor="watch"); app.root.update_idletasks()
            try:
                for e in intrari:
                    h = e.dxf.handle; b = v.bbox.get(h)
                    if not b: continue
                    A = None; ok = False
                    for hs, B in S.items():
                        if hs == h or not _bb_aproape(b, B["bb"], dist): continue
                        A = A or geom(v, h)
                        if rel in ("Пересекаются", "В пределах расстояния"): ok = distanta(A, B, dist + 1e-9) <= dist + 1e-9
                        elif rel == "Полностью внутри": ok = bool(B["pol"]) and all(any(in_poligon(x, y, q) for q in B["pol"]) for x, y in A["pts"])
                        else: ok = bool(A["pol"]) and all(any(in_poligon(x, y, q) for q in A["pol"]) for x, y in B["pts"])
                        if ok: break
                    if ok != v_inv.get(): gasite.add(h)
            finally: app.root.config(cursor="")
            aplica_metoda(self.ed, gasite, dict(METODE)[cm.get()]); d.destroy()
            app.mesaj(f"Выбор по расположению: «{rel}»{' ' + str(dist) if dist else ''} → найдено {len(gasite)}, выбрано {len(self.ed.sel)}.")
        f = tk.Frame(d, bg=CORP); f.grid(row=6, column=0, columnspan=2, sticky="e", padx=6, pady=8)
        buton(f, "OK", ruleaza, bg=ALBASTRU).pack(side="right", padx=2); buton(f, "Отмена", d.destroy).pack(side="right", padx=2)
