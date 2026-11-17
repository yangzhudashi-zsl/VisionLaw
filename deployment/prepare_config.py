#!/usr/bin/env python3
"""Generate a machine-specific YAML without importing or running VisionLaw.

Run this on the target machine so absolute paths belong to that machine.
Only the generated YAML is written; no data, CUDA, checkpoint or API is loaded.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


DEPLOYMENT = Path(__file__).resolve().parent
PROJECT = DEPLOYMENT.parent


def build_config(scene: str, datasets_root: Path, assets_root: Path,
                 init_path: Path | None = None, run_path: str | None = None) -> dict:
    manifest = json.loads((DEPLOYMENT / "scene_manifest.json").read_text(encoding="utf-8"))
    entry = manifest[scene]
    template = PROJECT / "experiment" / "configs" / f"finetune-{scene}.yaml"
    config = yaml.safe_load(template.read_text(encoding="utf-8"))
    asset_root = assets_root.expanduser().resolve()
    scene_assets = asset_root / entry["asset"]
    config["gaussians"]["kernels_path"] = (scene_assets / "kernels.ply").as_posix()
    config["particles"]["shape"]["asset_root"] = asset_root.as_posix()
    config["particles"]["shape"]["pcd_name"] = f'{entry["asset"]}/particles'
    # Config.update would cast YAML null to the string "None" instead of keeping
    # PCDShapeConfig.sort=None, which can break uncached point-cloud loading.
    if config["particles"]["shape"].get("sort") is None:
        config["particles"]["shape"].pop("sort", None)
    if "mesh_path" in config["particles"]:
        # The upstream ClayCat template accidentally points to bouncyball/mesh.ply.
        config["particles"]["mesh_path"] = (scene_assets / "mesh.ply").as_posix()
    config["dataset"]["data"]["path"] = (
        datasets_root.expanduser().resolve() / entry["dataset"]
    ).as_posix()
    checkpoint = init_path or PROJECT / "experiment" / "ckpt" / scene / "init.pt"
    config["dataset"]["data"]["init_path"] = checkpoint.expanduser().resolve().as_posix()
    # Existing experiments are protected by default. Each invocation should use a new run path.
    config["overwrite"] = False
    if run_path is not None:
        config["path"] = run_path
    return config


def main() -> int:
    manifest = json.loads((DEPLOYMENT / "scene_manifest.json").read_text(encoding="utf-8"))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", choices=list(manifest), required=True)
    parser.add_argument("--datasets-root", type=Path, required=True,
                        help="Parent directory containing BouncyBall, ClayCat, bun, etc.")
    parser.add_argument("--assets-root", type=Path, required=True,
                        help="Parent directory containing bouncyball, claycat, real-bun, etc.")
    parser.add_argument("--output", type=Path,
                        help="Default: deployment/configs/finetune-SCENE.yaml")
    parser.add_argument("--init-path", type=Path, help="Override the bundled initial-state checkpoint.")
    parser.add_argument("--run-path", help="For manual upstream entry only; deployment/run.py rejects YAML path overrides.")
    parser.add_argument("--force", action="store_true", help="Replace an existing generated YAML.")
    args = parser.parse_args()
    target = args.output or DEPLOYMENT / "configs" / f"finetune-{args.scene}.yaml"
    target = target.expanduser().resolve()
    config = build_config(args.scene, args.datasets_root, args.assets_root,
                          args.init_path, args.run_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("w" if args.force else "x", encoding="utf-8", newline="\n") as stream:
            stream.write("# Generated locally; do not commit machine paths or secrets.\n")
            yaml.safe_dump(config, stream, sort_keys=False, allow_unicode=True)
    except FileExistsError:
        parser.error(f"Refusing to replace {target}; choose another --output or use --force.")
    print(f"Generated {target}")
    print("No project code, dataset, checkpoint, CUDA operation or API was executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
