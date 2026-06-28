import argparse
import sys

from scaffold.engine.applier import apply
from scaffold.engine.baseline import load
from scaffold.engine.client import get_client


def _print_table(counts: dict, dry_run: bool) -> None:
    prefix = "[dry-run] " if dry_run else ""
    col_w = max(len(t) for t in counts) + 2
    header = f"{'type':<{col_w}}  {'created':>8}  {'updated':>8}  {'unchanged':>10}"
    separator = "-" * len(header)
    print(f"\n{prefix}results:")
    print(header)
    print(separator)
    for type_key, c in counts.items():
        print(f"{type_key:<{col_w}}  {c['created']:>8}  {c['updated']:>8}  {c['unchanged']:>10}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply a NetBox baseline YAML to a live NetBox instance."
    )
    parser.add_argument("baseline_file", help="Path to the baseline YAML (e.g. baselines/fakecorp.yaml)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would change without writing")
    args = parser.parse_args()

    try:
        baseline = load(args.baseline_file)
    except (ValueError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    nb = get_client()

    try:
        counts = apply(baseline, nb, dry_run=args.dry_run)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    _print_table(counts, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
