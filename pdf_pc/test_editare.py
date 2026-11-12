"""Test: editarea textului existent dintr-un PDF (rulează la construire, cu PyMuPDF-ul din exe)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdf_nucleu import fitz, rand_la, inlocuieste_rand

d = fitz.open(); p = d.new_page()
p.insert_text((72, 100), "Pret total: 100 lei", fontsize=14, color=(0, 0, 1))
p.insert_text((72, 130), "Randul de dedesubt ramane", fontsize=12)
p.draw_rect(fitz.Rect(60, 80, 400, 140), color=(1, 0, 0))
for rot in (0, 90):
    p.set_rotation(rot)
    if rot == 0:
        x, y = 100, 96
    else:
        q = fitz.Point(100, 96) * p.rotation_matrix; x, y = q.x, q.y
    info = rand_la(p, x, y)
    assert info and info["text"].startswith("Pret total"), info
    nou = "Pret total: 250 lei" if rot == 0 else "Pret total: 300 lei"
    inlocuieste_rand(p, info, nou)
    import re
    t = re.sub(r"[^\w:]+", " ", p.get_text())               # spațiile din fontul Arial pot ieși la citire ca alt caracter
    assert re.sub(r"[^\w:]+", " ", nou) in t, t
    assert "100 lei" not in t and "Randul de dedesubt ramane" in t, t
    assert any(dr["rect"] for dr in p.get_drawings()), "desenul a dispărut"
    print("rotatie", rot, "ok:", nou)
print("OK")
