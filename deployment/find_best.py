#!/usr/bin/env python3
"""Print the original candidate from final selected.json without model loading."""
import argparse
import json
from pathlib import Path
import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run = args.run_dir.expanduser().resolve()
    try:
        config = yaml.safe_load((run / "config.yaml").read_text(encoding="utf-8"))
        upper = config["optim"]["upper"]
        final_epoch = 2 * int(upper["alternate_epochs"]) + int(upper["joint_epochs"])
        final_selection = run / "iteration" / f"{final_epoch:04d}" / "selected.json"
        records = json.loads(final_selection.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        parser.error(f"Cannot read expected final selection; inference may be incomplete: {error}")
    if not records:
        parser.error("Final selection has no valid candidates; inspect experiment logs.")
    model = Path(min(records, key=lambda row: row["rank"])["root"])
    needed = [model / "physics.py", model / "ckpt/final_elasticity.pt", model / "ckpt/final_plasticity.pt"]
    if not all(path.is_file() for path in needed):
        parser.error(f"Candidate files missing at {model}; after migration restore paths or inspect JSON root.")
    print(model.resolve())


if __name__ == "__main__":
    main()
