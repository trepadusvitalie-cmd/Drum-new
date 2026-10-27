# PDF PC – editor PDF: pagini A0…A5, completare și semnare, combinare fișiere (PDF, Word, Excel, PowerPoint, imagini).
# Tot lucrul cu documentul se face într-un fir separat, ca fereastra să nu se blocheze nici la planșe A0.
import os, sys, io, copy, json, queue, socket, threading, shutil, ctypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from pdf_nucleu import fitz
from PIL import Image, ImageTk, ImageDraw
from pdf_nucleu import *

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
except Exception:
    TkinterDnD = None
def langa_exe(nume):
    """fișiere puse de utilizator lângă exe (titlu.txt, logo.png) – nu fac parte din codul programului"""
    d = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
    return os.path.join(d, nume)


def _titlu():
    try:
        t = open(langa_exe("titlu.txt"), encoding="utf-8-sig").read().strip()
        if t: return t
    except Exception: pass
    return "PDF PC"


NUME = _titlu()
CFG_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "PDF_PC")
os.makedirs(CFG_DIR, exist_ok=True)
CFG = os.path.join(CFG_DIR, "setari.json")
SEMN = os.path.join(CFG_DIR, "semnatura.png")
PORT = 47613
OX = OY = 24                                              # marginea paginii în fereastră
TEMA = {"panou": "#e8e8e8", "sursa": "#dfe7f2", "accent": "#1a73e8", "selectie": "#9cc3f5", "text2": "#444"}
UNELTE = [("sel", "↖", "Selectare / mutare (dublu clic pe text = editare, Delete = șterge)"),
          ("text", "IAb", "Adaugă text: clic pe pagină și scrie"), ("x", "✗", "Pune un X"), ("v", "✓", "Pune o bifă"),
          ("oval", "◯", "Cerc / oval: trage cu mouse-ul"), ("linie", "—", "Linie: trage cu mouse-ul"), ("punct", "•", "Punct"),
          ("drept", "▭", "Dreptunghi"), ("alb", "⬜", "Acoperă (alb): ascunde un text existent, apoi scrie peste"),
          ("evid", "🖍", "Evidențiere"), ("img", "🖼", "Imagine: alege fișierul, apoi clic pe pagină"),
          ("semn", "✍", "Semnătură")]


def cit_cfg():
    try: return json.load(open(CFG, encoding="utf-8"))
    except Exception: return {}


def scr_cfg(**kw):
    c = cit_cfg(); c.update(kw)
    try: json.dump(c, open(CFG, "w", encoding="utf-8"))
    except Exception: pass


class Sfat:
    """explicație mică la oprirea mouse-ului pe un buton"""
    def __init__(self, w, text):
        self.w, self.text, self.t, self.job = w, text, None, None
        w.bind("<Enter>", lambda e: self._prog()); w.bind("<Leave>", lambda e: self.ascunde()); w.bind("<ButtonPress>", lambda e: self.ascunde())

    def _prog(self):
        self.ascunde(); self.job = self.w.after(500, self.arata)

    def arata(self):
        self.job = None
        x, y = self.w.winfo_rootx() + 10, self.w.winfo_rooty() + self.w.winfo_height() + 4
        self.t = tk.Toplevel(self.w); self.t.wm_overrideredirect(True); self.t.wm_geometry(f"+{x}+{y}")
        tk.Label(self.t, text=self.text, bg="#ffffe1", relief="solid", bd=1, padx=6, pady=3).pack()

    def ascunde(self):
        if self.job: self.w.after_cancel(self.job); self.job = None
        if self.t: self.t.destroy(); self.t = None


class App:
    def __init__(self):
        self.root = TkinterDnD.Tk() if TkinterDnD else tk.Tk()
        self.root.title(NUME); self.root.geometry("1280x820"); self.root.minsize(900, 560)
        try: self.root.iconbitmap(default=os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(__file__)), "pdf_pc.ico"))
        except Exception: pass
        self._iconita()
        self.doc = None; self.cale = None; self.modificat = False
        self.dims = []; self.ver = 0; self.pag = 0; self.z = 96 / 72
        self.over = {}; self.imagini = {}; self.sel = None; self.undo = []; self.redo = []
        self.unealta = tk.StringVar(value="sel"); self.culoare = "#000000"; self.marime = tk.DoubleVar(value=12)
        self.sel_pag = {0}; self.thumbs = {}; self.render_ok = None; self._img = None; self._ovimg = []
        self.src = None; self.src_ver = 0; self.src_dims = []; self._s_poz = []; self.s_thumbs = {}; self.s_sel = set(); self.src_nume = ""
        self._t_poz = []; self._hover = None
        self._jobs = []; self._render_cer = None; self._thumb_cer = []; self._mx = threading.Lock(); self._ev = threading.Event()
        self._rez = queue.Queue(); self.ocupat = False; self._combina_asteapta = []; self._dlg_comb = None
        threading.Thread(target=self._lucrator, daemon=True).start()
        self._ui()
        self.root.after(40, self._sondaj)
        self.root.protocol("WM_DELETE_WINDOW", self.iesire)

    def _iconita(self):
        """iconița ferestrei: cercul din stânga lui logo.png (de lângă exe) cu eticheta „PDF”"""
        try:
            p = langa_exe("logo.png")
            if not os.path.exists(p): return
            im = Image.open(p).convert("RGBA"); im = im.crop((0, 0, min(im.height, im.width), im.height)).resize((256, 256), Image.LANCZOS)
            d = ImageDraw.Draw(im); d.rounded_rectangle((96, 168, 254, 246), radius=16, fill=(205, 30, 30, 255), outline="white", width=5)
            try:
                from PIL import ImageFont
                f = ImageFont.truetype("arialbd.ttf" if sys.platform == "win32" else "DejaVuSans-Bold.ttf", 52)
            except Exception:
                f = None
            d.text((175, 207), "PDF", fill="white", anchor="mm", font=f)
            self._icoane = [ImageTk.PhotoImage(im.resize((n, n), Image.LANCZOS)) for n in (64, 48, 32, 16)]
            self.root.iconphoto(True, *self._icoane)
        except Exception:
            pass

    def _logo(self, inaltime):
        p = langa_exe("logo.png")
        if not os.path.exists(p): return None
        try:
            im = Image.open(p).convert("RGBA"); k = inaltime / im.height
            return ImageTk.PhotoImage(im.resize((max(1, int(im.width * k)), inaltime), Image.LANCZOS))
        except Exception:
            return None

    # ======================= interfață =======================
    def _ui(self):
        st = ttk.Style()
        try: st.theme_use("vista" if sys.platform == "win32" else "clam")
        except Exception: pass
        st.configure("Ul.TButton", padding=(6, 2)); st.configure("Un.Toolbutton", padding=(6, 2), font=("Segoe UI", 11))
        m = tk.Menu(self.root); self.root.config(menu=m)
        self.m_fis = tk.Menu(m, tearoff=0, postcommand=self._meniu_fisier); m.add_cascade(label="Fișier", menu=self.m_fis)
        p = tk.Menu(m, tearoff=0); m.add_cascade(label="Pagini", menu=p)
        p.add_command(label="Pagină nouă (A0…A5)…", command=self.pagina_noua)
        p.add_command(label="Inserează din fișier (PDF, Word, Excel, imagine)…", command=self.insereaza_dialog)
        p.add_command(label="Schimbă formatul paginilor (A0…A5)…", command=self.format_dialog)
        p.add_command(label="Duplică pagina", command=self.duplica)
        p.add_command(label="Extrage paginile selectate…", command=self.extrage)
        p.add_separator()
        p.add_command(label="Rotește la stânga", command=lambda: self.roteste(-90))
        p.add_command(label="Rotește la dreapta", command=lambda: self.roteste(90))
        p.add_command(label="Mută sus", command=lambda: self.muta(-1)); p.add_command(label="Mută jos", command=lambda: self.muta(1))
        p.add_separator(); p.add_command(label="Șterge paginile selectate   Ctrl+Del", command=self.sterge_pagini)
        e = tk.Menu(m, tearoff=0); m.add_cascade(label="Editare", menu=e)
        e.add_command(label="Anulează   Ctrl+Z", command=self.anuleaza); e.add_command(label="Refă   Ctrl+Y", command=self.reface)
        e.add_command(label="Șterge obiectul selectat   Delete", command=self.sterge_obiect)
        v = tk.Menu(m, tearoff=0); m.add_cascade(label="Vizualizare", menu=v)
        v.add_command(label="Mărește   Ctrl++", command=lambda: self.zoom(1.25)); v.add_command(label="Micșorează   Ctrl+-", command=lambda: self.zoom(0.8))
        v.add_command(label="Pe lățime", command=self.pe_latime); v.add_command(label="Pagina întreagă", command=self.pe_pagina)
        v.add_command(label="100%", command=lambda: self.zoom_la(96 / 72))

        # bara 1: fișier, navigare, zoom, pagini
        b = ttk.Frame(self.root, padding=(4, 3)); b.pack(fill="x")
        def bt(par, t, cmd, sfat, **kw):
            w = ttk.Button(par, text=t, command=cmd, style="Ul.TButton", width=-2, **kw); w.pack(side="left", padx=1); Sfat(w, sfat); return w
        bt(b, "📂 Deschide", self.deschide_dialog, "Deschide PDF, Word, Excel, PowerPoint sau imagine (Ctrl+O)")
        bt(b, "💾 Salvează", self.salveaza, "Salvează (Ctrl+S)")
        bt(b, "🗂 Combină", lambda: self.combina_dialog([]), "Combină fișiere: unește mai multe fișiere într-un singur PDF")
        bt(b, "🖨", self.imprima, "Imprimă (Ctrl+P)")
        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=6)
        bt(b, "◀", lambda: self.mergi(self.pag - 1), "Pagina anterioară (PgUp)")
        self.e_pag = ttk.Entry(b, width=5, justify="center"); self.e_pag.pack(side="left")
        self.e_pag.bind("<Return>", lambda e: self._mergi_text())
        self.l_nr = ttk.Label(b, text="/ 0"); self.l_nr.pack(side="left", padx=3)
        bt(b, "▶", lambda: self.mergi(self.pag + 1), "Pagina următoare (PgDn)")
        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=6)
        bt(b, "−", lambda: self.zoom(0.8), "Micșorează"); self.cb_zoom = ttk.Combobox(b, width=7, values=["25%", "50%", "75%", "100%", "125%", "150%", "200%", "300%", "400%", "Pe lățime", "Pagină"])
        self.cb_zoom.pack(side="left"); self.cb_zoom.bind("<<ComboboxSelected>>", lambda e: self._zoom_text()); self.cb_zoom.bind("<Return>", lambda e: self._zoom_text())
        bt(b, "+", lambda: self.zoom(1.25), "Mărește")
        ttk.Separator(b, orient="vertical").pack(side="left", fill="y", padx=6)
        bt(b, "➕ Pagină", self.pagina_noua, "Adaugă pagină goală A0, A1, A2, A3, A4 sau A5")
        bt(b, "📥 Inserează", self.insereaza_dialog, "Inserează pagini din PDF, DOC, DOCX, Excel sau imagine după pagina curentă")
        bt(b, "📐 Format", self.format_dialog, "Schimbă formatul paginilor selectate (A0…A5)")
        bt(b, "⟲", lambda: self.roteste(-90), "Rotește la stânga"); bt(b, "⟳", lambda: self.roteste(90), "Rotește la dreapta")
        bt(b, "▲", lambda: self.muta(-1), "Mută pagina mai sus"); bt(b, "▼", lambda: self.muta(1), "Mută pagina mai jos")
        bt(b, "🗑", self.sterge_pagini, "Șterge paginile selectate")
        bt(b, "↶", self.anuleaza, "Anulează (Ctrl+Z)"); bt(b, "↷", self.reface, "Refă (Ctrl+Y)")

        # bara 2: completare și semnare
        b2 = ttk.Frame(self.root, padding=(4, 2)); b2.pack(fill="x")
        ttk.Label(b2, text="Completare și semnare:").pack(side="left", padx=(2, 6))
        for k, t, s in UNELTE:
            w = ttk.Radiobutton(b2, text=t, value=k, variable=self.unealta, style="Un.Toolbutton", command=self._unealta_aleasa)
            w.pack(side="left", padx=1); Sfat(w, s)
        ttk.Separator(b2, orient="vertical").pack(side="left", fill="y", padx=6)
        self.b_col = tk.Button(b2, text="●", fg=self.culoare, font=("Segoe UI", 14), bd=0, command=self.alege_culoare, cursor="hand2"); self.b_col.pack(side="left")
        Sfat(self.b_col, "Culoarea")
        for c in ("#000000", "#1f4fbf", "#d01010", "#108020"):
            w = tk.Button(b2, text="■", fg=c, bd=0, font=("Segoe UI", 11), command=lambda c=c: self.seteaza_culoare(c), cursor="hand2"); w.pack(side="left")
        ttk.Label(b2, text="  Mărime:").pack(side="left")
        sp = ttk.Spinbox(b2, from_=4, to=200, increment=1, width=5, textvariable=self.marime, command=self._marime_schimbata); sp.pack(side="left")
        sp.bind("<Return>", lambda e: self._marime_schimbata())
        self.img_logo = self._logo(30)
        if self.img_logo: ttk.Label(b2, image=self.img_logo).pack(side="right", padx=10)

        # zona principală: miniaturi | pagină
        pw = ttk.PanedWindow(self.root, orient="horizontal"); pw.pack(fill="both", expand=True)
        st_ = ttk.Frame(pw); pw.add(st_, weight=0); self.pw = pw
        fr_t = ttk.Frame(st_); fr_t.pack(side="left", fill="y")
        ttk.Label(fr_t, text="  Pagini").pack(anchor="w", pady=(4, 2))
        self.cv_t = tk.Canvas(fr_t, width=170, bg=TEMA["panou"], highlightthickness=0); sb = ttk.Scrollbar(fr_t, command=self.cv_t.yview)
        self.cv_t.config(yscrollcommand=lambda a, b_: (sb.set(a, b_), self._cere_thumbs())); sb.pack(side="right", fill="y"); self.cv_t.pack(side="left", fill="both", expand=True)
        self.fr_s = ttk.Frame(st_)                                  # coloana cu paginile fișierului adăugat (apare la „Inserează”)
        h = ttk.Frame(self.fr_s); h.pack(fill="x", pady=(4, 2))
        self.l_src = ttk.Label(h, text="", width=18); self.l_src.pack(side="left", padx=(4, 0))
        w = ttk.Button(h, text="✕", width=2, command=self.inchide_sursa); w.pack(side="right"); Sfat(w, "Închide coloana")
        w = ttk.Button(self.fr_s, text="⇇ Inserează toate", command=lambda: self.insereaza_din_sursa(None, None)); w.pack(fill="x", padx=4, pady=(0, 4))
        Sfat(w, "Inserează toate paginile după pagina curentă")
        self.cv_s = tk.Canvas(self.fr_s, width=170, bg=TEMA["sursa"], highlightthickness=0); sb2 = ttk.Scrollbar(self.fr_s, command=self.cv_s.yview)
        self.cv_s.config(yscrollcommand=lambda a, b_: (sb2.set(a, b_), self._cere_thumbs())); sb2.pack(side="right", fill="y"); self.cv_s.pack(side="left", fill="both", expand=True)
        dr = ttk.Frame(pw); pw.add(dr, weight=1)
        self.cv = tk.Canvas(dr, bg="#8a8f96", highlightthickness=0)
        sy = ttk.Scrollbar(dr, command=self.cv.yview); sx = ttk.Scrollbar(dr, orient="horizontal", command=self.cv.xview)
        self.cv.config(yscrollcommand=lambda a, b_: (sy.set(a, b_), self._cere_render()), xscrollcommand=lambda a, b_: (sx.set(a, b_), self._cere_render()))
        sy.pack(side="right", fill="y"); sx.pack(side="bottom", fill="x"); self.cv.pack(fill="both", expand=True)
        self.status = ttk.Label(self.root, text="Deschide un fișier (Ctrl+O), trage fișiere aici sau folosește „Combină fișiere”.", anchor="w", padding=(6, 2))
        self.status.pack(fill="x", side="bottom")
        self.pb = ttk.Progressbar(self.status, mode="indeterminate", length=160)

        self.cv.bind("<Configure>", lambda e: self._cere_render())
        self.cv.bind("<ButtonPress-1>", self._apasa); self.cv.bind("<B1-Motion>", self._trage); self.cv.bind("<ButtonRelease-1>", self._elibereaza)
        self.cv.bind("<Double-Button-1>", self._dublu)
        self.cv.bind("<MouseWheel>", self._rotita); self.cv.bind("<Button-4>", lambda e: self._rotita(e, 120)); self.cv.bind("<Button-5>", lambda e: self._rotita(e, -120))
        self.cv_t.bind("<MouseWheel>", lambda e: self.cv_t.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.cv_t.bind("<ButtonPress-1>", self._t_apasa); self.cv_t.bind("<B1-Motion>", self._t_trage); self.cv_t.bind("<ButtonRelease-1>", self._t_elib)
        self.cv_t.bind("<Button-3>", self._t_meniu); self.cv.bind("<Button-3>", self._cv_meniu)
        self.cv_s.bind("<ButtonPress-1>", self._s_apasa); self.cv_s.bind("<B1-Motion>", self._s_trage); self.cv_s.bind("<ButtonRelease-1>", self._s_elib)
        self.cv_s.bind("<Double-Button-1>", lambda e: self._s_dublu(e)); self.cv_s.bind("<Button-3>", self._s_meniu)
        self.cv_s.bind("<MouseWheel>", lambda e: self.cv_s.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        r = self.root
        r.bind_all("<Control-o>", lambda e: self.deschide_dialog()); r.bind_all("<Control-s>", lambda e: self.salveaza())
        r.bind_all("<Control-S>", lambda e: self.salveaza(ca=True)); r.bind_all("<Control-p>", lambda e: self.imprima())
        r.bind_all("<Control-w>", lambda e: self.inchide()); r.bind_all("<Control-q>", lambda e: self.iesire())
        r.bind_all("<Control-d>", lambda e: self.proprietati())
        r.bind_all("<Control-z>", lambda e: self.anuleaza()); r.bind_all("<Control-y>", lambda e: self.reface())
        r.bind_all("<Control-plus>", lambda e: self.zoom(1.25)); r.bind_all("<Control-equal>", lambda e: self.zoom(1.25)); r.bind_all("<Control-minus>", lambda e: self.zoom(0.8))
        r.bind_all("<Prior>", lambda e: self._tasta_nav(-1)); r.bind_all("<Next>", lambda e: self._tasta_nav(1))
        r.bind_all("<Delete>", lambda e: self._tasta_del()); r.bind_all("<Control-Delete>", lambda e: self.sterge_pagini())
        r.bind_all("<Escape>", lambda e: (self.unealta.set("sel"), self._selecteaza(None)))
        r.bind_all("<Key>", self._tasta_ctrl, add="+")
        if TkinterDnD:
            for w in (self.cv, self.cv_t, self.cv_s):
                w.drop_target_register(DND_FILES); w.dnd_bind("<<Drop>>", lambda e, w=w: self._drop(e, w))

    def _tasta_ctrl(self, e):
        """Ctrl+O/S/Z/Y/P merg și cu tastatura rusă/română (după codul tastei)"""
        if not (e.state & 4) or e.keysym.lower() in "oszypwqd" and len(e.keysym) == 1: return
        k = {79: self.deschide_dialog, 83: self.salveaza, 90: self.anuleaza, 89: self.reface, 80: self.imprima,
             87: self.inchide, 81: self.iesire, 68: self.proprietati}.get(e.keycode)
        if k and sys.platform == "win32": k()

    def _focus_text(self):
        return isinstance(self.root.focus_get(), (tk.Entry, ttk.Entry, tk.Text, ttk.Spinbox, ttk.Combobox))

    def _tasta_nav(self, d):
        if not self._focus_text(): self.mergi(self.pag + d)

    def _tasta_del(self):
        if not self._focus_text(): self.sterge_obiect()

    # ======================= fir de lucru (nu blochează fereastra) =======================
    def _lucrator(self):
        while True:
            self._ev.wait()
            with self._mx:
                job = self._jobs.pop(0) if self._jobs else None
                rc = None if job else self._render_cer
                if rc: self._render_cer = None
                th = None if (job or rc) else (self._thumb_cer.pop(0) if self._thumb_cer else None)
                if not (job or rc or th): self._ev.clear(); continue
            try:
                if job:
                    fn, gata = job
                    if gata is False:
                        try: fn()
                        except Exception: pass
                        continue
                    try: self._rez.put(("gata", gata, fn(), None))
                    except Exception as ex: self._rez.put(("gata", gata, None, ex))
                elif rc:
                    ver, pno, z, clip = rc
                    if self.doc is None or ver != self.ver or pno >= len(self.doc): continue
                    pix = self.doc[pno].get_pixmap(matrix=fitz.Matrix(z, z), clip=clip, alpha=False)
                    self._rez.put(("render", (ver, pno, z, tuple(clip)), Image.frombytes("RGB", (pix.width, pix.height), pix.samples), None))
                    del pix
                else:
                    tip_, ver, pno = th; d = self.doc if tip_ == "d" else self.src
                    if d is None or ver != (self.ver if tip_ == "d" else self.src_ver) or pno >= len(d): continue
                    pg = d[pno]; z = 120 / max(pg.rect.width, pg.rect.height)
                    pix = pg.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
                    self._rez.put(("thumb", (tip_, ver, pno), Image.frombytes("RGB", (pix.width, pix.height), pix.samples), None))
            except Exception as ex:
                print("lucrator:", ex)

    def lucru(self, fn, gata=None, mesaj="Se lucrează…"):
        """rulează fn() în fundal; gata(rezultat) se apelează în fereastră"""
        if self.ocupat:
            self.stare("⏳ Aștept terminarea operației anterioare…"); return False
        self.ocupat = True; self.stare("⏳ " + mesaj); self.pb.pack(side="right", padx=6); self.pb.start(12)
        self.root.config(cursor="watch")
        with self._mx: self._jobs.append((fn, gata)); self._ev.set()
        return True

    def _sondaj(self):
        try:
            while True:
                tip, a, b, ex = self._rez.get_nowait()
                if tip == "gata":
                    self.ocupat = False; self.pb.stop(); self.pb.pack_forget(); self.root.config(cursor="")
                    if ex: messagebox.showerror(NUME, str(ex), parent=self.root); self.stare("Eroare: " + str(ex).split("\n")[0])
                    elif a: a(b)
                    else: self.stare_pag()
                elif tip == "render" and a[0] == self.ver and a[1] == self.pag:
                    self._arata_randare(a, b)
                elif tip == "thumb":
                    if a[0] == "d" and a[1] == self.ver: self._arata_thumb(a[2], b)
                    elif a[0] == "s" and a[1] == self.src_ver: self._arata_thumb_s(a[2], b)
                elif tip == "combina":
                    self._primeste_combina(a)
                elif tip == "deschide":
                    self.root.deiconify(); self.root.lift(); self.deschide(a)
        except queue.Empty:
            pass
        self.root.after(40, self._sondaj)

    def _dupa_doc(self):
        """(în firul de lucru) după orice modificare a documentului"""
        self.dims = [(p.rect.width, p.rect.height) for p in self.doc] if self.doc else []
        self.ver += 1

    # ======================= deschidere / salvare =======================
    def _intreaba_salvare(self, continua):
        """dacă sunt modificări: Da = salvează și apoi continuă, Nu = continuă fără salvare, Anulează = nimic"""
        if self.doc is None or (not self.modificat and not any(self.over.values())): continua(); return
        r = messagebox.askyesnocancel(NUME, "Documentul are modificări nesalvate. Salvezi?", parent=self.root)
        if r is None: return
        if r: self.salveaza(dupa=continua)
        else: continua()

    def deschide_dialog(self):
        f = filedialog.askopenfilenames(parent=self.root, title="Deschide", filetypes=TIPURI)
        if not f: return
        if len(f) > 1: self.combina_dialog(list(f)); return
        self.deschide(f[0])

    def deschide(self, cale):
        self._intreaba_salvare(lambda: self._deschide(cale))

    def _deschide(self, cale):
        def fn():
            d = deschide_pdf(cale)
            if d.needs_pass: return ("parola", d)
            return ("ok", d)
        self.lucru(fn, lambda r: self._deschis(r, cale), "Se deschide " + os.path.basename(cale) + "…")

    def _deschis(self, r, cale, parola=None):
        st, d = r
        if st == "parola":
            from tkinter import simpledialog
            p = simpledialog.askstring(NUME, "PDF protejat. Parola:", show="*", parent=self.root)
            if not p or not d.authenticate(p): messagebox.showerror(NUME, "Parolă greșită.", parent=self.root); d.close(); return
        ext = os.path.splitext(cale)[1].lower()
        self._recent(cale); self._incarca(d, cale if ext == ".pdf" else None, os.path.basename(cale), modificat=ext != ".pdf")
        if ext != ".pdf": self.stare(f"{os.path.basename(cale)} a fost convertit în PDF – salvează-l cu Ctrl+S.")

    def _incarca(self, d, cale, titlu, modificat=False):
        def fn():
            if self.doc is not None and self.doc is not d:
                try: self.doc.close()
                except Exception: pass
            self.doc = d; self._dupa_doc()
        self._dupa_incarcare = (cale, titlu, modificat)
        with self._mx: self._jobs.insert(0, (fn, lambda _: self._incarcat())); self._ev.set()
        self.ocupat = True

    def _incarcat(self):
        self.cale, titlu, self.modificat = self._dupa_incarcare
        self.root.title(f"{titlu} – {NUME}"); self.titlu = titlu
        self.over = {}; self.undo = []; self.redo = []; self.sel = None; self.pag = 0; self.sel_pag = {0}
        self.pe_pagina(); self._reface_thumbs()

    def _cu_completari(self, op, gata, mesaj, undo=True):
        """op() modifică documentul; înainte se scriu completările în pagini și se păstrează o copie pentru Anulează"""
        over = copy.deepcopy(self.over); img = dict(self.imagini); pag = self.pag
        def fn():
            snap = None
            if undo:
                snap = tmp(); self.doc.save(snap)
            aplica(self.doc, over, img); r = op(); self._dupa_doc(); return (snap, over, pag, r)
        def g(res):
            snap, ov, pg, r = res
            if undo: self._pune_undo(("doc", snap, ov, pg)); self.redo = []
            self.over = {}; self.sel = None; self.modificat = True
            gata(r)
        return self.lucru(fn, g, mesaj)

    def salveaza(self, ca=False, dupa=None):
        if self.doc is None: return
        cale = self.cale
        if ca or not cale:
            cale = filedialog.asksaveasfilename(parent=self.root, title="Salvează ca", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                                initialfile=os.path.splitext(getattr(self, "titlu", "Document"))[0] + ".pdf")
            if not cale: return
        def op(): salveaza(self.doc, cale)
        def g(_):
            self.cale = cale; self.modificat = False; self.titlu = os.path.basename(cale); self._recent(cale)
            self.root.title(f"{self.titlu} – {NUME}"); self.undo = [x for x in self.undo if x[0] == "doc"]; self.redo = []
            self._reface_thumbs(); self._pagina_noua_afis(sus=False); self.stare("✔ Salvat: " + cale)
            if dupa: dupa()
        self._cu_completari(op, g, "Se salvează…", undo=False)

    def imprima(self):
        if self.doc is None: return
        if sys.platform != "win32": messagebox.showinfo(NUME, "Imprimarea merge pe Windows.", parent=self.root); return
        over = copy.deepcopy(self.over); img = dict(self.imagini)
        def fn():                                          # copie separată: documentul rămâne editabil
            t = tmp(); self.doc.save(t); d = fitz.open(t); aplica(d, over, img); t2 = tmp(); d.save(t2); d.close(); return t2
        def g(t):
            try: os.startfile(t, "print"); self.stare("Trimis la imprimantă (prin programul PDF implicit din Windows).")
            except Exception as ex: messagebox.showerror(NUME, f"Nu pot imprima: {ex}", parent=self.root)
        self.lucru(fn, g, "Se pregătește imprimarea…")

    def iesire(self):
        if self.ocupat and not messagebox.askyesno(NUME, "O operație este în lucru. Închizi oricum?", parent=self.root): return
        scr_cfg(sesiune=[self.cale] if self.cale else [])
        self._intreaba_salvare(self.root.destroy)

    # ======================= meniul Fișier (ca în programele PDF obișnuite) =======================
    def _meniu_fisier(self):
        f = self.m_fis; f.delete(0, "end"); are = self.doc is not None
        st = lambda c: "normal" if c else "disabled"
        f.add_command(label="Deschide…", accelerator="Ctrl+O", command=self.deschide_dialog)
        ses = [x for x in cit_cfg().get("sesiune", []) if os.path.exists(x)]
        f.add_command(label="Redeschide PDF-urile din ultima sesiune", state=st(ses), command=lambda: self.deschide(ses[0]) if len(ses) == 1 else self.combina_dialog(ses))
        f.add_command(label="Combină fișiere…", command=lambda: self.combina_dialog([]))
        f.add_separator()
        f.add_command(label="Salvează", accelerator="Ctrl+S", state=st(are), command=self.salveaza)
        f.add_command(label="Salvează ca…", accelerator="Shift+Ctrl+S", state=st(are), command=lambda: self.salveaza(ca=True))
        alt = tk.Menu(f, tearoff=0)
        alt.add_command(label="Word (.docx)…", command=lambda: self.exporta("docx"))
        alt.add_command(label="Imagini PNG (câte una pe pagină)…", command=lambda: self.exporta("png"))
        alt.add_command(label="Imagini JPG (câte una pe pagină)…", command=lambda: self.exporta("jpg"))
        alt.add_command(label="Text (.txt)…", command=lambda: self.exporta("txt"))
        alt.add_command(label="PDF micșorat (dimensiune redusă)…", command=lambda: self.exporta("mic"))
        f.add_cascade(label="Salvează în alt format", menu=alt, state=st(are))
        f.add_separator()
        f.add_command(label="Revino la versiunea salvată", state=st(are and self.cale), command=self.revino)
        f.add_command(label="Închide fișierul", accelerator="Ctrl+W", state=st(are), command=self.inchide)
        f.add_separator()
        f.add_command(label="Proprietăți…", accelerator="Ctrl+D", state=st(are), command=self.proprietati)
        f.add_separator()
        f.add_command(label="Imprimă…", accelerator="Ctrl+P", state=st(are), command=self.imprima)
        f.add_separator()
        rec = [x for x in cit_cfg().get("recente", []) if os.path.exists(x)]
        for k, x in enumerate(rec[:5]):
            n = x if len(x) < 55 else x[:3] + "…" + x[-50:]
            f.add_command(label=f"{k + 1}  {n}", underline=0, command=lambda x=x: self.deschide(x))
        f.add_command(label="Toate fișierele recente…", state=st(rec), command=self.toate_recente)
        f.add_separator()
        f.add_command(label="Adaugă în meniul click-dreapta din Windows", command=lambda: self.meniu_windows(True))
        f.add_command(label="Elimină din meniul click-dreapta", command=lambda: self.meniu_windows(False))
        f.add_separator()
        f.add_command(label="Ieșire", accelerator="Ctrl+Q", command=self.iesire)

    def _recent(self, cale):
        if not cale: return
        r = [cale] + [x for x in cit_cfg().get("recente", []) if os.path.normcase(x) != os.path.normcase(cale)]
        scr_cfg(recente=r[:30])

    def toate_recente(self):
        d = tk.Toplevel(self.root); d.title("Fișiere recente"); d.transient(self.root); d.geometry("700x400")
        lb = tk.Listbox(d, font=("Segoe UI", 10)); lb.pack(fill="both", expand=True, padx=8, pady=8)
        rec = [x for x in cit_cfg().get("recente", []) if os.path.exists(x)]
        for x in rec: lb.insert("end", x)
        def ok(_=None):
            s_ = lb.curselection()
            if s_: d.destroy(); self.deschide(rec[s_[0]])
        lb.bind("<Double-1>", ok); ttk.Button(d, text="Deschide", command=ok).pack(pady=(0, 8))

    def revino(self):
        if not self.cale: return
        if (self.modificat or any(self.over.values())) and not messagebox.askyesno(NUME, "Renunți la toate modificările nesalvate?", parent=self.root): return
        self.modificat = False; self.over = {}; self._deschide(self.cale)

    def inchide(self):
        if self.doc is None: return
        def fa():
            def fn():
                try: self.doc.close()
                except Exception: pass
                self.doc = None; self._dupa_doc()
            def g(_):
                self.cale = None; self.modificat = False; self.over = {}; self.undo = []; self.redo = []; self.sel = None
                self.cv.delete("all"); self.cv_t.delete("all"); self._t_poz = []; self.root.title(NUME)
                self.e_pag.delete(0, "end"); self.l_nr.config(text="/ 0"); self.stare("Fișier închis.")
            self.lucru(fn, g, "Se închide…")
        self._intreaba_salvare(fa)

    def proprietati(self):
        if self.doc is None: return
        def fn():
            md = dict(self.doc.metadata or {}); n = len(self.doc)
            fm = {}
            for w, h in self.dims: k = nume_format(w, h).split(" (")[0]; fm[k] = fm.get(k, 0) + 1
            return md, n, fm
        def g(r):
            md, n, fm = r
            d = tk.Toplevel(self.root); d.title("Proprietăți document"); d.transient(self.root); d.grab_set(); d.resizable(False, False)
            fr = ttk.Frame(d, padding=12); fr.pack()
            inf = [("Fișier", self.cale or "(nesalvat)"), ("Mărime", f"{os.path.getsize(self.cale) / 1048576:.2f} MB" if self.cale and os.path.exists(self.cale) else "–"),
                   ("Pagini", str(n)), ("Formate", ", ".join(f"{k}: {v}" for k, v in fm.items())), ("Versiune PDF", md.get("format", "")),
                   ("Creat cu", md.get("creator", "")), ("Produs de", md.get("producer", "")), ("Creat la", md.get("creationDate", "")), ("Modificat la", md.get("modDate", ""))]
            for k, (a, b) in enumerate(inf):
                ttk.Label(fr, text=a + ":", foreground="#555").grid(row=k, column=0, sticky="ne", padx=(0, 8), pady=1)
                ttk.Label(fr, text=b, wraplength=420).grid(row=k, column=1, sticky="w", pady=1)
            ed = {}
            for j, (cheie, et) in enumerate((("title", "Titlu"), ("author", "Autor"), ("subject", "Subiect"), ("keywords", "Cuvinte cheie"))):
                ttk.Label(fr, text=et + ":").grid(row=len(inf) + j, column=0, sticky="e", padx=(0, 8), pady=2)
                e = ttk.Entry(fr, width=55); e.insert(0, md.get(cheie, "") or ""); e.grid(row=len(inf) + j, column=1, sticky="w", pady=2); ed[cheie] = e
            def ok():
                nou = {k: e.get() for k, e in ed.items()}; d.destroy()
                if any((md.get(k) or "") != v for k, v in nou.items()):
                    def fn2():
                        m2 = dict(self.doc.metadata or {}); m2.update(nou); self.doc.set_metadata({k: v for k, v in m2.items() if k in ("title", "author", "subject", "keywords", "creator", "producer", "creationDate", "modDate")})
                    def g2(_): self.modificat = True; self.stare_pag()
                    self.lucru(fn2, g2, "Se salvează proprietățile…")
            b = ttk.Frame(fr); b.grid(row=99, column=0, columnspan=2, pady=(10, 0))
            ttk.Button(b, text="OK", command=ok).pack(side="left", padx=4); ttk.Button(b, text="Anulează", command=d.destroy).pack(side="left")
        self.lucru(fn, g, "Se citesc proprietățile…")

    def exporta(self, tip):
        if self.doc is None: return
        baza = os.path.splitext(getattr(self, "titlu", "Document"))[0]
        if tip in ("png", "jpg"):
            dest = filedialog.askdirectory(parent=self.root, title="Folderul pentru imagini")
        else:
            ext = {"docx": ".docx", "txt": ".txt", "mic": ".pdf"}[tip]
            dest = filedialog.asksaveasfilename(parent=self.root, defaultextension=ext, initialfile=baza + ("_mic" if tip == "mic" else "") + ext,
                                                filetypes=[({"docx": "Word", "txt": "Text", "mic": "PDF"}[tip], "*" + ext)])
        if not dest: return
        over = copy.deepcopy(self.over); img = dict(self.imagini)
        def fn():
            t = tmp(); self.doc.save(t); d = fitz.open(t); aplica(d, over, img)
            try:
                if tip in ("png", "jpg"):
                    for k, p in enumerate(d):
                        z = min(150 / 72, 9000 / max(p.rect.width, p.rect.height))       # A0 limitat la ~9000 px, ca să nu umple memoria
                        pix = p.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False)
                        pix.save(os.path.join(dest, f"{baza}_pagina_{k + 1:03d}.{tip}")); del pix
                    return f"{len(d)} imagini în {dest}"
                if tip == "txt":
                    open(dest, "w", encoding="utf-8").write("\n\f".join(p.get_text() for p in d)); return dest
                if tip == "mic":
                    try: d.rewrite_images(dpi_threshold=160, dpi_target=150, quality=75)
                    except Exception: pass
                    t2 = tmp(); d.save(t2, garbage=4, deflate=True, clean=True); shutil.move(t2, dest)
                    return f"{dest}  ({os.path.getsize(dest) / 1048576:.1f} MB)"
                t3 = tmp(); d.save(t3); d.close(); d = None
                pdf_in_word(t3, dest); return dest
            finally:
                if d is not None: d.close()
        self.lucru(fn, lambda r: self.stare("✔ Salvat: " + r), "Se salvează în alt format…")

    # ======================= pagini =======================
    def _pagini_sel(self):
        return sorted(p for p in self.sel_pag if p < len(self.dims)) or [self.pag]

    def _dupa_pagini(self, pag):
        self.pag = max(0, min(pag, len(self.dims) - 1)); self.sel_pag = {self.pag}
        self._reface_thumbs(); self._pagina_noua_afis()

    def dlg_format(self, titlu, cu_nr=False, cu_pozitie=False):
        d = tk.Toplevel(self.root); d.title(titlu); d.transient(self.root); d.grab_set(); d.resizable(False, False)
        fr = ttk.Frame(d, padding=12); fr.pack()
        v_f = tk.StringVar(value=cit_cfg().get("format", "A4")); v_o = tk.StringVar(value="Vertical"); v_n = tk.IntVar(value=1); v_p = tk.StringVar(value="După pagina curentă")
        ttk.Label(fr, text="Format:").grid(row=0, column=0, sticky="w", pady=3)
        cf = ttk.Frame(fr); cf.grid(row=0, column=1, sticky="w")
        for k in FORMATE: ttk.Radiobutton(cf, text=k, value=k, variable=v_f).pack(side="left", padx=3)
        ttk.Label(fr, text="Orientare:").grid(row=1, column=0, sticky="w", pady=3)
        co = ttk.Frame(fr); co.grid(row=1, column=1, sticky="w")
        for k in (["Automat"] if not cu_nr else []) + ["Vertical", "Orizontal"]: ttk.Radiobutton(co, text=k, value=k, variable=v_o).pack(side="left", padx=3)
        if not cu_nr: v_o.set("Automat")
        l = ttk.Label(fr, foreground="#555"); l.grid(row=2, column=1, sticky="w")
        def info(*_):
            w, h = FORMATE[v_f.get()]; l.config(text=f"{v_f.get()}: {w} × {h} mm")
        v_f.trace_add("write", info); info()
        if cu_nr:
            ttk.Label(fr, text="Număr pagini:").grid(row=3, column=0, sticky="w", pady=3)
            ttk.Spinbox(fr, from_=1, to=500, textvariable=v_n, width=6).grid(row=3, column=1, sticky="w")
        if cu_pozitie:
            ttk.Label(fr, text="Unde:").grid(row=4, column=0, sticky="w", pady=3)
            ttk.Combobox(fr, textvariable=v_p, state="readonly", values=["După pagina curentă", "Înainte de pagina curentă", "La început", "La sfârșit"], width=26).grid(row=4, column=1, sticky="w")
        rez = {}
        def ok():
            rez.update(f=v_f.get(), o=v_o.get(), n=max(1, v_n.get()), p=v_p.get()); scr_cfg(format=v_f.get()); d.destroy()
        bb = ttk.Frame(fr); bb.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(bb, text="OK", command=ok).pack(side="left", padx=4); ttk.Button(bb, text="Anulează", command=d.destroy).pack(side="left")
        d.bind("<Return>", lambda e: ok()); d.wait_window(); return rez

    def _pozitie(self, p):
        n = len(self.dims)
        return {"După pagina curentă": self.pag + 1, "Înainte de pagina curentă": self.pag, "La început": 0}.get(p, n) if n else 0

    def pagina_noua(self):
        r = self.dlg_format("Pagină nouă", cu_nr=True, cu_pozitie=self.doc is not None)
        if not r: return
        W, H = dim_pt(r["f"], r["o"] == "Orizontal")
        if self.doc is None:
            d = fitz.open()
            for k in range(r["n"]): d.new_page(width=W, height=H)
            self._incarca(d, None, "Document nou.pdf", True); return
        poz = self._pozitie(r["p"])
        def op():
            for k in range(r["n"]): self.doc.new_page(poz + k, width=W, height=H)
        self._cu_completari(op, lambda _: (self._dupa_pagini(poz), self.stare(f"Adăugat {r['n']} pagini {r['f']}.")), "Se adaugă pagini…")

    def insereaza_dialog(self):
        f = filedialog.askopenfilenames(parent=self.root, title="Inserează pagini din", filetypes=TIPURI)
        if f:
            if self.doc is None: self.insereaza(list(f))
            else: self.deschide_sursa(list(f))

    def insereaza(self, fisiere, poz=None):
        if self.doc is None:
            if len(fisiere) == 1: self.deschide(fisiere[0])
            else: self.combina_dialog(fisiere)
            return
        poz = self.pag + 1 if poz is None else poz
        def op():
            n0 = len(self.doc); p = poz
            for f in fisiere:
                s = deschide_pdf(f)
                if s.needs_pass and not s.authenticate(""): raise RuntimeError("PDF protejat cu parolă: " + os.path.basename(f))
                self.doc.insert_pdf(s, start_at=p); p += len(s); s.close()
            return len(self.doc) - n0
        self._cu_completari(op, lambda n: (self._dupa_pagini(poz), self.stare(f"Inserat {n} pagini.")), "Se inserează (conversie în PDF dacă e nevoie)…")

    def format_dialog(self):
        if self.doc is None: return
        ps = self._pagini_sel()
        r = self.dlg_format(f"Formatul paginilor ({len(ps)} selectate)")
        if not r: return
        if len(ps) == 1 and len(self.dims) > 1 and messagebox.askyesno(NUME, "Aplici formatul la toate paginile?", parent=self.root): ps = list(range(len(self.dims)))
        self._cu_completari(lambda: schimba_format(self.doc, ps, r["f"], r["o"]), lambda _: self._dupa_pagini(self.pag), f"Se trec paginile pe {r['f']}…")

    def duplica(self):
        if self.doc is None: return
        p = self.pag
        self._cu_completari(lambda: self.doc.fullcopy_page(p, p + 1), lambda _: self._dupa_pagini(p + 1), "Se duplică…")

    def extrage(self):
        if self.doc is None: return
        ps = self._pagini_sel()
        cale = filedialog.asksaveasfilename(parent=self.root, defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], title=f"Extrage {len(ps)} pagini în")
        if not cale: return
        def op():
            n = fitz.open()
            for p in ps: n.insert_pdf(self.doc, from_page=p, to_page=p)
            salveaza(n, cale); n.close()
        self._cu_completari(op, lambda _: (self._reface_thumbs(), self._pagina_noua_afis(), self.stare("✔ Extras în " + cale)), "Se extrag paginile…")

    def roteste(self, unghi):
        if self.doc is None: return
        ps = self._pagini_sel()
        def op():
            for p in ps: pg = self.doc[p]; pg.set_rotation((pg.rotation + unghi) % 360)
        self._cu_completari(op, lambda _: (self._reface_thumbs(), self._pagina_noua_afis()), "Se rotește…")

    def muta(self, d, la=None):
        if self.doc is None: return
        p = self.pag; t = (p + d) if la is None else la
        if t < 0 or t >= len(self.dims) or t == p: return
        def op(): self.doc.move_page(p, t if t < p else (t + 1 if t + 1 < len(self.doc) else -1))
        self._cu_completari(op, lambda _: self._dupa_pagini(t), "Se mută pagina…")

    def sterge_pagini(self):
        if self.doc is None or self._focus_text(): return
        ps = self._pagini_sel()
        if len(ps) >= len(self.dims): messagebox.showinfo(NUME, "Documentul trebuie să păstreze cel puțin o pagină.", parent=self.root); return
        if not messagebox.askyesno(NUME, f"Ștergi {len(ps)} pagini ({', '.join(str(p + 1) for p in ps[:10])}{'…' if len(ps) > 10 else ''})?", parent=self.root): return
        self._cu_completari(lambda: self.doc.delete_pages(ps), lambda _: self._dupa_pagini(min(ps)), "Se șterg paginile…")

    # ======================= anulare =======================
    def _pune_undo(self, x, lista=None):
        (self.undo if lista is None else lista).append(x)
        if len(self.undo) > 40: self.undo.pop(0)
        while sum(1 for u in self.undo if u[0] == "doc") > 8:
            k = next(i for i, u in enumerate(self.undo) if u[0] == "doc"); del self.undo[:k + 1]

    def _salv_ov(self):
        self._pune_undo(("ov", copy.deepcopy(self.over), self.pag)); self.redo = []

    def anuleaza(self, din=None, spre=None):
        if self._focus_text() and din is None: return
        din = self.undo if din is None else din; spre = self.redo if spre is None else spre
        if not din or self.doc is None or self.ocupat: return
        u = din.pop()
        if u[0] == "ov":
            spre.append(("ov", copy.deepcopy(self.over), self.pag)); self.over = u[1]; self.sel = None
            if u[2] != self.pag: self.mergi(u[2])
            else: self._deseneaza_ov()
            return
        _, snap, ov, pg = u
        over_acum = copy.deepcopy(self.over)
        def fn():
            s2 = tmp(); self.doc.save(s2); aplicat_acum = over_acum
            self.doc.close(); self.doc = fitz.open(snap); self._dupa_doc(); return (s2, aplicat_acum)
        def g(r):
            spre.append(("doc", r[0], r[1], self.pag)); self.over = ov; self.sel = None; self.modificat = True
            self._dupa_pagini(pg)
        self.lucru(fn, g, "Se anulează…")

    def reface(self):
        if self._focus_text(): return
        self.anuleaza(self.redo, self.undo)

    # ======================= afișare =======================
    def stare(self, t): self.status.config(text=t)

    def stare_pag(self):
        if not self.dims: return
        w, h = self.dims[self.pag]
        self.stare(f"Pagina {self.pag + 1} din {len(self.dims)}  ·  {nume_format(w, h)}  ·  {self.z * 72 / 96 * 100:.0f}%"
                   + ("  ·  modificat" if self.modificat or any(self.over.values()) else ""))

    def mergi(self, p):
        if not self.dims: return
        p = max(0, min(p, len(self.dims) - 1))
        if p != self.pag: self.sel = None
        self.pag = p; self.sel_pag = {p}; self._pagina_noua_afis(); self._marcheaza_thumbs(vezi=True)

    def _mergi_text(self):
        try: self.mergi(int(self.e_pag.get()) - 1)
        except ValueError: pass

    def _pagina_noua_afis(self, sus=True):
        if not self.dims: return
        w, h = self.dims[self.pag]; z = self.z
        self.cv.delete("all"); self._img = None; self.render_ok = None
        self.cv.create_rectangle(OX + 4, OY + 4, OX + w * z + 4, OY + h * z + 4, fill="#5c6066", outline="")
        self.cv.create_rectangle(OX, OY, OX + w * z, OY + h * z, fill="white", outline="#444", tags="foaie")
        self.cv.config(scrollregion=(0, 0, w * z + 2 * OX, h * z + 2 * OY))
        if sus: self.cv.yview_moveto(0)
        self.e_pag.delete(0, "end"); self.e_pag.insert(0, str(self.pag + 1)); self.l_nr.config(text=f"/ {len(self.dims)}")
        self.cb_zoom.set(f"{z * 72 / 96 * 100:.0f}%")
        self._deseneaza_ov(); self._cere_render(); self.stare_pag()

    def _vizibil(self):
        """zona de pagină vizibilă, în puncte PDF"""
        w, h = self.dims[self.pag]; z = self.z
        x0, y0 = self.cv.canvasx(0), self.cv.canvasy(0); x1, y1 = x0 + self.cv.winfo_width(), y0 + self.cv.winfo_height()
        r = fitz.Rect((x0 - OX) / z, (y0 - OY) / z, (x1 - OX) / z, (y1 - OY) / z) & fitz.Rect(0, 0, w, h)
        return r

    def _cere_render(self):
        if getattr(self, "_job_r", None): self.root.after_cancel(self._job_r)
        self._job_r = self.root.after(60, self._cere_render_acum)

    def _cere_render_acum(self):
        self._job_r = None
        if not self.dims: return
        v = self._vizibil()
        if v.is_empty: return
        ok = self.render_ok
        if ok and ok[0] == self.ver and ok[1] == self.pag and abs(ok[2] - self.z) < 1e-9 and fitz.Rect(ok[3]).contains(v): return
        w, h = self.dims[self.pag]; mx, my = v.width * 0.5, v.height * 0.5     # margine, ca derularea să nu ceară imediat altă randare
        clip = fitz.Rect(v.x0 - mx, v.y0 - my, v.x1 + mx, v.y1 + my) & fitz.Rect(0, 0, w, h)
        with self._mx: self._render_cer = (self.ver, self.pag, self.z, clip); self._ev.set()

    def _arata_randare(self, cheie, im):
        if abs(cheie[2] - self.z) > 1e-9: return
        self.render_ok = cheie; z = self.z; c = cheie[3]
        self._img = ImageTk.PhotoImage(im)
        self.cv.delete("randare")
        self.cv.create_image(OX + c[0] * z, OY + c[1] * z, image=self._img, anchor="nw", tags="randare")
        self.cv.tag_raise("randare", "foaie"); self.cv.tag_raise("ov")
        self._cere_render()

    def zoom_la(self, z, centru=None):
        if not self.dims: return
        w, h = self.dims[self.pag]
        z = max(0.1, min(z, 12.0, 30000 / max(w, h)))
        fx = fy = None
        if centru:
            cx, cy = self.cv.canvasx(centru[0]), self.cv.canvasy(centru[1]); px, py = (cx - OX) / self.z, (cy - OY) / self.z
        self.z = z; self._pagina_noua_afis(sus=False)
        if centru:
            W, H = w * z + 2 * OX, h * z + 2 * OY
            self.cv.xview_moveto(max(0, (OX + px * z - centru[0]) / W)); self.cv.yview_moveto(max(0, (OY + py * z - centru[1]) / H))

    def zoom(self, f, centru=None): self.zoom_la(self.z * f, centru)

    def pe_latime(self):
        if self.dims: self.zoom_la((max(200, self.cv.winfo_width()) - 2 * OX - 4) / self.dims[self.pag][0])

    def pe_pagina(self):
        if not self.dims: return
        w, h = self.dims[self.pag]; self.root.update_idletasks()
        self.zoom_la(min((max(200, self.cv.winfo_width()) - 2 * OX) / w, (max(200, self.cv.winfo_height()) - 2 * OY) / h))

    def _zoom_text(self):
        t = self.cb_zoom.get().strip()
        if t.startswith("Pe"): self.pe_latime()
        elif t.startswith("Pag"): self.pe_pagina()
        else:
            try: self.zoom_la(float(t.rstrip("%").replace(",", ".")) / 100 * 96 / 72)
            except ValueError: pass

    def _rotita(self, e, delta=None):
        d = delta if delta is not None else e.delta
        if e.state & 4: self.zoom(1.15 if d > 0 else 1 / 1.15, (e.x, e.y)); return
        a, b = self.cv.yview()
        if d < 0 and b >= 0.999 and self.pag < len(self.dims) - 1: self.mergi(self.pag + 1); return
        if d > 0 and a <= 0.001 and self.pag > 0: self.mergi(self.pag - 1); self.cv.yview_moveto(1); return
        self.cv.yview_scroll(-1 if d > 0 else 1, "units") if not (e.state & 1) else self.cv.xview_scroll(-1 if d > 0 else 1, "units")

    # ======================= miniaturi =======================
    def _reface_thumbs(self):
        self.thumbs = {}; self.cv_t.delete("all"); n = len(self.dims); self._t_poz = []
        y = 8
        for p in range(n):
            w, h = self.dims[p]; s = 120 / max(w, h); tw, th = w * s, h * s
            x = (165 - tw) / 2
            self.cv_t.create_rectangle(x - 3, y - 3, x + tw + 3, y + th + 3, outline="", fill="", tags=(f"cadru{p}", "cadru"))
            self.cv_t.create_rectangle(x, y, x + tw, y + th, fill="white", outline="#999", tags=f"t{p}")
            self.cv_t.create_text(82, y + th + 9, text=f"{p + 1}  ·  {nume_format(w, h).split(' (')[0]}", font=("Segoe UI", 8), tags=f"l{p}")
            self._t_poz.append((y, y + th + 18, x, tw, th)); y += th + 26
        self.cv_t.config(scrollregion=(0, 0, 165, y)); self._marcheaza_thumbs(); self._cere_thumbs()

    def _cere_thumbs(self):
        vrei = []
        for tip_, cv, poz, gata, ver in (("d", self.cv_t, self._t_poz, self.thumbs, self.ver), ("s", self.cv_s, self._s_poz, self.s_thumbs, self.src_ver)):
            if not poz or not cv.winfo_ismapped(): continue
            y0, y1 = cv.canvasy(0), cv.canvasy(cv.winfo_height())
            vrei += [(tip_, ver, p) for p, (a, b, *_ ) in enumerate(poz) if b >= y0 - 300 and a <= y1 + 300 and p not in gata]
        with self._mx: self._thumb_cer = vrei; self._ev.set()

    def _arata_thumb(self, p, im):
        if p >= len(self._t_poz): return
        y, _, x, tw, th = self._t_poz[p]; ph = ImageTk.PhotoImage(im.resize((max(1, int(tw)), max(1, int(th)))))
        self.thumbs[p] = ph; self.cv_t.create_image(x, y, image=ph, anchor="nw", tags=f"t{p}")

    def _marcheaza_thumbs(self, vezi=False):
        self.cv_t.itemconfig("cadru", fill="")
        for p in self.sel_pag: self.cv_t.itemconfig(f"cadru{p}", fill="#9cc3f5")
        if vezi and getattr(self, "_t_poz", None) and self.pag < len(self._t_poz):
            a, b, *_ = self._t_poz[self.pag]; tot = self._t_poz[-1][1] + 10; y0, y1 = self.cv_t.canvasy(0), self.cv_t.canvasy(self.cv_t.winfo_height())
            if a < y0 or b > y1: self.cv_t.yview_moveto(max(0, (a - 20) / tot))

    def _t_pag(self, e):
        y = self.cv_t.canvasy(e.y)
        for p, (a, b, *_ ) in enumerate(getattr(self, "_t_poz", [])):
            if a - 4 <= y <= b + 4: return p
        return None

    def _t_apasa(self, e):
        p = self._t_pag(e); self._t_drag = None
        if p is None: return
        if e.state & 4: self.sel_pag ^= {p}; self.sel_pag = self.sel_pag or {p}; self._marcheaza_thumbs(); return
        if e.state & 1: a, b = sorted((self.pag, p)); self.sel_pag = set(range(a, b + 1)); self._marcheaza_thumbs(); return
        self._t_drag = (p, e.y); self.mergi(p)

    def _t_trage(self, e):
        if self._t_drag and abs(e.y - self._t_drag[1]) > 8:
            self.cv_t.delete("linie_drag"); t = self._t_tinta(e)
            yy = self._t_poz[t][0] - 6 if t < len(self._t_poz) else self._t_poz[-1][1] + 4
            self.cv_t.create_line(10, yy, 160, yy, fill="#1a73e8", width=3, tags="linie_drag"); self.cv_t.config(cursor="sb_v_double_arrow")

    def _t_tinta(self, e):
        y = self.cv_t.canvasy(e.y)
        for p, (a, b, *_ ) in enumerate(self._t_poz):
            if y < (a + b) / 2: return p
        return len(self._t_poz)

    def _t_elib(self, e):
        self.cv_t.delete("linie_drag"); self.cv_t.config(cursor="")
        if self._t_drag and abs(e.y - self._t_drag[1]) > 8:
            p = self._t_drag[0]; t = self._t_tinta(e); dest = t if t < p else t - 1
            if dest != p: self.muta(0, la=dest)
        self._t_drag = None

    def _t_meniu(self, e):
        p = self._t_pag(e)
        if p is None or self.doc is None: return
        if p not in self.sel_pag: self.mergi(p)
        n = len(self._pagini_sel()); t = f"  ({n} pagini)" if n > 1 else ""
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label="Rotește la dreapta 90°" + t, command=lambda: self.roteste(90))
        m.add_command(label="Rotește la stânga 90°" + t, command=lambda: self.roteste(-90))
        m.add_command(label="Rotește 180°" + t, command=lambda: self.roteste(180))
        m.add_separator()
        m.add_command(label="Șterge" + t, command=self.sterge_pagini)
        m.add_command(label="Duplică pagina", command=self.duplica)
        m.add_command(label="Extrage" + t + "…", command=self.extrage)
        m.add_separator()
        m.add_command(label="Pagină nouă (A0…A5)…", command=self.pagina_noua)
        m.add_command(label="Inserează din fișier…", command=self.insereaza_dialog)
        m.add_command(label="Schimbă formatul" + t + "…", command=self.format_dialog)
        m.add_separator()
        m.add_command(label="Mută sus", command=lambda: self.muta(-1)); m.add_command(label="Mută jos", command=lambda: self.muta(1))
        m.tk_popup(e.x_root, e.y_root)

    def _cv_meniu(self, e):
        if not self.dims: return
        x, y = self._pt(e); k = self._gaseste(x, y); m = tk.Menu(self.root, tearoff=0)
        if k is not None:
            self._selecteaza(k); m.add_command(label="Șterge obiectul", command=self.sterge_obiect)
            o = self.over[self.pag][k]
            if o["t"] == "text": m.add_command(label="Editează textul", command=lambda: self._editeaza_text(o["r"][0], o["r"][1], o))
            m.add_separator()
        self.sel_pag = {self.pag}; self._marcheaza_thumbs()
        m.add_command(label="Rotește pagina la dreapta", command=lambda: self.roteste(90))
        m.add_command(label="Rotește pagina la stânga", command=lambda: self.roteste(-90))
        m.add_command(label="Șterge pagina", command=self.sterge_pagini)
        m.tk_popup(e.x_root, e.y_root)

    # ======================= coloana cu paginile fișierului adăugat =======================
    def deschide_sursa(self, fisiere):
        def fn():
            d = fitz.open()
            for f in fisiere:
                s_ = deschide_pdf(f)
                if s_.needs_pass and not s_.authenticate(""): raise RuntimeError("PDF protejat cu parolă: " + os.path.basename(f))
                d.insert_pdf(s_); s_.close()
            vechi = self.src; self.src = d; self.src_dims = [(p.rect.width, p.rect.height) for p in d]; self.src_ver += 1
            if vechi is not None:
                try: vechi.close()
                except Exception: pass
            return len(d)
        def g(n):
            self.src_nume = ", ".join(os.path.basename(f) for f in fisiere)
            self.l_src.config(text=(self.src_nume[:20] + "…") if len(self.src_nume) > 21 else self.src_nume)
            self.s_sel = set(); self._arata_sursa(True); self._reface_s()
            self.stare(f"{self.src_nume}: {n} pagini – trage paginile în coloana „Pagini” (Ctrl/Shift = mai multe), dublu clic = inserează după pagina curentă.")
        self.lucru(fn, g, "Se pregătesc paginile (conversie în PDF dacă e nevoie)…")

    def _arata_sursa(self, da):
        if da and not self.fr_s.winfo_ismapped(): self.fr_s.pack(side="left", fill="y", padx=(4, 0))
        if not da: self.fr_s.pack_forget()
        self.root.update_idletasks()
        try: self.pw.sashpos(0, 385 if da else 190)
        except Exception: pass

    def inchide_sursa(self):
        self._arata_sursa(False); self.cv_s.delete("all"); self._s_poz = []; self.s_thumbs = {}; self.s_sel = set()
        def fn():
            d = self.src; self.src = None; self.src_ver += 1
            if d is not None: d.close()
        with self._mx: self._jobs.append((fn, False)); self._ev.set()

    def _reface_s(self):
        cv = self.cv_s; cv.delete("all"); self.s_thumbs = {}; self._s_poz = []; y = 8
        for p, (w, h) in enumerate(self.src_dims):
            sc = 120 / max(w, h); tw, th = w * sc, h * sc; x = (165 - tw) / 2
            cv.create_rectangle(x - 4, y - 4, x + tw + 4, y + th + 4, outline="", fill="", width=2, tags=(f"cadru{p}", "cadru"))
            cv.create_rectangle(x, y, x + tw, y + th, fill="white", outline="#b9c2cf")
            cv.create_text(82, y + th + 10, text=f"{p + 1}  ·  {nume_format(w, h).split(' (')[0]}", font=("Segoe UI", 8), fill=TEMA["text2"])
            self._s_poz.append((y, y + th + 18, x, tw, th)); y += th + 28
        cv.config(scrollregion=(0, 0, 165, y)); cv.yview_moveto(0); self._marcheaza_s(); self.root.after(50, self._cere_thumbs)

    def _arata_thumb_s(self, p, im):
        if p >= len(self._s_poz): return
        y, _, x, tw, th = self._s_poz[p]; ph = ImageTk.PhotoImage(im.resize((max(1, int(tw)), max(1, int(th)))))
        self.s_thumbs[p] = ph; self.cv_s.create_image(x, y, image=ph, anchor="nw")

    def _marcheaza_s(self):
        self.cv_s.itemconfig("cadru", fill="", outline="")
        for p in self.s_sel: self.cv_s.itemconfig(f"cadru{p}", fill=TEMA["selectie"], outline=TEMA["accent"])

    def _s_pag(self, e):
        y = self.cv_s.canvasy(e.y)
        for p, (a, b, *_ ) in enumerate(self._s_poz):
            if a - 4 <= y <= b + 4: return p
        return None

    def _s_apasa(self, e):
        p = self._s_pag(e); self._s_drag = None
        if p is None: return
        if e.state & 4: self.s_sel ^= {p}
        elif e.state & 1 and self.s_sel: a, b = sorted((min(self.s_sel), p)); self.s_sel = set(range(a, b + 1))
        elif p not in self.s_sel: self.s_sel = {p}
        self._marcheaza_s(); self._s_drag = (p, e.x_root, e.y_root)

    def _tinta_t(self, y_root):
        if not self._t_poz: return 0
        y = self.cv_t.canvasy(y_root - self.cv_t.winfo_rooty())
        for p, (a, b, *_ ) in enumerate(self._t_poz):
            if y < (a + b) / 2: return p
        return len(self._t_poz)

    def _s_trage(self, e):
        if not self._s_drag or (abs(e.y_root - self._s_drag[2]) < 6 and abs(e.x_root - self._s_drag[1]) < 6): return
        n = len(self.s_sel) or 1; self.cv_t.delete("linie_drag"); self.cv_s.config(cursor="plus")
        w = self.root.winfo_containing(e.x_root, e.y_root)
        if w is self.cv_t:
            t = self._tinta_t(e.y_root)
            yy = (self._t_poz[t][0] - 8) if t < len(self._t_poz) else ((self._t_poz[-1][1] + 6) if self._t_poz else 6)
            self.cv_t.create_line(8, yy, 162, yy, fill=TEMA["accent"], width=4, tags="linie_drag")
            self.stare(f"Eliberează pentru a insera {n} pagini la poziția {t + 1}.")
        elif w is self.cv:
            self.stare(f"Eliberează pentru a insera {n} pagini după pagina {self.pag + 1}.")

    def _s_elib(self, e):
        self.cv_t.delete("linie_drag"); self.cv_s.config(cursor="")
        d = getattr(self, "_s_drag", None); self._s_drag = None
        if not d or (abs(e.y_root - d[2]) < 6 and abs(e.x_root - d[1]) < 6): return
        pag = sorted(self.s_sel) if d[0] in self.s_sel else [d[0]]
        w = self.root.winfo_containing(e.x_root, e.y_root)
        if w is self.cv_t: self.insereaza_din_sursa(pag, self._tinta_t(e.y_root))
        elif w is self.cv: self.insereaza_din_sursa(pag, self.pag + 1)
        else: self.stare_pag()

    def _s_dublu(self, e):
        p = self._s_pag(e)
        if p is not None: self.insereaza_din_sursa([p], None)

    def _s_meniu(self, e):
        p = self._s_pag(e)
        if p is None: return
        if p not in self.s_sel: self.s_sel = {p}; self._marcheaza_s()
        pag = sorted(self.s_sel); t = f"{len(pag)} pagini" if len(pag) > 1 else f"pagina {p + 1}"
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"Inserează {t} după pagina curentă", command=lambda: self.insereaza_din_sursa(pag, None))
        m.add_command(label=f"Inserează {t} la început", command=lambda: self.insereaza_din_sursa(pag, 0))
        m.add_command(label=f"Inserează {t} la sfârșit", command=lambda: self.insereaza_din_sursa(pag, len(self.dims)))
        m.add_separator()
        m.add_command(label="Selectează toate paginile", command=lambda: (setattr(self, "s_sel", set(range(len(self.src_dims)))), self._marcheaza_s()))
        m.add_command(label="Închide coloana", command=self.inchide_sursa)
        m.tk_popup(e.x_root, e.y_root)

    def insereaza_din_sursa(self, pagini, poz):
        if self.doc is None or self.src is None: return
        pagini = list(range(len(self.src_dims))) if pagini is None else pagini
        poz = self.pag + 1 if poz is None else poz
        def op():
            for k, p in enumerate(pagini): self.doc.insert_pdf(self.src, from_page=p, to_page=p, start_at=poz + k)
            return len(pagini)
        self._cu_completari(op, lambda n: (self._dupa_pagini(poz), self.stare(f"✔ Inserat {n} pagini din {self.src_nume} la poziția {poz + 1}.")),
                            "Se inserează paginile…")

    # ======================= drag & drop din Explorer =======================
    def _drop(self, e, w):
        f = [x for x in self.root.tk.splitlist(e.data) if os.path.isfile(x)]
        f = [x for x in f if os.path.splitext(x)[1].lower() in EXT_TOATE]
        if not f: self.stare("Tip de fișier nesuportat."); return
        if self.doc is None:
            if len(f) == 1: self.deschide(f[0])
            else: self.combina_dialog(f)
            return
        self.deschide_sursa(f)                              # paginile apar în coloana alăturată; le tragi unde ai nevoie

    # ======================= completări pe pagină =======================
    def _pt(self, e):
        return (self.cv.canvasx(e.x) - OX) / self.z, (self.cv.canvasy(e.y) - OY) / self.z

    def _P(self, x, y): return OX + x * self.z, OY + y * self.z

    def _unealta_aleasa(self):
        u = self.unealta.get(); self._selecteaza(None)
        self.cv.config(cursor={"sel": "arrow", "text": "xterm"}.get(u, "crosshair"))
        if u == "img":
            f = filedialog.askopenfilename(parent=self.root, filetypes=[("Imagini", "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff")])
            if not f: self.unealta.set("sel"); return
            self._img_aleasa = self._incarca_img(open(f, "rb").read())
            self.stare("Clic pe pagină pentru a pune imaginea (sau trage un dreptunghi).")
        if u == "semn": self._meniu_semnatura()

    def _incarca_img(self, data):
        im = Image.open(io.BytesIO(data)); b = io.BytesIO(); im.save(b, "PNG"); data = b.getvalue()
        k = f"i{len(self.imagini)}_{hash(data) & 0xffff}"; self.imagini[k] = data; return k

    def alege_culoare(self):
        c = colorchooser.askcolor(self.culoare, parent=self.root)[1]
        if c: self.seteaza_culoare(c)

    def seteaza_culoare(self, c):
        self.culoare = c; self.b_col.config(fg=c)
        if self.sel and self.sel[0] == self.pag:
            self._salv_ov(); self._obiect()["c"] = c; self._deseneaza_ov()

    def _marime_schimbata(self):
        if self.sel and self.sel[0] == self.pag and self._obiect()["t"] == "text":
            self._salv_ov(); o = self._obiect(); o["s"] = float(self.marime.get()); masoara_text(o); self._deseneaza_ov()

    def _obiect(self): return self.over[self.sel[0]][self.sel[1]]

    def _selecteaza(self, k):
        self.sel = None if k is None else (self.pag, k); self._deseneaza_ov()

    def _deseneaza_ov(self):
        cv = self.cv; cv.delete("ov"); self._ovimg = []; z = self.z; P = self._P
        for k, o in enumerate(self.over.get(self.pag, [])):
            t = o["t"]; c = o.get("c", "#000"); x0, y0, x1, y1 = cutie(o); a, b = P(x0, y0); A, B = P(x1, y1)
            lw = max(1, o.get("s", 12) / 10 * z)
            if t == "text":
                cv.create_text(P(o["r"][0], o["r"][1]), text=o["txt"], anchor="nw", fill=c, font=("Arial", -max(1, int(round(o["s"] * z)))), tags="ov")
            elif t == "x": cv.create_line(a, b, A, B, fill=c, width=lw, tags="ov"); cv.create_line(a, B, A, b, fill=c, width=lw, tags="ov")
            elif t == "v": cv.create_line(a, b + (B - b) * .55, a + (A - a) * .38, B, A, b, fill=c, width=lw, tags="ov")
            elif t == "oval": cv.create_oval(a, b, A, B, outline=c, width=lw, tags="ov")
            elif t == "linie": r = o["r"]; cv.create_line(*P(r[0], r[1]), *P(r[2], r[3]), fill=c, width=lw, tags="ov")
            elif t == "punct": cv.create_oval(a, b, A, B, fill=c, outline=c, tags="ov")
            elif t == "drept": cv.create_rectangle(a, b, A, B, outline=c, width=lw, tags="ov")
            elif t == "alb": cv.create_rectangle(a, b, A, B, fill="white", outline="#bbb", dash=(2, 2), tags="ov")
            elif t == "evid": cv.create_rectangle(a, b, A, B, fill=c, outline="", stipple="gray50", tags="ov")
            elif t in ("img", "semn"):
                im = Image.open(io.BytesIO(self.imagini[o["img"]])).convert("RGBA").resize((max(1, int(A - a)), max(1, int(B - b))))
                ph = ImageTk.PhotoImage(im); self._ovimg.append(ph); cv.create_image(a, b, image=ph, anchor="nw", tags="ov")
            if self.sel == (self.pag, k):
                cv.create_rectangle(a - 3, b - 3, A + 3, B + 3, outline="#1a73e8", dash=(4, 2), tags="ov")
                cv.create_rectangle(A, B, A + 8, B + 8, fill="#1a73e8", outline="white", tags="ov")
        self.stare_pag()

    def _gaseste(self, x, y):
        tol = 4 / self.z
        for k in range(len(self.over.get(self.pag, [])) - 1, -1, -1):
            x0, y0, x1, y1 = cutie(self.over[self.pag][k])
            if x0 - tol <= x <= x1 + tol and y0 - tol <= y <= y1 + tol: return k
        return None

    def _apasa(self, e):
        self.cv.focus_set()
        if not self.dims: return
        x, y = self._pt(e); u = self.unealta.get(); self._drag = None
        if u == "sel":
            if self.sel and self.sel[0] == self.pag:
                X1, Y1 = cutie(self._obiect())[2:]
                if abs(x - X1) * self.z < 10 and abs(y - Y1) * self.z < 10:
                    self._salv_ov(); self._drag = ("marime", x, y, copy.deepcopy(self._obiect())); return
            k = self._gaseste(x, y); self._selecteaza(k)
            if k is not None:
                o = self._obiect()
                if o["t"] == "text": self.marime.set(o["s"])
                self._salv_ov(); self._drag = ("muta", x, y, copy.deepcopy(o))
            return
        s = float(self.marime.get())
        if u == "text": self._editeaza_text(x, y); return
        if u in ("x", "v", "punct"):
            d = s * (0.5 if u == "punct" else 0.85); self._adauga({"t": u, "r": [x - d / 2, y - d / 2, x + d / 2, y + d / 2], "c": self.culoare, "s": s}); return
        if u in ("img", "semn"):
            k = getattr(self, "_img_aleasa", None) if u == "img" else getattr(self, "_semn_k", None)
            if not k: return
            self._drag = ("nou", x, y, {"t": u, "img": k, "r": [x, y, x, y], "c": self.culoare, "s": s}); return
        self._drag = ("nou", x, y, {"t": u, "r": [x, y, x, y], "c": self.culoare, "s": s})

    def _trage(self, e):
        if not self._drag: return
        x, y = self._pt(e); tip, x0, y0, o0 = self._drag
        if tip == "nou":
            o0["r"][2], o0["r"][3] = x, y; self.cv.delete("tmp"); a, b = self._P(x0, y0); A, B = self._P(x, y)
            if o0["t"] == "linie": self.cv.create_line(a, b, A, B, fill=self.culoare, tags="tmp")
            elif o0["t"] == "oval": self.cv.create_oval(a, b, A, B, outline=self.culoare, tags="tmp")
            else: self.cv.create_rectangle(a, b, A, B, outline=self.culoare, dash=(3, 2), tags="tmp")
            return
        o = self._obiect(); dx, dy = x - x0, y - y0
        if tip == "muta":
            r = o0["r"]; o["r"] = [r[0] + dx, r[1] + dy, r[2] + dx, r[3] + dy]
        else:
            X0, Y0, X1, Y1 = cutie(o0)
            if o["t"] == "text":
                o["s"] = max(3, o0["s"] * max(0.1, (Y1 - Y0 + dy) / max(1e-6, Y1 - Y0))); masoara_text(o); self.marime.set(round(o["s"], 1))
            elif o["t"] in ("img", "semn") and not (e.state & 1):                 # proporțional (Shift = liber)
                f = max(0.05, (X1 - X0 + dx) / max(1e-6, X1 - X0)); o["r"] = [X0, Y0, X0 + (X1 - X0) * f, Y0 + (Y1 - Y0) * f]
            elif o["t"] == "linie": o["r"] = [o0["r"][0], o0["r"][1], o0["r"][2] + dx, o0["r"][3] + dy]
            else: o["r"] = [X0, Y0, max(X0 + 1, X1 + dx), max(Y0 + 1, Y1 + dy)]
        self._deseneaza_ov()

    def _elibereaza(self, e):
        if not self._drag: return
        tip, x0, y0, o = self._drag; o0 = o; self._drag = None; self.cv.delete("tmp")
        if tip != "nou":
            o = self._obiect() if self.sel else None
            if o and o["r"] == o0["r"] and o.get("s") == o0.get("s"): self.undo.pop()
            else: self.modificat = True
            self._deseneaza_ov(); return
        x, y = self._pt(e); mic = abs(x - x0) * self.z < 4 and abs(y - y0) * self.z < 4
        if o["t"] in ("img", "semn"):
            im = Image.open(io.BytesIO(self.imagini[o["img"]])); asp = im.height / max(1, im.width)
            if mic:
                w = 150 if o["t"] == "semn" else min(250, self.dims[self.pag][0] / 2); o["r"] = [x0, y0, x0 + w, y0 + w * asp]
            else:
                w = abs(x - x0); o["r"] = [min(x, x0), min(y, y0), min(x, x0) + w, min(y, y0) + w * asp]
        elif mic:
            if o["t"] == "linie": return
            d = 60; o["r"] = [x0, y0, x0 + d, y0 + (d if o["t"] == "oval" else 20)]
        self._adauga(o)
        if o["t"] == "img": self.unealta.set("sel"); self.cv.config(cursor="arrow")

    def _adauga(self, o):
        self._salv_ov(); self.over.setdefault(self.pag, []).append(o); self.modificat = True
        self.sel = (self.pag, len(self.over[self.pag]) - 1); self._deseneaza_ov()

    def _dublu(self, e):
        x, y = self._pt(e); k = self._gaseste(x, y)
        if k is not None and self.over[self.pag][k]["t"] == "text":
            self._selecteaza(k); o = self._obiect(); self._editeaza_text(o["r"][0], o["r"][1], o)

    def _editeaza_text(self, x, y, o=None):
        d = tk.Toplevel(self.root); d.title("Text"); d.transient(self.root); d.grab_set()
        d.geometry(f"+{self.root.winfo_pointerx() + 10}+{self.root.winfo_pointery() + 10}")
        t = tk.Text(d, width=46, height=5, font=("Arial", 11), wrap="none"); t.pack(padx=8, pady=(8, 4)); t.focus_set()
        if o: t.insert("1.0", o["txt"])
        def ok(_=None):
            s = t.get("1.0", "end-1c").rstrip(); d.destroy()
            if o is not None:
                self._salv_ov()
                if s: o["txt"] = s; masoara_text(o)
                else: self.over[self.pag].remove(o); self.sel = None
                self.modificat = True; self._deseneaza_ov()
            elif s:
                n = {"t": "text", "txt": s, "s": float(self.marime.get()), "c": self.culoare, "r": [x, y, x, y]}; masoara_text(n); self._adauga(n)
        f = ttk.Frame(d); f.pack(pady=(0, 8))
        ttk.Button(f, text="OK (Ctrl+Enter)", command=ok).pack(side="left", padx=4); ttk.Button(f, text="Anulează", command=d.destroy).pack(side="left")
        t.bind("<Control-Return>", ok); d.bind("<Escape>", lambda e: d.destroy())

    def sterge_obiect(self):
        if self.sel and self.sel[0] == self.pag:
            self._salv_ov(); del self.over[self.pag][self.sel[1]]; self.sel = None; self.modificat = True; self._deseneaza_ov()

    # ======================= semnătură =======================
    def _meniu_semnatura(self):
        m = tk.Menu(self.root, tearoff=0)
        if os.path.exists(SEMN): m.add_command(label="Folosește semnătura salvată", command=lambda: self._foloseste_semn(open(SEMN, "rb").read()))
        m.add_command(label="Desenează semnătura…", command=self._deseneaza_semn)
        m.add_command(label="Încarcă imagine cu semnătura…", command=self._incarca_semn)
        m.add_separator(); m.add_command(label="Anulează", command=lambda: self.unealta.set("sel"))
        m.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def _foloseste_semn(self, data):
        self._semn_k = self._incarca_img(data); self.unealta.set("semn"); self.cv.config(cursor="crosshair")
        self.stare("Clic pe pagină pentru a pune semnătura (o poți muta și mări după aceea).")

    def _incarca_semn(self):
        f = filedialog.askopenfilename(parent=self.root, filetypes=[("Imagini", "*.png *.jpg *.jpeg *.bmp")])
        if not f: self.unealta.set("sel"); return
        im = Image.open(f).convert("RGBA")
        px = im.load()                                       # fundalul alb devine transparent
        for yy in range(im.height):
            for xx in range(im.width):
                r, g, b, a = px[xx, yy]
                if r > 225 and g > 225 and b > 225: px[xx, yy] = (r, g, b, 0)
        b_ = io.BytesIO(); im.save(b_, "PNG"); data = b_.getvalue()
        try: open(SEMN, "wb").write(data)
        except Exception: pass
        self._foloseste_semn(data)

    def _deseneaza_semn(self):
        d = tk.Toplevel(self.root); d.title("Desenează semnătura"); d.transient(self.root); d.grab_set()
        c = tk.Canvas(d, width=560, height=220, bg="white", cursor="pencil"); c.pack(padx=10, pady=10)
        c.create_line(30, 170, 530, 170, fill="#ccc"); linii = []; cur = []
        def ap(e): cur.clear(); cur.append((e.x, e.y)); linii.append(cur.copy())
        def tr(e):
            c.create_line(cur[-1][0], cur[-1][1], e.x, e.y, width=3, fill=self.culoare, capstyle="round", smooth=True); cur.append((e.x, e.y)); linii[-1] = cur.copy()
        c.bind("<ButtonPress-1>", ap); c.bind("<B1-Motion>", tr)
        def gata():
            pts = [p for l in linii for p in l]
            if not pts: d.destroy(); self.unealta.set("sel"); return
            S = 3; im = Image.new("RGBA", (560 * S, 220 * S), (0, 0, 0, 0)); dr = ImageDraw.Draw(im)
            for l in linii:
                if len(l) > 1: dr.line([(x * S, y * S) for x, y in l], fill=self.culoare, width=3 * S, joint="curve")
            x0 = max(0, min(p[0] for p in pts) - 6) * S; y0 = max(0, min(p[1] for p in pts) - 6) * S
            x1 = (max(p[0] for p in pts) + 6) * S; y1 = (max(p[1] for p in pts) + 6) * S
            im = im.crop((x0, y0, x1, y1)); b_ = io.BytesIO(); im.save(b_, "PNG"); data = b_.getvalue()
            try: open(SEMN, "wb").write(data)
            except Exception: pass
            d.destroy(); self._foloseste_semn(data)
        f = ttk.Frame(d); f.pack(pady=(0, 10))
        ttk.Button(f, text="Șterge", command=lambda: (c.delete("all"), linii.clear())).pack(side="left", padx=4)
        ttk.Button(f, text="Folosește", command=gata).pack(side="left", padx=4)
        ttk.Button(f, text="Anulează", command=lambda: (d.destroy(), self.unealta.set("sel"))).pack(side="left")

    # ======================= combinare =======================
    def combina_dialog(self, fisiere):
        if self._dlg_comb and self._dlg_comb.winfo_exists():
            self._dlg_comb.adauga(fisiere); self._dlg_comb.lift(); return
        self._dlg_comb = DialogCombina(self, fisiere)

    def _primeste_combina(self, fisiere):
        self._combina_asteapta += fisiere
        if getattr(self, "_job_c", None): self.root.after_cancel(self._job_c)
        self._job_c = self.root.after(700, self._deschide_combina_asteptat)

    def _deschide_combina_asteptat(self):
        self._job_c = None; f = self._combina_asteapta; self._combina_asteapta = []
        self.root.deiconify(); self.root.lift(); self.root.attributes("-topmost", True); self.root.after(300, lambda: self.root.attributes("-topmost", False))
        self.combina_dialog(f)

    def asculta(self, srv):
        """alte porniri din meniul click-dreapta trimit fișierele aici (un singur program deschis)"""
        def run():
            while True:
                try:
                    c, _ = srv.accept(); data = b""
                    while True:
                        x = c.recv(65536)
                        if not x: break
                        data += x
                    c.close()
                    l = [x for x in data.decode("utf-8").split("\n") if x.strip()]
                    if l and l[0] == "O" and len(l) == 2: self._rez.put(("deschide", l[1], None, None))
                    elif l: self._rez.put(("combina", l[1:], None, None))
                except Exception:
                    pass
        threading.Thread(target=run, daemon=True).start()

    # ======================= meniu click-dreapta Windows =======================
    def meniu_windows(self, adauga):
        if sys.platform != "win32": messagebox.showinfo(NUME, "Doar pe Windows.", parent=self.root); return
        try:
            meniu_windows(adauga)
            messagebox.showinfo(NUME, ("Am adăugat în meniul click-dreapta:\n• „Combină fișierele în PDF PC…” (PDF, Word, Excel, PowerPoint, imagini)\n• „Deschide în PDF PC” (PDF)\n\n"
                                       "Pe Windows 11 apar la „Afișați mai multe opțiuni” (Shift+F10).") if adauga else "Am eliminat din meniul click-dreapta.", parent=self.root)
        except Exception as ex:
            messagebox.showerror(NUME, str(ex), parent=self.root)


def meniu_windows(adauga):
    import winreg
    exe = sys.executable if getattr(sys, "frozen", False) else f'{sys.executable}" "{os.path.abspath(__file__)}'
    H = winreg.HKEY_CURRENT_USER
    def sterge(k):
        try:
            with winreg.OpenKey(H, k) as h:
                while True:
                    try: s = winreg.EnumKey(h, 0)
                    except OSError: break
                    sterge(k + "\\" + s)
            winreg.DeleteKey(H, k)
        except OSError: pass
    for ext in sorted(EXT_TOATE):
        for verb, text, cmd in (("PDFPC_Combina", "Combină fișierele în PDF PC…", f'"{exe}" --combina "%1"'),
                                ("PDFPC_Deschide", "Deschide în PDF PC", f'"{exe}" "%1"')):
            if verb == "PDFPC_Deschide" and ext != ".pdf": continue
            k = rf"Software\Classes\SystemFileAssociations\{ext}\shell\{verb}"
            if not adauga: sterge(k); continue
            with winreg.CreateKey(H, k) as h:
                winreg.SetValueEx(h, "", 0, winreg.REG_SZ, text); winreg.SetValueEx(h, "MultiSelectModel", 0, winreg.REG_SZ, "Player")
                if getattr(sys, "frozen", False): winreg.SetValueEx(h, "Icon", 0, winreg.REG_SZ, sys.executable)
            with winreg.CreateKey(H, k + r"\command") as h: winreg.SetValueEx(h, "", 0, winreg.REG_SZ, cmd)
    try: ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
    except Exception: pass


class DialogCombina(tk.Toplevel):
    def __init__(self, app, fisiere):
        super().__init__(app.root); self.app = app
        self.title("Combină fișiere"); self.geometry(f"900x500+{app.root.winfo_rootx() + 80}+{app.root.winfo_rooty() + 60}"); self.transient(app.root)
        fr = ttk.Frame(self, padding=8); fr.pack(fill="both", expand=True)
        ttk.Label(fr, text="Trage aici fișiere (PDF, DOC, DOCX, XLS, XLSX, PPT, imagini) sau folosește „Adaugă”. Ordinea din listă = ordinea în PDF.",
                  foreground="#444").pack(anchor="w", pady=(0, 6))
        mid = ttk.Frame(fr); mid.pack(fill="both", expand=True)
        self.tv = ttk.Treeview(mid, columns=("tip", "pag", "cale"), show="tree headings", selectmode="extended")
        self.tv.heading("#0", text="Fișier"); self.tv.heading("tip", text="Tip"); self.tv.heading("pag", text="Pagini (ex. 1-3, 5)"); self.tv.heading("cale", text="Folder")
        self.tv.column("#0", width=240); self.tv.column("tip", width=70, anchor="center"); self.tv.column("pag", width=120, anchor="center"); self.tv.column("cale", width=200)
        sb = ttk.Scrollbar(mid, command=self.tv.yview); self.tv.config(yscrollcommand=sb.set)
        bb = ttk.Frame(mid, padding=(8, 0)); bb.pack(side="right", fill="y")
        self.tv.pack(side="left", fill="both", expand=True); sb.pack(side="left", fill="y")
        for t, c in (("➕ Adaugă fișiere…", self.adauga_dialog), ("📁 Adaugă folder…", self.adauga_folder), ("▲ Sus", lambda: self.muta(-1)),
                     ("▼ Jos", lambda: self.muta(1)), ("✎ Pagini…", self.pagini), ("✖ Elimină", self.elimina), ("Golește lista", lambda: self.tv.delete(*self.tv.get_children()))):
            ttk.Button(bb, text=t, command=c, width=18).pack(pady=2, fill="x")
        jos = ttk.Frame(fr); jos.pack(fill="x", pady=(8, 0))
        ttk.Label(jos, text="Format pagini:").pack(side="left")
        self.v_f = tk.StringVar(value="Păstrează formatul"); ttk.Combobox(jos, textvariable=self.v_f, state="readonly", width=18, values=["Păstrează formatul"] + list(FORMATE)).pack(side="left", padx=4)
        ttk.Label(jos, text="Orientare:").pack(side="left", padx=(8, 0))
        self.v_o = tk.StringVar(value="Automat"); ttk.Combobox(jos, textvariable=self.v_o, state="readonly", width=10, values=["Automat", "Vertical", "Orizontal"]).pack(side="left", padx=4)
        ttk.Button(jos, text="Anulează", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(jos, text="🗂 Combină", command=self.combina).pack(side="right")
        self.tv.bind("<Double-1>", lambda e: self.pagini()); self.tv.bind("<Delete>", lambda e: self.elimina())
        self.tv.bind("<ButtonPress-1>", self._ap); self.tv.bind("<B1-Motion>", self._tr)
        if TkinterDnD:
            self.drop_target_register(DND_FILES); self.dnd_bind("<<Drop>>", lambda e: self.adauga(list(self.tk.splitlist(e.data))))
        self.adauga(fisiere)

    def adauga(self, fisiere):
        for f in fisiere:
            if os.path.isdir(f): self.adauga(sorted(os.path.join(f, x) for x in os.listdir(f))); continue
            ext = os.path.splitext(f)[1].lower()
            if ext in EXT_TOATE and os.path.isfile(f):
                self.tv.insert("", "end", text=os.path.basename(f), values=(ext[1:].upper(), "toate", os.path.dirname(f)), tags=(f,))

    def adauga_dialog(self):
        f = filedialog.askopenfilenames(parent=self, filetypes=TIPURI)
        if f: self.adauga(list(f))

    def adauga_folder(self):
        d = filedialog.askdirectory(parent=self)
        if d: self.adauga([d])

    def muta(self, d):
        sel = self.tv.selection()
        for i in (sel if d < 0 else reversed(sel)): self.tv.move(i, "", self.tv.index(i) + d)

    def elimina(self):
        for i in self.tv.selection(): self.tv.delete(i)

    def pagini(self):
        sel = self.tv.selection()
        if not sel: return
        from tkinter import simpledialog
        v = simpledialog.askstring("Pagini", "Ce pagini iei? (toate, sau ex. 1-3, 5, 8-)", initialvalue=self.tv.set(sel[0], "pag"), parent=self)
        if v is not None:
            for i in sel: self.tv.set(i, "pag", v.strip() or "toate")

    def _ap(self, e): self._d = self.tv.identify_row(e.y)

    def _tr(self, e):
        t = self.tv.identify_row(e.y)
        if getattr(self, "_d", None) and t and t != self._d: self.tv.move(self._d, "", self.tv.index(t))

    def combina(self):
        it = [(self.tv.item(i, "tags")[0], self.tv.set(i, "pag")) for i in self.tv.get_children()]
        if not it: messagebox.showinfo(NUME, "Adaugă cel puțin un fișier.", parent=self); return
        try:
            for f, p in it: pagini_din_text(p, 10 ** 6)
        except ValueError:
            messagebox.showerror(NUME, "Paginile se scriu așa: toate  sau  1-3, 5, 8-", parent=self); return
        app = self.app; fmt = None if self.v_f.get().startswith("Păstr") else self.v_f.get(); o = self.v_o.get()
        def porneste():
            def g(d):
                app._incarca(d, None, "Combinat.pdf", True); app.stare(f"✔ Combinat {len(it)} fișiere – salvează cu Ctrl+S.")
            if app.lucru(lambda: combina(it, fmt, o), g, f"Se combină {len(it)} fișiere (Word/Excel se convertesc în PDF)…"):
                try: self.destroy()
                except Exception: pass
        app._intreaba_salvare(porneste)


def main():
    limiteaza_cpu()
    args = sys.argv[1:]; combina_mod = bool(args and args[0] == "--combina")
    if combina_mod: args = args[1:]
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        srv.bind(("127.0.0.1", PORT)); srv.listen(16)
    except OSError:
        srv.close(); srv = None
        if args:                                            # programul e deja deschis: îi trimit fișierele
            try:
                c = socket.create_connection(("127.0.0.1", PORT), timeout=2); c.sendall("\n".join(["C" if combina_mod or len(args) > 1 else "O"] + [os.path.abspath(a) for a in args]).encode("utf-8")); c.close(); return
            except OSError:
                pass
    app = App()
    if srv: app.asculta(srv)
    args = [os.path.abspath(a) for a in args if os.path.exists(a)]
    if combina_mod or len(args) > 1: app._rez.put(("combina", args, None, None))
    elif args: app.root.after(200, lambda: app.deschide(args[0]))
    if sys.platform == "win32" and getattr(sys, "frozen", False) and not cit_cfg().get("meniu_intrebat"):
        def intreaba():
            scr_cfg(meniu_intrebat=True)
            if messagebox.askyesno(NUME, "Adaug „Combină fișierele în PDF PC…” în meniul click-dreapta din Windows?", parent=app.root):
                app.meniu_windows(True)
        app.root.after(1200, intreaba)
    app.root.mainloop()
    try: shutil.rmtree(TMP, ignore_errors=True)
    except Exception: pass


if __name__ == "__main__":
    main()
