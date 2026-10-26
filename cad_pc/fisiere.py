"""Deschiderea și salvarea desenelor.
DXF: direct (ezdxf).  DWG: se transformă prin ODA File Converter (gratuit) dacă e instalat, altfel prin AutoCAD-ul de pe calculator.
Fișierul original nu se atinge la deschidere (se lucrează pe o copie temporară, deci merge și dacă e deschis în AutoCAD)."""
import glob, json, os, shutil, subprocess, sys, tempfile, time
import ezdxf
from ezdxf import recover

TMP = os.path.join(tempfile.gettempdir(), "CAD_PC"); os.makedirs(TMP, exist_ok=True)
CFG = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "CAD_PC"); os.makedirs(CFG, exist_ok=True)
VERSIUNI = {"AutoCAD 2018": ("R2018", "ACAD2018", 64, 65), "AutoCAD 2013": ("R2013", "ACAD2013", 60, 61),
            "AutoCAD 2010": ("R2010", "ACAD2010", 48, 49), "AutoCAD 2007": ("R2007", "ACAD2007", 36, 37), "AutoCAD 2004": ("R2004", "ACAD2004", 24, 25)}


class EroareFisier(Exception): pass


# ---------------------------------------------------------------- convertoare
def oda_exe():
    """ODA File Converter, dacă e instalat"""
    for baza in (os.environ.get("ProgramFiles", r"C:\Program Files"), os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")):
        g = sorted(glob.glob(os.path.join(baza, "ODA", "ODAFileConverter*", "ODAFileConverter.exe")))
        if g: return g[-1]
    return shutil.which("ODAFileConverter")


def autocad():
    """AutoCAD-ul de pe calculator, prin COM (pornește ascuns dacă nu e deschis)"""
    try:
        import win32com.client
    except ImportError:
        return None
    try:
        return win32com.client.GetActiveObject("AutoCAD.Application")
    except Exception:
        try:
            a = win32com.client.Dispatch("AutoCAD.Application"); return a
        except Exception:
            return None


def ce_convertor():
    if oda_exe(): return "ODA File Converter"
    if sys.platform == "win32":
        try:
            import winreg; winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "AutoCAD.Application"); return "AutoCAD"
        except Exception: pass
    return None


def _oda(src, dst_dir, fmt, ver):
    """fmt: DWG/DXF; ver: ACAD2018…"""
    d_in = tempfile.mkdtemp(dir=TMP); shutil.copy2(src, d_in)
    os.makedirs(dst_dir, exist_ok=True)
    si = None
    if sys.platform == "win32":
        si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run([oda_exe(), d_in, dst_dir, ver, fmt, "0", "1", "*.*"], check=False, startupinfo=si, timeout=600)
    shutil.rmtree(d_in, ignore_errors=True)


def _acad(src, dst, tip):
    a = autocad()
    if a is None: raise EroareFisier("AutoCAD nu răspunde.")
    copie = os.path.join(tempfile.mkdtemp(dir=TMP), os.path.basename(src)); shutil.copy2(src, copie)
    doc = a.Documents.Open(copie, False)
    try:
        if os.path.exists(dst): os.remove(dst)
        doc.SaveAs(dst, tip)
    finally:
        try: doc.Close(False)
        except Exception: pass


def dwg_in_dxf(dwg):
    out_dir = tempfile.mkdtemp(dir=TMP); dxf = os.path.join(out_dir, os.path.splitext(os.path.basename(dwg))[0] + ".dxf")
    if oda_exe():
        _oda(dwg, out_dir, "DXF", "ACAD2018")
    elif ce_convertor() == "AutoCAD":
        _acad(dwg, dxf, 65)
    else:
        raise EroareFisier("Pentru DWG e nevoie de ODA File Converter (gratuit, opendesign.com) sau de AutoCAD instalat.\n"
                           "Poți deschide direct fișierele DXF.")
    if not os.path.exists(dxf): raise EroareFisier("Transformarea DWG → DXF a eșuat.")
    return dxf


def dxf_in_dwg(dxf, dwg, versiune="AutoCAD 2018"):
    rel, oda_v, ac_dwg, _ = VERSIUNI[versiune]
    if oda_exe():
        out_dir = tempfile.mkdtemp(dir=TMP); _oda(dxf, out_dir, "DWG", oda_v)
        rez = os.path.join(out_dir, os.path.splitext(os.path.basename(dxf))[0] + ".dwg")
        if not os.path.exists(rez): raise EroareFisier("Transformarea DXF → DWG a eșuat.")
        shutil.move(rez, dwg)
    elif ce_convertor() == "AutoCAD":
        _acad(dxf, dwg, ac_dwg)
    else:
        raise EroareFisier("Pentru salvarea în DWG e nevoie de ODA File Converter (gratuit) sau de AutoCAD instalat.\nSalvează ca DXF.")


# ---------------------------------------------------------------- deschide / salvează
def deschide(cale):
    ext = os.path.splitext(cale)[1].lower()
    if ext == ".dwg": sursa = dwg_in_dxf(cale)
    elif ext == ".dxf": sursa = cale
    else: raise EroareFisier("Se deschid fișiere DWG și DXF.")
    try:
        doc = ezdxf.readfile(sursa)
    except Exception:
        doc, aud = recover.readfile(sursa)
    adauga_recent(cale)
    return doc


def salveaza(doc, cale, versiune="AutoCAD 2018"):
    ext = os.path.splitext(cale)[1].lower()
    if os.path.exists(cale):                             # copie de siguranță, ca AutoCAD (.bak)
        try: shutil.copy2(cale, os.path.splitext(cale)[0] + ".bak")
        except Exception: pass
    if ext == ".dxf":
        doc.saveas(cale)
    else:
        tmp = os.path.join(tempfile.mkdtemp(dir=TMP), os.path.splitext(os.path.basename(cale))[0] + ".dxf")
        doc.saveas(tmp); dxf_in_dwg(tmp, cale, versiune)
    adauga_recent(cale)


def nou():
    doc = ezdxf.new("R2018", setup=True); doc.header["$INSUNITS"] = 6
    return doc


# ---------------------------------------------------------------- documente recente
def recente():
    try: return [p for p in json.load(open(os.path.join(CFG, "recente.json"), encoding="utf-8")) if os.path.exists(p)]
    except Exception: return []


def adauga_recent(p):
    r = [x for x in recente() if os.path.normcase(x) != os.path.normcase(p)]
    r.insert(0, p)
    try: json.dump(r[:20], open(os.path.join(CFG, "recente.json"), "w", encoding="utf-8"), ensure_ascii=False)
    except Exception: pass
