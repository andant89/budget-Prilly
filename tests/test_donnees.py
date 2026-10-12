"""Contrôles de cohérence des données : chaque série retombe sur les totaux officiels."""
import csv
import json
import os
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(RACINE, "data")


def lire(nom):
    with open(os.path.join(DATA, nom), encoding="utf-8") as f:
        return list(csv.DictReader(f))


# Totaux officiels relevés dans les annexes 10 des documents (et des budgets amendés scannés)
OFFICIELS = {
    "C2015": (63793003.50, 63929502.36), "C2016": (62594855.86, 61545309.20), "C2017": (65398823.94, 63023528.19),
    "C2018": (64712317.80, 63823900.37), "C2019": (64658373.95, 65675021.15), "C2020": (67110899.21, 67791657.20),
    "B2016": (60121200.00, 59941700.00), "B2017": (63805200.00, 62556100.00), "B2018": (64746800.00, 63736900.00),
    "B2019": (61779140.00, 60272080.00), "B2020": (63628600.00, 61251200.00), "B2021": (66563700.00, 62978100.00),
    "C2021": (68486656.70, 68108660.31), "C2022": (79557204.59, 82608530.05), "C2023": (72470287.87, 74665237.87),
    "C2024": (75627608.36, 75925158.36), "C2025": (77906130.79, 82691935.79),
    "B2022": (71409550.55, 66055900.00), "B2023": (74295285.00, 69912759.00), "B2024": (79833180.12, 73529024.12),
    "B2025": (78218085.00, 73645085.00),
    "P2023": (74396915.00, 69912759.00), "P2024": (80125955.12, 73559024.12), "P2025": (78103085.00, 73645085.00),
}


class TestRapprochement(unittest.TestCase):
    def test_series_retombent_sur_les_totaux_officiels(self):
        lignes = lire("lignes_large.csv")
        for s, (ch, rv) in OFFICIELS.items():
            if s not in lignes[0]:
                continue
            c = sum(float(l[s]) for l in lignes if l[s] and l["sens"] == "charge")
            r = sum(float(l[s]) for l in lignes if l[s] and l["sens"] == "revenu")
            self.assertAlmostEqual(c, ch, delta=0.01, msg=f"{s} charges")
            self.assertAlmostEqual(r, rv, delta=0.01, msg=f"{s} revenus")

    def test_resultats_coherents(self):
        for r in lire("resultats.csv"):
            self.assertAlmostEqual(float(r["revenus"]) - float(r["charges"]), float(r["resultat"]), delta=0.01)

    def test_aucun_controle_bloquant_en_echec(self):
        ko = [c for c in lire("controles.csv") if c["ok"] != "oui" and c["bloquant"] == "oui"]
        self.assertEqual(ko, [], ko[:5])
        self.assertGreater(len(lire("controles.csv")), 1000)

    def test_amendements_expliquent_l_ecart_projet_vote(self):
        res = {r["serie"]: r for r in lire("resultats.csv")}
        am = lire("amendements.csv")
        for an in {a["annee"] for a in am}:
            d = sum(float(a["difference"]) * (1 if a["sens"] == "revenu" else -1) for a in am if a["annee"] == an)
            self.assertAlmostEqual(float(res["P" + an]["resultat"]) + d, float(res["B" + an]["resultat"]), delta=0.01)

    def test_correspondance_numerotation(self):
        m = lire("correspondance_numerotation.csv")
        self.assertGreater(sum(1 for x in m if x["methode"] == "montant 2018 identique"), 900)
        cibles = [(x["section"], x["compte"]) for x in m]
        self.assertEqual(len(cibles), len(set(cibles)), "deux anciens comptes reliés au même nouveau compte")

    def test_cles_uniques(self):
        cles = [(l["section"], l["compte"]) for l in lire("lignes_large.csv")]
        self.assertEqual(len(cles), len(set(cles)))

    def test_site_a_jour(self):
        d = json.load(open(os.path.join(RACINE, "site", "data.json"), encoding="utf-8"))
        self.assertEqual(len(d["lignes"]), len(lire("lignes_large.csv")))
        html = open(os.path.join(RACINE, "site", "index.html"), encoding="utf-8").read()
        self.assertNotIn("/*DATA*/null", html)


if __name__ == "__main__":
    unittest.main()
