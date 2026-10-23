"""Panglica, la fel ca în Visio 2016 (culori și dimensiuni măsurate pe capturile din Visio):
bara filelor 24 px albastru #3955A3, corpul 92 px gri #F1F1F1, grupuri cu lățimile din Visio, titlul grupului jos.
Butoanele care au corespondent în program lucrează; celelalte apar estompate, ca în Visio când nu se pot folosi."""
import tkinter as tk
from tkinter import ttk

ALBASTRU = "#3955A3"; FUNDAL = "#F1F1F1"; SEP = "#D5D5D5"; TEXT = "#262626"; ESTOMPAT = "#A6A6A6"; HOVER = "#DADADA"; APASAT = "#C8C8C8"
F_FILA = ("Segoe UI", -12); F_BTN = ("Segoe UI", -12); F_GRUP = ("Segoe UI", -11); F_ICON = ("Segoe UI Symbol", -26); F_ICON_MIC = ("Segoe UI Symbol", -14)
H_FILE = 24; H_CORP = 92

FILE = ["File", "Home", "Insert", "Design", "Data", "Process", "Review", "View"]


class Panglica:
    def __init__(self, app, root):
        self.app = app; self.root = root; self.pagini = {}; self.file = {}
        # ---- bara de titlu cu bara de acces rapid (salvează, înapoi, înainte, tipărește) și numele fișierului
        sus = tk.Frame(root, bg=ALBASTRU, height=30); sus.pack(fill="x"); sus.pack_propagate(False)
        for txt, cmd, sfat in (("💾", app.salveaza, "Save"), ("↶", app.anuleaza_chat, "Undo"), ("↷", app.inainte, "Redo"), ("🖨", app.dialog_tiparire, "Print")):
            b = tk.Label(sus, text=txt, bg=ALBASTRU, fg="white", font=("Segoe UI Symbol", -15), padx=7, cursor="hand2"); b.pack(side="left")
            b.bind("<Button-1>", lambda e, c=cmd: c()); self._hover(b, ALBASTRU, "#4D69B3")
        app.lbl_fisier = tk.Label(sus, text="Fibra Visio", bg=ALBASTRU, fg="white", font=("Segoe UI", -12)); app.lbl_fisier.place(relx=0.5, rely=0.5, anchor="center")
        # ---- filele
        bf = tk.Frame(root, bg=ALBASTRU, height=H_FILE); bf.pack(fill="x"); bf.pack_propagate(False)
        for n in FILE:
            l = tk.Label(bf, text=n, bg=ALBASTRU, fg="white", font=F_FILA, padx=16, cursor="hand2"); l.pack(side="left", fill="y")
            l.bind("<Button-1>", lambda e, n=n: self.arata(n)); self.file[n] = l
            l.bind("<Enter>", lambda e, n=n: self.file[n].config(bg="#4D69B3") if n != self.activ else None)
            l.bind("<Leave>", lambda e, n=n: self.file[n].config(bg=ALBASTRU) if n != self.activ else None)
        tk.Label(bf, text="💡", bg=ALBASTRU, fg="#F2E28B", font=("Segoe UI Symbol", -13)).pack(side="left", padx=(16, 2))
        self.spune = tk.Entry(bf, bg=ALBASTRU, fg="#DCE3F3", insertbackground="white", relief="flat", font=F_FILA, width=34, highlightthickness=0)
        self.spune.insert(0, "Tell me what you want to do..."); self.spune.pack(side="left", fill="y")
        self.spune.bind("<FocusIn>", lambda e: (self.spune.delete(0, "end"), self.spune.config(fg="white")) if self.spune.get().startswith("Tell me") else None)
        self.spune.bind("<FocusOut>", lambda e: (self.spune.insert(0, "Tell me what you want to do..."), self.spune.config(fg="#DCE3F3")) if not self.spune.get() else None)
        self.spune.bind("<Return>", self._spune)
        # ---- corpul
        self.corp = tk.Frame(root, bg=FUNDAL, height=H_CORP); self.corp.pack(fill="x"); self.corp.pack_propagate(False)
        tk.Frame(root, bg=SEP, height=1).pack(fill="x")
        self.activ = None
        for n in FILE[1:]:
            f = tk.Frame(self.corp, bg=FUNDAL); self.pagini[n] = f; self.x = 0
            getattr(self, "fila_" + n.lower())(f)
        self.arata("Home")

    # ---------------------------------------------------------------- utilitare
    def _hover(self, w, bg, bg2):
        w.bind("<Enter>", lambda e: w.config(bg=bg2), add="+"); w.bind("<Leave>", lambda e: w.config(bg=bg), add="+")

    def _spune(self, e=None):
        t = self.spune.get().strip()
        if t and not t.startswith("Tell me"): self.app.trimite_text(t)
        self.spune.delete(0, "end"); self.app.cv.focus_set()

    def arata(self, n):
        if n == "File": return self.meniu_file()
        for k, l in self.file.items():
            act = k == n
            l.config(bg=FUNDAL if act else ALBASTRU, fg=ALBASTRU if act else "white")
        for k, f in self.pagini.items():
            if k == n: f.place(x=0, y=0, relwidth=1, height=H_CORP)
            else: f.place_forget()
        self.activ = n

    def grup(self, fila, titlu, w, lansator=False):
        g = tk.Frame(fila, bg=FUNDAL, width=w, height=H_CORP); g.place(x=self.x, y=0, width=w, height=H_CORP); self.x += w
        tk.Label(g, text=titlu, bg=FUNDAL, fg="#444444", font=F_GRUP).place(relx=0.5, y=74, anchor="n")
        tk.Frame(g, bg=SEP, width=1).place(x=w - 1, y=4, width=1, height=84)
        if lansator: tk.Label(g, text="⬊", bg=FUNDAL, fg="#777777", font=("Segoe UI Symbol", -9)).place(x=w - 12, y=76)
        return g

    def mare(self, g, x, icon, text, cmd=None, w=None, culoare="#2F5597"):
        """buton mare: iconița sus, textul dedesubt (ca „Paste”, „Align”, „New Page”)"""
        on = cmd is not None
        try:
            import tkinter.font as tkf
            lat = max(tkf.Font(family=F_BTN[0], size=F_BTN[1]).measure(r) for r in text.split("\n")) + 8
        except Exception: lat = 7 * max(len(r) for r in text.split("\n")) + 10
        w = max(w or 0, 40, lat)
        b = tk.Frame(g, bg=FUNDAL, width=w, height=70, cursor="hand2" if on else ""); b.place(x=x, y=2, width=w, height=70)
        i = tk.Label(b, text=icon, bg=FUNDAL, fg=culoare if on else ESTOMPAT, font=F_ICON); i.place(relx=0.5, y=0, anchor="n")
        t = tk.Label(b, text=text, bg=FUNDAL, fg=TEXT if on else ESTOMPAT, font=F_BTN, justify="center"); t.place(relx=0.5, y=36, anchor="n")
        if on:
            for z in (b, i, t):
                z.bind("<Button-1>", lambda e: cmd())
                z.bind("<Enter>", lambda e: [y.config(bg=HOVER) for y in (b, i, t)]); z.bind("<Leave>", lambda e: [y.config(bg=FUNDAL) for y in (b, i, t)])
        return b

    def mic(self, g, x, y, icon, text="", cmd=None, w=None, culoare="#2F5597"):
        """buton mic pe un rând (ca „Cut”, „Copy”, „Connector”)"""
        on = cmd is not None
        l = tk.Label(g, text=(icon + " " + text).strip() if text else icon, bg=FUNDAL, fg=(TEXT if text else culoare) if on else ESTOMPAT,
                     font=F_BTN if text else F_ICON_MIC, anchor="w", padx=3, cursor="hand2" if on else "")
        l.place(x=x, y=y, height=22, **({"width": w} if w else {}))
        if on:
            l.bind("<Button-1>", lambda e: cmd()); self._hover(l, FUNDAL, HOVER)
        return l

    def meniu(self, w, intrari):
        """meniu sub buton: [(text, funcție) sau None pentru linie]"""
        m = tk.Menu(self.root, tearoff=0, font=F_BTN)
        for x in intrari:
            if x is None: m.add_separator()
            else: m.add_command(label=x[0], command=x[1])
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() + w.winfo_height())

    # ---------------------------------------------------------------- File
    def meniu_file(self):
        a = self.app
        self.meniu(self.file["File"], [("New", a.nou), ("Open…", a.deschide), None, ("Save", a.salveaza), ("Save As…", a.salveaza_ca), None,
                                       ("Print…", a.dialog_tiparire), None, ("Close", a.inchide)])

    # ---------------------------------------------------------------- Home
    def fila_home(self, f):
        a = self.app
        g = self.grup(f, "Clipboard", 151)
        self.mare(g, 2, "📋", "Paste\n▾", a.lipeste, w=40, culoare="#B07B2B")
        self.mic(g, 44, 4, "✂", "Cut", self.taie); self.mic(g, 44, 26, "⧉", "Copy", a.copiaza); self.mic(g, 44, 48, "🖌", "Format Painter", self.pensula)
        g = self.grup(f, "Font", 212, True)
        try:
            import tkinter.font as tkf
            fonturi = sorted({x for x in tkf.families() if not x.startswith("@")})
        except Exception: fonturi = ["Arial", "Calibri"]
        a.cb_font = ttk.Combobox(g, values=fonturi, font=F_BTN); a.cb_font.set("Calibri"); a.cb_font.place(x=6, y=6, width=100, height=22)
        a.cb_font.bind("<<ComboboxSelected>>", lambda e: a.aplica_text(font=a.cb_font.get()))
        a.cb_font.bind("<Return>", lambda e: (a.aplica_text(font=a.cb_font.get()), "break")[1])
        a.cb_size = ttk.Combobox(g, values=[6, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36, 48, 72], font=F_BTN); a.cb_size.set("12pt.")
        a.cb_size.place(x=108, y=6, width=54, height=22)
        a.cb_size.bind("<<ComboboxSelected>>", lambda e: a.aplica_text(size=a.cb_size.get()))
        a.cb_size.bind("<Return>", lambda e: (a.aplica_text(size=a.cb_size.get().replace("pt.", "")), "break")[1])
        self.mic(g, 164, 4, "A⁺", cmd=lambda: a.aplica_text(delta=+1), culoare=TEXT); self.mic(g, 186, 4, "A⁻", cmd=lambda: a.aplica_text(delta=-1), culoare=TEXT)
        for i, (t, fn, cmd) in enumerate((("B", ("Segoe UI", -12, "bold"), lambda: a.aplica_text(stil=1)), ("I", ("Segoe UI", -12, "italic"), lambda: a.aplica_text(stil=2)),
                                          ("U", ("Segoe UI", -12, "underline"), lambda: a.aplica_text(stil=4)), ("abc", ("Segoe UI", -11, "overstrike"), None),
                                          ("Aa ▾", F_BTN, None))):
            l = tk.Label(g, text=t, bg=FUNDAL, fg=TEXT if cmd else ESTOMPAT, font=fn, cursor="hand2" if cmd else ""); l.place(x=6 + i * 23 + (8 if i == 4 else 0), y=36, height=22)
            if cmd: l.bind("<Button-1>", lambda e, c=cmd: c()); self._hover(l, FUNDAL, HOVER)
        cul = tk.Label(g, text="A", bg=FUNDAL, fg=TEXT, font=("Segoe UI", -13, "bold"), cursor="hand2"); cul.place(x=136, y=34, height=20)
        tk.Frame(g, bg="#FF0000", height=3).place(x=134, y=54, width=16, height=3)
        cul.bind("<Button-1>", lambda e: self.meniu(cul, [(n, lambda c=c: a.aplica_text(culoare=c)) for n, c in CULORI] + [None, ("More Colors…", a.alege_culoare)]))
        tk.Label(g, text="▾", bg=FUNDAL, fg=TEXT, font=F_BTN).place(x=152, y=36)
        a.lbl_text = tk.Label(g, text="", bg=FUNDAL)                     # (păstrat pentru starea textului selectat; nu se vede)
        g = self.grup(f, "Paragraph", 150, True)
        for i, (t, al) in enumerate((("≡", None), ("≡", None), ("≡", None))): self.mic(g, 6 + i * 24, 4, "☰", cmd=None)
        self.mic(g, 86, 4, "☷", cmd=None); self.mic(g, 116, 4, "A⤵", cmd=None)
        for i, (t, al) in enumerate((("⯇☰", "0"), ("☰", "1"), ("☰⯈", "2"), ("▤", "1"))):
            self.mic(g, 6 + i * 24, 36, "☰", cmd=lambda al=al: a.aplica_text(aliniere=al), culoare=TEXT)
        self.mic(g, 102, 36, "⇤", cmd=None); self.mic(g, 124, 36, "⇥", cmd=None)
        g = self.grup(f, "Tools", 137)
        self.unelte = {}
        for i, (k, ic, t) in enumerate((("pointer", "↖", "Pointer Tool"), ("connector", "⤴", "Connector"), ("text", "A", "Text"))):
            self.unelte[k] = self.mic(g, 4, 4 + i * 22, ic, t, lambda k=k: self.unealta(k), w=92)
        r = self.mic(g, 98, 4, "▭ ▾", cmd=lambda: self.meniu(r, [("Rectangle", lambda: self.unealta("rect")), ("Ellipse", lambda: self.unealta("ellipse")),
                                                                ("Line", lambda: self.unealta("connector"))]), culoare=TEXT)
        self.mic(g, 102, 26, "✕", cmd=lambda: self.unealta("pointer"), culoare="#2F5597"); self.mic(g, 102, 48, "⌖", cmd=None)
        self.unealta("pointer")
        g = self.grup(f, "Shape Styles", 494, True)
        gal = tk.Frame(g, bg="white", highlightthickness=1, highlightbackground="#C6C6C6"); gal.place(x=6, y=4, width=410, height=62)
        for i, (fill, line) in enumerate(STILURI):
            c = tk.Canvas(gal, width=46, height=40, bg="white", highlightthickness=0, cursor="hand2"); c.place(x=8 + i * 57, y=10)
            c.create_rectangle(4, 4, 42, 36, fill=fill, outline=line, width=1.5); c.create_text(23, 20, text="Abc", font=("Segoe UI", -9), fill="#333")
            c.bind("<Button-1>", lambda e, f_=fill, l_=line: self.stil_forma(f_, l_))
        tk.Frame(gal, bg="#E8E8E8").place(x=396, y=0, width=13, height=60)
        fl = self.mic(g, 420, 4, "▰", "Fill ▾", lambda: self.meniu(fl, [(n, lambda c=c: self.umple(c)) for n, c in CULORI] + [None, ("No Fill", lambda: self.umple(None))]), culoare="#F2C700")
        ln = self.mic(g, 420, 26, "▬", "Line ▾", lambda: self.meniu(ln, [(n, lambda c=c: self.linie(culoare=c)) for n, c in CULORI] + [None] +
                                                                    [(f"Weight {p} pt", lambda p=p: self.linie(gros=p)) for p in (0.25, 0.5, 0.75, 1, 1.5, 2.25, 3)] + [None,
                                                                    ("Solid", lambda: self.linie(model="1")), ("Dash", lambda: self.linie(model="2")), ("Dot", lambda: self.linie(model="3")),
                                                                    ("No Line", lambda: self.linie(model="0"))]), culoare="#2F5597")
        self.mic(g, 420, 48, "◫", "Effects ▾")
        g = self.grup(f, "Arrange", 214, True)
        al = self.mare(g, 6, "⊫", "Align\n▾", lambda: self.meniu(al, [("Align Left", lambda: self.aliniaza("l")), ("Align Center", lambda: self.aliniaza("c")),
                                                                    ("Align Right", lambda: self.aliniaza("r")), None, ("Align Top", lambda: self.aliniaza("t")),
                                                                    ("Align Middle", lambda: self.aliniaza("m")), ("Align Bottom", lambda: self.aliniaza("b"))]), w=42)
        po = self.mare(g, 50, "⊞", "Position\n▾", lambda: self.meniu(po, [("Distribute Horizontally", lambda: self.distribuie("h")),
                                                                         ("Distribute Vertically", lambda: self.distribuie("v"))]), w=52)
        self.mic(g, 104, 4, "⧉", "Bring to Front ▾", lambda: self.ordine(True)); self.mic(g, 104, 26, "⧉", "Send to Back ▾", lambda: self.ordine(False))
        self.mic(g, 104, 48, "▣", "Group ▾")
        g = self.grup(f, "Editing", 125)
        self.mare(g, 4, "⬠", "Change\nShape ▾", w=50)
        fi = self.mic(g, 54, 4, "🔍", "Find ▾", self.cauta); self.mic(g, 54, 26, "◧", "Layers ▾")
        se = self.mic(g, 54, 48, "↖", "Select ▾", lambda: self.meniu(se, [("Select All", lambda: a.selecteaza_tot()), ("Deselect", self.deselecteaza), None,
                                                                         ("Select splices", lambda: a.trimite_text("selecteaza sudurile")),
                                                                         ("Select red fibers", lambda: a.trimite_text("selecteaza fibrele rosii")),
                                                                         ("Select texts", lambda: a.trimite_text("selecteaza textele"))]))

    # ---------------------------------------------------------------- Insert
    def fila_insert(self, f):
        a = self.app
        g = self.grup(f, "Pages", 46); self.mare(g, 2, "🗋", "New\nPage ▾", a.pagina_noua, w=42, culoare="#555555")
        g = self.grup(f, "Illustrations", 196)
        self.mare(g, 4, "🖼", "Pictures"); self.mare(g, 52, "🖼", "Online\nPictures"); self.mare(g, 102, "📊", "Chart"); self.mare(g, 144, "📐", "CAD\nDrawing")
        g = self.grup(f, "Diagram Parts", 168)
        self.mare(g, 4, "⬚", "Container\n▾", lambda: a.container(), culoare="#555555"); self.mare(g, 62, "🗨", "Callout\n▾", lambda: a.container(callout=True), culoare="#555555")
        self.mare(g, 112, "⤴", "Connector", lambda: self.unealta("connector"), culoare="#555555")
        g = self.grup(f, "Links", 64); self.mare(g, 4, "🔗", "Hyperlink", w=56)
        g = self.grup(f, "Text", 300)
        self.mare(g, 4, "🅰", "Text\nBox ▾", a.caseta_text, culoare="#2F5597"); self.mare(g, 50, "💬", "ScreenTip"); self.mare(g, 110, "🗔", "Object")
        self.mare(g, 152, "▭", "Field")
        sy = self.mare(g, 192, "Ω", "Symbol\n▾", lambda: self.meniu(sy, [(c, lambda c=c: a.simbol(c)) for c in "Ø ° ± µ Ω ∑ ≈ ≤ ≥ × ÷ → ↔ ✓".split()]), culoare="#555555")
        a.btn_tabel = self.mare(g, 246, "▦", "Table\n▾", a.meniu_tabel, culoare="#555555")

    # ---------------------------------------------------------------- Design
    def fila_design(self, f):
        a = self.app
        g = self.grup(f, "Page Setup", 156, True)
        o = self.mare(g, 2, "🗎", "Orientation\n▾", lambda: self.meniu(o, [("Landscape", lambda: a.schimba_format(None, True)), ("Portrait", lambda: a.schimba_format(None, False))]), w=62, culoare="#555555")
        s = self.mare(g, 66, "🗍", "Size\n▾", lambda: self.meniu(s, [(f"{k}  ({w} × {h} mm)", lambda k=k: a.schimba_format(k, None)) for k, (w, h) in
                                                                     __import__("tiparire").FORMATE.items()]), w=40, culoare="#555555")
        self.mare(g, 108, "⤢", "Auto\nSize", w=44)
        g = self.grup(f, "Themes", 894)
        gal = tk.Frame(g, bg="white", highlightthickness=1, highlightbackground="#C6C6C6"); gal.place(x=6, y=2, width=866, height=68)
        for i, (c1, c2) in enumerate(TEME):
            c = tk.Canvas(gal, width=64, height=56, bg="white", highlightthickness=0); c.place(x=4 + i * 70, y=5)
            c.create_rectangle(4, 6, 46, 42, fill=c1, outline=c1); c.create_rectangle(30, 14, 58, 36, fill=c2, outline="white")
            c.create_text(18, 32, text="Aa", font=("Segoe UI", -12), fill="white" if c1 not in ("#FFFFFF", "#F7F7F7") else "#222")
        g = self.grup(f, "Variants", 246)
        tk.Frame(g, bg="white", highlightthickness=1, highlightbackground="#C6C6C6").place(x=6, y=2, width=232, height=68)
        g = self.grup(f, "Backgrounds", 141, True); self.mare(g, 4, "🖽", "Backgrounds\n▾", w=72); self.mare(g, 78, "🗒", "Borders &\nTitles ▾", w=60)
        g = self.grup(f, "Layout", 134, True); self.mare(g, 4, "⧈", "Re-Layout\nPage ▾", w=62); self.mare(g, 70, "⤳", "Connectors\n▾", w=62)

    # ---------------------------------------------------------------- Data / Process / Review: funcțiile pentru fibră
    def fila_data(self, f):
        a = self.app
        g = self.grup(f, "Fiber", 250)
        tk.Label(g, text="New cable", bg=FUNDAL, fg=TEXT, font=F_BTN).place(x=8, y=6)
        a.cb_stil = ttk.Combobox(g, state="readonly", values=["roșu", "linie întreruptă", "roșu întrerupt", "ca cele existente"], font=F_BTN)
        a.cb_stil.current(0); a.cb_stil.place(x=80, y=4, width=160, height=22); a.cb_stil.bind("<<ComboboxSelected>>", a.stil_cablu)
        tk.Label(g, text="Page", bg=FUNDAL, fg=TEXT, font=F_BTN).place(x=8, y=36)
        a.cb_pag = ttk.Combobox(g, state="readonly", font=F_BTN); a.cb_pag.place(x=80, y=34, width=160, height=22); a.cb_pag.bind("<<ComboboxSelected>>", a.alege_pagina)
        g = self.grup(f, "Sheet", 190)
        import tiparire
        tk.Label(g, text="Size", bg=FUNDAL, fg=TEXT, font=F_BTN).place(x=8, y=6)
        a.cb_format = ttk.Combobox(g, state="readonly", values=list(tiparire.FORMATE), font=F_BTN); a.cb_format.set(tiparire.IMPLICIT)
        a.cb_format.place(x=80, y=4, width=100, height=22); a.cb_format.bind("<<ComboboxSelected>>", lambda e: a.schimba_format())
        tk.Label(g, text="Orientation", bg=FUNDAL, fg=TEXT, font=F_BTN).place(x=8, y=36)
        a.cb_orient = ttk.Combobox(g, state="readonly", values=["culcat", "în picioare"], font=F_BTN); a.cb_orient.set("culcat")
        a.cb_orient.place(x=80, y=34, width=100, height=22); a.cb_orient.bind("<<ComboboxSelected>>", lambda e: a.schimba_format())
        g = self.grup(f, "Reports", 150)
        self.mare(g, 4, "🔢", "Free\nPorts", lambda: a.trimite_text("porturi libere"), culoare="#2F5597")
        self.mare(g, 52, "⦿", "Splices", lambda: a.trimite_text("cate suduri sunt"), culoare="#C00000")
        self.mare(g, 100, "☰", "List", lambda: a.trimite_text("lista"), culoare="#555555")

    def fila_process(self, f):
        a = self.app
        g = self.grup(f, "Assistant", 300)
        for i, (ic, t, cmd) in enumerate((("🏢", "New\nBuilding", "adauga cladire noua"), ("▥", "New\nODF", "adauga odf nou"), ("⬭", "New\nSplice Box", "adauga manson nou"),
                                          ("⤳", "Draw\nFiber", "trage o fibra"), ("❓", "Guide\nMe", "ghideaza-ma"))):
            self.mare(g, 4 + i * 58, ic, t, lambda c=cmd: a.trimite_text(c), w=56)

    def fila_review(self, f):
        a = self.app
        g = self.grup(f, "Proofing", 110); self.mare(g, 4, "abc✓", "Spelling", w=50); self.mare(g, 56, "📖", "Thesaurus", w=50)
        g = self.grup(f, "Memory", 160)
        self.mare(g, 4, "🧠", "What I\nLearned", lambda: a.trimite_text("ce ai invatat"), w=72, culoare="#7030A0")
        self.mare(g, 80, "🕘", "History", lambda: a.trimite_text("analizeaza discutia precedenta"), w=72, culoare="#555555")

    # ---------------------------------------------------------------- View
    def fila_view(self, f):
        a = self.app
        g = self.grup(f, "Views", 73); self.mare(g, 1, "🖵", "Presentation\nMode", self.prezentare, w=70)
        g = self.grup(f, "Show", 199, True)
        self.v = {k: tk.BooleanVar(value=v) for k, v in (("Ruler", True), ("Grid", True), ("Page Breaks", True), ("Guides", True),
                                                          ("Dynamic Grid", False), ("AutoConnect", False), ("Connection Points", False))}
        for k, x, y in (("Ruler", 6, 6), ("Grid", 6, 34), ("Page Breaks", 62, 6), ("Guides", 62, 34)):
            tk.Checkbutton(g, text=k, variable=self.v[k], bg=FUNDAL, activebackground=FUNDAL, font=F_BTN, command=a.deseneaza).place(x=x, y=y)
        tp = self.mare(g, 150, "▤", "Task\nPanes ▾", lambda: self.meniu(tp, [("Chat (show / hide)", a.comuta_chat)]), w=44, culoare="#555555")
        g = self.grup(f, "Zoom", 112)
        z = self.mic(g, 4, 4, "🔍", "Zoom", lambda: self.meniu(z, [(f"{p}%", lambda p=p: a.zoom_procent(p)) for p in (50, 75, 100, 150, 200, 400)]))
        self.mic(g, 4, 26, "⤢", "Fit to Window", a.potriveste); self.mic(g, 4, 48, "↔", "Page Width", a.latime_pagina)
        g = self.grup(f, "Visual Aids", 135, True)
        for i, k in enumerate(("Dynamic Grid", "AutoConnect", "Connection Points")):
            tk.Checkbutton(g, text=k, variable=self.v[k], bg=FUNDAL, activebackground=FUNDAL, font=F_BTN).place(x=4, y=2 + i * 22)
        g = self.grup(f, "Window", 225)
        self.mare(g, 4, "🗗", "New\nWindow", w=50); self.mare(g, 56, "▭", "Arrange\nAll", w=50); self.mare(g, 108, "🗗", "Cascade", w=50)
        self.mare(g, 160, "🗔", "Switch\nWindows ▾", w=60)
        g = self.grup(f, "Macros", 95); self.mare(g, 4, "📜", "Macros", w=44); self.mare(g, 50, "🧩", "Add-\nOns ▾", w=42)

    # ---------------------------------------------------------------- acțiuni
    def unealta(self, k):
        self.app.unealta = k
        for n, l in self.unelte.items(): l.config(bg=APASAT if n == k else FUNDAL)
        try: self.app.cv.config(cursor="crosshair" if k != "pointer" else "")
        except Exception: pass
        if k != "pointer": self.app.status.config(text={"connector": "Connector: trage pe schemă de la un punct la altul.", "text": "Text: clic pe schemă unde vrei textul.",
                                                       "rect": "Rectangle: trage pe schemă dreptunghiul.", "ellipse": "Ellipse: trage pe schemă cercul / elipsa."}.get(k, ""))

    def selectate(self):
        a = self.app
        if not a.doc or not a.selectie: a.status.config(text="Selectează întâi obiectele (clic pe ele)."); return []
        a.reselecteaza(); return a.selectie

    def taie(self):
        if self.selectate(): self.app.copiaza(); self.app.sterge_selectia()

    def pensula(self):
        """Format Painter: primul clic copiază stilul formei selectate, al doilea îl pune pe ce ai selectat acum"""
        a = self.app; sel = self.selectate()
        if not sel: return
        if not getattr(self, "stil_copiat", None):
            f = sel[0]; self.stil_copiat = {n: f.cell(n) for n in ("LineColor", "LineWeight", "LinePattern", "FillForegnd", "FillPattern") if f.cell(n) is not None}
            a.status.config(text="Format Painter: stilul e copiat. Selectează alte obiecte și apasă din nou Format Painter."); return
        a.inainte_de_modificare()
        for f in sel:
            for n, v in self.stil_copiat.items(): self._pune(f, n, v)
        self.stil_copiat = None; a.deseneaza(); a.modificat = True; a.status.config(text=f"Format Painter: am pus stilul pe {len(sel)} obiecte.")

    def _pune(self, f, n, v):
        import desen
        c = desen._cell(f.el, n, v)
        if "F" in c.attrib: del c.attrib["F"]

    def stil_forma(self, fill, line):
        sel = self.selectate()
        if not sel: return
        self.app.inainte_de_modificare()
        for f in sel:
            if not f.e1d: self._pune(f, "FillForegnd", fill); self._pune(f, "FillPattern", "1")
            self._pune(f, "LineColor", line)
        self.app.modificat = True; self.app.deseneaza()

    def umple(self, c):
        sel = self.selectate()
        if not sel: return
        self.app.inainte_de_modificare()
        for f in sel:
            if f.e1d: continue
            if c: self._pune(f, "FillForegnd", c); self._pune(f, "FillPattern", "1")
            else: self._pune(f, "FillPattern", "0")
        self.app.modificat = True; self.app.deseneaza()

    def linie(self, culoare=None, gros=None, model=None):
        sel = self.selectate()
        if not sel: return
        self.app.inainte_de_modificare()
        for f in sel:
            if culoare: self._pune(f, "LineColor", culoare)
            if gros: self._pune(f, "LineWeight", "%.6g" % (gros / 72))
            if model is not None: self._pune(f, "LinePattern", model)
        self.app.modificat = True; self.app.deseneaza()

    def aliniaza(self, unde):
        a = self.app; sel = self.selectate()
        if len(sel) < 2: a.status.config(text="Align: selectează cel puțin două obiecte (primul e reperul)."); return
        import gui
        S = a.chat.schema; b0 = sel[0].cutie(); a.inainte_de_modificare()
        for f in sel[1:]:
            b = f.cutie()
            dx = {"l": b0[0] - b[0], "r": b0[2] - b[2], "c": (b0[0] + b0[2] - b[0] - b[2]) / 2}.get(unde, 0)
            dy = {"b": b0[1] - b[1], "t": b0[3] - b[3], "m": (b0[1] + b0[3] - b[1] - b[3]) / 2}.get(unde, 0)
            gui.muta_forma(S, f, dx, dy)
        a.reselecteaza(); a.modificat = True; a.deseneaza()

    def distribuie(self, axa):
        a = self.app; sel = self.selectate()
        if len(sel) < 3: a.status.config(text="Distribute: selectează cel puțin trei obiecte."); return
        import gui
        S = a.chat.schema; k = 0 if axa == "h" else 1
        c = sorted(sel, key=lambda f: (f.cutie()[k] + f.cutie()[k + 2]) / 2)
        p0 = (c[0].cutie()[k] + c[0].cutie()[k + 2]) / 2; p1 = (c[-1].cutie()[k] + c[-1].cutie()[k + 2]) / 2; a.inainte_de_modificare()
        for i, f in enumerate(c[1:-1], 1):
            cur = (f.cutie()[k] + f.cutie()[k + 2]) / 2; tinta = p0 + (p1 - p0) * i / (len(c) - 1)
            gui.muta_forma(S, f, tinta - cur if k == 0 else 0, tinta - cur if k == 1 else 0)
        a.reselecteaza(); a.modificat = True; a.deseneaza()

    def ordine(self, sus):
        a = self.app; sel = self.selectate()
        if not sel: return
        sh = a.doc.pagini[a.chat.ip].shapes_el(); a.inainte_de_modificare()
        for f in sel:
            if f.el in list(sh):
                sh.remove(f.el)
                if sus: sh.append(f.el)
                else: sh.insert(0, f.el)
        a.reselecteaza(); a.modificat = True; a.deseneaza()

    def cauta(self):
        from tkinter import simpledialog
        a = self.app
        if not a.doc: return
        t = simpledialog.askstring("Find", "Find what:", parent=self.root)
        if not t: return
        import comenzi
        k = comenzi.fara_diacritice(t).lower()
        sel = [f for f in a.doc.pagini[a.chat.ip].forme() if k in comenzi.fara_diacritice(f.text_tot() or "").lower()]
        if not sel: a.status.config(text=f"Find: nu găsesc „{t}” pe pagina asta."); return
        a.selectie = sel; a.zoom_pe(sel); a.status.config(text=f"Find: am găsit {len(sel)} obiecte cu „{t}”.")

    def deselecteaza(self):
        self.app.selectie = []; self.app.deseneaza()

    def prezentare(self):
        r = self.root; on = not bool(r.attributes("-fullscreen")); r.attributes("-fullscreen", on)
        if on: r.bind("<Escape>", lambda e: (r.attributes("-fullscreen", False), r.unbind("<Escape>")))


CULORI = [("Black", "#000000"), ("Red", "#FF0000"), ("Blue", "#0000FF"), ("Green", "#00B050"), ("Yellow", "#FFFF00"), ("Orange", "#FFC000"),
          ("Purple", "#7030A0"), ("Gray", "#808080"), ("White", "#FFFFFF")]
STILURI = [("#FFFFFF", "#7F7F7F"), ("#F2F2F2", "#595959"), ("#DEEBF7", "#2E75B6"), ("#FBE5D6", "#C55A11"), ("#E2F0D9", "#548235"),
           ("#FFF2CC", "#BF9000"), ("#F2E6F2", "#7030A0")]
TEME = [("#5B9BD5", "#4472C4"), ("#2E9FD8", "#D6247F"), ("#6D6E70", "#8FB3A6"), ("#1F7DB8", "#FFFFFF"), ("#FFFFFF", "#222222"), ("#8C8A6E", "#A52A1A"),
        ("#A9C1E0", "#FFFFFF"), ("#4A86C5", "#70AD47"), ("#F7F7F7", "#F2B134"), ("#1C6FB6", "#2C5574"), ("#205A62", "#C00000"), ("#FFFFFF", "#DDDDDD")]
