"""Etapa 3 – simbolurile (blocurile): inserare (cu atribute), creare din obiectele selectate, înlocuire,
import de simboluri din alt desen DWG/DXF („Блоки из библиотек”) și o mică previzualizare a fiecărui bloc."""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ezdxf.math import Vec3
from stil import *
import fisiere


def blocuri(doc):
    return sorted(b.name for b in doc.blocks if not b.name.startswith("*") and not b.is_any_layout and not b.block.is_xref)


def previzualizare(cv, doc, nume, W=180, H=150):
    """desenează blocul simplificat (linii, cercuri, texte) într-un Canvas mic"""
    from ezdxf import path as ezpath
    cv.delete("all"); blk = doc.blocks.get(nume)
    if blk is None: return
    linii = []
    for e in blk:
        try:
            if e.dxftype() in ("ATTDEF", "TEXT", "MTEXT"):
                p = e.dxf.insert; linii.append([(p.x, p.y), (p.x + e.dxf.get("height", 1) * 0.6 * max(1, len(e.dxf.get("tag", e.dxf.get("text", "") or ""))), p.y)]); continue
            pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(0.01)]
            if len(pts) > 1: linii.append(pts)
        except Exception: pass
    if not linii: return cv.create_text(W / 2, H / 2, text="(нет просмотра)", fill=GRI)
    xs = [p[0] for l in linii for p in l]; ys = [p[1] for l in linii for p in l]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys); k = min((W - 20) / max(x1 - x0, 1e-9), (H - 20) / max(y1 - y0, 1e-9))
    for l in linii:
        cv.create_line([c for x, y in l for c in (10 + (x - x0) * k + (W - 20 - (x1 - x0) * k) / 2, H - 10 - (y - y0) * k - (H - 20 - (y1 - y0) * k) / 2)], fill="#e8ebef")


class Simboluri:
    def __init__(self, app):
        self.app = app; self.ultim = None; self.scara = 1.0; self.rot = 0.0

    @property
    def doc(self): return self.app.doc

    # ---------------------------------------------------------------- dialogul „Вставка блока”
    def dialog_inserare(self, nume=None):
        if not self.doc: return self.app.mesaj("Нет открытого чертежа.")
        if nume and nume in self.doc.blocks: return self.incepe_inserare(nume)
        d = tk.Toplevel(self.app.root); d.title("Вставка блока"); d.configure(bg=CORP); d.transient(self.app.root); d.geometry("560x400")
        st = tk.Frame(d, bg=CORP); st.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        dr = tk.Frame(d, bg=CORP); dr.pack(side="left", fill="y", padx=10, pady=10)
        tk.Label(st, text="Блоки текущего чертежа:", bg=CORP, fg=TEXT, font=F_MIC).pack(anchor="w")
        lb = tk.Listbox(st, bg="#2b313a", fg=TEXT, selectbackground=ACTIV, relief="flat", font=F_MIC, activestyle="none"); lb.pack(fill="both", expand=True, pady=4)
        cv = tk.Canvas(dr, width=180, height=150, bg="#212830", highlightthickness=1, highlightbackground=SEP); cv.pack(pady=(0, 8))
        def umple(sel=None):
            lb.delete(0, "end"); nume_b = blocuri(self.doc)
            for n in nume_b: lb.insert("end", n)
            i = nume_b.index(sel) if sel in nume_b else (nume_b.index(self.ultim) if self.ultim in nume_b else 0)
            if nume_b: lb.selection_set(i); lb.see(i); previzualizare(cv, self.doc, nume_b[i])
        lb.bind("<<ListboxSelect>>", lambda e: previzualizare(cv, self.doc, lb.get(lb.curselection()[0])) if lb.curselection() else None)
        f = tk.Frame(dr, bg=CORP); f.pack(fill="x")
        def camp(t, v):
            tk.Label(f, text=t, bg=CORP, fg=TEXT, font=F_MIC).pack(anchor="w")
            e = tk.Entry(f, bg="#2b313a", fg=TEXT, insertbackground=TEXT, relief="flat", width=12); e.insert(0, str(v)); e.pack(anchor="w", pady=(0, 6)); return e
        es = camp("Масштаб:", self.scara); er = camp("Поворот (°):", self.rot)
        def din_fisier():
            n = self.importa_biblioteca(parent=d)
            if n: umple(n)
        def ok(e=None):
            if not lb.curselection(): return
            try: self.scara = float(es.get().replace(",", ".")); self.rot = float(er.get().replace(",", "."))
            except ValueError: return messagebox.showerror("Вставка", "Масштаб и поворот – числа.", parent=d)
            n = lb.get(lb.curselection()[0]); d.destroy(); self.incepe_inserare(n)
        lb.bind("<Double-Button-1>", ok)
        for t, c in (("Из библиотеки (DWG/DXF)...", din_fisier), ("Вставить", ok), ("Отмена", d.destroy)):
            b = tk.Label(dr, text=t, bg=ALBASTRU if t == "Вставить" else FILE, fg="white", font=F_MIC, padx=10, pady=5); b.pack(fill="x", pady=3)
            b.bind("<Button-1>", lambda e, c=c: c())
        umple(nume)
        if not blocuri(self.doc): self.app.mesaj("В чертеже нет блоков — нажмите «Из библиотеки» и выберите DWG/DXF с символами.")

    def incepe_inserare(self, nume):
        self.ultim = nume
        self.app.ed.incepe("ВСТАВКА", f"ВСТАВКА «{nume}»  Точка вставки:", nevoie_sel=False, bloc=nume)

    def insereaza(self, nume, p):
        """apelat de editare când se dă clic pentru punctul de inserare"""
        blk = self.doc.blocks.get(nume); atrdef = [e for e in blk if e.dxftype() == "ATTDEF"]
        valori = {a.dxf.tag: a.dxf.text for a in atrdef}
        def pune(val):
            self.app.ed.instantaneu()
            ins = self.doc.modelspace().add_blockref(nume, p, dxfattribs={"layer": self.app.strat_curent(), "xscale": self.scara, "yscale": self.scara, "rotation": self.rot})
            if val: ins.add_auto_attribs(val)
            self.app.ed.sel = {ins.dxf.handle}; self.app.ed.gata_modificare(f"Вставлен блок «{nume}».")
        if not atrdef: return pune({})
        d = tk.Toplevel(self.app.root); d.title(f"Атрибуты – {nume}"); d.configure(bg=CORP); d.transient(self.app.root); d.columnconfigure(1, weight=1)
        intr = {}
        for i, a in enumerate(atrdef):
            tk.Label(d, text=(a.dxf.get("prompt", "") or a.dxf.tag) + ":", bg=CORP, fg=TEXT, font=F_MIC).grid(row=i, column=0, sticky="w", padx=10, pady=4)
            e = tk.Entry(d, bg="#2b313a", fg=TEXT, insertbackground=TEXT, relief="flat", width=30); e.insert(0, a.dxf.text); e.grid(row=i, column=1, sticky="we", padx=10, pady=4)
            intr[a.dxf.tag] = e
        list(intr.values())[0].focus_set()
        def ok(e=None):
            val = {k: w.get() for k, w in intr.items()}; d.destroy(); pune(val)
        b = tk.Label(d, text="OK", bg=ALBASTRU, fg="white", font=F_MIC, padx=16, pady=4); b.grid(row=len(atrdef), column=1, sticky="e", padx=10, pady=10)
        b.bind("<Button-1>", ok); d.bind("<Return>", ok)

    # ---------------------------------------------------------------- creare bloc din selecție
    def creeaza(self):
        ed = self.app.ed
        if not ed.sel: return self.app.mesaj("БЛОК: выберите объекты для символа, затем команду.")
        d = tk.Toplevel(self.app.root); d.title("Определение блока"); d.configure(bg=CORP); d.transient(self.app.root)
        tk.Label(d, text="Имя блока:", bg=CORP, fg=TEXT, font=F_MIC).grid(row=0, column=0, padx=10, pady=8)
        e = tk.Entry(d, bg="#2b313a", fg=TEXT, insertbackground=TEXT, relief="flat", width=30); e.grid(row=0, column=1, padx=10, pady=8); e.focus_set()
        tk.Label(d, text="После OK укажите базовую точку на чертеже.", bg=CORP, fg=GRI, font=F_MIC).grid(row=1, column=0, columnspan=2, padx=10)
        def ok(ev=None):
            n = e.get().strip()
            if not n: return
            if n in self.doc.blocks: return messagebox.showerror("Блок", f"Блок «{n}» уже существует.", parent=d)
            d.destroy(); ed.incepe("БЛОКБАЗА", f"БЛОК «{n}»  Базовая точка:", bloc=n)
        b = tk.Label(d, text="OK", bg=ALBASTRU, fg="white", font=F_MIC, padx=16, pady=4); b.grid(row=2, column=1, sticky="e", padx=10, pady=10)
        b.bind("<Button-1>", ok); d.bind("<Return>", ok)

    def termina_bloc(self, nume, p):
        ed = self.app.ed; ed.instantaneu(); msp = self.doc.modelspace()
        blk = self.doc.blocks.new(nume, base_point=(0, 0))
        for h in list(ed.sel):
            e = ed.ent(h)
            if e is None: continue
            c = e.copy(); c.translate(-p[0], -p[1], 0); blk.add_entity(c); msp.delete_entity(e)
        ins = msp.add_blockref(nume, p, dxfattribs={"layer": self.app.strat_curent()})
        ed.sel = {ins.dxf.handle}; ed.gata_modificare(f"Создан блок «{nume}» ({len(blk)} объектов).")

    # ---------------------------------------------------------------- înlocuire bloc
    def inlocuieste(self):
        ed = self.app.ed
        ins = [ed.ent(h) for h in ed.sel]; ins = [e for e in ins if e is not None and e.dxftype() == "INSERT"]
        if not ins: return self.app.mesaj("ЗАМЕНИТЬ: выберите блоки, которые нужно заменить.")
        d = tk.Toplevel(self.app.root); d.title("Заменить блок"); d.configure(bg=CORP); d.transient(self.app.root); d.geometry("420x360")
        tk.Label(d, text=f"Выбрано блоков: {len(ins)}. Заменить на:", bg=CORP, fg=TEXT, font=F_MIC).pack(anchor="w", padx=10, pady=6)
        lb = tk.Listbox(d, bg="#2b313a", fg=TEXT, selectbackground=ACTIV, relief="flat", font=F_MIC); lb.pack(fill="both", expand=True, padx=10)
        for n in blocuri(self.doc): lb.insert("end", n)
        def ok(e=None):
            if not lb.curselection(): return
            n = lb.get(lb.curselection()[0]); d.destroy(); ed.instantaneu(); msp = self.doc.modelspace(); noi = set()
            for e in ins:
                val = {a.dxf.tag: a.dxf.text for a in e.attribs}
                at = {k: e.dxf.get(k) for k in ("layer", "xscale", "yscale", "rotation", "color") if e.dxf.hasattr(k)}
                nou = msp.add_blockref(n, e.dxf.insert, dxfattribs=at)
                if any(x.dxftype() == "ATTDEF" for x in self.doc.blocks.get(n)): nou.add_auto_attribs(val)
                msp.delete_entity(e); noi.add(nou.dxf.handle)
            ed.sel = noi; ed.gata_modificare(f"Заменено блоков: {len(noi)} → «{n}»")
        lb.bind("<Double-Button-1>", ok)
        b = tk.Label(d, text="Заменить", bg=ALBASTRU, fg="white", font=F_MIC, padx=16, pady=4); b.pack(anchor="e", padx=10, pady=10); b.bind("<Button-1>", ok)

    # ---------------------------------------------------------------- simboluri din alt desen
    def importa_biblioteca(self, parent=None):
        p = filedialog.askopenfilename(parent=parent, title="Библиотека символов (DWG/DXF)", filetypes=[("Чертеж", "*.dwg *.dxf")])
        if not p: return None
        try: src = fisiere.deschide(p)
        except Exception as ex: messagebox.showerror("Библиотека", str(ex), parent=parent); return None
        nume = blocuri(src)
        if not nume: messagebox.showinfo("Библиотека", "В файле нет блоков.", parent=parent); return None
        d = tk.Toplevel(parent or self.app.root); d.title("Блоки из " + os.path.basename(p)); d.configure(bg=CORP); d.geometry("520x420")
        st = tk.Frame(d, bg=CORP); st.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        lb = tk.Listbox(st, bg="#2b313a", fg=TEXT, selectbackground=ACTIV, relief="flat", font=F_MIC, selectmode="extended"); lb.pack(fill="both", expand=True)
        for n in nume: lb.insert("end", n)
        cv = tk.Canvas(d, width=180, height=150, bg="#212830", highlightthickness=1, highlightbackground=SEP); cv.pack(side="top", padx=10, pady=10)
        lb.bind("<<ListboxSelect>>", lambda e: previzualizare(cv, src, lb.get(lb.curselection()[-1])) if lb.curselection() else None)
        rez = {"n": None}
        def ok(e=None):
            alese = [lb.get(i) for i in lb.curselection()] or nume
            from ezdxf.addons import Importer
            self.app.ed.instantaneu(); imp = Importer(src, self.doc); imp.import_blocks(alese); imp.finalize()
            rez["n"] = alese[0]; d.destroy(); self.app.mesaj(f"Импортировано блоков: {len(alese)} из {os.path.basename(p)}"); self.app.marcheaza()
        lb.bind("<Double-Button-1>", ok)
        b = tk.Label(d, text="Импортировать", bg=ALBASTRU, fg="white", font=F_MIC, padx=12, pady=5); b.pack(side="top", padx=10, fill="x"); b.bind("<Button-1>", ok)
        d.wait_window()
        return rez["n"]
