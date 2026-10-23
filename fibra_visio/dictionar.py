"""Dicționarul asistentului (fără internet): sinonime, numere scrise în litere, greșeli mici de tastare.
Transformă ce scrii liber într-o formă pe care asistentul o recunoaște. Numele din schemă nu le atinge."""
import difflib, re

# cuvânt (fără diacritice) -> forma canonică
SINONIME = {
    # acțiuni
    "adauga": "adauga", "adaug": "adauga", "adaugam": "adauga", "pune": "adauga", "puneti": "adauga", "punem": "adauga", "deseneaza": "adauga",
    "deseneza": "adauga", "desenez": "adauga", "fa": "adauga", "faci": "adauga", "facem": "adauga", "creeaza": "adauga", "creaza": "adauga",
    "construieste": "adauga", "insereaza": "adauga", "vreau": "adauga", "vrea": "adauga", "trebuie": "adauga", "doresc": "adauga",
    "plaseaza": "adauga", "amplaseaza": "adauga", "nou": "nou", "noua": "nou", "noi": "nou", "nuo": "nou",
    "добавь": "adauga", "нарисуй": "adauga", "поставь": "adauga", "новый": "nou", "новая": "nou", "новое": "nou",
    # obiecte
    "cladire": "cladire", "cladirea": "cladire", "cladiri": "cladire", "bloc": "cladire", "blocul": "cladire", "casa": "cladire", "casuta": "cladire",
    "imobil": "cladire", "constructie": "cladire", "hala": "cladire", "edificiu": "cladire", "здание": "cladire", "дом": "cladire",
    "manson": "manson", "mansonul": "manson", "mansoane": "manson", "mufa": "manson", "mufe": "manson", "jonctiune": "manson", "closure": "manson",
    "муфта": "manson", "муфту": "manson",
    "odf": "odf", "cutie": "odf", "cutia": "odf", "cutii": "odf", "box": "odf", "boxa": "odf", "dulap": "odf", "cabinet": "odf", "rack": "odf",
    "panou": "odf", "fdb": "odf", "fat": "odf", "кросс": "odf", "шкаф": "odf", "коробка": "odf", "бокс": "odf",
    "fibra": "fibra", "fibre": "fibra", "fir": "fibra", "fire": "fibra", "волокно": "fibra", "волокна": "fibra",
    "trage": "trage", "trag": "trage", "trageti": "trage", "trgae": "trage", "leaga": "trage", "conecteaza": "trage", "uneste": "trage",
    "cupleaza": "trage", "conectare": "trage", "legatura": "trage",
    "cablu": "cablu", "cablul": "cablu", "cabluri": "cablu", "кабель": "cablu",
    "port": "port", "portul": "port", "porturi": "porturi", "porturile": "porturi", "intrari": "porturi", "iesiri": "porturi", "порт": "port", "порты": "porturi",
    # locul
    "langa": "langa", "linga": "langa", "alaturi": "langa", "aproape": "langa", "lingă": "langa", "рядом": "langa",
    "pagina": "pagina", "foaie": "pagina", "foaia": "pagina", "lista": "lista",
    # întrebări
    "cate": "cate", "cite": "cate", "cati": "cate", "citi": "cate", "unde": "unde", "cum": "cum", "ce": "ce", "care": "care",
    "libere": "libere", "liber": "libere", "goale": "libere", "neocupate": "libere", "ocupate": "ocupate", "folosite": "ocupate",
}
GENERICE = set(SINONIME)
INVATATE = {}          # cuvinte învățate din discuții (memorie.py le pune aici)
NUMERE = {"unu": 1, "una": 1, "un": 1, "o": 1, "doi": 2, "doua": 2, "trei": 3, "patru": 4, "cinci": 5, "sase": 6, "sapte": 7, "opt": 8,
          "zece": 10, "unsprezece": 11, "doisprezece": 12, "douasprezece": 12, "saisprezece": 16, "douazeci": 20, "treizeci": 30,
          "patruzeci": 40, "один": 1, "два": 2, "три": 3, "четыре": 4, "восемь": 8, "двенадцать": 12, "двадцать": 20}


def fd(s):
    for a, b in zip("ăâîșşțţĂÂÎȘŞȚŢ", "aaisstt" + "AAISSTT"): s = s.replace(a, b)
    return s.lower()


def numere(t):
    """„douazeci si patru” -> 24, „doua” -> 2 (doar cuvintele-număr, restul rămâne)"""
    t = re.sub(r"\bdouazeci\s+si\s+patru\b", "24", t); t = re.sub(r"\bpatruzeci\s+si\s+opt\b", "48", t)
    t = re.sub(r"\bdouazeci\s+si\s+(\w+)\b", lambda m: str(20 + NUMERE.get(m.group(1), 0)) if m.group(1) in NUMERE else m.group(0), t)
    def rep(m):
        w = m.group(0)
        if w in ("o", "un", "una"): return w                     # „o cutie”, „un manson” – articol, nu număr
        return str(NUMERE[w]) if w in NUMERE else w
    return re.sub(r"\b\w+\b", rep, t)


def normalizeaza(t, nume_schema=()):
    """textul liber -> cuvinte canonice (pentru a recunoaște ce vrei); numele din schemă rămân neatinse"""
    t = numere(fd(t))
    protejat = {fd(w) for n in nume_schema for w in re.split(r"[\s_\-./]+", n) if w}
    out = []
    for w in re.findall(r"[\w\-./]+|[^\w\s]", t):
        if w in protejat or not re.search(r"[a-zа-я]", w): out.append(w); continue
        if w in SINONIME: out.append(SINONIME[w]); continue
        if w in INVATATE: out.append(INVATATE[w]); continue
        g = difflib.get_close_matches(w, list(SINONIME), n=1, cutoff=0.82) if len(w) >= 4 else []
        out.append(SINONIME[g[0]] if g else (radacina(w) if len(w) >= 4 and radacina(w) else w))
    return " ".join(out)


# rădăcini: prinde și formele pe care nu le-am scris în listă (blocurile, mansoanelor, cutiuta…)
RADACINI = [("cladire", ("clad", "bloc", "cas", "imob", "constr", "hal", "edif")), ("manson", ("mans", "muf", "jonct")),
            ("odf", ("odf", "cut", "dulap", "cabin", "rack", "box", "pano", "fdb")), ("adauga", ("adaug", "desen", "pun", "crea", "cree", "constru", "inser", "plas", "ampl", "vre")),
            ("nou", ("nou",)), ("fibra", ("fibr", "fir")), ("langa", ("lang", "ling", "alatur", "aproap"))]


def radacina(w):
    for canon, rs in RADACINI:
        if any(w.startswith(r) for r in rs) and len(w) >= 3: return canon
    return None


def intentie(t):
    """ce vrea să deseneze, din orice formulare: 'cladire' / 'manson' / 'odf' / None. Ordinea cuvintelor nu contează."""
    cuv = normalizeaza(t).split()
    can = set(cuv) | {radacina(w) for w in cuv}
    vrea = bool(can & {"adauga", "nou"})
    for i in ("cladire", "manson", "odf"):
        if i in can and vrea: return i
    if ("trage" in can or "fibra" in can) and not re.search(r"\d", t) and len(cuv) <= 6: return "fibra"   # „trage o fibră” fără detalii: te ghidez
    return None


def scor_intentii(t):
    """când nu e sigur: ce obiecte apar în text (pentru a propune variante)"""
    cuv = normalizeaza(t).split(); can = set(cuv) | {radacina(w) for w in cuv}
    return [i for i in ("cladire", "odf", "manson") if i in can]


# ---------------------------------------------------------------- întrebări despre program (răspunsuri fixe)
CUM = [
    (r"tabel", "Tabel: fila Inserare → ▦ Tabel → alegi pe grilă rânduri × coloane (sau „Altă mărime…”). Dublu-clic pe o celulă = scrii în ea."),
    (r"salv|vsd", "Salvare: 💾 Salvează (același format în care ai deschis: .vsdx sau .vsd). „Salvează ca…” – alegi .vsdx sau .vsd (.vsd cere Visio pe calculator)."),
    (r"text|scri|litere|font|marime", "Text: dublu-clic (sau F2) pe text → scrii pe loc (Enter = rând nou, Ctrl+Enter = gata). Mărimea, fontul, B/I/U, culoarea: fila Acasă."),
    (r"mut|muta", "Mutare: clic pe formă și tragi; săgețile = 1 mm (Shift = 1 cm). Mai multe forme: trage un dreptunghi pe gol sau Shift+clic."),
    (r"sterg|sterge", "Ștergere: selectezi și apeși Delete (sau clic dreapta → Șterge). Greșeală? săgeata ← (Ctrl+Z)."),
    (r"copi|lipe", "Copiere: selectezi → Ctrl+C → duci mausul unde vrei → Ctrl+V."),
    (r"fibr|port|leg", "Fibră: scrie „<nod> port 5 la <nod> port 3” (ex. „nord p5 la sud p6”); prin manșon: adaugă „prin M1”."),
    (r"cladir|bloc|casa", "Clădire nouă: scrie „adauga cladire noua” – te întreb pas cu pas (nume, câte ODF, porturi, unde, de la ce nod vin fibrele)."),
    (r"mans|mufa", "Manșon nou: scrie „adauga manson nou” – te întreb numele și unde îl pun."),
    (r"odf|cutie|cabinet", "ODF / cutie: scrie „adauga odf nou” – te întreb numele, porturile, cum stă banda și unde îl pun."),
    (r"simbol|invat", "Simbolurile tale: selectezi pe schemă manșonul / ODF-ul / clădirea → clic dreapta → „Învață ca simbol…”. De atunci le desenez așa."),
    (r"anul|inapoi|greseal", "Înapoi: săgeata ← sus (Ctrl+Z); Înainte: săgeata → (Ctrl+Y)."),
    (r"mari|redim|lat", "Mărimea unei forme: o selectezi și tragi de pătrățelele albe de pe margini."),
]


def cum_fac(t):
    """întrebări „cum fac / cum pot / unde e …” -> explicația, fără să schimbe ceva"""
    t = fd(t)
    if not re.search(r"\b(cum|unde|ce trebuie|cum pot|cum fac|cum se|nu stiu sa|explica)\b", t): return None
    for rx, r in CUM:
        if re.search(rx, t): return r
    return None
