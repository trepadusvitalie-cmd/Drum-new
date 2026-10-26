"""CAD PC – program care arată și lucrează ca AutoCAD 2025 (interfață în rusă): deschide DWG/DXF, zoom, pan, straturi, salvează DWG/DXF.
Pornire: python cad.py [fisier.dwg]"""
import os, sys, threading, traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from stil import *
import fisiere, panglica
from vedere import Vedere

TITLU_APP = "CAD PC 2025"
ACI = {1: "#ff0000", 2: "#ffff00", 3: "#00ff00", 4: "#00ffff", 5: "#0000ff", 6: "#ff00ff", 7: "#ffffff", 8: "#808080", 9: "#c0c0c0"}
NUME_CUL = {1: "Красный", 2: "Желтый", 3: "Зеленый", 4: "Голубой", 5: "Синий", 6: "Фиолетовый", 7: "Белый", 8: "8", 9: "9"}

# comenzile: numele din AutoCAD (rus și engleză, cu prescurtări) -> metoda
COMENZI = {
    "ОТКРЫТЬ": "deschide", "OPEN": "deschide", "НОВЫЙ": "nou", "NEW": "nou", "QNEW": "nou",
    "СОХРАНИТЬ": "salveaza", "SAVE": "salveaza", "QSAVE": "salveaza", "БСОХРАНИТЬ": "salveaza",
    "СОХРАНИТЬКАК": "salveaza_ca", "SAVEAS": "salveaza_ca", "ЗАКРЫТЬ": "inchide", "CLOSE": "inchide",
    "ПОКАЗАТЬ": "zoom_ext", "ZOOM": "zoom_ext", "Z": "zoom_ext", "П": "zoom_ext", "ZE": "zoom_ext",
    "ПАН": "pan_info", "PAN": "pan_info", "P": "pan_info",
    "СЛОЙ": "dialog_straturi", "LAYER": "dialog_straturi", "LA": "dialog_straturi", "СЛ": "dialog_straturi",
    "РЕГЕН": "regen", "REGEN": "regen", "RE": "regen", "СЕТКА": "comuta_grila", "GRID": "comuta_grila",
    "ОРТО": "comuta_orto", "ORTHO": "comuta_orto", "ВЫХОД": "iesire", "QUIT": "iesire", "EXIT": "iesire",
    "ИМПОРТ": "deschide", "IMPORT": "deschide", "ЭКСПОРТ": "salveaza_ca", "EXPORT": "salveaza_ca",
    "СЛОЙТЕК": "strat_curent_dialog", "СПРАВКА": "ajutor", "HELP": "ajutor", "?": "ajutor",
}


class App:
    def __init__(self, root, initial=None):
        self.root = root; self.doc = None; self.cale = None; self.modificat = False; self.ultima = None
        self.orto = False
        root.title(TITLU_APP); root.configure(bg=TITLU); root.geometry("1500x900")
        try: root.state("zoomed")
        except Exception: pass
        st = ttk.Style(root)
        try: st.theme_use("clam")
        except Exception: pass
        st.configure("Cad.TCombobox", fieldbackground="#2b313a", background=CORP, foreground=TEXT, arrowcolor=TEXT, bordercolor=SEP)
        st.map("Cad.TCombobox", fieldbackground=[("readonly", "#2b313a")], foreground=[("readonly", TEXT)])
        st.configure("Cad.Treeview", background="#2b313a", fieldbackground="#2b313a", foreground=TEXT, rowheight=22, borderwidth=0)
        st.configure("Cad.Treeview.Heading", background=CORP, foreground=TEXT, relief="flat")
        st.map("Cad.Treeview", background=[("selected", ACTIV)])
        root.option_add("*TCombobox*Listbox.background", "#2b313a"); root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self._bara_sus()
        self.pg = panglica.Panglica(self, root)
        self._bara_documente()
        self._jos()
        z = tk.Frame(root, bg=DESEN); z.pack(fill="both", expand=True)
        self.cv = tk.Canvas(z, bg=DESEN, highlightthickness=0, cursor="none" if sys.platform == "win32" else "crosshair")
        self.cv.pack(fill="both", expand=True)
        self.v = Vedere(self.cv)
        self._linie_comanda(z)
        self._start(z)
        self._legaturi()
        self.mesaj("CAD PC 2025: открой файл DWG/DXF (Ctrl+O) или введите команду.")
        self.arata_start()
        if initial: root.after(300, lambda: self.deschide_cale(initial))

    # ---------------------------------------------------------------- bara de sus: „A”, acces rapid, titlu, căutare
    def _bara_sus(self):
        b = tk.Frame(self.root, bg=TITLU, height=32); b.pack(fill="x"); b.pack_propagate(False)
        a = tk.Label(b, text=" A ", bg=ROSU_A, fg="white", font=(F, -15, "bold")); a.pack(side="left", padx=(6, 0), pady=4)
        tk.Label(b, text="▾", bg=TITLU, fg=TEXT, font=(F, -10)).pack(side="left", padx=(1, 8))
        a.bind("<Button-1>", lambda e: self.meniu_a())
        for ic, cmd in (("🗋", "НОВЫЙ"), ("🗁", "ОТКРЫТЬ"), ("💾", "СОХРАНИТЬ"), ("💾", "СОХРАНИТЬКАК"), ("⇪", "ЭКСПОРТ"), ("🖶", "ПЕЧАТЬ"),
                        ("↶", "ОТМЕНИТЬ"), ("↷", "ПОВТОРИТЬ")):
            l = tk.Label(b, text=ic, bg=TITLU, fg=TEXT, font=F_ICON_MIC, padx=4); l.pack(side="left")
            l.bind("<Button-1>", lambda e, c=cmd: self.executa(c))
            l.bind("<Enter>", lambda e, l=l: l.config(bg=HOVER)); l.bind("<Leave>", lambda e, l=l: l.config(bg=TITLU))
        tk.Label(b, text="▾", bg=TITLU, fg=TEXT, font=(F, -10)).pack(side="left", padx=4)
        tk.Label(b, text="➤ Общий доступ", bg=TITLU, fg="#8ab8ff", font=F_MIC).pack(side="left", padx=6)
        self.lbl_titlu = tk.Label(b, text=TITLU_APP, bg=TITLU, fg=TEXT, font=F_TITLU); self.lbl_titlu.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(b, text="?", bg=TITLU, fg=TEXT, font=(F, -14, "bold"), padx=8).pack(side="right")
        tk.Label(b, text="👤 Вход в службы ▾", bg=TITLU, fg=TEXT, font=F_MIC).pack(side="right", padx=6)
        tk.Label(b, text="🔍", bg=TITLU, fg=TEXT, font=F_ICON_MIC).pack(side="right")
        self.cauta = tk.Entry(b, bg="#2b313a", fg=GRI, insertbackground=TEXT, relief="flat", font=(F, -11, "italic"), width=30)
        self.cauta.insert(0, "Введите ключевое слово/фразу"); self.cauta.pack(side="right", ipady=2)
        self.cauta.bind("<FocusIn>", lambda e: (self.cauta.delete(0, "end"), self.cauta.config(fg=TEXT)) if self.cauta.get().startswith("Введите") else None)
        self.cauta.bind("<Return>", lambda e: self.executa(self.cauta.get()))

    # ---------------------------------------------------------------- tab-urile documentelor
    def _bara_documente(self):
        b = tk.Frame(self.root, bg=FILE, height=28); b.pack(fill="x"); b.pack_propagate(False)
        tk.Label(b, text="☰", bg=FILE, fg=TEXT, font=F_ICON_MIC, padx=10).pack(side="left")
        self.tab_start = tk.Label(b, text="Начало", bg=FILE, fg=TEXT, font=F_MIC, padx=14); self.tab_start.pack(side="left", fill="y")
        self.tab_start.bind("<Button-1>", lambda e: self.arata_start())
        self.tab_doc = tk.Frame(b, bg=CORP); self.tab_doc_l = tk.Label(self.tab_doc, text="", bg=CORP, fg="white", font=(F, -12, "bold"), padx=10)
        self.tab_doc_l.pack(side="left", fill="y"); self.tab_doc_l.bind("<Button-1>", lambda e: self.arata_desen())
        x = tk.Label(self.tab_doc, text="✕", bg=CORP, fg=GRI, font=F_MIC, padx=4); x.pack(side="left"); x.bind("<Button-1>", lambda e: self.inchide())
        p = tk.Label(b, text="＋", bg=FILE, fg=TEXT, font=F_ICON_MIC, padx=10); p.pack(side="left"); p.bind("<Button-1>", lambda e: self.nou())
        self._bara_doc = b; self._plus = p

    # ---------------------------------------------------------------- jos: tab-urile Модель / Layout și bara de stare
    def _jos(self):
        b = tk.Frame(self.root, bg=STARE, height=30); b.pack(side="bottom", fill="x"); b.pack_propagate(False)
        tk.Label(b, text="☰", bg=STARE, fg=TEXT, font=F_ICON_MIC, padx=10).pack(side="left")
        self.tab_lay = tk.Frame(b, bg=STARE); self.tab_lay.pack(side="left", fill="y")
        self._taburi_layout(["Model", "Layout1"])
        self.stare = {}
        dr = tk.Frame(b, bg=STARE); dr.pack(side="right", fill="y")
        for k, txt, tip, act in (("model", "МОДЕЛЬ", "Пространство модели", False), ("grila", "▦", "Сетка (F7)", True), ("snap", "⠿", "Шаговая привязка", False),
                                 ("orto", "∟", "Орто (F8)", False), ("polar", "◎", "Полярное отслеживание (F10)", True), ("izo", "⟋", "Изометрия", False),
                                 ("osnap", "◰", "Объектная привязка (F3)", True), ("adn", "✈", "Аннотативность", True), ("masc", "1:1", "Масштаб аннотаций", False),
                                 ("set", "⚙", "Рабочее пространство", False), ("plus", "+", "", False), ("izol", "⧉", "Изолировать объекты", False),
                                 ("acc", "⚡", "Аппаратное ускорение", True), ("ecran", "⛶", "Очистить экран", False), ("meniu", "☰", "Адаптация", False)):
            l = tk.Label(dr, text=txt, bg=ACTIV if act else STARE, fg="white", font=(F, -12, "bold") if k == "model" else F_ICON_MIC, padx=5)
            l.pack(side="left", fill="y", padx=1, pady=3); self.stare[k] = [l, act]
            l.bind("<Button-1>", lambda e, k=k: self.comuta_stare(k))
        self.stare["model"][0].config(bg="#1b2027")

    def _taburi_layout(self, nume):
        for w in self.tab_lay.winfo_children(): w.destroy()
        for n in nume:
            t = "Модель" if n == "Model" else n
            l = tk.Label(self.tab_lay, text=t, bg=CORP if n == "Model" else STARE, fg="white", font=(F, -12, "bold") if n == "Model" else F_MIC, padx=12)
            l.pack(side="left", fill="y"); l.bind("<Button-1>", lambda e, n=n: self.mesaj(f"Лист «{n}»: листы будут доступны в версии 3 (Модель / Layout, печать, PDF)."))
            tk.Label(self.tab_lay, text="/", bg=STARE, fg=SEP, font=F_MIC).pack(side="left")
        tk.Label(self.tab_lay, text="＋", bg=STARE, fg=TEXT, font=F_ICON_MIC, padx=8).pack(side="left")

    def comuta_stare(self, k):
        if k == "grila": return self.comuta_grila()
        if k == "orto": return self.comuta_orto()
        l, act = self.stare[k]
        if k in ("model", "plus", "meniu", "set", "masc"): return
        self.stare[k][1] = not act; l.config(bg=ACTIV if not act else STARE)

    def _seteaza_stare(self, k, act):
        self.stare[k][1] = act; self.stare[k][0].config(bg=ACTIV if act else STARE)

    # ---------------------------------------------------------------- linia de comandă (ca în AutoCAD, jos peste desen)
    def _linie_comanda(self, z):
        self.istoric = tk.Label(z, text="", bg="#2b313a", fg=TEXT, font=F_CMD, anchor="w", justify="left", padx=8)
        f = tk.Frame(z, bg=CMD, height=26); self.fcmd = f
        f.place(relx=0.5, rely=1.0, y=-8, anchor="s", relwidth=0.58, height=26)
        tk.Label(f, text="⁞ ✕ 🔧", bg="#9a9a9a", fg="#2b2b2b", font=F_ICON_MIC, padx=4).pack(side="left", fill="y")
        tk.Label(f, text=">_▾", bg=CMD, fg="#444", font=F_CMD).pack(side="left", padx=(4, 0))
        self.cmd = tk.Entry(f, bg=CMD, fg=CMD_TXT, insertbackground=CMD_TXT, relief="flat", font=(F_CMD[0], -12, "italic"))
        self.cmd.pack(side="left", fill="both", expand=True, padx=4)
        self._placeholder(True)
        self.cmd.bind("<FocusIn>", lambda e: self._placeholder(False)); self.cmd.bind("<FocusOut>", lambda e: self._placeholder(not self.cmd.get()))
        self.cmd.bind("<Return>", self._enter); self.cmd.bind("<Escape>", lambda e: self.anuleaza())
        self.cmd.bind("<Up>", lambda e: self._din_istoric(-1)); self.cmd.bind("<Down>", lambda e: self._din_istoric(1))
        self.linii = []; self.ist_cmd = []; self.ist_i = 0

    def _placeholder(self, da):
        if da and not self.cmd.get(): self.cmd.insert(0, "Введите команду"); self.cmd.config(fg="#6f6f6f", font=(F_CMD[0], -12, "italic"))
        elif not da and self.cmd.get() == "Введите команду": self.cmd.delete(0, "end"); self.cmd.config(fg=CMD_TXT, font=(F_CMD[0], -12))

    def mesaj(self, t):
        self.linii = (self.linii + [t])[-3:]
        self.istoric.config(text="\n".join(self.linii))
        self.istoric.place(relx=0.5, rely=1.0, y=-36, anchor="s", relwidth=0.58)
        if getattr(self, "_ascunde", None): self.root.after_cancel(self._ascunde)
        self._ascunde = self.root.after(9000, self.istoric.place_forget)

    def _enter(self, e=None):
        t = self.cmd.get().strip()
        if t == "Введите команду": t = ""
        self.cmd.delete(0, "end")
        if not t and self.ultima: t = self.ultima                      # Enter gol repetă ultima comandă, ca în AutoCAD
        if t: self.ist_cmd.append(t); self.ist_i = len(self.ist_cmd); self.executa(t)
        self.cv.focus_set(); self._placeholder(True)

    def _din_istoric(self, d):
        if not self.ist_cmd: return
        self.ist_i = max(0, min(len(self.ist_cmd) - 1, self.ist_i + d))
        self.cmd.delete(0, "end"); self.cmd.insert(0, self.ist_cmd[self.ist_i])

    def executa(self, t):
        t = t.strip()
        if not t: return
        cuv = t.split(None, 1); nume = cuv[0].lstrip("_.-").upper(); rest = cuv[1] if len(cuv) > 1 else ""
        self.mesaj("Команда: " + t)
        m = COMENZI.get(nume)
        if m:
            self.ultima = nume
            try: getattr(self, m)(rest) if rest else getattr(self, m)()
            except TypeError: getattr(self, m)()
            except Exception as ex: traceback.print_exc(); self.mesaj(f"Ошибка: {ex}")
        else:
            self.mesaj(f"«{nume}» — будет работать в следующей версии CAD PC (этап 2: редактирование и надписи, этап 3: блоки, листы, печать).")

    def anuleaza(self):
        self.cmd.delete(0, "end"); self.mesaj("*Прервано*"); self.cv.focus_set(); self._placeholder(True)

    # ---------------------------------------------------------------- pagina „Начало”
    def _start(self, z):
        s = tk.Frame(z, bg="#1b2027"); self.pagina_start = s
        tk.Label(s, text="CAD PC 2025", bg="#1b2027", fg="white", font=(F, -34, "bold")).pack(anchor="w", padx=60, pady=(50, 4))
        tk.Label(s, text="DWG / DXF — просмотр, редактирование, надписи, экспорт", bg="#1b2027", fg=GRI, font=(F, -14)).pack(anchor="w", padx=60)
        r = tk.Frame(s, bg="#1b2027"); r.pack(anchor="w", padx=60, pady=24)
        for txt, cmd in (("Новый  ▾", self.nou), ("Открыть...", self.deschide)):
            b = tk.Label(r, text=txt, bg=ALBASTRU if txt.startswith("Новый") else CORP, fg="white", font=(F, -14), padx=22, pady=8)
            b.pack(side="left", padx=(0, 12)); b.bind("<Button-1>", lambda e, c=cmd: c())
        tk.Label(s, text="Последние", bg="#1b2027", fg="white", font=(F, -16, "bold")).pack(anchor="w", padx=60, pady=(10, 6))
        self.lista_start = tk.Frame(s, bg="#1b2027"); self.lista_start.pack(anchor="w", padx=60, fill="x")
        c = fisiere.ce_convertor()
        tk.Label(s, text=("DWG: через " + c) if c else "DWG: установите бесплатный ODA File Converter (opendesign.com) или AutoCAD. DXF открывается всегда.",
                 bg="#1b2027", fg=GRI, font=(F, -12)).pack(side="bottom", anchor="w", padx=60, pady=20)

    def _umple_start(self):
        for w in self.lista_start.winfo_children(): w.destroy()
        for p in fisiere.recente()[:12]:
            l = tk.Label(self.lista_start, text="🗎  " + os.path.basename(p) + "      " + os.path.dirname(p), bg="#1b2027", fg=TEXT, font=(F, -13), anchor="w")
            l.pack(fill="x", pady=2); l.bind("<Button-1>", lambda e, p=p: self.deschide_cale(p))
            l.bind("<Enter>", lambda e, l=l: l.config(fg="#8ab8ff")); l.bind("<Leave>", lambda e, l=l: l.config(fg=TEXT))

    def arata_start(self):
        self._umple_start(); self.pagina_start.place(x=0, y=0, relwidth=1, relheight=1); self.pagina_start.lift()
        self.tab_start.config(bg=CORP, fg="white")

    def arata_desen(self):
        if self.doc is None: return
        self.pagina_start.place_forget(); self.tab_start.config(bg=FILE, fg=TEXT)
        self.fcmd.lift(); self.cv.focus_set()

    # ---------------------------------------------------------------- meniul „A”
    def meniu_a(self):
        m = tk.Toplevel(self.root); m.overrideredirect(True); m.configure(bg="#3b4453")
        x = self.root.winfo_rootx() + 4; y = self.root.winfo_rooty() + 32; m.geometry(f"500x620+{x}+{y}")
        st = tk.Frame(m, bg="#3b4453", width=150); st.pack(side="left", fill="y"); st.pack_propagate(False)
        dr = tk.Frame(m, bg="#2b313a"); dr.pack(side="left", fill="both", expand=True)
        def gata(f): m.destroy(); f()
        for ic, txt, f in (("🗋", "Создать", self.nou), ("🗁", "Открыть", self.deschide), ("💾", "Сохранить", self.salveaza),
                           ("💾", "Сохранить\nкак", self.salveaza_ca), ("⇩", "Импорт", self.deschide), ("⇧", "Экспорт", self.salveaza_ca),
                           ("🗂", "Публикация", lambda: self.executa("ПУБЛИКАЦИЯ")), ("🖶", "Печать", lambda: self.executa("ПЕЧАТЬ")),
                           ("🔧", "Утилиты", self.dialog_straturi), ("✖", "Закрыть", self.inchide)):
            r = tk.Frame(st, bg="#3b4453", height=56); r.pack(fill="x"); r.pack_propagate(False)
            a = tk.Label(r, text=ic, bg="#3b4453", fg=TEXT, font=(F_ICON[0], -22), width=2); a.pack(side="left", padx=8)
            b = tk.Label(r, text=txt, bg="#3b4453", fg=TEXT, font=F_MIC, justify="left"); b.pack(side="left")
            tk.Label(r, text="▸", bg="#3b4453", fg=TEXT, font=F_MIC).pack(side="right", padx=6)
            for w in (r, a, b):
                w.bind("<Button-1>", lambda e, f=f: gata(f))
                w.bind("<Enter>", lambda e, r=r: [c.config(bg=HOVER) for c in [r] + r.winfo_children()])
                w.bind("<Leave>", lambda e, r=r: [c.config(bg="#3b4453") for c in [r] + r.winfo_children()])
        tk.Label(dr, text="🕓  Последние документы", bg="#2b313a", fg=TEXT, font=F_MIC, anchor="w").pack(fill="x", padx=10, pady=(12, 6))
        tk.Label(dr, text="По упорядоченному списку ▾", bg="#2b313a", fg=TEXT, font=F_MIC, anchor="w").pack(fill="x", padx=10, pady=(0, 8))
        for p in fisiere.recente()[:15]:
            l = tk.Label(dr, text="🗎  " + os.path.basename(p), bg="#2b313a", fg=TEXT, font=F_MIC, anchor="w"); l.pack(fill="x", padx=10, pady=3)
            l.bind("<Button-1>", lambda e, p=p: gata(lambda: self.deschide_cale(p)))
            l.bind("<Enter>", lambda e, l=l: l.config(bg=HOVER)); l.bind("<Leave>", lambda e, l=l: l.config(bg="#2b313a"))
        jos = tk.Frame(dr, bg="#2b313a"); jos.pack(side="bottom", fill="x", pady=8)
        b = tk.Label(jos, text="Выход из CAD PC 2025", bg="#3b4453", fg=TEXT, font=F_MIC, padx=8, pady=3); b.pack(side="right", padx=6)
        b.bind("<Button-1>", lambda e: gata(self.iesire))
        tk.Label(jos, text="Параметры", bg="#3b4453", fg=TEXT, font=F_MIC, padx=8, pady=3).pack(side="right")
        m.bind("<FocusOut>", lambda e: m.destroy()); m.bind("<Escape>", lambda e: m.destroy()); m.focus_force()

    # ---------------------------------------------------------------- legăturile de tastatură și mouse
    def _legaturi(self):
        cv = self.cv; r = self.root
        cv.bind("<Configure>", lambda e: (self.v.deseneaza() if self.doc else None, self._suprapuneri()))
        cv.bind("<MouseWheel>", lambda e: self._roata(e, 1 if e.delta > 0 else -1))
        cv.bind("<Button-4>", lambda e: self._roata(e, 1)); cv.bind("<Button-5>", lambda e: self._roata(e, -1))
        cv.bind("<ButtonPress-2>", self._pan_start); cv.bind("<B2-Motion>", self._pan); cv.bind("<ButtonRelease-2>", lambda e: self.v.deseneaza())
        cv.bind("<Double-Button-2>", lambda e: self.zoom_ext())
        cv.bind("<Motion>", self._cursor); cv.bind("<Leave>", lambda e: cv.delete("cur"))
        cv.bind("<Key>", self._tasta)
        r.bind("<Control-o>", lambda e: self.deschide()); r.bind("<Control-s>", lambda e: self.salveaza()); r.bind("<Control-S>", lambda e: self.salveaza_ca())
        r.bind("<Control-n>", lambda e: self.nou()); r.bind("<F7>", lambda e: self.comuta_grila()); r.bind("<F8>", lambda e: self.comuta_orto())
        r.protocol("WM_DELETE_WINDOW", self.iesire)

    def _tasta(self, e):
        """ca în AutoCAD: ce scrii pe desen merge în linia de comandă"""
        if e.keysym == "Escape": return self.anuleaza()
        if e.keysym in ("Return", "space"): return self._enter()
        if e.char and e.char.isprintable() and not (e.state & 0x4):
            self.cmd.focus_set(); self._placeholder(False); self.cmd.insert("end", e.char)

    def _roata(self, e, d):
        if self.doc: self.v.zoom(1.2 if d > 0 else 1 / 1.2, e.x, e.y)

    def _pan_start(self, e):
        self._p0 = (e.x, e.y); self.cv.config(cursor="fleur")

    def _pan(self, e):
        if not self.doc: return
        dx, dy = e.x - self._p0[0], e.y - self._p0[1]; self._p0 = (e.x, e.y); self.v.deplaseaza(dx, dy)

    def _cursor(self, e):
        cv = self.cv; cv.delete("cur")
        if str(cv.cget("cursor")) == "fleur": cv.config(cursor="none" if sys.platform == "win32" else "crosshair")
        L = 60; c = "#ffffff"
        cv.create_line(e.x - L, e.y, e.x + L, e.y, fill=c, tags="cur"); cv.create_line(e.x, e.y - L, e.x, e.y + L, fill=c, tags="cur")
        cv.create_rectangle(e.x - 4, e.y - 4, e.x + 4, e.y + 4, outline=c, tags="cur")

    # ---------------------------------------------------------------- suprapunerile fixe: eticheta vederii, ViewCube, bara de navigare, axele
    def _suprapuneri(self):
        cv = self.cv; cv.delete("ov"); W, H = max(1, cv.winfo_width()), max(1, cv.winfo_height())
        cv.create_text(6, 10, text="[–][Сверху][2D-каркас]", fill=TEXT, anchor="w", font=F_MIC, tags="ov")
        cx, cy, r = W - 92, 110, 52                                          # ViewCube
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline="#59616d", width=10, tags="ov")
        cv.create_rectangle(cx - 25, cy - 25, cx + 25, cy + 25, fill="#cfd3d8", outline="#9aa0a8", tags="ov")
        cv.create_text(cx, cy, text="Сверху", fill="#3b3b3b", font=(F, -11), tags="ov")
        for t, dx, dy in (("С", 0, -r), ("Ю", 0, r), ("В", r, 0), ("З", -r, 0)):
            cv.create_text(cx + dx, cy + dy, text=t, fill=TEXT, font=(F, -16), tags="ov")
        cv.create_rectangle(cx - 22, cy + r + 18, cx + 22, cy + r + 34, fill="#59616d", outline="", tags="ov")
        cv.create_text(cx, cy + r + 26, text="МСК ▾", fill=TEXT, font=(F, -9), tags="ov")
        nx, ny = W - 22, cy + r + 60                                        # bara de navigare
        cv.create_rectangle(nx - 14, ny, nx + 14, ny + 200, fill="#3b4453", outline="#59616d", tags="ov")
        for i, t in enumerate(("◎", "✋", "⤢", "⊕", "▶")):
            cv.create_text(nx, ny + 22 + i * 38, text=t, fill=GRI, font=F_ICON_MIC, tags="ov")
        ox, oy = 20, H - 50                                                  # axele X/Y
        cv.create_line(ox, oy, ox, oy - 52, fill="#e8ebef", width=2, tags="ov"); cv.create_line(ox, oy, ox + 52, oy, fill="#e8ebef", width=2, tags="ov")
        cv.create_rectangle(ox - 4, oy - 4, ox + 4, oy + 4, outline="#e8ebef", tags="ov")
        cv.create_text(ox, oy - 62, text="Y", fill=TEXT, font=(F, -14), tags="ov"); cv.create_text(ox + 62, oy, text="✕", fill=TEXT, font=(F, -14), tags="ov")
        cv.tag_raise("ov")

    # ---------------------------------------------------------------- fișiere
    def _intreaba_salvare(self):
        if self.doc is None or not self.modificat: return True
        r = messagebox.askyesnocancel(TITLU_APP, f"Сохранить изменения в {os.path.basename(self.cale or 'Чертеж1.dwg')}?")
        if r is None: return False
        if r: return self.salveaza()
        return True

    def deschide(self):
        p = filedialog.askopenfilename(title="Выбор файла", filetypes=[("Чертеж (*.dwg; *.dxf)", "*.dwg *.dxf"), ("DWG", "*.dwg"), ("DXF", "*.dxf"), ("Все файлы", "*.*")])
        if p: self.deschide_cale(p)

    def deschide_cale(self, p):
        if not self._intreaba_salvare(): return
        self.mesaj(f"Открытие {os.path.basename(p)}…" + (" (DWG → " + (fisiere.ce_convertor() or "?") + ")" if p.lower().endswith(".dwg") else ""))
        self.root.config(cursor="watch"); self.root.update_idletasks()
        def lucru():
            try:
                doc = fisiere.deschide(p); self.root.after(0, lambda: self._deschis(doc, p))
            except Exception as ex:
                traceback.print_exc(); self.root.after(0, lambda: (self.root.config(cursor=""), messagebox.showerror(TITLU_APP, f"Не удалось открыть файл:\n{ex}")))
        threading.Thread(target=lucru, daemon=True).start()

    def _deschis(self, doc, p):
        self.root.config(cursor=""); self.doc = doc; self.cale = p; self.modificat = False
        self.arata_desen(); self.v.incarca(doc); self._suprapuneri(); self._titlu(); self._actualizeaza_straturi()
        self._taburi_layout(["Model"] + [l.name for l in doc.layouts if l.name != "Model"])
        n = sum(1 for _ in doc.modelspace())
        self.mesaj(f"Открыт {os.path.basename(p)}: {n} объектов, {len(doc.layers)} слоев.")

    def nou(self):
        if not self._intreaba_salvare(): return
        self.doc = fisiere.nou(); self.cale = None; self.modificat = False
        self.arata_desen(); self.v.incarca(self.doc); self.v.s = 4; self.v.deseneaza(); self._suprapuneri(); self._titlu(); self._actualizeaza_straturi()
        self.mesaj("Новый чертеж.")

    def salveaza(self):
        if self.doc is None: return False
        if not self.cale: return self.salveaza_ca()
        return self._scrie(self.cale)

    def salveaza_ca(self):
        if self.doc is None: return False
        baza = os.path.splitext(os.path.basename(self.cale))[0] if self.cale else "Чертеж1"
        p = filedialog.asksaveasfilename(title="Сохранение чертежа", initialfile=baza + ".dwg", defaultextension=".dwg",
                                         filetypes=[("Чертеж AutoCAD 2018 (*.dwg)", "*.dwg"), ("AutoCAD 2018 DXF (*.dxf)", "*.dxf")])
        if not p: return False
        return self._scrie(p)

    def _scrie(self, p):
        self.root.config(cursor="watch"); self.root.update_idletasks()
        try:
            fisiere.salveaza(self.doc, p)
        except Exception as ex:
            self.root.config(cursor=""); messagebox.showerror(TITLU_APP, f"Не удалось сохранить:\n{ex}"); return False
        self.root.config(cursor=""); self.cale = p; self.modificat = False; self._titlu()
        self.mesaj(f"Сохранено: {p}"); return True

    def inchide(self):
        if not self._intreaba_salvare(): return
        self.doc = None; self.cale = None; self.cv.delete("e"); self.cv.delete("g"); self._titlu(); self.arata_start()

    def iesire(self):
        if self._intreaba_salvare(): self.root.destroy()

    def _titlu(self):
        n = os.path.basename(self.cale) if self.cale else ("Чертеж1.dwg" if self.doc else "")
        self.lbl_titlu.config(text=f"{TITLU_APP}    {n}{'*' if self.modificat else ''}")
        self.root.title(f"{TITLU_APP} - [{n}]" if n else TITLU_APP)
        if self.doc:
            self.tab_doc_l.config(text=n + ("*" if self.modificat else "")); self.tab_doc.pack(side="left", fill="y", before=self._plus)
        else: self.tab_doc.pack_forget()

    # ---------------------------------------------------------------- vedere
    def zoom_ext(self, *a):
        if self.doc: self.v.zoom_extinde(); self.mesaj("Показать: границы")

    def pan_info(self):
        self.mesaj("Панорамирование: удерживайте колесо мыши и перемещайте. Двойной щелчок колесом — показать все.")

    def regen(self):
        if self.doc: self.v.reconstruieste(); self.v.deseneaza(); self.mesaj("Регенерация модели.")

    def comuta_grila(self):
        self.v.grila = not self.v.grila; self._seteaza_stare("grila", self.v.grila)
        if self.doc: self.v.deseneaza()
        self.mesaj("<Сетка вкл>" if self.v.grila else "<Сетка откл>")

    def comuta_orto(self):
        self.orto = not self.orto; self._seteaza_stare("orto", self.orto); self.mesaj("<Орто вкл>" if self.orto else "<Орто откл>")

    def ajutor(self):
        self.mesaj("Команды: ОТКРЫТЬ, СОХРАНИТЬ, СОХРАНИТЬКАК, ПОКАЗАТЬ (Z), СЛОЙ (LA), РЕГЕН, СЕТКА (F7), ОРТО (F8). Колесо — масштаб, нажатое колесо — панорама.")

    # ---------------------------------------------------------------- straturi
    def _actualizeaza_straturi(self):
        cb = self.pg.combo.get("слой")
        if not cb or not self.doc: return
        nume = sorted(l.dxf.name for l in self.doc.layers)
        cb["values"] = ["● " + n for n in nume]
        cur = self.doc.header.get("$CLAYER", "0"); cb.set("● " + cur)
        for k, val in (("цвет", "■ ПоСлою"), ("тип", "—— ПоСлою"), ("вес", "—— ПоСлою")):
            if k in self.pg.combo: self.pg.combo[k]["values"] = [val]; self.pg.combo[k].set(val)

    def combo_ales(self, k, val):
        if k == "слой" and self.doc:
            n = val[2:]; self.doc.header["$CLAYER"] = n; self.mesaj(f"Текущий слой: {n}")

    def strat_curent_dialog(self):
        self.dialog_straturi()

    def dialog_straturi(self):
        if not self.doc: return self.mesaj("Нет открытого чертежа.")
        d = tk.Toplevel(self.root); d.title("Диспетчер свойств слоев"); d.configure(bg=CORP); d.geometry("820x480"); d.transient(self.root)
        bara = tk.Frame(d, bg=CORP); bara.pack(fill="x", padx=6, pady=6)
        cols = ("st", "nume", "vkl", "zam", "blok", "cvet", "tip", "ves")
        tv = ttk.Treeview(d, columns=cols, show="headings", style="Cad.Treeview")
        for c, t, w in zip(cols, ("Статус", "Имя", "Вкл", "Заморозить", "Блокировать", "Цвет", "Тип линий", "Вес линий"), (60, 240, 50, 90, 90, 110, 100, 80)):
            tv.heading(c, text=t); tv.column(c, width=w, anchor="w" if c in ("nume", "cvet", "tip") else "center")
        tv.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        def umple():
            tv.delete(*tv.get_children()); cur = self.doc.header.get("$CLAYER", "0")
            for l in sorted(self.doc.layers, key=lambda l: l.dxf.name.lower()):
                c = abs(l.dxf.get("color", 7))
                tv.insert("", "end", iid=l.dxf.name, values=("✔" if l.dxf.name == cur else "", l.dxf.name, "💡" if l.is_on() else "○",
                          "❄" if l.is_frozen() else "☀", "🔒" if l.is_locked() else "🔓", "■ " + NUME_CUL.get(c, str(c)), l.dxf.get("linetype", "Continuous"), "—— По умолч."))
        def schimba(e):
            col = tv.identify_column(e.x); it = tv.identify_row(e.y)
            if not it: return
            l = self.doc.layers.get(it)
            if col == "#3": l.off() if l.is_on() else l.on()
            elif col == "#4":
                if it == self.doc.header.get("$CLAYER", "0"): return self.mesaj("Текущий слой нельзя заморозить.")
                l.thaw() if l.is_frozen() else l.freeze()
            elif col == "#5": l.unlock() if l.is_locked() else l.lock()
            elif col == "#6":
                r = colorchooser.askcolor(parent=d, title="Выбор цвета")
                if r and r[1]:
                    from ezdxf import colors as ec
                    l.rgb = tuple(int(v) for v in r[0])
            elif col == "#1": self.doc.header["$CLAYER"] = it
            else: return
            self.modificat = True; self._titlu(); umple(); self.v.reconstruieste(); self.v.deseneaza(); self._actualizeaza_straturi()
        tv.bind("<Button-1>", lambda e: d.after(1, lambda: schimba(e)))
        def nou():
            i = 1
            while f"Слой{i}" in self.doc.layers: i += 1
            self.doc.layers.add(f"Слой{i}", color=7); self.modificat = True; umple(); self._actualizeaza_straturi()
        def sterge():
            for it in tv.selection():
                if it in ("0", "Defpoints") or it == self.doc.header.get("$CLAYER", "0"): continue
                if any(e.dxf.layer == it for e in self.doc.modelspace()): self.mesaj(f"Слой «{it}» не пуст — не удален."); continue
                self.doc.layers.remove(it); self.modificat = True
            umple(); self._actualizeaza_straturi()
        def curent():
            s = tv.selection()
            if s: self.doc.header["$CLAYER"] = s[0]; umple(); self._actualizeaza_straturi()
        for txt, f in (("✚ Новый слой", nou), ("✖ Удалить слой", sterge), ("✔ Сделать текущим", curent)):
            b = tk.Label(bara, text=txt, bg=FILE, fg=TEXT, font=F_MIC, padx=10, pady=4); b.pack(side="left", padx=(0, 6))
            b.bind("<Button-1>", lambda e, f=f: f())
        tk.Label(bara, text="Щелчок по 💡 / ❄ / 🔒 / цвету — изменить", bg=CORP, fg=GRI, font=F_MIC).pack(side="right")
        umple()


def main():
    root = tk.Tk(); App(root, sys.argv[1] if len(sys.argv) > 1 else None); root.mainloop()


if __name__ == "__main__":
    main()
