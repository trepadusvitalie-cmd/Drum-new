"""Fișierele Visio vechi (.vsd): le convertește Visio-ul de pe calculator (invizibil, prin automatizare COM) în .vsdx și înapoi.
Fără Visio instalat nu se poate (formatul .vsd e binar, închis)."""
import os, shutil, tempfile


def e_deschis_in_visio(e):
    """eroarea Visio „fișierul e deschis pentru modificări în altă instanță de Visio”"""
    t = str(e).lower()
    return "another instance" in t or "open for modifications" in t or "-2032466468" in t


def _visio():
    import win32com.client                                       # pywin32 (inclus în exe)
    for prog in ("Visio.InvisibleApp", "Visio.Application"):
        try:
            app = win32com.client.Dispatch(prog)
            try: app.Visible = False
            except Exception: pass
            try: app.AlertResponse = 7                             # „Nu” la orice întrebare (fără ferestre)
            except Exception: pass
            return app
        except Exception:
            continue
    raise RuntimeError("nu găsesc Visio pe calculator")


def converteste(src, dst):
    """deschide src în Visio (ascuns, doar citire) și îl salvează ca dst; formatul după extensie (.vsd / .vsdx)"""
    app = _visio()
    try:
        doc = app.Documents.OpenEx(os.path.abspath(src), 2 + 8 + 64)  # doar citire + fără listă recentă + ascuns
        try: doc.SaveAs(os.path.abspath(dst))
        finally: doc.Close()
    finally:
        try: app.Quit()
        except Exception: pass
    return dst


def vsd_in_vsdx(path):
    """copie .vsdx într-un folder temporar. Lucrez pe o copie a fișierului, ca să meargă și când e deschis în Visio."""
    d = tempfile.mkdtemp(prefix="fibra_visio_")
    nume = os.path.splitext(os.path.basename(path))[0]
    copie = os.path.join(d, nume + "_copie.vsd")
    try: shutil.copy2(path, copie); src = copie
    except Exception: src = path                                  # nu se poate copia: încerc direct
    return converteste(src, os.path.join(d, nume + ".vsdx"))
