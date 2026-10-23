"""Cereri libere despre grupuri de obiecte de pe schemă: CE (sudurile, fibrele roșii, textele, manșoanele, M2, selecția…)
și CE FAC cu ele (selectez, arăt, număr, șterg, mut, colorez…). Ordinea cuvintelor și diacriticele nu contează."""
import re

ACT = [  # (acțiune, regex) – prima care se potrivește
    ("deselect", r"\b(deselect\w*|anuleaza selectia|scoate selectia|nimic selectat|fara selectie)\b"),
    ("numara", r"\b(cat[ei]|cit[ei]|numar[aă]\w*|numara|cate sunt|cati sunt|ce numar)\b"),
    ("sterge", r"\b(sterg\w*|elimin\w*|scoat\w*|inlatur\w*|rade|rad|anihil\w*)\b"),
    ("muta", r"\b(mut\w*|misc\w*|deplas\w*|impinge\w*)\b"),
    ("arata", r"\b(arat\w*|zoom\w*|apropie\w*|mergi la|du-ma|du ma|unde (e|este|sunt|se afla)|gas\w*|caut\w*|vezi|focus\w*)\b"),
    ("selecteaza", r"\b(select\w*|alege\w*|ia|marc\w*|evident\w*|bifea\w*)\b"),
]
CUV_STIL = r"\b(rosu|rosie|rosii|verde|verzi|albastr\w*|negru|neagra|negre|galben\w*|portocali\w*|mov|violet|gri|alb|alba|albe|maro|roz|" \
           r"intrerupt\w*|punctat\w*|continu\w*|gros\w*|ingroas\w*|subtir\w*|bold|colo\w*|vopse\w*|umple|fundal)\b"


def fd(s):
    for a, b in zip("ăâîșşțţĂÂÎȘŞȚŢ", "aaisstt" + "AAISSTT"): s = s.replace(a, b)
    return s.lower()


def actiune(cm):
    for a, rx in ACT:
        if re.search(rx, cm): return a
    return None


def tinta(app, cm):
    """-> (forme, descriere) sau (None, None) dacă textul nu numește un grup"""
    p = app.doc.pagini[app.chat.ip]; forme = list(p.forme())
    if re.search(r"\b(asta|acesta|aceasta|astea|acestea|selectat\w*|selectia|el|ea|ele|ei|-l|-o|-le)\b", cm) and app.selectie:
        return list(app.selectie), "obiecte selectate"
    if re.search(r"\b(sud(ur|ar|at|ez|eaz)\w*|imbin\w*|jonctiun\w*|splice\w*|punct\w* de sud\w*|punctele|punctul)\b", cm):
        pct = [f for f in forme if app.e_punct(f)]
        if pct: return pct, "puncte de sudură"
        # schema fără puncte: sudurile sunt notate cu etichete „M2=F”, „G=H” (cablul din stânga sudat cu cel din dreapta)
        et = [f for f in forme if re.fullmatch(r"[A-Za-z0-9/-]{1,8}\s*=\s*[A-Za-z0-9/-]{1,8}", (f.text_tot() or "").strip())]
        return et, "locuri de sudură (etichete „X=Y”)"
    if re.search(r"\b(fibr\w*|lini\w*|cabl\w*|fir\w*)\b", cm):
        cul = None
        for k in sorted(app.CULORI, key=len, reverse=True):
            if re.search(r"\b" + k + r"\b", cm) and not re.search(r"\b(fa|in|cu|la|pe)\s+" + k + r"\b", cm): cul = app.CULORI[k].upper(); break
        noi = bool(re.search(r"\bno(i|ua|ul)\b", cm)); intr = bool(re.search(r"\bintrerupt", cm) and not re.search(r"\b(fa|in)\s+intrerupt", cm))
        exist = bool(re.search(r"\bexist\w*|\bvechi\b", cm))
        def ok(f):
            if not f.e1d: return False
            lc = (app.culoare_forma(f) or "#000000").upper(); lp = f.cell("LinePattern", "1") or "1"
            if noi and not (lc == "#FF0000" or lp not in ("0", "1")): return False
            if exist and (lc == "#FF0000" or lp not in ("0", "1")): return False
            if intr and lp in ("0", "1"): return False
            return cul is None or lc == cul
        d = "linii" + (" noi" if noi else "") + (" existente" if exist else "") + (" întrerupte" if intr else "")
        return [f for f in forme if ok(f)], d
    if re.search(r"\b(text\w*|etichet\w*|scris\w*|inscript\w*|numer\w*)\b", cm) and not re.search(r"\bmai (mare|mic)", cm):
        return [f for f in forme if f.text and not f.e1d], "texte"
    if re.search(r"\b(manson\w*|muf\w*)\b", cm):
        import porturi
        S = app.chat.schema; out = []
        for m in porturi.mansoane(S):
            g = S.gaseste(m)
            if g is not None: out.append(g)
        return out, "manșoane"
    if re.search(r"\b(benz\w*|nod(uri|urile)?|odf\w*|cta\w*|bts\w*)\b", cm) and not _nume(app, cm):
        import porturi
        return [nd.banda for nd in porturi.noduri(app.chat.schema)], "benzi de porturi"
    if re.search(r"\b(tot|toate|totul|toata schema|intreaga schema)\b", cm) and not re.search(r"\b(fibr|lini|sud|text)", cm):
        return forme, "obiecte"
    n = _nume(app, cm)
    if n: return n
    return None, None


def _nume(app, cm):
    """un nume din schemă (M2, CTA Nord…) -> forma lui"""
    import porturi
    S = app.chat.schema
    try:
        for a, b, nume, nd in porturi.mentiuni(S, cm):
            if nd is not None:
                b0 = nd.banda; et = getattr(nd, "eticheta", None)
                return [x for x in (b0, et) if x is not None], nume
    except Exception: pass
    try:                                                              # manșoane și alte chenare cu nume (ex. „M1 CLO-0001”)
        nume = sorted(set(porturi.mansoane(S)) | {x for x, _ in porturi._candidati(S)}, key=len, reverse=True)
        c = re.sub(r"[\s_\-]+", "", cm)
        for nm in nume:
            k = re.sub(r"[\s_\-]+", "", fd(nm))
            prim = fd(nm).split()[0] if nm.split() else ""
            if (len(k) >= 2 and k in c) or (len(prim) >= 3 and re.search(r"\b" + re.escape(prim) + r"\b", cm)):
                g = S.gaseste(nm); out = [g] if g is not None else []
                try:                                                  # chenarul manșonului (nu doar eticheta lui)
                    b = porturi.cutie_nod(S, nm)
                    for f in S.p.forme():
                        if f.e1d or f is g: continue
                        try: fb = f.cutie()
                        except Exception: continue
                        if all(abs(fb[i] - b[i]) < 0.05 for i in range(4)): out.insert(0, f); break
                except Exception: pass
                if out: return out, nm
    except Exception: pass
    return None


def deplasare(cm):
    """„la dreapta cu 2 cm”, „sus 5 mm” -> (dx, dy) în inch"""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(cm|mm|m)?\b", cm)
    v = float(m.group(1).replace(",", ".")) if m else 1.0; u = (m.group(2) if m else None) or "cm"
    d = v / 2.54 if u == "cm" else v / 25.4 if u == "mm" else v / 2.54
    if re.search(r"\bstang", cm): return -d, 0
    if re.search(r"\bdreapt", cm): return d, 0
    if re.search(r"\bsus|deasupra", cm): return 0, d
    if re.search(r"\bjos|dedesubt", cm): return 0, -d
    return None


def interpreteaza(app, cm, orig=""):
    """cererea liberă -> mesaj, sau None dacă nu e despre grupuri de obiecte"""
    r = program(app, cm)                                              # tabel, copiere, pagini, zoom, salvare, stilul cablului nou, ce poți cere
    if r: return r
    r = verifica(app, cm)                                             # porturi libere pe schemă, neclarități, îmbunătățiri
    if r: return r
    import traseu
    r = traseu.cerere(app, cm)                                        # „arată portul ODF 2 cum ajunge la client” (+ desen pe pagină nouă)
    if r: return r
    if re.search(r"\bport\w*\b.*\bla\b|\bp\d+\b", cm): return None                  # comandă de fibră
    a = actiune(cm)
    if a == "deselect": app.selectie = []; app.deseneaza(); return "Am deselectat tot."
    if a is None and not re.search(CUV_STIL, cm): return None
    if re.fullmatch(r"(selecteaza|alege|marcheaza) (tot|toate|totul)", cm): app.selectie = list(app.doc.pagini[app.chat.ip].forme()); app.deseneaza(); return f"Am selectat tot ({len(app.selectie)} obiecte)."
    forme, ce = tinta(app, cm)
    if forme is None:
        if a in ("sterge", "muta") and app.selectie and len(cm.split()) <= 6 and not re.search(r"\d", cm.split()[-1] if a == "sterge" else ""):
            forme, ce = list(app.selectie), "obiecte selectate"
        else: return None
    if a == "sterge" and ce not in ("obiecte selectate",) and len(cm.split()) <= 2 and not forme: return None
    if not forme: return f"Nu găsesc {ce} pe pagina asta."
    n = len(forme)
    if a == "numara":
        return f"Pe pagina asta sunt {n} {ce}."
    if a == "sterge":
        if ce == "obiecte" and n > 20: return "Nu șterg toată schema dintr-o comandă. Selectează ce vrei și apasă Delete."
        app.selectie = forme; app.sterge_selectia(); return f"Am șters {n} {ce}. (Greșeală? săgeata ← sau Ctrl+Z)"
    if a == "muta":
        d = deplasare(cm)
        if not d: return f"Încotro să mut {ce}? Scrie, de ex., „mută-le la dreapta 2 cm” sau „sus 5 mm”."
        app.selectie = forme; app.muta_selectia(*d); return f"Am mutat {n} {ce} " + ("la dreapta" if d[0] > 0 else "la stânga" if d[0] < 0 else "în sus" if d[1] > 0 else "în jos") + "."
    app.selectie = forme
    categorii = ("puncte de sudură", "texte", "manșoane", "benzi de porturi", "obiecte", "locuri de sudură (etichete „X=Y”)")
    msg = "" if ce == "obiecte selectate" else (f"Am găsit și am selectat {n} {ce}." if ce in categorii or ce.startswith("linii") else f"Am găsit și am selectat {ce}.")
    rest = re.sub(r"\b(gas\w*|caut\w*|select\w*|arat\w*|marc\w*|evident\w*|colo\w*|vopse\w*|si|le|toate|sud\w*|punct\w*|de|cu|in|fibr\w*|lini\w*|cabl\w*|"
                  r"text\w*|etichet\w*|manson\w*|muf\w*|no(i|ua)|exist\w*|vechi)\b", " ", cm)
    if re.search(CUV_STIL, rest) and ce not in ("linii",) or re.search(r"\b(fa|in|cu|pe)\s+\w+", rest) and re.search(CUV_STIL, rest):
        r = app.comanda_selectie("selectate " + " ".join(rest.split()))
        if r and r.startswith("Gata"): msg = (msg + " " + r).strip()
    if not msg: return None
    if a == "arata" or a is None and n <= 3: app.zoom_pe(forme)
    else: app.deseneaza()
    return msg


# ---------------------------------------------------------------- comenzile programului, spuse liber
CE_POTI_CERE = """Ce îmi poți cere (scrie liber, fără diacritice, merge și cu greșeli):
• Fibra unui port până la client: „arata pentru port 21”, „arata portul ODF 7 cum ajunge la client”, apoi „deseneaza-l pe pagina noua”
• Porturi: „porturi libere”, „selecteaza pe schema porturile libere”, „eticheta portului”
• Suduri: „arata locurile unde este sudat”, „cate suduri sunt”, „coloreaza sudurile cu galben”
• Fibră nouă cu sudură: „CTA Nord port 3 la CTA Sud port 3 sudura in M1” sau „trage o fibra” (te întreb pas cu pas)
• Desen nou: „adauga cladire noua”, „adauga odf nou”, „adauga manson nou” – îți propun variante de așezare
• Verificare: „analizeaza schema”, „vezi neclaritatile”, „cum se poate imbunatati schema”
• Selecție și stil: „selecteaza fibrele rosii”, „fa rosu”, „fa mai gros”, „intrerupt”, „pune nr 5”, „inca”
• Editare: „copiaza”, „lipeste”, „sterge asta”, „muta-le la dreapta 1 cm”, „insereaza tabel 3 x 4”, „caseta text”
• Pagini și vedere: „pagina noua”, „pagina 2”, „potriveste”, „zoom 150”, „format A3”, „tipareste”, „salveaza”
• Cablul nou: „cablul nou rosu”, „cablul nou intrerupt”, „cablul nou ca cele existente”
• Memorie: „ce ai invatat”, „analizeaza discutia precedenta”, „inapoi” / „inainte”"""


def program(app, cm):
    if re.search(r"\b(ce (pot|poti|pots) (sa )?((te|iti) )?(cer|intreb|zic)|ce stii (sa )?(faci)?|ce comenzi|exemple|lista comenzi)\b", cm): return CE_POTI_CERE
    m = re.search(r"\b(?:insereaz\w*|adaug\w*|pune|fa|creeaz\w*)\s+(?:un\s+)?tabel\w*\D*(\d+)\s*(?:x|pe|randuri|rinduri|\*|cu)?\D*(\d+)?", cm)
    if m or re.fullmatch(r"(insereaza |adauga |pune )?(un )?tabel", cm):
        r_ = int(m.group(1)) if m and m.group(1) else 3; c_ = int(m.group(2)) if m and m.group(2) else 3
        if not (1 <= r_ <= 30 and 1 <= c_ <= 20): return "Tabelul poate avea 1–30 de rânduri și 1–20 de coloane."
        app.insereaza_tabel(r_, c_); app.modificat = True; return f"Am inserat un tabel de {r_} rânduri × {c_} coloane în mijlocul vederii. Dublu-clic pe o celulă ca să scrii."
    if re.fullmatch(r"(copiaza|copiere|copy)( asta| selectia| obiectul)?", cm):
        if not app.selectie: return "Selectează întâi ce vrei să copiezi, apoi scrie „copiaza”."
        app.copiaza(); return f"Am copiat {len(app.selectie)} obiecte. Scrie „lipeste” (sau Ctrl+V cu mausul unde vrei)."
    if re.fullmatch(r"(lipeste|lipire|paste|pune copia)( aici)?", cm): app.lipeste(); return "Am lipit ce era copiat."
    if re.fullmatch(r"(caseta (de )?text|adauga text|text nou)", cm): app.caseta_text(); return "Am pus o casetă de text – scrie în ea direct pe schemă."
    if re.fullmatch(r"(adauga |fa |deschide )?(o )?pagina noua", cm): app.pagina_noua(); return "Am făcut o pagină nouă."
    if re.fullmatch(r"(potriveste|toata schema|arata tot|vezi tot|fit)", cm): app.potriveste(); return "Am potrivit toată pagina în fereastră."
    m = re.fullmatch(r"zoom (\d+)\s*%?", cm)
    if m: app.zoom_procent(int(m.group(1))); return f"Zoom {m.group(1)}%."
    if re.fullmatch(r"(salveaza ca|salveaza cu alt nume|save as)", cm): app.salveaza_ca(); return "Am deschis fereastra „Salvează ca”."
    m = re.search(r"\bcablu\w* no(u|i)\b.*?\b(rosu intrerupt|rosu|intrerupt|ca (cele )?existente)\b", cm)
    if m and hasattr(app, "cb_stil"):
        v = {"rosu": "roșu", "intrerupt": "linie întreruptă", "rosu intrerupt": "roșu întrerupt"}.get(m.group(2), "ca cele existente")
        app.cb_stil.set(v); app.stil_cablu(); return f"De acum cablurile noi le desenez: {v}."
    return None


# ---------------------------------------------------------------- verificarea schemei
def verifica(app, cm):
    import verificare
    S = app.chat.schema; ip = app.chat.ip
    if re.search(r"\bport\w*\s+(libe|goal|neocup|nefolos)\w*", cm) and re.search(r"\b(select\w*|arat\w*|marc\w*|pe sch\w*|evident\w*|unde)\b", cm):
        lib = verificare.porturi_libere(S)
        if not lib: return "Nu sunt porturi libere pe pagina asta."
        app.marcaje = [(ip,) + b for _, _, b in lib]; app.selectie = []
        benzi = list({id(n): n.banda for n, _, _ in lib}.values())
        app.zoom_pe(benzi) if len(benzi) <= 3 else app.deseneaza()
        pe = {}
        for nd, k, _ in lib: pe.setdefault(nd.nume, []).append(k)
        import comenzi
        return f"Am marcat cu portocaliu {len(lib)} porturi libere:\n" + "\n".join(f"  {n}: {comenzi._compact(sorted(v))}" for n, v in pe.items())
    if re.search(r"\b(neclar\w*|problem\w*|greseli\w*|greseala|erori|eroare|verific\w* schema|controleaz\w*|ce e gresit|ce nu e bine)\b", cm):
        r = verificare.raport(S); sel = []; L = []
        if r["capete"]:
            L.append(f"• {len(r['capete'])} capete de linie care nu ajung nicăieri (fibră „în aer”) – marcate cu portocaliu."); sel += [f for f, _ in r["capete"]]
        if r["dublate"]: L.append(f"• {len(r['dublate'])} linii desenate de două ori, una peste alta."); sel += r["dublate"]
        if r["texte"]:
            L.append(f"• {len(r['texte'])} texte suprapuse (greu de citit): " + ", ".join(f"„{a}” peste „{b}”" for _, _, a, b in r["texte"][:4]))
            sel += [f for f, g, _, _ in r["texte"]] + [g for f, g, _, _ in r["texte"]]
        if r["rezerva"]: L.append(f"• {len(r['rezerva'])} fibre se opresc în manșon (rezervă) – e normal, doar ca informație.")
        app.marcaje = [(ip, p[0] - 0.06, p[1] - 0.06, p[0] + 0.06, p[1] + 0.06) for _, p in r["capete"]]
        if not sel:
            app.deseneaza(); return "N-am găsit neclarități: toate liniile ajung undeva, nu sunt linii dublate și nici texte suprapuse." + ("\n" + "\n".join(L) if L else "")
        ids = {}
        for f in sel: ids.setdefault(f.id, f)
        app.selectie = list(ids.values()); app.zoom_pe(app.selectie)
        return "Neclarități găsite (le-am selectat pe schemă):\n" + "\n".join(L)
    if re.search(r"\b(imbunat\w*|sfat\w*|recomand\w*|mai bun\w*|optimiz\w*)\b", cm):
        r = verificare.raport(S); L = []
        if r["capete"]: L.append(f"• Leagă sau șterge cele {len(r['capete'])} capete de linie „în aer” (scrie „vezi neclaritatile” ca să le vezi).")
        if r["dublate"]: L.append(f"• Șterge {len(r['dublate'])} linii dublate – par una, dar la tipar și la numărat fibrele încurcă.")
        if r["texte"]: L.append(f"• Mută {len(r['texte'])} texte care stau unul peste altul, ca să se poată citi.")
        if r["libere"]: L.append(f"• Ai {len(r['libere'])} porturi libere – scrie „selecteaza porturile libere” ca să le vezi; le poți folosi la clienți noi.")
        L.append("• Păstrează culoarea fibrei la fel de la un capăt la altul – așa o urmăresc corect („arata pentru port 21”).")
        return "Ce se poate îmbunătăți la schemă:\n" + "\n".join(L)
    return None


# ---------------------------------------------------------------- variante când nu înțeleg (din comenzile pe care le știu)
SABLOANE = ["gaseste sudurile si coloreaza cu galben", "selecteaza fibrele rosii", "selecteaza fibrele noi", "cate suduri sunt", "sterge sudurile",
            "arata M2", "selecteaza tot", "deselecteaza", "fa rosu", "fa mai gros", "fa intrerupt", "textul mai mare", "pune nr 5", "eticheta portului",
            "muta-le la dreapta 2 cm", "porturi libere", "tipareste", "format A3", "trage o fibra", "adauga manson nou", "adauga odf nou",
            "adauga cladire noua", "inca", "salveaza", "ce ai invatat", "arata portul ODF 2 cum ajunge la client", "deseneaza traseul pe pagina noua"]


def propune(cm, n=3):
    """cele mai apropiate comenzi cunoscute (după cuvinte comune, cu rădăcini)"""
    import difflib
    rad = lambda w: w[:5]
    cuv = {rad(w) for w in cm.split() if len(w) > 2}
    scor = []
    for s in SABLOANE:
        sc = {rad(w) for w in s.split() if len(w) > 2}
        com = len(cuv & sc)
        if com: scor.append((com + difflib.SequenceMatcher(None, cm, s).ratio(), s))
    return [s for _, s in sorted(scor, reverse=True)[:n]]
