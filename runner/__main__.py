import argparse

from . import build_data, discover, run, selfcheck


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m runner")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("discover", help="add new open-weight models from OpenRouter to bench/models.json")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=discover.main)

    p = sub.add_parser("run", help="run missing (model, question) pairs")
    p.add_argument("--models", help="comma-separated slugs (default: all active/auto models)")
    p.add_argument("--suites", help="comma-separated suites (default: all)")
    p.add_argument("--budget-usd", type=float, default=2.0, help="stop sending requests after this spend")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--rerun", action="store_true", help="ignore stored scores")
    p.set_defaults(fn=run.main)

    p = sub.add_parser("build-data", help="aggregate scores into site/src/data")
    p.add_argument("--include-test", action="store_true", help="include mock models (local testing)")
    p.set_defaults(fn=build_data.main)

    p = sub.add_parser("selfcheck", help="validate the question bank")
    p.set_defaults(fn=selfcheck.main)

    args = ap.parse_args()
    args.fn(args)


main()
