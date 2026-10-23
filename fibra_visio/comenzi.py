"""Chatul: înțelege comenzile scrise în română (cu sau fără diacritice) și le face pe schemă.
Fără internet: comenzile au forme fixe, cu multe variante. „ajutor” arată lista."""
import math, os, re
from desen import Schema, CUVINTE_TIP, TIPURI, tip_din_nume, pagina_sudura, RE_CABLU
from vsdx_doc import norm

AJUTOR = """Ce pot face (scrie ca în exemple; diacriticele nu contează):
• adaugă manșon M5 lângă M3          (manșon, ODF, splitter, stâlp, cămin, bloc, cutie)
• adaugă stâlp S12 la dreapta de M3    (dreapta / stânga / sus / jos)
• adaugă splitter SP1 1:8 lângă B4
• adaugă cablu 24FO de la M3 la S12, 150 m   (dacă S12 nu există, îl desenez)
• adaugă cablu 24FO întrerupt de la M3 la S12   (cablul nou: roșu / întrerupt, se alege sus)
• schimbă lungimea de la M1 la S5 în 180 m
• schimbă cablul de la M1 la S5 în 48FO
• șterge cablul de la M1 la S5   /   șterge M5
• mută M5 la dreapta cu 2 cm   /   mută M5 lângă S7
• redenumește M5 în M6
• în M1 sudează fibrele 1-12 din M1-S5 cu 13-24 din ODF1-M1
FIBRE PE PORTURI (scheme cu benzi galbene de porturi; numele le citesc din schema ta):
• CTA Nord port 1 la CTA Sud port 2
• trage fibrele de la CTA Nord 9-12 la BTS_Est 1-4 albastru
• portul 7 din CTA Sud la portul 2 din BTS_Vest intrerupt
• nord p3 la vest p3 sudura in M1     (merge și prescurtat, fără spații, cu mici greșeli)
• porturi   (ce benzi de porturi sunt pe pagină)
• listă  (ce e pe pagină)   •  cabluri   •  pagini   •  pagina 2
• anulează   •  salvează"""

DIRECTII = {"dreapta": "dreapta", "stanga": "stanga", "sus": "sus", "jos": "jos", "deasupra": "sus", "dedesubt": "jos", "sub": "jos"}


def fara_diacritice(s):
    for a, b in zip("ăâîșşțţĂÂÎȘŞȚŢ", "aaisstt" + "AAISSTT"): s = s.replace(a, b)
    return s


def interval(s):
    """„1-12” -> [1..12]; „1,3,5-7” -> [1,3,5,6,7]"""
    out = []
    for p in re.split(r"[,;]\s*|\s+si\s+", s.strip()):
        m = re.fullmatch(r"(\d+)\s*(?:-|–|pana la)\s*(\d+)", p.strip())
        if m: a, b = int(m.group(1)), int(m.group(2)); out += list(range(a, b + 1) if a <= b else range(a, b - 1, -1))
        elif p.strip().isdigit(): out.append(int(p))
    return out


NUME = r"([A-Za-z][\w.\-/]*\d[\w.\-/]*|[A-Za-z]+-?\d+\w*|\"[^\"]+\")"


def curat(n): return n.strip().strip('"').strip()


_MEMORIE = None


def memorie_comuna():
    """o singură memorie pentru toate schemele (fișierul de pe calculator)"""
    global _MEMORIE
    if _MEMORIE is None:
        import memorie
        try: _MEMORIE = memorie.Memorie()
        except Exception: _MEMORIE = memorie.Memorie(cale=os.path.join(os.path.expanduser("~"), ".fibravisio_memorie.json"))
    return _MEMORIE


NEINTELES = ("Nu am înțeles", "N-am", "Nu găsesc", "Scrie un", "Scrie numărul", "Câte fibre?")


def _compact(nr):
    """[1,2,3,7,9,10] -> „1-3, 7, 9-10”"""
    out = []; i = 0
    while i < len(nr):
        j = i
        while j + 1 < len(nr) and nr[j + 1] == nr[j] + 1: j += 1
        out.append(f"{nr[i]}-{nr[j]}" if j > i else str(nr[i])); i = j + 1
    return ", ".join(out)


def vorbeste_fara_schema(mesaj):
    """chatul merge și înainte să deschizi o schemă: salut, memorie, „cum fac…”, ajutor"""
    import dictionar
    t = re.sub(r"\s+", " ", fara_diacritice(mesaj.strip()).lower()).strip(" .!?")
    m = memorie_comuna()
    if re.search(r"\bporturi\w* (libere|ocupate|goale|folosite)|\b(cate|ce) porturi\b", t):
        r = "Deschide întâi o schemă și îți spun ce porturi sunt libere."
    else:
        class _D: pass
        d = _D(); d.memorie = m; d.stare_agenti = lambda: "Niciun agent nu lucrează acum."
        r = Chat.vorbeste(d, t)
    if r and r.startswith("Salut"): r = "Salut! Deschide o schemă (butonul „Deschide schema…” sau trage fișierul peste fereastră) și spune-mi liber ce vrei – ex. „vreau un bloc nou cu 2 dulapuri de 12 porturi”."
    if r is None:
        if t in ("ajutor", "help", "?", "comenzi", "ce poti face"): r = AJUTOR
        elif dictionar.intentie(t) or re.search(r"\bport", t):
            r = "Te-am înțeles – ca să desenez, deschide întâi schema (butonul „Deschide schema…” sau trage fișierul peste fereastră) sau apasă „Schemă nouă”. Apoi scrie din nou."
        else:
            r = "Deschide o schemă (butonul „Deschide schema…”, trage fișierul peste fereastră sau „Schemă nouă”) și spune-mi liber ce vrei să fac pe ea."
    try: m.noteaza(mesaj, r, True)
    except Exception: pass
    return r


class Chat:
    def __init__(self, doc):
        import threading
        self.doc = doc; self.ip = 0; self.istoric = []; self.refacere = []; self.variante = []
        self.memorie = memorie_comuna(); self.previzualizare = []; self.lucrari = []; self.lacat = threading.RLock()
        self.stare_agenti = lambda: "Niciun agent nu lucrează acum."
        import asistent; self.agent = asistent.Agent(self)

    def ruleaza_lucrare(self, fn):
        """rulează lucrarea unui agent (în firul lui), cu lacăt pe schemă și pas de „înapoi”"""
        with self.lacat:
            stare = self.doc.instantaneu()
            try: r = fn()
            except Exception as e:
                self.doc.restaureaza(stare); return f"N-am reușit: {e}", False, None
            msg, sch = r[0], r[1]; ip = r[2] if len(r) > 2 else None
            if sch: self.istoric.append(stare); self.istoric = self.istoric[-50:]; self.refacere = []
            return msg, sch, ip

    @property
    def schema(self): return Schema(self.doc, self.doc.pagini[self.ip])

    def raspunde(self, mesaj):
        """-> (răspuns, s-a schimbat desenul). Notează discuția în memorie și învață din ea."""
        prec = self.variante
        if re.fullmatch(r"\s*[1-9]\s*", mesaj) and prec and int(mesaj) <= len(prec) and not self.agent.activ:
            mesaj = prec[int(mesaj) - 1]                                  # în memorie notez varianta aleasă, nu cifra
        r, sch = self._raspunde(mesaj)
        try:
            ok = not r.startswith(NEINTELES)
            if not re.fullmatch(r"\s*\d+\s*", mesaj) or not ok: self.memorie.noteaza(mesaj, r, ok, self.doc.pagini[self.ip].nume)
            else: self.memorie.noteaza(mesaj, r, ok)
        except Exception: pass
        return r, sch

    def vorbeste(self, t):
        """discuție (nu schimbă schema): memorie, agenți, „cum fac…”. -> text sau None"""
        import dictionar
        m = self.memorie
        if re.search(r"\b(ce (ai|mai) invatat|ce stii despre mine|memori(a|e)|ce tii minte|ce ti-am spus)\b", t): return m.rezumat()
        if re.search(r"\b(discuti\w* (precedent|trecut|de (ieri|azi|dinainte))|ce am (vorbit|discutat|scris)|istoric\w*|analizeaza discuti\w*)\b", t):
            m.invata_din_istoric(); return m.ultimele(12) + "\n\nAm recitit discuțiile și am reînvățat din ele.\n" + m.rezumat()
        if re.fullmatch(r"(uita tot|sterge memoria|goleste memoria)", t): m.uita(); return "Am uitat tot ce am învățat (memoria e goală)."
        if re.search(r"\b(ce (fac|lucreaza) agentii|agenti|ce faci acum|cat mai (dureaza|ai)|e gata\??|status)\b", t): return self.stare_agenti()
        if re.search(r"\bporturi\w* (libere|ocupate|goale|folosite)|\b(cate|ce) porturi\b|\bunde (am|e|sunt) (loc|porturi)", t):
            import porturi
            S = self.schema; out = []
            for nd in porturi.noduri(S):
                oc = set(porturi.porturi_ocupate(S, nd)); lib = [p for p in range(1, nd.n + 1) if p not in oc]
                out.append(f"  {nd.nume}: {len(lib)} libere" + (f" ({_compact(lib)})" if lib else ""))
            return ("Porturi libere pe pagină:\n" + "\n".join(out)) if out else "Nu văd benzi de porturi pe pagina asta."
        if re.fullmatch(r"(salut|buna( ziua| seara| dimineata)?|noroc|hei|alo|privet|привет)", t):
            return "Salut! Spune-mi liber ce vrei pe schemă (ex. „vreau un bloc nou cu 2 dulapuri de 12 porturi lângă CTA Nord”)."
        if re.fullmatch(r"(multumesc|mersi|merci|bravo|super|ok|bine|spasibo|спасибо)", t): return "Cu plăcere! Ce mai facem?"
        return dictionar.cum_fac(t)

    def _raspunde(self, mesaj, traduce=True):
        prec, self.variante = self.variante, []
        t1 = re.sub(r"\s+", " ", fara_diacritice(mesaj.strip()).lower()).strip(" .!?")
        if not self.agent.activ:
            v = self.vorbeste(t1)
            if v: return v, False
            tr = self.memorie.traduce(mesaj) if traduce else None
            if tr and fara_diacritice(tr).lower().strip() != t1:            # am mai auzit asta: știu ce înseamnă
                r, sch = self._raspunde(tr, traduce=False)
                return f"(Am înțeles: „{tr}”)\n" + r, sch
        # asistentul: dialog pas cu pas (desenează ODF / manșon / clădire)
        import asistent, dictionar
        t0 = fara_diacritice(mesaj.strip()).lower()
        ag = self.agent
        if not ag.activ and re.fullmatch(r"(continua|reia|mergi mai departe|hai inapoi la (ea|el))", t1) and getattr(self, "amanate", None):
            self.agent = self.amanate.pop(); r = self.agent.urmatoarea(); self.variante = r[2]
            return "Reiau de unde am rămas. " + r[0], False
        if ag.activ:
            q = ag.intrebare
            v = self.vorbeste(t1)
            if v:                                                          # o întrebare pe lângă: răspund și țin dialogul deschis
                self.variante = ag.optiuni; return v + "\n\n(Încă aștept răspunsul la: " + getattr(ag, "text_intrebare", q or "") + ")", False
            if q != "nume" and dictionar.intentie(t1):                     # cere altceva nou: pun dialogul deoparte, încep altul
                self.amanate = (getattr(self, "amanate", None) or []) + [ag]; self.agent = asistent.Agent(self)
                r = self.agent.porneste(t0, mesaj)
                if r is not None:
                    self.variante = r[2]
                    return f"(Am pus deoparte „{ag.sloturi.get('nume', ag.intentie)}” – scrie „continua” ca s-o reiau.)\n" + r[0], False
                self.agent = self.amanate.pop()
            if re.search(r"\bport\w*\b.*\bla\b|\bp\d+\b.*\bla\b", t1) and q not in ("nume",):      # comandă de fibră în timpul dialogului
                self.agent = asistent.Agent(self)
                try: r, sch = self._raspunde(mesaj, traduce=False)
                finally: self.agent = ag
                self.variante = ag.optiuni
                return r + "\n\n(Revin la întrebarea de dinainte – alege mai jos.)", sch
        if self.agent.activ or not re.fullmatch(r"\s*[1-6]\s*", mesaj):
            stare = self.doc.instantaneu()
            try:
                r = self.agent.raspunde(t0, mesaj) if self.agent.activ else self.agent.porneste(t0, mesaj)
            except Exception as e:
                self.agent.intentie = None; self.doc.restaureaza(stare); return f"N-am reușit: {e}", True
            if r is not None:
                txt, sch, var = r[:3]; self.variante = var
                if sch: self.istoric.append(stare); self.istoric = self.istoric[-50:]; self.refacere = []
                if len(r) > 3 and r[3]:                                     # dialogul s-a terminat: lucrarea pleacă la un agent
                    self.lucrari.append(r[3]); self.agent = asistent.Agent(self)
                return txt, sch
        if re.fullmatch(r"\s*[1-6]\s*", mesaj) and prec and int(mesaj) <= len(prec):     # a ales o variantă propusă
            mesaj = prec[int(mesaj) - 1]
        mesaj = re.sub(r"^[\s•\-*·>]+", "", mesaj.strip())                 # fără buline / liniuțe copiate din ajutor
        mesaj = re.sub(r"\s{2,}\(.*\)\s*$", "", mesaj)                       # fără explicația din paranteză
        t = fara_diacritice(mesaj.strip()).lower()
        t = re.sub(r"\s+", " ", t).rstrip(".!")
        if not t: return "", False
        if t in ("ajutor", "help", "?", "comenzi", "ce poti face"): return AJUTOR, False
        if re.fullmatch(r"(anuleaza|undo|inapoi)( tot)?", t): return self.inapoi()
        if re.fullmatch(r"(reface|refa|redo|inainte)", t): return self.inainte()
        if re.fullmatch(r"(lista|listă|elemente|ce (e|este) pe (pagina|schema)|arata tot)", t): return self.lista(), False
        if t in ("cabluri", "lista cabluri", "arata cablurile"): return self.lista_cabluri(), False
        if t in ("pagini", "lista pagini"):
            return "Pagini: " + ", ".join(f"{i + 1}. {p.nume}" + (" (deschisă)" if i == self.ip else "") for i, p in enumerate(self.doc.pagini)), False
        m = re.fullmatch(r"(?:deschide )?pagina (\d+)", t)
        if m:
            k = int(m.group(1)) - 1
            if not 0 <= k < len(self.doc.pagini): return f"Nu există pagina {k + 1}. Sunt {len(self.doc.pagini)}.", False
            self.ip = k; return f"Am deschis pagina {k + 1}: {self.doc.pagini[k].nume}.", True
        if not self.lacat.acquire(blocking=False):                       # un agent desenează acum: comanda merge la rând
            self.lucrari.append((f"comanda „{mesaj}”", lambda m=mesaj, tt=t: (self.executa(m, tt) or ("Nu am înțeles comanda „" + m + "”.", False)) + (self.ip,)))
            return f"Un agent lucrează acum pe schemă – am pus comanda la rând, o fac imediat după el.", False
        try: return self._executa_direct(mesaj, t)
        finally: self.lacat.release()

    def _executa_direct(self, mesaj, t):
        stare = self.doc.instantaneu()
        try:
            r = self.executa(mesaj, t)
        except Exception as e:
            self.doc.restaureaza(stare); self.variante = self.propune(mesaj, str(e))
            return f"N-am reușit: {e}" + ("\nAi vrut să scrii:" if self.variante else ""), True
        if r is None:
            self.variante = self.propune(mesaj, "")
            return "Nu am înțeles comanda." + (" Ai vrut să scrii:" if self.variante else " Scrie „ajutor” ca să vezi exemple."), False
        if r[1]: self.istoric.append(stare); self.istoric = self.istoric[-50:]; self.refacere = []
        return r

    def inapoi(self):
        if not self.lacat.acquire(blocking=False): return "Un agent desenează acum – încearcă din nou peste o clipă.", False
        try: return self._inapoi()
        finally: self.lacat.release()

    def _inapoi(self):
        if not self.istoric: return "Nu am ce anula.", False
        self.refacere.append(self.doc.instantaneu()); self.doc.restaureaza(self.istoric.pop())
        self.ip = min(self.ip, len(self.doc.pagini) - 1); return "Înapoi: am anulat ultima modificare.", True

    def inainte(self):
        if not self.lacat.acquire(blocking=False): return "Un agent desenează acum – încearcă din nou peste o clipă.", False
        try: return self._inainte()
        finally: self.lacat.release()

    def _inainte(self):
        if not self.refacere: return "Nu am ce reface.", False
        self.istoric.append(self.doc.instantaneu()); self.doc.restaureaza(self.refacere.pop())
        self.ip = min(self.ip, len(self.doc.pagini) - 1); return "Înainte: am refăcut modificarea.", True

    # ---------- variante corecte când comanda e greșită ----------
    VOCAB = ["adauga", "trage", "leaga", "cablu", "cablul", "elementul", "manson", "stalp", "odf", "splitter", "camin", "bloc", "cutie", "port", "porturile",
             "la", "de", "din", "cu", "prin", "sudura", "in", "rosu", "albastru", "verde", "intrerupt", "sterge", "muta", "redenumeste",
             "schimba", "lungimea", "fibra", "fibrele", "dreapta", "stanga", "sus", "jos", "langa", "lista", "cabluri", "porturi",
             "pagini", "pagina", "anuleaza", "inapoi", "inainte", "salveaza", "ajutor", "sudeaza"]

    def propune(self, mesaj, eroare):
        import difflib, porturi
        S = self.schema; t = fara_diacritice(mesaj).strip(); out = []
        try: noduri = [n.nume for n in porturi.noduri(S)]
        except Exception: noduri = []
        try: nume = [x for x, _ in porturi._candidati(S)] + [x.split("\n")[0] for x, _ in S.elemente()]
        except Exception: nume = noduri[:]
        # 1) nume ambiguu: „cta” poate fi: CTA Nord, CTA Sud
        m = re.search(r"„(.+?)” (?:poate fi|se potrivește la mai multe): (.+?)(?:\. |$)", eroare)
        if m:
            for opt in [x.strip() for x in m.group(2).split(",")][:4]:
                out.append(re.sub(re.escape(m.group(1)), opt, t, count=1, flags=re.I))
        # 2) cuvinte scrise greșit -> cel mai apropiat cuvânt de comandă / nume din schemă
        cuv = re.findall(r"[\w\-.]+|\S", t); corect = []; schimbat = False
        dict_n = {norm(x).lower(): x for x in nume if x}
        try: span_nume = [(a, b) for a, b, _, _ in porturi.mentiuni(S, t.lower())]
        except Exception: span_nume = []
        cuvinte_nume = {w.lower() for x in nume for w in re.split(r"[\s_\-./]+", x) if w}
        poz = 0
        for w in cuv:
            st = t.find(w, poz); poz = st + len(w) if st >= 0 else poz
            wl = w.lower()
            if (not re.search(r"[a-z]", wl) or len(wl) < 3 or wl in self.VOCAB or norm(w).lower() in dict_n or wl in cuvinte_nume
                    or any(a <= st < b for a, b in span_nume)): corect.append(w); continue
            g = difflib.get_close_matches(wl, self.VOCAB, n=1, cutoff=0.75) or \
                [dict_n[x] for x in difflib.get_close_matches(norm(w).lower(), list(dict_n), n=1, cutoff=0.72)]
            if g: corect.append(g[0]); schimbat = True
            else: corect.append(w)
        if schimbat:
            fr = re.sub(r"\s+([,.])", r"\1", " ".join(corect))
            fr = re.sub(r"\b(\w+)( \1\b)+", r"\1", fr, flags=re.I)        # fără cuvinte repetate
            out.append(fr)
        # cablu nou fără porturi: propune forma completă
        if re.search(r"cablu", t.lower()) and noduri:
            try: men2 = [x[2] for x in porturi.mentiuni(S, t.lower()) if x[3] is not None]
            except Exception: men2 = []
            if len(men2) >= 2: out.insert(0, f"cablu nou 12FO de la {men2[0]} la {men2[1]}")
            elif len(men2) == 1: out += [f"cablu nou 12FO de la {men2[0]} la {b}" for b in noduri if b != men2[0]][:3]
        # 3) comanda de fibră incompletă: completează cu nodurile existente
        nr = re.findall(r"\d+", re.sub(r"(?i)(?:fo\s*-?\s*\d+)|(?:\d+\s*(?:fo|fibre|fib)\b)|\d+(?:[.,]\d+)?\s*(?:m|km)\b", " ", t))
        if noduri and nr and not re.search(r"cablu", t.lower()):
            try: men = [x[2] for x in porturi.mentiuni(S, t.lower()) if x[3] is not None]
            except Exception: men = []
            a = men[0] if men else None
            for b in noduri:
                if len(out) >= 4: break
                if a and b == a: continue
                pa, pb = nr[0], (nr[1] if len(nr) > 1 else nr[0])
                out.append(f"{a or noduri[0]} port {pa} la {b if a else (noduri[1] if len(noduri) > 1 else b)} port {pb}")
                if not a: break
        # 0) ai pomenit o clădire / un ODF / un manșon: poate vrei să-l desenez
        import dictionar
        for o in dictionar.scor_intentii(t):
            out.insert(0, {"cladire": "adauga cladire noua", "odf": "adauga odf nou", "manson": "adauga manson nou"}[o])
        # 4) nimic: exemple cu numele reale + asistentul care te ghidează
        if not out or len(out) < 2:
            out += ["ghideaza-ma (asistent)"]
        if not out:
            if len(noduri) >= 2: out += [f"{noduri[0]} port 1 la {noduri[1]} port 1", "porturi", "ajutor"]
            else:
                el = [x.split("\n")[0] for x, _ in S.elemente()][:2]
                out += ([f"adauga manson M9 langa {el[0]}", f"adauga cablu 12FO de la {el[0]} la {el[1] if len(el) > 1 else 'S9'}, 50 m"] if el else []) + ["lista", "ajutor"]
        vaz = []; 
        for x in out:
            if x and x.strip().lower() != t.lower() and x not in vaz: vaz.append(x)
        return vaz[:5]

    def gaseste(self, nume):
        f = self.schema.gaseste(curat(nume))
        if f is None: raise ValueError(f"nu găsesc „{curat(nume)}” pe pagina {self.doc.pagini[self.ip].nume}")
        return f

    def executa(self, orig, t):
        S = self.schema
        import porturi
        r = porturi.comanda(S, t)                       # fibre de la un port la altul (CTA / ODF / BTS cu bandă galbenă)
        if r is not None: return r, not r.startswith(("Benzi", "Nu găsesc"))
        # --- cablu nou ---
        m = re.match(r"(?:adauga|pune|deseneaza|trage|fa) (?:un |o )?cablu(?:l)?\s*(.*?)\s*de la " + NUME + r" (?:la|pana la|spre) " + NUME + r"(.*)$", t)
        if m:
            tipc, a, b, rest = m.group(1), curat(m.group(2)), curat(m.group(3)), m.group(4)
            tipc = (tipc + " " + rest)
            mf = re.search(r"(\d+)\s*(?:fo|f\.o\.|fibre|fib)\b", tipc); ml = re.search(r"(\d+(?:[.,]\d+)?)\s*(m|km)\b", tipc)
            fo = f"{mf.group(1)}FO" if mf else ""; L = ""
            if ml: L = ml.group(1).replace(",", ".") + " " + ml.group(2)
            A = S.gaseste(a); creat = []
            if A is None:
                A = S.adauga_element(self.nume_orig(orig, a)); creat.append(self.nume_orig(orig, a))
            B = S.gaseste(b)
            if B is None:
                B = S.adauga_element(self.nume_orig(orig, b), ancora=A); creat.append(self.nume_orig(orig, b))
            if S.cablu_intre(A, B) is not None and not re.search(r"\b(inca|al doilea|alt)\b", t):
                raise ValueError(f"între {a.upper()} și {b.upper()} există deja un cablu (scrie „încă un cablu” dacă vrei al doilea)")
            et = " ".join(x for x in (fo, L) if x)
            from desen import STIL_CABLU_NOU
            st = dict(STIL_CABLU_NOU)
            if re.search(r"\b(intrerupt|punctat|linie intrerupta|dashed)\b", tipc): st["intrerupt"] = True
            if re.search(r"\brosu\b", tipc): st["culoare"] = "#FF0000"
            S.adauga_cablu(A, B, et, st)
            msg = f"Am desenat cablul {et or ''} de la {A.text_tot().split(chr(10))[0]} la {B.text_tot().split(chr(10))[0]}."
            if creat: msg += " Am adăugat și: " + ", ".join(creat) + " (" + ", ".join(TIPURI[tip_din_nume(c)][4] for c in creat) + ")."
            return msg.replace("  ", " "), True
        # --- element nou ---
        m = re.match(r"(?:adauga|pune|deseneaza|fa) (?:un |o )?(\w+) " + NUME + r"(.*)$", t)
        if m and (m.group(1) in CUVINTE_TIP):
            tip = CUVINTE_TIP[m.group(1)]; nume = self.nume_orig(orig, curat(m.group(2))); rest = m.group(3)
            if S.gaseste(nume) is not None: raise ValueError(f"{nume} există deja pe pagină")
            det = ""
            mr = re.search(r"\b(1\s*[:x/]\s*\d+)\b", rest)
            if mr and tip == "splitter": det = mr.group(1).replace(" ", "").replace("x", ":").replace("/", ":")
            mp = re.search(r"(\d+)\s*porturi", rest)
            if mp and tip == "odf": det = f"{mp.group(1)} porturi"
            anc, dirc = None, None
            mm = re.search(r"(?:la )?(dreapta|stanga|sus|jos|deasupra|dedesubt|sub)(?: de| lui)? " + NUME, rest)
            if mm: dirc = DIRECTII[mm.group(1)]; anc = self.gaseste(mm.group(2))
            else:
                mm = re.search(r"(?:langa|linga|de|dupa|la) " + NUME, rest)
                if mm: anc = self.gaseste(mm.group(1))
            f = S.adauga_element(nume, tip, ancora=anc, directie=dirc, detalii=det)
            unde = (f" {({'sus': 'deasupra lui', 'jos': 'sub', 'dreapta': 'la dreapta de', 'stanga': 'la stânga de'}.get(dirc, 'lângă'))} {anc.text_tot().split(chr(10))[0]}") if anc else ""
            return f"Am adăugat {TIPURI[tip][4] if tip == 'odf' else TIPURI[tip][4].lower()} {nume}{(' ' + det) if det else ''}{unde}.", True
        # --- lungime / tip cablu ---
        m = re.match(r"(?:schimba|modifica|pune|seteaza) (lungimea|tipul|cablul)(?: cablului)? (?:de la |dintre )?" + NUME + r" (?:la|si|-) " + NUME + r" (?:in|la|=) (.+)$", t)
        if m:
            A, B = self.gaseste(m.group(2)), self.gaseste(m.group(3)); c = S.cablu_intre(A, B)
            if c is None: raise ValueError(f"nu găsesc cablu între {m.group(2).upper()} și {m.group(3).upper()}")
            val = m.group(4).strip(); vechi = c.text or ""
            ml = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(m|km)?", val); mf = re.fullmatch(r"(\d+)\s*(?:fo|fibre)", val)
            if ml:
                L = ml.group(1).replace(",", ".") + " " + (ml.group(2) or "m")
                nou = re.sub(r"\d+(?:[.,]\d+)?\s*(m|km)\b", L, vechi, flags=re.I) if re.search(r"\d+(?:[.,]\d+)?\s*(m|km)\b", vechi, re.I) else (vechi + " " + L).strip()
            elif mf:
                nou = RE_CABLU.sub(f"{mf.group(1)}FO", vechi) if RE_CABLU.search(vechi) else (f"{mf.group(1)}FO " + vechi).strip()
            else: nou = self.text_orig(orig, val)
            S.eticheta_cablu(c, nou)
            return f"Cablul {A.text_tot().split(chr(10))[0]}–{B.text_tot().split(chr(10))[0]}: „{vechi.strip()}” → „{nou}”.", True
        # --- ștergere ---
        m = re.match(r"(?:sterge|elimina|scoate) cablul (?:de la |dintre )?" + NUME + r" (?:la|si|-) " + NUME + "$", t)
        if m:
            A, B = self.gaseste(m.group(1)), self.gaseste(m.group(2)); c = S.cablu_intre(A, B)
            if c is None: raise ValueError(f"nu găsesc cablu între {m.group(1).upper()} și {m.group(2).upper()}")
            S.sterge(c); return f"Am șters cablul dintre {m.group(1).upper()} și {m.group(2).upper()}.", True
        m = re.match(r"(?:sterge|elimina|scoate) (?:\w+ )?" + NUME + "$", t)
        if m:
            f = self.gaseste(m.group(1)); cab = [c for c, a, b in S.cabluri() if f.id in (a, b)]
            for c in cab: S.sterge(c)
            S.sterge(f)
            return f"Am șters {m.group(1).upper()}" + (f" și {len(cab)} cabluri legate de el." if cab else "."), True
        # --- mutare ---
        m = re.match(r"(?:muta|deplaseaza) " + NUME + r" (?:mai )?(?:la |in )?(dreapta|stanga|sus|jos)(?: cu (\d+(?:[.,]\d+)?)\s*(cm|mm|m)?)?$", t)
        if m:
            f = self.gaseste(m.group(1)); d = float((m.group(3) or "2").replace(",", ".")); u = m.group(4) or "cm"
            inch = d / 2.54 if u == "cm" else d / 25.4 if u == "mm" else d * 100 / 2.54
            dx, dy = {"dreapta": (inch, 0), "stanga": (-inch, 0), "sus": (0, inch), "jos": (0, -inch)}[m.group(2)]
            S.muta(f, dx, dy); return f"Am mutat {m.group(1).upper()} la {m.group(2)} cu {d:g} {u}.", True
        m = re.match(r"(?:muta|deplaseaza) " + NUME + r" (?:langa|linga|la) " + NUME + "$", t)
        if m:
            f, g = self.gaseste(m.group(1)), self.gaseste(m.group(2))
            x0, y0, x1, y1 = f.cutie(); x, y = S.loc_langa(g, x1 - x0, y1 - y0)
            cx, cy = f.centru(); S.muta(f, x - cx, y - cy)
            return f"Am mutat {m.group(1).upper()} lângă {m.group(2).upper()}.", True
        # --- redenumire ---
        m = re.match(r"(?:redenumeste|schimba numele lui|schimba numele) " + NUME + r" (?:in|cu) " + NUME + "$", t)
        if m:
            f = self.gaseste(m.group(1)); nou = self.nume_orig(orig, curat(m.group(2)))
            S.redenumeste(f, nou); return f"Am redenumit {m.group(1).upper()} în {nou}.", True
        # --- sudură ---
        m = re.match(r"(?:in|la) " + NUME + r",? (?:sudeaza|sudez|leaga) (?:fibrele |fibra )?([\d,\-– ]+(?:si [\d\-]+)?) (?:din|de la) (?:cablul )?" + NUME +
                     r" cu (?:fibrele |fibra )?([\d,\-– ]+(?:si [\d\-]+)?) (?:din|de la) (?:cablul )?" + NUME + "$", t)
        if not m:
            m2 = re.match(r"(?:sudeaza|sudez|leaga) (?:in|la) " + NUME + r",? (?:fibrele |fibra )?([\d,\-– ]+) (?:din|de la) (?:cablul )?" + NUME +
                          r" cu (?:fibrele |fibra )?([\d,\-– ]+) (?:din|de la) (?:cablul )?" + NUME + "$", t)
            m = m2
        if m:
            mans = self.gaseste(m.group(1)).text_tot().split("\n")[0]
            fa, fb = interval(m.group(2)), interval(m.group(4))
            if len(fa) != len(fb): raise ValueError(f"numărul de fibre diferă: {len(fa)} și {len(fb)}")
            a_n, b_n = m.group(3).upper(), m.group(5).upper()
            pg, n = pagina_sudura(self.doc, mans, f"Cablu {a_n}", fa, f"Cablu {b_n}", fb)
            self.ip = self.doc.pagini.index(pg)
            return f"Am desenat sudura în {mans}: {n} fibre ({a_n} {m.group(2).strip()} ↔ {b_n} {m.group(4).strip()}), pe pagina „{pg.nume}”.", True
        return None

    def nume_orig(self, orig, nume_mic):
        """numele așa cum l-a scris omul (literele mari), nu varianta fără diacritice/litere mici"""
        o = fara_diacritice(orig)
        i = o.lower().find(nume_mic.lower())
        r = orig[i:i + len(nume_mic)] if i >= 0 else nume_mic
        return r.upper() if re.fullmatch(r"[a-z]+-?\d+\w*", r) else r

    def text_orig(self, orig, val):
        o = fara_diacritice(orig).lower(); i = o.rfind(val.lower())
        return orig[i:i + len(val)] if i >= 0 else val

    def lista(self):
        S = self.schema; el = S.elemente(); cab = S.cabluri()
        if not el: return f"Pagina „{self.doc.pagini[self.ip].nume}” nu are elemente cu nume."
        linii = [f"Pagina „{self.doc.pagini[self.ip].nume}”: {len(el)} elemente, {len(cab)} linii/cabluri."]
        linii.append("Elemente: " + ", ".join(t.split("\n")[0] for t, _ in el[:80]) + (" …" if len(el) > 80 else ""))
        return "\n".join(linii)

    def lista_cabluri(self):
        S = self.schema; out = []
        for c, a, b in S.cabluri():
            A, B = S.forma_id(a) if a else None, S.forma_id(b) if b else None
            na = A.text_tot().split("\n")[0] if A else "?"; nb = B.text_tot().split("\n")[0] if B else "?"
            out.append(f"{na} – {nb}: {(c.text or '').strip() or '(fără text)'}")
        return "Cabluri:\n" + "\n".join(out[:100]) if out else "Nu găsesc cabluri pe pagină."
