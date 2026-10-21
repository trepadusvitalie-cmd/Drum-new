"""Antrenează clasificatorul de indicatoare (rețea mică, numpy) pe imagini sintetice din desenele oficiale (Anexa 3).
Rulare: python antrenare_indicatoare.py 150 30  ->  model_indicatoare.npz"""
import os, sys, glob, random, time, cv2, numpy as np, json, hashlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import indicatoare
from multiprocessing import Pool
R = os.path.dirname(os.path.abspath(__file__)) + "/"
info = json.load(open(R + "indicatoare.json"))
# desene identice -> o singură clasă
grup = {}
for r in info:
    h = hashlib.md5(open(R + "icoane/" + r["nr"] + ".png", "rb").read()).hexdigest()
    grup.setdefault(h, []).append(r["nr"])
clase = list(grup.values()); print(len(info), "indicatoare,", len(clase), "desene distincte")
BG = sorted(glob.glob(os.path.join(R, "..", "..", "..", "training", "drum", "cm_*.jpg")))
def sint(args):
    ci, seed = args
    random.seed(seed); np.random.seed(seed % 2**32)
    bg = cv2.imread(random.choice(BG))
    nr = clase[ci][0]
    im = cv2.imread(R + "icoane/" + nr + ".png", cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 3: im = cv2.cvtColor(im, cv2.COLOR_BGR2BGRA)
    px = random.choice([20, 26, 32, 40, 56, 80, 110])
    k = px / max(im.shape[:2]); im = cv2.resize(im, (max(4, int(im.shape[1] * k)), max(4, int(im.shape[0] * k))), interpolation=cv2.INTER_AREA)
    h, w = im.shape[:2]; d = 0.15 * random.random()
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    if random.random() < 0.5:                                   # privit din lateral (îngustat orizontal)
        sx = random.uniform(0.6, 1.0); dst = src.copy(); dst[:, 0] *= sx
        dst[1:3, 1] += np.float32([-1, 1]) * random.uniform(0, 0.08) * h * random.choice([-1, 1])
    else: dst = src.copy()
    dst += np.float32([[random.uniform(-d, d) * w, random.uniform(-d, d) * h] for _ in range(4)])
    pad = int(0.15 * max(w, h)) + 2; dst += pad
    M = cv2.getPerspectiveTransform(src, dst); W, H = w + 2 * pad, h + 2 * pad
    warped = cv2.warpPerspective(im, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    y = random.randint(0, bg.shape[0] - H); x = random.randint(0, bg.shape[1] - W)
    patch = bg[y:y + H, x:x + W].astype(np.float32)
    a = warped[..., 3:] / 255.0
    sign = warped[..., :3].astype(np.float32)
    sign = sign * random.uniform(0.45, 1.2) + random.uniform(-25, 25)
    sign *= np.float32([random.uniform(0.8, 1.15), random.uniform(0.9, 1.05), random.uniform(0.8, 1.1)])
    if random.random() < 0.3:                                    # decolorat de soare / murdar
        g = sign.mean(2, keepdims=True); f = random.uniform(0.2, 0.6); sign = sign * (1 - f) + g * f + random.uniform(0, 30)
    out = np.clip(sign * a + patch * (1 - a), 0, 255).astype(np.uint8)
    if random.random() < 0.7: out = cv2.GaussianBlur(out, (0, 0), random.uniform(0.3, 1.3))
    ok, b = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, random.randint(35, 85)]); out = cv2.imdecode(b, 1)
    ys, xs = np.nonzero(warped[..., 3] > 100)
    j = lambda v: int(v + random.uniform(-0.1, 0.1) * max(w, h))
    x0, y0, x1, y1 = max(0, j(xs.min())), max(0, j(ys.min())), min(W, j(xs.max())), min(H, j(ys.max()))
    if x1 - x0 < 6 or y1 - y0 < 6: x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    return indicatoare.trasaturi(out[y0:y1, x0:x1]), ci
def set_(n, s0):
    with Pool(4) as p:
        r = p.map(sint, [(ci, s0 + ci * 1000 + i) for ci in range(len(clase)) for i in range(n)], chunksize=64)
    return np.stack([a for a, _ in r]), np.array([b for _, b in r])
if __name__ == "__main__":
    t0 = time.time()
    Xtr, ytr = set_(int(sys.argv[1]) if len(sys.argv) > 1 else 60, 1); Xva, yva = set_(10, 10_000_000)
    print("date", Xtr.shape, round(time.time() - t0), "s")
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-3
    Xtr = (Xtr - mu) / sd; Xva = (Xva - mu) / sd
    D, C = Xtr.shape[1], len(clase)
    # MLP cu un strat ascuns (ReLU), Adam
    rng = np.random.default_rng(0); Hh = 384
    P = dict(W1=rng.normal(0, np.sqrt(2 / D), (D, Hh)).astype(np.float32), b1=np.zeros(Hh, np.float32),
             W2=rng.normal(0, np.sqrt(1 / Hh), (Hh, C)).astype(np.float32), b2=np.zeros(C, np.float32))
    m = {k: np.zeros_like(v) for k, v in P.items()}; v_ = {k: np.zeros_like(v) for k, v in P.items()}
    lr, wd, bs, t = 1e-3, 1e-4, 256, 0
    def fwd(X):
        h = np.maximum(0, X @ P["W1"] + P["b1"]); return h, h @ P["W2"] + P["b2"]
    for ep in range(int(sys.argv[2]) if len(sys.argv) > 2 else 25):
        idx = rng.permutation(len(Xtr))
        for i in range(0, len(idx), bs):
            b = idx[i:i + bs]; X = Xtr[b]; y = ytr[b]
            X = X + rng.normal(0, 0.1, X.shape).astype(np.float32)
            drop = (rng.random((len(b), Hh)) > 0.3) / 0.7
            h, z = fwd(X); h = h * drop; z = h @ P["W2"] + P["b2"]
            z -= z.max(1, keepdims=True); p = np.exp(z); p /= p.sum(1, keepdims=True)
            g = p; g[np.arange(len(b)), y] -= 1; g /= len(b)
            G = dict(W2=h.T @ g, b2=g.sum(0)); gh = (g @ P["W2"].T) * (h > 0) * drop
            G["W1"] = X.T @ gh; G["b1"] = gh.sum(0)
            t += 1
            for k in P:
                gk = G[k] + (wd * P[k] if k[0] == "W" else 0)
                m[k] = 0.9 * m[k] + 0.1 * gk; v_[k] = 0.999 * v_[k] + 0.001 * gk * gk
                P[k] -= lr * (m[k] / (1 - 0.9 ** t)) / (np.sqrt(v_[k] / (1 - 0.999 ** t)) + 1e-8)
        if ep in (15, 22): lr *= 0.3
        _, z = fwd(Xva); top = np.argsort(-z, 1)[:, :3]
        print(f"ep {ep}: val top1 {(top[:, 0] == yva).mean():.1%} top3 {(top == yva[:, None]).any(1).mean():.1%}  {round(time.time() - t0)} s", flush=True)
    np.savez_compressed(R + "model_indicatoare.npz", mu=mu.astype(np.float32), sd=sd.astype(np.float32),
                        **{k: v.astype(np.float16) for k, v in P.items()}, clase=np.array(["|".join(c) for c in clase]))
    print("salvat")
