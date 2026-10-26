"""Lista de straturi din panglică, ca în AutoCAD: fiecare rând are becul (pornit/oprit), soarele (înghețat),
lacătul (blocat), pătratul de culoare și numele. Clic pe iconițe = comută; clic pe nume = strat curent
(sau, cu obiecte selectate, le mută pe acel strat)."""
import tkinter as tk
from ezdxf import colors as ezcolors
from stil import *

RH = 22


def culoare_strat(l):
    if l.dxf.hasattr("true_color"): return "#%02x%02x%02x" % ezcolors.int2rgb(l.dxf.true_color)
    c = abs(l.dxf.get("color", 7))
    return "#ffffff" if c in (7, 255) else "#%02x%02x%02x" % ezcolors.aci2rgb(c)


def iconite(cv, x, y, l, h=RH):
    """desenează becul, soarele / fulgul, lacătul și pătratul de culoare; întoarce zonele de clic"""
    cy = y + h / 2; z = {}
    on = l.is_on(); cv.create_oval(x + 3, cy - 7, x + 13, cy + 3, fill="#f5c518" if on else "#5a6578", outline="")
    cv.create_rectangle(x + 6, cy + 3, x + 10, cy + 7, fill="#c9ced6", outline=""); z["on"] = (x, x + 16)
    x += 20
    if l.is_frozen(): cv.create_text(x + 8, cy, text="❄", fill="#7fc8ff", font=(F, -13, "bold"))
    else:
        cv.create_oval(x + 4, cy - 4, x + 12, cy + 4, fill="#f5c518", outline="")
        for dx, dy in ((0, -7), (0, 7), (-7, 0), (7, 0), (-5, -5), (5, 5), (-5, 5), (5, -5)):
            cv.create_line(x + 8 + dx * 0.65, cy + dy * 0.65, x + 8 + dx, cy + dy, fill="#f5c518")
    z["frz"] = (x, x + 16); x += 20
    blc = l.is_locked()
    cv.create_rectangle(x + 3, cy - 1, x + 13, cy + 7, fill="#d9a520", outline="")
    cv.create_arc(x + 4, cy - 8, x + 12 if blc else x + 18, cy + 4, start=0, extent=180, style="arc", outline="#d9a520", width=2)
    z["lock"] = (x, x + 18); x += 22
    cv.create_rectangle(x + 2, cy - 6, x + 14, cy + 6, fill=culoare_strat(l), outline="#9aa0a8"); z["col"] = (x, x + 16)
    return x + 22, z


class ListaStraturi(tk.Frame):
    def __init__(self, parinte, app, latime=230):
        super().__init__(parinte, bg="#2b313a", highlightthickness=1, highlightbackground=SEP)
        self.app = app; self.text = "0"; self.lat = latime
        self.cv = tk.Canvas(self, width=latime, height=RH, bg="#2b313a", highlightthickness=0); self.cv.pack(side="left")
        s = tk.Label(self, text="▾", bg="#2b313a", fg=TEXT, font=(F, -11), padx=3); s.pack(side="left", fill="y")
        for w in (self.cv, s): w.bind("<Button-1>", lambda e: self.deschide())
        self.popup = None; self._deseneaza()

    # interfața pe care o folosește programul (ca la Combobox)
    def __setitem__(self, k, v): pass

    def set(self, t):
        self.text = t[2:] if t.startswith("● ") else t; self._deseneaza()

    def get(self): return "● " + self.text

    def _deseneaza(self):
        cv = self.cv; cv.delete("all"); doc = self.app.doc
        if doc and self.text in doc.layers:
            x, _ = iconite(cv, 2, 0, doc.layers.get(self.text))
            cv.create_text(x, RH / 2, text=self.text, fill=TEXT, anchor="w", font=F_MIC)
        else: cv.create_text(6, RH / 2, text=self.text, fill=TEXT, anchor="w", font=F_MIC)

    def deschide(self):
        doc = self.app.doc
        if doc is None: return
        if self.popup and self.popup.winfo_exists(): return self.inchide()
        straturi = sorted(doc.layers, key=lambda l: (l.dxf.name != "0", l.dxf.name.lower()))
        p = tk.Toplevel(self); p.overrideredirect(True); p.configure(bg="#2b313a", highlightthickness=1, highlightbackground=SEP)
        h = min(len(straturi), 18) * RH + 4
        p.geometry(f"{self.lat + 20}x{h}+{self.winfo_rootx()}+{self.winfo_rooty() + self.winfo_height()}")
        cv = tk.Canvas(p, bg="#2b313a", highlightthickness=0, width=self.lat + 4, height=h)
        sb = tk.Scrollbar(p, orient="vertical", command=cv.yview); cv.configure(yscrollcommand=sb.set, scrollregion=(0, 0, self.lat, len(straturi) * RH + 4))
        cv.pack(side="left", fill="both", expand=True)
        if len(straturi) > 18: sb.pack(side="right", fill="y")
        zone = []
        for i, l in enumerate(straturi):
            y = 2 + i * RH
            if l.dxf.name == self.text: cv.create_rectangle(0, y, self.lat + 4, y + RH, fill=HOVER, outline="")
            x, z = iconite(cv, 4, y, l)
            cv.create_text(x, y + RH / 2, text=l.dxf.name, fill=TEXT, anchor="w", font=F_MIC); zone.append((l, z))
        def clic(e):
            yy = cv.canvasy(e.y); i = int((yy - 2) // RH)
            if not (0 <= i < len(zone)): return
            l, z = zone[i]; x = e.x
            if z["on"][0] <= x <= z["on"][1]: l.off() if l.is_on() else l.on()
            elif z["frz"][0] <= x <= z["frz"][1]:
                if l.dxf.name == doc.header.get("$CLAYER", "0"): return self.app.mesaj("Текущий слой нельзя заморозить.")
                l.thaw() if l.is_frozen() else l.freeze()
            elif z["lock"][0] <= x <= z["lock"][1]: l.unlock() if l.is_locked() else l.lock()
            else:
                self.inchide(); self.app.combo_ales("слой", "● " + l.dxf.name); return
            self.app.marcheaza(); self.app.v.reconstruieste(); self.app.v.deseneaza(); self.inchide(); self.deschide(); self._deseneaza()
        cv.bind("<Button-1>", clic)
        cv.bind("<MouseWheel>", lambda e: cv.yview_scroll(-1 if e.delta > 0 else 1, "units"))
        self.popup = p
        self.after(150, lambda: self.winfo_toplevel().bind_all("<Button-1>", self._afara, add="+"))

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
