"""Etapa 2 – editarea: selecție (clic, fereastră, intersecție), mutare, copiere, rotire, scalare, oglindire, ștergere,
desfacere, anulare/refacere și desenare simplă (linie, polilinie, cerc). Comenzile cer puncte ca în AutoCAD:
clic pe desen sau valoare scrisă în linia de comandă."""
import io, math, re, zlib
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

    # ---------------------------------------------------------------- anulare / refacere
    # Se păstrează doar copiile obiectelor atinse și lista obiectelor din model de dinainte (nu tot desenul):
    # rapid și cu puțin RAM și pe desene mari. Pentru schimbări generale (straturi, tabele) – copie comprimată a desenului.
    def _handles(self):
        return {e.dxf.handle for e in self.doc.modelspace()}

    def instantaneu(self, handles=None, complet=False):
        if self.doc is None: return
        if complet:
            s = io.StringIO(); self.doc.write(s); rec = ("full", zlib.compress(s.getvalue().encode("utf-8"), 3))
        else:
            hs = set(self.sel if handles is None else handles); copii = {}
            for h in hs:
                e = self.ent(h)
                if e is not None and e.is_alive:
                    try: copii[h] = e.copy()
                    except Exception: pass
            rec = ("ent", self._handles(), copii)
        self.anulari = (self.anulari + [rec])[-60:]; self.refaceri = []
        # limită de memorie: cel mult ~150 000 de obiecte copiate în toată istoria (selecții mari pe desene mari)
        while len(self.anulari) > 1 and sum(len(r[2]) if r[0] == "ent" else 20000 for r in self.anulari) > 150000: self.anulari.pop(0)

    def _aplica_rec(self, rec):
        """readuce desenul la starea din înregistrare; întoarce înregistrarea inversă și ce trebuie redesenat"""
        if rec[0] == "foaie":                              # obiecte lipite pe o foaie: anularea le scoate
            lay = self.doc.layouts.get(rec[1])
            for h in rec[2]:
                e = self.ent(h)
                if e is not None and e.is_alive: lay.delete_entity(e)
            self.v.versiune += 1; self.v.deseneaza(); return ("nimic",)
        if rec[0] == "nimic": return ("nimic",)
        if rec[0] == "full":
            s = io.StringIO(); self.doc.write(s); inv = ("full", zlib.compress(s.getvalue().encode("utf-8"), 3))
            doc = ezdxf.read(io.StringIO(zlib.decompress(rec[1]).decode("utf-8")))
            self.app.doc = doc; self.v.doc = doc; self.v.layout = doc.modelspace(); self.v.reconstruieste(); self.app._actualizeaza_straturi()
            return inv
        _, inainte, copii = rec; msp = self.doc.modelspace(); cur = self._handles()
        de_sters = (cur - inainte) | {h for h in copii if h in cur}
        inv_copii = {}
        for h in de_sters:
            e = self.ent(h)
            if e is None: continue
            try: inv_copii[h] = e.copy()
            except Exception: pass
            msp.delete_entity(e)
        dupa_stergere = self._handles(); noi = set()
        for c in copii.values():
            c2 = c.copy(); msp.add_entity(c2); noi.add(c2.dxf.handle)
        self.v.actualizeaza(de_sters | noi)
        return ("ent", dupa_stergere, inv_copii)

    def anuleaza(self):
        if not self.anulari: return self.app.mesaj("Нечего отменять.")
        self.refaceri.append(self._aplica_rec(self.anulari.pop())); self._dupa_anulare("Отменено.")

    def reface(self):
        if not self.refaceri: return self.app.mesaj("Нечего повторять.")
        self.anulari.append(self._aplica_rec(self.refaceri.pop())); self._dupa_anulare("Повторено.")

    def _dupa_anulare(self, mesaj):
        self.sel = set(); self.v.selectie = set(); self.v.deseneaza(); self.app.cv.delete("grip"); self.app.marcheaza(); self.app.mesaj(mesaj)

    def gata_modificare(self, mesaj=None):
        rec = self.anulari[-1] if self.anulari else None
        if rec and rec[0] == "ent":                       # redesenez doar ce s-a schimbat
            self.v.actualizeaza((self._handles() - rec[1]) | set(rec[2]))
        else: self.v.reconstruieste()
        self.sel = {h for h in self.sel if self.ent(h) is not None and self.ent(h).is_alive}
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
        if self.v.foaie and self.stare and self.stare["cmd"] in ("ВСТАВИТЬБУФ", "PUNCT", "PUNCTE"):
            return self.punct(self.v.foaie_lume(e.x, e.y))
        if self.v.foaie:                                   # pe foaie: se poate selecta rama viewport-ului
            cv = self.app.cv; vp = None
            for it in cv.find_overlapping(e.x - 4, e.y - 4, e.x + 4, e.y + 4):
                for t in cv.gettags(it):
                    if t.startswith("hvp"): vp = t[3:]
            self.v.selectie = {"vp" + vp} if vp else set(); self.v.deseneaza()
            return self.app.mesaj("Видовой экран выбран. Правая кнопка – «Развернуть ВЭкран»." if vp else "Лист: редактирование модели – на вкладке «Модель».")
        if self.stare: return self.punct(self.punct_ecran(e.x, e.y))
        h = self.la_entitate(e.x, e.y)
        if h:
            grup = self.app.un.extinde_grup(h) if hasattr(self.app, "un") else {h}
            if e.state & 0x1: self.sel -= grup             # Shift = scoate din selecție
            else: self.sel |= grup
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
        self.stare = None; cv = self.app.cv; cv.delete("prev"); cv.delete("snap"); cv.delete("masura"); self.v.deseneaza(); self.prinderi()
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
        if st["cmd"] in ("REPETAT", "PUNCTE", "PUNCT"):
            if not t:
                if st["cmd"] == "REPETAT":
                    fin = st.get("fin"); self.opreste("Готово.")
                    if fin: fin()
                return
            m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*[,;]\s*(-?\d+(?:\.\d+)?)", t)
            if m: return self.punct((float(m.group(1)), float(m.group(2))))
            try: n = float(t.replace(",", "."))
            except ValueError: return self.app.mesaj("Нужна точка (щелчок или x,y) или число.")
            if st["cmd"] == "REPETAT" and st.get("numar"): return st["numar"](n)
            if st["cmd"] == "PUNCTE" and st.get("numere") and st["puncte"]: return self._puncte_avans(n)
            return self.app.mesaj("Нужна точка (щелчок на чертеже или x,y).")
        if not t:
            if st["cmd"] in ("ОТРЕЗОК", "ПЛИНИЯ", "КОПИРОВАТЬ", "ПЛОЩАДЬ"): return self.termina()
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
                self.instantaneu([]); a, b = st["puncte"][-2], st["puncte"][-1]
                self.doc.modelspace().add_line(a, b, dxfattribs={"layer": self.app.strat_curent()}); self.gata_modificare()
            return self.app.prompt("Следующая точка или [Enter = завершить]:")
        if c == "КРУГ":
            if st["baza"] is None: st["baza"] = p; return self.app.prompt("Радиус круга (число или точка):")
            return self._cerc(math.hypot(p[0] - st["baza"][0], p[1] - st["baza"][1]))
        if c in ("ИЗМЕРИТЬ", "УГОЛИЗМ", "ПЛОЩАДЬ", "КООРД"):
            st["puncte"].append(p); st["baza"] = p; pts = st["puncte"]
            if c == "КООРД": self.app.mesaj(f"X = {p[0]:.4f}   Y = {p[1]:.4f}   Z = 0.0000"); return self.opreste("Координаты точки.")
            if c == "ИЗМЕРИТЬ" and len(pts) == 2:
                (x1, y1), (x2, y2) = pts; d = math.hypot(x2 - x1, y2 - y1); a = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 360
                self.app.mesaj(f"Расстояние = {d:.4f},  Угол в плоскости XY = {a:.2f}°,  ΔX = {x2 - x1:.4f},  ΔY = {y2 - y1:.4f}")
                return self.opreste("Измерено.")
            if c == "УГОЛИЗМ" and len(pts) == 3:
                (ax, ay), (bx, by), (cx, cy) = pts
                u = abs(math.degrees(math.atan2(cy - by, cx - bx) - math.atan2(ay - by, ax - bx))) % 360; u = 360 - u if u > 180 else u
                self.app.mesaj(f"Угол = {u:.2f}°"); return self.opreste("Измерено.")
            if c == "ПЛОЩАДЬ" and len(pts) >= 2:
                sx, sy = self.v.ecran(*pts[-2]); ex, ey = self.v.ecran(*pts[-1]); self.app.cv.create_line(sx, sy, ex, ey, fill="#5fd36b", width=2, tags="masura")
            self.app.prompt({"ИЗМЕРИТЬ": "Вторая точка:", "УГОЛИЗМ": "Вершина угла:" if len(pts) == 1 else "Вторая сторона угла:",
                             "ПЛОЩАДЬ": "Следующая точка или [Enter = посчитать]:"}[c])
            return
        if c == "PUNCT":                                   # o comandă din alt modul cere un singur punct
            self.stare = None; self.app.prompt(None); self.app.cv.delete("snap"); return st["cb"](p)
        if c == "PUNCTE":                                  # cere n puncte, apoi cb(listă)
            return self._puncte_avans(p)
        if c == "REPETAT":                                 # clic după clic, până la Esc (ex.: atribute „Несколько”)
            self.app.cv.delete("snap"); st["cb"](p); return self.app.prompt(st["rep"]) if self.stare else None
        if c == "BAZABUF":
            self.stare = None; self.app.prompt(None); self.app.cv.delete("snap")
            self.copiaza_buf(); self.clip_baza = p
            if st.get("taie"): self.sterge()
            return self.app.mesaj("Базовая точка задана: " + ("вырезано" if st.get("taie") else "скопировано") + " в буфер.")
        if c == "ВСТАВКА":
            self.stare = None; self.app.prompt(None); self.app.cv.delete("snap"); return self.app.sim.insereaza(st["bloc"], p)
        if c == "БЛОКБАЗА":
            self.stare = None; self.app.prompt(None); self.app.cv.delete("snap"); return self.app.sim.termina_bloc(st["bloc"], p)
        if c == "ТЕКСТ":
            self.stare = None; self.app.prompt(None); self.app.cv.delete("snap")
            return self.app.et.dialog_text(None, p, mtext=st.get("mtext", False))
        if c == "ВСТАВИТЬБУФ" and self.v.foaie:
            return self._lipeste_pe_foaie(p)
        if c == "ВСТАВИТЬБУФ":
            self.instantaneu([]); bx, by = st["baza0"]; m = Matrix44.translate(p[0] - bx, p[1] - by, 0); msp = self.doc.modelspace(); noi = set()
            for e in self.clip:
                c2 = e.copy(); msp.add_entity(c2)
                try: c2.transform(m)
                except Exception: pass
                noi.add(c2.dxf.handle)
            self.sel = noi; self.gata_modificare(f"Вставлено объектов: {len(noi)}"); return self.opreste("Готово.")

    def _lipeste_pe_foaie(self, p):
        """lipirea pe o foaie (Layout): obiectele intră în spațiul foii; dacă sunt mai mari decât hârtia, se micșorează cât zona tipăribilă"""
        import tiparire
        lay = self.doc.layouts.get(self.v.foaie)
        cb = getattr(self, "clip_cutie", None)
        if cb: x0, y0, x1, y1 = cb
        else: x0, y0 = self.clip_baza or (0, 0); x1, y1 = x0 + 1, y0 + 1
        w, h = tiparire.dimensiune_foaie(self.doc, self.v.foaie); mg = tiparire.margini_foaie(self.doc, self.v.foaie)
        lw, lh = w - mg[0] - mg[2], h - mg[1] - mg[3]; k = 1.0
        if (x1 - x0) > lw or (y1 - y0) > lh: k = min(lw / max(x1 - x0, 1e-9), lh / max(y1 - y0, 1e-9))
        sw, sh = (x1 - x0) * k, (y1 - y0) * k                         # rămâne în zona tipăribilă (originea foii = colțul ei)
        px = max(0.0, min(p[0], lw - sw)); py = max(0.0, min(p[1], lh - sh))
        m = Matrix44.translate(-x0, -y0, 0) @ Matrix44.scale(k, k, k) @ Matrix44.translate(px, py, 0); noi = []
        for e in self.clip:
            c2 = e.copy(); lay.add_entity(c2)
            try: c2.transform(m)
            except Exception: pass
            noi.append(c2.dxf.handle)
        self.anulari = (self.anulari + [("foaie", self.v.foaie, noi)])[-60:]; self.refaceri = []
        self.v.versiune += 1; self.stare = None; self.app.prompt(None); self.app.cv.delete("snap"); self.v.deseneaza(); self.app.marcheaza()
        self.app.mesaj(f"Вставлено на лист «{self.v.foaie}»: {len(noi)} объектов" + (f", масштаб 1:{1 / k:.0f} (вписано в лист)." if k < 1 else "."))

    def _puncte_avans(self, val):
        st = self.stare; st["puncte"].append(val)
        if not isinstance(val, float): st["baza"] = val
        if len(st["puncte"]) < st["n"]: return self.app.prompt(st["prompturi"][len(st["puncte"])])
        self.stare = None; self.app.prompt(None); self.app.cv.delete("snap"); self.app.cv.delete("prev"); return st["cb"](st["puncte"])

    def termina(self):
        st = self.stare
        if st and st["cmd"] == "ПЛОЩАДЬ" and len(st["puncte"]) >= 3:
            pts = st["puncte"]; n = len(pts)
            a = abs(sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))) / 2
            per = sum(math.hypot(pts[(i + 1) % n][0] - pts[i][0], pts[(i + 1) % n][1] - pts[i][1]) for i in range(n))
            self.app.cv.delete("masura"); self.app.mesaj(f"Площадь = {a:.4f},  Периметр = {per:.4f}"); return self.opreste("Измерено.")
        if st and st["cmd"] == "ПЛИНИЯ" and len(st["puncte"]) >= 2:
            self.instantaneu([]); self.doc.modelspace().add_lwpolyline(st["puncte"], dxfattribs={"layer": self.app.strat_curent()}); self.gata_modificare()
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
        self.instantaneu([]); self.doc.modelspace().add_circle(self.stare["baza"], r, dxfattribs={"layer": self.app.strat_curent()})
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
        hs = [h for h in self.sel if self.ent(h) is not None]
        self.clip = [self.ent(h).copy() for h in hs]; self.clip_baza = None
        bb = [self.v.bbox[h] for h in hs if h in self.v.bbox]           # cutia originalelor (copiile nu au handle)
        self.clip_cutie = (min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb), max(b[3] for b in bb)) if bb else None
        self.app.mesaj(f"Скопировано в буфер: {len(self.clip)} объектов.")

    def lipeste_buf(self):
        if not self.clip: return self.app.mesaj("Буфер пуст.")
        xs = []; ys = []
        for e in self.clip:
            b = self.v.bbox.get(e.dxf.handle) if e.dxf.handle else None
        p0 = getattr(self, "clip_baza", None) or self.puncte_prindere_copie(self.clip[0])
        self.incepe("ВСТАВИТЬБУФ", "Точка вставки:", nevoie_sel=False, baza0=p0); self.stare["baza"] = None

    def lipeste_original(self):
        if not self.clip: return self.app.mesaj("Буфер пуст.")
        self.instantaneu([]); msp = self.doc.modelspace(); noi = set()
        for e in self.clip:
            c2 = e.copy(); msp.add_entity(c2); noi.add(c2.dxf.handle)
        self.sel = noi; self.gata_modificare(f"Вставлено с исходными координатами: {len(noi)}")

    def raza(self, sx, sy):
        h = self.la_entitate(sx, sy); e = self.ent(h) if h else None
        if e is not None and e.dxftype() in ("CIRCLE", "ARC"):
            r = e.dxf.radius; self.app.mesaj(f"Радиус = {r:.4f},  Диаметр = {2 * r:.4f}"); return True
        return False

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
