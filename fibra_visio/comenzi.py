"""Chatul: înțelege comenzile scrise în română (cu sau fără diacritice) și le face pe schemă.
Fără internet: comenzile au forme fixe, cu multe variante. „ajutor” arată lista."""
import math, re
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


class Chat:
    def __init__(self, doc):
        self.doc = doc; self.ip = 0; self.istoric = []

    @property
    def schema(self): return Schema(self.doc, self.doc.pagini[self.ip])

    def raspunde(self, mesaj):
        """-> (răspuns, s-a schimbat desenul)"""
        t = fara_diacritice(mesaj.strip()).lower()
        t = re.sub(r"\s+", " ", t).rstrip(".!")
        if not t: return "", False
        if t in ("ajutor", "help", "?", "comenzi", "ce poti face"): return AJUTOR, False
        if re.fullmatch(r"(anuleaza|undo|inapoi)( tot)?", t):
            if not self.istoric: return "Nu am ce anula.", False
            self.doc.restaureaza(self.istoric.pop()); self.ip = min(self.ip, len(self.doc.pagini) - 1)
            return "Am anulat ultima modificare.", True
        if re.fullmatch(r"(lista|listă|elemente|ce (e|este) pe (pagina|schema)|arata tot)", t): return self.lista(), False
        if t in ("cabluri", "lista cabluri", "arata cablurile"): return self.lista_cabluri(), False
        if t in ("pagini", "lista pagini"):
            return "Pagini: " + ", ".join(f"{i + 1}. {p.nume}" + (" (deschisă)" if i == self.ip else "") for i, p in enumerate(self.doc.pagini)), False
        m = re.fullmatch(r"(?:deschide )?pagina (\d+)", t)
        if m:
            k = int(m.group(1)) - 1
            if not 0 <= k < len(self.doc.pagini): return f"Nu există pagina {k + 1}. Sunt {len(self.doc.pagini)}.", False
            self.ip = k; return f"Am deschis pagina {k + 1}: {self.doc.pagini[k].nume}.", True
        stare = self.doc.instantaneu()
        try:
            r = self.executa(mesaj, t)
        except Exception as e:
            self.doc.restaureaza(stare); return f"N-am reușit: {e}", True
        if r is None:
            return "Nu am înțeles comanda. Scrie „ajutor” ca să vezi exemple.", False
        if r[1]: self.istoric.append(stare); self.istoric = self.istoric[-50:]
        return r

    def gaseste(self, nume):
        f = self.schema.gaseste(curat(nume))
        if f is None: raise ValueError(f"nu găsesc „{curat(nume)}” pe pagina {self.doc.pagini[self.ip].nume}")
        return f

    def executa(self, orig, t):
        S = self.schema
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
