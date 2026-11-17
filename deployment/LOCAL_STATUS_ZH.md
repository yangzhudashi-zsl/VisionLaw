# 本次本地准备状态

核对日期：2026-11-17。当前工作区为 `D:\work-codex\VisionLaw\code`。没有启动 VisionLaw，也没有请求 LLM。

| 项目 | 实际状态 |
| --- | --- |
| 官方代码 | 已从你的 `yangzhudashi-zsl/VisionLaw` 仓库克隆；初始提交与官方 main 一致：`a35e14ae4d3402b53037aeafef45b66c99097f8e`。保留上游提交历史。 |
| 本机硬件 | `nvidia-smi` 只读查询显示 RTX 3060 Laptop，6144 MiB，驱动 576.88；磁盘 D 初始可用约 670GB。未做性能/显存测试。 |
| Windows 工具环境 | 已创建 `.envs/visionlaw`，Python 3.10.22，安装 PyYAML 6.0.2；`pip check` 通过。只用于配置生成、数据路径检查、命令预览。 |
| 完整运行环境 | **未安装为原生 Windows 运行环境**。官方导入使用 Unix `fcntl`，本次不做 Windows 移植、不装 WSL；Linux 安装脚本供服务器使用，尚未在 Linux GPU 执行。 |
| 扩展源码 | 已下载 Gaussian Splatting `b17ded92b56ba02b6b7eaba2e66a2b0510f27764`；diff-gaussian-rasterization `59f5f77e3ddbac3ed9db93ec2cfe99ed6c5d121d`；simple-knn `44f764299fa305faf6ec5ebd99939e0508331503`；GLM `5c46b9c07008ae65cb81ab79cd677ecc1934b903`。未编译、未导入，不下载 SIBR 查看器。 |
| 配置 | 八场景本机配置已生成于 `deployment/configs/`，未纳入 Git；服务器必须重新生成其绝对路径。官方原始 YAML 保持不变。 |
| 外部数据/资产 | **未下载** NeuMA/真实数据、重建核、绑定和粒子资产；官方初始化 `experiment/ckpt/*/init.pt` 已随仓库存在，未加载其内容。 |
| 数据预检 | 对当前缺数据的 bb 配置检查，正确报告缺图像、相机 JSON、核、绑定、粒子及网格。报告在 `deployment/reports/bb-data-check.json`。这不是数据通过验证。 |
| API 密钥 | 未读取、填写或调用；后续服务器通过环境变量输入。 |
| 验证 | 150 份项目及部署 Python 文件 AST 语法解析通过；Bash/PowerShell 脚本语法检查、Git 空白检查通过；配置与数据预检工具使用合成文件布局检查过成功/缺失/防覆盖分支；命令预览没有启动项目。 |
| 实验 | **未训练、未仿真、未渲染、未评估，不声称复现成功。** |

部署改动为独立 `deployment/` 文件和真实场景渲染视角修复；前向渲染现在保留 YAML 中的 `d_0` 或 `r_1`。依赖清单解决上游 PyVista 双版本冲突并补上直接导入依赖。生成配置修正 ClayCat 网格路径和 `sort: null` 转换问题。单种子启动工具默认只预览，显式 `--execute` 后才会执行。

服务器仍须完成：租用合适 Linux GPU → 安装/编译完整依赖 → 下载并整理数据与资产 → 生成服务器配置并预检 → 自行输入 API key → 开始实际实验。操作命令见 [README_ZH.md](README_ZH.md)。
