"""Verificarea schemei: ce e neclar sau greșit desenat și ce se poate îmbunătăți.
• capete de linie care nu ajung nicăieri (fibră „în aer”)
• linii dublate (aceeași linie desenată de două ori, una peste alta)
• texte suprapuse (nu se pot citi)
• porturi libere pe benzi."""
import math
import porturi, traseu


def _dist_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def capete_libere(S, B=None):
    """capetele de linie care nu ating altă linie, o bandă sau un chenar"""
    B = B if B is not None else traseu.bucati(S)
    cutii = []
    for f in S.p.forme():
        if f.e1d: continue
        try: cutii.append(f.cutie())
        except Exception: pass
    seg = [(n, pts[i], pts[i + 1]) for n, (f, pts, c) in enumerate(B) for i in range(len(pts) - 1)]
    out = []
    for n, (f, pts, c) in enumerate(B):
        for p in (pts[0], pts[-1]):
            ok = False
            for m, a, b in seg:
                if m != n and _dist_seg(p, a, b) < 0.025: ok = True; break
            if not ok:
                for x0, y0, x1, y1 in cutii:                           # pe marginea unui chenar, sau în interiorul unei benzi / echipament mic
                    if not (x0 - 0.04 <= p[0] <= x1 + 0.04 and y0 - 0.04 <= p[1] <= y1 + 0.04): continue
                    pe_margine = min(abs(p[0] - x0), abs(p[0] - x1), abs(p[1] - y0), abs(p[1] - y1)) < 0.04
                    if pe_margine or (x1 - x0) * (y1 - y0) < 0.6: ok = True; break
            if not ok: out.append((f, p))
    return out


def dublate(B):
    """linii desenate de două ori, una peste alta"""
    vazute = {}; out = []
    for f, pts, c in B:
        k = tuple(sorted([(round(pts[0][0], 2), round(pts[0][1], 2)), (round(pts[-1][0], 2), round(pts[-1][1], 2))]))
        if k[0] == k[1]: continue
        if k in vazute and vazute[k].id != f.id: out.append(f)
        else: vazute[k] = f
    return out


def texte_suprapuse(S):
    tx = []
    for f in S.p.forme():
        t = (f.text_tot() or "").strip()
        if not t or f.e1d: continue
        try: b = f.cutie()
        except Exception: continue
        if (b[2] - b[0]) * (b[3] - b[1]) > 4: continue                    # chenare mari cu titlu, nu etichete
        tx.append((f, b, t))
    out = []
    for i in range(len(tx)):
        for j in range(i + 1, len(tx)):
            (f, a, ta), (g, b, tb) = tx[i], tx[j]
            ix = min(a[2], b[2]) - max(a[0], b[0]); iy = min(a[3], b[3]) - max(a[1], b[1])
            if ix <= 0 or iy <= 0: continue
            mic = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1])) or 1e-6
            if ix * iy / mic > 0.5 and ta != tb: out.append((f, g, ta, tb))
    return out


def porturi_libere(S):
    """[(nod, port, (x0, y0, x1, y1))] – dreptunghiul mic al fiecărui port liber, pentru marcat pe schemă"""
    out = []
    for nd in porturi.noduri(S):
        try:
            vert, (x0, y0, x1, y1), poz = porturi.porturi_xy(S, nd); oc = porturi.porturi_ocupate(S, nd)
        except Exception: continue
        pas = abs(poz[1] - poz[0]) / 2 if len(poz) > 1 else 0.04
        for k, v in enumerate(poz, 1):
            if k in oc: continue
            out.append((nd, k, (x0 - 0.02, v - pas, x1 + 0.02, v + pas) if vert else (v - pas, y0 - 0.02, v + pas, y1 + 0.02)))
    return out


def raport(S):
    B = traseu.bucati(S)
    cl = capete_libere(S, B); du = dublate(B); ts = texte_suprapuse(S); pl = porturi_libere(S)
    mans = []
    for m in porturi.mansoane(S):
        try: mans.append((m, porturi.cutie_nod(S, m)))
        except Exception: pass
    in_m = lambda p: next((m for m, b in mans if b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]), None)
    rezerva = [(f, p, in_m(p)) for f, p in cl if in_m(p)]
    aer = [(f, p) for f, p in cl if not in_m(p)]
    return {"capete": aer, "rezerva": rezerva, "dublate": du, "texte": ts, "libere": pl}
