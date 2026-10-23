"""Asistentul din chat (fără internet): ghidează pas cu pas și desenează singur ODF-uri, manșoane și clădiri noi,
le așază unde e loc pe foaie (sau pe o pagină nouă) și trage fibrele. Înțelege și fără diacritice."""
import re
import elemente, porturi, dictionar
from desen import Schema

ANULARE = re.compile(r"^(anuleaza|renunta|stop|lasa|nu mai|nu vreau|las-o|lasa-l)\b")
NUMERICE = ("nr_cutii", "porturi", "fibre", "pa", "pb")


def fd(s):
    for a, b in zip("ăâîșşțţĂÂÎȘŞȚŢ", "aaisstt" + "AAISSTT"): s = s.replace(a, b)
    return s.lower().strip()


class Agent:
    """un dialog: intenția + răspunsurile (sloturi); întreabă ce lipsește, cu variante de ales"""

    def __init__(self, chat):
        self.chat = chat; self.intentie = None; self.sloturi = {}; self.intrebare = None; self.optiuni = []; self.locuri = []

    @property
    def mem(self): return getattr(self.chat, "memorie", None)

    def _ord(self, slot, opt, cheie=lambda o: o):
        return self.mem.ordoneaza(slot, opt, cheie) if self.mem else opt

    def _intreaba(self, slot, text, opt):
        self.intrebare = slot; self.text_intrebare = text; self.optiuni = opt; return (text, False, opt)

    @property
    def activ(self): return self.intentie is not None

    # ---------------------------------------------------------------- pornire
    def porneste(self, t, orig):
        """t: mesajul fără diacritice. Întoarce (mesaj, schimbat, variante[, lucrare]) sau None dacă nu e pentru asistent."""
        if re.search(r"\bport(ul|urile)?\b.*\bla\b|\bp\d+\b", t) and not re.search(r"\b(cladire|bloc|manson|mufa|odf|cutie)\w*\s+(nou|noua)", t):
            return None                                                   # comandă de fibră pe porturi – nu e pentru asistent
        if re.search(r"^(ajuta|ajutor agent|ghid|ghideaza|ce pot face|asistent)", t):
            return ("Te pot ghida să desenezi:\n• o clădire nouă (cu ODF-uri / cutii în ea, legate cu fibre)\n• un ODF / o cutie cu porturi\n• un manșon\n"
                    "Scrie cum vrei tu (ex. „vreau un bloc nou cu 2 dulapuri de 12”) sau alege mai jos.", False,
                    ["adauga cladire noua", "adauga odf nou", "adauga manson nou"])
        u = self.mem.ultimul() if self.mem else None
        if u and re.search(r"\b(inca (unul|una|o data)|la fel|acelasi|aceeasi|mai fa (unul|una))\b", t) and u.get("tip"):
            self.intentie = u["tip"]; self.sloturi = dict(u.get("sloturi") or {}); self.sloturi.pop("nume", None); self.sloturi.pop("unde", None)
            self.prefill(t, orig); return self.urmatoarea()
        i = dictionar.intentie(t)
        if not i: return None
        self.intentie = i; self.sloturi = {}; self.prefill(t, orig)
        return self.urmatoarea()

    def prefill(self, t, orig):
        """ce a spus deja în prima frază: porturi, nume, orientare, unde"""
        t = dictionar.numere(t)
        m = re.search(r"(\d+)\s*(porturi|port|p\b|fibre|fo\b)", t) or re.search(r"\bde\s+(\d+)\b", t)
        if m: self.sloturi["porturi"] = int(m.group(1))
        m = re.search(r"(\d+)\s*(\w+)", dictionar.normalizeaza(t))
        for m in re.finditer(r"(\d+)\s+(\w+)", dictionar.normalizeaza(t)):
            if m.group(2) == "odf" and self.intentie == "cladire": self.sloturi["nr_cutii"] = int(m.group(1))
        if re.search(r"fara (odf|cutii|dulap)", t) and self.intentie == "cladire": self.sloturi["nr_cutii"] = 0
        if re.search(r"vertical", t): self.sloturi["orient"] = "v"
        if re.search(r"orizontal", t): self.sloturi["orient"] = "h"
        m = re.search(r"(?:numit|numita|nume|cu numele|cu nume)\s+[\"„]?([^\"”,]+)", orig, re.I)
        if m: self.sloturi["nume"] = m.group(1).strip()
        elif self.intentie != "cladire":                                  # „adauga manson M5 …”: numele e codul de după obiect
            m = re.search(r"(?i)\b(?:manson\w*|mufa\w*|odf|cutie\w*|dulap\w*|box\w*)\s+(?:nou[a]?\s+)?([A-Za-z]{1,6}[\-_ ]?\d+[\w\-]*)", dictionar.fd(orig))
            if m: self.sloturi["nume"] = orig[m.start(1):m.end(1)]
        m = re.search(r"\b(?:langa|linga|alaturi de|aproape de|in dreapta (?:de|la)|dupa)\s+(.+?)(?:\s+cu\s+|\s*,|$)", t)
        if m:
            ref = m.group(1).strip(); S = self.chat.schema
            try: porturi.cutie_nod(S, ref); self.sloturi["langa"] = ref
            except Exception:
                if S.gaseste(ref) is not None: self.sloturi["langa"] = ref
        if re.search(r"pagina noua|alta pagina|foaie noua", t): self.sloturi["unde"] = ("pagina", None, None)
        m = re.search(r"\b(?:sudur\w*|sudat\w*|sudez\w*|sudeaz\w*|prin)\s+(?:(?:in|la|din|prin)\s+)?(?:(?:manson\w*|mufa\w*)\s+)?(.+?)(?:\s+(?:cu|de la|langa)\s+|\s*,|$)", t)
        if m:
            try: porturi.cutie_nod(self.chat.schema, m.group(1).strip()); self.sloturi["sudura"] = self._nume_manson(m.group(1).strip())
            except Exception: pass
        if re.search(r"fara sudur|direct\b", t): self.sloturi["sudura"] = None
        m = re.search(r"\bde la\s+(.+?)(?:\s+(?:cu|prin|sudur\w*|langa)\b|\s*,|$)", t)
        if m:
            try: self.sloturi["sursa"] = porturi.gaseste_nod(self.chat.schema, m.group(1).strip()).nume
            except Exception: pass

    # ---------------------------------------------------------------- dialogul
    def noduri(self):
        try: return porturi.noduri(self.chat.schema)
        except Exception: return []

    def nume_existente(self):
        try: return [x for x, _ in porturi._candidati(self.chat.schema)][:8]
        except Exception: return []

    def urmatoarea(self):
        s = self.sloturi; i = self.intentie
        if i == "fibra": return self.urmatoarea_fibra()
        if "nume" not in s:
            ex = {"cladire": "Bloc 5, str. Test 1", "manson": "M5", "odf": "ODF Bloc 5"}[i]
            return self._intreaba("nume", f"Cum se numește {'clădirea' if i == 'cladire' else ('manșonul' if i == 'manson' else 'ODF-ul / cutia')}? (scrie numele, ex. „{ex}”)", [])
        if i == "cladire" and "nr_cutii" not in s:
            return self._intreaba("nr_cutii", "Câte ODF-uri / cutii pun în clădire?", self._ord("nr_cutii", ["1", "2", "3", "4", "fără cutii"]))
        if i in ("odf", "cladire") and s.get("nr_cutii", 1) and "porturi" not in s:
            return self._intreaba("porturi", "Câte porturi are fiecare ODF / cutie?", self._ord("porturi", ["8", "12", "24", "48"]))
        if i in ("odf", "cladire") and s.get("nr_cutii", 1) and "orient" not in s:
            return self._intreaba("orient", "Banda de porturi cum stă?", self._ord("orient", ["orizontală (porturile pe rând)", "verticală (porturile una sub alta)"],
                                                                                 lambda o: "v" if o.startswith("vert") else "h"))
        if (i == "odf" or (i == "cladire" and s.get("nr_cutii", 0))) and "sursa" not in s:
            ns = [n for n in self.noduri() if self._libere(n) > 0]
            if ns:
                ns = self._ord("sursa", ns, lambda n: n.nume)
                return self._intreaba("sursa", "De la ce nod pornesc fibrele spre " + ("clădire?" if i == "cladire" else s["nume"] + "?"), [f"{n.nume} ({self._libere(n)} porturi libere)" for n in ns[:6]] + ["fără fibre deocamdată"])
            s["sursa"] = None
        if i in ("odf", "cladire") and s.get("sursa") and "fibre" not in s:
            return self._intreaba("fibre", "Câte fibre la fiecare ODF / cutie?", self._ord("fibre", ["1", "2", "4", "toate porturile"], lambda o: "toate" if o.startswith("toate") else o))
        if i in ("odf", "cladire") and s.get("sursa") and "sudura" not in s:
            mans = porturi.mansoane(self.chat.schema)[:6]
            if mans: return self._intreaba("sudura", "Unde se face sudura? (fibrele trec prin manșon, cu punct de sudură)", ["nu, direct"] + [f"prin {m}" for m in self._ord("sudura", mans)])
            s["sudura"] = None
        if "unde" not in s:
            return self.propune_locuri()
        self.intrebare = None; self.optiuni = []; self.chat.previzualizare = []
        return self.lucrare()

    # ---------------------------------------------------------------- fibră pe porturi, cu sudură
    def urmatoarea_fibra(self):
        s = self.sloturi; ns = self.noduri()
        if not ns: self.intentie = None; return ("Pe pagina asta nu văd benzi de porturi.", False, [])
        if "A" not in s:
            return self._intreaba("A", "De la ce nod pleacă fibra?", [f"{n.nume} ({self._libere(n)} libere)" for n in sorted(self._ord("sursa", ns, lambda n: n.nume), key=lambda n: self._libere(n) == 0)[:6]])
        if "pa" not in s:
            A = porturi.gaseste_nod(self.chat.schema, s["A"]); lib = [p for p in range(1, A.n + 1) if p not in porturi.porturi_ocupate(self.chat.schema, A)]
            return self._intreaba("pa", f"Ce port(uri) la {s['A']}? (ex. 3 sau 1-4)", [str(p) for p in lib[:4]] + ([f"{lib[0]}-{lib[min(3, len(lib) - 1)]}"] if len(lib) > 1 else []))
        if "B" not in s:
            return self._intreaba("B", "Până la ce nod?", [f"{n.nume} ({self._libere(n)} libere)" for n in sorted(ns, key=lambda n: self._libere(n) == 0) if n.nume != s["A"]][:6])
        if "pb" not in s:
            B = porturi.gaseste_nod(self.chat.schema, s["B"]); lib = [p for p in range(1, B.n + 1) if p not in porturi.porturi_ocupate(self.chat.schema, B)]
            k = len(s["pa"]); opt = [f"{lib[0]}-{lib[k - 1]}" if k > 1 else str(lib[0])] if len(lib) >= k else []
            return self._intreaba("pb", f"Pe ce port(uri) la {s['B']}? ({k} {'port' if k == 1 else 'porturi'})", opt + (["aceleași numere"] if k else []))
        if "sudura" not in s:
            mans = porturi.mansoane(self.chat.schema)[:6]
            if mans: return self._intreaba("sudura", "Unde se face sudura?", ["fără sudură (direct)"] + [f"sudura in {m}" for m in self._ord("sudura", mans)])
            s["sudura"] = None
        self.intrebare = None; self.optiuni = []; self.intentie = None
        cmd = f"{s['A']} port {','.join(map(str, s['pa']))} la {s['B']} port {','.join(map(str, s['pb']))}" + (f" sudura in {s['sudura']}" if s.get("sudura") else "")
        ch = self.chat; ip = ch.ip
        def lucreaza():
            S = Schema(ch.doc, ch.doc.pagini[ip]); r = porturi.comanda(S, dictionar.fd(cmd))
            if r is None: raise ValueError(f"comanda „{cmd}” n-a mers")
            return (r if isinstance(r, str) else r[0]), True, ip
        return (f"Agentul trage fibra: {cmd}.", False, [], (f"fibra {s['A']} → {s['B']}", lucreaza))

    def _nume_manson(self, nm):
        """numele așa cum e scris pe schemă (M2, nu m2)"""
        for m in porturi.mansoane(self.chat.schema):
            if dictionar.fd(m) == dictionar.fd(nm) or dictionar.fd(m).startswith(dictionar.fd(nm) + " "): return m
        return nm

    def _porturi_din(self, t, nod):
        import comenzi
        m = re.findall(r"\d+\s*(?:-|–|pana la)\s*\d+|\d+", t)
        return comenzi.interval(",".join(m)) if m else []

    # ---------------------------------------------------------------- variante de așezare
    def _marime(self):
        s = self.sloturi; i = self.intentie; n = s.get("porturi", 12); orient = s.get("orient", "h" if i == "cladire" else "v")
        if i == "odf": w, h = elemente.marime_odf(n, orient); return w, h + 0.3 * elemente.K
        if i == "manson": w, h = elemente.marime_manson(); return w, h + 0.3 * elemente.K
        return elemente.marime_cladire([n] * s.get("nr_cutii", 0), orient)

    def _langa_xy(self, ref, w):
        S = self.chat.schema
        try:
            b = porturi.cutie_nod(S, ref); return (b[2] + w / 2 + 0.5, (b[1] + b[3]) / 2)
        except Exception:
            f = S.gaseste(ref)
            if f is not None: c = f.centru(); return (c[0] + w, c[1])
        return None

    def propune_locuri(self):
        """2–4 așezări diferite, desenate punctat pe schemă (1, 2, 3…): alegi una, sau pagină nouă"""
        S = self.chat.schema; elemente.potriveste_scara(S); w, h = self._marime(); tinte = []
        for ref in [self.sloturi.get("langa"), self.sloturi.get("sursa"), self.sloturi.get("sudura")]:
            if ref:
                xy = self._langa_xy(ref, w)
                if xy: tinte.append((xy[0], xy[1], f"lângă {ref}"))
        u = self.mem.ultimul() if self.mem else None
        if u and u.get("pagina") == self.chat.ip and u.get("nume"):
            xy = self._langa_xy(u["nume"], w)
            if xy: tinte.append((xy[0], xy[1], f"lângă {u['nume']} (ultimul desenat)"))
        self.locuri = elemente.variante_loc(S, w, h, tinte, n=4)
        self.chat.previzualizare = [(self.chat.ip, x - w / 2, y - h / 2, x + w / 2, y + h / 2, str(k)) for k, (x, y, _) in enumerate(self.locuri, 1)]
        opt = [f"varianta {k}: {d}" for k, (_, _, d) in enumerate(self.locuri, 1)] + ["pe o pagină nouă"]
        if not self.locuri:
            return self._intreaba("unde", "Pe pagina asta nu mai e loc. Îl pun pe o pagină nouă?", ["pe o pagină nouă", "anuleaza"])
        txt = (f"Ți-am desenat punctat pe schemă {len(self.locuri)} variant{'ă' if len(self.locuri) == 1 else 'e'} de așezare (1, 2, 3…)."
               + (f" Pe schema asta mică desenez la scara {elemente.K:.2f}." if abs(elemente.K - 1) > 0.15 else "")
               + " Alege una (clic pe ea în chat sau pe dreptunghiul de pe schemă):")
        return self._intreaba("unde", txt, opt)

    def _libere(self, nd):
        try: return nd.n - len(porturi.porturi_ocupate(self.chat.schema, nd))
        except Exception: return 0

    def neinteles(self, text):
        """n-am înțeles răspunsul: aceeași întrebare din nou, cu variantele de ales"""
        q = self.intrebare; r = self.urmatoarea()
        return (text + "\n" + r[0] + "\n(sau scrie „anuleaza” ca să renunți)", r[1], r[2])

    def raspunde(self, t, orig):
        t = dictionar.fd(t).strip(" .!")
        if ANULARE.search(t):
            self.intentie = None; self.chat.previzualizare = []; return ("Bine, am renunțat.", False, [])
        if t in ("?", "nu stiu", "nu inteleg", "ajutor", "help", "ce", "adica", "cum adica"):
            return self.neinteles("Îți explic: aleg eu variantele potrivite din schema ta – apasă pe una de mai jos.")
        q = self.intrebare; s = self.sloturi; o = orig.strip()
        if re.fullmatch(r"\d+", t) and self.optiuni and (q not in NUMERICE) and 1 <= int(t) <= len(self.optiuni):
            o = self.optiuni[int(t) - 1]; t = dictionar.fd(o)                 # a ales varianta după număr
        t = dictionar.numere(t)
        if q in ("A", "B"):
            try: s[q] = porturi.gaseste_nod(self.chat.schema, re.sub(r"\s*\(.*$", "", re.sub(r"^(de la|din|la|pana la)\s+", "", o, flags=re.I))).nume
            except Exception: return self.neinteles("Nu găsesc nodul ăsta. Alege:")
            if self._libere(porturi.gaseste_nod(self.chat.schema, s[q])) == 0:
                nm = s.pop(q); return self.neinteles(f"{nm} nu mai are porturi libere. Alege alt nod:")
            if self.mem and q == "A": self.mem.alege("sursa", s[q])
            return self.urmatoarea()
        if q in ("pa", "pb"):
            p = list(s["pa"]) if q == "pb" and re.search(r"aceleasi|la fel", t) else self._porturi_din(t, None)
            if not p: return self.neinteles("Scrie numărul portului (ex. 3 sau 1-4).")
            if q == "pb" and len(p) != len(s["pa"]): return self.neinteles(f"Trebuie {len(s['pa'])} porturi, ai scris {len(p)}.")
            S = self.chat.schema; nd = porturi.gaseste_nod(S, s["A" if q == "pa" else "B"])
            ocup = sorted(set(p) & set(porturi.porturi_ocupate(S, nd))); peste = [x for x in p if x > nd.n]
            if peste: return self.neinteles(f"{nd.nume} are doar {nd.n} porturi.")
            if ocup: return self.neinteles(f"La {nd.nume} portul {', '.join(map(str, ocup))} e deja ocupat.")
            s[q] = p; return self.urmatoarea()
        if q == "nume":
            if len(o) < 1: return ("Scrie un nume, te rog.", False, [])
            o = re.sub(r"(?i)^(se (numeste|cheama)|numele( este| e)?|il cheama|ii zice|denumirea)\s+", "", o)
            s["nume"] = o.strip("\"„” ")
        elif q == "nr_cutii":
            if re.search(r"fara|^0|niciuna|nici una|nimic", t): s["nr_cutii"] = 0
            else:
                m = re.search(r"\d+", t)
                if not m: return self.neinteles("Scrie un număr (ex. 2).")
                s["nr_cutii"] = min(8, int(m.group()))
        elif q == "porturi":
            m = re.search(r"\d+", t)
            if not m or not 1 <= int(m.group()) <= 96: return self.neinteles("Scrie numărul de porturi (1–96).")
            s["porturi"] = int(m.group())
        elif q == "orient":
            if re.search(r"vert|una sub|sub alta|sus|jos|in picioare|coloana", t): s["orient"] = "v"
            elif re.search(r"oriz|rand|lat|stanga|dreapta|culcat|linie", t): s["orient"] = "h"
            else: return self.neinteles("N-am înțeles cum stă banda. Alege:")
        elif q == "unde":
            m = re.search(r"(?:varianta|var|v|nr|numarul)?\s*(\d+)\b", t)
            if re.search(r"pagin\w* nou|alta pagina|foaie noua|pagina urmatoare", t): s["unde"] = ("pagina", None, None)
            elif m and 1 <= int(m.group(1)) <= len(self.locuri):
                x, y, d = self.locuri[int(m.group(1)) - 1]; s["unde"] = ("xy", (x, y), d)
            elif re.fullmatch(r"\d+", t): return self.neinteles(f"Nu am varianta {t}. Alege una:")
            elif re.search(r"liber|oriunde|unde vrei|cum crezi|tu alegi|alege tu|nu conteaza", t) and self.locuri:
                x, y, d = self.locuri[0]; s["unde"] = ("xy", (x, y), d)
            else:
                nume = re.sub(r"^(pune-?l|pune-?o|il pui|o pui)?\s*(langa|linga|la|sub|deasupra|dreapta|stanga|in|alaturi de|aproape de)\s+(de\s+)?", "", t)
                if self._langa_xy(nume, 1) is None: return self.neinteles(f"Nu găsesc „{nume}” pe schemă. Alege o variantă:")
                s["langa"] = nume; return self.propune_locuri()
        elif q == "sursa":
            if re.search(r"^(fara|nu\b|deocamdata|niciun|nimic)", t): s["sursa"] = None
            else:
                try: s["sursa"] = porturi.gaseste_nod(self.chat.schema, re.sub(r"\s*\(.*$", "", re.sub(r"^(de la|din|la)\s+", "", o, flags=re.I))).nume
                except Exception:
                    return self.neinteles("Nu găsesc nodul ăsta. Alege de la ce nod pornesc fibrele:")
        elif q == "fibre":
            if "toate" in t: s["fibre"] = "toate"
            else:
                m = re.search(r"\d+", t)
                if not m: return self.neinteles("Câte fibre? Scrie un număr sau „toate”.")
                s["fibre"] = int(m.group())
        elif q == "sudura":
            if re.search(r"^(nu|direct|fara)|fara sudura", t): s["sudura"] = None
            else:
                nm = re.sub(r"(?i)^(da,?\s+)?(prin|sudura|sudat|sudeaza)?\s*(in|la|prin)?\s*(manson\w*|mufa\w*)?\s*", "", dictionar.fd(o)).strip()
                try: porturi.cutie_nod(self.chat.schema, nm); s["sudura"] = self._nume_manson(nm)
                except Exception: return self.neinteles(f"Nu găsesc manșonul „{nm}”. Alege:")
        if self.mem and q in ("nr_cutii", "porturi", "orient", "sursa", "fibre", "sudura") and s.get(q) is not None:
            self.mem.alege(q, s[q])
        return self.urmatoarea()

    # ---------------------------------------------------------------- desenul (lucrarea unui agent, în fundal)
    def lucrare(self):
        """dialogul s-a terminat: dau lucrarea unui agent (rulează în fundal, chatul rămâne liber)"""
        s = dict(self.sloturi); i = self.intentie; ip = self.chat.ip; K = elemente.K; self.intentie = None
        ce = {"cladire": f"clădirea „{s['nume']}”", "manson": f"manșonul {s['nume']}", "odf": f"{s['nume']}"}[i]
        def lucreaza():
            elemente.K = K
            return self.executa(i, s, ip)
        return (f"Am dat lucrarea unui agent: desenează {ce}. Între timp poți scrie mai departe.", False, [], (f"desenez {ce}", lucreaza))

    def executa(self, i, s, ip):
        ch = self.chat; doc = ch.doc
        n = s.get("porturi", 12); orient = s.get("orient", "h" if i == "cladire" else "v")
        w, h = self._marime_din(i, s)
        S = Schema(doc, doc.pagini[ip]); pag_noua = False; mesaj_loc = ""; pag_veche = ip
        tip, poz, desc = s.get("unde", ("xy", None, ""))
        if tip == "xy":
            # între timp alt agent poate a desenat acolo: verific și, la nevoie, caut cel mai apropiat loc liber
            lib = elemente.loc_liber(S, w, h, poz)
            if lib and (abs(lib[0] - poz[0]) > 0.05 or abs(lib[1] - poz[1]) > 0.05): mesaj_loc = " (Locul ales se ocupase între timp – l-am mutat alături.)"
            poz = lib
        else: poz = None
        if poz is None:                                               # nu încape: pagină nouă, cu același format
            p = doc.pagina_noua(f"{s['nume']}"); ip = doc.pagini.index(p); S = Schema(doc, p)
            pag_noua = True; W, H = S.p.dimensiune(); poz = (W / 2, H / 2)
            mesaj_loc = (" Pe pagina curentă nu era loc, așa că l-am pus pe o pagină nouă" if tip != "pagina" else " L-am pus pe o pagină nouă") + f" („{p.nume}”)."
        cx, cy = poz; K = elemente.K
        if self.mem: self.mem.ultimul(s["nume"], i, ip); self.mem.d["ultimul"]["sloturi"] = {k: v for k, v in s.items() if k not in ("unde",)}
        if i == "odf":
            elemente.odf(S, s["nume"], n, cx, cy, orient)
            msg = f"✔ Am desenat {s['nume']} cu {n} porturi ({'vertical' if orient == 'v' else 'orizontal'})." + mesaj_loc
            if s.get("sursa") and not pag_noua: msg += self._fibre(S, [s["nume"]], s)
            else: msg += " Acum poți trage fibre la el, ex. „<nod> port 1 la " + s["nume"] + " port 1 sudura in M1”."
            return msg, True, ip
        if i == "manson":
            elemente.manson(S, s["nume"], cx, cy)
            return (f"✔ Am desenat manșonul {s['nume']}." + mesaj_loc + f" Fibrele le poți trece prin el cu „… prin {s['nume']}”.", True, ip)
        # clădire cu cutii
        x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        elemente.cladire(S, s["nume"], x0, y0, x1, y1)
        k = s.get("nr_cutii", 0); nume_cutii = []
        for j in range(k):
            nm = f"ODF {j + 1} {s['nume']}" if k > 1 else f"ODF {s['nume']}"
            ow, oh = elemente.marime_odf(n, orient)
            ocx, ocy = x0 + 0.35 * K + j * (ow + 0.45 * K) + ow / 2, cy - 0.2 * K
            elemente.odf(S, nm, n, ocx, ocy, orient); nume_cutii.append(nm)
        msg = f"✔ Am desenat clădirea „{s['nume']}”" + (f" cu {k} ODF ({n} porturi fiecare)" if k else "") + "." + mesaj_loc
        if s.get("sursa") and k:
            if pag_noua:
                msg += f" Fibrele de la {s['sursa']} nu le pot trage pe altă pagină – am pus trimiteri „Vezi pag.”."
                elemente.text(S, x0 + 0.6, y1 + 0.25, f"← de la {s['sursa']} (pag. {pag_veche + 1})", pt=9, w=2.6, culoare="#C00000")
                S0 = Schema(doc, doc.pagini[pag_veche])
                try:
                    A = porturi.gaseste_nod(S0, s["sursa"]); b = A.banda.cutie()
                    elemente.text(S0, b[2] + 1.2, (b[1] + b[3]) / 2, f"→ {s['nume']}: vezi pag. {ip + 1}", pt=9, w=2.6, culoare="#C00000")
                except Exception: pass
            else: msg += self._fibre(S, nume_cutii, s)
        return msg, True, ip

    def _fibre(self, S, nume_cutii, s):
        """fibrele de la sursă la fiecare cutie, pe porturile libere, cu sudură în manșonul ales"""
        try:
            A = porturi.gaseste_nod(S, s["sursa"]); libere = [p for p in range(1, A.n + 1) if p not in porturi.porturi_ocupate(S, A)]
            tot = 0
            for nm in nume_cutii:
                B = porturi.gaseste_nod(S, nm); nf = B.n if s.get("fibre") == "toate" else min(int(s.get("fibre") or 1), B.n)
                for q in range(nf):
                    if not libere: break
                    porturi.trage(S, A, libere.pop(0), B, q + 1, decalaj=(tot - 2) * porturi.PAS, sudura=s.get("sudura")); tot += 1
            msg = f" Am tras {tot} fibre de la {A.nume}" + (f", cu sudură în {s['sudura']}" if s.get("sudura") else "") + "."
            return msg + (" (Nu mai sunt porturi libere la sursă.)" if not libere else "")
        except Exception as e:
            return f" Fibrele nu le-am putut trage: {e}"

    def _marime_din(self, i, s):
        vechi = self.intentie, self.sloturi
        self.intentie, self.sloturi = i, s
        try: return self._marime()
        finally: self.intentie, self.sloturi = vechi
