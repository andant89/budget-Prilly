# Méthodologie

## Documents utilisés

La liste des documents, leur adresse et la signification de leurs trois colonnes se trouvent dans `sources/documents.json`. Chaque document de la commune présente le budget de fonctionnement détaillé (annexe 12, « par Direction – détail ») avec trois colonnes de charges et de revenus :

| Document | Colonne 1 | Colonne 2 | Colonne 3 |
|---|---|---|---|
| Budget N (préavis de la Municipalité) | projet de budget N | budget voté N-1 | comptes N-2 |
| États financiers N | comptes N | budget voté N | comptes N-1 |

Jusqu'en 2021, les budgets publiés (« fascicules ») ne contiennent que des récapitulatifs par groupe de services et par nature. Le budget voté ligne par ligne de ces années vient donc des comptes de la même année (colonne « Budget »), et les totaux des fascicules servent de contrôle (`documents_de_controle`). Pour les documents anciens, dont la présentation des totaux varie, les totaux officiels sont relevés à la main dans `sources/documents.json` (`totaux_officiels`).

On en tire trois types de séries :

- **Comptes** (`C`) : pris dans les états financiers de l'année quand ils existent, sinon dans le budget publié deux ans plus tard.
- **Budget voté** (`B`) : pris dans le document suivant (budget N+1 ou états financiers N), qui reprend le budget tel qu'adopté par le Conseil communal. Quand une série figure dans plusieurs documents, les états financiers sont préférés, puis le document le plus récent ; toute différence entre deux sources est signalée dans `data/controles.csv`.
- **Projet** (`P`) : première colonne du budget publié par la Municipalité.

Le budget 2025 a connu deux versions. Le Conseil communal a amendé la première version le 9 décembre 2024 ; la Municipalité a ensuite présenté une **version 2** (préavis 02-2025), qui intègre ces amendements et d'autres ajustements, puis le Conseil a encore amendé cette version 2. La série `P2025` correspond à la version 2 ; la première version n'est pas reprise.

## Extraction

`pipeline/extract.py` lit la position de chaque mot avec `pdftotext -bbox` (poppler). Les montants sont rattachés à leur colonne d'après la position de l'en-tête « Charges / Revenus » de chaque page. Le budget 2024 est mis en page par planches (deux pages côte à côte) : seul le contenu visible de chaque page est retenu.

Les lignes sont classées en direction (1 chiffre), groupe (2 chiffres), service ou « section » (4 chiffres) et compte (`3011.000`). Les lignes de texte sans montant qui suivent un compte sont les commentaires de la commune. Une coquille du budget 2025 (compte `3909005` sans point) est corrigée automatiquement.

La page 36 des états financiers 2025 a été publiée sans texte (dessin vectoriel). Elle est lue par reconnaissance de caractères (tesseract) ; le résultat est conservé dans `sources/ocr/` et marqué `ocr` dans `sources/extraits/`. Ses 27 lignes ferment exactement les totaux officiels ; les commentaires de cette page peuvent contenir de petites fautes de lecture.

## Ancienne numérotation (jusqu'aux comptes 2018)

Jusqu'en 2018, les comptes sont numérotés « 110.3011 » (section à 3 chiffres, nature) avec des sous-comptes « 110.3170.01 ». Deux particularités sont traitées dans `pipeline/numerotation.py` :

- **Sous-totaux** : les lignes « X.0 » (par exemple « 351.3121.0 EAU ») sont des en-têtes de regroupement, et un compte dont le montant égale exactement, dans toutes les colonnes, la somme de ses sous-comptes est un sous-total. Ils sont retirés pour ne pas compter deux fois ; les totaux des services le confirment.
- **Correspondance** : les comptes 2018 figurent dans les deux numérotations (comptes 2018 et colonne « Comptes 2018 » des comptes 2019). Une ancienne ligne est reliée à la nouvelle quand le montant 2018 est identique dans le même service (957 lignes) ; à défaut, quand le numéro converti mécaniquement (110.3170.01 → 1100 / 3170.001) existe avec un libellé proche (32 lignes). Les autres (147 lignes, surtout des comptes supprimés en 2019) gardent leur ancien numéro, précédé de « A ». La table complète est dans `data/correspondance_numerotation.csv`.

Les sections passent de 3 à 4 chiffres en ajoutant un zéro (110 → 1100) ; les noms concordent.

## Documents scannés

Les comptes 2017 et 2021 sont publiés sous forme d'images. Toutes leurs pages sont lues par reconnaissance de caractères (tesseract, 300 dpi) ; le résultat brut est conservé dans `sources/ocr/`. L'extraction corrige automatiquement les confusions courantes (« § » ou « $ » pour 5, « ° » ou « ’ » pour l'apostrophe, « : » ou « / » pour le point décimal, montants coupés en deux) et déduit la position des colonnes de celle des montants quand l'en-tête n'est pas lisible.

Les erreurs restantes ont été repérées grâce aux contrôles (sous-totaux de chaque service) et à la comparaison avec les mêmes comptes publiés en texte dans un autre document ; elles sont corrigées dans `sources/corrections.csv`, avec pour chacune la raison et la vérification faite sur l'image. Quand une série existe à la fois dans un document scanné et dans un document texte, c'est le document texte qui fait foi.

## Contrôles

`pipeline/merge.py` vérifie, pour chaque document et chaque colonne :

1. le total des charges et des revenus contre l'annexe 10 (bloquant) ;
2. les sous-totaux de chaque service, groupe et direction contre la somme de leurs lignes (bloquant) ;
3. les totaux par nature à trois chiffres de l'annexe 10 (non bloquant) ;
4. les totaux des budgets votés 2024 et 2025 contre les documents amendés scannés publiés par la commune (bloquant).

Au dernier passage, aucun contrôle bloquant n'est en échec. Quelques incohérences des documents eux-mêmes sont signalées comme « écarts connus » (`pipeline/config.json`) : le total des revenus 2017 (63'023'528.17 dans les comptes 2018, alors que le détail et le budget 2019 donnent 63'023'528.19), le total de la direction Services industriels dans les comptes 2017 (qui oublie le téléréseau), et la nature 319 des comptes 2024 (105.75 francs d'écart entre l'annexe 10 et le détail des états financiers 2025). Les amendes fiscales (compte 4001.020) sont classées par la commune sous la nature 437 « Amendes » et non sous les impôts ; ce reclassement est repris (`pipeline/config.json`).

## Amendements

`data/amendements.csv` compare, ligne par ligne, le projet de la Municipalité et le budget voté de la même année. La somme des différences explique exactement l'écart entre les résultats du projet et du budget voté (contrôlé par les tests). Pour 2025, les deux lignes modifiées correspondent au document amendé scanné.

## Libellés

Les documents écrivent les libellés en majuscules sans accents. Les fichiers de données gardent le libellé original (`libelle`) et ajoutent une version lisible (`libelle_lisible`), en minuscules avec les accents rétablis pour les mots courants (`pipeline/libelles.py`). Les initiales des élu·e·s responsables, qui suivent le nom de chaque service dans les documents (« – MAA »), ne sont pas reprises.

## Limites

- Les **projets de budget** de la Municipalité ne sont disponibles ligne par ligne que depuis 2023 ; pour 2016 à 2019, les budgets amendés listent les amendements votés, qui ne sont pas encore repris.
- Seul le **budget de fonctionnement** est repris. Les investissements, le bilan, la dette et les comptes de la STEP et du SDIS, présents dans les états financiers, ne le sont pas encore.
- Les **imputations internes** (natures 39 et 49) sont des facturations entre services ; elles s'annulent dans le résultat. Les totaux officiels les incluent ; plusieurs vues du tableau de bord les excluent et l'indiquent.
- Les **attributions et prélèvements aux fonds** (natures 38 et 48) sont des écritures comptables qui peuvent faire varier fortement une ligne d'une année à l'autre.
- Les services sont parfois **réorganisés** : un compte peut changer de numéro ou de service. Une ligne est identifiée par son service et son compte ; un changement de service crée une nouvelle ligne.
- Les montants sont en **francs courants**, non corrigés de l'inflation ni de l'évolution de la population.
