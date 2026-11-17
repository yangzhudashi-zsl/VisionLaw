# VisionLaw 本地准备与服务器操作流程

准备日期：2026-11-17。官方代码基线为 `a35e14ae4d3402b53037aeafef45b66c99097f8e`，来自 [JiajingLin/VisionLaw](https://github.com/JiajingLin/VisionLaw)，你的仓库为 [yangzhudashi-zsl/VisionLaw](https://github.com/yangzhudashi-zsl/VisionLaw)。本次只做下载、环境准备和静态检查，没有启动项目、训练、仿真、渲染或 LLM 请求。

## 1. 本机与服务器的用途

本机 Windows 上准备源码、Python 3.10 配置工具环境、CUDA 扩展源码与部署文件。官方项目导入时使用 Unix 的 `fcntl`，并包含 Xvfb；本次没有移植为原生 Windows 可运行程序，也没有安装 WSL。本机 RTX 3060 Laptop 6GB 是否能完成实验，没有运行证据。

完整运行环境在后续 Linux GPU 服务器安装。论文第 6、15 页使用 **NVIDIA A40 48GB**，优先租与论文一致的显卡。Ubuntu 22.04、16 核 CPU、64GB 内存和至少 150GB 可用持久磁盘是工程预留建议，并非论文最低配置。数据解压和输出可能需要更多空间。24GB 显卡是否够用尚未验证。租机前确认持久盘策略、镜像包含 CUDA Toolkit 11.8 的 `nvcc`，以及能访问 GitHub、GitLab、PyPI、数据站和 LLM 服务。

## 2. 本机准备与目录

```text
D:\work-codex\VisionLaw\
  原始论文.pdf                     # 保留在父目录，不上传论文
  code\                           # 你的 GitHub 仓库
    .envs\visionlaw\python.exe     # 本地配置工具环境
    gaussian-splatting\            # 固定版本外部源码，忽略提交
    deployment\                   # 本流程与部署脚本
    experiment\ckpt\              # 官方提供的 init.pt
  datasets\                       # 后续存放数据，目前未下载
```

PowerShell 中重新准备工具环境或生成配置：

```powershell
Set-Location D:\work-codex\VisionLaw\code
& .\deployment\setup_local.ps1
$vlPython = '.\.envs\visionlaw\python.exe'
& $vlPython deployment/prepare_config.py --scene bb --datasets-root ../datasets/data --assets-root ../datasets/assets
& $vlPython deployment/check_data.py --config deployment/configs/finetune-bb.yaml
```

已有配置会拒绝覆盖，确需更新时加 `--force`，只替换生成的 YAML。数据未下载时预检应失败。配置含本机绝对路径，**到服务器重新生成**。预检不导入项目，不加载 `.pt`、NPZ 或 CUDA。

## 3. 服务器环境安装

下面的 Linux 命令供以后执行，本次没有执行。SSH 登录后先检查：

```bash
nvidia-smi
nvcc --version
df -h
free -h
```

`nvidia-smi` 顶部 CUDA 版本表示驱动能力，不等于 Toolkit 版本。选择带 Conda、CUDA Toolkit 11.8 的 Ubuntu 22.04 镜像。安装系统包；root 登录可去掉 `sudo`：

```bash
sudo apt-get update
sudo apt-get install -y git build-essential gcc-11 g++-11 ffmpeg xvfb xauth tmux \
  libgl1 libegl1 libglib2.0-0 libxrender1 libsm6 libxext6
```

在云控制台确认持久盘挂载点，下面 `/data` 仅是示例，改成实际持久磁盘路径：

```bash
export VISIONLAW_WORK=/data/visionlaw-work
mkdir -p "$VISIONLAW_WORK"
git clone https://github.com/yangzhudashi-zsl/VisionLaw.git "$VISIONLAW_WORK/code"
cd "$VISIONLAW_WORK/code"
git rev-parse HEAD
export CUDA_HOME=/usr/local/cuda-11.8
export CC=gcc-11
export CXX=g++-11
export TORCH_CUDA_ARCH_LIST=8.6  # A40；其他显卡按架构调整
bash deployment/install_server.sh
conda activate "$PWD/.envs/visionlaw-server"
export PYTHONPATH="$PWD:${PYTHONPATH:-}"
```

脚本采用 Python 3.10、PyTorch 2.1.2/torchvision 0.16.2/torchaudio 2.1.2（cu118）、warp-lang 1.1.0。Gaussian Splatting 固定为 `b17ded92b56ba02b6b7eaba2e66a2b0510f27764`，只下载两个必需扩展及其子模块，不装 SIBR 查看器。安装后执行 `pip check` 并保存实际依赖清单至 `deployment/reports/`。

**不要直接安装原始 requirements.txt**：它包含冲突的 PyVista 固定版本。本流程的 `requirements-linux.txt` 保留后面的 0.44.0，补上 `jaxtyping`、`ffmpeg-python` 等直接导入依赖。它是部署选定版本列表，尚未在 Linux GPU 上完成解析、安装和运行验证，不是完整锁文件。安装过程不会启动训练、仿真、渲染或请求 LLM。云镜像预装的 Torch 不用覆盖，使用此独立环境。

## 4. 官方数据下载与布局

以下链接来自 [官方 README](https://github.com/JiajingLin/VisionLaw#dataset-preparation)，本次未下载或验证压缩包内容。失效时从官方仓库或作者获取更新：

- [合成数据（NeuMA）](https://1drv.ms/u/c/3f1ccc11f481c100/EZUKCz9lrVBLquZGaXqvF1IB_XVKBBx4BK2LAt8GuFpVZQ?e=ub9Jek)
- [真实数据](https://1drv.ms/u/c/3f1ccc11f481c100/Edqcvj_qOK9HgWycdfX53UMBn-5XTTh3VDcu56CcNEzx6A?e=LT0R1j)
- 重建及绑定资产：使用官方 README 的 **Download the assets** 链接。
- [官方已推断本构示例（仅渲染可用）](https://1drv.ms/f/c/9a797b44cb7a4d76/IgDvWoVxuww5TbyuGFbTJo7-AWffYrrHQCz17jB8z0EYG7I?e=B2hfd8)

解压后检查是否多套了一层目录。推荐布局：

```text
/data/visionlaw-work/
  data/
    BouncyBall/
      data_dynamic.json
      data_dynamic/d_0_000.png ...
    JellyDuck/ RubberPawn/ ClayCat/ HoneyBottle/ SandFish/
    bun/
      sparse/0/cameras.bin
      cameras_calib.json
      dynamics/r_1_0.jpg ...
      dynamic_masks/r_1_0.png ...
    burger/ ...
  assets/
    bouncyball/
      kernels.ply
      bindings.pt
      particles.npz 或 particles.ply
      mesh.ply
    jellyduck/ rubberpawn/ claycat/ honeybottle/ sandfish/
    real-bun/ real-burger/
```

`bindings.pt` 必须在 `kernels.ply` 同目录；粒子 NPZ/PLY 至少一个。预检还要求合成模板中配置的 `mesh.ply` 存在。

| 场景选项 | data 下的目录 | assets 下的目录 |
| --- | --- | --- |
| bb | BouncyBall | bouncyball |
| jd | JellyDuck | jellyduck |
| rp | RubberPawn | rubberpawn |
| cc | ClayCat | claycat |
| hb | HoneyBottle | honeybottle |
| sf | SandFish | sandfish |
| bun | bun | real-bun |
| burger | burger | real-burger |

若先下载到 Windows，可用云平台文件上传或 `scp -r` 传输数据；大文件优先用平台支持的可续传方式。不要上传本机 `.envs` 或编译好的 Windows 扩展，服务器重新安装。

## 5. 服务器生成配置与静态预检

```bash
cd "$VISIONLAW_WORK/code"
python deployment/prepare_config.py --scene bb \
  --datasets-root "$VISIONLAW_WORK/data" --assets-root "$VISIONLAW_WORK/assets"
python deployment/check_data.py --config deployment/configs/finetune-bb.yaml --json
```

将 `bb` 换成表内其他选项。生成器保留上游实验参数，修正 ClayCat 网格路径，删除会被旧解析器误转为字符串的 `sort: null`，设置 `overwrite: false`，引用代码内的 `experiment/ckpt/<scene>/init.pt`。如有另一个初始化，传 `--init-path`。不要另加顶层 `path/seed/gpu/resume`，由启动工具管理。

静态预检通过不证明 checkpoint 内容、粒子绑定、显存或仿真正确。数据/资产目录要可写：上游会重建数据目录里的 `guidance/`，首次可能生成粒子缓存。不要让并行任务共享同一场景的数据工作目录。

## 6. 以后实际运行：单场景单种子

下面的执行步骤会使用 GPU 和付费 LLM，**本次没有执行**。先只预览命令：

```bash
python deployment/run.py infer --config deployment/configs/finetune-bb.yaml \
  --output "$VISIONLAW_WORK/runs/bb-seed0" --seed 0
```

准备实际运行时，先进入持久会话。若新开终端或 tmux 服务已存在，在会话内重新设置工作路径并激活环境（示例路径仍须改成实际持久盘）：

```bash
tmux new -s visionlaw
export VISIONLAW_WORK=/data/visionlaw-work
cd "$VISIONLAW_WORK/code"
conda activate "$PWD/.envs/visionlaw-server"
```

然后在这个会话内输入自己的 key，不写进代码/YAML或 shell 历史：

```bash
read -rsp 'OPENAI_API_KEY: ' OPENAI_API_KEY
export OPENAI_API_KEY
printf '\n'
```

使用官方已注册的 `openai-gpt-4.1-mini`，SDK 从环境读 key。第三方兼容服务可另设 `OPENAI_BASE_URL`，其兼容性本次未验证。不要通过 dataclass/YAML 填 key，上游会打印并保存配置。

在同一个会话内执行；SSH 断开后可用 `tmux attach -t visionlaw` 重新连接：

```bash
mkdir -p "$VISIONLAW_WORK/logs"
set -o pipefail
python deployment/run.py infer --config deployment/configs/finetune-bb.yaml \
  --output "$VISIONLAW_WORK/runs/bb-seed0" --seed 0 --gpu 0 --execute \
  2>&1 | tee "$VISIONLAW_WORK/logs/bb-seed0.log"
```

`run.py` 只有加 `--execute` 才启动项目，并要求 Linux、数据预检通过、输出目录不存在和 API key 已设置。`--gpu` 指物理 GPU，工具经 `CUDA_VISIBLE_DEVICES` 映射，内部保持 `cuda:0`。官方旧推断 launcher 固定连续跑 5 个种子，初次不要误用；`experiment/script/forward.py` 还指向不存在的文件，不要使用。

单次结果检查后，可用新目录串行扩展 5 个种子，例如新一批次：

```bash
for seed in 0 1 2 3 4; do
  python deployment/run.py infer --config deployment/configs/finetune-bb.yaml \
    --output "$VISIONLAW_WORK/runs/bb-batch2-seed${seed}" --seed "$seed" --execute || break
done
```

不要开启 overwrite 复用已有输出。上游完整断点恢复本次未验证，中断后保留旧结果，用新目录重跑前先评估费用。完整论文还要做其他 7 个场景和评估，单次运行不等于论文复现。

## 7. 选择模型、渲染与取回结果

推断输出含候选本构、checkpoint、消息、每轮选择 JSON 和 TensorBoard 文件。工具从最终轮 `selected.json` 找出实际候选：

```bash
MODEL_DIR="$(python deployment/find_best.py --run-dir "$VISIONLAW_WORK/runs/bb-seed0")"
python deployment/run.py render --config deployment/configs/finetune-bb.yaml \
  --output "$VISIONLAW_WORK/renders/bb-seed0" --model-dir "$MODEL_DIR"
# 以后需要实际渲染时，给上一命令添加 --execute。
```

模型目录必须有 `physics.py`、`ckpt/final_elasticity.pt` 和 `ckpt/final_plasticity.pt`。`iteration/*/best_0000` 只是摘要，不能直接渲染。`find_best.py` 只读 JSON 和文件元数据；失败或迁移后绝对路径失效时会报错。常规配置最终排名是 `iteration/0007`，工具自动选择最后一轮。

停机前备份 `runs/`、`renders/`、`logs/`、生成的配置和 `deployment/reports/`，记录代码 commit、GPU、实际依赖、种子、数据校验值，勿把 API key 一并打包。在本机 PowerShell 取回示例：

```powershell
# 替换用户名、地址、端口、服务器目录。
scp -P 22 -r user@server:/data/visionlaw-work/runs D:\work-codex\VisionLaw\output
```

确认结果备份与持久盘策略后再停止/释放实例。论文时间表不能直接换算你的租机总时长，API 费用也单独计算。

## 8. 常见问题

| 现象 | 处理 |
| --- | --- |
| `No module named fcntl` | 使用 Linux；本机仅配置工具环境。 |
| PyVista 版本冲突 | 安装 deployment/requirements-linux.txt。 |
| 无 nvcc / CUDA 不匹配 | 选 CUDA Toolkit 11.8，检查 CUDA_HOME。 |
| 编译缺 glm/simple-knn | 按安装脚本更新子模块，检查 GitHub/GitLab 网络。 |
| 扩展 `undefined symbol` | 在当前独立环境用固定源码重新编译，不复制外部 .so。 |
| 数据预检失败 | 按完整报错路径查解压层数、大小写、图像和资产。 |
| API 401/429 或模型不可用 | 查 key、余额/限额、模型权限与网络，保留日志，避免高频重试。 |
| 首次评估时下载失败 | LPIPS/VGG16 还会联网取权重，需访问 PyTorch 下载站和 richzhang/PerceptualSimilarity。 |
| 显存不足 | 优先使用论文的 48GB 级别；缩短帧数/减网格会改变实验，须另存并记录。 |
| 退出码正常但结果缺失 | 查日志及 selected.json；上游会把部分候选错误捕获为无限损失。 |

论文与代码差异见 [PAPER_AND_CODE_NOTES_ZH.md](PAPER_AND_CODE_NOTES_ZH.md)。本次准备状态见 [LOCAL_STATUS_ZH.md](LOCAL_STATUS_ZH.md)。
