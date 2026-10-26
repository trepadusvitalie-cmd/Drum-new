"""CAD PC – program care arată și lucrează ca AutoCAD 2025 (interfață în rusă): deschide DWG/DXF, zoom, pan, straturi, salvează DWG/DXF.
Pornire: python cad.py [fisier.dwg]"""
import os, sys, threading, traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from stil import *
import fisiere, panglica
from vedere import Vedere
from editare import Editare
from etichete import Etichete, CULORI
from simboluri import Simboluri
from imagini import Imagini
import tiparire

def _langa_exe(nume):
    """fișiere puse de utilizator lângă exe (titlu.txt, logo.png) – nu fac parte din codul programului"""
    d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(d, nume)


def _titlu_app():
    try:
        t = open(_langa_exe("titlu.txt"), encoding="utf-8-sig").read().strip()
        if t: return t
    except Exception: pass
    return "CAD PC 2025"


TITLU_APP = _titlu_app()
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
    # etapa 2: editare
    "ОТМЕНИТЬ": "c_anuleaza", "UNDO": "c_anuleaza", "U": "c_anuleaza", "ПОВТОРИТЬ": "c_reface", "REDO": "c_reface",
    "СТЕРЕТЬ": "c_sterge", "ERASE": "c_sterge", "E": "c_sterge", "С": "c_sterge", "DELETE": "c_sterge",
    "ПЕРЕНЕСТИ": "c_muta", "MOVE": "c_muta", "M": "c_muta", "КОПИРОВАТЬ": "c_copiaza", "COPY": "c_copiaza", "CO": "c_copiaza", "CP": "c_copiaza",
    "ПОВЕРНУТЬ": "c_roteste", "ROTATE": "c_roteste", "RO": "c_roteste", "МАСШТАБ": "c_scaleaza", "SCALE": "c_scaleaza", "SC": "c_scaleaza",
    "ЗЕРКАЛО": "c_oglinda", "MIRROR": "c_oglinda", "MI": "c_oglinda", "РАСЧЛЕНИТЬ": "c_desface", "EXPLODE": "c_desface", "X": "c_desface", "BURST": "c_desface",
    "MOCORO": "c_muta", "ОТРЕЗОК": "c_linie", "LINE": "c_linie", "L": "c_linie", "ПЛИНИЯ": "c_plinie", "PLINE": "c_plinie", "PL": "c_plinie",
    "КРУГ": "c_cerc", "CIRCLE": "c_cerc", "C": "c_cerc", "ВЫБРАТЬВСЕ": "c_tot", "SELECTALL": "c_tot",
    "КОПБУФ": "c_copbuf", "COPYCLIP": "c_copbuf", "ВСТАВИТЬБУФ": "c_lipbuf", "PASTECLIP": "c_lipbuf", "ВЫРЕЗАТЬ": "c_taie", "CUTCLIP": "c_taie",
    "СВОЙСТВА": "c_prop", "PROPERTIES": "c_prop", "CH": "c_prop", "PR": "c_prop",
    # etapa 2: etichete
    "ТЕКСТ": "c_text", "TEXT": "c_text", "DTEXT": "c_text", "DT": "c_text", "МТЕКСТ": "c_mtext", "MTEXT": "c_mtext", "T": "c_mtext", "MT": "c_mtext",
    "TXTEDIT": "c_edtext", "DDEDIT": "c_edtext", "ED": "c_edtext", "TEXTEDIT": "c_edtext", "РЕДТЕКСТ": "c_edtext",
    "НАЙТИ": "c_cauta", "FIND": "c_cauta", "НАЙТИТЕКСТ": "c_cauta", "TCOUNT": "c_numar", "НУМЕРАЦИЯ": "c_numar",
    "ATTOUT": "c_export", "ЭКСПОРТАТР": "c_export", "ИЗВЛЕЧЬ": "c_export", "DATAEXTRACTION": "c_export", "ЭКСПОРТДАННЫХ": "c_export", "XLIST": "c_prop",
    "ATTIN": "c_import", "ИМПОРТАТР": "c_import", "ИМПОРТДАННЫХ": "c_import",
    "АТРРЕД": "c_atr", "EATTEDIT": "c_atr", "ATTEDIT": "c_atr", "ДИСПАТР": "c_atr", "BATTMAN": "c_atr",
    # măsurători și altele
    "ИЗМЕРИТЬ": "c_dist", "DIST": "c_dist", "DI": "c_dist", "MEASUREGEOM": "c_dist", "ПЛОЩАДЬ": "c_arie", "AREA": "c_arie", "AA": "c_arie",
    # etapa 3: simboluri, foi, tipărire
    "ВСТАВИТЬ": "c_insert", "INSERT": "c_insert", "I": "c_insert", "БЛОКИ": "c_insert", "BLOCKSPALETTE": "c_insert",
    "БЛОК": "c_bloc", "BLOCK": "c_bloc", "B": "c_bloc", "ЗАМЕНИТЬБЛОК": "c_inlocbloc", "BLOCKREPLACE": "c_inlocbloc",
    "ПЕЧАТЬ": "c_print", "PLOT": "c_print", "PRINT": "c_print", "ПАКЕТПЕЧАТЬ": "c_print", "ПРЕДВАР": "c_print", "PREVIEW": "c_print",
    "ЭКСПОРТPDF": "c_pdf", "EXPORTPDF": "c_pdf", "ПУБЛИКАЦИЯ": "c_pdf", "PUBLISH": "c_pdf",
    "ЛИСТ": "foaie_noua", "LAYOUT": "foaie_noua",
    "ПРИСОЕД": "c_imagine", "ИЗОБР": "c_imagine", "IMAGEATTACH": "c_imagine", "IMAGE": "c_imagine", "IAT": "c_imagine", "ATTACH": "c_imagine", "TIFF": "c_imagine",
    "УГОЛИЗМ": "c_unghi", "РАДИУСИЗМ": "c_raza", "КООРД": "c_coord", "ID": "c_coord", "ВСТАВИТЬИСХ": "c_liporig", "PASTEORIG": "c_liporig",
}


class App:
    def __init__(self, root, initial=None):
        self.root = root; self.doc = None; self.cale = None; self.modificat = False; self.ultima = None
        self.orto = False
        root.title(TITLU_APP); root.configure(bg=TITLU); root.geometry("1500x900"); self._iconita()
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
        self.v = Vedere(self.cv); self.ed = Editare(self); self.et = Etichete(self); self.sim = Simboluri(self); self.img = Imagini(self); self.ultim_mouse = (0, 0); self._prompt = None
        self._linie_comanda(z)
        self._start(z)
        self._legaturi()
        self.mesaj("CAD PC 2025: открой файл DWG/DXF (Ctrl+O) или введите команду.")
        self.arata_start()
        if initial: root.after(300, lambda: self.deschide_cale(initial))

    # ---------------------------------------------------------------- bara de sus: „A”, acces rapid, titlu, căutare
    def _bara_sus(self):
        b = tk.Frame(self.root, bg=TITLU, height=32); b.pack(fill="x"); b.pack_propagate(False)
        a = tk.Canvas(b, width=24, height=24, bg=TITLU, highlightthickness=0); a.pack(side="left", padx=(6, 0), pady=4)
        a.create_rectangle(1, 1, 23, 23, fill=ROSU_A, outline="#e2393f"); a.create_text(12, 12, text="A", fill="white", font=(F, -15, "bold"))
        sa = tk.Label(b, text="▾", bg=TITLU, fg=TEXT, font=(F, -10), padx=3); sa.pack(side="left", padx=(1, 8))
        for w in (a, sa):
            w.bind("<Button-1>", lambda e: self.meniu_a())
            w.bind("<Enter>", lambda e: sa.config(bg=HOVER)); w.bind("<Leave>", lambda e: sa.config(bg=TITLU))
        self._qat = {}; self._qat_bara = tk.Frame(b, bg=TITLU); self._qat_bara.pack(side="left")
        self._qat_vars = {}
        self._umple_qat()
        sg = tk.Label(b, text="▾", bg=TITLU, fg=TEXT, font=(F, -10)); sg.pack(side="left", padx=4)
        sg.bind("<Button-1>", lambda e: self.meniu_qat(sg))
        tk.Label(b, text="➤ Общий доступ", bg=TITLU, fg="#8ab8ff", font=F_MIC).pack(side="left", padx=6)
        self.logo = self._logo(26)
        self.lbl_titlu = tk.Label(b, text=TITLU_APP, bg=TITLU, fg=TEXT, font=F_TITLU, image=self.logo or "", compound="left", padx=6)
        self.lbl_titlu.place(relx=0.5, rely=0.5, anchor="center")
        h = tk.Label(b, text="?  ▾", bg=TITLU, fg=TEXT, font=(F, -13, "bold"), padx=8); h.pack(side="right")
        h.bind("<Button-1>", lambda e: self.meniu_sus("ajutor", h))
        c = tk.Label(b, text="⩓ ▾", bg=TITLU, fg=TEXT, font=(F, -14), padx=6); c.pack(side="right")
        c.bind("<Button-1>", lambda e: self.meniu_sus("cont", c))
        tk.Label(b, text="🛒", bg=TITLU, fg=TEXT, font=F_ICON_MIC, padx=4).pack(side="right")
        tk.Label(b, text="👤 Вход в службы ▾", bg=TITLU, fg=TEXT, font=F_MIC).pack(side="right", padx=6)
        tk.Label(b, text="🔍", bg=TITLU, fg=TEXT, font=F_ICON_MIC).pack(side="right")
        self.cauta = tk.Entry(b, bg="#2b313a", fg=GRI, insertbackground=TEXT, relief="flat", font=(F, -11, "italic"), width=30)
        self.cauta.insert(0, "Введите ключевое слово/фразу"); self.cauta.pack(side="right", ipady=2)
        self.cauta.bind("<FocusIn>", lambda e: (self.cauta.delete(0, "end"), self.cauta.config(fg=TEXT)) if self.cauta.get().startswith("Введите") else None)
        self.cauta.bind("<Return>", lambda e: self.executa(self.cauta.get()))

    # bara de acces rapid: (nume în meniu, icoană, comandă, vizibil implicit)
    QAT = [("Создать", "🗋", "НОВЫЙ", True), ("Открыть", "🗁", "ОТКРЫТЬ", True), ("Сохранить", "💾", "СОХРАНИТЬ", True), ("Сохранить как...", "💾", "СОХРАНИТЬКАК", True),
           ("Открыть в интернете и на мобильных устройствах", "⇩", "ОТКРЫТЬ", True), ("Сохранить в интернете и на мобильных устройствах", "⇪", "СОХРАНИТЬКАК", True),
           ("Печать", "🖶", "ПЕЧАТЬ", True), ("Отменить", "↶", "ОТМЕНИТЬ", True), ("Повторить", "↷", "ПОВТОРИТЬ", True),
           ("Пакетная печать", "🖶", "ПАКЕТПЕЧАТЬ", False), ("Слой", "☰", "СЛОЙ", False), ("Копирование свойств", "🖌", "КОПИРОВАТЬСВ", False),
           ("Предварительный просмотр", "🔍", "ПРЕДВАР", False), ("Свойства", "▤", "СВОЙСТВА", False), ("Визуализация", "◐", "ВИЗУАЛИЗАЦИЯ", False),
           ("Диспетчер подшивок", "📁", "ПОДШИВКИ", False), ("Рабочее пространство", "⚙", "РАБПРОСТР", False)]

    def _umple_qat(self):
        for w in self._qat_bara.winfo_children(): w.destroy()
        for nume, ic, cmd, vz in self.QAT:
            v = self._qat_vars.setdefault(nume, tk.BooleanVar(value=vz))
            if not v.get(): continue
            l = tk.Label(self._qat_bara, text=ic, bg=TITLU, fg=TEXT, font=F_ICON_MIC, padx=4); l.pack(side="left")
            l.bind("<Button-1>", lambda e, c=cmd: self.executa(c))
            l.bind("<Enter>", lambda e, l=l: l.config(bg=HOVER)); l.bind("<Leave>", lambda e, l=l: l.config(bg=TITLU))

    def meniu_qat(self, w):
        m = tk.Menu(self.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", selectcolor=TEXT, bd=0, font=F_MIC)
        m.add_command(label="Адаптировать панель быстрого доступа", state="disabled")
        for nume, *_ in self.QAT: m.add_checkbutton(label=nume, variable=self._qat_vars[nume], command=self._umple_qat)
        m.add_separator()
        m.add_command(label="Другие команды...", command=self.dialog_ajutor)
        m.add_command(label="Показать строку меню", command=lambda: self.mesaj("Строка меню: используйте меню «A» и ленту."))
        m.add_command(label="Показать под лентой", command=lambda: self.mesaj("Панель быстрого доступа остается над лентой."))
        m.tk_popup(w.winfo_rootx() - 20, w.winfo_rooty() + w.winfo_height())

    def meniu_taburi(self, w):
        m = tk.Menu(self.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", bd=0, font=F_MIC)
        m.add_command(label="      Начало", command=self.arata_start)
        if self.doc: m.add_command(label="  •  " + (os.path.basename(self.cale) if self.cale else "Чертеж1.dwg") + ("*" if self.modificat else ""), command=self.arata_desen)
        m.add_separator()
        m.add_command(label="＋  Новый чертеж", command=self.nou)
        m.add_command(label="🗋  Создать...", command=self.nou)
        m.add_command(label="🗁  Открыть...", command=self.deschide)
        m.add_command(label="💾  Сохранить все", command=self.salveaza)
        m.add_command(label="✖  Закрыть все", command=self.inchide)
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() + w.winfo_height())

    def meniu_foi(self, w):
        m = tk.Menu(self.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", bd=0, font=F_MIC)
        m.add_command(label="＋  Новый лист", command=self.foaie_noua)
        m.add_command(label="▤  Из шаблона...", command=self.foaie_noua)
        m.add_separator()
        m.add_command(label="☰  Диспетчер параметров листов...", command=self.c_print)
        m.add_command(label="✔  Выбрать все листы", command=lambda: self.mesaj("Выбраны все листы."))
        m.add_command(label="🖶  Опубликовать выбранные листы...", command=self.c_pdf)
        m.add_separator()
        m.add_command(label="⇡  Закрепить над строкой состояния", command=lambda: self.mesaj("Вкладки листов: над строкой состояния."))
        m.add_command(label="•  Закрепить на уровне строки состояния", command=lambda: self.mesaj("Вкладки листов: на уровне строки состояния."))
        m.add_separator()
        nume = ["Model"] + ([l.name for l in self.doc.layouts if l.name != "Model"] if self.doc else ["Layout1"])
        for n in nume:
            m.add_command(label=("  •  " if n == getattr(self, "foaie_act", "Model") else "      ") + ("Модель" if n == "Model" else n),
                          command=lambda n=n: self.schimba_foaie(n))
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() - 22 * (len(nume) + 8) - 30)

    def foaie_noua(self):
        if not self.doc: return self.mesaj("Нет открытого чертежа.")
        i = 1
        while f"Layout{i}" in [l.name for l in self.doc.layouts]: i += 1
        lay = self.doc.layouts.new(f"Layout{i}")
        try:                                              # foaie A3 culcată cu un viewport care arată tot modelul
            lay.page_setup(size=(420, 297), margins=(10, 10, 10, 10), units="mm")
            b = self.v.limite() if not self.v.foaie else None
            if b:
                cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2; vh = max(b[3] - b[1], (b[2] - b[0]) * 277 / 400) * 1.05
                lay.add_viewport(center=(210, 148.5), size=(400, 277), view_center_point=(cx, cy), view_height=vh)
        except Exception: traceback.print_exc()
        self.marcheaza(); self.v.versiune += 1
        self.schimba_foaie(f"Layout{i}"); self.mesaj(f"Создан лист Layout{i} (A3) с видовым экраном на всю модель.")

    def meniu_cmd(self, w):
        m = tk.Menu(self.root, tearoff=0, bg="#f0f0f0", fg="#1b1b1b", activebackground="#cfe3ff", activeforeground="#000", bd=1, font=F_MIC)
        sub = tk.Menu(m, tearoff=0, bg="#f0f0f0", fg="#1b1b1b", activebackground="#cfe3ff", font=F_MIC)
        if not hasattr(self, "_v_cmd"): self._v_cmd = {k: tk.BooleanVar(value=True) for k in ("auto", "srch", "mid")}
        sub.add_checkbutton(label="Автозавершение", variable=self._v_cmd["auto"])
        sub.add_checkbutton(label="Поиск системных переменных", variable=self._v_cmd["srch"])
        sub.add_checkbutton(label="Поиск в середине строки", variable=self._v_cmd["mid"])
        m.add_cascade(label="Параметры ввода", menu=sub)
        m.add_command(label="Строки журнала командной строки", command=self.jurnal_comenzi)
        m.add_command(label="Параметры поиска при вводе...", command=lambda: self.mesaj("Поиск при вводе: включен."))
        m.add_separator()
        m.add_command(label="Прозрачность...", command=lambda: self.mesaj("Прозрачность командной строки: 0%."))
        m.add_command(label="Параметры...", command=self.dialog_ajutor)
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() - 150)

    def jurnal_comenzi(self):
        d = tk.Toplevel(self.root); d.title("Журнал командной строки"); d.configure(bg=CORP); d.geometry("620x360")
        t = tk.Text(d, bg="#2b313a", fg=TEXT, relief="flat", font=F_CMD, padx=10, pady=8); t.pack(fill="both", expand=True)
        t.insert("1.0", "\n".join(self.jurnal)); t.see("end"); t.config(state="disabled")

    def meniu_sus(self, k, w):
        m = tk.Menu(self.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", bd=0, font=F_MIC)
        if k == "cont":
            m.add_command(label="Подключиться", state="disabled")
            for t in ("Учетная запись", "Сертифицированное оборудование"): m.add_command(label="      " + t, command=lambda t=t: self.mesaj(f"«{t}» — недоступно (без интернета)."))
            m.add_command(label="CAD PC в Интернете", state="disabled")
            for t in ("Главная страница", "YouTube", "Facebook", "Twitter"): m.add_command(label="      " + t, command=lambda t=t: self.mesaj(f"«{t}» — недоступно (без интернета)."))
        else:
            m.add_command(label="Справка", command=self.dialog_ajutor)
            m.add_command(label="Загрузить автономную справку", command=self.dialog_ajutor)
            m.add_command(label="Обратная связь", command=lambda: self.mesaj("Обратная связь: напишите разработчику CAD PC."))
            m.add_command(label="Загрузить пакеты локализации", command=lambda: self.mesaj("Язык интерфейса: русский."))
            m.add_command(label="Анализатор производительности", command=lambda: self.mesaj(f"Объектов на экране: {len(self.v.prim)}"))
            m.add_separator()
            m.add_command(label="Параметры конфиденциальности...", command=lambda: self.mesaj("CAD PC работает без интернета и ничего не отправляет."))
            m.add_separator()
            m.add_command(label="О программе CAD PC 2025", command=lambda: messagebox.showinfo(TITLU_APP, "CAD PC 2025\nПросмотр и редактирование DWG / DXF.\nDWG — через ODA File Converter или AutoCAD."))
        m.tk_popup(w.winfo_rootx() - 180, w.winfo_rooty() + w.winfo_height())

    def dialog_ajutor(self):
        d = tk.Toplevel(self.root); d.title("Справка CAD PC"); d.configure(bg=CORP); d.geometry("620x520")
        t = tk.Text(d, bg="#2b313a", fg=TEXT, relief="flat", font=F_MIC, wrap="word", padx=12, pady=10); t.pack(fill="both", expand=True)
        t.insert("1.0", """Мышь: колесо — масштаб, нажатое колесо — панорама, двойной щелчок колесом — показать все.
Выбор: щелчок по объекту; рамка слева направо — только целиком внутри; справа налево — пересекающие. Shift+щелчок — убрать из выбора. Esc — снять выбор.
Двойной щелчок: по тексту — редактировать текст; по блоку — атрибуты; по другому объекту — свойства.

Файл: ОТКРЫТЬ (Ctrl+O), СОХРАНИТЬ (Ctrl+S), СОХРАНИТЬКАК (Ctrl+Shift+S), НОВЫЙ (Ctrl+N)
Вид: ПОКАЗАТЬ / Z, РЕГЕН, СЕТКА (F7), ОРТО (F8), объектная привязка (F3)
Слои: СЛОЙ / LA; список слоев на ленте — текущий слой или слой выбранных объектов
Редактирование: ПЕРЕНЕСТИ (M), КОПИРОВАТЬ (CO), ПОВЕРНУТЬ (RO), МАСШТАБ (SC), ЗЕРКАЛО (MI), СТЕРЕТЬ (E, Delete),
  РАСЧЛЕНИТЬ (X), ОТМЕНИТЬ (U, Ctrl+Z), ПОВТОРИТЬ (Ctrl+Y), ВЫБРАТЬВСЕ (Ctrl+A), Ctrl+C / Ctrl+V / Ctrl+X
Рисование: ОТРЕЗОК (L), ПЛИНИЯ (PL), КРУГ (C)
Надписи: ТЕКСТ (DT), МТЕКСТ (T), РЕДТЕКСТ (ED), НАЙТИ (Ctrl+F) — найти и заменить,
  TCOUNT — автонумерация, АТРРЕД — атрибуты блока, ATTOUT — экспорт атрибутов и текстов в Excel, ATTIN — импорт из Excel
Точки: щелчок на чертеже или ввод «x,y»; число — расстояние в направлении мыши (для ПОВЕРНУТЬ — угол, для МАСШТАБ — коэффициент).
Enter или правая кнопка — завершить команду; пустой Enter — повторить последнюю команду.""")
        t.config(state="disabled")

    def _iconita(self):
        """iconița ferestrei: icon.png de lângă exe sau partea pătrată din stânga a lui logo.png"""
        try:
            from PIL import Image, ImageTk
            p = _langa_exe("icon.png")
            if os.path.exists(p): im = Image.open(p).convert("RGBA")
            else:
                p = _langa_exe("logo.png")
                if not os.path.exists(p): return
                im = Image.open(p).convert("RGBA"); im = im.crop((0, 0, min(im.height, im.width), im.height))
            self._icoane = [ImageTk.PhotoImage(im.resize((n, n), Image.LANCZOS)) for n in (48, 32, 16)]
            self.root.iconphoto(True, *self._icoane)
        except Exception: pass

    def _logo(self, inaltime):
        """logo.png de lângă exe, micșorat la înălțimea dată (dacă există)"""
        p = _langa_exe("logo.png")
        if not os.path.exists(p): return None
        try:
            img = tk.PhotoImage(file=p); k = max(1, round(img.height() / inaltime))
            return img.subsample(k, k) if k > 1 else img
        except Exception: return None

    # ---------------------------------------------------------------- tab-urile documentelor
    def _bara_documente(self):
        b = tk.Frame(self.root, bg=FILE, height=28); b.pack(fill="x"); b.pack_propagate(False)
        mt = tk.Label(b, text="☰", bg=FILE, fg="#8ab8ff", font=F_ICON_MIC, padx=10); mt.pack(side="left")
        mt.bind("<Button-1>", lambda e: self.meniu_taburi(mt))
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
        ml = tk.Label(b, text="☰", bg=STARE, fg="#8ab8ff", font=F_ICON_MIC, padx=10); ml.pack(side="left")
        ml.bind("<Button-1>", lambda e: self.meniu_foi(ml))
        self.tab_lay = tk.Frame(b, bg=STARE); self.tab_lay.pack(side="left", fill="y")
        self._taburi_layout(["Model", "Layout1"])
        self.stare = {}
        dr = tk.Frame(b, bg=STARE); dr.pack(side="right", fill="y"); self._dr_stare = dr
        self.lbl_coord = tk.Label(b, text="", bg=STARE, fg=TEXT, font=F_CMD)
        for k, txt, tip, act in (("model", "МОДЕЛЬ", "Пространство модели", False), ("grila", "▦", "Сетка (F7)", True), ("snap", "⠿", "Шаговая привязка", False),
                                 ("orto", "∟", "Орто (F8)", False), ("polar", "◎", "Полярное отслеживание (F10)", True), ("izo", "⟋", "Изометрия", False),
                                 ("osnap", "◰", "Объектная привязка (F3)", True), ("adn", "✈", "Аннотативность", True), ("masc", "1:1", "Масштаб аннотаций", False),
                                 ("set", "⚙", "Рабочее пространство", False), ("plus", "+", "", False), ("izol", "⧉", "Изолировать объекты", False),
                                 ("acc", "⚡", "Аппаратное ускорение", True), ("ecran", "⛶", "Очистить экран", False), ("meniu", "☰", "Адаптация", False)):
            l = tk.Label(dr, text=txt, bg=ACTIV if act else STARE, fg="white", font=(F, -12, "bold") if k == "model" else F_ICON_MIC, padx=5)
            l.pack(side="left", fill="y", padx=1, pady=3); self.stare[k] = [l, act]
            l.bind("<Button-1>", lambda e, k=k: self.comuta_stare(k))
            if k in ("snap", "polar", "osnap", "set", "masc"):                # săgețile ▾ cu meniurile lor
                a = tk.Label(dr, text="▾", bg=STARE, fg=TEXT, font=(F, -10)); a.pack(side="left", fill="y")
                a.bind("<Button-1>", lambda e, k=k, a=a: self.meniu_sageata(k, a))
        self.stare["model"][0].config(bg="#1b2027")

    def _taburi_layout(self, nume):
        for w in self.tab_lay.winfo_children(): w.destroy()
        for n in nume:
            t = "Модель" if n == "Model" else n
            act = n == getattr(self, "foaie_act", "Model")
            l = tk.Label(self.tab_lay, text=t, bg=CORP if act else STARE, fg="white", font=(F, -12, "bold") if act else F_MIC, padx=12)
            l.pack(side="left", fill="y"); l.bind("<Button-1>", lambda e, n=n: self.schimba_foaie(n))
            tk.Label(self.tab_lay, text="/", bg=STARE, fg=SEP, font=F_MIC).pack(side="left")
        pl = tk.Label(self.tab_lay, text="＋", bg=STARE, fg=TEXT, font=F_ICON_MIC, padx=8); pl.pack(side="left")
        pl.bind("<Button-1>", lambda e: self.foaie_noua())

    # elementele meniului „☰” din bara de stare (ca în AutoCAD): (text, cheia butonului sau None, bifat implicit)
    ADAPTARE = [("Координаты", "coord", False), ("Пространство модели", "model", True), None, ("Сетка", "grila", True), ("Режим привязки", "snap", True), None,
                ("Подразумеваемые зависимости", None, False), ("Динамический ввод", None, False), None, ("Режим «Орто»", "orto", True),
                ("Полярное отслеживание", "polar", True), ("Изометрическое проектирование", "izo", True), None, ("Отслеживание привязки к объектам", None, True),
                ("Объектная привязка 2D", "osnap", True), None, ("Толщина линий", None, False), ("Прозрачность", None, False), ("Циклический выбор", None, False),
                ("Объектная привязка 3D", None, False), None, ("Динамическая ПСК", None, False), ("Фильтрация выбора", None, False), ("Гизмо", None, False), None,
                ("Видимость аннотаций", "adn", True), ("Автомасштаб", None, True), ("Масштаб аннотаций", "masc", True), None,
                ("Переключение рабочего пространства", "set", True), None, ("Монитор аннотаций", None, True), ("Единицы", None, False), ("Быстрые свойства", None, False),
                ("Блокировка элементов интерфейса", None, False), None, ("Изолировать объекты", "izol", True), ("Производительность графики", "acc", False), None,
                ("Очистить экран", "ecran", True)]

    def meniu_stare(self):
        if not hasattr(self, "_vad"): self._vad = {t[0]: tk.BooleanVar(value=t[2]) for t in self.ADAPTARE if t}
        m = tk.Menu(self.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", selectcolor=TEXT, bd=0, font=F_MIC)
        for t in self.ADAPTARE:
            if t is None: m.add_separator(); continue
            m.add_checkbutton(label=t[0], variable=self._vad[t[0]], command=lambda t=t: self._aplica_adaptare(t))
        l = self.stare["meniu"][0]; m.tk_popup(l.winfo_rootx() - 230, l.winfo_rooty() - 880)

    def _aplica_adaptare(self, t):
        nume, k, _ = t; v = self._vad[nume].get()
        if k == "coord":
            if v: self.lbl_coord.pack(side="right", padx=10, before=self._dr_stare)
            else: self.lbl_coord.pack_forget()
        elif k and k in self.stare:
            l = self.stare[k][0]
            if v: l.pack(side="left", fill="y", padx=1, pady=3, before=self.stare["meniu"][0])
            else: l.pack_forget()

    MENIURI_SAGEATA = {
        "snap": [("Полярная привязка", False), ("Шаговая привязка", True), None, ("Параметры привязки...", None)],
        "polar": [("90, 540, 810, 1080...", True), ("45, 630, 945, 1260...", False), ("30, 660, 990, 1320...", False), ("23, 675, 1013, 1350...", False),
                  ("18, 684, 1026, 1368...", False), ("15, 690, 1035, 1380...", False), ("10, 700, 1050, 1400...", False), ("5, 710, 1065, 1420...", False),
                  None, ("Параметры отслеживания...", None)],
        "osnap": [("⌐  Конточка", True), ("⊿  Середина", False), ("⊙  Центр", True), ("⊡  Геометрический центр", False), ("▫  Узел", False),
                  ("◇  Квадрант", False), ("✕  Пересечение", True), ("┄  Продолжение", True), ("⊓  Т.вставки", False), ("⊥  Нормаль", False),
                  ("◯  Касательная", False), ("⌇  Ближайшая", False), ("⊠  Кажущееся пересечение", False), ("∥  Параллельно", False), None,
                  ("Параметры объектной привязки...", None)],
        "set": [("Рисование и аннотации", True), ("Основы 3D", False), ("3D-моделирование", False), ("Классический AutoCAD", False), None,
                ("Сохранить текущее как...", None), ("Параметры рабочего пространства...", None), ("Адаптация...", None), ("Отображение меток рабочего пространства", False)],
        "masc": [(m, m == "1:1") for m in ("100:1", "10:1", "1:1", "1:10", "1:100", "1:16", "1:2", "1:20", "1:30", "1:4", "1:40", "1:5", "1:50", "1:8", "2:1", "4:1", "8:1")]
                + [("Пользовательский...", None), None, ("Масштаб внешних ссылок", None), ("Процентные значения", None)],
    }

    def meniu_sageata(self, k, w):
        if not hasattr(self, "_vm"): self._vm = {}
        m = tk.Menu(self.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", selectcolor=TEXT, bd=0, font=F_MIC)
        exclusiv = k in ("snap", "polar", "set", "masc")
        if exclusiv and k not in self._vm:
            self._vm[k] = tk.StringVar(value=next(t[0] for t in self.MENIURI_SAGEATA[k] if t and t[1]))
        for t in self.MENIURI_SAGEATA[k]:
            if t is None: m.add_separator(); continue
            nume, bif = t
            if bif is None: m.add_command(label=nume, command=lambda n=nume: self.mesaj(f"«{n.rstrip('.')}» — в следующей версии."))
            elif exclusiv: m.add_radiobutton(label=nume, variable=self._vm[k], value=nume, command=lambda k=k: self._ales_sageata(k))
            else:
                v = self._vm.setdefault(k + nume, tk.BooleanVar(value=bif)); m.add_checkbutton(label=nume, variable=v)
        m.tk_popup(w.winfo_rootx() - 120, w.winfo_rooty() - 22 * len(self.MENIURI_SAGEATA[k]) - 10)

    def _ales_sageata(self, k):
        v = self._vm[k].get()
        if k == "masc": self.stare["masc"][0].config(text=v)
        self.mesaj({"snap": "Привязка: ", "polar": "Полярные углы: ", "set": "Рабочее пространство: ", "masc": "Масштаб аннотаций: "}[k] + v)

    def comuta_stare(self, k):
        if k == "meniu": return self.meniu_stare()
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
        tk.Label(f, text="⁞ ✕", bg="#9a9a9a", fg="#2b2b2b", font=F_ICON_MIC, padx=4).pack(side="left", fill="y")
        ch = tk.Label(f, text="🔧", bg="#9a9a9a", fg="#2b2b2b", font=F_ICON_MIC, padx=4); ch.pack(side="left", fill="y")
        ch.bind("<Button-1>", lambda e: self.meniu_cmd(ch))
        tk.Label(f, text=">_▾", bg=CMD, fg="#444", font=F_CMD).pack(side="left", padx=(4, 0))
        self.cmd = tk.Entry(f, bg=CMD, fg=CMD_TXT, insertbackground=CMD_TXT, relief="flat", font=(F_CMD[0], -12, "italic"))
        self.cmd.pack(side="left", fill="both", expand=True, padx=4)
        self._placeholder(True)
        self.cmd.bind("<FocusIn>", lambda e: self._placeholder(False)); self.cmd.bind("<FocusOut>", lambda e: self._placeholder(not self.cmd.get()))
        self.cmd.bind("<Return>", self._enter); self.cmd.bind("<Escape>", lambda e: self.anuleaza())
        self.cmd.bind("<Up>", lambda e: self._din_istoric(-1)); self.cmd.bind("<Down>", lambda e: self._din_istoric(1))
        self.linii = []; self.ist_cmd = []; self.ist_i = 0; self.jurnal = getattr(self, 'jurnal', [])

    def _placeholder(self, da):
        txt = getattr(self, "_prompt", None) or "Введите команду"
        if da and not self.cmd.get(): self.cmd.insert(0, txt); self.cmd.config(fg="#1f4f9a" if getattr(self, "_prompt", None) else "#6f6f6f", font=(F_CMD[0], -12, "italic"))
        elif not da and self.cmd.get() in ("Введите команду", getattr(self, "_prompt", None) or "Введите команду"):
            self.cmd.delete(0, "end"); self.cmd.config(fg=CMD_TXT, font=(F_CMD[0], -12))

    def mesaj(self, t):
        if not hasattr(self, "jurnal"): self.jurnal = []
        self.jurnal = (self.jurnal + [t])[-500:]
        self.linii = (self.linii + [t])[-3:]
        self.istoric.config(text="\n".join(self.linii))
        self.istoric.place(relx=0.5, rely=1.0, y=-36, anchor="s", relwidth=0.58)
        if getattr(self, "_ascunde", None): self.root.after_cancel(self._ascunde)
        self._ascunde = self.root.after(9000, self.istoric.place_forget)

    def _enter(self, e=None):
        t = self.cmd.get().strip()
        if t in ("Введите команду", self._prompt or "Введите команду"): t = ""
        self.cmd.delete(0, "end")
        if self.ed.stare:                                              # o comandă așteaptă un punct / o valoare
            self.ed.valoare(t); self.cv.focus_set(); self._placeholder(True); return
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
        self.cmd.delete(0, "end")
        if self.ed.stare: self.ed.opreste()
        elif self.ed.sel: self.ed.goleste()
        else: self.mesaj("*Прервано*")
        self.cv.focus_set(); self._placeholder(True)

    def prompt(self, t):
        self._prompt = t; self.cmd.delete(0, "end"); self._placeholder(True)
        if t: self.cmd.focus_set(); self._placeholder(False); self.cv.focus_set()

    def marcheaza(self):
        self.modificat = True; self._titlu()

    def strat_curent(self):
        n = self.doc.header.get("$CLAYER", "0") if self.doc else "0"
        return n if self.doc and n in self.doc.layers else "0"

    def dupa_selectie(self):
        cb = self.pg.combo.get("слой")
        if not cb or not self.doc: return
        if self.ed.sel:
            straturi = {self.ed.ent(h).dxf.layer for h in self.ed.sel if self.ed.ent(h) is not None}
            cb.set("● " + straturi.pop() if len(straturi) == 1 else "*РАЗЛИЧНЫЕ*")
        else: cb.set("● " + self.strat_curent())

    # ---------------------------------------------------------------- pagina „Начало”
    def _start(self, z):
        s = tk.Frame(z, bg="#1b2027"); self.pagina_start = s
        self.logo_mare = self._logo(90)
        tk.Label(s, text=TITLU_APP, bg="#1b2027", fg="white", font=(F, -34, "bold"), image=self.logo_mare or "", compound="left", padx=12).pack(anchor="w", padx=60, pady=(50, 4))
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
        """meniul „A” ca în AutoCAD: stânga comenzile, dreapta ultimele documente sau opțiunile comenzii de sub mouse"""
        if getattr(self, "_meniu", None) and self._meniu.winfo_exists(): return self._inchide_meniu()
        # cadru în interiorul ferestrei (pe Windows, ferestrele fără bară deschise din clic nu apăreau)
        m = tk.Frame(self.root, bg="#3b4453", highlightthickness=1, highlightbackground=SEP); self._meniu = m
        m.place(x=4, y=32, width=520, height=min(630, max(300, self.root.winfo_height() - 60))); m.lift()
        st = tk.Frame(m, bg="#3b4453", width=160); st.pack(side="left", fill="y"); st.pack_propagate(False)
        dr = tk.Frame(m, bg="#2b313a"); dr.pack(side="left", fill="both", expand=True)
        def gata(f): self._inchide_meniu(); f()
        def dreapta(titlu, optiuni):
            for w in dr.winfo_children(): w.destroy()
            tk.Label(dr, text=titlu, bg="#2b313a", fg=TEXT, font=(F, -13, "bold"), anchor="w").pack(fill="x", padx=12, pady=(14, 8))
            tk.Frame(dr, bg=SEP, height=1).pack(fill="x", padx=10, pady=(0, 6))
            for ic, txt, sub, f in optiuni:
                r = tk.Frame(dr, bg="#2b313a"); r.pack(fill="x", padx=6, pady=1)
                a = tk.Label(r, text=ic, bg="#2b313a", fg=TEXT, font=(F_ICON[0], -20), width=2); a.pack(side="left", padx=6)
                b = tk.Label(r, text=txt + ("\n" + sub if sub else ""), bg="#2b313a", fg=TEXT, font=F_MIC, justify="left", anchor="w"); b.pack(side="left", fill="x", pady=4)
                for w in (r, a, b):
                    w.bind("<Button-1>", lambda e, f=f: gata(f))
                    w.bind("<Enter>", lambda e, r=r: [c.config(bg=HOVER) for c in [r] + r.winfo_children()])
                    w.bind("<Leave>", lambda e, r=r: [c.config(bg="#2b313a") for c in [r] + r.winfo_children()])
        def recente():
            for w in dr.winfo_children(): w.destroy()
            tk.Label(dr, text="🕓  Последние документы", bg="#2b313a", fg=TEXT, font=F_MIC, anchor="w").pack(fill="x", padx=10, pady=(12, 6))
            tk.Label(dr, text="По упорядоченному списку ▾", bg="#2b313a", fg=TEXT, font=F_MIC, anchor="w").pack(fill="x", padx=10, pady=(0, 8))
            for p in fisiere.recente()[:15]:
                l = tk.Label(dr, text="🗎  " + os.path.basename(p), bg="#2b313a", fg=TEXT, font=F_MIC, anchor="w"); l.pack(fill="x", padx=10, pady=3)
                l.bind("<Button-1>", lambda e, p=p: gata(lambda: self.deschide_cale(p)))
                l.bind("<Enter>", lambda e, l=l: l.config(bg=HOVER)); l.bind("<Leave>", lambda e, l=l: l.config(bg="#2b313a"))
            jos = tk.Frame(dr, bg="#2b313a"); jos.pack(side="bottom", fill="x", pady=8)
            b = tk.Label(jos, text="Выход из " + TITLU_APP, bg="#3b4453", fg=TEXT, font=F_MIC, padx=8, pady=3); b.pack(side="right", padx=6)
            b.bind("<Button-1>", lambda e: gata(self.iesire))
            tk.Label(jos, text="Параметры", bg="#3b4453", fg=TEXT, font=F_MIC, padx=8, pady=3).pack(side="right")
        sub = {
            "Создать": [("🗋", "Чертеж", "Создание нового пустого чертежа", self.nou)],
            "Открыть": [("🗁", "Чертеж", "Открытие файла DWG или DXF", self.deschide)] +
                       [("🗎", os.path.basename(p), os.path.dirname(p), (lambda p=p: self.deschide_cale(p))) for p in fisiere.recente()[:5]],
            "Сохранить\nкак": [("💾", "Чертеж", "Сохранение в формате DWG (AutoCAD 2018)", self.salveaza_ca),
                               ("💾", "DWG AutoCAD 2013", "Для старых версий AutoCAD", lambda: self.salveaza_ca("AutoCAD 2013")),
                               ("💾", "DWG AutoCAD 2010", "", lambda: self.salveaza_ca("AutoCAD 2010")),
                               ("💾", "DXF", "Формат обмена чертежами", lambda: self.salveaza_ca("DXF"))],
            "Импорт": [("⇩", "DWG / DXF", "Открыть чертеж", self.deschide)],
            "Экспорт": [("⇧", "DXF", "Сохранить копию в DXF", lambda: self.salveaza_ca("DXF")),
                        ("⇧", "DWG", "Сохранить копию в DWG", self.salveaza_ca),
                        ("📄", "PDF", "Модель или лист в PDF (A0–A5)", self.c_pdf)],
            "Публикация": [("🗂", "Публикация в PDF", "Модель или лист в PDF", self.c_pdf)],
            "Печать": [("🖶", "Печать", "Печать на принтер или в PDF (A0–A5)", self.c_print),
                       ("🔍", "Предварительный просмотр", "Просмотр перед печатью", self.c_print)],
            "Утилиты": [("☰", "Свойства слоев", "Диспетчер слоев", self.dialog_straturi),
                        ("🔎", "Найти и заменить", "Поиск текста в чертеже", lambda: self.executa("НАЙТИ"))],
            "Закрыть": [("✖", "Текущий чертеж", "", self.inchide), ("✖", "Выход", "Закрыть CAD PC", self.iesire)],
        }
        for ic, txt, f in (("🗋", "Создать", self.nou), ("🗁", "Открыть", self.deschide), ("💾", "Сохранить", self.salveaza),
                           ("💾", "Сохранить\nкак", self.salveaza_ca), ("⇩", "Импорт", self.deschide), ("⇧", "Экспорт", self.salveaza_ca),
                           ("🗂", "Публикация", lambda: self.executa("ПУБЛИКАЦИЯ")), ("🖶", "Печать", lambda: self.executa("ПЕЧАТЬ")),
                           ("🔧", "Утилиты", self.dialog_straturi), ("✖", "Закрыть", self.inchide)):
            r = tk.Frame(st, bg="#3b4453", height=56); r.pack(fill="x"); r.pack_propagate(False)
            a = tk.Label(r, text=ic, bg="#3b4453", fg=TEXT, font=(F_ICON[0], -22), width=2); a.pack(side="left", padx=8)
            b = tk.Label(r, text=txt, bg="#3b4453", fg=TEXT, font=F_MIC, justify="left"); b.pack(side="left")
            if txt in sub: tk.Label(r, text="▸", bg="#3b4453", fg=TEXT, font=F_MIC).pack(side="right", padx=6)
            def intra(e, r=r, txt=txt):
                for c in [r] + r.winfo_children(): c.config(bg=HOVER)
                if txt in sub: dreapta(txt.replace("\n", " "), sub[txt])
            for w in (r, a, b):
                w.bind("<Button-1>", lambda e, f=f: gata(f)); w.bind("<Enter>", intra)
                w.bind("<Leave>", lambda e, r=r: [c.config(bg="#3b4453") for c in [r] + r.winfo_children()])
        recente()
        self.root.bind("<Escape>", lambda e: self._inchide_meniu(), add="+")
        # se închide la un clic în afara meniului (nu la pierderea focusului – pe Windows asta îl închidea imediat)
        self.root.after(200, lambda: self.root.bind_all("<Button-1>", self._clic_afara_meniu, add="+"))

    def _clic_afara_meniu(self, e):
        m = getattr(self, "_meniu", None)
        if not m or not m.winfo_exists(): return
        x, y = e.x_root, e.y_root
        if not (m.winfo_rootx() <= x <= m.winfo_rootx() + m.winfo_width() and m.winfo_rooty() <= y <= m.winfo_rooty() + m.winfo_height()):
            self._inchide_meniu()

    def _inchide_meniu(self):
        m = getattr(self, "_meniu", None)
        if m and m.winfo_exists(): m.destroy()
        self._meniu = None
        try: self.root.unbind_all("<Button-1>")
        except Exception: pass

    # ---------------------------------------------------------------- legăturile de tastatură și mouse
    def _legaturi(self):
        cv = self.cv; r = self.root
        cv.bind("<Configure>", lambda e: (self.v.deseneaza() if self.doc else None, self._suprapuneri()))
        cv.bind("<MouseWheel>", lambda e: self._roata(e, 1 if e.delta > 0 else -1))
        cv.bind("<Button-4>", lambda e: self._roata(e, 1)); cv.bind("<Button-5>", lambda e: self._roata(e, -1))
        cv.bind("<ButtonPress-2>", self._pan_start); cv.bind("<B2-Motion>", self._pan); cv.bind("<ButtonRelease-2>", lambda e: self.v.deseneaza())
        cv.bind("<Double-Button-2>", lambda e: self.zoom_ext())
        cv.bind("<Motion>", self._cursor); cv.bind("<Leave>", lambda e: cv.delete("cur"))
        cv.bind("<Button-1>", lambda e: (cv.focus_set(), self.ed.clic(e))); cv.bind("<B1-Motion>", lambda e: (self.ed.trage(e), self._cursor(e)))
        cv.bind("<ButtonRelease-1>", self.ed.elibereaza); cv.bind("<Double-Button-1>", self._dublu_clic)
        cv.bind("<Button-3>", lambda e: self._enter() if self.ed.stare else None)
        cv.bind("<Key>", self._tasta)
        r.bind("<Control-z>", lambda e: self.c_anuleaza()); r.bind("<Control-y>", lambda e: self.c_reface())
        r.bind("<Control-a>", lambda e: self.c_tot() if self.focus_desen() else None); r.bind("<Delete>", lambda e: self.c_sterge() if self.focus_desen() else None)
        r.bind("<Control-c>", lambda e: self.c_copbuf() if self.focus_desen() else None); r.bind("<Control-v>", lambda e: self.c_lipbuf() if self.focus_desen() else None)
        r.bind("<Control-x>", lambda e: self.c_taie() if self.focus_desen() else None); r.bind("<Control-f>", lambda e: self.c_cauta())
        r.bind("<F3>", lambda e: self.comuta_stare("osnap"))
        r.bind("<Control-o>", lambda e: self.deschide()); r.bind("<Control-s>", lambda e: self.salveaza()); r.bind("<Control-S>", lambda e: self.salveaza_ca())
        r.bind("<Control-n>", lambda e: self.nou()); r.bind("<Control-p>", lambda e: self.c_print()); r.bind("<F7>", lambda e: self.comuta_grila()); r.bind("<F8>", lambda e: self.comuta_orto())
        r.protocol("WM_DELETE_WINDOW", self.iesire)

    def focus_desen(self):
        f = self.root.focus_get(); return f is self.cv or f is None

    def _dublu_clic(self, e):
        h = self.ed.la_entitate(e.x, e.y)
        if not h or self.ed.stare: return
        ent = self.ed.ent(h); t = ent.dxftype()
        if t in ("TEXT", "MTEXT"): self.et.dialog_text(ent)
        elif t == "INSERT": self.et.dialog_atribute(ent)
        else: self.et.dialog_proprietati([ent])

    def _tasta(self, e):
        """ca în AutoCAD: ce scrii pe desen merge în linia de comandă"""
        if e.keysym == "Escape": return self.anuleaza()
        if e.keysym == "Delete": return self.c_sterge()
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
        self.ultim_mouse = (e.x, e.y); self.ed.miscare(e)
        if self.doc and self.lbl_coord.winfo_ismapped():
            x, y = self.v.lume(e.x, e.y); self.lbl_coord.config(text=f"{x:.4f}, {y:.4f}, 0.0000")
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
                doc = fisiere.deschide(p); pv = self.v.pregateste(doc); self.root.after(0, lambda: self._deschis(doc, p, pv))
            except Exception as ex:
                traceback.print_exc(); self.root.after(0, lambda: (self.root.config(cursor=""), messagebox.showerror(TITLU_APP, f"Не удалось открыть файл:\n{ex}")))
        threading.Thread(target=lucru, daemon=True).start()

    def _deschis(self, doc, p, gata=None):
        self.root.config(cursor=""); self.doc = doc; self.cale = p; self.modificat = False
        self.ed.sel = set(); self.ed.anulari = []; self.ed.refaceri = []; self.v.selectie = set(); self.v.foaie = None; self.foaie_act = "Model"
        self.v.dosar = os.path.dirname(os.path.abspath(p)); self.arata_desen(); self.v.incarca(doc, gata=gata); self._suprapuneri(); self._titlu(); self._actualizeaza_straturi()
        self._taburi_layout(["Model"] + [l.name for l in doc.layouts if l.name != "Model"])
        n = sum(1 for _ in doc.modelspace())
        self.mesaj(f"Открыт {os.path.basename(p)}: {n} объектов, {len(doc.layers)} слоев.")

    def nou(self):
        if not self._intreaba_salvare(): return
        self.doc = fisiere.nou(); self.cale = None; self.modificat = False; self.ed.sel = set(); self.ed.anulari = []; self.v.selectie = set()
        self.arata_desen(); self.v.incarca(self.doc); self.v.s = 4; self.v.deseneaza(); self._suprapuneri(); self._titlu(); self._actualizeaza_straturi()
        self.mesaj("Новый чертеж.")

    def salveaza(self):
        if self.doc is None: return False
        if not self.cale: return self.salveaza_ca()
        return self._scrie(self.cale)

    def salveaza_ca(self, versiune="AutoCAD 2018"):
        if self.doc is None: return False
        baza = os.path.splitext(os.path.basename(self.cale))[0] if self.cale else "Чертеж1"
        dxf = versiune == "DXF"; ver = "AutoCAD 2018" if dxf else versiune
        tipuri = [("AutoCAD 2018 DXF (*.dxf)", "*.dxf"), (f"Чертеж {ver} (*.dwg)", "*.dwg")] if dxf else [(f"Чертеж {ver} (*.dwg)", "*.dwg"), ("AutoCAD 2018 DXF (*.dxf)", "*.dxf")]
        p = filedialog.asksaveasfilename(title="Сохранение чертежа", initialfile=baza + (".dxf" if dxf else ".dwg"), defaultextension=".dxf" if dxf else ".dwg", filetypes=tipuri)
        if not p: return False
        return self._scrie(p, ver)

    def _scrie(self, p, versiune="AutoCAD 2018"):
        self.root.config(cursor="watch"); self.root.update_idletasks()
        try:
            fisiere.salveaza(self.doc, p, versiune)
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
        return self.dialog_ajutor()

    def _ajutor_vechi(self):
        self.mesaj("Команды: ОТКРЫТЬ, СОХРАНИТЬ, Z, LA | M, CO, RO, SC, MI, E, X, U | L, PL, C | ТЕКСТ, МТЕКСТ, ED, НАЙТИ, TCOUNT, ATTOUT, ATTIN, АТРРЕД.")

    def alege_culoare(self, aci, rgb):
        """din lista de culori: schimbă culoarea obiectelor selectate sau culoarea curentă pentru obiectele noi"""
        if not self.doc: return
        if self.ed.sel:
            self.ed.instantaneu()
            for h in self.ed.sel:
                e = self.ed.ent(h)
                if e is None: continue
                if rgb: e.rgb = rgb
                else:
                    if e.dxf.hasattr("true_color"): e.dxf.discard("true_color")
                    e.dxf.color = aci
            self.ed.gata_modificare(f"Цвет изменен для {len(self.ed.sel)} объектов")
        else:
            self.culoare_curenta = (aci, rgb); self.mesaj("Текущий цвет: " + (("RGB %d,%d,%d" % rgb) if rgb else str(aci)))

    # ---------------------------------------------------------------- etapa 2: comenzi de editare și etichete
    def c_anuleaza(self): self.ed.anuleaza() if self.doc else None
    def c_reface(self): self.ed.reface() if self.doc else None
    def c_sterge(self): self.ed.sterge() if self.doc else None
    def c_desface(self): self.ed.desface() if self.doc else None
    def c_tot(self): self.ed.tot() if self.doc else None
    def c_copbuf(self): self.ed.copiaza_buf() if self.doc else None
    def c_lipbuf(self): self.ed.lipeste_buf() if self.doc else None
    def c_taie(self):
        if self.doc and self.ed.sel: self.ed.copiaza_buf(); self.ed.sterge()
    def c_muta(self): self.ed.incepe("ПЕРЕНЕСТИ", "ПЕРЕНЕСТИ  Базовая точка:")
    def c_copiaza(self): self.ed.incepe("КОПИРОВАТЬ", "КОПИРОВАТЬ  Базовая точка:")
    def c_roteste(self): self.ed.incepe("ПОВЕРНУТЬ", "ПОВЕРНУТЬ  Базовая точка:")
    def c_scaleaza(self): self.ed.incepe("МАСШТАБ", "МАСШТАБ  Базовая точка:")
    def c_oglinda(self): self.ed.incepe("ЗЕРКАЛО", "ЗЕРКАЛО  Первая точка оси отражения:")
    def c_linie(self): self.ed.incepe("ОТРЕЗОК", "ОТРЕЗОК  Первая точка:", nevoie_sel=False)
    def c_plinie(self): self.ed.incepe("ПЛИНИЯ", "ПЛИНИЯ  Начальная точка:", nevoie_sel=False)
    def c_cerc(self): self.ed.incepe("КРУГ", "КРУГ  Центр круга:", nevoie_sel=False)
    def c_text(self): self.ed.incepe("ТЕКСТ", "ТЕКСТ  Начальная точка текста:", nevoie_sel=False)
    def c_mtext(self): self.ed.incepe("ТЕКСТ", "МТЕКСТ  Точка вставки:", nevoie_sel=False, mtext=True)
    def c_cauta(self, txt=""):
        self.et.cauta_inlocuieste(txt if txt != "Поиск текста" else "")
    def c_insert(self, nume=""): self.sim.dialog_inserare(nume.strip() or None)
    def c_bloc(self): self.sim.creeaza() if self.doc else None
    def c_inlocbloc(self): self.sim.inlocuieste() if self.doc else None
    def c_print(self): tiparire.dialog(self)
    def c_imagine(self): self.img.importa()
    def c_pdf(self): tiparire.dialog(self, doar_pdf=True)

    def schimba_foaie(self, n):
        if not self.doc: return
        if self.ed.stare: self.ed.opreste()
        self.foaie_act = n; self.v.arata_foaie(n); self._taburi_layout(["Model"] + [l.name for l in self.doc.layouts if l.name != "Model"])
        self.stare["model"][0].config(text="МОДЕЛЬ" if n == "Model" else "ЛИСТ")
        self.mesaj("Модель" if n == "Model" else f"Лист «{n}»: колесо — масштаб, нажатое колесо — панорама; печать — Ctrl+P.")

    def c_dist(self): self.ed.incepe("ИЗМЕРИТЬ", "ИЗМЕРИТЬ  Первая точка:", nevoie_sel=False)
    def c_arie(self): self.ed.incepe("ПЛОЩАДЬ", "ПЛОЩАДЬ  Первая угловая точка:", nevoie_sel=False)
    def c_unghi(self): self.ed.incepe("УГОЛИЗМ", "УГОЛ  Точка на первой стороне:", nevoie_sel=False)
    def c_coord(self): self.ed.incepe("КООРД", "КООРД  Укажите точку:", nevoie_sel=False)
    def c_liporig(self): self.ed.lipeste_original() if self.doc else None
    def c_raza(self):
        ents = [self.ed.ent(h) for h in self.ed.sel]; c = [e for e in ents if e is not None and e.dxftype() in ("CIRCLE", "ARC")]
        if c: self.mesaj(f"Радиус = {c[0].dxf.radius:.4f},  Диаметр = {2 * c[0].dxf.radius:.4f}")
        else: self.mesaj("РАДИУС: выберите круг или дугу, затем команду.")
    def c_numar(self): self.et.numerotare() if self.doc else None
    def c_export(self): self.et.export_excel()
    def c_import(self): self.et.import_excel()
    def c_edtext(self):
        ents = [self.ed.ent(h) for h in self.ed.sel]; t = [e for e in ents if e is not None and e.dxftype() in ("TEXT", "MTEXT")]
        if t: self.et.dialog_text(t[0])
        else: self.mesaj("Выберите текст (или двойной щелчок по тексту).")
    def c_atr(self):
        b = [self.ed.ent(h) for h in self.ed.sel]; b = [e for e in b if e is not None and e.dxftype() == "INSERT"]
        if b: self.et.dialog_atribute(b[0])
        else: self.mesaj("Выберите блок (или двойной щелчок по блоку).")
    def c_prop(self):
        ents = [self.ed.ent(h) for h in self.ed.sel if self.ed.ent(h) is not None]
        self.et.dialog_proprietati(ents)

    # ---------------------------------------------------------------- straturi
    def _actualizeaza_straturi(self):
        cb = self.pg.combo.get("слой")
        if not cb or not self.doc: return
        nume = sorted(l.dxf.name for l in self.doc.layers)
        cb["values"] = ["● " + n for n in nume]
        cur = self.doc.header.get("$CLAYER", "0"); cb.set("● " + cur)
        if "цвет" in self.pg.combo: self.pg.combo["цвет"]["values"] = ["■ " + n for n, _ in CULORI]; self.pg.combo["цвет"].set("■ ПоСлою")
        for k, val in (("тип", "—— ПоСлою"), ("вес", "—— ПоСлою")):
            if k in self.pg.combo: self.pg.combo[k]["values"] = [val]; self.pg.combo[k].set(val)
        if "высота" in self.pg.combo: self.pg.combo["высота"]["values"] = ["1", "1.5", "2", "2.5", "3", "4", "5", "10"]; self.pg.combo["высота"].set(str(self.et.inaltime))
        if "стильтекста" in self.pg.combo: self.pg.combo["стильтекста"]["values"] = sorted(s.dxf.name for s in self.doc.styles); self.pg.combo["стильтекста"].set("Standard")

    def combo_ales(self, k, val):
        if not self.doc: return
        if k == "слой":
            n = val[2:]
            if self.ed.sel: self.ed.schimba_strat(n)                  # ca în AutoCAD: cu obiecte selectate, lista schimbă stratul lor
            else: self.doc.header["$CLAYER"] = n; self.mesaj(f"Текущий слой: {n}")
        elif k == "цвет":
            v = dict(CULORI)[val[2:]]
            if not self.ed.schimba_culoare(v): self.mesaj("Выберите объекты, затем цвет.")
        elif k == "высота":
            try: self.et.inaltime = float(val); self.mesaj(f"Высота текста: {val}")
            except ValueError: pass

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


def prioritate_mica():
    """Windows: prioritate sub normal și 2 nuclee lăsate libere, ca PC-ul să nu se blocheze"""
    if os.name != "nt": return
    try:
        import ctypes
        k = ctypes.windll.kernel32; h = k.GetCurrentProcess()
        k.SetPriorityClass(h, 0x4000)                      # BELOW_NORMAL_PRIORITY_CLASS
        n = os.cpu_count() or 1
        if n > 2: k.SetProcessAffinityMask(h, ctypes.c_size_t((1 << (n - 2)) - 1))
    except Exception: pass


def main():
    prioritate_mica()
    root = tk.Tk(); App(root, sys.argv[1] if len(sys.argv) > 1 else None); root.mainloop()


if __name__ == "__main__":
    main()
