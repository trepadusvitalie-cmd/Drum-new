"""Antrenarea modelului pe cadrele marcate (date/imagini + date/etichete) și punerea lui în model/.

Calculatorul nu se blochează: se lasă 2 nuclee libere, memoria folosită e cel mult jumătate din cea liberă
(și cel mult 8 GB), iar procesul rulează cu prioritate scăzută. Merge pe orice calculator (4, 8, 16 GB…);
cu placă video NVIDIA e de ~10 ori mai repede.

Folosire:  python antreneaza.py [epoci]   (implicit 80)"""
import glob, os, random, shutil, sys, time

AICI = os.path.dirname(os.path.abspath(__file__))
DRUM = os.path.dirname(AICI)
IMG = os.path.join(AICI, "date", "imagini")
ETI = os.path.join(AICI, "date", "etichete")
SET = os.path.join(AICI, "date", "set")
CLASE = ["groapa", "copac", "semn"]
MAX_RAM_GB = 8.0
NUCLEE_LIBERE = 2


def resurse():
    """(nuclee de folosit, GB de memorie de folosit, placa video da/nu)"""
    n = os.cpu_count() or 4
    nuc = max(1, n - NUCLEE_LIBERE)
    try:
        import psutil
        liber = psutil.virtual_memory().available / 2 ** 30
    except ImportError:
        liber = 4.0
    ram = max(1.0, min(MAX_RAM_GB, liber * 0.5))
    import torch
    return nuc, ram, torch.cuda.is_available()


def prioritate_mica():
    try:
        import psutil
        p = psutil.Process()
        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 10)
    except Exception:
        pass


def pregateste_setul():
    """Cadrele marcate se împart: 85% învățare, 15% verificare (la întâmplare, mereu la fel)."""
    perechi = [(f, os.path.join(ETI, os.path.splitext(os.path.basename(f))[0] + ".txt"))
               for f in sorted(glob.glob(os.path.join(IMG, "*.jpg")))]
    perechi = [(f, e) for f, e in perechi if os.path.exists(e)]
    if len(perechi) < 20:
        raise SystemExit(f"Sunt doar {len(perechi)} cadre marcate. Marchează cel puțin 20 (ideal 150–300) cu MARCHEAZA.bat.")
    random.Random(7).shuffle(perechi); nv = max(3, len(perechi) * 15 // 100)
    if os.path.exists(SET): shutil.rmtree(SET)
    for parte, lista in (("val", perechi[:nv]), ("train", perechi[nv:])):
        for sub in ("images", "labels"): os.makedirs(os.path.join(SET, parte, sub))
        for f, e in lista:
            shutil.copy(f, os.path.join(SET, parte, "images")); shutil.copy(e, os.path.join(SET, parte, "labels"))
    yml = os.path.join(SET, "drum.yaml")
    with open(yml, "w", encoding="utf-8") as g:
        g.write(f"path: {SET}\ntrain: train/images\nval: val/images\nnames:\n" + "".join(f"  {i}: {c}\n" for i, c in enumerate(CLASE)))
    print(f"Cadre marcate: {len(perechi)} ({len(perechi) - nv} învățare, {nv} verificare)")
    return yml


def main():
    epoci = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    prioritate_mica()
    nuc, ram, gpu = resurse()
    import torch
    torch.set_num_threads(nuc)
    from ultralytics import YOLO
    yml = pregateste_setul()
    # pornim de la modelul nostru dacă există în .pt, altfel de la modelul mic general (se descarcă o dată, ~6 MB)
    baza = next(iter(sorted(glob.glob(os.path.join(DRUM, "model", "*.pt")))), "yolo11n.pt")
    if gpu:
        lot = 0.6                       # ultralytics alege lotul să ocupe ~60% din memoria plăcii video
    else:
        lot = int(max(2, min(16, ram / 0.5)))     # ~0.5 GB pe imagine la 640 px, pe procesor
    print(f"Antrenare pe {'placa video' if gpu else 'procesor'}: {nuc} nuclee (2 libere), memorie ≤ {ram:.1f} GB, lot {lot}, {epoci} epoci")
    print(f"Pornire de la: {os.path.basename(baza)}")
    t0 = time.time()
    m = YOLO(baza)
    m.train(data=yml, epochs=epoci, imgsz=640, batch=lot, workers=min(2, nuc), device=0 if gpu else "cpu",
            project=os.path.join(AICI, "rezultate"), name="drum_v2", exist_ok=True, patience=20,
            cache=False, plots=True, verbose=False,
            fliplr=0.5, degrees=3, scale=0.4, hsv_h=0.02, hsv_s=0.5, hsv_v=0.4)
    best = os.path.join(AICI, "rezultate", "drum_v2", "weights", "best.pt")
    print(f"Antrenare gata în {(time.time() - t0) / 60:.0f} min. Se pregătește modelul pentru program…")
    onnx = YOLO(best).export(format="onnx", imgsz=640, simplify=True)
    os.makedirs(os.path.join(DRUM, "model"), exist_ok=True)
    shutil.copy(onnx, os.path.join(DRUM, "model", "drum_v2.onnx"))
    with open(os.path.join(DRUM, "model", "labels.txt"), "w", encoding="utf-8") as f: f.write("\n".join(CLASE) + "\n")
    rez = YOLO(best).val(data=yml, imgsz=640, device=0 if gpu else "cpu", workers=min(2, nuc), verbose=False)
    print(f"\nModelul nou: model\\drum_v2.onnx (îl folosește automat ANALIZEAZA.bat și Drum_Analiza.exe)")
    print(f"Pe cadrele de verificare: precizie {rez.box.mp * 100:.0f}%, găsiți {rez.box.mr * 100:.0f}% (mAP50 {rez.box.map50 * 100:.0f}%)")
    print("Graficele și exemplele: antrenare\\rezultate\\drum_v2\\")


if __name__ == "__main__":
    main()
