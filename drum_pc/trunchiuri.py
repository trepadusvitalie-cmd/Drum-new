"""Împărțirea pe trunchiuri: la alei și aliniamente dese, modelul pune un singur chenar peste un rând
întreg de copaci. Aici chenarul se desface în trunchiuri, fiecare cu baza lui (de unde se calculează
poziția pe sol), după culoare (scoarță închisă / maro, nu frunziș verde) și formă (verticală, îngustă).
"""
import cv2
import numpy as np

LAT_RAND = 0.22          # un chenar de copac mai lat de 22% din cadru e probabil un rând de copaci
MIN_TRUNCHIURI = 2       # se înlocuiește chenarul doar dacă ies cel puțin 2 trunchiuri
PRAG_COPAC = 0.25        # doar un copac sigur al modelului (peste prag) „acoperă” trunchiurile găsite în dreptul lui


def masca_drum(img, hsv=None):
    """Carosabilul / drumul de pământ: zona mare, fără frunziș, legată de marginea de jos a cadrului,
    în dreptul mijlocului (drumul pe care merge mașina). Se mărește puțin ca să cuprindă și marginile."""
    hsv = hsv if hsv is not None else cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, W = img.shape[:2]
    h, s, v = [hsv[..., i].astype(np.float32) for i in range(3)]
    nu_verde = ~((h >= 30) & (h <= 90) & (s > 45))
    asfalt = (s < 80) & (v > 25)                              # asfalt / pietriș: cenușiu (și verzui de la lumina prin frunze), și în umbră
    pamant = ((nu_verde & (v > 70)) | asfalt).astype(np.uint8)
    pamant = cv2.medianBlur(pamant * 255, 7) > 127                # umbrele și petele de lumină nu rup drumul
    pamant = cv2.morphologyEx(pamant.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(pamant, 4)
    drum = np.zeros((H, W), bool)
    for i in range(1, n):
        x, y, w, hh, a = st[i]
        if y + hh >= H - 2 and a > 0.01 * H * W and x < W * 0.65 and x + w > W * 0.35:   # atinge jos, în dreptul mijlocului
            z = lab == i
            # trunchiurile lipite de drum nu sunt drum: pe fiecare rând se păstrează doar porțiunea continuă din mijlocul drumului
            for r in np.where(z.any(1))[0]:
                c = np.where(z[r])[0]; mij = int(np.median(c))
                st_ = mij; dr_ = mij
                while st_ > 0 and z[r, st_ - 1]: st_ -= 1
                while dr_ < W - 1 and z[r, dr_ + 1]: dr_ += 1
                drum[r, st_:dr_ + 1] = True
    return cv2.dilate(drum.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0


def masca_scoarta(img):
    """1 = pixel de scoarță: mai închis decât ce-l înconjoară și nu verde, sau maro (scoarță luminată)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = [hsv[..., i].astype(np.float32) for i in range(3)]
    verde = (h >= 30) & (h <= 90) & (s > 60) & (v > 95)          # frunziș: verde ȘI luminos (scoarța umbrită e verde-închis)
    fond = cv2.blur(v, (41, 41))
    inchis = (v < 0.82 * fond) & (v < 150)
    maro = (h <= 25) & (s >= 40) & (s <= 190) & (v >= 40) & (v <= 190)
    m = ((inchis | maro) & ~verde & ~masca_drum(img, hsv)).astype(np.uint8)   # pe carosabil nu cresc copaci
    global _brut, _vegetatie, _fundal; _brut = m.copy(); _vegetatie = ((h >= 25) & (h <= 95) & (s > 40)).astype(np.float32)
    _fundal = (((h >= 25) & (h <= 95) & (s > 40) & (v > 110)) | ((s < 40) & (v > 190))).astype(np.float32)   # iarbă/frunze luminate sau cer (nu mușchi pe scoarță)                           # masca înainte de netezire: pentru coborârea bazei
    H = img.shape[0]
    k = max(15, int(0.035 * H))
    # trunchiurile pot fi și înclinate: se păstrează liniile lungi verticale sau aplecate până la ~20°
    sus = np.zeros_like(m)
    for grade in (-20, -10, 0, 10, 20):
        ker = np.zeros((k, k), np.uint8); c = k // 2; dx = int(round(c * np.tan(np.radians(grade))))
        cv2.line(ker, (c - dx, 0), (c + dx, k - 1), 1, 1)
        sus |= cv2.morphologyEx(m, cv2.MORPH_OPEN, ker)
    m = cv2.morphologyEx(sus, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (3, k)))
    return m


_brut = None
_vegetatie = None
_fundal = None


def coboara_baza(xb, yb, H, latime=2, gol=4):
    """Baza se coboară de-a lungul trunchiului cât timp sub ea e tot scoarță (umbrele și tufele rup masca
    netezită mai sus decât solul). Trunchiul poate fi înclinat: pe fiecare rând se urmărește mijlocul scoarței,
    care se poate muta cu câte 1–2 pixeli în lateral. -> (x, y) unde trunchiul atinge pământul."""
    if _brut is None: return xb, yb
    W = _brut.shape[1]; x, y, lips = float(xb), int(yb), 0
    while y + 1 < H:
        a, b = max(0, int(x) - latime - 2), min(W, int(x) + latime + 3)
        c = np.where(_brut[y + 1, a:b] > 0)[0]
        if len(c) >= max(1, latime):
            x = 0.5 * x + 0.5 * (a + float(np.median(c))); y += 1; lips = 0
        elif lips < gol: y += 1; lips += 1
        else: break
    return x, y - lips


def vai(profil, a, b, adanc=0.45, minim=3):
    """Trunchiuri lipite fără spațiu între ele: se taie la „văile” profilului (coloane mai puțin pline
    între două trunchiuri). -> listă de intervale (a, b)."""
    p = np.convolve(profil[a:b].astype(float), np.ones(3) / 3, mode="same")
    taieri = []
    for i in range(minim, len(p) - minim):
        if p[i] <= p[i - 1] and p[i] <= p[i + 1]:
            st, dr = p[:i].max(), p[i + 1:].max()
            if p[i] < adanc * min(st, dr) and (not taieri or i - taieri[-1] >= minim): taieri.append(i)
    lim = [0] + taieri + [len(p)]
    return [(a + lim[k], a + lim[k + 1]) for k in range(len(lim) - 1) if lim[k + 1] - lim[k] >= 2]


def trunchiuri(img, box, masca=None):
    """Trunchiurile din chenarul box=(x0,y0,x1,y1) -> listă (x0, y0, x1, y_baza), de la stânga la dreapta.
    Baza trebuie să fie în jumătatea de jos a chenarului (unde trunchiul atinge solul)."""
    H, W = img.shape[:2]
    x0, y0, x1, y1 = [int(round(v)) for v in box]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 - x0 < 8 or y1 - y0 < 20: return []
    m = (masca if masca is not None else masca_scoarta(img))[y0:y1, x0:x1]
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    bh = y1 - y0; res = []
    for i in range(1, n):
        x, y, w, h, _a = st[i]
        if h < max(25, 0.12 * bh): continue
        comp = (lab[y:y + h, x:x + w] == i)
        # trunchiuri lipite (rând des): se despart după coloanele goale din partea de jos a bucății
        jos = comp[int(h * 0.55):].sum(0)
        plin = jos > 0.3 * (h - int(h * 0.55))           # coloana e plină pe măcar 30% din partea de jos (nu raportat la cel mai gros)
        bucati, k = [], 0
        while k < w:
            if plin[k]:
                j = k
                while j < w and plin[j]: j += 1
                bucati += vai(jos, k, j); k = j
            else: k += 1
        for a, b in bucati:
            sub = comp[:, a:b]; rows = np.where(sub.any(1))[0]
            if len(rows) == 0: continue
            top, bot = rows[0], rows[-1]; hh = bot - top + 1
            ww = sub.sum() / max(1, hh)                        # grosimea medie (un trunchi înclinat are chenarul lat)
            if hh < max(25, 0.12 * bh) or hh < 2.2 * ww or ww > 0.09 * W: continue
            if y + bot < 0.55 * bh: continue                # baza prea sus: e o creangă, nu un trunchi pe sol
            ys, xs = np.where(sub[top:bot + 1])
            xb = a + float(np.median(xs[ys >= hh - 6]))
            xj, yb = coboara_baza(x0 + x + xb, y0 + y + bot, H)
            res.append([min(x0 + x + a, xj - 1), y0 + y + top, max(x0 + x + b, xj + 1), yb, xj])
    # bazele unui rând stau pe o linie (solul în perspectivă): cele mult deasupra ei sunt crengi sau tufe.
    # Fiecare parte a drumului are linia ei (în perspectivă cele două margini urcă spre punctul de fugă).
    def linia_solului(res):
        if len(res) >= 4:
            xs_ = np.array([r[4] for r in res]); yb_ = np.array([r[3] for r in res], float)
            a_, b_ = np.polyfit(xs_, yb_, 1); rez = yb_ - (a_ * xs_ + b_)
            ok = rez > -max(0.03 * H, 2.0 * np.median(np.abs(rez)))      # linia solului refăcută fără cele din aer
            if ok.sum() >= 3: a_, b_ = np.polyfit(xs_[ok], yb_[ok], 1); rez = yb_ - (a_ * xs_ + b_)
            prag = max(0.025 * H, 2.0 * np.median(np.abs(rez[ok] if ok.any() else rez)))
            bune = []
            for r, e in zip(res, rez):
                if e > -prag: bune.append(r); continue             # copacii apropiați au baza mai jos: e normal
                # baza „în aer”: dacă sub ea, până la linia solului, e doar iarbă/tufă, baza e ascunsă -> se pune pe sol
                ysol = int(a_ * r[4] + b_)
                if ysol - r[3] <= 0.12 * H and _vegetatie is not None:
                    c0, c1 = max(0, int(r[4]) - 2), min(W, int(r[4]) + 3)
                    if _vegetatie[int(r[3]) + 1:ysol + 1, c0:c1].mean() >= 0.6:
                        r[3] = ysol; bune.append(r)
            return bune
        return res
    stg = [r for r in res if r[4] < W / 2]; dr = [r for r in res if r[4] >= W / 2]
    res = linia_solului(stg) + linia_solului(dr)
    # același trunchi rupt în bucăți (umbre, crengi): bazele apropiate se unesc, rămâne cea mai înaltă bucată
    res.sort(key=lambda r: r[4]); uniti = []
    for r in res:
        if uniti and abs(uniti[-1][4] - r[4]) < max(6, 0.012 * W) and abs(uniti[-1][3] - r[3]) < 0.03 * H:
            if r[3] - r[1] > uniti[-1][3] - uniti[-1][1]: uniti[-1] = r
        else:
            uniti.append(r)
    # copac înclinat tăiat în două bucăți: bucata de sus „se termină” în aer, iar trunchiul continuă oblic
    # până la baza bucății de jos. Dacă de la baza de sus la baza de jos e scoarță tot drumul, e același copac.
    if _brut is not None and len(uniti) >= 2:
        def scoarta_pe_drum(p, q):
            n = int(max(abs(q[3] - p[3]), abs(q[4] - p[4]))) + 1; bun = 0
            for t in np.linspace(0, 1, n):
                x, y = int(p[4] + t * (q[4] - p[4])), int(p[3] + t * (q[3] - p[3]))
                if _brut[min(H - 1, y), max(0, x - 3):min(W, x + 4)].any(): bun += 1
            return bun / n
        sterse = set()
        for i, p in enumerate(uniti):
            for j, q in enumerate(uniti):
                if i == j or j in sterse: continue
                if q[3] - p[3] > 0.06 * H and abs(q[4] - p[4]) < 0.1 * W and q[1] < p[3] and scoarta_pe_drum(p, q) >= 0.85:
                    sterse.add(i); break
        uniti = [r for i, r in enumerate(uniti) if i not in sterse]
    return [(r[0], r[1], r[2], r[3]) for r in uniti]


def coroane(img, baze, drum):
    """A doua verificare, pe fiecare cadru: copacii a căror tulpină nu se vede (ascunsă de tufe, iarbă înaltă)
    se găsesc după coroana verde. Coroana = pată mare de frunziș, separată de vecine prin cer sau gol,
    sub care nu s-a găsit niciun trunchi. Baza se pune sub mijlocul coroanei, pe linia solului.
    baze = listă (x, y) a trunchiurilor găsite. -> listă (x0, y0, x1, y_baza) pentru copacii noi."""
    H, W = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); h, s, v = [hsv[..., i].astype(np.float32) for i in range(3)]
    frunze = ((h >= 25) & (h <= 95) & (s > 50) & (v > 50)).astype(np.uint8)
    k = max(9, int(0.02 * H)) | 1
    frunze = cv2.morphologyEx(frunze, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    frunze = cv2.morphologyEx(frunze, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    if drum is not None and drum.any():
        y_sol = int(np.where(drum.any(1))[0].min())                      # capătul îndepărtat al drumului
    else:
        y_sol = int(0.6 * H)
    frunze[y_sol:] = 0                                                   # coroanele sunt deasupra solului
    n, lab, st, cen = cv2.connectedComponentsWithStats(frunze, 8)
    # linia solului pe fiecare parte, din bazele trunchiurilor (în perspectivă urcă spre mijloc)
    def y_baza(x):
        parte = [b for b in baze if (b[0] < W / 2) == (x < W / 2)]
        if len(parte) >= 2:
            xs = np.array([b[0] for b in parte]); ys = np.array([b[1] for b in parte], float)
            a_, b_ = np.polyfit(xs, ys, 1); return float(a_ * x + b_)
        if parte: return float(parte[0][1])
        return None
    noi = []
    for i in range(1, n):
        x, y, w, hh, a = st[i]
        if a < 0.004 * H * W or w > 0.3 * W or hh < 0.08 * H: continue   # prea mică, sau un acoperiș întreg de frunze
        if x <= 1 or x + w >= W - 1: continue                           # tăiată de marginea cadrului: nu se știe mijlocul
        cx = float(cen[i][0])
        if any(x - 0.02 * W <= b[0] <= x + w + 0.02 * W for b in baze): continue   # are deja trunchi sub ea
        yb = y_baza(cx)
        if yb is None or yb <= y + hh * 0.5: continue
        if drum is not None and drum[int(min(H - 1, yb)), int(cx)]: continue        # nu pe drum
        noi.append((cx - 0.01 * W, float(y), cx + 0.01 * W, yb))
    return noi


def imparte(img, dets, prag_rand=0.08):
    """Detecțiile modelului (x0,y0,x1,y1,scor,clasa): chenarele late de „copac” (rânduri de copaci) se
    înlocuiesc cu câte un chenar pe trunchi. Pentru rânduri se acceptă și scor mai mic (prag_rand):
    un rând de copaci are scor mic tocmai fiindcă nu seamănă cu un singur copac."""
    H, W = img.shape[:2]; masca = None; out = []; noi = []
    este_copac = lambda lab: "copac" in lab.lower() or "tree" in lab.lower()
    for x0, y0, x1, y1, s, lab in dets:
        lat = (x1 - x0) / W
        if este_copac(lab) and lat < LAT_RAND and s >= PRAG_COPAC:
            # un copac sigur al modelului: poate avea în chenar încă un copac (doi copaci lipiți), iar dacă
            # chenarul iese sub cadru, baza poate fi totuși în imagine (trunchiul stă pe iarbă deasupra marginii)
            if masca is None: masca = masca_scoarta(img)
            tr = [t for t in trunchiuri(img, (x0, y0, x1, y1), masca)
                  if t[3] < H - 4 and t[3] - t[1] >= 0.2 * (min(y1, H) - max(y0, 0))
                  and t[3] - max(y0, 0) >= 0.85 * (min(y1, H) - max(y0, 0))]   # baza jos, lângă baza copacului (nu un copac din fundal)
            tr = [t for i, t in enumerate(tr) if all(abs((t[0] + t[2]) / 2 - (u[0] + u[2]) / 2) > 0.025 * W for u in tr[:i])]
            # doi copaci alăturați au bazele la aceeași înălțime; un copac înclinat dă două bucăți la înălțimi diferite
            if len(tr) >= 2:
                jos_ = max(t[3] for t in tr)
                tr = [t for t in tr if jos_ - t[3] <= 0.06 * H]
            # copaci diferiți doar dacă între ei se vede fundal; altfel e un trunchi gros cu scoarța pătată de lumină
            if len(tr) >= 2 and _brut is not None:
                tr.sort(key=lambda t: t[0]); grup = [tr[0]]
                for t in tr[1:]:
                    p = grup[-1]
                    # jos, lângă baze (ultimii ~12% din trunchi): între cele două trunchiuri trebuie să existe
                    # măcar o coloană fără scoarță (fundal); trunchiurile înclinate au chenarele suprapuse sus
                    y1_ = int(min(p[3], t[3])); y0_ = int(max(0, y1_ - 0.12 * (y1_ - min(p[1], t[1]))))
                    a, b = int((p[0] + p[2]) / 2), int((t[0] + t[2]) / 2)
                    # fundal = frunziș/iarbă verde sau cer; scoarța luminată de soare e cenușie, nu fundal
                    prof = _vegetatie[y0_:y1_, a:b].mean(0) if b > a and y1_ > y0_ else np.zeros(1)
                    gol = abs(b - a) >= max(4, 0.02 * W) and prof.max() > 0.6
                    if gol: grup.append(t)
                    else: grup[-1] = (min(p[0], t[0]), min(p[1], t[1]), max(p[2], t[2]), max(p[3], t[3]))
                tr = grup
            if len(tr) >= 2:
                for a, b, c, d in tr: out.append((float(a), float(y0), float(c), float(d), s, lab))
                continue
            if y1 >= H - 3 and tr:
                out.append((x0, y0, x1, float(tr[0][3]), s, lab)); continue
            # chenarul modelului se oprește uneori la jumătatea trunchiului: baza se caută mai jos, pe același trunchi
            # (dacă trunchiul merge până la marginea de jos, baza nu se vede: chenarul ajunge jos și copacul se ia
            #  din alt cadru, nu cu baza „în aer” la jumătatea trunchiului)
            jos = [t for t in trunchiuri(img, (x0, y0, x1, H), masca) if t[3] > y1 + 0.02 * H and t[1] < y1]
            if jos: y1 = float(max(jos, key=lambda t: t[3] - t[1])[3])
            out.append((x0, y0, x1, y1, s, lab)); continue
        if not este_copac(lab) or lat < LAT_RAND or s < prag_rand:
            out.append((x0, y0, x1, y1, s, lab)); continue
        if masca is None: masca = masca_scoarta(img)
        tr = trunchiuri(img, (x0, y0, x1, y1), masca)
        if len(tr) < MIN_TRUNCHIURI:
            out.append((x0, y0, x1, y1, s, lab)); continue
        sc = max(s, 0.26)                                   # trunchi găsit pe formă: trece pragul copacilor
        for a, b, c, d in tr:
            noi.append((float(a), float(y0 if y0 < b else b), float(c), float(d), sc, lab))
    # un trunchi găsit de două ori (rânduri suprapuse) sau care e deja un copac detectat de model rămâne o dată
    singuri = [d for d in out if este_copac(d[5]) and (d[2] - d[0]) / W < LAT_RAND and d[4] >= PRAG_COPAC]
    pastrate = []
    for d in sorted(noi, key=lambda d: -(d[3] - d[1])):
        cx = (d[0] + d[2]) / 2
        if any(a <= cx <= c for a, _, c, _, _, _ in singuri): continue
        if any(abs(cx - (p[0] + p[2]) / 2) < max(6, 0.008 * W) and abs(d[3] - p[3]) < 0.05 * H for p in pastrate): continue
        pastrate.append(d)
    # baza trebuie să fie pe pământ: nu mai sus de capătul îndepărtat al drumului (orizontul solului).
    # Tot ce are „baza” mai sus e o bucată de trunchi sau de crengi văzută în aer -> nu se pune pe hartă.
    drum = masca_drum(img)
    if drum.any():
        y_sol = np.where(drum.any(1))[0].min() - 0.01 * H
        rez = [d for d in out + pastrate if not este_copac(d[5]) or d[3] >= y_sol]
    else:
        rez = out + pastrate
    # același copac numărat de mai multe ori: două baze mai apropiate decât grosimea trunchiului la sol
    # (măsurată pe rândul de deasupra bazei, pe toată pata de scoarță continuă) sunt un singur copac
    if _brut is not None:
        def grosime(d):
            # pe trei rânduri deasupra bazei: lățimea pătei de scoarță și mijlocul ei (mediana). Un copac nu e mai
            # gros de ~7% din cadru.
            x = int(min(W - 1, max(0, (d[0] + d[2]) / 2))); latimi, mijloace = [], []
            for f in (0.03, 0.07, 0.11):
                y = int(min(H - 1, max(0, d[3] - f * H)))
                rand = cv2.dilate(_brut[y:y + 1], np.ones((1, 9), np.uint8))[0]
                x_ = x
                if not rand[x_]:                                  # cel mai apropiat pixel de scoarță (bucata găsită e lângă trunchi)
                    c = np.where(rand[max(0, x - int(0.04 * W)):x + int(0.04 * W) + 1])[0]
                    if not len(c): continue
                    x_ = max(0, x - int(0.04 * W)) + int(c[np.argmin(np.abs(c + max(0, x - int(0.04 * W)) - x))])
                a = x_
                while a > 0 and rand[a - 1]: a -= 1
                b = x_
                while b < W - 1 and rand[b + 1]: b += 1
                latimi.append(b - a + 1); mijloace.append((a + b) / 2)
            if not latimi: return 0.01 * W, x
            return min(float(np.median(latimi)), 0.07 * W), float(np.median(mijloace))
        def fundal_intre(d, f):
            # între cele două trunchiuri, puțin deasupra bazelor, se vede iarbă/frunziș -> sunt doi copaci
            y1_ = int(min(d[3], f[3])); y0_ = int(max(0, y1_ - 0.08 * H))
            a, b = sorted((int((d[0] + d[2]) / 2), int((f[0] + f[2]) / 2)))
            return b > a + 2 and _fundal is not None and _fundal[y0_:y1_, a:b].mean(0).max() > 0.6
        # bucățile aceluiași copac se adună într-un grup; din grup rămâne bucata cea mai apropiată de mijlocul
        # trunchiului (cea care stă pe trunchi), nu cea cu scorul cel mai mare
        copaci = sorted([d for d in rez if este_copac(d[5])], key=lambda d: -d[4])
        alte = [d for d in rez if not este_copac(d[5])]; grupuri = []
        for d in copaci:
            cx = (d[0] + d[2]) / 2; g, _ = grosime(d)
            for gr in grupuri:
                f = gr[0]
                if abs(cx - (f[0] + f[2]) / 2) < 0.9 * max(g, grosime(f)[0]) and abs(d[3] - f[3]) < 0.05 * H and not fundal_intre(d, f):
                    gr.append(d); break
            else:
                grupuri.append([d])
        finale = []
        for gr in grupuri:
            mij = float(np.median([grosime(d)[1] for d in gr]))
            finale.append(min(gr, key=lambda d: abs((d[0] + d[2]) / 2 - mij)))
        # punctul se mută pe cel mai apropiat trunchi gros de lângă bază (nu pe o umbră, un stâlp sau o margine);
        # o bucată subțire fără trunchi gros lângă ea e un stâlp sau o umbră -> nu e copac
        gros = max(4, 0.006 * W); finale2 = []
        for d in finale:
            cx = (d[0] + d[2]) / 2; cand = []
            for f in (0.03, 0.06, 0.09):
                y = int(min(H - 1, max(0, d[3] - f * H)))
                rand = cv2.morphologyEx(_brut[y:y + 1], cv2.MORPH_CLOSE, np.ones((1, 5), np.uint8))[0]
                x = 0
                while x < W:
                    if rand[x]:
                        a = x
                        while x < W and rand[x]: x += 1
                        if x - a >= gros and min(x - a, 0.07 * W) == x - a: cand.append(((a + x - 1) / 2, x - a))
                    else: x += 1
            aproape = [c for c in cand if abs(c[0] - cx) <= 0.06 * W]
            if aproape:
                m = float(np.median([c[0] for c in aproape if abs(c[0] - min(aproape, key=lambda c: abs(c[0] - cx))[0]) < gros * 2]))
                lat = max(2, (d[2] - d[0]) / 2)
                d = (m - lat, d[1], m + lat, d[3], d[4], d[5])
            elif d[2] - d[0] < gros:
                continue
            finale2.append(d)
        # după mutare, două puncte pe același trunchi -> unul
        finale = []
        for d in sorted(finale2, key=lambda d: -d[4]):
            if any(abs((d[0] + d[2]) / 2 - (f[0] + f[2]) / 2) < gros * 1.5 and abs(d[3] - f[3]) < 0.05 * H for f in finale): continue
            finale.append(d)
        rez = alte + finale
    # a doua verificare: copacii fără tulpină vizibilă, după coroană
    lab0 = next((d[5] for d in rez if este_copac(d[5])), "copac")
    baze = [((d[0] + d[2]) / 2, d[3]) for d in rez if este_copac(d[5])]
    for a, b, c, d in coroane(img, baze, masca_drum(img)):
        rez.append((a, b, c, d, PRAG_COPAC + 0.01, lab0))
    return rez
