"""Etapa 3 – tipărirea și PDF: desenul (Модель sau o foaie Layout) randat cu ezdxf + PyMuPDF pe formatele A1–A5,
fundal alb, color sau alb-negru. Tipărirea: imaginea paginii trimisă la imprimantă (Windows, GDI)."""
import io, os, sys, tempfile
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from stil import *

FORMATE = {"A0": (1189, 841), "A1": (841, 594), "A2": (594, 420), "A3": (420, 297), "A4": (297, 210), "A5": (210, 148)}
IMPLICIT = "A3"
PDF = "Сохранить в PDF"


def _randeaza(doc, foaie, monocrom):
    from ezdxf.addons.drawing import RenderContext, Frontend, pymupdf, config
    lay = doc.modelspace() if foaie in (None, "Model") else doc.layouts.get(foaie)
    ctx = RenderContext(doc); be = pymupdf.PyMuPdfBackend()
    cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE,
                               color_policy=config.ColorPolicy.BLACK if monocrom else config.ColorPolicy.COLOR)
    Frontend(ctx, be, config=cfg).draw_layout(lay, finalize=True)
    return be


def _pagina(fmt, orientare, margini):
    from ezdxf.addons.drawing import layout as dl
    w, h = FORMATE.get(fmt, FORMATE[IMPLICIT])
    if orientare == "Книжная": w, h = h, w
    return dl.Page(w, h, dl.Units.mm, margins=dl.Margins.all(margini))


def pdf(doc, foaie="Model", fmt=IMPLICIT, orientare="Альбомная", monocrom=False, margini=10):
    from ezdxf.addons.drawing import layout as dl
    be = _randeaza(doc, foaie, monocrom)
    return be.get_pdf_bytes(_pagina(fmt, orientare, margini), settings=dl.Settings(fit_page=True))


def png(doc, foaie="Model", fmt=IMPLICIT, orientare="Альбомная", monocrom=False, margini=10, dpi=96):
    dpi = int(dpi)
    from ezdxf.addons.drawing import layout as dl
    be = _randeaza(doc, foaie, monocrom)
    return be.get_pixmap_bytes(_pagina(fmt, orientare, margini), fmt="png", settings=dl.Settings(fit_page=True), dpi=dpi)


def dimensiune_foaie(doc, foaie):
    """hârtia foii Layout în mm (A3 dacă nu e setată)"""
    try:
        dl = doc.layouts.get(foaie).dxf_layout.dxf
        w, h = dl.get("paper_width", 0), dl.get("paper_height", 0)
        if dl.get("plot_rotation", 0) in (1, 3): w, h = h, w
        if w > 1 and h > 1: return w, h
    except Exception: pass
    return FORMATE[IMPLICIT]


def png_foaie(doc, foaie, dpi):
    dpi = int(dpi)
    from ezdxf.addons.drawing import layout as dl
    w, h = dimensiune_foaie(doc, foaie)
    be = _randeaza(doc, foaie, False)
    return be.get_pixmap_bytes(dl.Page(w, h, dl.Units.mm, margins=dl.Margins.all(0)), fmt="png", settings=dl.Settings(fit_page=True), dpi=dpi)


def imprimante():
    try:
        import win32print
        lst = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
        imp = win32print.GetDefaultPrinter()
        return [imp] + [p for p in lst if p != imp] + [PDF]
    except Exception:
        return [PDF]


# codurile Windows ale formatelor de hârtie (DMPAPER_*); A0 și A1 nu au cod standard – rămâne hârtia imprimantei
DMPAPER = {"A2": 66, "A3": 8, "A4": 9, "A5": 11}


def _dc(imprimanta, fmt, orientare):
    """contextul imprimantei cu formatul și orientarea cerute (dacă imprimanta le are)"""
    import win32ui, win32print, win32gui, win32con
    try:
        h = win32print.OpenPrinter(imprimanta)
        try:
            dm = win32print.GetPrinter(h, 2)["pDevMode"]
            if fmt in DMPAPER: dm.PaperSize = DMPAPER[fmt]; dm.Fields |= win32con.DM_PAPERSIZE
            dm.Orientation = 2 if orientare == "Альбомная" else 1; dm.Fields |= win32con.DM_ORIENTATION
            win32print.DocumentProperties(0, h, imprimanta, dm, dm, win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER)
        finally: win32print.ClosePrinter(h)
        return win32ui.CreateDCFromHandle(win32gui.CreateDC("WINSPOOL", imprimanta, dm))
    except Exception:
        dc = win32ui.CreateDC(); dc.CreatePrinterDC(imprimanta); return dc


def tipareste(png_bytes, imprimanta, titlu="CAD PC", fmt=IMPLICIT, orientare="Альбомная"):
    """trimite imaginea paginii la imprimantă, pe formatul cerut, potrivită pe zona tipăribilă (GDI)"""
    import win32con
    from PIL import Image, ImageWin
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    dc = _dc(imprimanta, fmt, orientare)
    W, H = dc.GetDeviceCaps(win32con.HORZRES), dc.GetDeviceCaps(win32con.VERTRES)
    if (W > H) != (img.width > img.height): img = img.rotate(90, expand=True)
    k = min(W / img.width, H / img.height); w, h = int(img.width * k), int(img.height * k)
    x, y = (W - w) // 2, (H - h) // 2
    dc.StartDoc(titlu); dc.StartPage()
    ImageWin.Dib(img).draw(dc.GetHandleOutput(), (x, y, x + w, y + h))
    dc.EndPage(); dc.EndDoc(); dc.DeleteDC()


def dialog(app, doar_pdf=False):
    if not app.doc: return app.mesaj("Нет открытого чертежа.")
    foaie = app.v.foaie or "Model"
    d = tk.Toplevel(app.root); d.title(("Экспорт в PDF – " if doar_pdf else "Печать – ") + ("Модель" if foaie == "Model" else foaie))
    d.configure(bg=CORP); d.transient(app.root); d.geometry("560x330"); d.columnconfigure(1, weight=1)
    def rand(t, w, r):
        tk.Label(d, text=t, bg=CORP, fg=TEXT, font=F_MIC).grid(row=r, column=0, sticky="w", padx=12, pady=6); w.grid(row=r, column=1, sticky="we", padx=12, pady=6); return w
    imp = ttk.Combobox(d, values=[PDF] if doar_pdf else imprimante(), state="readonly"); rand("Принтер/плоттер:", imp, 0); imp.current(0)
    fmt = ttk.Combobox(d, values=list(FORMATE), state="readonly"); rand("Формат листа:", fmt, 1); fmt.set(IMPLICIT)
    ori = ttk.Combobox(d, values=["Альбомная", "Книжная"], state="readonly"); rand("Ориентация:", ori, 2); ori.set("Альбомная")
    foi = ttk.Combobox(d, values=["Model"] + [l.name for l in app.doc.layouts if l.name != "Model"], state="readonly"); rand("Что печатать:", foi, 3); foi.set(foaie)
    mono = tk.BooleanVar(value=False)
    tk.Checkbutton(d, text="Монохромная печать (все линии черные)", variable=mono, bg=CORP, fg=TEXT, selectcolor="#2b313a", activebackground=CORP,
                   activeforeground=TEXT).grid(row=4, column=1, sticky="w", padx=12)
    mg = tk.Entry(d, bg="#2b313a", fg=TEXT, insertbackground=TEXT, relief="flat", width=6); mg.insert(0, "10"); rand("Поля (мм):", mg, 5)
    def param():
        try: m = float(mg.get().replace(",", "."))
        except ValueError: m = 10
        return dict(foaie=foi.get(), fmt=fmt.get(), orientare=ori.get(), monocrom=mono.get(), margini=m)
    def previzualizare():
        app.root.config(cursor="watch"); app.root.update_idletasks()
        try: data = png(app.doc, dpi=60, **param())
        except Exception as ex: app.root.config(cursor=""); return messagebox.showerror("Просмотр", str(ex), parent=d)
        app.root.config(cursor="")
        v = tk.Toplevel(d); v.title("Предварительный просмотр"); v.configure(bg="#5a5a5a")
        foto = tk.PhotoImage(data=data); v._foto = foto
        tk.Label(v, image=foto, bg="#5a5a5a", bd=8).pack(padx=16, pady=16)
    def ok():
        p = param(); app.root.config(cursor="watch"); app.root.update_idletasks()
        try:
            if imp.get() == PDF:
                baza = os.path.splitext(os.path.basename(app.cale or "Чертеж1"))[0] + ("" if p["foaie"] == "Model" else "_" + p["foaie"])
                cale = filedialog.asksaveasfilename(parent=d, title="Сохранить PDF", initialfile=baza + ".pdf", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
                if not cale: app.root.config(cursor=""); return
                open(cale, "wb").write(pdf(app.doc, **p)); app.mesaj(f"PDF сохранен: {cale}")
                if os.name == "nt":
                    try: os.startfile(cale)
                    except Exception: pass
            else:
                dpi = {"A0": 100, "A1": 130, "A2": 160}.get(p["fmt"], 200)
                tipareste(png(app.doc, dpi=dpi, **p), imp.get(), os.path.basename(app.cale or "Чертеж1"), p["fmt"], p["orientare"])
                app.mesaj(f"Отправлено на печать: {imp.get()} ({p['fmt']}, {p['orientare']}).")
        except Exception as ex:
            app.root.config(cursor=""); return messagebox.showerror("Печать", f"Ошибка: {ex}", parent=d)
        app.root.config(cursor=""); d.destroy()
    f = tk.Frame(d, bg=CORP); f.grid(row=6, column=0, columnspan=2, sticky="e", padx=12, pady=12)
    for t, c in (("Просмотр...", previzualizare), ("OK", ok), ("Отмена", d.destroy)):
        b = tk.Label(f, text=t, bg=ALBASTRU if t == "OK" else FILE, fg="white", font=F_MIC, padx=16, pady=4); b.pack(side="left", padx=4)
        b.bind("<Button-1>", lambda e, c=c: c())
