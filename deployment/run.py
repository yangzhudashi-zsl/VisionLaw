#!/usr/bin/env python3
"""Print a single-seed command; execute only with --execute on Linux.

The default only reads YAML/file metadata and prints argv. It never imports the
project, initializes CUDA, deserializes checkpoints or contacts an LLM.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

import yaml

from check_data import check

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("infer", "render"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="A new, empty experiment path.")
    parser.add_argument("--seed", type=int, choices=range(5), default=0)
    parser.add_argument("--gpu", default="0", help="Physical device mapped to internal cuda:0.")
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--execute", action="store_true", help="Actually run on Linux, including billable LLM calls for infer.")
    args = parser.parse_args()
    config_path = args.config.expanduser().resolve()
    output = args.output.expanduser().resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8-sig"))
    # YAML options are applied after argv in upstream, so reject overrides that
    # would silently replace this launcher's safety and reproducibility options.
    for key in ("path", "seed", "resume", "gpu"):
        if key in config:
            parser.error(f"Remove top-level {key!r} from the generated YAML; launcher manages it.")
    if config.get("overwrite", False):
        parser.error("Set overwrite: false in the generated YAML.")
    if config.get("llm", {}).get("api_key"):
        parser.error("Use OPENAI_API_KEY in the environment, not a YAML key.")
    if output.exists():
        parser.error(f"Output already exists; choose a new path: {output}")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.gpu
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUNBUFFERED"] = "1"
    if args.mode == "infer":
        command = [sys.executable, str(ROOT / "experiment/entry/agent_vision_bilevel.py"),
                   "--config", str(config_path), "--path", str(output),
                   f"--seed={args.seed}", "--gpu=0", "--overwrite=false", "--resume=false",
                   "--llm=openai-gpt-4.1-mini", "--llm.primitives=(elastoplasticity)",
                   "--physics.env.physics=elastoplasticity"]
    else:
        if args.model_dir is None:
            parser.error("render requires --model-dir (original candidate with physics.py and ckpt/)")
        model = args.model_dir.expanduser().resolve()
        required = [model / "physics.py", model / "ckpt/final_elasticity.pt",
                    model / "ckpt/final_plasticity.pt"]
        if any(not path.is_file() for path in required):
            parser.error("Model directory lacks physics.py or final elasticity/plasticity checkpoints.")
        command = [sys.executable, str(ROOT / "experiment/entry/vision/elastoplasticity/forward.py"),
                   "--config", str(config_path), "--path", str(output), "--model_dir", str(model)]
    print(f"Working directory: {ROOT}")
    print(f"CUDA_VISIBLE_DEVICES={args.gpu}; internal device cuda:0")
    print("Command:", shlex.join(command))
    if not args.execute:
        print("Preview only. No project, CUDA or API execution. Add --execute on the Linux server when ready.")
        return 0
    if sys.platform != "linux":
        parser.error("Actual project execution requires Linux; upstream imports fcntl.")
    check_config = copy.deepcopy(config)
    if args.mode == "render":
        # forward.py renders every frame, regardless of training's subsampling.
        check_config["dataset"]["data"]["skip_frames"] = 1
    report = check(check_config, ROOT)
    if report.errors:
        print(json.dumps({"data_errors": report.errors}, ensure_ascii=False, indent=2))
        return 1
    if args.mode == "infer" and not env.get("OPENAI_API_KEY"):
        parser.error("OPENAI_API_KEY is unset or empty.")
    return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
