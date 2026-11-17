# Planification d'un réseau mobile GSM avec Python

Mini-projet 2 : bilan de liaison, rayon de cellule, distance de réutilisation, SIR,
plan hexagonal, allocation des canaux, études de densité et d'environnement.

## Installation (PowerShell)
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

## Utilisation
| Action | Commande |
|---|---|
| Application web | `streamlit run src/planif/front_end/app_streamlit.py` |
| Chaîne complète (CLI) | `python scripts/p4_run_all.py` |
| Autre motif / stratégie | `python scripts/p4_run_all.py --N 9 --strategy contigue` |
| Tests | `python -m pytest -v` |
| Phase 1 / 2 / 3 seule | `python scripts/p1_run_radio.py` / `p2_run_plan.py` / `p3_run_alloc.py` |

Les paramètres sont dans `config/params.json` (modifiables dans l'application) ;
les hypothèses d'étude (zone, environnements, densités) sont dans `config/studies.json`.

## Architecture
- `src/planif/contracts.py` : objets échangés entre modules (figé).
- `back_end/` : calcul (P1 : radio ; P2 : plan, coloration ; P3 : allocation, études).
- `front_end/` : tracés et application Streamlit (aucun calcul).
- `pipeline.py` : enchaîne P1, P2, P3 et exporte `results/p4_final/`.
- `results/pX_*/` : sorties de chaque phase (`tables/` et `figures/`).

## Choix techniques non précisés par l'énoncé
- PL(d0) en espace libre : 32.44 + 20 log10(f_MHz) + 20 log10(d0_km), ou clé `PL_d0_dB`.
- Hexagones pointe en haut, grille « odd-r », R = rayon centre-sommet.
- Exposants : urbain 3.5, sub-urbain 3.0, rural 2.5 ; zone de 5000 km² ; 1 site par cellule.
- 1 canal par utilisateur actif (un vrai GSM multiplexe 8 intervalles de temps).
- Dans ce modèle le SIR ne dépend que de N et de n, pas de R.