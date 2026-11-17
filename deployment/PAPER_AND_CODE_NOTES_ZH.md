# VisionLaw 论文、公开代码与复现边界

核对日期：2026-11-17。论文为当前文件夹中的 ICLR 2026 版本；公开代码基线为 `JiajingLin/VisionLaw` 提交 `a35e14ae4d3402b53037aeafef45b66c99097f8e`。本说明来自论文阅读与源码静态核对，没有启动本构搜索、训练、仿真、渲染或 LLM API 请求。

来源：[论文](https://arxiv.org/abs/2508.13792)、[官方 README](https://github.com/JiajingLin/VisionLaw/blob/a35e14ae4d3402b53037aeafef45b66c99097f8e/README.md)。下列页码为论文页脚页码。

## 硬件与输入条件

- 论文第 6 页 §4.1.1、第 15 页 A.1 明确使用 **NVIDIA A40 48GB**。这是已报告的实验平台，不是已证明的最低显存。其他 24GB 卡及本机 6GB 卡能否运行完整流程，尚无本次运行证据；服务器 CPU、内存、磁盘容量建议属于工程预留，不能写成论文实测需求。
- 初始化使用初始时刻的**多视角图像**重建 3DGS，并建立 Particle-GS 绑定；后续动力学推断使用**单个正面视角视频**（第 6、15 页）。单视角动力学监督不代表从任意一段单视角视频直接完成几何重建。
- 论文第 15 页 A.2 说明初速度使用 NeuMA 数据配置。实际 `experiment/entry/vision/elastoplasticity/train.py` 加载 Gaussian 核同目录下的 `bindings.pt`，并从 `dataset.data.init_path` 加载初始状态。数据视频、Gaussian 核、绑定和初始状态都必须准备齐全；不能用空文件代替。
- 软件版本以代码及部署文件为依据。官方 README 指定 Python 3.10、PyTorch 2.1.2/cu118，并固定 Gaussian Splatting 提交；论文相关实验段落没有给出完整的软件环境锁定信息。

## 论文协议与实际配置

| 项目 | 论文设置 | 公开代码核对与处理 |
|---|---|---|
| LLM | GPT-4.1-mini，第 6、15 页 | `visionlaw/config/llm/openai.py` 中模型为 `gpt-4.1-mini`。需要可用的服务、API 密钥及独立 API 费用；密钥使用环境变量，不写入版本库。 |
| 上层轮数 | 4 轮交替、3 轮联合，第 15 页 | YAML 的 `alternate_epochs: 2` 在 `agent_vision_bilevel.py` 乘以 2，随后 `joint_epochs: 3`，共 7 轮。 |
| 搜索规模 | 交替阶段 top 3 各产生 6 个子代；联合阶段 top 5 产生 18 个子代，第 15 页 | YAML 交替阶段 `num_exploit + num_explore = 2 + 4`、`batch_size: 3`；联合阶段为 `6 + 12`、`batch_size: 5`。这是完整搜索的成本来源。 |
| 下层优化 | Adam，10 次，学习率 **1e-3**，第 15 页 | 八份 `experiment/configs/finetune-*.yaml` 均为 `num_epochs: 10`、**`lr: 0.03`**；`train.py` 将该学习率用于弹性及塑性 Adam。存在论文与代码差异，本次保留公开 YAML；后续若比较两者，应另存配置并记录，不能悄悄改成 1e-3 后宣称原样复现。 |
| 初始本构 | 第 6、15 页称 linear isotropic + identity plasticity；第 20 页附录 E 却称 fixed corotated + identity | `visionlaw/config/physics/env/physics/templates/elastoplasticity.py` 实际为线性各向同性弹性表达式和 `F_corrected = F`；启动脚本使用该模板。本次遵循实际代码，保留论文内部表述差异。 |
| MPM 网格 | 合成 `32³`、真实 `70³`，重力 9.8 m/s²，第 15 页 | 对应 YAML 使用 `num_grids: 32/70` 和向下重力；不为了适配小显存自动降低网格。 |
| 合成帧数 | 每序列 400 帧，训练每 5 帧取一帧，第 15 页 | 例如 `finetune-bb.yaml` 的数据配置为 `nframes: 400`、`skip_frames: 5`。注意模拟步长与视频抽帧是不同配置项。 |
| 真实帧数 | Bun、Burger 各序列 19 帧，第 15 页 | 两份真实数据 YAML 的模拟及数据 `nframes` 均为 18。可能涉及初始帧的计数口径，尚未通过实际数据核实；本次不擅改。 |

## 完整实验的规模与评估

论文第 15 页包括 6 个合成场景（BouncyBall、JellyDuck、RubberPawn、ClayCat、HoneyBottle、SandFish）及 2 个真实场景（Bun、Burger）。合成场景各有 10 个视角，真实场景各有 3 个视角。论文每场景使用随机种子 **0、1、2、3、4**；全部 8 场景按此协议为 40 次场景/种子推断。`experiment/script/invent_constitutive_bilevel.py` 的 `range(5)` 会对选定场景依次启动这五个种子，不能把这一入口误认为单次轻量运行。

第 7 页 §4.1.3 使用真实粒子轨迹的 L2-Chamfer 距离衡量动力学一致性，使用 PSNR、SSIM、LPIPS 衡量视觉结果。拥有视频不等于具备全部粒子轨迹评估条件。第 9 页 §4.3.1 的“前 200 帧推断、后 200 帧预测”属于时间外推实验，不能默认当作所有实验的训练划分。

第 18 页表 2 的平均 **11,343 秒与 11,405 秒**来自第 10 页 §4.3.3 的五轮消融设置（4 轮交替加 1 轮联合），不是完整 4+3 轮搜索的统一耗时。不能据此承诺任意场景、其他 GPU 或全部 40 次推断在约三小时内完成。第 22 页 F 也指出大量前向仿真和反向参数优化会使搜索耗时；实际耗时与显存、数据、候选有效性和 API 延迟有关。

## 本次交付能证明什么

本次交付准备本地代码、数据路径工具、依赖安装脚本和服务器操作流程。静态语法、文件存在性、配置检查或依赖安装成功，只能证明相应准备步骤通过。它们不能证明 CUDA 扩展实际可用、数据完整可读、LLM 搜索成功、仿真稳定、显存足够或论文指标已复现。

后续应按“依赖安装与预检 → 数据与初始化资产核对 → 明确启动一个场景/种子 → 检查日志及产物 → 按论文协议扩展场景和种子 → 评估并记录差异”的顺序执行。前向渲染作者提供的 `physics.py`/检查点示例与从视频重新进行 LLM 本构搜索属于不同任务。只有完成实际实验并保存对应配置、版本、随机种子、日志和指标，才能报告运行或复现结果。
