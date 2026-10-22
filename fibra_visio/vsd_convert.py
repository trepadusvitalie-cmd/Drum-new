"""Fișierele Visio vechi (.vsd): le convertește Visio-ul de pe calculator (invizibil, prin automatizare COM) în .vsdx și înapoi.
Fără Visio instalat nu se poate (formatul .vsd e binar, închis)."""
import os, tempfile


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
    """copie .vsdx într-un folder temporar"""
    d = tempfile.mkdtemp(prefix="fibra_visio_")
    return converteste(path, os.path.join(d, os.path.splitext(os.path.basename(path))[0] + ".vsdx"))
