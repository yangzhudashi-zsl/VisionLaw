#!/usr/bin/env bash
# Installation only: never calls training, rendering, Warp initialization or LLMs.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GS_REV=b17ded92b56ba02b6b7eaba2e66a2b0510f27764
PREFIX="${VISIONLAW_ENV_PREFIX:-$ROOT/.envs/visionlaw-server}"
[[ "$(uname -s)" == Linux ]] || { echo 'Linux is required (upstream imports fcntl).' >&2; exit 1; }
command -v conda >/dev/null || { echo 'Activate a Conda-capable terminal first.' >&2; exit 1; }
export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda-11.8}"
[[ -x "$CUDA_HOME/bin/nvcc" ]] || { echo "Missing nvcc: $CUDA_HOME/bin/nvcc" >&2; exit 1; }
"$CUDA_HOME/bin/nvcc" --version | grep -q 'release 11.8' || { echo 'Use CUDA Toolkit 11.8 for cu118 extensions.' >&2; exit 1; }
command -v g++ >/dev/null || { echo 'Install g++/build-essential first.' >&2; exit 1; }
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
export TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST:-8.6}"
export MAX_JOBS="${MAX_JOBS:-4}"
export CC="${CC:-gcc}"
export CXX="${CXX:-g++}"
if [[ ! -x "$PREFIX/bin/python" ]]; then
  conda create -y --prefix "$PREFIX" python=3.10 pip --override-channels -c https://repo.anaconda.com/pkgs/main
fi
PY="$PREFIX/bin/python"
PIP_INDEX="${VISIONLAW_PIP_INDEX:-https://pypi.org/simple}"
"$PY" -c 'import sys; assert sys.version_info[:2] == (3,10), "Expected Python 3.10"'
"$PY" -m pip install --index-url "$PIP_INDEX" 'pip==24.3.1' 'setuptools==69.5.1' 'wheel==0.43.0'
"$PY" -m pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
"$PY" -m pip install --index-url "$PIP_INDEX" -r "$ROOT/deployment/requirements-linux.txt"
GS="$ROOT/gaussian-splatting"
if [[ ! -d "$GS/.git" ]]; then
  git clone --no-checkout https://github.com/graphdeco-inria/gaussian-splatting.git "$GS"
else
  [[ -z "$(git -C "$GS" status --porcelain --untracked-files=all)" ]] || { echo 'Gaussian Splatting has local modifications; inspect before installing.' >&2; exit 1; }
fi
git -C "$GS" checkout "$GS_REV"
git -C "$GS" submodule update --init --recursive submodules/diff-gaussian-rasterization submodules/simple-knn
"$PY" -m pip install --no-build-isolation "$GS/submodules/diff-gaussian-rasterization" "$GS/submodules/simple-knn"
"$PY" -m pip install --no-deps --no-build-isolation -e "$ROOT"
"$PY" -m pip check
mkdir -p "$ROOT/deployment/reports"
"$PY" -m pip freeze > "$ROOT/deployment/reports/pip-freeze-linux.txt"
conda list --prefix "$PREFIX" --explicit > "$ROOT/deployment/reports/conda-linux-explicit.txt"
printf 'Installed dependencies in %s. No experiment was started.\n' "$PREFIX"
