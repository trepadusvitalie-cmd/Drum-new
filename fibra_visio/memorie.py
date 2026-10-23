"""Memoria chatului (pe calculator, fără internet): ține minte discuțiile, învață din ele și își amintește alegerile tale.
Fișierul: %APPDATA%/FibraVisio/memorie.json (doar pe calculatorul tău).

Ce învață din discuțiile de dinainte:
• expresii: ai scris ceva ce n-am înțeles, apoi ai ales / ai scris varianta bună -> data viitoare înțeleg direct;
• cuvinte: dacă diferă un singur cuvânt între ce n-am înțeles și ce a mers, țin minte cuvântul tău;
• preferințe: câte porturi, cum stă banda, de la ce nod, prin ce manșon – le propun primele;
• ultimul lucru desenat: „lângă el”, „încă unul”, „la fel” se referă la el."""
import difflib, json, os, re, threading, time
import dictionar

LIMITA = 3000                     # câte replici păstrez
_lacat = threading.Lock()


def fisier():
    d = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "FibraVisio")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "memorie.json")


def _cheie(t):
    return " ".join(dictionar.fd(t).replace(",", " ").split())


class Memorie:
    def __init__(self, cale=None):
        self.cale = cale or fisier()
        self.d = {"discutii": [], "expresii": {}, "cuvinte": {}, "preferinte": {}, "ultimul": None}
        try:
            with open(self.cale, encoding="utf-8") as f: self.d.update(json.load(f))
        except Exception: pass
        self.invata_din_istoric()

    # ---------------------------------------------------------------- salvare
    def salveaza(self):
        with _lacat:
            self.d["discutii"] = self.d["discutii"][-LIMITA:]
            tmp = self.cale + ".tmp"
            try:
                with open(tmp, "w", encoding="utf-8") as f: json.dump(self.d, f, ensure_ascii=False)
                os.replace(tmp, self.cale)
            except Exception: pass

    # ---------------------------------------------------------------- discuția
    def noteaza(self, eu, raspuns, inteles, schema=""):
        """o replică: ce ai scris, ce am răspuns, dacă am înțeles"""
        self.d["discutii"].append({"t": time.strftime("%Y-%m-%d %H:%M"), "eu": eu, "prog": raspuns[:300], "ok": bool(inteles), "schema": schema})
        if inteles: self._invata_ultimele()
        self.salveaza()

    def _invata_ultimele(self):
        """ultima replică a mers; dacă cea de dinainte (sau cu 2 înainte) n-a mers, o leg de asta"""
        dl = self.d["discutii"]
        bun = dl[-1]
        for prev in dl[-3:-1][::-1]:
            if prev["ok"]: break
            self._leaga(prev["eu"], bun["eu"])
            break

    def _leaga(self, gresit, bun):
        g, b = _cheie(gresit), _cheie(bun)
        if not g or g == b or re.fullmatch(r"\d+", b) or re.fullmatch(r"\d+", g): return
        if len(g) > 120: return
        self.d["expresii"][g] = bun
        # un singur cuvânt diferit -> cuvântul tău înseamnă cuvântul bun
        gw, bw = g.split(), b.split()
        ops = [o for o in difflib.SequenceMatcher(None, gw, bw).get_opcodes() if o[0] != "equal"]
        if len(ops) == 1 and ops[0][0] == "replace" and ops[0][2] - ops[0][1] == 1 and ops[0][4] - ops[0][3] == 1:
            w, c = gw[ops[0][1]], bw[ops[0][3]]
            if len(w) >= 3 and not re.search(r"\d", w): self.d["cuvinte"][w] = c
        dictionar.INVATATE.update(self.d["cuvinte"])

    def invata_din_istoric(self):
        """la pornire: recitesc toate discuțiile de dinainte și reînvăț din ele"""
        dl = self.d["discutii"]
        for i in range(1, len(dl)):
            if dl[i]["ok"] and not dl[i - 1]["ok"]: self._leaga(dl[i - 1]["eu"], dl[i]["eu"])
            elif dl[i]["ok"] and i >= 2 and not dl[i - 1]["ok"] and not dl[i - 2]["ok"]: self._leaga(dl[i - 2]["eu"], dl[i]["eu"])
        dictionar.INVATATE.update(self.d["cuvinte"])

    def traduce(self, t):
        """dacă ai mai spus la fel (sau aproape la fel) și am aflat ce înseamnă -> comanda învățată"""
        k = _cheie(t); ex = self.d["expresii"]
        if k in ex: return ex[k]
        g = difflib.get_close_matches(k, list(ex), n=1, cutoff=0.88)
        return ex[g[0]] if g else None

    # ---------------------------------------------------------------- preferințe
    def alege(self, slot, valoare):
        p = self.d["preferinte"].setdefault(slot, {}); v = str(valoare); p[v] = p.get(v, 0) + 1
        self.salveaza()

    def preferate(self, slot, n=3):
        p = self.d["preferinte"].get(slot, {})
        return [k for k, _ in sorted(p.items(), key=lambda kv: -kv[1])][:n]

    def ordoneaza(self, slot, optiuni, cheie=lambda o: o):
        """opțiunile alese des de tine vin primele"""
        pr = self.preferate(slot, 10)
        return sorted(optiuni, key=lambda o: (pr.index(str(cheie(o))) if str(cheie(o)) in pr else 99))

    def ultimul(self, nume=None, tip=None, pagina=None):
        if nume is None: return self.d.get("ultimul")
        self.d["ultimul"] = {"nume": nume, "tip": tip, "pagina": pagina}; self.salveaza()

    # ---------------------------------------------------------------- „ce ai învățat”, „ce am vorbit”
    def rezumat(self):
        dl = self.d["discutii"]; ok = sum(1 for x in dl if x["ok"])
        r = [f"Țin minte {len(dl)} replici ({ok} înțelese, {len(dl) - ok} neînțelese)."]
        if self.d["expresii"]:
            r.append("Expresii învățate de la tine:")
            r += [f"  • „{k}” → {v}" for k, v in list(self.d["expresii"].items())[-8:]]
        if self.d["cuvinte"]:
            r.append("Cuvinte: " + ", ".join(f"{k} = {v}" for k, v in list(self.d["cuvinte"].items())[-12:]))
        for s, nume in (("porturi", "porturi"), ("orient", "banda"), ("sursa", "sursa"), ("fibre", "fibre")):
            p = self.preferate(s, 2)
            if p: r.append(f"De obicei alegi {nume}: {', '.join(p)}")
        u = self.ultimul()
        if u: r.append(f"Ultimul desenat: {u['nume']}")
        return "\n".join(r)

    def ultimele(self, n=10):
        dl = self.d["discutii"][-n:]
        if not dl: return "Încă n-am vorbit nimic."
        return "Ultimele discuții:\n" + "\n".join(f"  {x['t'][5:]}  tu: {x['eu'][:60]}" + ("" if x["ok"] else "   (n-am înțeles)") for x in dl)

    def uita(self):
        self.d = {"discutii": [], "expresii": {}, "cuvinte": {}, "preferinte": {}, "ultimul": None}; dictionar.INVATATE.clear(); self.salveaza()
