"""Trafic PC – analiza video a traficului (portabil, fără instalare).

Deschizi filmul (sau camera live), desenezi porțile de numărare și zonele direct pe imagine,
apeși Start. Rezultatul: Excel cu treceri pe clase și sens, pe intervale, zone și alerte (+ video cu desene)."""
import os, sys, threading, time, queue, traceback, json, base64

_BAZA = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _incarca_cv2():
    """În .exe: încarcă direct modulul binar OpenCV (cv2*.pyd), fără „bootstrap”-ul pachetului cv2
    (pe alt calculator dă „recursion is detected during loading of cv2”)."""
    if not getattr(sys, "frozen", False) or "cv2" in sys.modules: return
    import glob, importlib.util
    pyd = sorted(glob.glob(os.path.join(_BAZA, "**", "cv2*.pyd"), recursive=True), key=len)
    if not pyd:
        raise ImportError("Lipsește fișierul OpenCV (cv2*.pyd) din folderul _internal – extrage din nou toată arhiva.")
    dll = {_BAZA, os.path.dirname(pyd[0])} | {os.path.dirname(f) for f in glob.glob(os.path.join(_BAZA, "**", "opencv_*.dll"), recursive=True)}
    for d in dll:
        try: os.add_dll_directory(d)
        except (OSError, AttributeError): pass
    os.environ["PATH"] = os.pathsep.join(dll) + os.pathsep + os.environ.get("PATH", "")
    spec = importlib.util.spec_from_file_location("cv2", pyd[0])
    mod = importlib.util.module_from_spec(spec); sys.modules["cv2"] = mod; spec.loader.exec_module(mod)


_incarca_cv2()

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import numpy as np
import cv2
import detector, motor, raport
from stil import Buton, card, teme, FONT, BG, CARD, TEXT, GRI, VERDE, ROSU, ALBASTRU, ANTET

TITLU = "Trafic PC – analiza video a traficului"
MODELE = {"Precis (YOLOX-S)": "yolox_s.onnx", "Rapid (YOLOX-Tiny)": "yolox_tiny.onnx"}


def png_tk(img):
    ok, b = cv2.imencode(".png", img); return tk.PhotoImage(data=base64.b64encode(b.tobytes()))


class App:
    def __init__(self, root, initial=None):
        self.root = root; root.title(TITLU); teme(root); root.geometry("1400x860"); root.minsize(1100, 700)
        self.video = None; self.img0 = None; self.s = 1.0; self.ox = self.oy = 0
        self.cfg = {"porti": [], "zone": [], "calibrare": None}
        self.mod = None; self.puncte = []; self.q = queue.Queue(maxsize=2); self.th = None
        self._stop = False; self._pauza = False; self.an = None
        # antet
        a = tk.Frame(root, bg=ANTET); a.pack(fill="x")
        tk.Label(a, text="🚦 Trafic PC", bg=ANTET, fg="white", font=(FONT, 15, "bold")).pack(side="left", padx=14, pady=8)
        tk.Label(a, text="numărare pe porți · zone · viteză · export Excel", bg=ANTET, fg="#b9c7d6", font=(FONT, 10)).pack(side="left")
        corp = tk.Frame(root, bg=BG); corp.pack(fill="both", expand=True, pady=(10, 0))
        # imaginea
        st = tk.Frame(corp, bg="#111"); st.pack(side="left", fill="both", expand=True, padx=(14, 0), pady=(0, 10))
        self.c = tk.Canvas(st, bg="#111", highlightthickness=0, cursor="crosshair"); self.c.pack(fill="both", expand=True)
        self.c.bind("<Button-1>", self.click); self.c.bind("<Button-3>", self.click_dreapta); self.c.bind("<Double-Button-1>", self.click_dreapta)
        self.c.bind("<Motion>", self.misca); self.c.bind("<Configure>", lambda e: self.arata())
        self.ajutor = tk.Label(st, text="Deschide un film sau o cameră.", bg="#111", fg="#e8edf2", font=(FONT, 10), anchor="w")
        self.ajutor.pack(fill="x", padx=8, pady=4)
        # panoul din dreapta
        dr = tk.Frame(corp, bg=BG, width=380); dr.pack(side="right", fill="y"); dr.pack_propagate(False)
        f = card(dr, "VIDEO")
        r = tk.Frame(f, bg=CARD); r.pack(fill="x")
        Buton(r, "📂 Deschide film", self.deschide, "albastru").pack(side="left")
        Buton(r, "📡 Cameră live", self.camera).pack(side="left", padx=6)
        self.lbl_video = tk.Label(f, text="—", bg=CARD, fg=GRI, font=(FONT, 9), anchor="w", wraplength=330, justify="left"); self.lbl_video.pack(fill="x", pady=(6, 0))
        r = tk.Frame(f, bg=CARD); r.pack(fill="x", pady=(6, 0))
        tk.Label(r, text="Ora începutului filmării:", bg=CARD, fg=TEXT, font=(FONT, 9)).pack(side="left")
        self.ora = tk.StringVar(value=time.strftime("%Y-%m-%d %H:%M:%S")); tk.Entry(r, textvariable=self.ora, width=19, font=(FONT, 9)).pack(side="left", padx=4)
        f = card(dr, "DESENEAZĂ PE IMAGINE")
        r = tk.Frame(f, bg=CARD); r.pack(fill="x")
        Buton(r, "➕ Poartă", lambda: self.incepe("poarta")).pack(side="left")
        Buton(r, "⬠ Zonă", lambda: self.incepe("zona")).pack(side="left", padx=6)
        Buton(r, "📏 Calibrare", lambda: self.incepe("calibrare")).pack(side="left")
        self.lista = tk.Listbox(f, height=6, font=(FONT, 9), relief="flat", highlightthickness=1, highlightbackground="#dde2e8")
        self.lista.pack(fill="x", pady=(8, 4))
        r = tk.Frame(f, bg=CARD); r.pack(fill="x")
        Buton(r, "✖ Șterge", self.sterge).pack(side="left")
        Buton(r, "💾 Salvează", self.salveaza_cfg).pack(side="left", padx=6)
        Buton(r, "📄 Încarcă", self.incarca_cfg).pack(side="left")
        f = card(dr, "ANALIZA")
        r = tk.Frame(f, bg=CARD); r.pack(fill="x")
        tk.Label(r, text="Model:", bg=CARD, fg=TEXT, font=(FONT, 9)).pack(side="left")
        self.model = tk.StringVar(value=list(MODELE)[0])
        ttk.Combobox(r, textvariable=self.model, values=list(MODELE), state="readonly", width=18).pack(side="left", padx=4)
        r = tk.Frame(f, bg=CARD); r.pack(fill="x", pady=(4, 0))
        tk.Label(r, text="Cadre analizate pe secundă:", bg=CARD, fg=TEXT, font=(FONT, 9)).pack(side="left")
        self.fps = tk.IntVar(value=10); tk.Spinbox(r, from_=2, to=30, textvariable=self.fps, width=4).pack(side="left", padx=4)
        r = tk.Frame(f, bg=CARD); r.pack(fill="x", pady=(4, 0))
        tk.Label(r, text="Camera e:", bg=CARD, fg=TEXT, font=(FONT, 9)).pack(side="left")
        self.ancora = tk.StringVar(value="jos")
        tk.Radiobutton(r, text="în unghi", variable=self.ancora, value="jos", bg=CARD).pack(side="left")
        tk.Radiobutton(r, text="drept de sus", variable=self.ancora, value="centru", bg=CARD).pack(side="left")
        self.pietoni = tk.BooleanVar(value=False)
        tk.Checkbutton(f, text="Numără și pietonii (nu intră în raportul auto)", variable=self.pietoni, bg=CARD, anchor="w").pack(fill="x")
        self.video_out = tk.BooleanVar(value=True)
        tk.Checkbutton(f, text="Salvează și video-ul cu desene", variable=self.video_out, bg=CARD, anchor="w").pack(fill="x")
        r = tk.Frame(f, bg=CARD); r.pack(fill="x", pady=(6, 0))
        self.b_start = Buton(r, "▶ Start", self.start, "principal", mare=True); self.b_start.pack(side="left")
        self.b_pauza = Buton(r, "⏸ Pauză", self.pauza); self.b_pauza.pack(side="left", padx=6); self.b_pauza.config(state="disabled")
        self.b_stop = Buton(r, "■ Stop", self.stop, "rosu"); self.b_stop.pack(side="left"); self.b_stop.config(state="disabled")
        self.bar = ttk.Progressbar(f, style="Drum.Horizontal.TProgressbar", maximum=1.0); self.bar.pack(fill="x", pady=(8, 2))
        self.stare = tk.Label(f, text="", bg=CARD, fg=GRI, font=(FONT, 9), anchor="w"); self.stare.pack(fill="x")
        f = card(dr, "CONTOARE", expand=True)
        self.txt = tk.Text(f, height=10, font=("Consolas", 9), relief="flat", bg=CARD, wrap="word"); self.txt.pack(fill="both", expand=True)
        r = tk.Frame(dr, bg=BG); r.pack(fill="x", padx=14, pady=(0, 10))
        self.b_xls = Buton(r, "📊 Rezultatul (Excel)", self.deschide_rezultat, "albastru"); self.b_xls.pack(side="left", fill="x", expand=True)
        Buton(r, "📅 Raport lunar", self.raport_lunar).pack(side="left", padx=(6, 0))
        self.b_xls.config(state="disabled"); self.rezultat = None
        if initial: root.after(300, lambda: self.incarca_video(initial))
        root.after(80, self.poll)

    # ---------------------------------------------------------------- video
    def deschide(self):
        p = filedialog.askopenfilename(title="Alege filmul", filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.mts *.m4v *.wmv"), ("Toate", "*.*")])
        if p: self.incarca_video(p)

    def camera(self):
        u = simpledialog.askstring(TITLU, "Adresa camerei (de ex. rtsp://utilizator:parola@192.168.1.10:554/stream1)\n"
                                          "sau numărul camerei web (0):", parent=self.root)
        if u: self.incarca_video(int(u) if u.strip().isdigit() else u.strip())

    def incarca_video(self, p):
        cap = cv2.VideoCapture(p); ok, img = cap.read()
        fps = cap.get(cv2.CAP_PROP_FPS) or 0; n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0; cap.release()
        if not ok: messagebox.showerror(TITLU, f"Nu se poate citi: {p}"); return
        self.video = p; self.img0 = img
        if isinstance(p, str) and os.path.exists(p):
            dur = n / fps if fps else 0
            self.lbl_video.config(text=f"{os.path.basename(p)}\n{img.shape[1]}×{img.shape[0]} · {fps:.1f} cadre/s · {int(dur // 60)} min {int(dur % 60)} s")
            self.ora.set(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(p) - dur)))
            cj = os.path.splitext(p)[0] + "_trafic.json"
            if os.path.exists(cj): self.cfg = json.load(open(cj, encoding="utf-8")); self.actualizeaza_lista()
        else:
            self.lbl_video.config(text=f"Cameră live: {p}\n{img.shape[1]}×{img.shape[0]}"); self.ora.set(time.strftime("%Y-%m-%d %H:%M:%S"))
        self.ajutor.config(text="Desenează porțile de numărare (➕ Poartă) și zonele (⬠ Zonă), apoi ▶ Start.")
        self.arata()

    # ---------------------------------------------------------------- desenul
    def arata(self, img=None):
        img = img if img is not None else (self.img0 if self.img0 is not None else None)
        self.c.delete("all")
        if img is None: return
        if img is self.img0:
            an = motor.Analiza({**self.cfg, "calibrare": None}); img = motor.deseneaza(img, an, [])
        W, H = max(1, self.c.winfo_width()), max(1, self.c.winfo_height()); h, w = img.shape[:2]
        self.s = min(W / w, H / h); nw, nh = int(w * self.s), int(h * self.s); self.ox, self.oy = (W - nw) // 2, (H - nh) // 2
        self.foto = png_tk(cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA))
        self.c.create_image(self.ox, self.oy, image=self.foto, anchor="nw")
        if self.cfg.get("calibrare"):
            p = [self.ecran(*q) for q in self.cfg["calibrare"]["puncte"]]
            self.c.create_polygon(*[v for q in p for v in q], outline="#ff3cd2", fill="", dash=(4, 3), width=2)
        if self.puncte:
            p = [self.ecran(*q) for q in self.puncte]
            for x, y in p: self.c.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#ffd400", outline="black")
            if len(p) > 1: self.c.create_line(*[v for q in p for v in q], fill="#ffd400", width=2)

    def ecran(self, x, y): return x * self.s + self.ox, y * self.s + self.oy
    def imagine(self, x, y): return [round((x - self.ox) / self.s, 1), round((y - self.oy) / self.s, 1)]

    def incepe(self, mod):
        if self.img0 is None: messagebox.showinfo(TITLU, "Deschide întâi un film sau o cameră."); return
        self.mod = mod; self.puncte = []
        self.ajutor.config(text={"poarta": "Poartă: clic pe capătul A, apoi pe capătul B. Sensul A→B e cel care taie linia de la stânga la dreapta privind din A spre B.",
                                 "zona": "Zonă: clic pe colțuri; clic dreapta (sau dublu-clic) închide zona.",
                                 "calibrare": "Calibrare viteză: clic pe 4 colțuri ale unui dreptunghi real de pe sol (de ex. marcajele unei benzi), în ordine: stânga-sus, dreapta-sus, dreapta-jos, stânga-jos."}[mod])
        self.arata()

    def click(self, e):
        if not self.mod: return
        self.puncte.append(self.imagine(e.x, e.y))
        if self.mod == "poarta" and len(self.puncte) == 2:
            n = simpledialog.askstring(TITLU, "Numele porții:", initialvalue=f"Poarta {len(self.cfg['porti']) + 1}", parent=self.root)
            if n: self.cfg["porti"].append({"nume": n, "a": self.puncte[0], "b": self.puncte[1]})
            self.gata()
        elif self.mod == "calibrare" and len(self.puncte) == 4:
            L = simpledialog.askfloat(TITLU, "Lungimea dreptunghiului, de-a lungul drumului (m):", parent=self.root, minvalue=0.5)
            W = simpledialog.askfloat(TITLU, "Lățimea dreptunghiului, de-a curmezișul (m):", parent=self.root, minvalue=0.5) if L else None
            if L and W: self.cfg["calibrare"] = {"puncte": self.puncte, "lungime_m": L, "latime_m": W}
            self.gata()
        else: self.arata()

    def click_dreapta(self, e):
        if self.mod != "zona" or len(self.puncte) < 3: return
        n = simpledialog.askstring(TITLU, "Numele zonei:", initialvalue=f"Zona {len(self.cfg['zone']) + 1}", parent=self.root)
        if n:
            st = simpledialog.askinteger(TITLU, "Alertă dacă un obiect stă în zonă mai mult de (secunde, 0 = fără):", initialvalue=0, minvalue=0, parent=self.root)
            self.cfg["zone"].append({"nume": n, "poligon": self.puncte, "stationare_s": st or 0})
        self.gata()

    def misca(self, e):
        if self.mod and self.puncte:
            self.c.delete("ghid"); x, y = self.ecran(*self.puncte[-1])
            self.c.create_line(x, y, e.x, e.y, fill="#ffd400", dash=(3, 3), tags="ghid")

    def gata(self):
        self.mod = None; self.puncte = []; self.actualizeaza_lista()
        self.ajutor.config(text="Gata. Mai adaugă porți/zone sau apasă ▶ Start."); self.arata()

    def actualizeaza_lista(self):
        self.lista.delete(0, "end")
        for g in self.cfg.get("porti", []): self.lista.insert("end", f"➕ {g['nume']}")
        for z in self.cfg.get("zone", []): self.lista.insert("end", f"⬠ {z['nume']}" + (f" (alertă > {z['stationare_s']} s)" if z.get("stationare_s") else ""))
        if self.cfg.get("calibrare"): c = self.cfg["calibrare"]; self.lista.insert("end", f"📏 Calibrare {c['lungime_m']} × {c['latime_m']} m")

    def sterge(self):
        sel = self.lista.curselection()
        if not sel: return
        i = sel[0]; np_ = len(self.cfg["porti"]); nz = len(self.cfg["zone"])
        if i < np_: self.cfg["porti"].pop(i)
        elif i < np_ + nz: self.cfg["zone"].pop(i - np_)
        else: self.cfg["calibrare"] = None
        self.actualizeaza_lista(); self.arata()

    def salveaza_cfg(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Configurare", "*.json")],
                                         initialfile=(os.path.splitext(os.path.basename(self.video))[0] + "_trafic.json") if isinstance(self.video, str) else "trafic.json")
        if p: json.dump(self.cfg, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    def incarca_cfg(self):
        p = filedialog.askopenfilename(filetypes=[("Configurare", "*.json")])
        if p: self.cfg = json.load(open(p, encoding="utf-8")); self.actualizeaza_lista(); self.arata()

    # ---------------------------------------------------------------- analiza
    def start(self):
        if self.video is None: messagebox.showinfo(TITLU, "Deschide întâi un film sau o cameră."); return
        if not self.cfg["porti"] and not self.cfg["zone"]:
            if not messagebox.askyesno(TITLU, "Nu ai desenat nicio poartă sau zonă.\nSe va număra fiecare vehicul care trece prin imagine (o dată), pe sensuri: în jos (A→B) și în sus (B→A).\nPentru numărare pe benzi sau intersecții desenează o „Poartă”. Continui?"): return
        clase = ["bicicleta", "masina", "motocicleta", "autobuz", "tramvai", "camion"] + (["pieton"] if self.pietoni.get() else [])
        cfg = dict(self.cfg, model=MODELE[self.model.get()], fps_analiza=self.fps.get(), ancora=self.ancora.get(), ora_start=self.ora.get().strip(), clase=clase)
        if isinstance(self.video, str) and os.path.exists(self.video):
            baza = os.path.splitext(self.video)[0] + "_trafic"
            json.dump(self.cfg, open(baza + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        else:
            d = os.path.join(os.path.expanduser("~"), "Documents", "Trafic PC"); os.makedirs(d, exist_ok=True)
            baza = os.path.join(d, "camera_" + time.strftime("%Y%m%d_%H%M%S"))
        self.rezultat = baza + ".xlsx"; self._stop = False; self._pauza = False
        for b in (self.b_pauza, self.b_stop): b.config(state="normal")
        self.b_start.config(state="disabled"); self.b_xls.config(state="disabled"); self.mod = None
        self.ajutor.config(text="Se analizează… Poți întrerupe oricând; rezultatul de până atunci se salvează.")
        self.th = threading.Thread(target=self.lucru, args=(cfg, baza), daemon=True); self.th.start()

    def lucru(self, cfg, baza):
        try:
            det = detector.Detector(cfg["model"], 0.3)
            self.q.put(("stare", f"Model pe {det.dev}"))
            def cadru(img, an):
                try: self.q.put_nowait(("cadru", img, an))
                except queue.Full: pass
            an = motor.ruleaza(self.video, cfg, baza + ".xlsx", baza + ".mp4" if self.video_out.get() else None, det=det,
                               progres=lambda f, s: self.q.put(("progres", f, s)), cadru_cb=cadru,
                               stop=lambda: self._stop, pauza=lambda: self._pauza)
            self.q.put(("gata", an))
        except Exception as e:
            traceback.print_exc(); self.q.put(("eroare", f"{e}"))

    def pauza(self):
        self._pauza = not self._pauza; self.b_pauza.config(text="▶ Continuă" if self._pauza else "⏸ Pauză")

    def stop(self):
        self._stop = True; self.stare.config(text="Se oprește și se salvează rezultatul…")

    def poll(self):
        try:
            while True:
                m = self.q.get_nowait()
                if m[0] == "cadru": self.arata(m[1]); self.contoare(m[2])
                elif m[0] == "progres": self.bar["value"] = m[1]; self.stare.config(text=m[2])
                elif m[0] == "stare": self.stare.config(text=m[1])
                elif m[0] == "gata":
                    self.contoare(m[1]); self.bar["value"] = 1.0; self.terminat()
                    self.stare.config(text=f"Gata → {os.path.basename(self.rezultat)}"); self.b_xls.config(state="normal")
                    self.ajutor.config(text="Gata. Rezultatul e în Excel (și video-ul cu desene, dacă ai bifat), lângă film.")
                elif m[0] == "eroare":
                    self.terminat(); messagebox.showerror(TITLU, m[1])
        except queue.Empty: pass
        self.root.after(80, self.poll)

    def terminat(self):
        self.b_start.config(state="normal"); self.b_pauza.config(state="disabled", text="⏸ Pauză"); self.b_stop.config(state="disabled")

    def contoare(self, an):
        self.txt.delete("1.0", "end")
        from collections import Counter
        for g in an.contor:
            self.txt.insert("end", f"{g}\n")
            for s in ("A→B", "B→A"):
                c = Counter(x[6] or detector.NUME[x[3]] for x in an.treceri if x[1] == g and x[2] == s)
                self.txt.insert("end", f"  {s}: {sum(c.values()):4d}   " + ", ".join(f"{k} {v}" for k, v in c.most_common()) + "\n")
        for z in an.zone:
            n = sum(1 for e in an.zone_ev if e[2] == z["nume"]) + len(an.in_zona.get(z["nume"], {}))
            self.txt.insert("end", f"{z['nume']}: {n} obiecte, acum în zonă {len(an.in_zona.get(z['nume'], {}))}\n")
        for t, z, i, c, m in an.alerte[-5:]: self.txt.insert("end", f"⚠ {z}: {detector.NUME[c]} {i} – {m}\n")

    def raport_lunar(self):
        ps = filedialog.askopenfilenames(title="Alege fișierele *_treceri.csv (toate filmările lunii)", filetypes=[("Treceri", "*_treceri.csv")])
        if not ps: return
        porti = sorted({r[1] for r in raport.citeste_csv(ps)})
        alese = None
        if len(porti) > 1:
            a = simpledialog.askstring(TITLU, "Porțile din fișiere:\n  " + "\n  ".join(porti) +
                                       "\n\nScrie porțile de pus în raport, despărțite prin virgulă (gol = toate):", parent=self.root)
            alese = [x.strip() for x in a.split(",") if x.strip()] if a else None
        out = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="Raport_lunar.xlsx", filetypes=[("Excel", "*.xlsx")])
        if not out: return
        n = raport.raport_lunar(ps, out, alese)
        messagebox.showinfo(TITLU, f"Raport făcut din {n} treceri, {len(ps)} fișiere:\n{out}")
        if os.name == "nt": os.startfile(out)

    def deschide_rezultat(self):
        if self.rezultat and os.path.exists(self.rezultat):
            if os.name == "nt": os.startfile(self.rezultat)
            else: messagebox.showinfo(TITLU, self.rezultat)


def prioritate_mica():
    """Windows: procesul cu prioritate „sub normal” – analiza lungă nu mai blochează restul calculatorului"""
    try:
        import ctypes; k = ctypes.windll.kernel32; k.SetPriorityClass(k.GetCurrentProcess(), 0x4000)
    except Exception: pass


def main():
    prioritate_mica()
    root = tk.Tk(); App(root, sys.argv[1] if len(sys.argv) > 1 else None); root.mainloop()


if __name__ == "__main__":
    main()
