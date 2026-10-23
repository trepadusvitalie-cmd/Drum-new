"""Traseul unei fibre: de la un port (ex. ODF portul 2) până la client, urmărind linia după CULOARE.
Pe schemă fibra e făcută din bucăți (linii, polilinii) lipite cap la cap; la benzi (ODF-uri de subinel) și manșoane
continuă cu bucata de aceeași culoare. Rezultatul: bucățile, opririle (manșoane, ODF-uri, client) și cablurile (FO-xx)."""
import math, re
import porturi

GRI = {"#7f7f7f"}
FAMILIE = {"#808080": "#7f7f7f", "#a6a6a6": "#7f7f7f", "#bfbfbf": "#7f7f7f", "#262626": "#000000", "#00cc00": "#00b050", "#3a28d9": "#0000ff",
           "#993300": "#9c4a09", "#ffff00": "#ffc000"}           # fibrele gri = rezervă / trec mai departe fără să fie folosite


def _toate(forme):
    for f in forme:
        yield f
        yield from _toate(f.copii)


def _culoare(f):
    """culoarea fibrei, ca familie (nuanțele apropiate – #00b050 și #00cc00 – sunt aceeași culoare de fibră)"""
    c = (f.cell("LineColor") or "#000000").lower()
    c = {"0": "#000000", "1": "#ffffff", "2": "#ff0000", "4": "#0000ff"}.get(c, c)
    return FAMILIE.get(c) or _familie(c)


def _familie(c):
    try: r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    except Exception: return c
    import colorsys
    h, l, s_ = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if s_ < 0.15: return "#000000" if l < 0.25 else ("#ffffff" if l > 0.9 else "#7f7f7f")
    h *= 360
    for lim, nume in ((15, "#ff0000"), (40, "#9c4a09" if l < 0.45 else "#ffa500"), (65, "#ffc000"), (170, "#00b050"), (200, "#00b0f0"),
                      (255, "#0000ff"), (290, "#7030a0"), (335, "#ff00ff"), (361, "#ff0000")):
        if h < lim: return nume
    return c


def bucati(S):
    """toate liniile deschise de pe pagină: (forma, [puncte], culoare)"""
    out = []
    for f in _toate(S.p.forme()):
        if (f.cell("LinePattern", "1") or "1") == "0": continue
        try: cs = f.contur()
        except Exception: continue
        for pts, plin in cs:
            if len(pts) < 2: continue
            if math.dist(pts[0], pts[-1]) < 0.005 and len(pts) > 2: continue          # contur închis = chenar, nu fibră
            out.append((f, [tuple(p) for p in pts], _culoare(f)))
    return out


def _cutii_inchise(S):
    """chenarele mici închise (echipamente, client): (forma, cutie)"""
    out = []
    for f in _toate(S.p.forme()):
        if f.e1d: continue
        try: b = f.cutie()
        except Exception: continue
        if 0.03 < b[2] - b[0] < 1.0 and 0.03 < b[3] - b[1] < 1.0:
            try: inch = any(len(p) > 2 and math.dist(p[0], p[-1]) < 0.005 for p, _ in f.contur())
            except Exception: inch = False
            if inch: out.append((f, b))
    return out


def _texte(S):
    out = []
    for f in _toate(S.p.forme()):
        t = (f.text_tot() or "").strip()
        if not t: continue
        try: b = f.cutie()
        except Exception: continue
        out.append((" ".join(t.split()), ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2), b))
    return out


def port_xy(S, nd, k):
    vert, (x0, y0, x1, y1), poz = porturi.porturi_xy(S, nd)
    return vert, (x0, y0, x1, y1), poz[k - 1]


def urmareste(S, nd, k):
    """-> dict cu traseul fibrei din portul k al nodului nd, sau None dacă portul e liber"""
    B = bucati(S); vert, (x0, y0, x1, y1), pk = port_xy(S, nd, k)
    start = None
    for i, (f, pts, c) in enumerate(B):
        for j in (0, -1):
            px, py = pts[j]
            if vert and min(abs(px - x0), abs(px - x1)) < 0.15 and abs(py - pk) < 0.02: start = (i, j)
            if not vert and min(abs(py - y0), abs(py - y1)) < 0.15 and abs(px - pk) < 0.02: start = (i, j)
    if start is None: return None
    i, j = start; cul0 = B[i][2]; vazut = {i}; drum = [i]; parcurse = list(B[i][1])
    cur = B[i][1][-1] if j == 0 else B[i][1][0]
    benzi = [n for n in porturi.noduri(S)]; cutii = _cutii_inchise(S); toate_benzi = porturi.benzi(S)
    pe_start = lambda p: (min(abs(p[0] - x0), abs(p[0] - x1)) < 0.15 and y0 - 0.05 <= p[1] <= y1 + 0.05) if vert else \
        (min(abs(p[1] - y0), abs(p[1] - y1)) < 0.15 and x0 - 0.05 <= p[0] <= x1 + 0.05)
    capat = None
    tx = _texte(S); ids_benzi = {bb.id for bb in toate_benzi}
    mans_cutii = []
    for m in porturi.mansoane(S):
        if re.search(r"(?i)\bM\d|manson|mufa|clo", m):
            try: mans_cutii.append(porturi.cutie_nod(S, m))
            except Exception: pass
    in_manson = lambda p: next((b for b in mans_cutii if b[0] - 0.05 <= p[0] <= b[2] + 0.05 and b[1] - 0.05 <= p[1] <= b[3] + 0.05), None)
    cb = [bb.cutie() for bb in toate_benzi]
    langa_banda = lambda p: any(b[0] - 0.2 <= p[0] <= b[2] + 0.2 and b[1] - 0.2 <= p[1] <= b[3] + 0.2 for b in cb)
    for _ in range(400):
        # am ajuns la client / echipament (chenar mic închis cu „CLIENT”, „ODB”, „ECHIPAMENT” lângă el)?
        for f, b in cutii:
            if f.id in ids_benzi: continue
            if b[0] - 0.03 <= cur[0] <= b[2] + 0.03 and b[1] - 0.03 <= cur[1] <= b[3] + 0.03 and _nume_aproape(tx, b, ("CLIENT", "ODB", "ECHIPAMENT"), 0.9):
                capat = (f, b); break
        if capat: break
        cel = None
        trepte = ((0.03, True), (0.03, False)) if cul0 in GRI else \
            ((0.03, True), (0.03, False), (0.45, True)) + (((0.7, True),) if langa_banda(cur) else ())
        for tol, aceeasi in trepte:
            for n, (f, pts, c) in enumerate(B):
                if n in vazut or (aceeasi and c != cul0) or (not aceeasi and (c in GRI or c in ("#000000", "#262626"))): continue
                if pe_start(pts[0]) or pe_start(pts[-1]): continue           # nu mă întorc în ODF-ul de pornire (pe alt port)
                for jj in (0, -1):
                    alt = pts[-1] if jj == 0 else pts[0]
                    if any(math.dist(alt, q) < 0.15 for q in parcurse): continue    # fibra vecină, care merge înapoi pe lângă drumul meu
                    dd = math.dist(pts[jj], cur)
                    if dd < tol and (cel is None or dd < cel[0]): cel = (dd, n, jj)
            if cel: break
        if not cel and cul0 not in GRI:                               # banda unui ODF: fibra iese pe partea cealaltă, în ordinea culorii
            cel = _prin_banda(B, cur, cul0, vazut, toate_benzi, pe_start, parcurse)
        bm = in_manson(cur) if not cel and cul0 not in GRI else None
        if bm:                                                        # în manșon: sudura continuă cu fibra de aceeași culoare din același manșon
            for n, (f, pts, c) in enumerate(B):
                if n in vazut or c != cul0 or pe_start(pts[0]) or pe_start(pts[-1]): continue
                for jj in (0, -1):
                    q = pts[jj]
                    if bm[0] - 0.05 <= q[0] <= bm[2] + 0.05 and bm[1] - 0.05 <= q[1] <= bm[3] + 0.05:
                        dd = math.dist(q, cur)
                        if cel is None or dd < cel[0]: cel = (dd, n, jj)
        if not cel: break
        _, n, jj = cel; vazut.add(n); drum.append(n); cur = B[n][1][-1] if jj == 0 else B[n][1][0]; parcurse += B[n][1]
        if B[n][2] not in GRI: cul0 = B[n][2]
    puncte = [p for n in drum for p in B[n][1]]
    return {"bucati": [B[n] for n in drum], "puncte": puncte, "culoare": B[i][2], "capat": cur, "client": capat,
            "opriri": opriri(S, puncte, cur, nd, k, capat), "nod": nd, "port": k}


def _prin_banda(B, cur, cul0, vazut, benzi, pe_start, parcurse):
    """fibra a ajuns la o bandă (ODF de subinel): intră pe o parte, iese pe cealaltă. A câta fibră de culoarea asta intră
    (în ordinea porturilor) = a câta fibră de aceeași culoare iese pe partea opusă."""
    for bf in benzi:
        x0, y0, x1, y1 = bf.cutie()
        if not (x0 - 0.15 <= cur[0] <= x1 + 0.15 and y0 - 0.15 <= cur[1] <= y1 + 0.15): continue
        oriz = (x1 - x0) >= (y1 - y0); cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        parte = (lambda p: p[1] > cy) if oriz else (lambda p: p[0] > cx)
        de_a_lungul = (lambda p: p[0]) if oriz else (lambda p: -p[1])
        pe_banda = lambda p: x0 - 0.15 <= p[0] <= x1 + 0.15 and y0 - 0.15 <= p[1] <= y1 + 0.15
        intra, ies = [], []
        for n, (f, pts, c) in enumerate(B):
            if c != cul0 or pe_start(pts[0]) or pe_start(pts[-1]): continue
            for jj in (0, -1):
                q = pts[jj]; alt = pts[-1] if jj == 0 else pts[0]
                if not pe_banda(q) or pe_banda(alt): continue
                (intra if parte(q) == parte(cur) else ies).append((de_a_lungul(q), n, jj, q))
        intra.sort(); ies.sort()
        rang = min(range(len(intra)), key=lambda r: math.dist(intra[r][3], cur)) if intra else 0
        libere = [x for x in ies if x[1] not in vazut]
        if not libere: continue
        _, n, jj, q = (ies[rang] if rang < len(ies) and ies[rang][1] not in vazut else libere[0])
        return (math.dist(q, cur), n, jj)
    return None


def opriri(S, puncte, cur, nd, k, capat):
    """prin ce trece fibra, în ordine: manșoane (M1…), ODF-uri de subinel (benzi), clientul de la capăt"""
    tx = _texte(S); out = [("ODF", _nume_aproape(tx, nd.banda.cutie(), ("ODF", "INEL", "CENTRAL")) or nd.nume, k)]
    vazute = set()
    mans = []
    for m in porturi.mansoane(S):
        if not re.search(r"(?i)\bM\d|manson|mufa|clo", m): continue
        try: mans.append((m, porturi.cutie_nod(S, m)))
        except Exception: pass
    b0 = nd.banda.cutie()
    suprapus = lambda b: not (b[2] < b0[0] - 0.05 or b[0] > b0[2] + 0.05 or b[3] < b0[1] - 0.05 or b[1] > b0[3] + 0.05)
    noduri_ = {n.banda.id: n for n in porturi.noduri(S)}
    benzi = [b_ for b_ in porturi.benzi(S) if not suprapus(b_.cutie())]
    for p in puncte:
        for m, b in mans:
            if m not in vazute and b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3]: vazute.add(m); out.append(("manșon", m, None))
        for bf in benzi:
            b = bf.cutie()
            if bf.id not in vazute and b[0] - 0.16 <= p[0] <= b[2] + 0.16 and b[1] - 0.16 <= p[1] <= b[3] + 0.16:
                vazute.add(bf.id); nume = _nume_aproape(tx, b, ("SUBINEL", "ODB", "CLIENT"), 1.3) or _nume_aproape(tx, b, ("ODF",), 1.0) or "ODF"
                kk = None
                n = noduri_.get(bf.id)
                if n is not None:
                    vert, (x0, y0, x1, y1), poz = porturi.porturi_xy(S, n)
                    kk = min(range(len(poz)), key=lambda i: abs(poz[i] - (p[1] if vert else p[0]))) + 1
                if not (out and out[-1][1] == nume): out.append(("ODF", nume, kk))
    if capat:
        b = capat[1]; out.append(("client", _nume_aproape(tx, b, ("CLIENT", "ODB", "ECHIPAMENT"), 0.9) or "client", None))
    else:
        m_in = [m for m, b in mans if b[0] - 0.05 <= cur[0] <= b[2] + 0.05 and b[1] - 0.05 <= cur[1] <= b[3] + 0.05]
        out.append(("capăt", f"se oprește în {m_in[0]} (fibră de rezervă)" if m_in else
                    (_nume_aproape(tx, (cur[0], cur[1], cur[0], cur[1]), ("CLIENT", "ODB", "SUBINEL"), 0.6) or "capătul liniei"), None))
    return out


def _nume_aproape(tx, b, chei, raza=1.2):
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2; best = None
    for t, (x, y), tb in tx:
        if not any(k in t.upper() for k in chei): continue
        if re.fullmatch(r"[\d\s|….]+", t): continue
        d = math.dist((x, y), (cx, cy))
        if d < raza and (best is None or d < best[0]): best = (d, t)
    return best[1] if best else None


def cabluri(S, puncte):
    """etichetele de cablu (FO-12, FO-8…) de lângă traseu, în ordinea în care le întâlnește"""
    tx = [(t, c) for t, c, _ in _texte(S) if re.fullmatch(r"FO-\s*\d+", t)]
    out = []
    for p in puncte[::2]:
        for t, c in tx:
            if math.dist(p, c) < 0.35 and (not out or out[-1] != t): out.append(t)
    return out


NUME_CULORI = {"#0000ff": "albastru", "#3a28d9": "albastru", "#ffc000": "galben", "#ffff00": "galben", "#00b050": "verde", "#00cc00": "verde",
               "#7030a0": "violet", "#ff00ff": "roz", "#9c4a09": "maro", "#993300": "maro", "#ff0000": "roșu", "#7f7f7f": "gri",
               "#000000": "negru", "#262626": "negru", "#ffffff": "alb"}


def descrie(info):
    c = NUME_CULORI.get(info["culoare"], info["culoare"])
    pasi = []
    for tip, nume, k in info["opriri"]:
        pasi.append(f"{nume}" + (f" portul {k}" if k else "") + (" (client)" if tip == "client" else ""))
    return f"Fibra {c}: " + " → ".join(pasi)


# ---------------------------------------------------------------- desenul pe pagină nouă
def deseneaza(doc, S, info):
    """o pagină nouă cu schema simplă a traseului: ODF → manșoane → ODF subinel → client, pe un rând"""
    import elemente
    from desen import Schema
    nume = f"Traseu {info['nod'].nume} p{info['port']}"
    p = doc.pagina_noua(nume); T = Schema(doc, p); W, H = p.dimensiune()
    op = info["opriri"]; n = len(op); cab = cabluri(S, info["puncte"])
    culoare = info["culoare"] if info["culoare"] not in ("#ffffff",) else "#000000"
    elemente.text(T, W / 2, H - 0.8, f"TRASEUL FIBREI: {info['nod'].nume} PORTUL {info['port']} → CLIENT", pt=16, w=W - 2, culoare="#C00000")
    pas = (W - 2.5) / max(n - 1, 1); y = H / 2 + 0.6
    xs = [1.25 + i * pas for i in range(n)]
    for i in range(n - 1):                                            # fibra, în culoarea ei
        porturi._linie(T, (xs[i] + 0.55, y), (xs[i + 1] - 0.55, y), culoare, False, gros=0.03)
        if i < len(cab): elemente.text(T, (xs[i] + xs[i + 1]) / 2, y + 0.22, cab[i], pt=10, w=1.0)
    for x, (tip, nm, k) in zip(xs, op):
        if tip == "manșon":
            elemente.chenar(T, x - 0.55, y - 0.4, x + 0.55, y + 0.4, rotunjit=0.12)
        elif tip == "client":
            elemente.chenar(T, x - 0.55, y - 0.35, x + 0.55, y + 0.35, gros=0.025, culoare="#C00000")
        else:
            elemente.chenar(T, x - 0.55, y - 0.5, x + 0.55, y + 0.5)
            b = elemente._forma(T, x, y, 0.16, 0.6); elemente._cell(b, "FillForegnd", "#FFFF99"); elemente._cell(b, "FillPattern", "1"); elemente._dreptunghi(b)
        elemente.text(T, x, y - 0.75, nm, pt=10, w=1.9)
        if k: elemente.text(T, x, y + 0.65, f"port {k}", pt=10, w=1.2, culoare="#C00000")
    elemente.text(T, W / 2, y - 1.6, descrie(info), pt=10, bold=False, w=W - 2)
    return p


# ---------------------------------------------------------------- din chat
CERE = r"\b(arat\w*|urmar\w*|trase\w*|cum ajunge|unde (ajunge|merge|duce|iese)|drum\w*|traseu\w*|pana la client|la client|verific\w*)\b"
DESEN = r"\b(desen\w*|pagina noua|pagina nou|alta pagina|pe pagina|schema noua|fa schema|fa-mi schema)\b"


ULTIMUL = {}


def din_text(S, cm):
    """„arată portul ODF 2 cum ajunge la client” -> (Nod, 2)"""
    try: men = [m for m in porturi.mentiuni(S, cm) if m[3] is not None]
    except ValueError:                                                # „odf” se potrivește la mai multe: iau nodul numit exact așa
        cuv = re.findall(r"[a-z0-9_/\-]+", cm)
        men = [(cm.find(n.nume.lower()), cm.find(n.nume.lower()) + len(n.nume), n.nume, n) for n in porturi.noduri(S)
               if n.nume.lower() in cuv or n.nume.lower() in cm]
        men = sorted([m for m in men if m[0] >= 0], key=lambda m: (-len(m[2]), m[0]))[:1]
    if not men:                                                       # „arată pentru port 21”: fără nume = ODF-ul de dinainte (sau cel mai mare)
        m = re.search(r"(?:port\w*|p)\s*(\d+)", cm)
        if not m: return None
        ns = porturi.noduri(S)
        nd = next((n for n in ns if n.nume == ULTIMUL.get("nod")), None) or max(ns, key=lambda n: (n.nume.upper().startswith("ODF"), n.n), default=None)
        k = int(m.group(1))
        return (nd, k) if nd and 1 <= k <= nd.n else None
    a, b, nume, nd = men[0]
    m = re.search(r"^\W*(?:port\w*\s*|p\s*)?(\d+)", cm[b:]) or re.search(r"port\w*\s*(\d+)", cm) or re.search(r"\b(\d+)\b", cm[b:])
    if not m: return None
    k = int(m.group(1))
    return (nd, k) if 1 <= k <= nd.n else None


def cerere(app, cm):
    """chat: urmărește fibra și (dacă ceri) o desenează pe o pagină nouă -> mesaj sau None"""
    vrea_desen = re.search(DESEN, cm)
    if not (re.search(CERE, cm) or vrea_desen): return None
    if vrea_desen and not re.search(r"\bport|\bp\d|odf", cm) and getattr(app, "ultim_traseu", None):
        info, ip = app.ultim_traseu
        from desen import Schema
        S0 = Schema(app.doc, app.doc.pagini[ip])
        with app.chat.lacat:
            app.inainte_de_modificare(); pg = deseneaza(app.doc, S0, info)
        app.chat.ip = app.doc.pagini.index(pg); app.modificat = True; app.selectie = []; app.actualizeaza_pagini(); app.potriveste()
        return f"Am desenat traseul pe pagina nouă „{pg.nume}”."
    if app.doc.pagini[app.chat.ip].nume.startswith("Traseu") and getattr(app, "ultim_traseu", None):
        app.chat.ip = app.ultim_traseu[1]; app.actualizeaza_pagini()           # urmăresc pe schema de unde am plecat, nu pe pagina desenată
    S = app.chat.schema
    np_ = din_text(S, cm)
    if not np_: return None
    nd, k = np_
    info = urmareste(S, nd, k)
    if info is None: return f"La {nd.nume} portul {k} e liber – nu pleacă nicio fibră din el."
    app.ultim_traseu = (info, app.chat.ip); ULTIMUL["nod"] = nd.nume
    app.selectie = [f for f, _, _ in info["bucati"]]; app.zoom_pe(app.selectie)
    msg = descrie(info) + "."
    cab = cabluri(S, info["puncte"])
    if cab: msg += " Cabluri pe drum: " + ", ".join(cab) + "."
    msg += f" Am selectat-o pe schemă ({len(info['bucati'])} bucăți de linie)."
    if vrea_desen:
        with app.chat.lacat:
            app.inainte_de_modificare(); pg = deseneaza(app.doc, S, info)
        app.chat.ip = app.doc.pagini.index(pg); app.modificat = True; app.selectie = []; app.actualizeaza_pagini(); app.potriveste()
        msg += f" Am desenat traseul pe pagina nouă „{pg.nume}”."
    else:
        msg += " Scrie „deseneaza-l pe pagina noua” ca să-l desenez separat."
    return msg
