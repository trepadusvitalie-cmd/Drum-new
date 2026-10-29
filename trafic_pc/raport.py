"""Raportul zilnic, în formatul cerut: Data | Ziua | Car | Bus | Motorbike | Light | Heavy | Unknown | Bicycle | Van | Total,
cu bară pe Total, roșu la zilele slabe (sub jumătate din mediană) și rândul Total jos.
Se face dintr-o singură analiză sau din mai multe filmări (raport lunar din fișierele *_treceri.csv)."""
import csv, datetime, os
from collections import Counter, defaultdict
import numpy as np

RAPORT = ["Car", "Bus", "Motorbike", "Light", "Heavy", "Unknown", "Bicycle", "Van"]
ZILE = ["Luni", "Marți", "Miercuri", "Joi", "Vineri", "Sâmbătă", "Duminică"]


def clasa_raport(u, ref_aria):
    """Clasa din raport pentru o urmă: mașina se împarte în Car / Van, camionul în Light / Heavy după mărime
    (aria chenarului față de o mașină obișnuită la aceeași distanță). Pietonii, animalele -> None (nu intră)."""
    tot = sum(u.voturi.values()) or 1; cls, v = u.voturi.most_common(1)[0]
    if v / tot < 0.55 or getattr(u, "loviri_ai", 3) < 2: return "Unknown"    # clasă nesigură sau văzut doar ca mișcare
    if cls in ("pieton", "animal"): return None
    if cls == "bicicleta": return "Bicycle"
    if cls == "motocicleta": return "Motorbike"
    if cls in ("autobuz", "tramvai"): return "Bus"
    st = getattr(u, "marimi", [])
    if not st: return "Car" if cls == "masina" else "Light"
    yc, aria, asp = (float(np.median([s[k] for s in st])) for k in range(3))
    r = aria / max(1e-6, ref_aria(yc))
    if cls == "masina": return "Van" if r > 1.6 or (r > 1.25 and asp > 0.95) else "Car"
    return "Heavy" if r > 3.0 else "Light"                                         # camion


class Referinta:
    """Aria tipică a unei mașini (Car) în funcție de poziția verticală în imagine (perspectiva)."""

    def __init__(self): self.p = []

    def adauga(self, yc, aria):
        self.p.append((yc, aria)); self.p = self.p[-2000:]

    def __call__(self, yc):
        if len(self.p) < 5: return float(np.median([a for _, a in self.p])) if self.p else 1.0
        a = np.array(self.p); k = np.argsort(np.abs(a[:, 0] - yc))[:40]
        return float(np.median(a[k, 1]))


def scrie_csv(path, randuri):
    """randuri: (datetime, poarta, sens, clasa_raport, clasa, id, viteza)"""
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["DataOra", "Poarta", "Sens", "ClasaRaport", "Clasa", "ID", "Viteza_kmh"])
        for r in randuri: w.writerow([r[0].strftime("%Y-%m-%d %H:%M:%S"), *r[1:6], "" if r[6] is None else round(r[6], 1)])


def citeste_csv(paths):
    out = []
    for p in paths:
        with open(p, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                out.append((datetime.datetime.strptime(r["DataOra"], "%Y-%m-%d %H:%M:%S"), r["Poarta"], r["Sens"], r["ClasaRaport"],
                            r["Clasa"], r["ID"], float(r["Viteza_kmh"]) if r["Viteza_kmh"] else None))
    return out


def foaie_zilnica(wb, randuri, titlu="Raport zilnic", luni_intregi=True, porti=None):
    """Adaugă foaia în formatul tabelului: o linie pe zi, toate zilele lunii (zilele fără date = 0, în roșu)."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.formatting.rule import DataBarRule
    ws = wb.create_sheet(titlu, 0)
    randuri = [r for r in randuri if r[3] and (not porti or r[1] in porti)]
    zi = defaultdict(Counter)
    for r in randuri: zi[r[0].date()][r[3]] += 1
    if zi:
        d0, d1 = min(zi), max(zi)
        if luni_intregi:
            d0 = d0.replace(day=1); nxt = (d1.replace(day=28) + datetime.timedelta(days=4)); d1 = nxt - datetime.timedelta(days=nxt.day)
        zile = [d0 + datetime.timedelta(days=k) for k in range((d1 - d0).days + 1)]
    else: zile = []
    sub = Side(style="thin", color="000000"); B = Border(left=sub, right=sub, top=sub, bottom=sub)
    cap = ["Data", "Ziua"] + RAPORT + ["Total"]
    ws.append(cap)
    for c in ws[1]: c.font = Font(bold=True); c.alignment = Alignment(horizontal="center"); c.border = B; c.fill = PatternFill("solid", fgColor="F2F2F2")
    tot = [ZILE and 0] * 0; totals = []
    for d in zile:
        c = zi.get(d, Counter()); vals = [c.get(k, 0) for k in RAPORT]; t = sum(vals); totals.append(t)
        ws.append([d.strftime("%d.%m.%Y"), ZILE[d.weekday()]] + [v if v else None for v in vals] + [t])
    n = len(zile)
    med = float(np.median([t for t in totals if t > 0])) if any(totals) else 0
    for i in range(n):
        row = ws[i + 2]
        for k, c in enumerate(row):
            c.border = B
            if k >= 2: c.number_format = "#,##0"; c.alignment = Alignment(horizontal="right")
        tc = row[len(cap) - 1]; tc.font = Font(bold=True)
        if totals[i] < 0.5 * med or totals[i] == 0: tc.fill = PatternFill("solid", fgColor="F4807A")
    ws.append([])
    sume = [sum(zi[d].get(k, 0) for d in zile) for k in RAPORT]
    ws.append(["Total", ""] + sume + [sum(sume)])
    for c in ws[ws.max_row]: c.font = Font(bold=True); c.border = B; c.number_format = "#,##0"
    if n:
        ws.conditional_formatting.add(f"{chr(64 + len(cap))}2:{chr(64 + len(cap))}{n + 1}",
                                      DataBarRule(start_type="num", start_value=0, end_type="max", color="4F81BD", showValue=True))
    ws.column_dimensions["A"].width = 12; ws.column_dimensions["B"].width = 11
    for k in range(3, len(cap) + 1): ws.column_dimensions[chr(64 + k)].width = 10
    ws.freeze_panes = "A2"
    ws.page_setup.orientation = "landscape"; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True                   # la tipar: toate coloanele pe o pagină
    return ws


def raport_lunar(csv_paths, out_xlsx, porti=None):
    from openpyxl import Workbook
    randuri = citeste_csv(csv_paths); wb = Workbook(); wb.remove(wb.active)
    foaie_zilnica(wb, randuri, porti=porti)
    # și pe ore (media pe zi a săptămânii), util pentru orele de vârf
    ws = wb.create_sheet("Pe ore")
    ws.append(["Ora"] + RAPORT + ["Total"])
    h = defaultdict(Counter)
    for r in randuri:
        if r[3] and (not porti or r[1] in porti): h[r[0].hour][r[3]] += 1
    for o in range(24):
        v = [h[o].get(k, 0) for k in RAPORT]; ws.append([f"{o:02d}:00"] + v + [sum(v)])
    wb.save(out_xlsx)
    return len(randuri)
