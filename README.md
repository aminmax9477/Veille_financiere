# Veille financiere

Collecte automatisee de donnees financieres et macroeconomiques a partir de
sources publiques, avec **controle qualite et reconciliation entre sources**.

Le parti pris du projet : collecter beaucoup de donnees ne sert a rien si on
ne sait pas lesquelles sont fiables. Chaque serie est donc recoupee entre
plusieurs fournisseurs quand c'est possible, et chaque valeur est accompagnee
d'un verdict explicite (fraicheur, continuite, valeurs aberrantes, accord
entre sources).

## Installation

```bash
pip install -e .            # ou simplement : pip install requests
cp .env.example .env        # puis renseigner FRED_API_KEY
```

Deux cles sont utilisees : **FRED**
([gratuite](https://fredaccount.stlouisfed.org/apikeys)) et **London
Strategic Edge** ([londonstrategicedge.com/data](https://londonstrategicedge.com/data)).
Chacune est facultative — la collecte se rabat sur les autres sources et
signale ce qui manque — mais LSE est la seule a couvrir le CAC 40, l'Euro
Stoxx 50 en quotidien et l'or. Toutes les autres sources sont ouvertes. Renseigner `VF_SEC_CONTACT` est recommande :
la SEC exige un contact identifiable dans le `User-Agent`.

## Utilisation

```bash
veille doctor                          # verifier la config et joindre les sources
veille agenda --days 2                 # agenda macro seul, sans collecter les series
veille catalogue                       # lister les series suivies
veille collect                         # collecte + rapport console
veille collect -f markdown -o veille.md
veille collect -f json -o veille.json
veille collect --source fred --source ecb          # limiter aux sources voulues
veille collect --series fx.eurusd                  # limiter a une serie
veille history fx.eurusd --limit 20                # historique en base
```

Sans installation : `PYTHONPATH=src python3 -m veille_financiere.cli collect`.

L'option `--strict` renvoie un code de sortie non nul si un controle est en
erreur ou si un appel a echoue, ce qui permet de brancher la commande dans
une tache planifiee.

## Sources cablees

| Source | Couverture | Cle requise | Fiabilite observee |
|---|---|---|---|
| **FRED** (Fed de Saint-Louis) | Macro US, taux, indices, matieres premieres, crypto (Coinbase) | oui, gratuite | tres bonne |
| **London Strategic Edge** | Indices mondiaux, change, crypto, matieres premieres, rendements souverains, macro 194 pays | oui | tres bonne |
| **BCE** (portail de donnees) | Change, taux directeurs, inflation zone euro | non | tres bonne |
| **Eurostat** | Inflation IPCH par pays | non | bonne (jeu de donnees en retard) |
| **OCDE** | Indices de cours boursiers | non | bonne |
| **Banque mondiale** | Indicateurs annuels par pays | non | tres bonne |
| **FMI** (DataMapper) | Projections World Economic Outlook | non | tres bonne |
| **SEC EDGAR** | Fondamentaux XBRL des societes americaines | non (contact recommande) | tres bonne |
| **CoinGecko** | Prix crypto | non | bonne (debit limite) |
| **Frankfurter** | Change (references BCE) | non | tres bonne |
| **Yahoo Finance** | Actions, indices, matieres premieres | non | **desactive par defaut** (voir plus bas) |

### London Strategic Edge

C'est la source qui comble les angles morts des donnees publiques :

- **CAC 40, Euro Stoxx 50 en quotidien, or** — aucune alternative gratuite
  fiable n'existait ; ces series etaient auparavant absentes du rapport.
- **Inflation zone euro et France** — publiee jusqu'a juin 2026 la ou
  Eurostat et la BCE s'arretent a decembre 2025, soit six mois d'avance.
- **Rendements souverains allemands et francais**, absents de FRED.
- **Recoupement** de la plupart des series de marche deja couvertes, ce qui
  fait passer le nombre de series reconciliables de 16 a 21.

Trois familles d'endpoints sont exploitees, selectionnees par la cle `mode`
d'une entree du catalogue : `candles` (chandeliers OHLCV), `series`
(couples date/valeur pour la macro et les rendements) et `bond_yields`.

### Agenda macroeconomique

Le rapport s'ouvre sur ce qui est tombe et ce qui est attendu, en deux
tableaux : **deja paru** (avec constate, consensus et precedent, et un
verdict au-dessus / conforme / en dessous) et **attendu** (heure de
publication et consensus). C'est ce qui manquait le plus a une veille du
matin : savoir que la BCE publie ses minutes a 11h30 vaut souvent mieux
qu'une decimale de plus sur le CAC.

L'agenda est aussi la source la plus fraiche pour la macro. Le 20 aout, la
serie d'inflation zone euro s'arretait a juin, alors que l'agenda portait
deja le HICP de juillet publie la veille. Quand un chiffre vient de sortir,
il apparait la avant d'apparaitre dans les series.

`veille agenda` interroge l'agenda seul, sans collecter les series.

### A propos de Yahoo Finance

L'API de Yahoo est non documentee et limitee par adresse IP. Depuis certains
environnements (conteneurs, CI, sorties mutualisees) elle renvoie des `429`
en continu. Le projet la conserve en complement mais **ne s'appuie jamais
dessus seul** quand une alternative existe : les indices americains viennent
de FRED, l'Euro Stoxx 50 de la BCE, l'indice boursier francais de l'OCDE.
Une source qui echoue n'interrompt jamais la collecte. Un **disjoncteur**
coupe les appels vers un hote apres trois echecs consecutifs : sans lui, une
source hors service fait perdre plusieurs minutes en reessais dont l'issue
est deja connue (le run complet passe de plus de quinze minutes a environ une
minute). Une reponse 4xx definitive n'ouvre pas le disjoncteur : elle signale
une requete mal formee, pas un hote en panne.

Depuis le cablage de London Strategic Edge, plus aucune serie ne depend de
Yahoo seul : les trois qui manquaient au rapport (CAC 40, Euro Stoxx 50, or)
sont desormais servies par LSE. Yahoo est donc **desactive par defaut** — il
ne faisait plus qu'ajouter une minute et une trentaine de lignes d'erreur
par run. `VF_ENABLE_YAHOO=1` le remet en service pour qui dispose d'une
sortie reseau moins sollicitee.

## Controles qualite

Chaque serie passe quatre controles, journalises en base :

| Controle | Ce qu'il verifie |
|---|---|
| `freshness` | La derniere valeur est-elle assez recente pour la frequence annoncee ? Les projections datees dans le futur (FMI) sont traitees a part. |
| `continuity` | Manque-t-il des points dans l'historique ? Les dates sont dedoublonnees pour ne pas confondre couverture multi-sources et trou. |
| `outlier` | La derniere variation depasse-t-elle 6 ecarts-types de la distribution passee ? |
| `reconcile` | Les sources couvrant la meme serie sont-elles d'accord ? |

### Comment fonctionne la reconciliation

Trois regles evitent la plupart des faux positifs :

1. **Comparaison a date egale uniquement.** FRED publie ses taux de change
   avec quelques jours de retard sur la BCE. Comparer les dernieres valeurs
   de chaque source produirait une divergence qui ne reflete qu'un decalage
   de calendrier. Seules les dates communes sont confrontees.
2. **Seuils par categorie.** Les parites de change doivent coller de pres
   (0,4 %, ce qui laisse la place aux heures de fixing differentes : 14h15
   CET pour la BCE, midi a New York pour FRED), les agregats macro beaucoup
   moins (10 %, revisions et differences de methodologie).
3. **Dates de periode normalisees.** FRED et LSE datent une observation
   mensuelle au premier jour du mois, la BCE et Eurostat au libelle du mois.
   Sans recalage en fin de periode, deux sources decrivant le meme mois
   n'ont aucune date commune et le recoupement conclut a tort qu'elles ne
   sont pas comparables. Les series trimestrielles sont laissees telles
   quelles : les exercices des entreprises ne suivent pas le calendrier
   civil.
4. **Plancher absolu.** Une croissance de 0,70 % contre 0,86 % represente
   19 % d'ecart relatif mais seulement 0,16 point : sans plancher absolu,
   toute serie proche de zero declencherait une alerte.

Une serie peut surcharger le seuil de sa categorie quand celui-ci ne lui
convient pas : le VIX vit parmi les indices actions mais, cote a une
quinzaine de points, il bouge trop vite pour leur seuil resserre.

Une divergence dont le rapport est proche d'un facteur 10, 100 ou 1000 est
signalee comme probable probleme d'unite plutot que comme desaccord de fond.

### Valeur de reference

Quand plusieurs sources couvrent une serie, la valeur retenue est celle de la
source la plus fraiche ; a fraicheur egale, les institutions officielles
(BCE, FRED, Eurostat, SEC) passent avant les agregateurs de marche.

## Donnees

Tout est persiste dans `data/veille.sqlite3` :

- `observations` — cle primaire `(series_id, source, date)`, donc idempotent :
  relancer la collecte met a jour les valeurs revisees sans creer de doublon ;
- `run_log` — resultat de chaque appel (succes, latence, erreur) ;
- `quality_checks` — historique des controles, pour suivre la degradation
  d'une source dans le temps.

Le cache HTTP (`data/cache/`) evite de solliciter inutilement les APIs
limitees en debit.

## Fraicheur reelle

Le `close` d'une bougie quotidienne **en cours** est deja le dernier prix
traite — verifie en comparant la bougie `1d` et la derniere bougie `1h`
d'un meme instrument, qui donnent la meme valeur. Interroger l'intraday ne
fournirait donc pas un chiffre plus recent, seulement le chemin parcouru.

Ce que cela donne selon l'heure d'execution :

| Type | A 7h du matin | En seance |
|---|---|---|
| Indices europeens | derniere cloture (la premiere bougie du jour n'apparait qu'a 8h) | prix courant |
| Indices US | future en preouverture | prix courant |
| Change, crypto | prix courant (marches ouverts) | prix courant |
| Taux, macro | derniere publication officielle | idem |

Un WebSocket existe chez LSE mais n'a pas ete cable : il suppose un
processus connecte en permanence, ce qu'une tache declenchee une fois par
jour ne peut pas exploiter. Un simple appel REST est strictement meilleur
dans ce cas.

## Limites connues

- **Inflation zone euro et France** : Eurostat et la BCE s'arretent a
  decembre 2025 et divergent de 0,1 point sur ce mois (2,0 % contre 1,9 %),
  ecart absorbe par la tolerance macro. LSE prend le relais jusqu'a juin
  2026 et fournit la valeur de reference.
- **Rendements souverains allemands et francais** : environ dix jours de
  retard chez LSE, signale a chaque run. Pour la zone euro, la courbe AAA de
  la BCE (`rate.ea_10y_aaa`) est quotidienne et a J-1. Sur les taux
  americains, FRED reste le plus a jour (J-2) : les instruments LSE
  `USB10Y/USD` et consorts cotent un **prix de future** (108,5) et non un
  rendement (4,71), ils ne sont donc pas utilisables comme taux.
- **Projections** : le FMI publie jusqu'en 2031. Ces valeurs sont exclues du
  chiffre de reference et regroupees dans une section a part, pour ne pas
  presenter une prevision comme le dernier chiffre connu.
- **IBEX 35** : la serie LSE s'arrete a juin 2026 et est signalee comme
  obsolete a chaque run.
- **Resultat net trimestriel** : le quatrieme trimestre n'apparait pas
  toujours comme periode de 90 jours dans XBRL, les societes ne publiant
  alors que le cumul annuel dans leur 10-K. La serie peut donc sauter un
  trimestre. Le deduire (annuel moins cumul 9 mois) reste a faire.
## Un point de vigilance sur les fondamentaux SEC

Dans XBRL, une meme balise de flux (`NetIncomeLoss`) apparait aussi bien dans
un 10-Q (3 mois) que dans un 10-K (12 mois), et les rapports trimestriels
contiennent en plus des cumuls 6 et 9 mois. Les additionner dans une seule
serie donnerait des variations sans aucun sens. Les concepts de flux sont
donc filtres sur leur duree reelle (`duration_days`), tandis que les concepts
de stock (`Assets`, `StockholdersEquity`), dates a un instant, sont conserves
tels quels.

## Tests

```bash
PYTHONPATH=src python3 -m pytest tests/ -q
```

Les tests couvrent les parseurs (avec des charges utiles reelles figees), la
logique de qualite et la persistance. Ils ne font aucun appel reseau.

## Structure

```
src/veille_financiere/
  config.py      parametres et chargement des cles
  http.py        session HTTP: backoff, limitation de debit, cache disque
  models.py      Observation / SeriesResult
  storage.py     persistance SQLite
  quality.py     controles et reconciliation
  registry.py    catalogue des series suivies
  pipeline.py    orchestration
  report.py      rendu console / Markdown
  cli.py         interface en ligne de commande
  sources/       un module par fournisseur
```

Ajouter une serie se fait dans `registry.py` ; ajouter un fournisseur revient
a sous-classer `Source` et a implementer `_fetch_series`.
