import re
import json
import argparse
from pathlib import Path

# Single-pass pattern with named groups. Precedence: IP → serial → hostname.
# re.ASCII ensures \b and character classes only match ASCII — correct for
# network identifiers and prevents surprises on files with non-ASCII prose.
_PATTERN = re.compile(
    r'(?P<ip>\b(?:\d{1,3}\.){3}\d{1,3}\b)'
    r'|(?P<serial>\bFAKE-SN-\d+\b)'
    r'|(?P<host>\b[a-z][a-z]*(?:-[a-z0-9]+)*-\d+\b)',
    re.ASCII,
)

# Anchored to this file's location so the module works regardless of cwd.
_DEFAULT_MAP_PATH = Path(__file__).resolve().parent / "identifiers.map.json"


def pseudonymize(text: str) -> tuple[str, dict[str, str]]:
    """
    Replace every sensitive identifier in text with a stable, deterministic
    placeholder. Same token → same placeholder across the entire document.

    Returns (pseudonymized_text, mapping) where mapping is
    {placeholder: real_value} — the reversal key for re-identification later.
    """
    counters = {"ip": 0, "serial": 0, "host": 0}
    token_to_placeholder: dict[str, str] = {}  # real_value → placeholder

    def _replace(match: re.Match) -> str:
        token = match.group(0)
        if token in token_to_placeholder:
            return token_to_placeholder[token]  # deterministic: same token, same result

        if match.group("ip"):
            counters["ip"] += 1
            placeholder = f"IP_{counters['ip']:03d}"
        elif match.group("serial"):
            counters["serial"] += 1
            placeholder = f"SERIAL_{counters['serial']:03d}"
        else:
            counters["host"] += 1
            placeholder = f"HOST_{counters['host']:03d}"

        token_to_placeholder[token] = placeholder
        return placeholder

    pseudonymized = _PATTERN.sub(_replace, text)
    # Invert: placeholder → real value, ready for the re-identification slice.
    mapping = {v: k for k, v in token_to_placeholder.items()}
    return pseudonymized, mapping


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pseudonymize sensitive identifiers in a network document."
    )
    parser.add_argument("input_file", type=Path, help="Path to the input document")
    parser.add_argument(
        "--map-out",
        type=Path,
        default=_DEFAULT_MAP_PATH,
        help=f"Path to write the identifier mapping (default: {_DEFAULT_MAP_PATH})",
    )
    args = parser.parse_args()

    text = args.input_file.read_text()
    pseudonymized, mapping = pseudonymize(text)

    args.map_out.write_text(json.dumps(mapping, indent=2))
    print(f"[map] {len(mapping)} identifiers → {args.map_out}", flush=True)
    print()
    print(pseudonymized)


if __name__ == "__main__":
    main()
