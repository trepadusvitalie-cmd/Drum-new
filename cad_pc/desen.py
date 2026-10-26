"""CAD PC 3.3 – comenzi de desenare și cote: cerc (6 moduri), arc (11 moduri), nor de revizie, inel, spline, dreaptă / rază,
punct, împărțire / marcare, racordare / teșire / îmbinare, masive, cote (liniară, aliniată, rază, diametru, continuă, de bază)."""
import math
import tkinter as tk
from tkinter import simpledialog, messagebox
from ezdxf.math import Vec2, Matrix44


def _d(a, b): return math.hypot(b[0] - a[0], b[1] - a[1])
def _ang(c, p): return math.degrees(math.atan2(p[1] - c[1], p[0] - c[0])) % 360


def cerc3(a, b, c):
    ax, ay = a; bx, by = b; cx, cy = c; d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-12: return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / d
    return (ux, uy), _d((ux, uy), a)


def _intersectie(p1, d1, p2, d2):
    cr = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(cr) < 1e-12: return None
    t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / cr
    return (p1[0] + d1[0] * t, p1[1] + d1[1] * t)


def _ccw_intre(a0, a, a1):
    """a se află pe arcul care merge în sens trigonometric de la a0 la a1?"""
    return (a - a0) % 360 <= (a1 - a0) % 360


class Desen:
    def __init__(self, app):
        self.app = app; self.raza_racord = 0.0; self.tesire = (1.0, 1.0); self.ultima_cota = None

    @property
    def doc(self): return self.app.doc

    @property
    def ed(self): return self.app.ed

    def _at(self): return {"layer": self.app.strat_curent()}

    def _gata(self, ents, msg):
        self.ed.gata_modificare(msg); self.app.marcheaza(); return ents

    def _puncte(self, prompturi, cb, numere=False):
        self.ed.incepe("PUNCTE", prompturi[0], nevoie_sel=False, n=len(prompturi), prompturi=prompturi, cb=cb, numere=numere)

    def _linie_la(self, p):
        """obiectul LINE / LWPOLYLINE de sub punctul dat → ((x0, y0), (x1, y1), entitate, index segment)"""
        sx, sy = self.app.v.ecran(*p); h = self.ed.la_entitate(sx, sy); e = self.ed.ent(h) if h else None
        if e is None: return None
        if e.dxftype() == "LINE": return (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y), e, None
        if e.dxftype() == "LWPOLYLINE":
            pts = [(x, y) for x, y, *_ in e.get_points()]
            if e.closed: pts.append(pts[0])
            best = None
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]; dx, dy = b[0] - a[0], b[1] - a[1]; L = dx * dx + dy * dy or 1e-12
                t = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L)); q = (a[0] + dx * t, a[1] + dy * t); dd = _d(q, p)
                if best is None or dd < best[0]: best = (dd, a, b, i)
            if best: return best[1], best[2], e, best[3]
        return None

    # ================================================================ КРУГ (6 moduri)
    def cerc(self, mod):
        if not self.doc: return
        msp = self.doc.modelspace()
        def pune(c, r, msg="Круг"):
            if r is None or r <= 0: return self.app.mesaj("Круг не построен.")
            self.ed.instantaneu([]); e = msp.add_circle(c, r, dxfattribs=self._at()); self._gata([e], f"{msg}: центр {c[0]:.3f},{c[1]:.3f}  R = {r:.4f}")
        if mod == "ЦР": return self.app.executa("КРУГ")
        if mod == "ЦД": return self._puncte(["КРУГ  Центр:", "Диаметр (точка или число):"], lambda p: pune(p[0], (p[1] if isinstance(p[1], float) else _d(*p) ) / 2), True)
        if mod == "2Т": return self._puncte(["КРУГ  Первая конечная точка диаметра:", "Вторая конечная точка диаметра:"],
                                            lambda p: pune(((p[0][0] + p[1][0]) / 2, (p[0][1] + p[1][1]) / 2), _d(*p) / 2))
        if mod == "3Т":
            def cb(p):
                r = cerc3(*p); pune(r[0], r[1]) if r else self.app.mesaj("Точки на одной прямой.")
            return self._puncte(["КРУГ  Первая точка:", "Вторая точка:", "Третья точка:"], cb)
        if mod == "ККР":
            def cb(p):
                l1, l2 = self._linie_la(p[0]), self._linie_la(p[1])
                if not l1 or not l2: return self.app.mesaj("Укажите два отрезка (касательные).")
                r = simpledialog.askfloat("Круг", "Радиус круга:", parent=self.app.root, minvalue=1e-9)
                if not r: return
                c = self._centru_tangent(l1, l2, r, p)
                pune(c, r, "Круг (кас., кас., радиус)") if c else self.app.mesaj("Отрезки параллельны.")
            return self._puncte(["КРУГ  Точка на первом объекте касания:", "Точка на втором объекте касания:"], cb)
        if mod == "3К":
            def cb(p):
                ls = [self._linie_la(q) for q in p]
                if not all(ls): return self.app.mesaj("Укажите три отрезка.")
                c, r = self._cerc_3tangente(ls, p)
                pune(c, r, "Круг (3 касания)") if c else self.app.mesaj("Круг не найден.")
            return self._puncte(["КРУГ  Первый объект касания:", "Второй объект касания:", "Третий объект касания:"], cb)

    def _centru_tangent(self, l1, l2, r, picks):
        (a1, b1), (a2, b2) = l1[:2], l2[:2]
        d1 = (b1[0] - a1[0], b1[1] - a1[1]); d2 = (b2[0] - a2[0], b2[1] - a2[1])
        n1 = Vec2(-d1[1], d1[0]).normalize(); n2 = Vec2(-d2[1], d2[0]).normalize()
        best = None; tinta = ((picks[0][0] + picks[1][0]) / 2, (picks[0][1] + picks[1][1]) / 2)
        for s1 in (1, -1):
            for s2 in (1, -1):
                c = _intersectie((a1[0] + n1.x * r * s1, a1[1] + n1.y * r * s1), d1, (a2[0] + n2.x * r * s2, a2[1] + n2.y * r * s2), d2)
                if c and (best is None or _d(c, tinta) < best[0]): best = (_d(c, tinta), c)
        return best[1] if best else None

    def _cerc_3tangente(self, ls, picks):
        dirs = [(l[1][0] - l[0][0], l[1][1] - l[0][1]) for l in ls]
        A = _intersectie(ls[1][0], dirs[1], ls[2][0], dirs[2]); B = _intersectie(ls[0][0], dirs[0], ls[2][0], dirs[2]); C = _intersectie(ls[0][0], dirs[0], ls[1][0], dirs[1])
        if not (A and B and C): return None, None
        a, b, c = _d(B, C), _d(A, C), _d(A, B); tinta = (sum(p[0] for p in picks) / 3, sum(p[1] for p in picks) / 3); best = None
        for sa, sb, sc in ((1, 1, 1), (-1, 1, 1), (1, -1, 1), (1, 1, -1)):
            s = sa * a + sb * b + sc * c
            if abs(s) < 1e-12: continue
            o = ((sa * a * A[0] + sb * b * B[0] + sc * c * C[0]) / s, (sa * a * A[1] + sb * b * B[1] + sc * c * C[1]) / s)
            p0, d0 = ls[0][0], dirs[0]; r = abs((o[0] - p0[0]) * d0[1] - (o[1] - p0[1]) * d0[0]) / math.hypot(*d0)
            if best is None or _d(o, tinta) < best[0]: best = (_d(o, tinta), o, r)
        return (best[1], best[2]) if best else (None, None)

    # ================================================================ ДУГА (11 moduri)
    def arc(self, mod):
        if not self.doc: return
        def pune(c, r, a0, a1):
            if r is None or r <= 0: return self.app.mesaj("Дуга не построена.")
            self.ed.instantaneu([]); e = self.doc.modelspace().add_arc(c, r, a0 % 360, a1 % 360, dxfattribs=self._at())
            self._gata([e], f"Дуга: R = {r:.4f}, длина = {math.radians((a1 - a0) % 360) * r:.4f}")
        def val(x, c=None, impl="ang"):
            if isinstance(x, float): return x
            return _ang(c, x) if impl == "ang" else _d(c, x)
        def se_unghi(s, e, A):
            A = math.radians(A); ch = _d(s, e)
            if abs(math.sin(A / 2)) < 1e-12: return self.app.mesaj("Неверный угол.")
            r = ch / (2 * math.sin(A / 2)); m = ((s[0] + e[0]) / 2, (s[1] + e[1]) / 2); h = r * math.cos(A / 2)
            ux, uy = (e[0] - s[0]) / ch, (e[1] - s[1]) / ch; c = (m[0] - uy * h, m[1] + ux * h)
            pune(c, abs(r), _ang(c, s), _ang(c, e)) if r > 0 else pune(c, abs(r), _ang(c, e), _ang(c, s))
        def se_dir(s, e, dvec):
            n = (-dvec[1], dvec[0]); c = _intersectie(s, n, ((s[0] + e[0]) / 2, (s[1] + e[1]) / 2), (-(e[1] - s[1]), e[0] - s[0]))
            if not c: return self.app.mesaj("Дуга не построена.")
            r = _d(c, s); cr = dvec[0] * (c[1] - s[1]) - dvec[1] * (c[0] - s[0])
            pune(c, r, _ang(c, s), _ang(c, e)) if cr > 0 else pune(c, r, _ang(c, e), _ang(c, s))
        P = self._puncte
        if mod == "3Т":
            def cb(p):
                r = cerc3(*p)
                if not r: return self.app.mesaj("Точки на одной прямой.")
                c, R = r; a0, a1, a2 = _ang(c, p[0]), _ang(c, p[1]), _ang(c, p[2])
                pune(c, R, a0, a2) if _ccw_intre(a0, a1, a2) else pune(c, R, a2, a0)
            return P(["ДУГА  Начальная точка:", "Вторая точка:", "Конечная точка:"], cb)
        if mod == "НЦК": return P(["ДУГА  Начальная точка:", "Центр:", "Конечная точка:"], lambda p: pune(p[1], _d(p[1], p[0]), _ang(p[1], p[0]), _ang(p[1], p[2])))
        if mod == "НЦУ": return P(["ДУГА  Начальная точка:", "Центр:", "Центральный угол (число или точка):"],
                                   lambda p: pune(p[1], _d(p[1], p[0]), _ang(p[1], p[0]), _ang(p[1], p[0]) + (p[2] if isinstance(p[2], float) else (_ang(p[1], p[2]) - _ang(p[1], p[0])) % 360)), True)
        if mod == "НЦД":
            def cb(p):
                r = _d(p[1], p[0]); L = val(p[2], p[0], "d")
                if L > 2 * r: return self.app.mesaj("Хорда длиннее диаметра.")
                a0 = _ang(p[1], p[0]); pune(p[1], r, a0, a0 + math.degrees(2 * math.asin(L / (2 * r))))
            return P(["ДУГА  Начальная точка:", "Центр:", "Длина хорды (число или точка):"], cb, True)
        if mod == "НКУ": return P(["ДУГА  Начальная точка:", "Конечная точка:", "Центральный угол (число или точка):"],
                                   lambda p: se_unghi(p[0], p[1], p[2] if isinstance(p[2], float) else _ang(p[0], p[2])), True)
        if mod == "НКН": return P(["ДУГА  Начальная точка:", "Конечная точка:", "Направление касательной в начальной точке:"],
                                   lambda p: se_dir(p[0], p[1], (p[2][0] - p[0][0], p[2][1] - p[0][1])))
        if mod == "НКР":
            def cb(p):
                R = val(p[2], p[1], "d"); ch = _d(p[0], p[1])
                if R < ch / 2: return self.app.mesaj("Радиус меньше половины хорды.")
                se_unghi(p[0], p[1], math.degrees(2 * math.asin(ch / (2 * R))))
            return P(["ДУГА  Начальная точка:", "Конечная точка:", "Радиус (число или точка):"], cb, True)
        if mod == "ЦНК": return P(["ДУГА  Центр:", "Начальная точка:", "Конечная точка:"], lambda p: pune(p[0], _d(p[0], p[1]), _ang(p[0], p[1]), _ang(p[0], p[2])))
        if mod == "ЦНУ": return P(["ДУГА  Центр:", "Начальная точка:", "Центральный угол (число или точка):"],
                                   lambda p: pune(p[0], _d(p[0], p[1]), _ang(p[0], p[1]), _ang(p[0], p[1]) + (p[2] if isinstance(p[2], float) else (_ang(p[0], p[2]) - _ang(p[0], p[1])) % 360)), True)
        if mod == "ЦНД":
            def cb(p):
                r = _d(p[0], p[1]); L = val(p[2], p[1], "d")
                if L > 2 * r: return self.app.mesaj("Хорда длиннее диаметра.")
                a0 = _ang(p[0], p[1]); pune(p[0], r, a0, a0 + math.degrees(2 * math.asin(L / (2 * r))))
            return P(["ДУГА  Центр:", "Начальная точка:", "Длина хорды (число или точка):"], cb, True)
        if mod == "ПРОД":
            ult = None
            for e in self.doc.modelspace():
                if e.dxftype() in ("LINE", "ARC"): ult = e
            if ult is None: return self.app.mesaj("Нет отрезка или дуги для продолжения.")
            if ult.dxftype() == "LINE": s = (ult.dxf.end.x, ult.dxf.end.y); d = (ult.dxf.end.x - ult.dxf.start.x, ult.dxf.end.y - ult.dxf.start.y)
            else:
                c = ult.dxf.center; a = math.radians(ult.dxf.end_angle); s = (c.x + ult.dxf.radius * math.cos(a), c.y + ult.dxf.radius * math.sin(a)); d = (-math.sin(a), math.cos(a))
            return P(["ДУГА (продолжение)  Конечная точка:"], lambda p: se_dir(s, p[0], d))

    # ================================================================ alte obiecte de desen
    def nor(self, mod):
        if not self.doc: return
        def construieste(pts, inchis=True):
            L = max(_d(pts[0], pts[1]) / 8, 16 / max(self.app.v.s, 1e-9)) if len(pts) > 1 else 1
            pv = []; seq = pts + ([pts[0]] if inchis else [])
            for i in range(len(seq) - 1):
                a, b = seq[i], seq[i + 1]; n = max(1, int(_d(a, b) / L))
                for k in range(n): pv.append((a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n, 0, 0, -0.5))
            arie = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
            if arie < 0: pv = [(x, y, 0, 0, 0.5) for x, y, *_ in pv]
            self.ed.instantaneu([]); e = self.doc.modelspace().add_lwpolyline(pv, format="xyseb", close=inchis, dxfattribs=self._at())
            self._gata([e], "Облако для пометок создано.")
        if mod == "ПРЯМ":
            return self._puncte(["ОБЛАКО  Первый угол:", "Противоположный угол:"],
                                lambda p: construieste([p[0], (p[1][0], p[0][1]), p[1], (p[0][0], p[1][1])]))
        pts = []
        def adauga(p): pts.append(p)
        def fin():
            if len(pts) >= 3: construieste(pts)
            else: self.app.mesaj("Нужно минимум 3 точки.")
        txt = "ОБЛАКО  Укажите точку (Enter – замкнуть):" if mod == "МНОГ" else "ОБЛАКО (от руки)  Ведите по точкам, Enter – замкнуть:"
        self.ed.incepe("REPETAT", txt, nevoie_sel=False, rep=txt, cb=adauga, fin=fin)

    def inel(self):
        if not self.doc: return
        di = simpledialog.askfloat("Кольцо", "Внутренний диаметр:", initialvalue=0.5, parent=self.app.root, minvalue=0)
        if di is None: return
        de = simpledialog.askfloat("Кольцо", "Внешний диаметр:", initialvalue=1.0, parent=self.app.root, minvalue=1e-9)
        if not de: return
        r = (di + de) / 4; w = (de - di) / 2
        def pune(p):
            self.ed.instantaneu([])
            e = self.doc.modelspace().add_lwpolyline([(p[0] - r, p[1], w, w, 1), (p[0] + r, p[1], w, w, 1)], format="xyseb", close=True, dxfattribs=self._at())
            self._gata([e], "Кольцо.")
        self.ed.incepe("REPETAT", "КОЛЬЦО  Центр (Esc – конец):", nevoie_sel=False, rep="Центр кольца (Esc – конец):", cb=pune)

    def spline(self):
        pts = []
        def fin():
            if len(pts) < 2: return
            self.ed.instantaneu([]); e = self.doc.modelspace().add_spline(pts, dxfattribs=self._at()); self._gata([e], "Сплайн.")
        self.ed.incepe("REPETAT", "СПЛАЙН  Точки (Enter – конец):", nevoie_sel=False, rep="Следующая точка (Enter – конец):", cb=pts.append, fin=fin)

    def dreapta(self, raza=False):
        st = {}
        def cb(p):
            if "a" not in st: st["a"] = p; return
            a = st["a"]; d = (p[0] - a[0], p[1] - a[1]); L = math.hypot(*d) or 1; u = (d[0] / L, d[1] / L, 0)
            self.ed.instantaneu([]); msp = self.doc.modelspace()
            e = msp.add_ray(a, u, dxfattribs=self._at()) if raza else msp.add_xline(a, u, dxfattribs=self._at())
            self._gata([e], "Луч." if raza else "Прямая.")
        n = "ЛУЧ" if raza else "ПРЯМАЯ"
        self.ed.incepe("REPETAT", f"{n}  Начальная точка, затем точки направления (Esc – конец):", nevoie_sel=False, rep="Укажите точку (Esc – конец):", cb=cb)

    def punct(self):
        def cb(p):
            self.ed.instantaneu([]); e = self.doc.modelspace().add_point(p, dxfattribs=self._at()); self._gata([e], f"Точка {p[0]:.3f}, {p[1]:.3f}")
        self.ed.incepe("REPETAT", "ТОЧКА  Укажите точку (Esc – конец):", nevoie_sel=False, rep="Укажите точку (Esc – конец):", cb=cb)

    def imparte(self, masura=False):
        """ДЕЛИТЬ / РАЗМЕТИТЬ: puncte pe obiectul selectat, la distanțe egale"""
        from ezdxf import path as ezpath
        ents = [self.ed.ent(h) for h in self.ed.sel if self.ed.ent(h) is not None]
        if len(ents) != 1: return self.app.mesaj("Выберите один объект (отрезок, полилинию, дугу, круг, сплайн), затем команду.")
        try: pts = [Vec2(v) for v in ezpath.make_path(ents[0]).flattening(0.005)]
        except Exception: return self.app.mesaj("Этот объект нельзя разделить.")
        L = sum((pts[i + 1] - pts[i]).magnitude for i in range(len(pts) - 1))
        if masura:
            d = simpledialog.askfloat("Разметить", f"Длина сегмента (длина объекта {L:.3f}):", parent=self.app.root, minvalue=1e-9)
            if not d: return
            dist = [d * k for k in range(1, int(L / d) + 1) if d * k < L - 1e-9]
        else:
            n = simpledialog.askinteger("Делить", "Число сегментов:", initialvalue=4, parent=self.app.root, minvalue=2, maxvalue=10000)
            if not n: return
            dist = [L * k / n for k in range(1, n)]
        self.ed.instantaneu([]); msp = self.doc.modelspace(); acc = 0; i = 0; noi = []
        for t in dist:
            while i < len(pts) - 1 and acc + (pts[i + 1] - pts[i]).magnitude < t: acc += (pts[i + 1] - pts[i]).magnitude; i += 1
            if i >= len(pts) - 1: break
            seg = pts[i + 1] - pts[i]; q = pts[i] + seg.normalize() * (t - acc) if seg.magnitude else pts[i]
            noi.append(msp.add_point((q.x, q.y), dxfattribs=self._at()))
        self._gata(noi, f"Поставлено точек: {len(noi)} (стиль точек – «Отображение точек»).")

    # ================================================================ СОПРЯЖЕНИЕ / ФАСКА / СОЕДИНЕНИЕ КРИВЫХ
    def racord(self, mod="R"):
        if not self.doc: return
        nume = {"R": "СОПРЯЖЕНИЕ", "F": "ФАСКА", "S": "СОЕДИНЕНИЕ"}[mod]
        if mod == "R": txt = f"{nume}  Радиус = {self.raza_racord:g}. Введите новый радиус или укажите первый отрезок:"
        elif mod == "F": txt = f"{nume}  Длины = {self.tesire[0]:g}, {self.tesire[1]:g}. Введите длину или укажите первый отрезок:"
        else: txt = f"{nume}  Первый объект (у конца, который соединить):"
        st = {"p": []}
        def nr(v):
            if mod == "R": self.raza_racord = v
            elif mod == "F": self.tesire = (v, v)
            self.app.mesaj(f"{nume}: значение {v:g}. Укажите первый отрезок:")
        def cb(p):
            st["p"].append(p)
            if len(st["p"]) < 2: return self.app.mesaj("Укажите второй объект:")
            self.ed.opreste("Готово."); self._racord(mod, *st["p"])
        self.ed.incepe("REPETAT", txt, nevoie_sel=False, rep="Укажите объект:", cb=cb, numar=nr)

    def _racord(self, mod, p1, p2):
        l1, l2 = self._linie_la(p1), self._linie_la(p2)
        if not l1 or not l2 or l1[2] is l2[2] and l1[3] == l2[3]: return self.app.mesaj("Нужны два разных отрезка.")
        if l1[2].dxftype() != "LINE" or l2[2].dxftype() != "LINE": return self.app.mesaj("Сопряжение/фаска выполняются для отрезков (LINE). Полилинии – расчлените (РАСЧЛЕНИТЬ).")
        (a1, b1, e1, _), (a2, b2, e2, _) = l1, l2
        d1 = (b1[0] - a1[0], b1[1] - a1[1]); d2 = (b2[0] - a2[0], b2[1] - a2[1]); I = _intersectie(a1, d1, a2, d2)
        msp = self.doc.modelspace(); self.ed.instantaneu([e1.dxf.handle, e2.dxf.handle])
        def capat_pastrat(a, b, p):                    # capătul care rămâne: cel de partea punctului ales
            return a if _d(a, p) > _d(b, p) and _d(a, I) > 1e-9 and ((a[0] - I[0]) * (p[0] - I[0]) + (a[1] - I[1]) * (p[1] - I[1])) > 0 or _d(b, I) < 1e-9 else b
        if mod == "S" or I is None:
            q1 = min((a1, b1), key=lambda q: _d(q, p2)); q2 = min((a2, b2), key=lambda q: _d(q, p1))
            e = msp.add_spline([q1, ((q1[0] + q2[0]) / 2, (q1[1] + q2[1]) / 2), q2], dxfattribs=self._at())
            return self._gata([e], "Соединение кривых.")
        k1 = a1 if _d(a1, I) >= _d(b1, I) else b1; k2 = a2 if _d(a2, I) >= _d(b2, I) else b2
        u1 = Vec2(k1[0] - I[0], k1[1] - I[1]).normalize(); u2 = Vec2(k2[0] - I[0], k2[1] - I[1]).normalize()
        def seteaza(e, k, nou):
            e.dxf.start = (k[0], k[1]); e.dxf.end = (nou[0], nou[1])
        if mod == "F":
            t1 = (I[0] + u1.x * self.tesire[0], I[1] + u1.y * self.tesire[0]); t2 = (I[0] + u2.x * self.tesire[1], I[1] + u2.y * self.tesire[1])
            seteaza(e1, k1, t1); seteaza(e2, k2, t2); e = msp.add_line(t1, t2, dxfattribs=self._at())
            return self._gata([e], f"Фаска {self.tesire[0]:g} × {self.tesire[1]:g}.")
        r = self.raza_racord
        if r <= 1e-12:
            seteaza(e1, k1, I); seteaza(e2, k2, I); return self._gata([], "Отрезки соединены в углу (радиус 0).")
        unghi = math.acos(max(-1, min(1, u1.x * u2.x + u1.y * u2.y)))
        if unghi < 1e-6 or abs(unghi - math.pi) < 1e-6: return self.app.mesaj("Отрезки параллельны.")
        t = r / math.tan(unghi / 2); T1 = (I[0] + u1.x * t, I[1] + u1.y * t); T2 = (I[0] + u2.x * t, I[1] + u2.y * t)
        bis = (u1 + u2).normalize(); c = (I[0] + bis.x * r / math.sin(unghi / 2), I[1] + bis.y * r / math.sin(unghi / 2))
        seteaza(e1, k1, T1); seteaza(e2, k2, T2)
        a0, a1_ = _ang(c, T1), _ang(c, T2)
        if (a1_ - a0) % 360 > 180: a0, a1_ = a1_, a0
        e = msp.add_arc(c, r, a0, a1_, dxfattribs=self._at()); self._gata([e], f"Сопряжение R = {r:g}.")

    # ================================================================ МАССИВ
    def masiv(self, tip):
        if not self.ed.sel: return self.app.mesaj("Выберите объекты, затем «Массив».")
        r = self.app.root
        if tip == "ПРЯМ":
            nr = simpledialog.askinteger("Прямоугольный массив", "Строк:", initialvalue=3, parent=r, minvalue=1)
            nc = simpledialog.askinteger("Прямоугольный массив", "Столбцов:", initialvalue=4, parent=r, minvalue=1) if nr else None
            if not nc: return
            b = self._cutie_sel(); dx = simpledialog.askfloat("Прямоугольный массив", "Расстояние между столбцами:", initialvalue=round((b[2] - b[0]) * 1.5 or 10, 3), parent=r)
            dy = simpledialog.askfloat("Прямоугольный массив", "Расстояние между строками:", initialvalue=round((b[3] - b[1]) * 1.5 or 10, 3), parent=r) if dx is not None else None
            if dy is None: return
            return self._copii([Matrix44.translate(j * dx, i * dy, 0) for i in range(nr) for j in range(nc) if i or j], f"Массив {nr} × {nc}.")
        if tip == "КРУГ":
            def cb(p):
                n = simpledialog.askinteger("Круговой массив", "Число элементов:", initialvalue=6, parent=r, minvalue=2)
                if not n: return
                a = simpledialog.askfloat("Круговой массив", "Угол заполнения (градусы):", initialvalue=360, parent=r)
                if a is None: return
                pas = a / n if abs(a) >= 360 else a / (n - 1)
                ms = [Matrix44.translate(-p[0], -p[1], 0) @ Matrix44.z_rotate(math.radians(pas * k)) @ Matrix44.translate(p[0], p[1], 0) for k in range(1, n)]
                self._copii(ms, f"Круговой массив: {n} элементов.")
            return self.ed.incepe("PUNCT", "МАССИВКРУГ  Центр массива:", nevoie_sel=False, cb=cb)
        if tip == "ТРАЕКТ":
            def cb(p):
                from ezdxf import path as ezpath
                sx, sy = self.app.v.ecran(*p); h = self.ed.la_entitate(sx, sy); e = self.ed.ent(h) if h else None
                if e is None: return self.app.mesaj("Траектория не найдена.")
                n = simpledialog.askinteger("Массив по траектории", "Число элементов:", initialvalue=5, parent=r, minvalue=2)
                if not n: return
                pts = [Vec2(v) for v in ezpath.make_path(e).flattening(0.005)]; L = sum((pts[i + 1] - pts[i]).magnitude for i in range(len(pts) - 1))
                b = self._cutie_sel(); baza = Vec2(b[0], b[1]); ms = []
                for k in range(1, n):
                    t = L * k / (n - 1); acc = 0; i = 0
                    while i < len(pts) - 2 and acc + (pts[i + 1] - pts[i]).magnitude < t: acc += (pts[i + 1] - pts[i]).magnitude; i += 1
                    seg = pts[i + 1] - pts[i]; q = pts[i] + (seg.normalize() * (t - acc) if seg.magnitude else Vec2())
                    ms.append(Matrix44.translate(q.x - pts[0].x, q.y - pts[0].y, 0))
                self._copii(ms, f"Массив по траектории: {n} элементов.")
            return self.ed.incepe("PUNCT", "МАССИВТРАЕКТ  Выберите траекторию:", nevoie_sel=False, cb=cb)

    def _cutie_sel(self):
        bb = [self.app.v.bbox[h] for h in self.ed.sel if h in self.app.v.bbox]
        if not bb: return (0, 0, 0, 0)
        return min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb), max(b[3] for b in bb)

    def _copii(self, matrici, msg):
        self.ed.instantaneu([]); msp = self.doc.modelspace(); noi = []
        orig = [self.ed.ent(h) for h in self.ed.sel if self.ed.ent(h) is not None]
        for m in matrici:
            for e in orig:
                try: c = e.copy(); msp.add_entity(c); c.transform(m); noi.append(c)
                except Exception: pass
        self._gata(noi, msg + f" Создано копий: {len(noi)}.")

    # ================================================================ РАЗМЕРЫ
    def _dim(self, f, msg):
        self.ed.instantaneu([])
        try:
            d = f(); d.render()
        except Exception as ex: return self.app.mesaj(f"Размер не построен: {ex}")
        self.ultima_cota = d; self._gata([d.dimension], msg)

    def cota(self, tip):
        if not self.doc: return
        msp = self.doc.modelspace(); at = dict(self._at(), dimstyle="Standard") if "Standard" in self.doc.dimstyles else self._at()
        if tip in ("ЛИН", "ПАРАЛ"):
            def cb(p):
                a, b, loc = p
                if tip == "ПАРАЛ":
                    dist = ((loc[0] - a[0]) * -(b[1] - a[1]) + (loc[1] - a[1]) * (b[0] - a[0])) / max(_d(a, b), 1e-12)
                    self._dim(lambda: msp.add_aligned_dim(p1=a, p2=b, distance=dist, dxfattribs=at), f"Параллельный размер: {_d(a, b):.4f}")
                else:
                    vert = abs(loc[0] - (a[0] + b[0]) / 2) > abs(loc[1] - (a[1] + b[1]) / 2)
                    self._dim(lambda: msp.add_linear_dim(base=loc, p1=a, p2=b, angle=90 if vert else 0, dxfattribs=at),
                              f"Линейный размер: {abs(b[1] - a[1]) if vert else abs(b[0] - a[0]):.4f}")
            return self._puncte(["РАЗМЕР  Начало первой выносной линии:", "Начало второй выносной линии:", "Положение размерной линии:"], cb)
        if tip in ("РАД", "ДИАМ"):
            def cb(p):
                sx, sy = self.app.v.ecran(*p[0]); h = self.ed.la_entitate(sx, sy); e = self.ed.ent(h) if h else None
                if e is None or e.dxftype() not in ("CIRCLE", "ARC"): return self.app.mesaj("Укажите круг или дугу.")
                c, r = e.dxf.center, e.dxf.radius; a = math.radians(_ang((c.x, c.y), p[0]))
                if tip == "РАД": self._dim(lambda: msp.add_radius_dim(center=c, radius=r, angle=math.degrees(a), dxfattribs=at), f"Радиус: {r:.4f}")
                else: self._dim(lambda: msp.add_diameter_dim(center=c, radius=r, angle=math.degrees(a), dxfattribs=at), f"Диаметр: {2 * r:.4f}")
            return self._puncte([f"РАЗМЕР  Выберите {'дугу или круг'}:"], cb)
        if tip in ("ПРОД", "БАЗ"):
            d = self.ultima_cota
            if d is None: return self.app.mesaj("Сначала постройте линейный размер.")
            ent = d.dimension; p1, p2 = ent.dxf.defpoint2, ent.dxf.defpoint3; base = ent.dxf.defpoint; ang = ent.dxf.get("angle", 0)
            pas = 7 * (self.doc.dimstyles.get("Standard").dxf.get("dimtxt", 2.5) if "Standard" in self.doc.dimstyles else 2.5)
            def cb(p):
                nonlocal p1, p2, base
                q = p[0]
                if tip == "ПРОД":
                    start = p2; loc = base
                else:
                    start = p1; off = (0, -pas) if ang == 0 else (pas, 0); loc = (base.x + off[0], base.y + off[1]) if hasattr(base, "x") else (base[0] + off[0], base[1] + off[1])
                self._dim(lambda: msp.add_linear_dim(base=loc, p1=start, p2=q, angle=ang, dxfattribs=at), "Размер " + ("продолжен." if tip == "ПРОД" else "от базы."))
                e2 = self.ultima_cota.dimension; p2 = e2.dxf.defpoint3; base = e2.dxf.defpoint
            return self.ed.incepe("REPETAT", "Начало следующей выносной линии (Esc – конец):", nevoie_sel=False, rep="Начало следующей выносной линии (Esc – конец):", cb=lambda q: cb([q]))
