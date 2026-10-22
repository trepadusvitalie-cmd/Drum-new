"""Fibra Visio – fereastra: schema în stânga, chatul în dreapta. Deschizi un .vsdx, scrii ce să facă, salvezi."""
import copy, math, os, re, shutil, sys, traceback
import xml.etree.ElementTree as ET
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


ACCENT = "#0F6CBD"; FUNDAL = "#F3F3F3"; PANOU = "#FFFFFF"; BULA_EU = "#DCEBFA"; BULA_PROG = "#F1F3F5"; BULA_ERR = "#FDE7E9"


class App:
    def __init__(self, root):
        self.root = root; self.doc = None; self.chat = None; self.modificat = False; self.orig_vsd = None
        self.zoom = 50.0; self.ox = 20; self.oy = 20; self.istoric_cmd = []; self.ih = 0
        root.title(TITLU); root.geometry("1440x880"); root.minsize(1000, 600)
        try:
            import sv_ttk; sv_ttk.set_theme("light")                    # tema Windows 11 (Sun Valley)
        except Exception:
            ttk.Style().theme_use("clam")
        st = ttk.Style(); FONT = ("Segoe UI", 10)
        st.configure(".", font=FONT); st.configure("Titlu.TLabel", font=("Segoe UI Semibold", 14), foreground=ACCENT)
        st.configure("Mic.TLabel", font=("Segoe UI", 9), foreground="#606060")
        # --- bara de sus ---
        bar = ttk.Frame(root, padding=(10, 8)); bar.pack(fill="x")
        ttk.Label(bar, text="◈ Fibra Visio", style="Titlu.TLabel").pack(side="left", padx=(0, 16))
        for txt, cmd in (("📂  Deschide", self.deschide), ("＋  Schemă nouă", self.nou), ("💾  Salvează", self.salveaza), ("Salvează ca…", self.salveaza_ca)):
            ttk.Button(bar, text=txt, command=cmd).pack(side="left", padx=3)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=12)
        ttk.Label(bar, text="Pagina", style="Mic.TLabel").pack(side="left", padx=(0, 4))
        self.cb_pag = ttk.Combobox(bar, state="readonly", width=26); self.cb_pag.pack(side="left"); self.cb_pag.bind("<<ComboboxSelected>>", self.alege_pagina)
        ttk.Label(bar, text="Cablu nou", style="Mic.TLabel").pack(side="left", padx=(14, 4))
        self.cb_stil = ttk.Combobox(bar, state="readonly", width=17, values=["roșu", "linie întreruptă", "roșu întrerupt", "ca cele existente"])
        self.cb_stil.current(0); self.cb_stil.pack(side="left"); self.cb_stil.bind("<<ComboboxSelected>>", self.stil_cablu)
        ttk.Button(bar, text="⤢  Potrivește", command=self.potriveste).pack(side="right")
        st.configure("Sag.TButton", font=("Segoe UI", 15), padding=(10, 0))
        ttk.Button(bar, text="→", width=3, style="Sag.TButton", command=self.inainte).pack(side="right", padx=(4, 10))
        ttk.Button(bar, text="←", width=3, style="Sag.TButton", command=self.anuleaza_chat).pack(side="right")
        # --- schema | chat ---
        pw = ttk.PanedWindow(root, orient="horizontal"); pw.pack(fill="both", expand=True, padx=8, pady=(0, 4)); self.pw = pw
        stg = ttk.Frame(pw); pw.add(stg, weight=3)
        self.cv = tk.Canvas(stg, bg="#E6E8EB", highlightthickness=0); self.cv.pack(fill="both", expand=True)
        self.cv.bind("<MouseWheel>", self.roata); self.cv.bind("<Button-4>", lambda e: self.zoom_la(e, 1.15)); self.cv.bind("<Button-5>", lambda e: self.zoom_la(e, 1 / 1.15))
        self.cv.bind("<ButtonPress-1>", self.clic); self.cv.bind("<B1-Motion>", self.trage); self.cv.bind("<ButtonRelease-1>", self.elibereaza)
        self.cv.bind("<Double-Button-1>", self.editeaza_text)
        self.cv.bind("<ButtonRelease-3>", self.meniu)
        self.cv.bind("<F2>", self.editeaza_text); self.cv.bind("<Return>", self.editeaza_text)
        for b in ("2", "3"):
            self.cv.bind(f"<ButtonPress-{b}>", self.pan_start); self.cv.bind(f"<B{b}-Motion>", self.pan)
        self.cv.bind("<Configure>", lambda e: self.deseneaza())
        self.selectie = []; self.mod = None; self.clipboard = []
        for k, fn in (("<Control-c>", self.copiaza), ("<Control-C>", self.copiaza), ("<Control-v>", self.lipeste), ("<Control-V>", self.lipeste),
                      ("<Delete>", self.sterge_selectia), ("<Control-z>", self.anuleaza), ("<Control-Z>", self.anuleaza), ("<Control-y>", self.inainte_tasta), ("<Control-Y>", self.inainte_tasta), ("<Control-a>", self.selecteaza_tot),
                      ("<Control-s>", lambda e: self.salveaza()), ("<Control-o>", lambda e: self.deschide())):
            root.bind(k, fn)
        for k in ("<Left>", "<Right>", "<Up>", "<Down>"): self.cv.bind(k, self.sageti)
        dr = tk.Frame(pw, bg=PANOU, width=440); pw.add(dr, weight=1)
        cap = tk.Frame(dr, bg=PANOU); cap.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(cap, text="Chat", bg=PANOU, fg="#202020", font=("Segoe UI Semibold", 12)).pack(side="left")
        tk.Label(cap, text="scrie liber, fără diacritice", bg=PANOU, fg="#808080", font=("Segoe UI", 9)).pack(side="left", padx=8)
        jos = tk.Frame(dr, bg=PANOU); jos.pack(side="bottom", fill="x", padx=10, pady=10)
        self.lb_sug = tk.Listbox(jos, height=6, font=("Segoe UI", 10), activestyle="none", relief="flat", bd=0, highlightthickness=1,
                                 highlightbackground="#C7CDD4", selectbackground=ACCENT, selectforeground="white")
        self.lb_sug.bind("<ButtonRelease-1>", lambda e: self.accepta_sugestie()); self.sug_vizibil = False; self.termeni = []
        chips = tk.Frame(jos, bg=PANOU); chips.pack(fill="x", pady=(0, 6)); self.chips = chips
        self.ghid = tk.Label(jos, text="", bg=PANOU, fg="#5B6470", font=("Segoe UI", 9), anchor="w", justify="left", wraplength=400)
        self.ghid.pack(fill="x", pady=(0, 4))
        for c in ("porturi", "lista", "cabluri", "inapoi", "inainte", "ajutor"):
            b = tk.Label(chips, text=c, bg="#EEF2F6", fg="#334155", font=("Segoe UI", 9), padx=10, pady=3, cursor="hand2")
            b.pack(side="left", padx=(0, 6)); b.bind("<Button-1>", lambda e, c=c: self.trimite_text(c))
        cad = tk.Frame(jos, bg="#C7CDD4", padx=1, pady=1); cad.pack(fill="x")
        rand = tk.Frame(cad, bg="white"); rand.pack(fill="x")
        self.ent = tk.Text(rand, height=3, wrap="word", font=("Segoe UI", 11), relief="flat", bd=0, padx=8, pady=6, highlightthickness=0)
        self.ent.pack(side="left", fill="x", expand=True)
        trim = tk.Label(rand, text="➤", bg=ACCENT, fg="white", font=("Segoe UI", 14), padx=14, cursor="hand2"); trim.pack(side="right", fill="y")
        trim.bind("<Button-1>", lambda e: self.trimite())
        self.ent.bind("<Return>", self.enter); self.ent.bind("<Shift-Return>", lambda e: None)
        self.ent.bind("<Up>", self.cmd_sus); self.ent.bind("<Down>", self.cmd_jos)
        self.ent.bind("<KeyRelease>", self.sugereaza); self.ent.bind("<Tab>", lambda e: self.accepta_sugestie() or "break")
        self.ent.bind("<Escape>", lambda e: self.ascunde_sugestii())
        corp = tk.Frame(dr, bg=PANOU); corp.pack(fill="both", expand=True, padx=(10, 4))
        self.txt = tk.Text(corp, wrap="word", state="disabled", font=("Segoe UI", 10), bg=PANOU, relief="flat", bd=0, padx=4, pady=4,
                           highlightthickness=0, spacing1=2, spacing3=2)
        sb = ttk.Scrollbar(corp, command=self.txt.yview); self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); self.txt.pack(fill="both", expand=True)
        self.txt.tag_config("eu", background=BULA_EU, foreground="#0B3B66", lmargin1=70, lmargin2=70, rmargin=6, spacing1=6, spacing3=6,
                            font=("Segoe UI", 10), justify="left")
        self.txt.tag_config("prog", background=BULA_PROG, foreground="#202020", lmargin1=6, lmargin2=6, rmargin=50, spacing1=6, spacing3=6)
        self.txt.tag_config("err", background=BULA_ERR, foreground="#A4262C", lmargin1=6, lmargin2=6, rmargin=50, spacing1=6, spacing3=6)
        self.txt.tag_config("cine", foreground="#808080", font=("Segoe UI", 8), spacing1=8)
        self.txt.tag_config("cine_eu", justify="right", rmargin=8)
        self.txt.tag_config("var", foreground=ACCENT, font=("Segoe UI", 10, "underline"), lmargin1=14, lmargin2=14, spacing1=3)
        self.status = ttk.Label(root, text="Deschide o schemă .vsdx / .vsd (sau trage fișierul aici) ori începe una nouă.", anchor="w",
                                style="Mic.TLabel", padding=(10, 3)); self.status.pack(fill="x")
        root.protocol("WM_DELETE_WINDOW", self.inchide)
        self.scrie("Bună! Deschide o schemă Visio (.vsdx sau .vsd) – sau trage fișierul peste fereastră – apoi scrie aici ce să fac.\n"
                   "Scrie „ajutor” ca să vezi exemple.", "prog")
        self.activeaza_drop()
        self.ent.focus_set()
        root.after(150, lambda: self.pw.sashpos(0, int(root.winfo_width() * 0.68)))

    def activeaza_drop(self):
        """drag & drop: tragi un .vsdx / .vsd peste fereastră și se deschide"""
        try:
            from tkinterdnd2 import DND_FILES
            for w in (self.root, self.cv, self.txt, self.ent):
                w.drop_target_register(DND_FILES); w.dnd_bind("<<Drop>>", self.la_drop)
        except Exception:
            pass

    def la_drop(self, e):
        fis = self.root.tk.splitlist(e.data)
        fis = [f for f in fis if f.lower().endswith((".vsdx", ".vsd"))]
        if not fis: self.scrie("Trage un fișier Visio (.vsdx sau .vsd).", "err"); return
        if self.intreaba_salvare(): self.deschide_cale(fis[0])

    def scrie_variante(self, var):
        """variantele corecte, ca butoane în chat: clic (sau cifra) și se execută"""
        self.txt.configure(state="normal")
        for i, v in enumerate(var, 1):
            tg = f"var_{id(var)}_{i}"
            self.txt.insert("end", f"  {i}.  {v}  \n", ("var", tg))
            self.txt.tag_bind(tg, "<Button-1>", lambda e, v=v: self.trimite_text(v))
            self.txt.tag_bind(tg, "<Enter>", lambda e, tg=tg: (self.txt.tag_config(tg, background="#CFE3FA"), self.txt.config(cursor="hand2")))
            self.txt.tag_bind(tg, "<Leave>", lambda e, tg=tg: (self.txt.tag_config(tg, background=""), self.txt.config(cursor="")))
        self.txt.insert("end", "  (apasă pe variantă sau scrie cifra ei)\n", ("cine",))
        self.txt.configure(state="disabled"); self.txt.see("end")

    def trimite_text(self, s):
        self.ent.delete("1.0", "end"); self.ent.insert("1.0", s); self.trimite()

    # ---------- chat ----------
    def scrie(self, s, tag):
        self.txt.configure(state="normal")
        self.txt.insert("end", ("Tu" if tag == "eu" else "Fibra Visio") + "\n", ("cine", "cine_eu") if tag == "eu" else ("cine",))
        self.txt.insert("end", " " + s.strip() + " \n", tag)
        self.txt.configure(state="disabled"); self.txt.see("end")

    def trimite(self):
        m = self.ent.get("1.0", "end").strip()
        if not m: return
        self.ent.delete("1.0", "end"); self.istoric_cmd.append(m); self.ih = len(self.istoric_cmd)
        self.scrie(m, "eu")
        cm = comenzi.fara_diacritice(m).lower().strip(" .!")
        if cm in ("anuleaza", "undo", "inapoi", "reface", "redo", "inainte") and self.doc is not None:
            r, sch = self.chat.inapoi() if cm in ("anuleaza", "undo", "inapoi") else self.chat.inainte()
            self.scrie(r, "prog")
            if sch: self.selectie = []; self.termeni = []; self.actualizeaza_pagini(); self.deseneaza(); self.modificat = True
            return
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
                if self.chat.variante: self.scrie_variante(self.chat.variante)
                if sch and not r.startswith("N-am"): self.modificat = True
        except Exception:
            self.scrie("Eroare: " + traceback.format_exc(limit=2), "err")
        self.actualizeaza_pagini(); self.selectie = []; self.termeni = []; self.ascunde_sugestii()
        self.deseneaza() if self.chat.ip == ip0 else self.potriveste()

    # ---------- sugestii în timp ce scrii ----------
    VOCAB = ["port", "porturile", "la", "prin", "sudura in", "rosu", "albastru", "verde", "intrerupt", "trage", "adauga", "leaga",
             "manson", "stalp", "odf", "splitter", "cablu", "sterge", "muta", "redenumeste", "schimba lungimea", "anuleaza",
             "salveaza", "lista", "cabluri", "porturi", "pagini", "pagina", "ajutor"]

    def actualizeaza_termeni(self):
        """numele din proiect (toate paginile): noduri, manșoane, elemente, cabluri – pentru sugestii"""
        t = []
        try:
            import porturi
            for i in range(len(self.doc.pagini)):
                S = desen.Schema(self.doc, self.doc.pagini[i])
                for nume, _ in porturi._candidati(S): t.append(nume)
                for x, _ in S.elemente():
                    l0 = x.split("\n")[0].strip()
                    if l0 and len(l0) <= 30 and not re.fullmatch(r"[\d,.\s]+", l0): t.append(" ".join(x.split()) if re.match(r"(?i)^FO", x) else l0)
        except Exception: pass
        vaz = set(); self.termeni = []
        for x in t:
            k = vsdx_doc.norm(x)
            if k and k not in vaz: vaz.add(k); self.termeni.append(x)

    def cuvant_curent(self):
        inainte = self.ent.get("1.0", "insert")
        m = re.search(r"([\w\-.ăâîșşțţĂÂÎȘŞȚŢ]+(?: [\w\-.ăâîșşțţĂÂÎȘŞȚŢ]+)?)$", inainte)
        return inainte, m

    def ghideaza(self):
        """rândul de ajutor de deasupra căsuței: ce urmează de scris"""
        if not self.doc: self.ghid.config(text="Deschide întâi o schemă (📂 Deschide sau trage fișierul aici)."); return
        import porturi
        t = comenzi.fara_diacritice(self.ent.get("1.0", "end")).strip().lower()
        S = self.chat.schema
        try: noduri = porturi.noduri(S)
        except Exception: noduri = []
        nume = ", ".join(n.nume for n in noduri[:4])
        if not t:
            self.ghid.config(text=(f"Exemplu: {noduri[0].nume} port 1 la {noduri[1].nume} port 2   ·   " if len(noduri) > 1 else "")
                             + "adauga manson M5 langa M2   ·   lista   ·   ajutor"); return
        if re.match(r"(adauga|pune) (manson|stalp|odf|splitter|camin|bloc|cutie)\b", t):
            self.ghid.config(text="→ nume (ex. M5) + unde: langa M2 / la dreapta de M2 / sub M2"); return
        if re.match(r"(adauga|trage|pune) cablu", t):
            self.ghid.config(text="→ tip + capete + lungime:  24FO de la M1 la S5, 120 m   (optional: intrerupt)"); return
        if re.match(r"(sterge|muta|redenumeste|schimba)", t):
            self.ghid.config(text="→ sterge M5 · sterge cablul de la M1 la S5 · muta M5 la dreapta cu 2 cm · redenumeste M5 in M6 · schimba lungimea de la M1 la S5 in 80 m"); return
        if not noduri: self.ghid.config(text="Scrie „ajutor” pentru comenzi."); return
        try: men = porturi.mentiuni(S, t)
        except ValueError as e: self.ghid.config(text=f"⚠ {e}", fg="#A4262C"); return
        self.ghid.config(fg="#5B6470")
        cap = [m for m in men if m[3] is not None]
        if not cap: self.ghid.config(text=f"→ scrie nodul de pornire: {nume}…"); return
        A = cap[0][3]; dupa_a = t[cap[0][1]:]
        if len(cap) == 1:
            if not re.search(r"\d", t): self.ghid.config(text=f"→ portul la {A.nume}: port 1…{A.n}"); return
            alt = ", ".join(n.nume for n in noduri if n.nume != A.nume)[:80]
            self.ghid.config(text=f"→ „la” + nodul de destinație: {alt}"); return
        B = cap[1][3]
        if not re.search(r"\d", t[cap[1][1]:]) and not re.search(r"\d", t[:cap[0][0]]):
            self.ghid.config(text=f"→ portul la {B.nume}: port 1…{B.n}"); return
        self.ghid.config(text=f"✔ Gata – Enter: fibră {A.nume} → {B.nume}.  Opțional: rosu / albastru / intrerupt / prin M1 (sudură)", fg="#107C10")

    def sugereaza(self, e=None):
        try: self.ghideaza()
        except Exception: pass
        if e is not None and e.keysym in ("Up", "Down", "Return", "Tab", "Escape", "Shift_L", "Shift_R", "Control_L", "Control_R"): return
        if not self.doc: return
        if not self.termeni: self.actualizeaza_termeni()
        inainte, m = self.cuvant_curent()
        if not m or not re.search(r"[^\W\d_]", m.group(0)): return self.ascunde_sugestii()
        variante = []
        for frag in ([m.group(0)] + ([m.group(0).split(" ")[-1]] if " " in m.group(0) else [])):
            q = vsdx_doc.norm(frag)
            if not q: continue
            tot = self.termeni + self.VOCAB
            inc = [x for x in tot if vsdx_doc.norm(x).startswith(q)]
            cont = [x for x in tot if q in vsdx_doc.norm(x) and x not in inc]
            for x in inc + cont:
                if vsdx_doc.norm(x) != q and (x, frag) not in variante and x not in [v[0] for v in variante]: variante.append((x, frag))
            if variante: break
        if not variante: return self.ascunde_sugestii()
        self.variante = variante[:8]
        self.lb_sug.delete(0, "end")
        for x, _ in self.variante: self.lb_sug.insert("end", "  " + x)
        self.lb_sug.configure(height=len(self.variante)); self.lb_sug.selection_clear(0, "end"); self.lb_sug.selection_set(0); self.sug_ales = False
        if not self.sug_vizibil: self.lb_sug.pack(fill="x", pady=(0, 6), before=self.chips); self.sug_vizibil = True

    def ascunde_sugestii(self):
        if self.sug_vizibil: self.lb_sug.pack_forget(); self.sug_vizibil = False

    def accepta_sugestie(self):
        if not self.sug_vizibil: return False
        sel = self.lb_sug.curselection(); k = sel[0] if sel else 0
        x, frag = self.variante[k]
        self.ent.delete(f"insert-{len(frag)}c", "insert"); self.ent.insert("insert", x + " ")
        self.ascunde_sugestii(); self.ent.focus_set(); return True

    def enter(self, e):
        if self.sug_vizibil and getattr(self, "sug_ales", False): self.accepta_sugestie(); return "break"
        self.ascunde_sugestii(); self.trimite(); return "break"

    def cmd_sus(self, e):
        if self.sug_vizibil:
            sel = self.lb_sug.curselection(); k = max(0, (sel[0] if sel else 0) - 1)
            self.lb_sug.selection_clear(0, "end"); self.lb_sug.selection_set(k); self.lb_sug.see(k); self.sug_ales = True; return "break"
        if self.istoric_cmd and self.ih > 0:
            self.ih -= 1; self.ent.delete("1.0", "end"); self.ent.insert("1.0", self.istoric_cmd[self.ih])
        return "break"

    def cmd_jos(self, e):
        if self.sug_vizibil:
            sel = self.lb_sug.curselection(); k = min(self.lb_sug.size() - 1, (sel[0] if sel else -1) + 1)
            self.lb_sug.selection_clear(0, "end"); self.lb_sug.selection_set(k); self.lb_sug.see(k); self.sug_ales = True; return "break"
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
        p = filedialog.askopenfilename(title="Deschide schema Visio", filetypes=[("Visio", "*.vsdx *.vsd"), ("Visio nou", "*.vsdx"), ("Visio vechi", "*.vsd"), ("Toate", "*.*")])
        if p: self.deschide_cale(p)

    def deschide_cale(self, p):
        self.orig_vsd = None
        if p.lower().endswith(".vsd"):                                   # format vechi: îl convertește Visio-ul de pe calculator
            self.status.config(text="Convertesc .vsd → .vsdx cu Visio (câteva secunde)…"); self.root.update()
            try:
                import vsd_convert
                tmp = vsd_convert.vsd_in_vsdx(p)
            except Exception as e:
                messagebox.showerror(TITLU, "Fișierul .vsd e formatul vechi al Visio. Ca să-l deschid, am nevoie de Visio instalat pe calculator.\n"
                                     f"({e})\n\nAltfel: deschide-l în Visio → Fișier → Salvare ca → Visio Drawing (.vsdx)."); return
            self.orig_vsd = p
            try: self.doc = vsdx_doc.Document(tmp)
            except Exception as e:
                messagebox.showerror(TITLU, f"Nu pot deschide fișierul:\n{e}"); return
            self.doc.path = None                                           # „Salvează” scrie înapoi în .vsd (prin Visio)
        else:
            try:
                self.doc = vsdx_doc.Document(p)
            except Exception as e:
                messagebox.showerror(TITLU, f"Nu pot deschide fișierul:\n{e}"); return
        self.chat = comenzi.Chat(self.doc); self.modificat = False; self.backup_facut = False; self.selectie = []
        self.root.title(f"{TITLU} – {os.path.basename(p)}"); self.actualizeaza_pagini(); self.potriveste()
        self.termeni = []; self.analizeaza(); self.ghideaza()

    def nou(self):
        if not self.intreaba_salvare(): return
        self.doc = vsdx_doc.Document(); self.chat = comenzi.Chat(self.doc); self.modificat = False; self.backup_facut = False; self.selectie = []
        self.root.title(f"{TITLU} – schemă nouă"); self.actualizeaza_pagini(); self.potriveste()
        self.scrie("Am început o schemă nouă (A3 culcat). Exemplu: „adaugă ODF ODF-1 48 porturi”.", "prog")

    def salveaza(self):
        """salvează în același format în care a fost deschis (.vsdx → .vsdx, .vsd → .vsd); originalul se păstrează o dată ca …_original"""
        if self.doc is None: return False
        if not self.doc.path and not self.orig_vsd: return self.salveaza_ca()
        tinta = self.orig_vsd or self.doc.path
        try:
            if not getattr(self, "backup_facut", False) and os.path.exists(tinta):
                b = os.path.splitext(tinta)[0] + "_original" + os.path.splitext(tinta)[1]
                if not os.path.exists(b): shutil.copy2(tinta, b)
                self.backup_facut = True
            if self.orig_vsd:                                         # .vsd: îl scrie Visio-ul de pe calculator
                import tempfile, vsd_convert
                self.status.config(text="Salvez ca .vsd prin Visio…"); self.root.update()
                tmp = os.path.join(tempfile.mkdtemp(prefix="fibra_visio_"), "schema.vsdx"); self.doc.salveaza(tmp, pastreaza_cale=True)
                vsd_convert.converteste(tmp, tinta)
            else:
                self.doc.salveaza(tinta)
        except PermissionError:
            messagebox.showerror(TITLU, "Nu pot scrie fișierul – probabil e deschis în Visio. Închide-l acolo sau folosește „Salvează ca…”."); return False
        except Exception as e:
            messagebox.showerror(TITLU, f"Nu am putut salva:\n{e}"); return False
        self.modificat = False; self.status.config(text=f"Salvat: {tinta}")
        self.scrie(f"Am salvat „{os.path.basename(tinta)}” (același format). Originalul e păstrat ca …_original{os.path.splitext(tinta)[1]}.", "prog")
        return True

    def salveaza_ca(self):
        if self.doc is None: return False
        p = filedialog.asksaveasfilename(title="Salvează schema", filetypes=[("Visio (.vsdx)", "*.vsdx"), ("Visio 2003-2010 (.vsd)", "*.vsd")],
                                         initialfile=os.path.basename(self.orig_vsd or self.doc.path or "schema_fibra.vsdx"),
                                         defaultextension=os.path.splitext(self.orig_vsd)[1] if self.orig_vsd else ".vsdx")
        if not p: return False
        if p.lower().endswith(".vsd"):                                   # .vsd: salvez .vsdx temporar și îl convertește Visio
            try:
                import tempfile, vsd_convert
                tmp = os.path.join(tempfile.mkdtemp(prefix="fibra_visio_"), "schema.vsdx"); self.doc.salveaza(tmp, pastreaza_cale=True)
                vsd_convert.converteste(tmp, p)
            except Exception as e:
                messagebox.showerror(TITLU, f"Nu pot salva ca .vsd (am nevoie de Visio pe calculator):\n{e}"); return False
            self.orig_vsd = p; self.backup_facut = True
            self.modificat = False; self.status.config(text=f"Salvat: {p}"); self.scrie(f"Am salvat „{os.path.basename(p)}” (format .vsd).", "prog"); return True
        try: self.doc.salveaza(p); self.orig_vsd = None
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
        self.chat.ip = self.cb_pag.current(); self.selectie = []; self.potriveste(); self.analizeaza()

    def analizeaza(self):
        """la deschidere / schimbarea paginii: ce e pe schemă, ce nume pot folosi în chat"""
        import porturi
        try: self.scrie(porturi.analiza(self.chat.schema, os.path.basename(self.orig_vsd or self.doc.path or "schemă nouă")), "prog")
        except Exception as e: self.scrie(f"Am deschis schema ({len(self.doc.pagini)} pagini). Gata de lucru. (analiza: {e})", "prog")

    # ---------- desen (ca în Visio) ----------
    def ecran(self, x, y):
        H = self.doc.pagini[self.chat.ip].dimensiune()[1]
        return self.ox + x * self.zoom, self.oy + (H - y) * self.zoom

    def pagina_xy(self, X, Y):
        H = self.doc.pagini[self.chat.ip].dimensiune()[1]
        return (X - self.ox) / self.zoom, H - (Y - self.oy) / self.zoom

    def potriveste(self):
        """vederea pe desen (pe toată pagina, dacă e goală)"""
        if not self.doc: return
        p = self.doc.pagini[self.chat.ip]; W, H = p.dimensiune()
        x0, y0, x1, y1 = 0, 0, W, H
        try:
            bs = [f.cutie() for f in p.forme()]
            if bs:
                x0, y0 = min(min(b[0] for b in bs), 0) - 0.2, min(min(b[1] for b in bs), 0) - 0.2
                x1, y1 = max(max(b[2] for b in bs), W) + 0.2, max(max(b[3] for b in bs), H) + 0.2
        except Exception: pass
        cw, ch = max(self.cv.winfo_width(), 200), max(self.cv.winfo_height(), 200)
        self.zoom = min((cw - 30) / max(x1 - x0, 0.5), (ch - 30) / max(y1 - y0, 0.5))
        self.ox = (cw - (x1 - x0) * self.zoom) / 2 - x0 * self.zoom
        self.oy = (ch - (y1 - y0) * self.zoom) / 2 - (H - y1) * self.zoom
        self.deseneaza()

    def deseneaza(self):
        if getattr(self, "ed_win", None): self.inchide_editor(True); return     # întâi termină editarea textului
        cv = self.cv; cv.delete("all")
        if not self.doc: return
        p = self.doc.pagini[self.chat.ip]; W, H = p.dimensiune()
        x0, y0 = self.ecran(0, H); x1, y1 = self.ecran(W, 0)
        cv.create_rectangle(x0 + 3, y0 + 3, x1 + 3, y1 + 3, fill="#C9CED4", outline=""); cv.create_rectangle(x0, y0, x1, y1, fill="white", outline="#D0D4D9")
        self.cutii = []                                          # (forma de sus, cutie) pentru selectare
        err = 0
        for f in p.forme():
            try:
                self.forma(f); self.cutii.append((f, f.cutie()))
            except Exception:
                err += 1
        for f in self.selectie:
            try:
                b = f.cutie(); a = self.ecran(b[0], b[3]); c = self.ecran(b[2], b[1])
                cv.create_rectangle(a[0] - 3, a[1] - 3, c[0] + 3, c[1] + 3, outline="#0078D7", dash=(4, 2), width=2)
            except Exception: pass
        self.manere = []
        if len(self.selectie) == 1 and not self.selectie[0].e1d:
            try:
                b = self.selectie[0].cutie(); a = self.ecran(b[0], b[3]); c = self.ecran(b[2], b[1])
                xs = (a[0] - 3, (a[0] + c[0]) / 2, c[0] + 3); ys = (a[1] - 3, (a[1] + c[1]) / 2, c[1] + 3)
                for i, X in enumerate(xs):
                    for j, Y in enumerate(ys):
                        if i == 1 and j == 1: continue
                        cv.create_rectangle(X - 4, Y - 4, X + 4, Y + 4, fill="white", outline="#0078D7", width=1.5)
                        self.manere.append((X, Y, i, j))
            except Exception: pass
        n = len(self.selectie)
        self.status.config(text=f"Pagina {self.chat.ip + 1}/{len(self.doc.pagini)} „{p.nume}”" + (f" – selectate: {n}" if n else "") +
                           "   |  clic: selectează · trage: mută · trage pe gol: selectează zona · Ctrl+C/Ctrl+V · Delete · dublu-clic: text · "
                           "Ctrl+Z / Ctrl+Y · rotița: zoom · clic dreapta + trage: mută vederea" + (f"  ({err} forme neafișate)" if err else ""))

    def forma(self, f):
        lp = f.cell("LinePattern", "1") or "1"
        lc = "" if lp == "0" else culoare(f.cell("LineColor"), "#000000")
        fp = f.cell("FillPattern", "1") or "1"
        fc = "" if fp == "0" else culoare(f.cell("FillForegnd"), "#FFFFFF")
        lw = max(1, min(8, f.num("LineWeight", 0.01) * self.zoom))
        dash = None if lp in ("0", "1") else ((6, 3) if lp in ("2", "9", "10", "23") else (2, 2) if lp in ("3", "16") else (8, 3, 2, 3))
        rot = f.num("Rounding", 0) * self.zoom
        for pts, plin in f.contur():
            xy = [self.ecran(x, y) for x, y in pts]
            if len(xy) < 2: continue
            inchis = len(xy) > 2 and abs(xy[0][0] - xy[-1][0]) < 0.5 and abs(xy[0][1] - xy[-1][1]) < 0.5
            if inchis and rot > 1.5: xy = rotunjit(xy, rot)
            flat = [c for p in xy for c in p]
            if plin and inchis and fc:
                self.cv.create_polygon(*flat, fill=fc, outline="")
            if lc:
                self.cv.create_line(*flat, fill=lc, width=lw, dash=dash, capstyle="butt")
        for c in f.copii: self.forma(c)
        self.text(f)

    def text(self, f):
        t = f.text
        if not t: return
        px = f.sectiune("Character", "Size", "0.1111"); px = vsdx_doc.fnum(px, 0.1111) * self.zoom
        if px < 3.5: return                                       # prea mic la zoomul acesta
        T = f.transforma(); w, h = f.num("Width"), f.num("Height")
        if f.e1d:
            bx, by, ex, ey = f.num("BeginX"), f.num("BeginY"), f.num("EndX"), f.num("EndY")
            x, y = (bx + ex) / 2, (by + ey) / 2
            if f.parinte: x, y = f.parinte.transforma()(x, y)
            ang = 0.0
        else:
            tx = f.cell("TxtPinX"); ty = f.cell("TxtPinY")
            x, y = T(vsdx_doc.fnum(tx, w / 2) if tx is not None else w / 2, vsdx_doc.fnum(ty, h / 2) if ty is not None else h / 2)
            ang, g = 0.0, f                                         # unghiul textului: rotirile formei și ale grupurilor (oglindirea nu întoarce textul)
            while g is not None: ang += math.degrees(g.num("Angle", 0)); g = g.parinte
            ang += math.degrees(f.num("TxtAngle", 0))
        ang = (ang + 180) % 360 - 180
        col = culoare(f.sectiune("Character", "Color"), "#000000")
        stl = int(vsdx_doc.fnum(f.sectiune("Character", "Style", "0"), 0))
        font = ("Arial", -max(4, int(round(px))), ("bold " if stl & 1 else "") + ("italic" if stl & 2 else ""))
        X, Y = self.ecran(x, y)
        al = f.sectiune("Paragraph", "HorzAlign", "1") or "1"
        lat = max(w, f.num("TxtWidth", w)) * self.zoom
        kw = dict(text=t, font=font, fill=col, justify={"0": "left", "2": "right"}.get(al, "center"), angle=ang)
        if abs(ang) < 1 and lat > 20 and not f.e1d and "\n" not in t: kw["width"] = lat
        it = self.cv.create_text(X, Y, **kw)
        bk = f.cell("TextBkgnd", "0")
        if bk and bk not in ("0",) and abs(ang) < 1:
            b = self.cv.bbox(it)
            if b: self.cv.tag_lower(self.cv.create_rectangle(b[0] - 1, b[1], b[2] + 1, b[3], fill=culoare(bk, "#FFFFFF"), outline=""), it)

    # ---------- vederea ----------
    def roata(self, e): self.zoom_la(e, 1.15 if e.delta > 0 else 1 / 1.15)

    def zoom_la(self, e, k):
        self.ox = e.x - (e.x - self.ox) * k; self.oy = e.y - (e.y - self.oy) * k; self.zoom *= k; self.deseneaza()

    def pan_start(self, e): self.px, self.py = e.x, e.y; self.px0, self.py0 = e.x, e.y

    def pan(self, e):
        self.ox += e.x - self.px; self.oy += e.y - self.py; self.px, self.py = e.x, e.y; self.deseneaza()

    # ---------- editare cu mausul ----------
    def forma_la(self, X, Y):
        """forma de sus de sub maus (cea mai mică care conține punctul; liniile – după distanță)"""
        if not self.doc: return None
        x, y = self.pagina_xy(X, Y); tol = 5 / self.zoom; best, ba = None, 1e18
        for f, (x0, y0, x1, y1) in getattr(self, "cutii", []):
            if not (x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol): continue
            if f.e1d:
                bx, by, ex, ey = f.num("BeginX"), f.num("BeginY"), f.num("EndX"), f.num("EndY")
                d = dist_seg(x, y, bx, by, ex, ey)
                if d <= tol and d * d < ba: best, ba = f, d * d * 0.01
                continue
            a = max(x1 - x0, 0.01) * max(y1 - y0, 0.01)
            if a < ba: best, ba = f, a
        return best

    def clic(self, e):
        self.cv.focus_set()
        if not self.doc: return
        self.mouse0 = (e.x, e.y); self.mod = None
        for X, Y, i, j in getattr(self, "manere", []):
            if abs(e.x - X) <= 6 and abs(e.y - Y) <= 6:
                self.mod = "redim"; self.maner = (i, j); return
        f = self.forma_la(e.x, e.y); ids = [s.id for s in self.selectie]
        if f is not None:
            if e.state & 0x0001:                                   # Shift: adaugă / scoate din selecție
                self.selectie = [s for s in self.selectie if s.id != f.id] if f.id in ids else self.selectie + [f]
            elif f.id not in ids: self.selectie = [f]
            self.mod = "muta"
        else:
            if not e.state & 0x0001: self.selectie = []
            self.mod = "zona"
        self.deseneaza()

    def trage(self, e):
        if not self.doc or self.mod is None: return
        self.cv.delete("tras")
        if self.mod == "zona":
            self.cv.create_rectangle(self.mouse0[0], self.mouse0[1], e.x, e.y, outline="#0078D7", dash=(3, 2), tags="tras")
        elif self.mod == "redim" and self.selectie:
            r = self.cutie_noua(e)
            if r: self.cv.create_rectangle(*r, outline="#0078D7", dash=(4, 2), width=2, tags="tras")
        elif self.mod == "muta" and self.selectie:
            dx, dy = e.x - self.mouse0[0], e.y - self.mouse0[1]
            for f in self.selectie:
                b = f.cutie(); a = self.ecran(b[0], b[3]); c = self.ecran(b[2], b[1])
                self.cv.create_rectangle(a[0] + dx, a[1] + dy, c[0] + dx, c[1] + dy, outline="#0078D7", width=2, tags="tras")

    def elibereaza(self, e):
        if not self.doc or self.mod is None: return
        self.cv.delete("tras"); mod, self.mod = self.mod, None
        if mod == "redim":
            r = self.cutie_noua(e)
            if r and (abs(e.x - self.mouse0[0]) > 2 or abs(e.y - self.mouse0[1]) > 2): self.redimensioneaza(self.selectie[0], r)
            return
        if mod == "zona":
            if abs(e.x - self.mouse0[0]) < 3 and abs(e.y - self.mouse0[1]) < 3: return
            a = self.pagina_xy(min(e.x, self.mouse0[0]), max(e.y, self.mouse0[1])); b = self.pagina_xy(max(e.x, self.mouse0[0]), min(e.y, self.mouse0[1]))
            noi = [f for f, (x0, y0, x1, y1) in self.cutii if x0 >= a[0] and x1 <= b[0] and y0 >= a[1] and y1 <= b[1]]
            ids = {s.id for s in self.selectie}; self.selectie += [f for f in noi if f.id not in ids]; self.deseneaza()
        elif mod == "muta":
            dx, dy = (e.x - self.mouse0[0]) / self.zoom, -(e.y - self.mouse0[1]) / self.zoom
            if abs(dx) * self.zoom < 2 and abs(dy) * self.zoom < 2: return
            self.muta_selectia(dx, dy)

    def cutie_noua(self, e):
        """dreptunghiul nou (pe ecran) când tragi de mânerul (i, j): 0 = stânga/sus, 2 = dreapta/jos, 1 = neschimbat"""
        b = self.selectie[0].cutie(); a = self.ecran(b[0], b[3]); c = self.ecran(b[2], b[1])
        x0, y0, x1, y1 = a[0], a[1], c[0], c[1]; i, j = self.maner; dx, dy = e.x - self.mouse0[0], e.y - self.mouse0[1]
        if i == 0: x0 = min(x0 + dx, x1 - 4)
        if i == 2: x1 = max(x1 + dx, x0 + 4)
        if j == 0: y0 = min(y0 + dy, y1 - 4)
        if j == 2: y1 = max(y1 + dy, y0 + 4)
        return x0, y0, x1, y1

    def redimensioneaza(self, f, r):
        """schimbă lățimea / înălțimea formei (chenar, text, manșon…) la dreptunghiul r de pe ecran"""
        if abs(math.sin(f.num("Angle", 0))) > 0.01 and abs(math.cos(f.num("Angle", 0))) > 0.01:
            self.status.config(text="Forma e rotită oblic – n-o pot redimensiona aici (fă-o în Visio)."); return
        X0, Y1 = self.pagina_xy(r[0], r[1]); X1, Y0 = self.pagina_xy(r[2], r[3])
        b = f.cutie(); ow, oh = b[2] - b[0], b[3] - b[1]
        if ow <= 0 or oh <= 0: return
        sx, sy = (X1 - X0) / ow, (Y1 - Y0) / oh
        vert = abs(math.sin(f.num("Angle", 0))) > 0.5                         # rotită 90°: lățimea formei e pe verticală
        kx, ky = (sy, sx) if vert else (sx, sy)
        self.inainte_de_modificare(); self.reselecteaza(); f = self.selectie[0]; V = vsdx_doc.V
        W, H = f.num("Width") * kx, f.num("Height") * ky
        for n, k in (("Width", kx), ("Height", ky), ("LocPinX", kx), ("LocPinY", ky), ("TxtPinX", kx), ("TxtWidth", kx), ("TxtLocPinX", kx),
                     ("TxtPinY", ky), ("TxtHeight", ky), ("TxtLocPinY", ky)):
            v = f.cell(n)
            if v is None: continue
            c = f.el.find(V + "Cell[@N='%s']" % n)
            if c is None:
                if n.startswith("Txt"): continue
                c = desen._cell(f.el, n, 0.0)
            c.set("V", "%.10g" % (vsdx_doc.fnum(v) * k))
        # geometria cu valori absolute: scalată (rândurile din forma de bază se copiază în formă, cu formula moștenită)
        for g in f.el.findall(V + "Section[@N='Geometry']"):
            for row in g.findall(V + "Row"):
                if (row.get("T") or "").startswith("Rel"): continue
                for c in row.findall(V + "Cell"):
                    if c.get("N") in ("X", "A", "C"): c.set("V", "%.10g" % (vsdx_doc.fnum(c.get("V")) * kx))
                    if c.get("N") in ("Y", "B", "D"): c.set("V", "%.10g" % (vsdx_doc.fnum(c.get("V")) * ky))
        if f.master and f.master[1] is not None and f.el.find(V + "Section[@N='Geometry']") is None:
            for g in f.master[1].findall(V + "Section[@N='Geometry']"):
                ng = ET.SubElement(f.el, V + "Section", {"N": "Geometry", "IX": g.get("IX", "0")})
                for row in g.findall(V + "Row"):
                    if (row.get("T") or "").startswith("Rel"): continue
                    nr = ET.SubElement(ng, V + "Row", {"IX": row.get("IX", "0")})
                    for c in row.findall(V + "Cell"):
                        k = kx if c.get("N") in ("X", "A", "C") else ky if c.get("N") in ("Y", "B", "D") else 1
                        a = {"N": c.get("N"), "V": "%.10g" % (vsdx_doc.fnum(c.get("V")) * k)}
                        if c.get("F"): a["F"] = "Inh"
                        ET.SubElement(nr, V + "Cell", a)
        f = Forma_noua(self, f)
        nb = f.cutie()                                                          # mută ca să stea exact în dreptunghiul cerut
        desen._cell(f.el, "PinX", f.num("PinX") + X0 - nb[0]); desen._cell(f.el, "PinY", f.num("PinY") + Y0 - nb[1])
        self.reselecteaza(); self.deseneaza(); self.status.config(text=f"Mărime nouă: {X1 - X0:.2f} × {Y1 - Y0:.2f} inch")

    def inainte_de_modificare(self):
        self.chat.istoric.append(self.doc.instantaneu()); self.chat.istoric = self.chat.istoric[-50:]; self.chat.refacere = []; self.modificat = True

    def reselecteaza(self):
        ids = [s.id for s in self.selectie]; toate = {f.id: f for f in self.doc.pagini[self.chat.ip].forme()}
        self.selectie = [toate[i] for i in ids if i in toate]

    def muta_selectia(self, dx, dy):
        if not self.selectie: return
        self.inainte_de_modificare(); self.reselecteaza(); S = self.chat.schema
        for f in self.selectie: muta_forma(S, f, dx, dy)
        self.reselecteaza(); self.deseneaza()

    def sageti(self, e):
        if not self.selectie or self.focus_in_chat(): return
        pas = (1 / 2.54) if e.state & 0x0001 else (0.1 / 2.54)
        dx, dy = {"Left": (-pas, 0), "Right": (pas, 0), "Up": (0, pas), "Down": (0, -pas)}[e.keysym]
        self.muta_selectia(dx, dy); return "break"

    def focus_in_chat(self):
        try: f = self.root.focus_get()
        except Exception: f = None
        return f in (self.ent, self.txt) or (getattr(self, "ed_win", None) and f is getattr(self, "ed_txt", None))

    def copiaza(self, e=None):
        if (e is not None and self.focus_in_chat()) or not self.selectie: return
        self.clipboard = [copy.deepcopy(f.el) for f in self.selectie]
        b = [f.cutie() for f in self.selectie]; self.clip_centru = ((min(x[0] for x in b) + max(x[2] for x in b)) / 2, (min(x[1] for x in b) + max(x[3] for x in b)) / 2)
        self.status.config(text=f"Copiat: {len(self.clipboard)} forme. Du mausul unde vrei și apasă Ctrl+V.")
        return "break"

    def lipeste(self, e=None):
        if (e is not None and self.focus_in_chat()) or not getattr(self, "clipboard", None) or not self.doc: return
        self.inainte_de_modificare(); p = self.doc.pagini[self.chat.ip]; sh = p.shapes_el()
        X = self.cv.winfo_pointerx() - self.cv.winfo_rootx(); Y = self.cv.winfo_pointery() - self.cv.winfo_rooty()
        if 0 <= X <= self.cv.winfo_width() and 0 <= Y <= self.cv.winfo_height(): tx, ty = self.pagina_xy(X, Y)
        else: tx, ty = self.clip_centru[0] + 0.3, self.clip_centru[1] - 0.3
        dx, dy = tx - self.clip_centru[0], ty - self.clip_centru[1]; nid = p.id_nou(); noi = []
        for el in self.clipboard:
            el = copy.deepcopy(el)
            for s in el.iter(vsdx_doc.V + "Shape"): s.set("ID", str(nid)); nid += 1
            for s in el.iter(vsdx_doc.V + "Shape"):
                for a in ("UniqueID",):
                    if a in s.attrib: del s.attrib[a]
            sh.append(el); noi.append(int(el.get("ID")))
        toate = {f.id: f for f in p.forme()}; S = self.chat.schema
        for i in noi: muta_forma(S, toate[i], dx, dy, lipit=False)
        toate = {f.id: f for f in p.forme()}; self.selectie = [toate[i] for i in noi]
        self.deseneaza(); self.status.config(text=f"Lipit: {len(noi)} forme.")
        return "break"

    def sterge_selectia(self, e=None):
        if (e is not None and self.focus_in_chat()) or not self.selectie or getattr(self, "ed_win", None): return
        self.inainte_de_modificare(); self.reselecteaza(); S = self.chat.schema
        for f in self.selectie: S.sterge(f)
        n = len(self.selectie); self.selectie = []; self.deseneaza(); self.status.config(text=f"Șters: {n} forme.")
        return "break"

    def anuleaza_chat(self):
        if not self.doc: return
        r, sch = self.chat.inapoi(); self.status.config(text=r)
        if sch: self.selectie = []; self.termeni = []; self.actualizeaza_pagini(); self.deseneaza(); self.modificat = True

    def inainte(self):
        if not self.doc: return
        r, sch = self.chat.inainte(); self.status.config(text=r)
        if sch: self.selectie = []; self.termeni = []; self.actualizeaza_pagini(); self.deseneaza(); self.modificat = True

    def anuleaza(self, e=None):
        if self.focus_in_chat() or not self.doc: return
        self.anuleaza_chat(); return "break"

    def inainte_tasta(self, e=None):
        if self.focus_in_chat() or not self.doc: return
        self.inainte(); return "break"

    def forma_text_la(self, X, Y):
        """forma cu text de sub maus – și în interiorul grupurilor; cea mai mică"""
        x, y = self.pagina_xy(X, Y); tol = 4 / self.zoom; best, ba = None, 1e18
        for f in self.doc.pagini[self.chat.ip].toate():
            if not f.text: continue
            try: x0, y0, x1, y1 = f.cutie()
            except Exception: continue
            if x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol:
                a = max(x1 - x0, 0.01) * max(y1 - y0, 0.01)
                if a < ba: best, ba = f, a
        return best

    def cu_text(self, f):
        """forma însăși, sau primul copil cu text (la grupuri)"""
        if f.text or not f.copii: return f
        for c in f.copii:
            g = self.cu_text(c)
            if g.text: return g
        return f

    def editeaza_text(self, e=None):
        if not self.doc: return
        if e is not None and hasattr(e, "x") and e.widget is self.cv:
            f = self.forma_text_la(e.x, e.y) or self.forma_la(e.x, e.y)
        else:
            if self.focus_in_chat() or not self.selectie: return
            f = self.cu_text(self.selectie[0])
        if f is None: return
        self.mod = None; self.cv.delete("tras")
        self.editor_pe_schema(f)
        return "break"

    def editor_pe_schema(self, f):
        """editarea textului direct pe schemă: Enter = gata, Shift+Enter = rând nou, Esc = renunță"""
        if getattr(self, "ed_win", None): self.inchide_editor(False)
        try: x0, y0, x1, y1 = f.cutie()
        except Exception: return
        a = self.ecran(x0, y1); b = self.ecran(x1, y0)
        w = max(160, b[0] - a[0] + 20); vechi = f.text
        lin = max(1, len(vechi.split("\n")))
        t = tk.Text(self.cv, width=1, height=min(lin, 8), font=("Arial", 11), wrap="word", relief="solid", bd=1,
                    highlightthickness=2, highlightcolor=ACCENT, padx=4, pady=2, undo=True)
        t.insert("1.0", vechi); t.tag_add("sel", "1.0", "end-1c")
        self.ed_win = self.cv.create_window((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, window=t, width=min(w, 600),
                                           height=min(lin, 8) * 22 + 12)
        self.ed_txt, self.ed_forma = t, f
        t.focus_set()
        t.bind("<Return>", lambda e: (self.inchide_editor(True), "break")[1])
        t.bind("<KP_Enter>", lambda e: (self.inchide_editor(True), "break")[1])
        t.bind("<Shift-Return>", lambda e: (t.insert("insert", "\n"), t.configure(height=int(t.cget("height")) + 1),
                                            self.cv.itemconfigure(self.ed_win, height=(int(t.cget("height"))) * 22 + 12), "break")[3])
        t.bind("<Escape>", lambda e: (self.inchide_editor(False), "break")[1])
        t.bind("<FocusOut>", lambda e: self.root.after(50, lambda: self.inchide_editor(True) if getattr(self, "ed_win", None) else None))
        self.status.config(text="Editezi textul: Enter = gata · Shift+Enter = rând nou · Esc = renunță")

    def inchide_editor(self, pastreaza):
        if not getattr(self, "ed_win", None): return
        nou = self.ed_txt.get("1.0", "end-1c"); f = self.ed_forma
        self.cv.delete(self.ed_win); self.ed_txt.destroy(); self.ed_win = None; self.cv.focus_set()
        if pastreaza and nou != f.text:
            self.inainte_de_modificare(); desen._text(f.el, nou); self.termeni = []
            self.status.config(text="Text schimbat.")
        self.reselecteaza(); self.deseneaza()

    def meniu(self, e):
        """clic dreapta (fără tragere): meniul cu acțiuni"""
        if not self.doc or abs(e.x - self.px0) > 3 or abs(e.y - self.py0) > 3: return
        f = self.forma_la(e.x, e.y)
        if f is not None and f.id not in [s.id for s in self.selectie]: self.selectie = [f]; self.deseneaza()
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Editează textul        F2", command=lambda: self.editor_pe_schema(self.forma_text_la(e.x, e.y) or self.cu_text(f)) if f else None,
                      state="normal" if f else "disabled")
        m.add_separator()
        m.add_command(label="Copiază                Ctrl+C", command=self.copiaza, state="normal" if self.selectie else "disabled")
        m.add_command(label="Lipește aici           Ctrl+V", command=self.lipeste, state="normal" if self.clipboard else "disabled")
        m.add_command(label="Șterge                 Delete", command=self.sterge_selectia, state="normal" if self.selectie else "disabled")
        m.add_separator()
        m.add_command(label="Înapoi                 Ctrl+Z", command=self.anuleaza_chat)
        m.add_command(label="Înainte                Ctrl+Y", command=self.inainte)
        m.add_command(label="Potrivește vederea", command=self.potriveste)
        m.tk_popup(e.x_root, e.y_root)

    def selecteaza_tot(self, e=None):
        if self.focus_in_chat() or not self.doc: return
        self.selectie = self.doc.pagini[self.chat.ip].forme(); self.deseneaza(); return "break"


def Forma_noua(app, f):
    toate = {g.id: g for g in app.doc.pagini[app.chat.ip].forme()}
    return toate.get(f.id, f)


def dist_seg(x, y, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L))
    return math.hypot(x - ax - t * dx, y - ay - t * dy)


def rotunjit(pts, r):
    """colțuri rotunjite (celula Rounding din Visio) pentru un contur închis, în pixeli"""
    p = pts[:-1]; out = []; n = len(p)
    for i in range(n):
        a, b, c = p[i - 1], p[i], p[(i + 1) % n]
        l1 = math.hypot(b[0] - a[0], b[1] - a[1]); l2 = math.hypot(c[0] - b[0], c[1] - b[1])
        rr = min(r, l1 / 2, l2 / 2)
        if rr < 1: out.append(b); continue
        p1 = (b[0] + (a[0] - b[0]) * rr / l1, b[1] + (a[1] - b[1]) * rr / l1); p2 = (b[0] + (c[0] - b[0]) * rr / l2, b[1] + (c[1] - b[1]) * rr / l2)
        for k in range(7):
            t = k / 6; out.append(((1 - t) ** 2 * p1[0] + 2 * (1 - t) * t * b[0] + t * t * p2[0], (1 - t) ** 2 * p1[1] + 2 * (1 - t) * t * b[1] + t * t * p2[1]))
    return out + [out[0]]


def muta_forma(S, f, dx, dy, lipit=True):
    """mută o formă: 2D – Pin (și cablurile lipite de ea); 1D – capetele (dezlipite de alte forme)"""
    V = vsdx_doc.V
    if f.e1d:
        for c in ("BeginX", "EndX", "PinX"):
            el = f.el.find(V + "Cell[@N='%s']" % c)
            if el is not None:
                el.set("V", "%.10g" % (vsdx_doc.fnum(el.get("V")) + dx))
                if c != "PinX" and "F" in el.attrib and "Sheet." in el.get("F"): del el.attrib["F"]
        for c in ("BeginY", "EndY", "PinY"):
            el = f.el.find(V + "Cell[@N='%s']" % c)
            if el is not None:
                el.set("V", "%.10g" % (vsdx_doc.fnum(el.get("V")) + dy))
                if c != "PinY" and "F" in el.attrib and "Sheet." in el.get("F"): del el.attrib["F"]
        con = S.p.connects()
        for c in list(con):
            if c.get("FromSheet") == str(f.id): con.remove(c)
        return
    if lipit: S.muta(f, dx, dy)
    else:
        desen._cell(f.el, "PinX", f.num("PinX") + dx); desen._cell(f.el, "PinY", f.num("PinY") + dy)


def editor_text(root, vechi):
    """fereastră mică pentru textul unei forme (mai multe rânduri)"""
    w = tk.Toplevel(root); w.title("Text"); w.transient(root); w.grab_set(); rez = {"t": None}
    t = tk.Text(w, width=50, height=6, font=("Arial", 11)); t.pack(padx=8, pady=8, fill="both", expand=True); t.insert("1.0", vechi); t.focus_set()
    b = ttk.Frame(w); b.pack(pady=(0, 8))
    def ok(e=None): rez["t"] = t.get("1.0", "end").rstrip("\n"); w.destroy(); return "break"
    ttk.Button(b, text="OK", command=ok).pack(side="left", padx=4); ttk.Button(b, text="Renunță", command=w.destroy).pack(side="left")
    t.bind("<Control-Return>", ok); root.wait_window(w)
    return rez["t"]


def main():
    try:
        from tkinterdnd2 import TkinterDnD                                     # fereastră care primește fișiere trase cu mausul
        root = TkinterDnD.Tk()
    except Exception:
        root = tk.Tk()
    try: root.tk.call("tk", "scaling", 1.25)
    except Exception: pass
    app = App(root)
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):                       # dublu-clic pe un .vsdx / tras peste exe
        root.after(200, lambda: app.deschide_cale(sys.argv[1]))
    root.mainloop()


if __name__ == "__main__":
    main()
