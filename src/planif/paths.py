"""Chemins du projet (partage par toute l'equipe)."""
from pathlib import Path

# .../planif-gsm/src/planif/paths.py -> racine = 3 niveaux au-dessus
ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT_DIR / "config"
RESULTS_DIR = ROOT_DIR / "results"
DEFAULT_PARAMS_FILE = CONFIG_DIR / "params.json"


def results_dir(phase: str, kind: str) -> Path:
    """Retourne results/<phase>/<kind> (ex: results/p1_radio/figures) et le cree."""
    path = RESULTS_DIR / phase / kind
    path.mkdir(parents=True, exist_ok=True)
    return path