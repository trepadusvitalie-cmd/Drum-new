"""Etapa 2 – editarea: selecție (clic, fereastră, intersecție), mutare, copiere, rotire, scalare, oglindire, ștergere,
desfacere, anulare/refacere și desenare simplă (linie, polilinie, cerc). Comenzile cer puncte ca în AutoCAD:
clic pe desen sau valoare scrisă în linia de comandă."""
import io, math, re
import ezdxf
from ezdxf.math import Matrix44, Vec3
from stil import *

PICK = 5


class Editare:
    def __init__(self, app):
        self.app = app; self.sel = set(); self.stare = None; self.anulari = []; self.refaceri = []
        self._fer = None; self._ultim_punct = None; self.clip = []

    # ---------------------------------------------------------------- utilitare
    @property
    def doc(self): return self.app.doc

    @property
    def v(self): return self.app.v

    def ent(self, h):
        try: return self.doc.entitydb[h]
        except Exception: return None

    def blocat(self, e):
        l = self.doc.layers.get(e.dxf.layer) if e.dxf.layer in self.doc.layers else None
        return l is not None and l.is_locked()

    def arata_selectia(self):
        self.v.selectie = set(self.sel); self.v.deseneaza(); self.prinderi()
        self.app.dupa_selectie()

    def prinderi(self):
        cv = self.app.cv; cv.delete("grip"); n = 0
        for h in list(self.sel)[:300]:
            for x, y in self.puncte_prindere(h)[:20]:
                sx, sy = self.v.ecran(x, y); cv.create_rectangle(sx - 4, sy - 4, sx + 4, sy + 4, fill=GRIP, outline="#9cc3ff", tags="grip"); n += 1
        cv.tag_raise("grip"); cv.tag_raise("cur")

    def puncte_prindere(self, h):
        e = self.ent(h)
        if e is None: return []
        t = e.dxftype()
        try:
            if t == "LINE": return [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y), ((e.dxf.start.x + e.dxf.end.x) / 2, (e.dxf.start.y + e.dxf.end.y) / 2)]
            if t == "LWPOLYLINE": return [(p[0], p[1]) for p in e.get_points("xy")]
            if t in ("CIRCLE", "ARC"): c = e.dxf.center; return [(c.x, c.y)]
            if t in ("TEXT", "MTEXT", "INSERT", "POINT"):
                p = e.dxf.insert if t != "POINT" else e.dxf.location; return [(p.x, p.y)]
        except Exception: pass
        b = self.v.bbox.get(h)
        return [(b[0], b[1]), (b[2], b[3])] if b else []

    # ---------------------------------------------------------------- anulare / refacere (instantanee ale desenului)
    def instantaneu(self):
        if self.doc is None: return
        s = io.StringIO(); self.doc.write(s); self.anulari = (self.anulari + [s.getvalue()])[-40:]; self.refaceri = []

    def _restaureaza(self, txt):
        doc = ezdxf.read(io.StringIO(txt))
        self.app.doc = doc; self.v.doc = doc; self.v.layout = doc.modelspace(); self.sel = set()
        self.v.reconstruieste(); self.v.selectie = set(); self.v.deseneaza(); self.app.cv.delete("grip")
        self.app.marcheaza(); self.app._actualizeaza_straturi()

    def anuleaza(self):
        if not self.anulari: return self.app.mesaj("Нечего отменять.")
        s = io.StringIO(); self.doc.write(s); self.refaceri.append(s.getvalue())
        self._restaureaza(self.anulari.pop()); self.app.mesaj("Отменено.")

    def reface(self):
        if not self.refaceri: return self.app.mesaj("Нечего повторять.")
        s = io.StringIO(); self.doc.write(s); self.anulari.append(s.getvalue())
        self._restaureaza(self.refaceri.pop()); self.app.mesaj("Повторено.")

    def gata_modificare(self, mesaj=None):
        self.v.reconstruieste(); self.sel = {h for h in self.sel if self.ent(h) is not None and self.ent(h).is_alive}
        self.arata_selectia(); self.app.marcheaza()
        if mesaj: self.app.mesaj(mesaj)

    # ---------------------------------------------------------------- selecția cu mouse-ul
    def la_entitate(self, sx, sy):
        cv = self.app.cv
        for it in reversed(cv.find_overlapping(sx - PICK, sy - PICK, sx + PICK, sy + PICK)):
            for t in cv.gettags(it):
                if t.startswith("h") and t != "h":
                    e = self.ent(t[1:])
                    if e is not None and not self.blocat(e): return t[1:]
        return None

    def clic(self, e):
        if self.doc is None: return
        if self.stare: return self.punct(self.punct_ecran(e.x, e.y))
        h = self.la_entitate(e.x, e.y)
        if h:
            if e.state & 0x1: self.sel.discard(h)          # Shift = scoate din selecție
            else: self.sel.add(h)
            return self.arata_selectia()
        self._fer = (e.x, e.y)                              # începe selecția cu fereastră

    def trage(self, e):
        if self.stare or not self._fer: return
        cv = self.app.cv; cv.delete("fer"); x0, y0 = self._fer
        dreapta = e.x >= x0
        cv.create_rectangle(x0, y0, e.x, e.y, outline="#4f8ff7" if dreapta else "#5fd36b", dash=() if dreapta else (5, 3),
                            fill="#4f8ff7" if dreapta else "#5fd36b", stipple="gray12", tags="fer")

    def elibereaza(self, e):
        if self.stare or not self._fer: return
        x0, y0 = self._fer; self._fer = None; self.app.cv.delete("fer")
        if abs(e.x - x0) < 4 and abs(e.y - y0) < 4:
            if not (e.state & 0x1) and self.sel: self.sel = set(); self.arata_selectia()
            return
        wx0, wy0 = self.v.lume(min(x0, e.x), max(y0, e.y)); wx1, wy1 = self.v.lume(max(x0, e.x), min(y0, e.y))
        fereastra = e.x >= x0
        for h, (a, b, c, d) in self.v.bbox.items():
            ent = self.ent(h)
            if ent is None or self.blocat(ent) or not self.v.strat_vizibil(ent.dxf.get("layer", "0")): continue
            if fereastra: ok = a >= wx0 and c <= wx1 and b >= wy0 and d <= wy1
            else: ok = not (c < wx0 or a > wx1 or d < wy0 or b > wy1)
            if ok: self.sel.add(h)
        self.arata_selectia()
        self.app.mesaj(f"Выбрано объектов: {len(self.sel)}")

    def tot(self):
        self.sel = {h for h in self.v.bbox if self.ent(h) is not None and not self.blocat(self.ent(h))}
        self.arata_selectia(); self.app.mesaj(f"Выбрано объектов: {len(self.sel)}")

    def goleste(self):
        self.sel = set(); self.v.selectie = set(); self.v.deseneaza(); self.app.cv.delete("grip"); self.app.dupa_selectie()

    # ---------------------------------------------------------------- puncte: prindere de obiecte și orto
    def punct_ecran(self, sx, sy):
        x, y = self.v.lume(sx, sy)
        if self.app.stare["osnap"][1]:
            best = None
            for h, (a, b, c, d) in self.v.bbox.items():
                ax, ay = self.v.ecran(a, d); cx2, cy2 = self.v.ecran(c, b)
                if not (ax - 15 <= sx <= cx2 + 15 and ay - 15 <= sy <= cy2 + 15): continue
                for px, py in self.puncte_prindere(h)[:60]:
                    qx, qy = self.v.ecran(px, py); dd = (qx - sx) ** 2 + (qy - sy) ** 2
                    if dd < 144 and (best is None or dd < best[0]): best = (dd, px, py)
            if best: x, y = best[1], best[2]
        if self.app.orto and self.stare and self.stare.get("baza") is not None and not self._snap_gasit(sx, sy):
            bx, by = self.stare["baza"]
            if abs(x - bx) >= abs(y - by): y = by
            else: x = bx
        return x, y

    def _snap_gasit(self, sx, sy):
        return False

    def marcaj_snap(self, sx, sy):
        cv = self.app.cv; cv.delete("snap")
        if not (self.stare and self.app.stare["osnap"][1]): return
        x, y = self.punct_ecran(sx, sy); qx, qy = self.v.ecran(x, y)
        if abs(qx - sx) > 0.5 or abs(qy - sy) > 0.5:
            cv.create_rectangle(qx - 6, qy - 6, qx + 6, qy + 6, outline="#ffd400", width=2, tags="snap")

    # ---------------------------------------------------------------- comenzi interactive (cer puncte)
    def incepe(self, cmd, prompt, nevoie_sel=True, **date):
        if self.doc is None: return self.app.mesaj("Нет открытого чертежа.")
        if nevoie_sel and not self.sel: return self.app.mesaj(f"{cmd}: сначала выберите объекты (щелчок или рамка), затем снова команду.")
        self.stare = dict(cmd=cmd, baza=None, puncte=[], **date); self.app.mesaj(prompt); self.app.prompt(prompt)

    def opreste(self, mesaj="*Прервано*"):
        self.stare = None; cv = self.app.cv; cv.delete("prev"); cv.delete("snap"); self.v.deseneaza(); self.prinderi()
        self.app.prompt(None); self.app.mesaj(mesaj)

    def miscare(self, e):
        if not self.stare: return
        self.marcaj_snap(e.x, e.y)
        cv = self.app.cv; cv.delete("prev"); st = self.stare
        if st.get("baza") is None: return
        x, y = self.punct_ecran(e.x, e.y); bx, by = st["baza"]; sx0, sy0 = self.v.ecran(bx, by); sx1, sy1 = self.v.ecran(x, y)
        cv.create_line(sx0, sy0, sx1, sy1, fill="#e8ebef", dash=(4, 3), tags="prev")
        if st["cmd"] in ("ПЕРЕНЕСТИ", "КОПИРОВАТЬ"):
            for h in st.get("de_mutat", []): pass
            dx, dy = sx1 - sx0, sy1 - sy0
            for h in list(self.sel)[:400]:
                for it in cv.find_withtag("h" + h):
                    c = cv.coords(it)
                    if cv.type(it) == "text": cv.create_text(c[0] + dx, c[1] + dy, text=cv.itemcget(it, "text"), fill=SELECT, font=cv.itemcget(it, "font"),
                                                             anchor=cv.itemcget(it, "anchor"), angle=cv.itemcget(it, "angle"), tags="prev")
                    elif cv.type(it) == "line": cv.create_line([v + (dx if i % 2 == 0 else dy) for i, v in enumerate(c)], fill=SELECT, tags="prev")
        elif st["cmd"] == "КРУГ":
            r = math.hypot(sx1 - sx0, sy1 - sy0); cv.create_oval(sx0 - r, sy0 - r, sx0 + r, sy0 + r, outline="#e8ebef", tags="prev")
        elif st["cmd"] in ("ОТРЕЗОК", "ПЛИНИЯ") and st["puncte"]:
            pts = [c for p in st["puncte"] for c in self.v.ecran(*p)]
            if len(pts) >= 4: cv.create_line(pts, fill="#e8ebef", tags="prev")

    def valoare(self, t):
        """text scris în linia de comandă cât o comandă cere ceva: număr, punct „x,y” sau Da/Nu"""
        st = self.stare; t = (t or "").strip()
        if not t:
            if st["cmd"] in ("ОТРЕЗОК", "ПЛИНИЯ", "КОПИРОВАТЬ"): return self.termina()
            if st["cmd"] == "ЗЕРКАЛО" and st.get("intreaba"): return self._oglinda(False)
            return
        if st["cmd"] == "ЗЕРКАЛО" and st.get("intreaba"):
            return self._oglinda(t.upper().startswith(("Д", "Y")))
        m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)", t)
        if m: return self.punct((float(m.group(1)), float(m.group(2))))
        try: n = float(t.replace(",", "."))
        except ValueError: return self.app.mesaj("Нужна точка (щелчок или x,y) или число.")
        if st["cmd"] == "ПОВЕРНУТЬ" and st.get("baza") is not None: return self._roteste(n)
        if st["cmd"] == "МАСШТАБ" and st.get("baza") is not None: return self._scaleaza(n)
        if st["cmd"] == "КРУГ" and st.get("baza") is not None: return self._cerc(n)
        if st.get("baza") is not None and st["cmd"] in ("ПЕРЕНЕСТИ", "КОПИРОВАТЬ", "ОТРЕЗОК", "ПЛИНИЯ"):    # distanță pe direcția mouse-ului
            mx, my = self.app.ultim_mouse; x, y = self.v.lume(mx, my); bx, by = st["baza"]; d = math.hypot(x - bx, y - by) or 1
            return self.punct((bx + (x - bx) / d * n, by + (y - by) / d * n))
        self.app.mesaj("Нужна точка (щелчок на чертеже).")

    def punct(self, p):
        st = self.stare; c = st["cmd"]
        if c in ("ПЕРЕНЕСТИ", "КОПИРОВАТЬ"):
            if st["baza"] is None: st["baza"] = p; return self.app.prompt("Вторая точка или <использовать первую точку как смещение>:")
            bx, by = st["baza"]; m = Matrix44.translate(p[0] - bx, p[1] - by, 0)
            if c == "ПЕРЕНЕСТИ": self._aplica(m, copie=False, mesaj="Перенесено"); return self.opreste("Перенесено.")
            self._aplica(m, copie=True, mesaj="Скопировано"); st["baza"] = st["baza"]; return self.app.prompt("Вторая точка или [Выход] <Выход>:")
        if c == "ПОВЕРНУТЬ":
            if st["baza"] is None: st["baza"] = p; return self.app.prompt("Угол поворота (градусы) или укажите точку:")
            bx, by = st["baza"]; return self._roteste(math.degrees(math.atan2(p[1] - by, p[0] - bx)))
        if c == "МАСШТАБ":
            if st["baza"] is None: st["baza"] = p; return self.app.prompt("Масштаб (число, например 2 или 0.5):")
            return self.app.mesaj("Введите число – масштаб.")
        if c == "ЗЕРКАЛО":
            if st["baza"] is None: st["baza"] = p; return self.app.prompt("Вторая точка оси отражения:")
            st["p2"] = p; st["intreaba"] = True; return self.app.prompt("Удалить исходные объекты? [Да/Нет] <Нет>:")
        if c in ("ОТРЕЗОК", "ПЛИНИЯ"):
            st["puncte"].append(p); st["baza"] = p
            if c == "ОТРЕЗОК" and len(st["puncte"]) >= 2:
                self.instantaneu(); a, b = st["puncte"][-2], st["puncte"][-1]
                self.doc.modelspace().add_line(a, b, dxfattribs={"layer": self.app.strat_curent()}); self.gata_modificare()
            return self.app.prompt("Следующая точка или [Enter = завершить]:")
        if c == "КРУГ":
            if st["baza"] is None: st["baza"] = p; return self.app.prompt("Радиус круга (число или точка):")
            return self._cerc(math.hypot(p[0] - st["baza"][0], p[1] - st["baza"][1]))
        if c == "ТЕКСТ":
            self.stare = None; self.app.prompt(None); self.app.cv.delete("snap")
            return self.app.et.dialog_text(None, p, mtext=st.get("mtext", False))
        if c == "ВСТАВИТЬБУФ":
            self.instantaneu(); bx, by = st["baza0"]; m = Matrix44.translate(p[0] - bx, p[1] - by, 0); msp = self.doc.modelspace(); noi = set()
            for e in self.clip:
                c2 = e.copy(); msp.add_entity(c2)
                try: c2.transform(m)
                except Exception: pass
                noi.add(c2.dxf.handle)
            self.sel = noi; self.gata_modificare(f"Вставлено объектов: {len(noi)}"); return self.opreste("Готово.")

    def termina(self):
        st = self.stare
        if st and st["cmd"] == "ПЛИНИЯ" and len(st["puncte"]) >= 2:
            self.instantaneu(); self.doc.modelspace().add_lwpolyline(st["puncte"], dxfattribs={"layer": self.app.strat_curent()}); self.gata_modificare()
        self.opreste("Готово.")

    def _aplica(self, m, copie, mesaj):
        self.instantaneu(); msp = self.doc.modelspace(); noi = set(); gres = 0
        for h in list(self.sel):
            e = self.ent(h)
            if e is None: continue
            if copie: e = e.copy(); msp.add_entity(e); noi.add(e.dxf.handle)
            try: e.transform(m)
            except Exception: gres += 1
        if copie: self.sel = noi | set()
        self.gata_modificare(f"{mesaj}: {len(self.sel)} объектов" + (f" ({gres} не удалось)" if gres else ""))

    def _roteste(self, unghi):
        bx, by = self.stare["baza"]
        m = Matrix44.translate(-bx, -by, 0) @ Matrix44.z_rotate(math.radians(unghi)) @ Matrix44.translate(bx, by, 0)
        self._aplica(m, False, f"Повернуто на {unghi:.1f}°"); self.opreste(f"Повернуто на {unghi:.1f}°.")

    def _scaleaza(self, f):
        if f <= 0: return self.app.mesaj("Масштаб должен быть > 0.")
        bx, by = self.stare["baza"]
        m = Matrix44.translate(-bx, -by, 0) @ Matrix44.scale(f, f, f) @ Matrix44.translate(bx, by, 0)
        self._aplica(m, False, f"Масштаб {f}"); self.opreste(f"Масштаб {f}.")

    def _oglinda(self, sterge):
        (x1, y1), (x2, y2) = self.stare["baza"], self.stare["p2"]; a = math.atan2(y2 - y1, x2 - x1)
        m = (Matrix44.translate(-x1, -y1, 0) @ Matrix44.z_rotate(-a) @ Matrix44.scale(1, -1, 1) @ Matrix44.z_rotate(a) @ Matrix44.translate(x1, y1, 0))
        self._aplica(m, not sterge, "Отражено"); self.opreste("Отражено.")

    def _cerc(self, r):
        self.instantaneu(); self.doc.modelspace().add_circle(self.stare["baza"], r, dxfattribs={"layer": self.app.strat_curent()})
        self.gata_modificare(); self.opreste("Круг построен.")

    # ---------------------------------------------------------------- comenzi directe
    def sterge(self):
        if not self.sel: return self.app.mesaj("СТЕРЕТЬ: сначала выберите объекты.")
        self.instantaneu(); msp = self.doc.modelspace(); n = 0
        for h in list(self.sel):
            e = self.ent(h)
            if e is not None and e.is_alive:
                try: msp.delete_entity(e); n += 1
                except Exception: pass
        self.sel = set(); self.gata_modificare(f"Удалено объектов: {n}")

    def desface(self):
        if not self.sel: return self.app.mesaj("РАСЧЛЕНИТЬ: выберите блоки или полилинии.")
        self.instantaneu(); n = 0; noi = set()
        for h in list(self.sel):
            e = self.ent(h)
            if e is not None and e.dxftype() in ("INSERT", "LWPOLYLINE", "POLYLINE", "DIMENSION", "MTEXT", "LEADER", "MLEADER", "MULTILEADER"):
                try: noi |= {x.dxf.handle for x in e.explode()}; n += 1
                except Exception: pass
        self.sel = noi; self.gata_modificare(f"Расчленено объектов: {n}")

    def copiaza_buf(self):
        self.clip = [self.ent(h).copy() for h in self.sel if self.ent(h) is not None]
        self.app.mesaj(f"Скопировано в буфер: {len(self.clip)} объектов.")

    def lipeste_buf(self):
        if not self.clip: return self.app.mesaj("Буфер пуст.")
        xs = []; ys = []
        for e in self.clip:
            b = self.v.bbox.get(e.dxf.handle) if e.dxf.handle else None
        p0 = self.puncte_prindere_copie(self.clip[0])
        self.incepe("ВСТАВИТЬБУФ", "Точка вставки:", nevoie_sel=False, baza0=p0); self.stare["baza"] = None

    def puncte_prindere_copie(self, e):
        try:
            if e.dxftype() == "LINE": return (e.dxf.start.x, e.dxf.start.y)
            if e.dxftype() in ("TEXT", "MTEXT", "INSERT"): return (e.dxf.insert.x, e.dxf.insert.y)
            if e.dxftype() in ("CIRCLE", "ARC"): return (e.dxf.center.x, e.dxf.center.y)
            if e.dxftype() == "LWPOLYLINE": p = list(e.get_points("xy"))[0]; return p
        except Exception: pass
        return (0.0, 0.0)

    def schimba_strat(self, strat):
        if not self.sel: return False
        self.instantaneu()
        for h in self.sel:
            e = self.ent(h)
            if e is not None: e.dxf.layer = strat
        self.gata_modificare(f"Слой «{strat}» для {len(self.sel)} объектов"); return True

    def schimba_culoare(self, aci):
        if not self.sel: return False
        self.instantaneu()
        for h in self.sel:
            e = self.ent(h)
            if e is None: continue
            if e.dxf.hasattr("true_color"): e.dxf.discard("true_color")
            e.dxf.color = aci
        self.gata_modificare(f"Цвет изменен для {len(self.sel)} объектов"); return True
