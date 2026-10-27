# PDF PC – partea fără interfață: formate A0…A5, conversie în PDF, combinare, aplicarea completărilor pe pagini.
import os, sys, shutil, tempfile, threading, subprocess, ctypes, itertools
try:
    import pymupdf as fitz
except ImportError:
    import fitz

MM = 72 / 25.4
FORMATE = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297), "A5": (148, 210)}
EXT_W = {".doc", ".docx", ".rtf", ".odt", ".txt"}
EXT_X = {".xls", ".xlsx", ".xlsm", ".ods", ".csv"}
EXT_P = {".ppt", ".pptx", ".odp"}
EXT_I = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif"}
EXT_TOATE = {".pdf"} | EXT_W | EXT_X | EXT_P | EXT_I
TIPURI = [("Toate fișierele suportate", " ".join("*" + e for e in sorted(EXT_TOATE))), ("PDF", "*.pdf"),
          ("Word", "*.doc *.docx *.rtf *.odt *.txt"), ("Excel", "*.xls *.xlsx *.xlsm *.ods *.csv"),
          ("PowerPoint", "*.ppt *.pptx *.odp"), ("Imagini", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.gif")]
TMP = tempfile.mkdtemp(prefix="pdfpc_")
_nr = itertools.count()


def tmp(sufix=".pdf"):
    return os.path.join(TMP, f"f{next(_nr)}{sufix}")


def _font():
    for f in (r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(f): return f
    return None


FONT = _font()
FNT = fitz.Font(fontfile=FONT) if FONT else fitz.Font("helv")
LINIE = FNT.ascender - FNT.descender                     # înălțimea unui rând, în multipli de mărimea fontului


def limiteaza_cpu():
    """lasă 2 nuclee libere și rulează cu prioritate sub normal, ca să nu blocheze calculatorul"""
    try:
        n = os.cpu_count() or 1
        if sys.platform == "win32":
            k = ctypes.windll.kernel32; h = k.GetCurrentProcess()
            if n > 2: k.SetProcessAffinityMask(h, (1 << (n - 2)) - 1)
            k.SetPriorityClass(h, 0x4000)
        elif n > 2:
            os.sched_setaffinity(0, set(range(n - 2)))
    except Exception:
        pass
    try: fitz.TOOLS.store_maxsize = 128 * 1024 * 1024     # memoria cache MuPDF limitată
    except Exception: pass


def dim_pt(fmt, orizontal):
    w, h = FORMATE[fmt]; w, h = w * MM, h * MM
    return (h, w) if orizontal else (w, h)


def nume_format(w, h):
    a, b = sorted((w / MM, h / MM)); o = "orizontal" if w > h + 0.5 else "vertical"
    for k, (fw, fh) in FORMATE.items():
        if abs(a - fw) <= fw * 0.02 + 2 and abs(b - fh) <= fh * 0.02 + 2: return f"{k} {o} ({fw}×{fh} mm)"
    return f"{w / MM:.0f}×{h / MM:.0f} mm"


def pagini_din_text(t, n):
    """'1-3, 5' -> [0, 1, 2, 4]; gol sau 'toate' -> toate paginile"""
    t = (t or "").strip().lower()
    if t in ("", "toate", "all"): return list(range(n))
    rez = []
    for b in t.replace(";", ",").split(","):
        b = b.strip()
        if not b: continue
        if "-" in b:
            x, y = b.split("-", 1); x = int(x or 1); y = int(y or n)
            rez += list(range(x - 1, y)) if x <= y else list(range(x - 1, y - 2, -1))
        else:
            rez.append(int(b) - 1)
    return [p for p in rez if 0 <= p < n]


# ---------- conversie în PDF ----------
def _soffice():
    for c in (shutil.which("soffice"), r"C:\Program Files\LibreOffice\program\soffice.exe",
              r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
        if c and os.path.exists(c): return c


def _prin_office(cale, iesire, ext):
    import pythoncom, win32com.client
    pythoncom.CoInitialize(); app = None
    try:
        src, dst = os.path.abspath(cale), os.path.abspath(iesire)
        if ext in EXT_W:
            app = win32com.client.DispatchEx("Word.Application"); app.Visible = False; app.DisplayAlerts = 0
            d = app.Documents.Open(src, False, True, False); d.ExportAsFixedFormat(dst, 17); d.Close(False)
        elif ext in EXT_X:
            app = win32com.client.DispatchEx("Excel.Application"); app.Visible = False; app.DisplayAlerts = False
            w = app.Workbooks.Open(src, 0, True); w.ExportAsFixedFormat(0, dst); w.Close(False)
        else:
            app = win32com.client.DispatchEx("PowerPoint.Application")
            p = app.Presentations.Open(src, True, False, False); p.SaveAs(dst, 32); p.Close()
    finally:
        if app is not None:
            try: app.Quit()
            except Exception: pass
        pythoncom.CoUninitialize()


def deschide_pdf(cale):
    """orice fișier suportat -> fitz.Document. PDF-ul se deschide dintr-o copie, ca originalul să poată fi suprascris la salvare."""
    ext = os.path.splitext(cale)[1].lower()
    if ext == ".pdf":
        t = tmp(); shutil.copyfile(cale, t); return fitz.open(t)
    if ext in EXT_I:
        with fitz.open(cale) as im: data = im.convert_to_pdf()
        t = tmp(); open(t, "wb").write(data); return fitz.open(t)
    if ext in EXT_W | EXT_X | EXT_P:
        out = tmp(); err = []
        if sys.platform == "win32":
            try: _prin_office(cale, out, ext)
            except Exception as e: err.append(f"Microsoft Office: {e}")
        if not os.path.exists(out):
            so = _soffice()
            if so:
                od = tempfile.mkdtemp(dir=TMP)
                subprocess.run([so, "--headless", "--convert-to", "pdf", "--outdir", od, cale], timeout=300,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                g = [f for f in os.listdir(od) if f.lower().endswith(".pdf")]
                if g: shutil.move(os.path.join(od, g[0]), out)
            else:
                err.append("LibreOffice nu este instalat.")
        if not os.path.exists(out):
            raise RuntimeError(f"Nu pot converti în PDF: {os.path.basename(cale)}\n\n" + "\n".join(err) +
                               "\n\nPentru Word/Excel/PowerPoint trebuie instalat Microsoft Office sau LibreOffice (gratuit).")
        return fitz.open(out)
    raise RuntimeError("Tip de fișier nesuportat: " + (ext or os.path.basename(cale)))


# ---------- pagini ----------
def schimba_format(doc, pagini, fmt, orient="Automat"):
    """pune paginile pe formatul ales (A0…A5); conținutul se scalează proporțional și se centrează"""
    t = tmp(); doc.save(t); src = fitz.open(t)
    for p in sorted(set(pagini)):
        r = src[p].rect
        oriz = (r.width > r.height) if orient == "Automat" else (orient == "Orizontal")
        W, H = dim_pt(fmt, oriz)
        doc.delete_page(p); np_ = doc.new_page(p, width=W, height=H); np_.show_pdf_page(np_.rect, src, p)
    src.close()


def combina(intrari, fmt=None, orient="Automat", progres=None):
    """intrari = [(cale, 'pagini')]; rezultat: un document nou"""
    out = fitz.open()
    for k, (cale, pag) in enumerate(intrari):
        if progres: progres(k, len(intrari), cale)
        src = deschide_pdf(cale)
        if src.needs_pass and not src.authenticate(""):
            raise RuntimeError("PDF protejat cu parolă: " + os.path.basename(cale))
        for a in pagini_din_text(pag, len(src)): out.insert_pdf(src, from_page=a, to_page=a)
        src.close()
    if fmt and len(out): schimba_format(out, range(len(out)), fmt, orient)
    return out


def salveaza(doc, cale):
    """salvare sigură: întâi într-un fișier temporar, apoi se înlocuiește ținta"""
    t = tmp(); doc.save(t, garbage=3, deflate=True)
    try:
        if os.path.exists(cale): os.remove(cale)
    except PermissionError:
        raise RuntimeError(f"Fișierul este deschis în alt program și nu poate fi suprascris:\n{cale}")
    shutil.move(t, cale)


# ---------- completări (text, semne, forme, imagini, semnătură) ----------
def hex_rgb(c):
    c = (c or "000000").lstrip("#")
    if len(c) == 3: c = "".join(x * 2 for x in c)
    return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))


def cutie(o):
    x0, y0, x1, y1 = o["r"]; return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def masoara_text(o):
    """recalculează dreptunghiul unui text după conținut și mărime"""
    r = o["txt"].split("\n"); s = o["s"]
    w = max([FNT.text_length(x, fontsize=s) for x in r] + [s])
    x0, y0 = o["r"][0], o["r"][1]; o["r"] = [x0, y0, x0 + w, y0 + len(r) * s * LINIE]


def aplica(doc, over, imagini):
    """scrie definitiv completările în pagini (la salvare sau înainte de operațiile cu pagini)"""
    for pno, lst in over.items():
        if pno >= len(doc) or not lst: continue
        pg = doc[pno]; M = pg.derotation_matrix; rot = pg.rotation
        q = lambda x, y: fitz.Point(x, y) * M
        for o in lst:
            col = hex_rgb(o.get("c", "#000000")); t = o["t"]; x0, y0, x1, y1 = cutie(o); w = max(0.8, o.get("s", 12) / 10)
            R = fitz.Rect(x0, y0, x1, y1) * M
            if t == "text":
                s = o["s"]
                for k, rand in enumerate(o["txt"].split("\n")):
                    if rand.strip():
                        kw = dict(fontname="F0", fontfile=FONT) if FONT else dict(fontname="helv")
                        pg.insert_text(q(o["r"][0], o["r"][1] + s * FNT.ascender + k * s * LINIE), rand, fontsize=s, color=col, rotate=rot, **kw)
            elif t == "x":
                pg.draw_line(q(x0, y0), q(x1, y1), color=col, width=w); pg.draw_line(q(x0, y1), q(x1, y0), color=col, width=w)
            elif t == "v":
                pg.draw_polyline([q(x0, y0 + (y1 - y0) * .55), q(x0 + (x1 - x0) * .38, y1), q(x1, y0)], color=col, width=w)
            elif t == "oval":
                pg.draw_oval(R, color=col, width=w)
            elif t == "linie":
                a = o["r"]; pg.draw_line(q(a[0], a[1]), q(a[2], a[3]), color=col, width=w)
            elif t == "punct":
                pg.draw_circle(q((x0 + x1) / 2, (y0 + y1) / 2), (x1 - x0) / 2, color=col, fill=col)
            elif t == "drept":
                pg.draw_rect(R, color=col, width=w)
            elif t == "alb":
                pg.draw_rect(R, color=None, fill=(1, 1, 1), width=0)
            elif t == "evid":
                pg.draw_rect(R, color=None, fill=col, fill_opacity=0.35, width=0, overlay=True)
            elif t in ("img", "semn"):
                pg.insert_image(R, stream=imagini[o["img"]], keep_proportion=False, rotate=rot)
