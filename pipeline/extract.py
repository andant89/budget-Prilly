#!/usr/bin/env python3
"""Extraction des brochures budgétaires et des états financiers de la Ville de Prilly.

Pour chaque document de sources/documents.json :
  - lit le texte et la position de chaque mot avec `pdftotext -bbox` (poppler-utils) ;
  - reconstitue les lignes de l'annexe 12 « détail par Direction » : direction, groupe,
    section (service) et compte, avec les six montants (charges et revenus de trois colonnes)
    et les commentaires de la Municipalité ;
  - lit les totaux officiels (annexe 10) et les noms des natures et des directions ;
  - pour les pages enregistrées sans texte (dessin), utilise la reconnaissance de caractères
    (tesseract) ; le résultat est conservé dans sources/ocr/ pour ne pas dépendre de tesseract
    lors des reconstructions suivantes.

Résultat : sources/extraits/<document>.csv et sources/extraits/<document>.json
Usage : python3 pipeline/extract.py [id_document ...]
"""
import csv
import html
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(RACINE, "sources")
NUM = re.compile(r"^-?\d{1,3}(?:['’]\d{3})*[.,]\d\d$")
CODE = re.compile(r"^\d{4}\.?\d{3}$")
PIED = re.compile(r"^(?:\d{1,3}|(?:\d+ )?Page \d+(?: \d+)?|\d{2}\.\d{2}\.\d{4}(?: \d+)?|\d+ P e\d+|P e\d+)$")
WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>')
PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)


def montant(t):
    return round(float(t.replace("'", "").replace("’", "").replace(",", ".")), 2)


def mots_pdf(chemin):
    """Liste des pages ; chaque page = (largeur, hauteur, [mots]) avec mot = dict x0,top,x1,bottom,text."""
    out = subprocess.run(["pdftotext", "-bbox", chemin, "-"], capture_output=True, text=True, check=True).stdout
    pages = []
    for w, h, corps in PAGE.findall(out):
        w, h = float(w), float(h)
        mots = [{"x0": float(a), "top": float(b), "x1": float(c), "bottom": float(d), "text": html.unescape(t)}
                for a, b, c, d, t in WORD.findall(corps)]
        mots = [m for m in mots if m["x0"] >= 0 and m["x1"] <= w + 1]  # ignore le contenu hors page (planches InDesign)
        pages.append((w, h, mots))
    return pages


def mots_ocr(chemin_pdf, doc_id, no_page, largeur):
    """Mots d'une page sans texte, par OCR (résultat mis en cache dans sources/ocr)."""
    cache = os.path.join(SRC, "ocr", f"{doc_id}-p{no_page}.tsv")
    if not os.path.exists(cache):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            img = os.path.join(tmp, "p")
            subprocess.run(["pdftoppm", "-r", "300", "-gray", "-png", "-f", str(no_page), "-l", str(no_page),
                            "-singlefile", chemin_pdf, img], check=True)
            subprocess.run(["tesseract", img + ".png", os.path.join(tmp, "o"), "--psm", "6", "tsv"],
                           check=True, capture_output=True)
            with open(os.path.join(tmp, "o.tsv"), encoding="utf-8") as f, open(cache, "w", encoding="utf-8") as g:
                g.write(f.read())
    echelle = 72 / 300
    mots = []
    with open(cache, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            t = (r.get("text") or "").strip()
            if not t or r["conf"] in ("-1",):
                continue
            x0, y0 = int(r["left"]) * echelle, int(r["top"]) * echelle
            mots.append({"x0": x0, "top": y0, "x1": x0 + int(r["width"]) * echelle,
                         "bottom": y0 + int(r["height"]) * echelle, "text": t})
    return mots


def lignes_de(mots, tol=2.5):
    """Regroupe les mots en lignes selon leur position verticale."""
    lignes = []
    for m in sorted(mots, key=lambda m: (m["top"], m["x0"])):
        if lignes and abs(lignes[-1][0] - m["top"]) <= tol:
            lignes[-1][1].append(m)
        else:
            lignes.append([m["top"], [m]])
    return [(t, sorted(ws, key=lambda w: w["x0"])) for t, ws in lignes]


def entetes(mots):
    """Repère la ligne d'en-tête « Charges Revenus » et renvoie (hauteur, [colonnes par moitié de page])."""
    h = [w for w in mots if w["text"] in ("Charges", "Revenus")]
    if len(h) < 6:
        return None, []
    ht = Counter(round(w["top"]) for w in h).most_common(1)[0][0]
    h = sorted([w for w in h if abs(round(w["top"]) - ht) <= 2], key=lambda w: w["x1"])
    return ht, [[w["x1"] for w in h[i:i + 6]] for i in range(0, len(h) - 5, 6)]


def libelles_colonnes(mots, ht, cols):
    """Libellés des trois colonnes (ex. « Budget 2025 ») au-dessus de l'en-tête."""
    au_dessus = [w for w in mots if ht - 30 < w["top"] < ht - 2]
    res = []
    for i in range(3):
        centre = (cols[2 * i] + cols[2 * i + 1]) / 2 - 25
        cand = [w for w in au_dessus if w["text"] in ("Budget", "Comptes")]
        if not cand:
            return None
        w = min(cand, key=lambda w: abs((w["x0"] + w["x1"]) / 2 - centre))
        an = [v for v in au_dessus if re.match(r"^20\d\d$", v["text"]) and 0 < v["x0"] - w["x1"] < 20]
        res.append(f"{w['text']} {an[0]['text'] if an else '?'}")
    return res


def extraire_detail(doc, chemin):
    pages = mots_pdf(chemin)
    marque = re.compile(r"par\s+Direction\s*-\s*d")
    detail = [i for i, (_, _, ms) in enumerate(pages)
              if marque.search(" ".join(w["text"] for w in ms[:40]))]
    if not detail:
        sys.exit(f"{doc['id']} : annexe 12 introuvable")
    premiere, derniere = detail[0], detail[-1]
    lignes_out = []
    libelles = None
    cols_ref = None
    for i in range(premiere, derniere + 1):
        w, hgt, mots = pages[i]
        source = "texte"
        if len(mots) < 5:  # page enregistrée sans texte
            mots = mots_ocr(chemin, doc["id"], i + 1, w)
            source = "ocr"
        ht, moities = entetes(mots)
        if not moities:
            if source == "ocr" and cols_ref:
                ht, moities = 0, cols_ref
            else:
                continue
        if source == "texte":
            cols_ref = None
        lab = libelles_colonnes(mots, ht, moities[0]) if source == "texte" else None
        if lab and libelles is None:
            libelles = lab
        bornes = [m[-1] + 30 for m in moities]

        def moitie(x):
            for k, b in enumerate(bornes):
                if x <= b:
                    return k
            return len(bornes) - 1

        for k, cols in enumerate(moities):
            ms = [m for m in mots if moitie(m["x1"]) == k and m["top"] > ht + 5]
            x_code = None
            for top, ws in lignes_de(ms, tol=2.5 if source == "texte" else 4):
                txt = " ".join(x["text"] for x in ws).strip()
                if PIED.match(txt):
                    continue
                premier = ws[0]["text"]
                def col(x):
                    return min(range(6), key=lambda j: abs(cols[j] - x["x1"]))
                nums = [x for x in ws if NUM.match(x["text"]) and abs(cols[col(x)] - x["x1"]) <= 30]
                hors = [x for x in ws if NUM.match(x["text"]) and x not in nums]
                if hors and re.match(r"^\d{1,4}(\.?\d{3})?$", premier) and x_code is not None \
                        and hors[0]["x0"] > cols[0] - 120:
                    sys.exit(f"{doc['id']} p.{i + 1} : montant hors colonne : {txt}")
                vals = [None] * 6
                for x in nums:
                    vals[col(x)] = montant(x["text"])
                libelle = " ".join(x["text"] for x in ws[1:] if x not in nums).strip()
                if CODE.match(premier) and not nums and (not libelle or not libelle.isupper()) and lignes_out \
                        and lignes_out[-1]["type"] == "compte":
                    lignes_out[-1]["commentaire"] = (lignes_out[-1]["commentaire"] + " " + txt).strip()
                    continue
                if CODE.match(premier):
                    c = premier.replace(".", "")
                    typ, code = "compte", c[:4] + "." + c[4:]
                    x_code = ws[0]["x0"]
                elif re.match(r"^\d{4}$", premier) and (nums or libelle.isupper()):
                    typ, code = "section", premier
                elif re.match(r"^\d{2}$", premier) and (nums or libelle.isupper()):
                    typ, code = "groupe", premier
                elif re.match(r"^\d$", premier) and libelle and (nums or libelle.isupper()):
                    typ, code = "direction", premier
                elif not nums and lignes_out:
                    der = lignes_out[-1]
                    if der["type"] in ("section", "groupe", "direction") and txt.isupper():
                        der["libelle"] = (der["libelle"] + " " + txt).strip()
                    elif der["type"] == "compte":
                        der["commentaire"] = (der["commentaire"] + " " + txt).strip()
                    continue
                else:
                    continue
                lignes_out.append({"document": doc["id"], "page": i + 1, "source": source, "type": typ,
                                   "code": code, "libelle": libelle, "commentaire": "",
                                   **{f"v{j}": ("" if v is None else f"{v:.2f}") for j, v in enumerate(vals)}})
        if source == "texte":
            cols_ref = moities
    return lignes_out, libelles


def extraire_annexes(chemin):
    """Totaux officiels (annexe 10), noms des natures et des directions (annexes 10 et 11)."""
    txt = subprocess.run(["pdftotext", "-layout", chemin, "-"], capture_output=True, text=True, check=True).stdout
    pages = txt.split("\f")
    nature = [p for p in pages if re.search(r"par\s+nature\s*-\s*condens", p)]
    res = {"totaux": {}, "natures": {}, "natures_montants": {}, "directions": {}}
    val = r"-?\d{1,3}(?:'\d{3})*\.\d\d"
    for p in nature:
        for ln in p.split("\n"):
            m = re.match(r"^\s*(Charges|Revenus)\s+(.*)$", ln)
            if m and m.group(1).lower() not in res["totaux"]:
                n = [montant(x) for x in re.findall(val, m.group(2))]
                if len(n) >= 7:
                    res["totaux"][m.group(1).lower()] = [abs(n[0]), abs(n[2]), abs(n[6])]
            m = re.match(r"^\s*(\d{2,3})\*?\s+([A-ZÀ-Ü][^0-9]*?)\s{2,}(.*)$", ln)
            if m:
                res["natures"].setdefault(m.group(1), m.group(2).strip())
                if len(m.group(1)) == 3:
                    n = [montant(x) for x in re.findall(val, m.group(3))]
                    if len(n) == 5:
                        res["natures_montants"][m.group(1)] = [n[0], n[1], n[4]]
    for p in pages:
        if re.search(r"par\s+Direction\s*-\s*(R[ée]sultat|condens)", p):
            for ln in p.split("\n"):
                m = re.match(r"^\s*([1-9])\s+([A-ZÉ][^\d|]*?)\s*\|?\s{2,}-?\d", ln)
                if m:
                    res["directions"].setdefault(m.group(1), m.group(2).strip())
    return res


CHAMPS = ["document", "page", "source", "type", "code", "libelle", "v0", "v1", "v2", "v3", "v4", "v5", "commentaire"]


def main():
    cfg = json.load(open(os.path.join(SRC, "documents.json"), encoding="utf-8"))
    choix = set(sys.argv[1:])
    os.makedirs(os.path.join(SRC, "extraits"), exist_ok=True)
    os.makedirs(os.path.join(SRC, "ocr"), exist_ok=True)
    for doc in cfg["documents"]:
        if choix and doc["id"] not in choix:
            continue
        chemin = os.path.join(SRC, "pdf", doc["fichier"])
        if not os.path.exists(chemin):
            print(f"{doc['id']} : PDF absent ({chemin}), extraction existante conservée")
            continue
        lignes, libelles = extraire_detail(doc, chemin)
        attendu = [("Budget " if c.split(":")[0] in ("projet", "budget") else "Comptes ") + c.split(":")[1]
                   for c in doc["colonnes"]]
        if libelles != attendu:
            sys.exit(f"{doc['id']} : colonnes {libelles}, attendu {attendu} (voir documents.json)")
        annexes = extraire_annexes(chemin)
        annexes["colonnes"] = doc["colonnes"]
        with open(os.path.join(SRC, "extraits", doc["id"] + ".csv"), "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=CHAMPS)
            wr.writeheader()
            wr.writerows(lignes)
        with open(os.path.join(SRC, "extraits", doc["id"] + ".json"), "w", encoding="utf-8") as f:
            json.dump(annexes, f, ensure_ascii=False, indent=1, sort_keys=True)
        n = Counter(l["type"] for l in lignes)
        ocr = sum(1 for l in lignes if l["source"] == "ocr")
        print(f"{doc['id']} : {n['compte']} comptes, {n['section']} sections, {n['groupe']} groupes, "
              f"{n['direction']} directions, {ocr} lignes par OCR ; totaux officiels {annexes['totaux']}")


if __name__ == "__main__":
    main()
