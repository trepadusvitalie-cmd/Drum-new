"""Fibra Visio – fereastra: schema în stânga, chatul în dreapta. Deschizi un .vsdx, scrii ce să facă, salvezi."""
import os, re, shutil, sys, traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import vsdx_doc, desen, comenzi

TITLU = "Fibra Visio"
CUL_INDEX = {0: "#000000", 1: "#FFFFFF", 2: "#FF0000", 3: "#00FF00", 4: "#0000FF", 5: "#FFFF00", 6: "#FF00FF", 7: "#00FFFF",
             8: "#800000", 9: "#008000", 10: "#000080", 11: "#808000", 12: "#800080", 13: "#008080", 14: "#C0C0C0", 15: "#808080"}


def culoare(v, implicit):
    if not v: return implicit
    if v.startswith("#") and len(v) == 7: return v
    if re.fullmatch(r"\d+", v): return CUL_INDEX.get(int(v), implicit)
    m = re.match(r"RGB\((\d+),\s*(\d+),\s*(\d+)\)", v)
    if m: return "#%02X%02X%02X" % tuple(int(x) for x in m.groups())
    return implicit


class App:
    def __init__(self, root):
        self.root = root; self.doc = None; self.chat = None; self.modificat = False
        self.zoom = 50.0; self.ox = 20; self.oy = 20; self.istoric_cmd = []; self.ih = 0
        root.title(TITLU); root.geometry("1400x850")
        bar = ttk.Frame(root); bar.pack(fill="x", padx=6, pady=4)
        ttk.Button(bar, text="Deschide schema…", command=self.deschide).pack(side="left")
        ttk.Button(bar, text="Schemă nouă", command=self.nou).pack(side="left", padx=4)
        ttk.Button(bar, text="Salvează", command=self.salveaza).pack(side="left")
        ttk.Button(bar, text="Salvează ca…", command=self.salveaza_ca).pack(side="left", padx=4)
        ttk.Label(bar, text="   Pagina:").pack(side="left")
        self.cb_pag = ttk.Combobox(bar, state="readonly", width=28); self.cb_pag.pack(side="left"); self.cb_pag.bind("<<ComboboxSelected>>", self.alege_pagina)
        ttk.Label(bar, text="   Cablu nou:").pack(side="left")
        self.cb_stil = ttk.Combobox(bar, state="readonly", width=20, values=["roșu", "linie întreruptă", "roșu întrerupt", "ca cele existente"])
        self.cb_stil.current(0); self.cb_stil.pack(side="left"); self.cb_stil.bind("<<ComboboxSelected>>", self.stil_cablu)
        ttk.Button(bar, text="Potrivește", command=self.potriveste).pack(side="right")
        pw = ttk.PanedWindow(root, orient="horizontal"); pw.pack(fill="both", expand=True); self.pw = pw
        st = ttk.Frame(pw); pw.add(st, weight=3)
        self.cv = tk.Canvas(st, bg="#B0B0B0", highlightthickness=0); self.cv.pack(fill="both", expand=True)
        self.cv.bind("<MouseWheel>", self.roata); self.cv.bind("<Button-4>", lambda e: self.zoom_la(e, 1.15)); self.cv.bind("<Button-5>", lambda e: self.zoom_la(e, 1 / 1.15))
        self.cv.bind("<ButtonPress-1>", self.start_drag); self.cv.bind("<B1-Motion>", self.drag); self.cv.bind("<Configure>", lambda e: self.deseneaza())
        dr = ttk.Frame(pw, width=430); pw.add(dr, weight=1)
        self.txt = tk.Text(dr, wrap="word", state="disabled", font=("Segoe UI", 10), bg="#FAFAFA", relief="flat", padx=8, pady=8)
        sb = ttk.Scrollbar(dr, command=self.txt.yview); self.txt.configure(yscrollcommand=sb.set)
        jos = ttk.Frame(dr); jos.pack(side="bottom", fill="x", padx=4, pady=4)
        sb.pack(side="right", fill="y"); self.txt.pack(fill="both", expand=True)
        self.txt.tag_config("eu", foreground="#1F4E79", font=("Segoe UI", 10, "bold")); self.txt.tag_config("prog", foreground="#202020")
        self.txt.tag_config("err", foreground="#C00000")
        self.ent = tk.Text(jos, height=3, wrap="word", font=("Segoe UI", 11)); self.ent.pack(side="left", fill="x", expand=True)
        ttk.Button(jos, text="Trimite", command=self.trimite).pack(side="left", padx=4, fill="y")
        self.ent.bind("<Return>", lambda e: (self.trimite(), "break")[1]); self.ent.bind("<Shift-Return>", lambda e: None)
        self.ent.bind("<Up>", self.cmd_sus); self.ent.bind("<Down>", self.cmd_jos)
        self.status = ttk.Label(root, text="Deschide o schemă .vsdx sau începe una nouă.", anchor="w"); self.status.pack(fill="x", padx=6, pady=2)
        root.protocol("WM_DELETE_WINDOW", self.inchide)
        self.scrie("Bună! Deschide o schemă Visio (.vsdx) sau apasă „Schemă nouă”, apoi scrie aici ce să fac.\n"
                   "Scrie „ajutor” ca să vezi exemple de comenzi.", "prog")
        self.ent.focus_set()
        root.after(100, lambda: self.pw.sashpos(0, int(root.winfo_width() * 0.66)))

    # ---------- chat ----------
    def scrie(self, s, tag):
        self.txt.configure(state="normal"); self.txt.insert("end", ("Tu: " if tag == "eu" else "") + s + "\n\n", tag)
        self.txt.configure(state="disabled"); self.txt.see("end")

    def trimite(self):
        m = self.ent.get("1.0", "end").strip()
        if not m: return
        self.ent.delete("1.0", "end"); self.istoric_cmd.append(m); self.ih = len(self.istoric_cmd)
        self.scrie(m, "eu")
        if comenzi.fara_diacritice(m).lower().strip(" .!") in ("salveaza", "salveaza schema", "save"):
            self.salveaza(); return
        if self.doc is None:
            if comenzi.fara_diacritice(m).lower().strip() in ("ajutor", "help", "?"): self.scrie(comenzi.AJUTOR, "prog")
            else: self.scrie("Întâi deschide o schemă (butonul „Deschide schema…”) sau apasă „Schemă nouă”.", "err")
            return
        ip0 = self.chat.ip
        try:
            for linie in [x for x in re.split(r"\n+", m) if x.strip()]:             # mai multe comenzi, câte una pe rând
                r, sch = self.chat.raspunde(linie)
                self.scrie(r, "err" if r.startswith(("N-am", "Nu am înțeles", "Nu găsesc")) else "prog")
                if sch and not r.startswith("N-am"): self.modificat = True
        except Exception:
            self.scrie("Eroare: " + traceback.format_exc(limit=2), "err")
        self.actualizeaza_pagini()
        self.potriveste()

    def cmd_sus(self, e):
        if self.istoric_cmd and self.ih > 0:
            self.ih -= 1; self.ent.delete("1.0", "end"); self.ent.insert("1.0", self.istoric_cmd[self.ih])
        return "break"

    def cmd_jos(self, e):
        if self.ih < len(self.istoric_cmd) - 1:
            self.ih += 1; self.ent.delete("1.0", "end"); self.ent.insert("1.0", self.istoric_cmd[self.ih])
        return "break"

    # ---------- fișiere ----------
    def intreaba_salvare(self):
        if self.doc is not None and self.modificat:
            r = messagebox.askyesnocancel(TITLU, "Schema are modificări nesalvate. Le salvez?")
            if r is None: return False
            if r: return self.salveaza()
        return True

    def deschide(self):
        if not self.intreaba_salvare(): return
        p = filedialog.askopenfilename(title="Deschide schema Visio", filetypes=[("Visio", "*.vsdx"), ("Toate", "*.*")])
        if p: self.deschide_cale(p)

    def deschide_cale(self, p):
        if p.lower().endswith(".vsd"):
            messagebox.showwarning(TITLU, "Fișierele .vsd (format vechi) nu se pot modifica. Deschide-l în Visio și salvează-l ca .vsdx."); return
        try:
            self.doc = vsdx_doc.Document(p)
        except Exception as e:
            messagebox.showerror(TITLU, f"Nu pot deschide fișierul:\n{e}"); return
        self.chat = comenzi.Chat(self.doc); self.modificat = False; self.backup_facut = False
        self.root.title(f"{TITLU} – {os.path.basename(p)}"); self.actualizeaza_pagini(); self.potriveste()
        S = self.chat.schema
        self.scrie(f"Am deschis „{os.path.basename(p)}”: {len(self.doc.pagini)} pagini; pe prima, {len(S.elemente())} elemente cu nume și {len(S.cabluri())} linii.", "prog")

    def nou(self):
        if not self.intreaba_salvare(): return
        self.doc = vsdx_doc.Document(); self.chat = comenzi.Chat(self.doc); self.modificat = False; self.backup_facut = False
        self.root.title(f"{TITLU} – schemă nouă"); self.actualizeaza_pagini(); self.potriveste()
        self.scrie("Am început o schemă nouă (A3 culcat). Exemplu: „adaugă ODF ODF-1 48 porturi”.", "prog")

    def salveaza(self):
        if self.doc is None: return False
        if not self.doc.path: return self.salveaza_ca()
        try:
            if not getattr(self, "backup_facut", False) and os.path.exists(self.doc.path):   # copia originalului, o singură dată
                b = os.path.splitext(self.doc.path)[0] + "_original.vsdx"
                if not os.path.exists(b): shutil.copy2(self.doc.path, b)
                self.backup_facut = True
            self.doc.salveaza(self.doc.path)
        except PermissionError:
            messagebox.showerror(TITLU, "Nu pot scrie fișierul – probabil e deschis în Visio. Închide-l acolo sau folosește „Salvează ca…”."); return False
        self.modificat = False; self.status.config(text=f"Salvat: {self.doc.path}")
        self.scrie(f"Am salvat „{os.path.basename(self.doc.path)}”. (Originalul e păstrat ca …_original.vsdx)", "prog")
        return True

    def salveaza_ca(self):
        if self.doc is None: return False
        p = filedialog.asksaveasfilename(title="Salvează schema", defaultextension=".vsdx", filetypes=[("Visio", "*.vsdx")],
                                         initialfile=os.path.basename(self.doc.path) if self.doc.path else "schema_fibra.vsdx")
        if not p: return False
        try: self.doc.salveaza(p)
        except PermissionError:
            messagebox.showerror(TITLU, "Nu pot scrie fișierul – probabil e deschis în Visio."); return False
        self.modificat = False; self.backup_facut = True; self.root.title(f"{TITLU} – {os.path.basename(p)}")
        self.status.config(text=f"Salvat: {p}"); self.scrie(f"Am salvat „{os.path.basename(p)}”.", "prog"); return True

    def inchide(self):
        if self.intreaba_salvare(): self.root.destroy()

    def stil_cablu(self, e=None):
        v = self.cb_stil.get()
        desen.STIL_CABLU_NOU.update({"roșu": {"culoare": "#FF0000", "intrerupt": False}, "linie întreruptă": {"culoare": None, "intrerupt": True},
                                     "roșu întrerupt": {"culoare": "#FF0000", "intrerupt": True}, "ca cele existente": {"culoare": None, "intrerupt": False}}[v])
        self.scrie(f"Cablurile noi le desenez: {v}.", "prog")

    # ---------- pagini ----------
    def actualizeaza_pagini(self):
        if not self.doc: return
        self.cb_pag["values"] = [f"{i + 1}. {p.nume}" for i, p in enumerate(self.doc.pagini)]
        self.cb_pag.current(self.chat.ip)

    def alege_pagina(self, e=None):
        self.chat.ip = self.cb_pag.current(); self.potriveste()

    # ---------- desen ----------
    def ecran(self, x, y):
        H = self.doc.pagini[self.chat.ip].dimensiune()[1]
        return self.ox + x * self.zoom, self.oy + (H - y) * self.zoom

    def potriveste(self):
        """vederea pe desen (pe toată pagina, dacă e goală)"""
        if not self.doc: return
        p = self.doc.pagini[self.chat.ip]; W, H = p.dimensiune()
        x0, y0, x1, y1 = 0, 0, W, H
        try:
            bs = [f.cutie() for f in p.forme()]
            if bs:
                x0, y0 = min(b[0] for b in bs) - 0.5, min(b[1] for b in bs) - 0.5
                x1, y1 = max(b[2] for b in bs) + 0.5, max(b[3] for b in bs) + 0.5
        except Exception: pass
        cw, ch = max(self.cv.winfo_width(), 200), max(self.cv.winfo_height(), 200)
        self.zoom = min((cw - 40) / max(x1 - x0, 0.5), (ch - 40) / max(y1 - y0, 0.5))
        self.ox = (cw - (x1 - x0) * self.zoom) / 2 - x0 * self.zoom
        self.oy = (ch - (y1 - y0) * self.zoom) / 2 - (H - y1) * self.zoom
        self.deseneaza()

    def deseneaza(self):
        cv = self.cv; cv.delete("all")
        if not self.doc: return
        p = self.doc.pagini[self.chat.ip]; W, H = p.dimensiune()
        x0, y0 = self.ecran(0, H); x1, y1 = self.ecran(W, 0)
        cv.create_rectangle(x0 + 4, y0 + 4, x1 + 4, y1 + 4, fill="#808080", outline=""); cv.create_rectangle(x0, y0, x1, y1, fill="white", outline="#606060")
        try:
            for f in p.forme(): self.forma(f)
        except Exception:
            self.status.config(text="Unele forme nu se pot arăta în previzualizare (în Visio apar normal).")
        self.status.config(text=f"Pagina {self.chat.ip + 1}/{len(self.doc.pagini)} „{p.nume}” – rotița: zoom, trage cu mausul: mută vederea")

    def forma(self, f):
        lc = culoare(f.cell("LineColor"), "#000000"); fc = culoare(f.cell("FillForegnd"), "")
        lw = max(1, min(6, f.num("LineWeight", 0.01) * 72 * self.zoom / 50))
        dash = (5, 3) if (f.cell("LinePattern") or "1") not in ("1", "0") else None
        if f.cell("LinePattern") == "0": lc = ""
        for pts, plin in f.contur():
            xy = [c for x, y in pts for c in self.ecran(x, y)]
            if len(xy) < 4: continue
            if plin and fc and len(pts) > 2 and f.cell("FillPattern") != "0":
                self.cv.create_polygon(*xy, fill=fc, outline=lc or "", width=lw, dash=dash)
            elif lc:
                self.cv.create_line(*xy, fill=lc, width=lw, dash=dash)
        for c in f.copii: self.forma(c)
        t = f.text
        if t and self.zoom > 12:
            if f.cell("TxtPinX") is not None and not f.e1d:
                T = f.transforma(); x, y = T(f.num("TxtPinX"), f.num("TxtPinY"))
            elif f.e1d:
                x, y = (f.num("BeginX") + f.num("EndX")) / 2, (f.num("BeginY") + f.num("EndY")) / 2
                if f.parinte: x, y = f.parinte.transforma()(x, y)
            else: x, y = f.transforma()(f.num("Width") / 2, f.num("Height") / 2)
            sz = 0.1111
            ch = f.el.find(vsdx_doc.V + "Section[@N='Character']")
            if ch is not None:
                c = ch.find(vsdx_doc.V + "Row/" + vsdx_doc.V + "Cell[@N='Size']")
                if c is not None: sz = vsdx_doc.fnum(c.get("V"), sz)
            pt = max(6, min(28, int(sz * 72 * self.zoom / 72)))
            col = "#000000"
            if ch is not None:
                c = ch.find(vsdx_doc.V + "Row/" + vsdx_doc.V + "Cell[@N='Color']")
                if c is not None: col = culoare(c.get("V"), "#000000")
            X, Y = self.ecran(x, y)
            if f.e1d:
                it = self.cv.create_text(X, Y, text=t, font=("Segoe UI", pt), fill=col if col != "#FFFFFF" else "#000000")
                b = self.cv.bbox(it)
                if b: self.cv.tag_lower(self.cv.create_rectangle(b[0] - 1, b[1], b[2] + 1, b[3], fill="white", outline=""), it)
            else: self.cv.create_text(X, Y, text=t, font=("Segoe UI", pt), fill=col, justify="center")

    def roata(self, e): self.zoom_la(e, 1.15 if e.delta > 0 else 1 / 1.15)

    def zoom_la(self, e, k):
        self.ox = e.x - (e.x - self.ox) * k; self.oy = e.y - (e.y - self.oy) * k; self.zoom *= k; self.deseneaza()

    def start_drag(self, e): self.dx, self.dy = e.x, e.y

    def drag(self, e):
        self.ox += e.x - self.dx; self.oy += e.y - self.dy; self.dx, self.dy = e.x, e.y; self.deseneaza()


def main():
    root = tk.Tk()
    try: root.tk.call("tk", "scaling", 1.25)
    except Exception: pass
    app = App(root)
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):                       # dublu-clic pe un .vsdx / tras peste exe
        root.after(200, lambda: app.deschide_cale(sys.argv[1]))
    root.mainloop()


if __name__ == "__main__":
    main()
