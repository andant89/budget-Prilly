"""Passage de l'ancienne numérotation des comptes (jusqu'aux comptes 2018) à la nouvelle (dès 2019).

Ancienne : « 110.3011 », « 110.3170.01 » (section à 3 chiffres, nature à 4 chiffres, sous-compte).
Nouvelle : section « 1100 », compte « 3011.000 », « 3170.001 ».

1. Sous-totaux : dans l'ancienne présentation, certains comptes sont des regroupements de leurs
   sous-comptes (« 351.3121.0 EAU », ou « 110.3170 » quand il égale exactement la somme de ses
   sous-comptes). Ils sont retirés pour ne pas compter deux fois.
2. Correspondance : les comptes 2018 figurent dans les deux numérotations (comptes 2018, ancienne ;
   comptes 2019, colonne « Comptes 2018 », nouvelle). Une ligne est reliée quand le montant 2018 est
   identique dans le même service ; à défaut, quand le numéro converti existe avec un libellé proche.
   Sinon, la ligne garde son ancien numéro (préfixe « A ») et forme une série à part.
"""
import re
import unicodedata
from collections import defaultdict

ANCIEN = re.compile(r"^(\d{3})\.(\d{4})(?:\.(\d{1,3}))?$")
VIDES = {"de", "des", "du", "la", "le", "les", "et", "a", "au", "aux", "d", "l", "en", "pour", "sur"}


def ancien(code):
    return bool(ANCIEN.match(code))


def _v(r, j):
    x = r.get(f"v{j}", "")
    return float(x) if x not in ("", None) else 0.0


def sans_sous_totaux(comptes):
    """Retire les lignes qui ne sont que la somme de leurs sous-comptes (ancienne numérotation)."""
    par_base = defaultdict(list)
    autres = []
    for r in comptes:
        m = ANCIEN.match(r["code"])
        if m:
            par_base[(r["section"], m.group(1) + "." + m.group(2))].append((r, m.group(3)))
        else:
            autres.append(r)
    garde = []
    for _, g in par_base.items():
        g = [(r, s) for r, s in g if s != "0"]  # « X.0 » : en-tête de regroupement
        meres = [r for r, s in g if s is None]
        filles = [r for r, s in g if s is not None]
        if meres and filles and all(abs(sum(_v(r, j) for r in meres) - sum(_v(r, j) for r in filles)) < 0.01
                                    for j in range(6)):
            garde += filles
        else:
            garde += [r for r, _ in g]
    return autres + garde


def converti(code):
    """Numéro ancien converti mécaniquement : 110.3170.01 -> (1100, 3170.001)."""
    m = ANCIEN.match(code)
    sec, nat, sous = m.groups()
    return sec + "0", f"{nat}.{(sous or '0').zfill(3) if sous not in (None, '0') else '000'}"


def mots(lib):
    s = "".join(c for c in unicodedata.normalize("NFD", lib.lower()) if unicodedata.category(c) != "Mn")
    return {w for w in re.findall(r"[a-z0-9]+", s) if w not in VIDES and len(w) > 1}


def proche(a, b):
    x, y = mots(a), mots(b)
    return bool(x and y) and len(x & y) / len(x | y) >= 0.34


def correspondance(anciens, nouveaux, col_ancien, col_nouveau):
    """anciens / nouveaux : lignes de compte (après retrait des sous-totaux) des deux documents qui se recouvrent.
    col_* : indices (charges, revenus) de la série commune dans chaque document.
    Renvoie {(section ancienne, code ancien): (section nouvelle, compte nouveau, méthode)}."""
    nv = {}
    for r in nouveaux:
        nv[(r["section"], r["code"])] = (sum(_v(r, j) for j in col_nouveau), r["libelle"])
    pris = set()
    res = {}
    # 1. même montant 2018 dans le même service et du même sens (charge / revenu)
    for r in anciens:
        val = sum(_v(r, j) for j in col_ancien)
        if not val:
            continue
        sec4 = r["section"] + "0"
        cand = [k for k, (v, _) in nv.items() if k[0] == sec4 and k[1][0] == r["code"][4] and abs(v - val) < 0.005
                and k not in pris]
        if len(cand) > 1:
            conv = converti(r["code"])
            cand = [conv] if conv in cand else ([k for k in cand if k[1][:4] == r["code"][4:8]] or cand)
            if len(cand) > 1:
                cand = [k for k in cand if proche(nv[k][1], r["libelle"])] or cand
        if len(cand) == 1:
            res[(r["section"], r["code"])] = (*cand[0], "montant 2018 identique")
            pris.add(cand[0])
    return res, nv, pris


def completer(cle, libelle, res, nv, pris):
    """Lignes sans correspondance par montant : numéro converti si le libellé est proche, sinon ancien numéro."""
    if cle in res:
        return res[cle]
    sec, code = cle
    conv = converti(code)
    if conv in nv and conv not in pris and proche(nv[conv][1], libelle):
        pris.add(conv)
        res[cle] = (*conv, "numéro converti, libellé proche")
    else:
        m = ANCIEN.match(code)
        res[cle] = (sec + "0", f"{m.group(2)}.A{m.group(3) or '0'}", "ancien numéro conservé")
    return res[cle]
