"""Lista de culori din panglică, ca în AutoCAD: ПоСлою, ПоБлоку, grila de culori, „Индекс цветов” și „Дополнительные цвета…”."""
import tkinter as tk
from tkinter import colorchooser
from ezdxf import colors as ezcolors
from stil import *

NUME = {256: "ПоСлою", 0: "ПоБлоку", 1: "Красный", 2: "Желтый", 3: "Зеленый", 4: "Голубой", 5: "Синий", 6: "Фиолетовый", 7: "Белый"}


def hexaci(c):
    if c in (7, 255, 256, 0): return "#ffffff"
    return "#%02x%02x%02x" % ezcolors.aci2rgb(c)


# grila: coloana de gri + nuanțe (indexul AutoCAD: 10 = roșu … 230 = roz), pe rânduri luminozitatea
GRILA = [[250, 10, 30, 50, 70, 110, 150, 170, 190, 210, 230],
         [251, 12, 32, 52, 72, 112, 152, 172, 192, 212, 232],
         [252, 11, 31, 51, 71, 111, 151, 171, 191, 211, 231],
         [253, 13, 33, 53, 73, 113, 153, 173, 193, 213, 233],
         [254, 15, 35, 55, 75, 115, 155, 175, 195, 215, 235]]
INDEX = [1, 2, 3, 4, 5, 6, 7, 8, 9]


class ListaCulori(tk.Frame):
    def __init__(self, parinte, app, latime=170):
        super().__init__(parinte, bg="#2b313a", highlightthickness=1, highlightbackground=SEP)
        self.app = app; self.val = 256; self.rgb = None; self.lat = latime
        self.cv = tk.Canvas(self, width=latime, height=20, bg="#2b313a", highlightthickness=0); self.cv.pack(side="left")
        s = tk.Label(self, text="▾", bg="#2b313a", fg=TEXT, font=(F, -11), padx=3); s.pack(side="left", fill="y")
        for w in (self.cv, s): w.bind("<Button-1>", lambda e: self.deschide())
        self.popup = None; self._deseneaza()

    def __setitem__(self, k, v): pass
    def set(self, t): self._deseneaza()
    def get(self): return NUME.get(self.val, str(self.val))

    def arata(self, val, rgb=None):
        self.val = val; self.rgb = rgb; self._deseneaza()

    def _deseneaza(self):
        cv = self.cv; cv.delete("all")
        col = ("#%02x%02x%02x" % self.rgb) if self.rgb else hexaci(self.val)
        cv.create_rectangle(4, 3, 18, 17, fill=col, outline="#9aa0a8")
        cv.create_text(26, 10, text=("RGB %d,%d,%d" % self.rgb) if self.rgb else NUME.get(self.val, f"Цвет {self.val}"), fill=TEXT, anchor="w", font=F_MIC)

    def deschide(self):
        if self.popup and self.popup.winfo_exists(): return self.inchide()
        top = self.winfo_toplevel()
        p = tk.Frame(top, bg="#3b4453", highlightthickness=1, highlightbackground=SEP)
        def rand(text, val):
            r = tk.Frame(p, bg="#3b4453"); r.pack(fill="x", padx=2, pady=1)
            sw = tk.Canvas(r, width=16, height=16, bg="#3b4453", highlightthickness=0); sw.create_rectangle(1, 1, 15, 15, fill="#ffffff", outline="#9aa0a8"); sw.pack(side="left", padx=4)
            l = tk.Label(r, text=text, bg="#3b4453", fg=TEXT, font=F_MIC, anchor="w"); l.pack(side="left", fill="x", expand=True)
            for w in (r, sw, l):
                w.bind("<Button-1>", lambda e: self.alege(val))
                w.bind("<Enter>", lambda e: [c.config(bg=HOVER) for c in (r, l)]); w.bind("<Leave>", lambda e: [c.config(bg="#3b4453") for c in (r, l)])
        rand("ПоСлою", 256); rand("ПоБлоку", 0)
        g = tk.Canvas(p, width=11 * 20 + 4, height=5 * 20 + 4, bg="#3b4453", highlightthickness=0); g.pack(padx=4, pady=4)
        for i, rnd in enumerate(GRILA):
            for j, c in enumerate(rnd): g.create_rectangle(2 + j * 20, 2 + i * 20, 18 + j * 20, 18 + i * 20, fill=hexaci(c), outline="#2b313a", tags=f"c{c}")
        g.bind("<Button-1>", lambda e: self._din_grila(g, e))
        tk.Label(p, text="Индекс цветов", bg="#3b4453", fg=TEXT, font=F_MIC, anchor="w").pack(fill="x", padx=6)
        ix = tk.Canvas(p, width=11 * 20 + 4, height=22, bg="#3b4453", highlightthickness=0); ix.pack(padx=4, pady=(2, 4))
        for j, c in enumerate(INDEX): ix.create_rectangle(2 + j * 22, 2, 18 + j * 22, 18, fill=hexaci(c), outline="#2b313a", tags=f"c{c}")
        ix.bind("<Button-1>", lambda e: self._din_grila(ix, e))
        d = tk.Label(p, text="🎨  Дополнительные цвета...", bg="#3b4453", fg=TEXT, font=F_MIC, anchor="w"); d.pack(fill="x", padx=6, pady=(2, 6))
        d.bind("<Button-1>", lambda e: self.alege_rgb())
        p.update_idletasks()
        x = min(self.winfo_rootx() - top.winfo_rootx(), top.winfo_width() - p.winfo_reqwidth() - 4)
        p.place(x=x, y=self.winfo_rooty() - top.winfo_rooty() + self.winfo_height()); p.lift()
        self.popup = p
        self.after(150, lambda: self.winfo_toplevel().bind_all("<Button-1>", self._afara, add="+"))

    def _din_grila(self, g, e):
        for it in g.find_overlapping(e.x, e.y, e.x, e.y):
            for t in g.gettags(it):
                if t.startswith("c"): return self.alege(int(t[1:]))

    def alege(self, val):
        self.inchide(); self.arata(val); self.app.alege_culoare(val, None)

    def alege_rgb(self):
        self.inchide(); r = colorchooser.askcolor(title="Выбор цвета")
        if r and r[0]:
            rgb = tuple(int(v) for v in r[0]); self.arata(256, rgb); self.app.alege_culoare(None, rgb)

    def _afara(self, e):
        p = self.popup
        if not p or not p.winfo_exists(): return
        if not (p.winfo_rootx() <= e.x_root <= p.winfo_rootx() + p.winfo_width() and p.winfo_rooty() <= e.y_root <= p.winfo_rooty() + p.winfo_height()):
            if not (self.winfo_rootx() <= e.x_root <= self.winfo_rootx() + self.winfo_width() and self.winfo_rooty() <= e.y_root <= self.winfo_rooty() + self.winfo_height()):
                self.inchide()

    def inchide(self):
        if self.popup and self.popup.winfo_exists(): self.popup.destroy()
        self.popup = None
        try: self.winfo_toplevel().unbind_all("<Button-1>")
        except Exception: pass
