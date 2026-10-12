# Budget de Prilly en données ouvertes

Les budgets et les comptes de la Ville de Prilly, ligne par ligne, extraits des documents officiels de la commune et rendus lisibles : un tableau de bord interactif et des fichiers CSV réutilisables.

**Couverture actuelle** : comptes 2015 à 2025, budgets votés 2016 à 2025, projets de budget de la Municipalité 2023 à 2025, soit 2'121 lignes du budget de fonctionnement dans 8 directions.

> Projet indépendant, sans lien avec l'administration communale. Les chiffres proviennent des documents publiés par la Ville de Prilly ; en cas de doute, le document officiel fait foi.

## Pourquoi

La commune publie ses budgets et ses comptes en PDF sur [sa page Budgets & Comptes](https://www.prilly.ch/ville-administration/finances-impots/budgets-comptes). Ce projet transforme ces documents en données structurées pour chercher une ligne, suivre son évolution, comparer le budget voté à ce qui a été réellement dépensé et voir ce que le Conseil communal a modifié dans le projet de la Municipalité.

## Principe de neutralité

L'outil décrit ce que montrent les chiffres. Il ne dit pas ce qu'il faudrait en conclure, ce qui relève d'un choix politique. Les textes du tableau de bord s'en tiennent aux montants, aux écarts et aux méthodes de calcul. Toute contribution doit respecter ce principe.

## Contenu

| Dossier | Contenu |
|---|---|
| `site/index.html` | Tableau de bord autonome, à ouvrir dans un navigateur (aussi publié via GitHub Pages) |
| `data/` | Données ouvertes au format CSV (UTF-8, séparateur virgule) |
| `pipeline/` | Scripts d'extraction et de fusion (Python, bibliothèque standard ; `pdftotext` pour lire les PDF) |
| `sources/` | Liste des documents, extractions brutes de chaque document et résultat de la reconnaissance de caractères |
| `tests/` | Contrôles automatiques de cohérence |
| `docs/` | Méthodologie, ajout d'un document, mode d'emploi de l'assistant |
| `assistant/` | Outils pour interroger les données avec votre propre IA (serveur MCP et script) |

### Fichiers de données

| Fichier | Une ligne par | Colonnes principales |
|---|---|---|
| `lignes_large.csv` | ligne budgétaire (service et compte) | direction, groupe, service, compte, nature, sens (charge ou revenu), libellé original et lisible, puis une colonne par série |
| `lignes.csv` | ligne et série | même contenu en format long : série, type, année, montant |
| `sections.csv` | service | nom, groupe, direction |
| `natures.csv` | nature comptable | nom |
| `resultats.csv` | série | charges, revenus, résultat, document source |
| `amendements.csv` | ligne modifiée | année, projet de la Municipalité, budget voté, différence |
| `commentaires.csv` | commentaire | texte des explications données par la commune pour une ligne |
| `correspondance_numerotation.csv` | ancien compte | lien entre l'ancienne numérotation (jusqu'en 2018) et la nouvelle, avec la méthode utilisée |
| `controles.csv` | contrôle | plus de 3'000 contrôles contre les totaux officiels de chaque document |

Séries : `C2025` = comptes 2025 (réalisé), `B2025` = budget 2025 voté par le Conseil communal, `P2025` = projet de budget 2025 de la Municipalité. Les montants sont en francs, sans arrondi, positifs pour les charges comme pour les revenus (la colonne `sens` indique lequel). Les codes suivent le plan comptable des communes vaudoises : comptes 3xxx pour les charges, 4xxx pour les revenus ; les deux premiers chiffres donnent la nature (30 personnel, 35 participations à des collectivités publiques, 40 impôts, etc.).

## Le tableau de bord

**Comprendre**
- **Accueil** : chiffres clés, « sur 100 francs dépensés », d'où viennent les revenus, questions fréquentes avec leur réponse chiffrée
- **Explorer** : carte proportionnelle, de la direction jusqu'à la ligne
- **Rechercher** : toutes les lignes, avec des mots courants (école, piscine, déchets, accueil de jour…) et dans les commentaires de la commune
- **Comment lire** : projet, budget voté et comptes ; sources ; limites ; glossaire

**Approfondir**
- **Vue d'ensemble** : charges, revenus et résultat de chaque série ; coût net par direction ; charges par nature
- **Évolutions** : plus fortes hausses et baisses entre deux années, avec un badge qui indique le type de comparaison
- **Budget et comptes** : écarts entre prévision et réalisation, avec les explications de la commune
- **Amendements** : ce que le Conseil communal a modifié dans le projet de la Municipalité
- **Fiche service** : un service sur toutes les années, ligne par ligne

## Interroger le budget avec votre IA

Téléchargez le projet et branchez l'IA de votre choix : Claude Desktop, Claude Code ou toute application compatible MCP via `assistant/mcp_server.py`, ou n'importe quel modèle compatible OpenAI (local avec Ollama, ou en ligne) via `assistant/ask.py`. L'IA répond uniquement à partir des données de `data/`, cite les lignes utilisées et suit des consignes de neutralité. Mode d'emploi : [docs/assistant.md](docs/assistant.md).

## Reconstruire les données

Prérequis : Python 3.9 ou plus récent.

```sh
make rebuild   # depuis les extractions déjà présentes dans sources/extraits/
make all       # depuis les PDF placés dans sources/pdf/ (nécessite pdftotext)
make test      # contrôles uniquement
```

Pour ajouter un document (nouveau budget, nouveaux comptes), voir [docs/ajouter-un-document.md](docs/ajouter-un-document.md).

## Fiabilité

Chaque document est contrôlé contre ses propres totaux : total des charges et des revenus de chaque colonne, sous-totaux de chaque service, groupe et direction, totaux par nature. Toutes les séries retombent au centime près sur les totaux officiels, et les budgets votés correspondent aux récapitulatifs publiés par la commune (budgets 2016 à 2021, budgets amendés 2024 et 2025). Les comptes 2017 et 2021, publiés sous forme d'images, ont été lus par reconnaissance de caractères ; les quelques corrections manuelles sont listées dans `sources/corrections.csv`. Les choix de méthode et leurs limites sont décrits dans [docs/methodologie.md](docs/methodologie.md).

## Licence

Code sous licence MIT (voir `LICENSE`). Les données sont issues de documents publiés par la Ville de Prilly ; merci de citer la source : « Ville de Prilly, budgets et états financiers, mise en forme par le projet Budget de Prilly en données ouvertes ».
