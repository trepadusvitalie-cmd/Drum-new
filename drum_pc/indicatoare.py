"""Clasificarea indicatoarelor rutiere după Regulamentul circulației rutiere (HG nr. 357/2009, Anexa nr. 3).
Fiecare chenar „semn” se compară cu desenele oficiale din rcr/icoane: culorile pe zone (roșu, albastru, galben,
alb, negru…) în interiorul formei indicatorului, conturul (gradienții) și proporțiile. Rezultatul: numărul din
regulament (de ex. 2.2 = STOP), denumirea, categoria și încrederea."""
import json, os, sys
import cv2, numpy as np

S = 40                                    # mărimea la care se compară
AICI = os.path.dirname(os.path.abspath(__file__))
# culori: 0 alt, 1 roșu, 2 albastru, 3 galben, 4 alb, 5 negru, 6 verde, 7 maro/portocaliu
NC = 8


def _dir():
    return os.path.join(getattr(sys, "_MEIPASS", AICI), "rcr")


def clase_culoare(bgr):
    """Clasa de culoare a fiecărui pixel, cu luminozitatea raportată la imagine (umbră, contre-jour)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV); H, Sa, V = [hsv[..., i].astype(np.float32) for i in range(3)]
    Vn = V / max(60.0, float(np.percentile(V, 97)))
    c = np.zeros(H.shape, np.int8)
    col = Sa > 70
    c[col & ((H < 9) | (H > 160)) & (Vn > 0.25)] = 1
    c[col & (H >= 95) & (H <= 135) & (Vn > 0.2)] = 2
    c[col & (H >= 18) & (H <= 34) & (Vn > 0.5)] = 3
    c[col & (H >= 9) & (H < 18)] = 7
    c[col & (H > 34) & (H < 95)] = 6
    c[(Sa <= 70) & (Vn > 0.62)] = 4
    c[(Vn < 0.33) & (c == 0)] = 5
    return c


def _hog(gray):
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0); gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1)
    mag = np.hypot(gx, gy); ang = (np.arctan2(gy, gx) % np.pi) / np.pi * 8
    b = np.minimum(ang.astype(int), 7); h = np.zeros((5, 5, 8), np.float32); cs = S // 5
    for i in range(5):
        for j in range(5):
            m = mag[i * cs:(i + 1) * cs, j * cs:(j + 1) * cs].ravel(); bb = b[i * cs:(i + 1) * cs, j * cs:(j + 1) * cs].ravel()
            h[i, j] = np.bincount(bb, m, 8)
    h = h.ravel(); return h / (np.linalg.norm(h) + 1e-6)


def _norm(gr, masca=None):
    """Tonurile de gri (desenul din interior), centrate și normate – pentru corelație."""
    g = cv2.GaussianBlur(gr, (3, 3), 0.8)
    if masca is not None: g = np.where(masca, g, g[masca].mean() if masca.any() else 128)
    g = g - g.mean(); return (g / (np.linalg.norm(g) + 1e-6)).ravel()


def _patrat(img, fond):
    """Imaginea în pătratul S×S, cu proporțiile păstrate (centrată)."""
    h, w = img.shape[:2]; k = S / max(h, w); nw, nh = max(1, round(w * k)), max(1, round(h * k))
    out = np.full((S, S) + img.shape[2:], fond, img.dtype)
    x, y = (S - nw) // 2, (S - nh) // 2
    out[y:y + nh, x:x + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    return out


def trasaturi(crop):
    """Vectorul de trăsături al unui chenar: culorile pe zone (16×16), conturul (HOG) și tonurile de gri (20×20)."""
    q = _patrat(crop, 128)
    c = clase_culoare(q); oh = np.zeros((16, 16, NC), np.float32)
    for k in range(NC): oh[..., k] = cv2.resize((c == k).astype(np.float32), (16, 16), interpolation=cv2.INTER_AREA)
    gr = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g2 = cv2.resize(gr, (20, 20), interpolation=cv2.INTER_AREA); g2 = (g2 - g2.mean()) / (g2.std() + 1e-3)
    h, w = crop.shape[:2]
    return np.concatenate([oh.ravel(), _hog(gr) * 4, g2.ravel() * 0.25, [np.log(w / h)]]).astype(np.float32)


class Clasificator:
    def __init__(self, folder=None):
        folder = folder or _dir()
        self.info = json.load(open(os.path.join(folder, "indicatoare.json"), encoding="utf-8"))
        cul, masca, hog, ar, gri = [], [], [], [], []
        for r in self.info:
            im = cv2.imread(os.path.join(folder, "icoane", r["nr"] + ".png"), cv2.IMREAD_UNCHANGED)
            if im.ndim == 2: im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGRA)
            if im.shape[2] == 3: im = cv2.cvtColor(im, cv2.COLOR_BGR2BGRA)
            ar.append(im.shape[1] / im.shape[0])
            q = _patrat(im, 0); a = q[..., 3] > 128
            al = q[..., 3:].astype(np.float32) / 255; bgr = (q[..., :3] * al + 128 * (1 - al)).astype(np.uint8)
            cul.append(np.where(a, clase_culoare(bgr), -1).ravel()); masca.append(a.ravel())
            gr = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
            hog.append(_hog(gr)); gri.append(_norm(gr, a))
        self.cul = np.array(cul); self.masca = np.array(masca); self.hog = np.array(hog); self.ar = np.log(np.array(ar))
        self.gri = np.array(gri)
        self.arie = self.masca.sum(1).clip(1)
        # cât din fiecare culoare are desenul (pentru potrivirea „globală” a paletei)
        self.paleta = np.stack([((self.cul == k).sum(1) / self.arie) for k in range(NC)], 1)
        # rețeaua mică antrenată pe imagini sintetice din aceste desene (dacă există, are întâietate)
        f = os.path.join(folder, "model_indicatoare.npz"); self.retea = None
        if os.path.exists(f):
            z = np.load(f); self.retea = {k: z[k].astype(np.float32) for k in ("mu", "sd", "W1", "b1", "W2", "b2")}
            self.clase = [c.split("|")[0] for c in z["clase"]]

    def scoruri(self, crop):
        if crop is None or crop.size == 0 or min(crop.shape[:2]) < 8: return None
        h, w = crop.shape[:2]
        q = _patrat(crop, 128)
        c = clase_culoare(q).ravel()
        loc = ((self.cul == c[None]) & self.masca).sum(1) / self.arie               # culoarea potrivită pe zone
        pal_c = np.stack([((c[None] == k) & self.masca).sum(1) / self.arie for k in range(NC)], 1)
        pal = 1 - 0.5 * np.abs(pal_c - self.paleta).sum(1)                            # paleta întreagă
        gr = cv2.cvtColor(q, cv2.COLOR_BGR2GRAY).astype(np.float32)
        g = self.hog @ _hog(gr)
        gn = _norm(gr)                                          # corelația tonurilor în interiorul formei fiecărui desen
        m = self.masca; gm = np.where(m, gn[None], 0); gm -= (gm.sum(1) / self.arie)[:, None] * m
        ncc = (gm * self.gri).sum(1) / (np.linalg.norm(gm, axis=1) + 1e-6)
        prop = np.exp(-2.0 * np.abs(np.log(w / h) - self.ar))
        return (0.35 * loc + 0.15 * pal + 0.25 * g + 0.25 * ncc) * (0.6 + 0.4 * prop)

    def probabilitati(self, crop):
        if crop is None or crop.size == 0 or min(crop.shape[:2]) < 8: return None
        P = self.retea; x = (trasaturi(crop) - P["mu"]) / P["sd"]
        z = np.maximum(0, x @ P["W1"] + P["b1"]) @ P["W2"] + P["b2"]
        z = np.exp(z - z.max()); return z / z.sum()

    def clasifica(self, crop, top=3):
        """-> [(nr, scor), …] cele mai potrivite indicatoare din regulament."""
        if self.retea is not None:
            p = self.probabilitati(crop)
            if p is None: return []
            return [(self.clase[i], float(p[i])) for i in np.argsort(-p)[:top]]
        s = self.scoruri(crop)
        if s is None: return []
        idx = np.argsort(-s)[:top]
        return [(self.info[i]["nr"], float(s[i])) for i in idx]

    def detalii(self, nr):
        return next((r for r in self.info if r["nr"] == nr), None)


_cl = None


def clasificator():
    global _cl
    if _cl is None:
        try: _cl = Clasificator()
        except Exception as e:                                   # fără rcr/ – programul merge mai departe fără clasificare
            print("indicatoare: clasificatorul nu s-a încărcat:", e); _cl = False
    return _cl or None


def vot(obs):
    """Indicatorul unui obiect din toate cadrele în care s-a văzut: vot ponderat cu mărimea chenarului și scorul.
    -> (nr, încredere 0..1) sau (None, 0)."""
    tot = {}; sw = 0.0
    for o in obs:
        for k, (nr, sc) in enumerate(o.get("rcr") or []):
            w = (o["box"][2] - o["box"][0]) * sc * (1.0 if k == 0 else 0.35)
            tot[nr] = tot.get(nr, 0) + w
        if o.get("rcr"): sw += (o["box"][2] - o["box"][0]) * o["rcr"][0][1]
    if not tot: return None, 0.0
    nr = max(tot, key=tot.get)
    return nr, round(min(1.0, tot[nr] / max(sw, 1e-6)), 2)
