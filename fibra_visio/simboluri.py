"""Simbolurile învățate de la utilizator: selectezi pe schemă un manșon / ODF / clădire, „Învață ca simbol”,
iar asistentul îl desenează apoi exact așa (copie), cu numele nou. Se țin într-un fișier local (fără internet)."""
import copy, json, os
import xml.etree.ElementTree as ET
from vsdx_doc import V, NS, text_forma
from desen import _cell, _text

ET.register_namespace("", NS)


def fisier():
    d = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "FibraVisio"); os.makedirs(d, exist_ok=True)
    return os.path.join(d, "simboluri.json")


def incarca():
    try:
        with open(fisier(), encoding="utf-8") as f: return json.load(f)
    except Exception: return {}


def invata(doc, forme, tip, nume_simbol):
    """salvează formele selectate (XML + cutia comună) ca simbol de tipul dat"""
    bs = [f.cutie() for f in forme]
    x0, y0, x1, y1 = min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs)
    shapes = []
    for f in forme:
        mn = doc.nume_master(f.el.get("Master")) if f.el.get("Master") is not None else ""
        shapes.append({"xml": ET.tostring(f.el, encoding="unicode"), "master": mn})
    # eticheta = textul cel mai lung care nu e doar numere (ex. „M1 CLO-0001”)
    texte = [(len(f.text_tot()), i) for i, f in enumerate(forme) if f.text_tot() and not f.text_tot().replace("\n", "").strip().isdigit()]
    lib = incarca()
    lib.setdefault(tip, [])
    lib[tip] = [s for s in lib[tip] if s["nume"] != nume_simbol] + [{
        "nume": nume_simbol, "cx": (x0 + x1) / 2, "cy": (y0 + y1) / 2, "w": x1 - x0, "h": y1 - y0, "shapes": shapes,
        "eticheta": max(texte)[1] if texte else None}]
    with open(fisier(), "w", encoding="utf-8") as f: json.dump(lib, f, ensure_ascii=False)
    return x1 - x0, y1 - y0


def simbol(tip):
    lib = incarca()
    return lib[tip][-1] if lib.get(tip) else None


def deseneaza(S, sim, cx, cy, nume):
    """pune copia simbolului cu centrul în (cx, cy) și numele nou pe etichetă"""
    doc = S.doc; sh = S.p.shapes_el(); nid = S.p.id_nou(); dx, dy = cx - sim["cx"], cy - sim["cy"]
    mastere = {}
    doc.master_forma("0")
    for mid, (m, _) in (doc._masters or {}).items(): mastere[(m.get("NameU") or "")] = mid
    for i, s in enumerate(sim["shapes"]):
        el = ET.fromstring(s["xml"])
        for e in el.iter(V + "Shape"):
            e.set("ID", str(nid)); nid += 1
            if "UniqueID" in e.attrib: del e.attrib["UniqueID"]
        if el.get("Master") is not None:
            if s["master"] and s["master"] in mastere: el.set("Master", mastere[s["master"]])
            else: del el.attrib["Master"]
        for n, d in (("PinX", dx), ("PinY", dy), ("BeginX", dx), ("BeginY", dy), ("EndX", dx), ("EndY", dy)):
            c = el.find(V + "Cell[@N='%s']" % n)
            if c is not None:
                c.set("V", "%.10g" % (float(c.get("V") or 0) + d))
                if "F" in c.attrib and "Sheet." in c.get("F"): del c.attrib["F"]
        if i == sim.get("eticheta"):
            for e in el.iter(V + "Shape"):
                if text_forma(e): _text(e, nume); break
            else: _text(el, nume)
        sh.append(el)
    return (cx - sim["w"] / 2, cy - sim["h"] / 2, cx + sim["w"] / 2, cy + sim["h"] / 2)
