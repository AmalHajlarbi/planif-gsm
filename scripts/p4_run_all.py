"""Phase 4 : chaine complete P1 -> P2 -> P3 + exports finaux dans results/p4_final/.

Executer depuis la racine du projet (planif-gsm/) :
    python scripts/p4_run_all.py
    python scripts/p4_run_all.py --N 9 --strategy contigue --rows 9 --cols 9
"""
from __future__ import annotations

import argparse

from planif.back_end.freq_allocation import STRATEGIES
from planif.back_end.params_io import load_params, update_params
from planif.paths import DEFAULT_PARAMS_FILE
from planif.pipeline import DEFAULT_STRATEGY, build_summary_text, export_all, run_pipeline


def main() -> None:
    ap = argparse.ArgumentParser(description="Planification GSM : chaine complete")
    ap.add_argument("--params", default=str(DEFAULT_PARAMS_FILE), help="chemin de params.json")
    ap.add_argument("--N", type=int, default=None, help="motif a utiliser (sinon : params.json)")
    ap.add_argument("--strategy", choices=STRATEGIES, default=DEFAULT_STRATEGY)
    ap.add_argument("--rows", type=int, default=7)
    ap.add_argument("--cols", type=int, default=7)
    ap.add_argument("--no-studies", action="store_true", help="ne pas calculer les etudes P3")
    args = ap.parse_args()

    params = load_params(args.params)
    if args.N is not None:
        params = update_params(params, N=args.N)

    result = run_pipeline(params, strategy=args.strategy, rows=args.rows, cols=args.cols,
                          with_studies=not args.no_studies)
    print(build_summary_text(result))

    files = export_all(result)
    print(f"\n{len(files)} fichiers generes dans {files[0].parent.parent} :")
    for f in files:
        print(" -", f.name)


if __name__ == "__main__":
    main()