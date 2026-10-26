"""CAD PC 3.3 – meniurile de clic dreapta (desen, tab-uri, foi, panglică), importuri (PDF, DWG/DXF), «Запись блока на диск»,
blocuri recente / preferate, atribute (Несколько, afișare, sincronizare, punct de bază), export foi PDF, «Параметры», pseudonime."""
import json, os, subprocess, sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from stil import *
from unelte import dialog, buton, eticheta, intrare, numar

M_STIL = dict(tearoff=0, bg="#f0f0f0", fg="#1b1b1b", activebackground="#0078d7", activeforeground="white", bd=1, font=(F, -12))


def _setari_fisier():
    d = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "CAD_PC"); os.makedirs(d, exist_ok=True)
    return os.path.join(d, "setari.json")


def setari():
    try: return json.load(open(_setari_fisier(), encoding="utf-8"))
    except Exception: return {}


def salveaza_setari(s):
    try: json.dump(s, open(_setari_fisier(), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception: pass


def calc_sigur(expr):
    """calculator fără eval: doar numere, + - * / ** %, paranteze și funcțiile din math enumerate mai jos"""
    import ast, math as _m, operator as op
    fn = {k: getattr(_m, k) for k in ("sqrt", "sin", "cos", "tan", "atan", "atan2", "degrees", "radians", "log", "log10", "exp", "hypot", "floor", "ceil")}
    fn.update(abs=abs, round=round, min=min, max=max); const = {"pi": _m.pi, "e": _m.e}
    ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow, ast.Mod: op.mod, ast.USub: op.neg, ast.UAdd: op.pos}
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.Name) and n.id in const: return const[n.id]
        if isinstance(n, ast.BinOp) and type(n.op) in ops:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 1000: raise ValueError("слишком большая степень")
            return ops[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in ops: return ops[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in fn and not n.keywords: return fn[n.func.id](*[ev(a) for a in n.args])
        raise ValueError("недопустимое выражение")
    return ev(ast.parse(expr.replace(",", ".").replace("^", "**"), mode="eval"))


class Meniuri:
    def __init__(self, app):
        self.app = app; s = setari()
        self.blocuri_recente = s.get("blocuri_recente", []); self.blocuri_pref = s.get("blocuri_pref", [])
        self.aliasuri = s.get("aliasuri", {})

    @property
    def doc(self): return self.app.doc

    @property
    def ed(self): return self.app.ed

    def _salv(self):
        s = setari(); s.update(blocuri_recente=self.blocuri_recente[:20], blocuri_pref=self.blocuri_pref, aliasuri=self.aliasuri); salveaza_setari(s)

    # ================================================================ clic dreapta pe desen
    def context_desen(self, e):
        a = self.app; m = tk.Menu(a.root, **M_STIL); ult = getattr(a, "ultima", None)
        if ult: m.add_command(label=f"Повторить {ult}", command=lambda: a.executa(ult))
        rec = tk.Menu(m, **M_STIL)
        for c in self.recente(): rec.add_command(label=c, command=lambda c=c: a.executa(c))
        m.add_cascade(label="Последний ввод", menu=rec); m.add_separator()
        if a.v.foaie:
            m.add_command(label="Развернуть ВЭкран", command=lambda: a.schimba_foaie("Model"))
            m.add_command(label="Подрезать видовой экран", command=lambda: a.mesaj("Подрезка ВЭ: будет в следующей версии."))
            m.add_separator()
        buf = tk.Menu(m, **M_STIL)
        for t, c, k in (("Вырезать", "ВЫРЕЗАТЬ", "Ctrl+X"), ("Вырезать с базовой точкой", "ВЫРЕЗАТЬБАЗ", "Ctrl+Shift+X"), ("Копировать", "КОПБУФ", "Ctrl+C"),
                        ("Копировать с базовой точкой", "КОПБАЗ", "Ctrl+Shift+C"), ("Вставить", "ВСТАВИТЬБУФ", "Ctrl+V"), ("Вставить как блок", "ВСТАВИТЬБЛОК", "Ctrl+Shift+V"),
                        ("Вставить с исходными координатами", "ВСТАВИТЬИСХ", ""), ("Специальная вставка...", "ВСТАВИТЬБУФ", "")):
            buf.add_command(label=t, accelerator=k, command=lambda c=c: a.executa(c))
        m.add_cascade(label="Буфер обмена", menu=buf); m.add_separator()
        iz = tk.Menu(m, **M_STIL)
        for t, c in (("Изолировать объекты", "ИЗОЛИРОВАТЬ"), ("Скрыть объекты", "СКРЫТЬ"), ("Завершить изоляцию объектов", "НЕИЗОЛИРОВАТЬ")):
            iz.add_command(label=t, command=lambda c=c: a.executa(c))
        m.add_cascade(label="Изолировать", menu=iz); m.add_separator()
        if self.ed.sel:
            for t, c in (("Стереть", "СТЕРЕТЬ"), ("Переместить", "ПЕРЕНЕСТИ"), ("Копировать выбранные", "КОПИРОВАТЬ"), ("Масштаб", "МАСШТАБ"), ("Повернуть", "ПОВЕРНУТЬ")):
                m.add_command(label=t, command=lambda c=c: a.executa(c))
            po = tk.Menu(m, **M_STIL)
            for t, c in (("На передний план", "ПОРВПЕРЕД"), ("На задний план", "ПОРНАЗАД"), ("Перед объектами", "ПОРПЕРЕД"), ("За объектами", "ПОРЗА")):
                po.add_command(label=t, command=lambda c=c: a.executa(c))
            m.add_cascade(label="Порядок прорисовки", menu=po)
            gr = tk.Menu(m, **M_STIL); gr.add_command(label="Группа", command=lambda: a.executa("ГРУППА")); gr.add_command(label="Разгруппировать", command=lambda: a.executa("РАЗГРУППИРОВАТЬ"))
            m.add_cascade(label="Группа", menu=gr); m.add_separator()
            m.add_command(label="Добавить выбранные", command=self.adauga_selectat); m.add_separator()
            m.add_command(label="Выбрать подобные", command=self.selecteaza_similare); m.add_command(label="Отменить выбор", command=self.ed.goleste)
        else:
            m.add_command(label="Отменить", command=lambda: a.executa("ОТМЕНИТЬ"), accelerator="Ctrl+Z")
            m.add_command(label="Повторить", command=lambda: a.executa("ПОВТОРИТЬ"), accelerator="Ctrl+Y")
            m.add_command(label="Панорамирование", command=lambda: a.mesaj("Панорамирование: нажатое колесо мыши.")); m.add_command(label="Зумирование", command=lambda: a.executa("ПОКАЗАТЬ"))
            m.add_command(label="Штурвалы", command=lambda: a.mesaj("Штурвалы: колесо – масштаб, нажатое колесо – панорама, двойной щелчок колесом – показать все."))
            m.add_separator(); rec2 = tk.Menu(m, **M_STIL); rec2.add_command(label="Запись", command=lambda: a.mesaj("Рекордер операций: будет в следующей версии.")); rec2.add_command(label="Остановить", state="disabled")
            m.add_cascade(label="Рекордер операций", menu=rec2)
        m.add_separator()
        fs = tk.Menu(m, **M_STIL)
        for t in ("Без фильтра", "Вершина", "Кромка", "Грань", "Журнал тела", "Компонент вида чертежа"): fs.add_command(label=t, command=lambda t=t: a.mesaj(f"Фильтр подобъектов: {t}"))
        m.add_cascade(label="Фильтр выбора подобъектов", menu=fs)
        m.add_command(label="Быстрый выбор...", command=self.selectie_rapida); m.add_command(label="БыстрКальк", command=self.calculator)
        m.add_command(label="Подсчет", command=lambda: a.mesaj(f"Выбрано объектов: {len(self.ed.sel)}"), state="normal" if self.ed.sel else "disabled")
        m.add_command(label="Найти...", command=lambda: a.executa("НАЙТИ")); m.add_command(label="Свойства", command=lambda: a.executa("СВОЙСТВА"))
        m.add_command(label="Параметры...", command=self.parametri)
        m.tk_popup(e.x_root, e.y_root)

    def recente(self):
        r = []
        for c in reversed(getattr(self.app, "ist_cmd", []) + getattr(self.app, "_recente_panglica", [])):
            c = c.split()[0].upper()
            if c not in r: r.append(c)
        return r[:12] or ["(нет)"]

    def meniu_recente(self, w):
        m = tk.Menu(self.app.root, **M_STIL)
        for c in self.recente(): m.add_command(label=c, command=lambda c=c: self.app.executa(c))
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() - 22 * len(self.recente()) - 6)

    def adauga_selectat(self):
        e = self.ed.ent(next(iter(self.ed.sel)))
        cmd = {"LINE": "ОТРЕЗОК", "LWPOLYLINE": "ПЛИНИЯ", "CIRCLE": "КРУГ", "ARC": "ДУГА3Т", "TEXT": "ТЕКСТ", "MTEXT": "МТЕКСТ", "HATCH": "ШТРИХ",
               "POINT": "ТОЧКА", "SPLINE": "СПЛАЙН"}.get(e.dxftype())
        if e.dxftype() == "INSERT": return self.app.executa("ВСТАВИТЬ " + e.dxf.name)
        if e.dxftype() in ("LINE", "LWPOLYLINE", "CIRCLE", "TEXT", "MTEXT", "HATCH", "POINT", "SPLINE", "ARC"): self.app.doc.header["$CLAYER"] = e.dxf.layer
        self.ed.goleste(); self.app.executa(cmd) if cmd else self.app.mesaj("Для этого типа объекта «Добавить выбранные» не поддерживается.")

    def selecteaza_similare(self):
        tipuri = {(self.ed.ent(h).dxftype(), self.ed.ent(h).dxf.get("layer", "0"), self.ed.ent(h).dxf.get("name", "") if self.ed.ent(h).dxftype() == "INSERT" else "")
                  for h in self.ed.sel if self.ed.ent(h) is not None}
        self.ed.sel = {e.dxf.handle for e in self.doc.modelspace()
                       if (e.dxftype(), e.dxf.get("layer", "0"), e.dxf.get("name", "") if e.dxftype() == "INSERT" else "") in tipuri and not self.ed.blocat(e)}
        self.ed.arata_selectia(); self.app.dupa_selectie(); self.app.mesaj(f"Выбрано подобных: {len(self.ed.sel)}")

    def selectie_rapida(self):
        if not self.doc: return
        d = dialog(self.app, "Быстрый выбор"); msp = self.doc.modelspace()
        tipuri = sorted({e.dxftype() for e in msp}); straturi = sorted(l.dxf.name for l in self.doc.layers)
        eticheta(d, "Тип объектов:", 0, 0); ct = ttk.Combobox(d, values=["Все"] + tipuri, state="readonly", width=24); ct.set("Все"); ct.grid(row=0, column=1, padx=6)
        eticheta(d, "Слой:", 1, 0); cs = ttk.Combobox(d, values=["Все"] + straturi, state="readonly", width=24); cs.set("Все"); cs.grid(row=1, column=1, padx=6)
        eticheta(d, "Имя блока / текст содержит:", 2, 0); et = intrare(d, "", 2, 1, 26)
        v_add = tk.BooleanVar(value=False)
        tk.Checkbutton(d, text="Добавить к текущему набору", variable=v_add, bg=CORP, fg=TEXT, selectcolor="#2b313a", activebackground=CORP, font=F_MIC).grid(row=3, column=0, columnspan=2, sticky="w", padx=4)
        def ok():
            t, s, q = ct.get(), cs.get(), et.get().strip().lower(); rez = set()
            for e in msp:
                if t != "Все" and e.dxftype() != t: continue
                if s != "Все" and e.dxf.get("layer", "0") != s: continue
                if q:
                    txt = (e.dxf.get("name", "") if e.dxftype() == "INSERT" else e.plain_text() if e.dxftype() == "MTEXT" else e.dxf.get("text", "")) or ""
                    if q not in txt.lower(): continue
                if not self.ed.blocat(e): rez.add(e.dxf.handle)
            self.ed.sel = (self.ed.sel | rez) if v_add.get() else rez; d.destroy(); self.ed.arata_selectia(); self.app.dupa_selectie()
            self.app.mesaj(f"Быстрый выбор: {len(rez)} объектов.")
        buton(d, "OK", ok, bg=ALBASTRU).grid(row=4, column=1, sticky="e", padx=6, pady=8)

    def calculator(self):
        import math as _m
        v = simpledialog.askstring("БыстрКальк", "Выражение (например 2*pi*5 или sqrt(3**2+4**2)):", parent=self.app.root)
        if not v: return
        try: r = calc_sigur(v)
        except Exception as ex: return messagebox.showerror("БыстрКальк", f"Ошибка: {ex}")
        self.app.root.clipboard_clear(); self.app.root.clipboard_append(str(r)); self.app.mesaj(f"БыстрКальк: {v} = {r}  (скопировано в буфер)")

    # ================================================================ clic dreapta pe tab-ul fișierului și pe „+”
    def context_fisier(self, e):
        a = self.app; m = tk.Menu(a.root, **M_STIL)
        for t, c in (("Создать...", a.nou), ("Открыть...", a.deschide), ("Сохранить", a.salveaza), ("Сохранить как...", a.salveaza_ca), ("Сохранить все", a.salveaza)):
            m.add_command(label=t, command=c)
        m.add_separator(); m.add_command(label="Закрыть", command=a.inchide); m.add_command(label="Закрыть все", command=a.inchide)
        m.add_command(label="Закрыть все другие чертежи", command=lambda: a.mesaj("Открыт один чертеж – закрывать нечего."))
        m.add_separator(); m.add_command(label="Копировать полный путь к файлу", command=self.copiaza_cale, state="normal" if a.cale else "disabled")
        m.add_command(label="Открыть папку файла", command=self.deschide_dosar, state="normal" if a.cale else "disabled")
        m.tk_popup(e.x_root, e.y_root)

    def context_plus(self, e):
        a = self.app; m = tk.Menu(a.root, **M_STIL)
        for t, c in (("Создать...", a.nou), ("Открыть...", a.deschide), ("Сохранить все", a.salveaza)): m.add_command(label=t, command=c)
        m.add_separator(); m.add_command(label="Закрыть все", command=a.inchide); m.tk_popup(e.x_root, e.y_root)

    def copiaza_cale(self):
        self.app.root.clipboard_clear(); self.app.root.clipboard_append(os.path.abspath(self.app.cale)); self.app.mesaj("Путь скопирован: " + os.path.abspath(self.app.cale))

    def deschide_dosar(self):
        p = os.path.abspath(self.app.cale)
        try:
            if os.name == "nt": subprocess.Popen(["explorer", "/select,", p])
            else: subprocess.Popen(["xdg-open", os.path.dirname(p)])
        except Exception as ex: self.app.mesaj(f"Не удалось открыть папку: {ex}")

    # ================================================================ clic dreapta pe tab-urile foilor
    def context_foi(self, e, nume=None):
        a = self.app; m = tk.Menu(a.root, **M_STIL)
        m.add_command(label="Новый лист", command=a.foaie_noua); m.add_command(label="Из шаблона...", command=self.foaie_din_sablon)
        if nume and nume != "Model":
            m.add_separator(); m.add_command(label="Удалить", command=lambda: self.sterge_foaie(nume)); m.add_command(label="Переименовать", command=lambda: self.redenumeste_foaie(nume))
            m.add_command(label="Перенести/копировать...", command=lambda: self.copiaza_foaie(nume))
        m.add_command(label="Выбрать все листы", command=lambda: a.mesaj("Выбраны все листы (для публикации – «Экспорт: Все листы»)."))
        m.add_separator(); m.add_command(label="Активировать вкладку «Модель»", command=lambda: a.schimba_foaie("Model"))
        m.add_command(label="Диспетчер параметров листов...", command=a.c_print); m.add_command(label="Печать...", command=a.c_print)
        m.add_separator(); m.add_command(label="Настройка стандарта оформления...", command=lambda: a.mesaj("Стандарт оформления: формат A3, поля 10 мм (задаются в «Печать»)."))
        m.tk_popup(e.x_root, e.y_root)

    def sterge_foaie(self, n):
        if not messagebox.askyesno("Удалить лист", f"Удалить лист «{n}»?"): return
        try: self.doc.layouts.delete(n)
        except Exception as ex: return messagebox.showerror("Лист", str(ex))
        self.app.marcheaza(); self.app.schimba_foaie("Model")

    def redenumeste_foaie(self, n):
        nou = simpledialog.askstring("Переименовать лист", "Новое имя:", initialvalue=n, parent=self.app.root)
        if not nou or nou == n: return
        try: self.doc.layouts.rename(n, nou)
        except Exception as ex: return messagebox.showerror("Лист", str(ex))
        self.app.marcheaza(); self.app.schimba_foaie(nou)

    def copiaza_foaie(self, n):
        nou = simpledialog.askstring("Копировать лист", "Имя копии:", initialvalue=n + " (2)", parent=self.app.root)
        if not nou: return
        try:
            src = self.doc.layouts.get(n); dst = self.doc.layouts.new(nou); dl = src.dxf_layout.dxf
            dst.page_setup(size=(dl.get("paper_width", 420), dl.get("paper_height", 297)), margins=(10, 10, 10, 10), units="mm")
            for e in src:
                if e.dxftype() == "VIEWPORT" and e.dxf.get("id", 2) == 1: continue
                dst.add_entity(e.copy())
        except Exception as ex: return messagebox.showerror("Лист", str(ex))
        self.app.marcheaza(); self.app.schimba_foaie(nou)

    def foaie_din_sablon(self):
        p = filedialog.askopenfilename(title="Лист из шаблона", filetypes=[("Чертеж / шаблон", "*.dwg *.dxf *.dwt"), ("Все файлы", "*.*")])
        if not p: return
        import fisiere
        try: src = fisiere.deschide(p)
        except Exception as ex: return messagebox.showerror("Шаблон", str(ex))
        nume = [l.name for l in src.layouts if l.name != "Model"]
        if not nume: return self.app.mesaj("В шаблоне нет листов.")
        n = nume[0]; nou = n
        while nou in [l.name for l in self.doc.layouts]: nou += "_1"
        dl = src.layouts.get(n).dxf_layout.dxf; dst = self.doc.layouts.new(nou)
        dst.page_setup(size=(dl.get("paper_width", 420), dl.get("paper_height", 297)), margins=(10, 10, 10, 10), units="mm")
        from ezdxf.addons import Importer
        imp = Importer(src, self.doc); imp.import_entities([e for e in src.layouts.get(n) if not (e.dxftype() == "VIEWPORT" and e.dxf.get("id", 2) == 1)], dst); imp.finalize()
        self.app.marcheaza(); self.app.schimba_foaie(nou); self.app.mesaj(f"Лист «{nou}» создан из шаблона {os.path.basename(p)}.")

    # ================================================================ clic dreapta pe panglică
    def context_panglica(self, e):
        a = self.app; pg = a.pg; m = tk.Menu(a.root, **M_STIL)
        m.add_command(label="Показать связанную группу инструментальных палитр", state="disabled")
        gp = tk.Menu(m, **M_STIL); gp.add_command(label="Все палитры", command=self.adaptare); m.add_cascade(label="Группа инструментальных палитр", menu=gp); m.add_separator()
        tb = tk.Menu(m, **M_STIL)
        for n in pg.file:
            v = tk.BooleanVar(value=pg.file[n].winfo_ismapped() or n not in pg.ascunse); pg._vars = getattr(pg, "_vars", {}); pg._vars["f" + n] = v
            tb.add_checkbutton(label=n, variable=v, command=lambda n=n, v=v: pg.arata_fila(n, v.get()))
        m.add_cascade(label="Показать вкладки", menu=tb)
        pn = tk.Menu(m, **M_STIL)
        for titlu, fr in pg.grupuri.get(pg.activ, []):
            v = tk.BooleanVar(value=fr.winfo_ismapped()); pg._vars["g" + titlu] = v
            pn.add_checkbutton(label=titlu, variable=v, command=lambda fr=fr, v=v: pg.arata_grup(fr, v.get()))
        m.add_cascade(label="Показать панели", menu=pn)
        v = tk.BooleanVar(value=pg.titluri); pg._vars["titluri"] = v
        m.add_checkbutton(label="Показать заголовки панелей", variable=v, command=lambda: pg.arata_titluri(v.get()))
        m.add_separator(); m.add_command(label="Освободить", state="disabled"); m.add_command(label="Закрыть", command=pg.comuta)
        m.tk_popup(e.x_root, e.y_root)

    # ================================================================ importuri
    def import_pdf(self):
        if not self.doc: return self.app.mesaj("Нет открытого чертежа.")
        p = filedialog.askopenfilename(title="Импорт PDF", filetypes=[("PDF", "*.pdf")])
        if not p: return
        import fitz
        try: pdf = fitz.open(p)
        except Exception as ex: return messagebox.showerror("Импорт PDF", str(ex))
        d = dialog(self.app, "Импорт PDF – " + os.path.basename(p))
        eticheta(d, f"Страница (1–{pdf.page_count}):", 0, 0); ep = intrare(d, 1, 0, 1)
        eticheta(d, "Масштаб (1 = мм бумаги):", 1, 0); es = intrare(d, 1, 1, 1)
        eticheta(d, "Точка вставки X:", 2, 0); ex_ = intrare(d, 0, 2, 1); eticheta(d, "Y:", 3, 0); ey = intrare(d, 0, 3, 1)
        v_txt = tk.BooleanVar(value=True); v_fill = tk.BooleanVar(value=True)
        for i, (t, v) in enumerate((("Импорт текста (TrueType)", v_txt), ("Импорт заливок (штриховка SOLID)", v_fill))):
            tk.Checkbutton(d, text=t, variable=v, bg=CORP, fg=TEXT, selectcolor="#2b313a", activebackground=CORP, font=F_MIC).grid(row=4 + i, column=0, columnspan=2, sticky="w", padx=4)
        def ok():
            try: nr = int(numar(ep, 1)) - 1; pg = pdf[max(0, min(pdf.page_count - 1, nr))]
            except Exception as ex: return messagebox.showerror("PDF", str(ex), parent=d)
            k = numar(es, 1) * 25.4 / 72; x0, y0 = numar(ex_, 0), numar(ey, 0); d.destroy(); self._pdf_pagina(pg, k, x0, y0, v_txt.get(), v_fill.get(), os.path.basename(p))
        buton(d, "OK", ok, bg=ALBASTRU).grid(row=6, column=1, sticky="e", padx=6, pady=8)

    def _pdf_pagina(self, pg, k, x0, y0, texte, umpleri, nume):
        from ezdxf import colors as ezc
        H = pg.rect.height; msp = self.doc.modelspace(); self.ed.instantaneu([])
        strat = "PDF_" + os.path.splitext(nume)[0][:40]
        for ch in '<>/\\":;?*|=`': strat = strat.replace(ch, "_")
        if strat not in self.doc.layers: self.doc.layers.add(strat, color=7)
        T = lambda q: (x0 + q.x * k, y0 + (H - q.y) * k); n = 0; m = 0
        for dr in pg.get_drawings():
            rgb = dr.get("color") or dr.get("fill") or (0, 0, 0); tc = ezc.rgb2int(tuple(int(c * 255) for c in rgb))
            at = {"layer": strat, "true_color": tc}; cur = []
            def gol():
                nonlocal cur, n
                if len(cur) >= 2:
                    inchis = len(cur) > 3 and abs(cur[0][0] - cur[-1][0]) < 1e-6 and abs(cur[0][1] - cur[-1][1]) < 1e-6
                    msp.add_lwpolyline(cur[:-1] if inchis else cur, close=inchis, dxfattribs=at); n += 1
                    if umpleri and inchis and dr.get("fill") and len(cur) >= 4:
                        h = msp.add_hatch(dxfattribs={"layer": strat}); h.set_solid_fill(); h.dxf.true_color = ezc.rgb2int(tuple(int(c * 255) for c in dr["fill"]))
                        h.paths.add_polyline_path(cur, is_closed=True)
                cur = []
            for it in dr["items"]:
                op = it[0]
                if op == "l": a, b = T(it[1]), T(it[2]); pts = [a, b]
                elif op == "c":
                    p0, c1, c2, p3 = it[1:5]; pts = []
                    for i in range(9):
                        t = i / 8; u = 1 - t
                        q = (u ** 3 * p0.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t ** 3 * p3.x, u ** 3 * p0.y + 3 * u * u * t * c1.y + 3 * u * t * t * c2.y + t ** 3 * p3.y)
                        pts.append((x0 + q[0] * k, y0 + (H - q[1]) * k))
                elif op == "re":
                    r = it[1]; gol(); cur = [T(r.tl), T(r.tr), T(r.br), T(r.bl), T(r.tl)]; gol(); continue
                elif op == "qu":
                    q = it[1]; gol(); cur = [T(q.ul), T(q.ur), T(q.lr), T(q.ll), T(q.ul)]; gol(); continue
                else: continue
                if cur and (abs(cur[-1][0] - pts[0][0]) > 1e-6 or abs(cur[-1][1] - pts[0][1]) > 1e-6): gol()
                cur.extend(pts if not cur else pts[1:])
            gol()
        if texte:
            for b in pg.get_text("dict")["blocks"]:
                for l in b.get("lines", []):
                    for s in l.get("spans", []):
                        t = s.get("text", "").strip()
                        if not t: continue
                        o = s["origin"]; msp.add_text(t, height=max(0.1, s["size"] * k * 0.72), dxfattribs={"layer": strat}).set_placement((x0 + o[0] * k, y0 + (H - o[1]) * k)); m += 1
        self.ed.gata_modificare(); self.app.marcheaza(); self.app.v.zoom_extinde()
        self.app.mesaj(f"Импорт PDF: {n} полилиний, {m} текстов на слой «{strat}».")

    def import_dgn(self):
        messagebox.showinfo("Импорт DGN", "Формат MicroStation DGN нельзя прочитать без коммерческой библиотеки.\n\n"
                            "Сохраните файл в MicroStation (или в бесплатном Bentley View) как DWG/DXF и откройте его, "
                            "либо используйте «Импорт» → DWG/DXF.", parent=self.app.root)

    def import_desen(self):
        """IMPORT: obiectele din alt DWG/DXF intră în desenul curent (cu straturi, blocuri, stiluri)"""
        if not self.doc: return self.app.mesaj("Нет открытого чертежа.")
        p = filedialog.askopenfilename(title="Импорт чертежа", filetypes=[("Чертеж", "*.dwg *.dxf"), ("Все файлы", "*.*")])
        if not p: return
        import fisiere
        from ezdxf.addons import Importer
        try: src = fisiere.deschide(p)
        except Exception as ex: return messagebox.showerror("Импорт", str(ex))
        self.ed.instantaneu([]); imp = Importer(src, self.doc); imp.import_modelspace(); imp.finalize()
        self.ed.gata_modificare(); self.app._actualizeaza_straturi(); self.app.marcheaza(); self.app.v.zoom_extinde()
        self.app.mesaj(f"Импортирован {os.path.basename(p)}: {sum(1 for _ in src.modelspace())} объектов.")

    # ================================================================ blocuri
    def bloc_inserat(self, nume):
        if nume in self.blocuri_recente: self.blocuri_recente.remove(nume)
        self.blocuri_recente.insert(0, nume); self._salv()

    def meniu_blocuri(self, tip):
        a = self.app
        if tip == "lib": return a.sim.importa_biblioteca() if hasattr(a.sim, "importa_biblioteca") else a.executa("ВСТАВИТЬ")
        lst = self.blocuri_recente if tip == "rec" else self.blocuri_pref
        if not a.doc: return
        d = dialog(a, "Последние блоки" if tip == "rec" else "Избранные блоки")
        lb = tk.Listbox(d, bg="#2b313a", fg=TEXT, selectbackground=ACTIV, width=36, height=12); lb.pack(padx=8, pady=8)
        for n in lst:
            if n in a.doc.blocks: lb.insert("end", n)
        def ins():
            if lb.curselection(): n = lb.get(lb.curselection()[0]); d.destroy(); a.executa("ВСТАВИТЬ " + n)
        def pref():
            n = simpledialog.askstring("Избранные блоки", "Имя блока добавить в избранные:", parent=d)
            if n and n in a.doc.blocks and n not in self.blocuri_pref: self.blocuri_pref.append(n); self._salv(); lb.insert("end", n)
        def scoate():
            if lb.curselection():
                n = lb.get(lb.curselection()[0])
                if n in lst: lst.remove(n); self._salv()
                lb.delete(lb.curselection()[0])
        f = tk.Frame(d, bg=CORP); f.pack(fill="x", padx=8, pady=6)
        buton(f, "Вставить", ins, bg=ALBASTRU).pack(side="left", padx=2)
        if tip == "pref": buton(f, "Добавить...", pref).pack(side="left", padx=2)
        buton(f, "Убрать", scoate).pack(side="left", padx=2); lb.bind("<Double-Button-1>", lambda e: ins())
        if not lb.size(): lb.insert("end", "(пусто)")

    def wblock(self):
        """Запись блока на диск: un bloc, obiectele selectate sau tot desenul → DWG/DXF separat"""
        if not self.doc: return
        import ezdxf, fisiere
        from ezdxf.addons import Importer
        d = dialog(self.app, "Запись блока на диск"); sursa = tk.StringVar(value="obiecte" if self.ed.sel else "bloc")
        blocuri = sorted(b.name for b in self.doc.blocks if not b.name.startswith("*") and not b.is_any_layout)
        tk.Label(d, text="Источник", bg=CORP, fg=TEXT, font=(F, -12, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        for i, (t, v) in enumerate((("Блок:", "bloc"), ("Весь чертеж", "tot"), ("Объекты (выбранные: %d)" % len(self.ed.sel), "obiecte"))):
            tk.Radiobutton(d, text=t, value=v, variable=sursa, bg=CORP, fg=TEXT, selectcolor="#2b313a", activebackground=CORP, font=F_MIC).grid(row=1 + i, column=0, sticky="w", padx=12)
        cb = ttk.Combobox(d, values=blocuri, state="readonly", width=24); cb.grid(row=1, column=1, padx=6)
        if blocuri: cb.set(blocuri[0])
        eticheta(d, "Базовая точка X:", 4, 0); ebx = intrare(d, 0, 4, 1); eticheta(d, "Y:", 5, 0); eby = intrare(d, 0, 5, 1)
        eticheta(d, "Файл:", 6, 0); ef = intrare(d, os.path.join(os.path.dirname(self.app.cale or os.path.expanduser("~")), "новый блок.dwg"), 6, 1, 40)
        def alege():
            p = filedialog.asksaveasfilename(title="Имя файла", defaultextension=".dwg", filetypes=[("Чертеж DWG", "*.dwg"), ("DXF", "*.dxf")], parent=d)
            if p: ef.delete(0, "end"); ef.insert(0, p)
        buton(d, "...", alege, padx=6).grid(row=6, column=2, padx=4)
        def ok():
            nou = ezdxf.new(self.doc.dxfversion); imp = Importer(self.doc, nou); s = sursa.get(); bx, by = numar(ebx, 0), numar(eby, 0)
            from ezdxf.math import Matrix44
            if s == "bloc":
                if not cb.get(): return
                imp.import_block(cb.get()); imp.finalize(); blk = nou.blocks.get(cb.get())
                bp = blk.block.dxf.base_point
                for e in list(blk): c = e.copy(); nou.modelspace().add_entity(c); c.transform(Matrix44.translate(-bp.x, -bp.y, 0))
            elif s == "obiecte":
                if not self.ed.sel: return messagebox.showinfo("Запись блока", "Нет выбранных объектов.", parent=d)
                imp.import_entities([self.ed.ent(h) for h in self.ed.sel if self.ed.ent(h) is not None], nou.modelspace()); imp.finalize()
                for e in nou.modelspace(): e.transform(Matrix44.translate(-bx, -by, 0))
            else: imp.import_modelspace(); imp.finalize()
            cale = ef.get().strip(); d.destroy()
            try: fisiere.salveaza(nou, cale, "AutoCAD 2018")
            except Exception as ex: return messagebox.showerror("Запись блока", str(ex))
            self.app.mesaj(f"Записано на диск: {cale} ({sum(1 for _ in nou.modelspace())} объектов).")
        buton(d, "OK", ok, bg=ALBASTRU).grid(row=7, column=1, sticky="e", padx=6, pady=8)

    def atribute_multiple(self):
        def cb(p):
            sx, sy = self.app.v.ecran(*p); h = self.ed.la_entitate(sx, sy); e = self.ed.ent(h) if h else None
            if e is None or e.dxftype() != "INSERT" or not e.attribs: return self.app.mesaj("Выберите блок с атрибутами.")
            self.app.et.dialog_atribute(e)
        self.ed.incepe("REPETAT", "АТРРЕД (несколько)  Выберите блок (Esc – конец):", nevoie_sel=False, rep="Выберите блок (Esc – конец):", cb=cb)

    def afisare_atribute(self, mod):
        """ATTDISP: Сохранить (normal) / Показать все / Скрыть все"""
        if not self.doc: return
        self.app.v.atribute = mod; self.doc.header["$ATTMODE"] = {"normal": 1, "toate": 2, "niciunul": 0}[mod]
        self.app.v.reconstruieste(); self.app.v.deseneaza()
        self.app.mesaj({"normal": "Отображение атрибутов: как задано.", "toate": "Показаны все атрибуты (и скрытые).", "niciunul": "Все атрибуты скрыты."}[mod])

    def sincronizare(self):
        """ATTSYNC: atributele blocurilor refăcute după definiția blocului (valorile se păstrează)"""
        if not self.doc: return
        nume = {self.ed.ent(h).dxf.name for h in self.ed.sel if self.ed.ent(h) is not None and self.ed.ent(h).dxftype() == "INSERT"}
        if not nume:
            n = simpledialog.askstring("Синхронизация", "Имя блока (пусто = все блоки):", parent=self.app.root)
            if n is None: return
            nume = {n} if n else {b.name for b in self.doc.blocks}
        ins = [e for e in self.doc.modelspace().query("INSERT") if e.dxf.name in nume]
        self.ed.instantaneu([e.dxf.handle for e in ins]); k = 0
        for e in ins:
            vechi = {a.dxf.tag: a.dxf.text for a in e.attribs}
            for a in list(e.attribs): e.delete_attrib(a.dxf.tag)
            try: e.add_auto_attribs(vechi); k += 1
            except Exception: pass
        self.ed.gata_modificare(f"Синхронизировано блоков: {k}."); self.app.marcheaza()

    def punct_baza(self):
        def cb(p):
            self.doc.header["$INSBASE"] = (p[0], p[1], 0); self.app.marcheaza(); self.app.mesaj(f"Базовая точка чертежа: {p[0]:.3f}, {p[1]:.3f}")
        self.ed.incepe("PUNCT", "БАЗА  Базовая точка вставки чертежа:", nevoie_sel=False, cb=cb)

    # ================================================================ export foi
    def export_pdf(self, tip=None):
        a = self.app; pg = a.pg.combo
        if not a.doc: return
        if (pg.get("параметрылиста") and "Переопределить" in pg["параметрылиста"].get()): return a.c_pdf()
        toate = tip == "toate" or (pg.get("экспорт") and "Все" in pg["экспорт"].get())
        import tiparire, fitz
        foi = [l.name for l in a.doc.layouts if l.name != "Model"] if toate else [getattr(a, "foaie_act", "Model")]
        if toate and not foi: foi = ["Model"]
        baza = os.path.splitext(os.path.basename(a.cale or "Чертеж1"))[0] + ("" if toate else "-" + foi[0])
        p = filedialog.asksaveasfilename(title="Экспорт в PDF", initialfile=baza + ".pdf", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not p: return
        a.root.config(cursor="watch"); a.root.update_idletasks(); rez = fitz.open()
        try:
            for f in foi:
                fmt = "A3"
                if f != "Model":
                    w, h = tiparire.dimensiune_foaie(a.doc, f); fmt = min(tiparire.FORMATE, key=lambda k: abs(max(tiparire.FORMATE[k]) - max(w, h)))
                rez.insert_pdf(fitz.open("pdf", tiparire.pdf(a.doc, f, fmt)))
            rez.save(p)
        except Exception as ex: messagebox.showerror("Экспорт PDF", str(ex))
        else: a.mesaj(f"PDF: {len(foi)} лист(ов) → {p}")
        finally: a.root.config(cursor="")

    def export_dwf(self, fmt):
        messagebox.showinfo("Экспорт " + fmt, f"Формат {fmt} – закрытый формат Autodesk, без их библиотеки его не создать.\n\nИспользуйте PDF – он открывается везде.", parent=self.app.root)

    # ================================================================ Параметры (Options)
    def parametri(self):
        a = self.app; s = setari(); d = dialog(a, "Параметры", "620x440")
        tk.Label(d, text=f"Текущий профиль: <<Профиль без имени>>        Текущий чертеж: {os.path.basename(a.cale or 'Чертеж1.dwg')}", bg=CORP, fg=TEXT, font=F_MIC).pack(anchor="w", padx=8, pady=4)
        nb = ttk.Notebook(d); nb.pack(fill="both", expand=True, padx=8)
        val = {}
        def fila(t):
            f = tk.Frame(nb, bg=CORP); nb.add(f, text=t); return f
        f = fila("Файлы")
        tk.Label(f, text="Пути доступа, имена файлов и папки:", bg=CORP, fg=TEXT, font=F_MIC).pack(anchor="w", padx=6, pady=4)
        tv = ttk.Treeview(f, show="tree", height=10); tv.pack(fill="both", expand=True, padx=6)
        import fisiere
        for t, v in (("Путь поиска вспомогательных файлов", os.path.dirname(os.path.abspath(sys.argv[0]))), ("Папка для файла автосохранения", s.get("autosalv_dir", os.path.join(os.environ.get("TEMP", "/tmp")))),
                     ("Конвертер DWG (ODA File Converter)", fisiere.oda_exe() or "не найден – https://www.opendesign.com/guestfiles/oda_file_converter"),
                     ("Расположение изображений, импортируемых из PDF", os.path.expanduser("~")), ("Кэш карт Esri", os.path.join(os.environ.get("APPDATA") or "~", "CAD_PC", "harti"))):
            i = tv.insert("", "end", text="📁 " + t); tv.insert(i, "end", text=v)
        f = fila("Экран")
        eticheta(f, "Цвет фона модели:", 0, 0); val["fundal"] = intrare(f, s.get("fundal", "#212830"), 0, 1)
        eticheta(f, "Размер перекрестья (%):", 1, 0); val["cursor"] = intrare(f, s.get("cursor", 5), 1, 1)
        eticheta(f, "Затенение блокированных слоев (%):", 2, 0); val["estompare"] = intrare(f, s.get("estompare", 50), 2, 1)
        f = fila("Открытие/Сохранение")
        eticheta(f, "Сохранять как (формат по умолчанию):", 0, 0); cv = ttk.Combobox(f, values=list(fisiere.VERSIUNI) if hasattr(fisiere, "VERSIUNI") else ["AutoCAD 2018"], state="readonly", width=24)
        cv.set(s.get("versiune", "AutoCAD 2018")); cv.grid(row=0, column=1, padx=6); val["versiune"] = cv
        eticheta(f, "Автосохранение каждые (мин, 0 = выкл):", 1, 0); val["autosalv"] = intrare(f, s.get("autosalv", 10), 1, 1)
        v_bak = tk.BooleanVar(value=s.get("bak", True)); val["bak"] = v_bak
        tk.Checkbutton(f, text="Создавать резервную копию (.bak) при сохранении", variable=v_bak, bg=CORP, fg=TEXT, selectcolor="#2b313a", activebackground=CORP, font=F_MIC).grid(row=2, column=0, columnspan=2, sticky="w", padx=4)
        f = fila("Печать/Публикация")
        eticheta(f, "Формат по умолчанию:", 0, 0); cf = ttk.Combobox(f, values=["A0", "A1", "A2", "A3", "A4", "A5"], state="readonly", width=8); cf.set(s.get("format", "A3")); cf.grid(row=0, column=1); val["format"] = cf
        f = fila("Система")
        tk.Label(f, text="Процесс работает с пониженным приоритетом и оставляет 2 ядра процессора свободными.\nБольшие чертежи готовятся в фоне.",
                 bg=CORP, fg=TEXT, font=F_MIC, justify="left").pack(anchor="w", padx=6, pady=6)
        f = fila("Пользовательские")
        v_dr = tk.BooleanVar(value=s.get("meniu_dreapta", True)); val["meniu_dreapta"] = v_dr
        tk.Checkbutton(f, text="Контекстные меню в области рисования (правая кнопка)", variable=v_dr, bg=CORP, fg=TEXT, selectcolor="#2b313a", activebackground=CORP, font=F_MIC).pack(anchor="w", padx=6, pady=6)
        f = fila("Построения")
        eticheta(f, "Размер маркера привязки (пикс.):", 0, 0); val["marcaj"] = intrare(f, s.get("marcaj", 6), 0, 1)
        f = fila("Выбор")
        eticheta(f, "Размер прицела (пикс.):", 0, 0); val["pick"] = intrare(f, s.get("pick", 5), 0, 1)
        eticheta(f, "Размер ручек (пикс.):", 1, 0); val["grip"] = intrare(f, s.get("grip", 5), 1, 1)
        def aplica():
            for k, w in val.items(): s[k] = w.get() if not isinstance(w, tk.Entry) else (w.get() if k == "fundal" else numar(w, 0))
            salveaza_setari(s); a.aplica_setari(s)
        def ok(): aplica(); d.destroy()
        fj = tk.Frame(d, bg=CORP); fj.pack(fill="x", padx=8, pady=8)
        for t, c in (("Справка", lambda: a.executa("СПРАВКА")), ("Применить", aplica), ("Отмена", d.destroy), ("OK", ok)):
            buton(fj, t, c, bg=ALBASTRU if t == "OK" else FILE).pack(side="right", padx=2)

    # ================================================================ Адаптация, псевдонимы
    def adaptare(self):
        d = dialog(self.app, "Адаптация"); nb = ttk.Notebook(d); nb.pack(fill="both", expand=True, padx=8, pady=8)
        f = tk.Frame(nb, bg=CORP); nb.add(f, text="Палитры инструментов - все палитры")
        st = tk.Listbox(f, bg="white", fg="#111", width=34, height=14); st.grid(row=1, column=0, padx=6, pady=4)
        dr = ttk.Treeview(f, show="tree", height=14); dr.grid(row=1, column=1, padx=6, pady=4)
        tk.Label(f, text="Палитры:", bg=CORP, fg=TEXT, font=F_MIC).grid(row=0, column=0, sticky="w"); tk.Label(f, text="Группы палитр:", bg=CORP, fg=TEXT, font=F_MIC).grid(row=0, column=1, sticky="w")
        for n in ("Аннотация", "Блоки (символы чертежа)", "Штриховка и заливка", "Таблицы", "Выноски", "Чертить", "Редактировать", "Слои"): st.insert("end", n)
        for g, sub in (("Аннотация", ["Выноски", "Таблицы"]), ("Чертеж", ["Чертить", "Редактировать", "Штриховка и заливка"]), ("Блоки", ["Блоки (символы чертежа)"])):
            i = dr.insert("", "end", text=g, open=True)
            for x in sub: dr.insert(i, "end", text=x)
        tk.Label(f, text="Текущая группа палитр:   Все палитры", bg=CORP, fg=TEXT, font=F_MIC).grid(row=2, column=0, sticky="w", padx=6)
        buton(d, "Закрыть", d.destroy).pack(side="right", padx=8, pady=8)

    def pseudonime(self, fila=0):
        a = self.app; d = dialog(a, "Редактировать псевдонимы", "560x420"); nb = ttk.Notebook(d); nb.pack(fill="both", expand=True, padx=8, pady=8)
        f = tk.Frame(nb, bg=CORP); nb.add(f, text="Псевдонимы команд")
        tv = ttk.Treeview(f, columns=("a", "c"), show="headings", height=14); tv.heading("a", text="Псевдоним"); tv.heading("c", text="Команда")
        tv.pack(fill="both", expand=True, padx=6, pady=4)
        import cad
        def umple():
            tv.delete(*tv.get_children())
            for k, v in sorted(self.aliasuri.items()): tv.insert("", "end", values=(k, v), tags=("u",))
            for k, v in sorted(cad.COMENZI.items()): tv.insert("", "end", values=(k, v))
        def adauga():
            k = simpledialog.askstring("Псевдоним", "Псевдоним (например ЛИН):", parent=d)
            if not k: return
            c = simpledialog.askstring("Псевдоним", "Команда (например ОТРЕЗОК):", parent=d)
            if c and c.upper() in cad.COMENZI: self.aliasuri[k.upper()] = c.upper(); self._salv(); umple()
            elif c: messagebox.showerror("Псевдоним", f"Команда «{c}» неизвестна.", parent=d)
        def sterge():
            for i in tv.selection():
                k = tv.item(i, "values")[0]
                if k in self.aliasuri: del self.aliasuri[k]
            self._salv(); umple()
        for t in ("Список автоисправления", "Список синонимов"):
            g = tk.Frame(nb, bg=CORP); nb.add(g, text=t)
            tk.Label(g, text="Ошибочный ввод исправляется по псевдонимам; синонимы – это псевдонимы пользователя\n(вкладка «Псевдонимы команд»).", bg=CORP, fg=TEXT, font=F_MIC, justify="left").pack(padx=8, pady=8, anchor="w")
        nb.select(fila); fb = tk.Frame(d, bg=CORP); fb.pack(fill="x", padx=8, pady=6)
        for t, c in (("Добавить...", adauga), ("Удалить", sterge), ("Закрыть", d.destroy)): buton(fb, t, c).pack(side="left", padx=2)
        umple()
