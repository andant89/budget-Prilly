# Ajouter un document (nouveau budget ou nouveaux comptes)

1. Télécharger le PDF depuis la [page Budgets & Comptes de Prilly](https://www.prilly.ch/ville-administration/finances-impots/budgets-comptes) et le placer dans `sources/pdf/`, par exemple `budget-2026.pdf` ou `comptes-2026.pdf`. Prendre le fichier original (Enregistrer sous), pas une impression en PDF.
2. Ajouter une entrée dans `sources/documents.json` : identifiant, nom du fichier, type (`budget` ou `comptes`), année, titre, adresse, et les trois colonnes de l'annexe 12 dans l'ordre (`projet:2026`, `budget:2025`, `comptes:2024` pour un budget ; `comptes:2026`, `budget:2026`, `comptes:2025` pour des états financiers).
   Options : `"ocr": true` pour un document scanné (toutes les pages passent par la reconnaissance de caractères) ; `"planches": true` si le PDF contient deux pages côte à côte ; `"totaux_officiels"` pour indiquer à la main les totaux des charges et revenus de chaque colonne quand l'annexe 10 n'a pas le format habituel.
3. Lancer `make all`. L'extraction vérifie que les en-têtes de colonnes du document correspondent à ce qui est déclaré ; la fusion vérifie les totaux.
4. Lire le résumé affiché : aucun contrôle bloquant ne doit être en échec. Les écarts éventuels sont listés dans `data/controles.csv`.
5. Si une page est enregistrée sans texte, l'extraction utilise la reconnaissance de caractères (`tesseract` doit être installé) et garde le résultat dans `sources/ocr/`. Vérifier ces lignes contre le document.
6. Si la commune publie un budget amendé scanné, ajouter ses totaux dans `documents_de_controle` de `sources/documents.json`.
7. Committer le PDF n'est pas nécessaire (`sources/pdf/` est ignoré) ; committer `sources/documents.json`, `sources/extraits/`, `sources/ocr/`, `data/` et `site/`.
