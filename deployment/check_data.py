#!/usr/bin/env python3
"""Read-only data-layout checks based on VisionLaw's actual camera/MPM loaders.

This is not a runtime or numerical check. It reads YAML/JSON and file metadata;
it never imports VisionLaw, Torch or Warp and never deserializes .pt/.npz files.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


PROJECT = Path(__file__).resolve().parent.parent


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.files_checked = 0
        self.summary: dict = {}

    def file(self, path: Path, label: str) -> bool:
        self.files_checked += 1
        if not path.is_file():
            self.errors.append(f"Missing {label}: {path}")
            return False
        if path.stat().st_size == 0:
            self.errors.append(f"Empty {label}: {path}")
            return False
        return True

    def json(self, path: Path, label: str):
        if not self.file(path, label):
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            self.errors.append(f"Invalid {label}: {path}: {error}")
            return None


def resolve(value: str, project: Path) -> Path:
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (project / path).resolve()


def matrix(value, rows: tuple[int, ...], columns: int) -> bool:
    return (isinstance(value, list) and len(value) in rows
            and all(isinstance(row, list) and len(row) == columns
                    and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in row)
                    for row in value))


def discover_frames(directory: Path, data: dict, report: Report) -> tuple[list[str], list[int]]:
    if not directory.is_dir():
        report.errors.append(f"Missing image directory: {directory}")
        return [], []
    nframes = int(data["nframes"])
    skip = int(data.get("skip_frames", 1))
    if nframes < 1 or skip < 1:
        raise ValueError("dataset.data.nframes and skip_frames must be positive")
    # Matches VideoGuidance.readCameras, including the special 250-frame case.
    all_steps = set(range(401 if nframes == 250 else nframes + 1))
    excluded = set(data.get("exclude_steps") or [])
    excluded.update(all_steps - set(range(0, nframes + 1, skip)))
    used = data.get("used_views") or []
    views, steps = set(), set()
    invalid_names = []
    for path in directory.iterdir():
        match = re.fullmatch(r"(.+)_(-?\d+)\.[^.]+", path.name)
        if not path.is_file() or match is None:
            invalid_names.append(path.name)
            continue
        view, step = match.group(1), int(match.group(2))
        if not used or view in used:
            views.add(view)
        # The upstream loader derives steps from every view, including unselected views.
        if step not in excluded:
            steps.add(step)
    if invalid_names:
        report.errors.append("Unexpected entries would break camera-loader filename parsing: "
                             + ", ".join(invalid_names[:10]))
    for view in used:
        if view not in views:
            report.errors.append(f"Configured view {view!r} has no images in {directory}")
    if not views or not steps:
        report.errors.append(f"No selected views/steps in {directory}")
    required_steps = set(range(0, nframes + 1, skip)) - set(data.get("exclude_steps") or [])
    missing_steps = sorted(required_steps - steps)
    if missing_steps:
        report.errors.append(f"Missing configured time steps (first 20): {missing_steps[:20]}")
    outside = sorted(step for step in steps if step > nframes)
    if outside:
        report.warnings.append(f"Loader also sees steps beyond nframes (first 20): {outside[:20]}")
    report.summary.update(views=sorted(views), loaded_steps=len(steps),
                          first_step=min(steps) if steps else None,
                          last_step=max(steps) if steps else None)
    return sorted(views), sorted(steps)


def synthetic(root: Path, data: dict, report: Report) -> None:
    transformsfile = data.get("transformsfile", "data_dynamic.json")
    subfolder = transformsfile.split(".")[0]
    views, steps = discover_frames(root / subfolder, data, report)
    entries = report.json(root / transformsfile, "synthetic camera metadata")
    if entries is None:
        return
    if not isinstance(entries, list):
        report.errors.append("Synthetic camera JSON must be a list, as readNeuMASyntheticCameras expects.")
        return
    meta = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("file_path"), str):
            report.errors.append(f"Camera entry {index} is missing a string file_path.")
            continue
        key = entry["file_path"]
        if key in meta:
            report.errors.append(f"Duplicate camera file_path: {key}")
        meta[key] = entry
    for view in views:
        for step in steps:
            key = f"./{subfolder}/{view}_{step:03d}.png"
            report.file(root / key, "synthetic PNG")
            entry = meta.get(key)
            if entry is None:
                report.errors.append(f"Missing camera JSON key: {key}")
                continue
            if not matrix(entry.get("c2w"), (3, 4), 4):
                report.errors.append(f"Expected numeric 3x4 or 4x4 c2w for {key}")
            if not matrix(entry.get("intrinsic"), (3,), 3):
                report.errors.append(f"Expected numeric 3x3 intrinsic for {key}")


def real_capture(root: Path, data: dict, report: Report) -> None:
    report.file(root / "sparse" / "0" / "cameras.bin", "COLMAP camera intrinsics")
    calibration = report.json(root / "cameras_calib.json", "real camera calibration")
    views, steps = discover_frames(root / "dynamics", data, report)
    if calibration is not None and not isinstance(calibration, dict):
        report.errors.append("cameras_calib.json must contain a mapping keyed by view.")
        calibration = None
    for view in views:
        if calibration is not None:
            entry = calibration.get(view)
            if not isinstance(entry, dict) or "rvecs" not in entry or "tvecs" not in entry:
                report.errors.append(f"Missing rvecs/tvecs camera calibration for {view}")
        for step in steps:
            if not data.get("read_mask_only", False):
                report.file(root / "dynamics" / f"{view}_{step}.jpg", "real JPG")
            report.file(root / "dynamic_masks" / f"{view}_{step}.png", "real PNG mask")
    report.warnings.append("COLMAP binary contents, camera calibration numbers and image dimensions "
                           "are not decoded by this static check; upstream RealCapture assumes 1920x1080.")


def check(config: dict, project: Path) -> Report:
    report = Report()
    data = config["dataset"]["data"]
    camera_type = config["dataset"]["camera_type"]
    kernels = resolve(config["gaussians"]["kernels_path"], project)
    report.file(kernels, "Gaussian kernels")
    report.file(kernels.parent / "bindings.pt", "Gaussian-particle bindings checkpoint")
    report.file(resolve(data["init_path"], project), "initial position/velocity checkpoint")
    shape = config["particles"]["shape"]
    asset_root = resolve(shape["asset_root"], project)
    particle_base = asset_root / shape["pcd_name"]
    particle_cache = Path(str(particle_base) + ".npz")
    if particle_cache.is_file():
        report.file(particle_cache, "cached particles/volume")
        report.summary["particles"] = str(particle_cache)
    else:
        particle_ply = Path(str(particle_base) + ".ply")
        report.file(particle_ply, "particle point cloud (no NPZ cache exists)")
        report.summary["particles"] = str(particle_ply)
        report.warnings.append("No particles.npz cache: runtime will compute particle volumes and write "
                               "a cache beside particles.ply; the assets directory must be writable.")
    configured_mesh = config["particles"].get("mesh_path")
    if configured_mesh:
        report.file(resolve(configured_mesh, project), "configured particle mesh")
    meshes = list(particle_base.parent.glob("mesh.*")) if particle_base.parent.is_dir() else []
    if not particle_cache.is_file() and len(meshes) != 1:
        report.warnings.append("MPM loader finds other than one mesh.* beside particles.ply; "
                               "it will use convex-hull volume instead of mesh volume.")
    dataset_root = resolve(data["path"], project)
    report.summary.update(camera_type=camera_type, dataset=str(dataset_root))
    if camera_type == "NeuMASynthetic":
        synthetic(dataset_root, data, report)
    elif camera_type == "RealCapture":
        real_capture(dataset_root, data, report)
    else:
        report.errors.append(f"Unsupported camera_type: {camera_type}")
    report.warnings.append("Checkpoint, NPZ/PLY contents and particle/binding compatibility are not loaded "
                           "or validated. Static success does not establish runnable training or reproduction.")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=PROJECT,
                        help="Resolve relative config data paths from this project root.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable report.")
    args = parser.parse_args()
    try:
        config = yaml.safe_load(args.config.read_text(encoding="utf-8-sig"))
        report = check(config, args.project_root.expanduser().resolve())
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        parser.error(f"Cannot check config: {error}")
    result = {"static_data_check": "failed" if report.errors else "passed",
              "files_checked": report.files_checked, "summary": report.summary,
              "errors": report.errors, "warnings": report.warnings}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f'Static data check: {result["static_data_check"]}; files checked: {report.files_checked}')
        print(json.dumps(report.summary, indent=2, ensure_ascii=False))
        for error in report.errors:
            print(f"ERROR: {error}")
        for warning in report.warnings:
            print(f"WARNING: {warning}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
