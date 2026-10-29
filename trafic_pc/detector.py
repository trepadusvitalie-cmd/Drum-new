"""Detectorul: YOLOX (Apache-2.0, setul COCO) în ONNX. Întoarce chenarele obiectelor de trafic.
Modelul rulează pe placa video (DirectML/CUDA) dacă e mai rapid decât procesorul, altfel pe procesor."""
import os, sys, time
import numpy as np
import cv2
import onnxruntime as ort

AICI = os.path.dirname(os.path.abspath(__file__))

# clasa COCO -> clasa noastră
COCO = {0: "pieton", 1: "bicicleta", 2: "masina", 3: "motocicleta", 5: "autobuz", 6: "tramvai", 7: "camion"}
CLASE = ["pieton", "bicicleta", "masina", "motocicleta", "autobuz", "tramvai", "camion", "animal"]
NUME = {"pieton": "Pieton", "bicicleta": "Bicicletă", "masina": "Mașină", "motocicleta": "Motocicletă",
        "autobuz": "Autobuz", "tramvai": "Tramvai", "camion": "Camion", "animal": "Animal"}
PRAG_CLASA = {"animal": 0.5, "tramvai": 0.4}                  # clase cu mai multe confuzii: cer mai multă siguranță
CUL = {"pieton": (60, 60, 230), "bicicleta": (200, 90, 200), "masina": (230, 160, 40), "motocicleta": (180, 60, 160),
       "autobuz": (40, 200, 240), "tramvai": (40, 140, 255), "camion": (120, 90, 60), "animal": (90, 170, 90)}


def date_dir():
    return getattr(sys, "_MEIPASS", AICI)


def log(*a):
    print(*a, flush=True)


class Detector:
    def __init__(self, model="yolox_s.onnx", prag=0.35, gpu=True):
        path = model if os.path.isabs(model) else os.path.join(date_dir(), "model", model)
        # jumătate din nuclee și fără „arena” de memorie: calculatorul rămâne utilizabil, RAM-ul nu tot crește
        so = ort.SessionOptions(); so.intra_op_num_threads = max(1, (os.cpu_count() or 4) // 2); so.inter_op_num_threads = 1
        so.enable_cpu_mem_arena = False; so.enable_mem_pattern = False
        self.sess = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"]); self.dev = "procesor"
        self.inp = self.sess.get_inputs()[0].name; self.S = self.sess.get_inputs()[0].shape[2]
        if gpu:                                                    # placa video doar dacă e mai rapidă
            av = ort.get_available_providers(); t_cpu = self._viteza(self.sess)
            for prov, nume in (("CUDAExecutionProvider", "placa video (CUDA)"), ("DmlExecutionProvider", "placa video (DirectML)")):
                if prov not in av: continue
                try:
                    s2 = ort.InferenceSession(path, so, providers=[prov, "CPUExecutionProvider"]); t = self._viteza(s2)
                    if t < 0.9 * t_cpu: self.sess, self.dev, t_cpu = s2, nume, t
                except Exception as e: log("GPU indisponibil:", e)
            log(f"Model {os.path.basename(path)} pe {self.dev}: {t_cpu * 1000:.0f} ms/cadru")
        self.prag = prag
        g, st = [], []                                             # grilele YOLOX (pași 8, 16, 32)
        for s in (8, 16, 32):
            n = self.S // s; yv, xv = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
            g.append(np.stack([xv, yv], 2).reshape(-1, 2)); st.append(np.full((n * n, 1), s))
        self.grid = np.concatenate(g).astype(np.float32); self.stride = np.concatenate(st).astype(np.float32)

    def _viteza(self, sess):
        x = np.zeros((1, 3, self.S, self.S), np.float32); sess.run(None, {self.inp: x})
        t = time.time()
        for _ in range(3): sess.run(None, {self.inp: x})
        return (time.time() - t) / 3

    def __call__(self, img):
        """-> listă de (x0, y0, x1, y1, scor, clasa)"""
        h, w = img.shape[:2]; r = min(self.S / h, self.S / w)
        pad = np.full((self.S, self.S, 3), 114, np.uint8)
        pad[:int(h * r), :int(w * r)] = cv2.resize(img, (int(w * r), int(h * r)), interpolation=cv2.INTER_LINEAR)
        x = pad.transpose(2, 0, 1)[None].astype(np.float32)
        o = self.sess.run(None, {self.inp: x})[0][0]
        xy = (o[:, :2] + self.grid) * self.stride; wh = np.exp(o[:, 2:4]) * self.stride
        sc = o[:, 4:5] * o[:, 5:]; cls = sc.argmax(1); conf = sc[np.arange(len(sc)), cls]
        keep = (conf >= self.prag) & np.isin(cls, list(COCO))
        if not keep.any(): return []
        xy, wh, conf, cls = xy[keep], wh[keep], conf[keep], cls[keep]
        b = np.c_[xy - wh / 2, xy + wh / 2] / r
        out = []
        for c in np.unique(cls):                                   # NMS pe clase
            m = cls == c; bb = b[m]; cc = conf[m]
            idx = cv2.dnn.NMSBoxes(np.c_[bb[:, :2], bb[:, 2:] - bb[:, :2]].tolist(), cc.tolist(), self.prag, 0.45)
            for i in np.array(idx).reshape(-1):
                if cc[i] < PRAG_CLASA.get(COCO[int(c)], 0): continue
                x0, y0, x1, y1 = bb[i]
                out.append((max(0.0, x0), max(0.0, y0), min(w - 1.0, x1), min(h - 1.0, y1), float(cc[i]), COCO[int(c)]))
        return out
