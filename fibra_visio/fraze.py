"""Felul în care vorbește utilizatorul (adunat din discuțiile de lucru): fraza lui -> comanda pe care programul o știe.
Merge și cu greșeli de scriere: se caută fraza cea mai apropiată. Fără internet."""
import difflib, re

FRAZE = {
    # urmărirea fibrei și desenul traseului
    "arata portul odf 2 cum ajunge la client": "arata pentru port 2",
    "arata portul odf 2 cum ajunje la client": "arata pentru port 2",
    "odf central arata schema la port 21": "arata pentru port 21",
    "arata pentru port 21": "arata pentru port 21",
    "unde ajunge portul 5": "arata pentru port 5",
    "cum merge fibra de la portul 3": "arata pentru port 3",
    "urmareste fibra de la odf port 7": "arata pentru port 7",
    "genereaza o pagina nou cu schema asta": "deseneaza-l pe pagina noua",
    "genereaza o pagina noua cu schema asta": "deseneaza-l pe pagina noua",
    "deseneaza intr-o pagina noua schema de la odf pina la client": "deseneaza-l pe pagina noua",
    "sa mi deseneze intro pagina noua schema de la odf pina la client": "deseneaza-l pe pagina noua",
    "fa schema pe alta pagina": "deseneaza-l pe pagina noua",
    # porturi
    "selecteaza pe schema porturile libere": "selecteaza porturile libere",
    "selecteaza pe schmea porturile librere": "selecteaza porturile libere",
    "arata porturile libere": "selecteaza porturile libere",
    "unde sunt porturi libere": "selecteaza porturile libere",
    "cate porturi libere sunt": "porturi libere",
    "porturi goale": "porturi libere",
    # verificarea schemei
    "vezi neclaritatile si selecteaza pe schema": "vezi neclaritatile",
    "vezi neclaritatile": "vezi neclaritatile",
    "verifica schema": "vezi neclaritatile",
    "ce e gresit pe schema": "vezi neclaritatile",
    "gaseste greselile": "vezi neclaritatile",
    "cum se poate de imbunatatit schema": "cum se poate imbunatati schema",
    "cum spoate de imbunatatit schema": "cum se poate imbunatati schema",
    "ce sfaturi ai pentru schema": "cum se poate imbunatati schema",
    "analizeaza schema": "analizeaza schema",
    "ce potis spune": "analizeaza schema",
    "ce poti spune despre schema": "analizeaza schema",
    # suduri
    "gaseste sudurile si selecteaza si coloreaza cu galben": "gaseste sudurile si coloreaza cu galben",
    "colorezaza sudura cu galben": "gaseste sudurile si coloreaza cu galben",
    "coloreaza sudurile galben": "gaseste sudurile si coloreaza cu galben",
    "arata sudurile": "gaseste sudurile",
    "cate suduri sunt": "cate suduri sunt",
    # selecție, culori, grosime
    "obiectul selectat fa rosu": "fa rosu",
    "obiectul slectata fa rosu": "fa rosu",
    "selctat coloarea in verde": "fa verde",
    "fa ma gros": "fa mai gros",
    "obiectul selectat fa mai gros": "fa mai gros",
    "inca mai gros": "fa mai gros",
    "fa subtire": "fa subtire",
    "fa intrerupt": "fa intrerupt",
    "selecteaza fibrele noi": "selecteaza fibrele noi",
    "selecteaza fibrele rosii": "selecteaza fibrele rosii",
    "selecteaza fibrele albastre": "selecteaza fibrele albastre",
    "selecteaza tot": "selecteaza tot",
    # etichete
    "pune nr 5": "pune nr 5",
    "adauga eticheta portului": "eticheta portului",
    "pune numarul portului": "eticheta portului",
    # desen nou cu asistentul
    "adauga cladire noua": "adauga cladire noua",
    "deseneaza o cladire noua cu odf": "adauga cladire noua",
    "deseneaza singur cutii cabinete": "adauga odf nou",
    "adauga mason": "adauga manson nou",
    "adauga mufa": "adauga manson nou",
    "trage o fibra": "trage o fibra",
    "indic sudarea": "trage o fibra",
    "adauga sudare": "trage o fibra",
    "ghideaza ma": "ghideaza-ma",
    # tipar, foaie
    "tipareste": "tipareste",
    "da la print": "tipareste",
    "format a3": "format A3",
    "pune pe a4": "format A4",
    # discuție
    "ce ai invatat": "ce ai invatat",
    "analizeaza discutia precedenta": "analizeaza discutia precedenta",
}


def _cheie(t):
    t = t.lower()
    for a, b in zip("ăâîșşțţ", "aaisstt"): t = t.replace(a, b)
    return " ".join(re.sub(r"[^\w\s/-]", " ", t).split())


_CHEI = {_cheie(k): v for k, v in FRAZE.items()}


def traduce(t):
    """fraza utilizatorului -> comanda cunoscută (sau None). Cifrele din frază (porturi, numere) se păstrează."""
    k = _cheie(t)
    if k in _CHEI: return _cu_cifre(k, _CHEI[k], k)
    g = difflib.get_close_matches(k, list(_CHEI), n=1, cutoff=0.78)
    return _cu_cifre(k, _CHEI[g[0]], g[0]) if g else None


def _cu_cifre(scris, comanda, model):
    """„arata portul odf 7 …” potrivit pe modelul cu 2: păstrez numărul scris de utilizator"""
    nr_s, nr_m = re.findall(r"\d+", scris), re.findall(r"\d+", model)
    if nr_s and nr_m and nr_s != nr_m:
        for a, b in zip(nr_m, nr_s): comanda = re.sub(r"\b%s\b" % a, b, comanda, count=1)
    return comanda
