# 量子安全联邦学习通信系统

本项目面向多方数据协作场景，构建了一个量子密钥分发、差分隐私、模型压缩、拜占庭共识与区块链记录相结合的联邦学习安全通信原型系统。系统通过软件仿真实现核心流程，用于验证通信加密、隐私保护、参数传输优化和训练记录防篡改等功能。

## 功能模块

| 模块 | 文件 | 说明 |
|------|------|------|
| 量子密钥分发与加密 | `core/qkd_module.py` | BB84 协议仿真、误码率检测、QKD 会话密钥派生与 HMAC 载荷认证 |
| 差分隐私保护 | `core/qdp_module.py` | 梯度裁剪、混合噪声注入、隐私预算管理 |
| 联邦学习与压缩 | `core/fl_mpo_module.py` | 两层 MLP、FedAvg/鲁棒聚合、MPO 参数压缩 |
| 共识与链式记录 | `core/blockchain_consensus.py` | 参数哈希、轻量 PoW、拜占庭节点检测 |
| 攻防实验 | `core/attack_module.py` | 窃听、模型毒化、梯度泄漏、链上篡改实验 |
| 真实医疗数据 | `core/medical_data.py` | 下载并预处理 UCI 101,766 条糖尿病住院记录，按患者划分五医院数据孤岛 |
| 五医院场景 | `medical_federated_demo.py` | 单医院/普通联邦/四层安全联邦三组对照并生成可复核结果 |
| 小型真实语音数据 | `core/parkinson_data.py` | UCI Parkinson 756 条录音，按受试者无泄漏划分并构造五机构孤岛 |
| 四层优势对照 | `parkinson_federated_demo.py` | 干净/投毒 FedAvg、梯度反演、MPO、共识与链上存证一体化实验 |
| 邮件与金融数据 | `core/small_scenario_data.py` | UCI Spambase 与台湾企业破产数据的下载、标准化和五机构非IID划分 |
| 多领域真实场景 | `multidomain_federated_demo.py` | 邮件网关和金融风控的四层安全联邦对照与结果导出 |

## 项目结构

```text
QuantumSecureFL/
├── main.py                         # PyQt 图形界面入口
├── medical_federated_demo.py       # 真实医疗数据五医院端到端演示
├── parkinson_federated_demo.py     # 小型真实语音数据四层优势对照
├── multidomain_federated_demo.py   # 邮件/金融两个真实数据场景
├── quick_demo.py                   # 快速自检脚本
├── scientific_simulation.py         # 端到端仿真脚本
├── requirements.txt                # pip 依赖
├── environment.yml                 # conda 环境配置
├── README.md
├── core/                           # 核心模块
├── tests/                          # 测试脚本
├── experiments/                    # 实验与指标脚本
├── scripts/                        # 验证脚本
└── docs/                           # 架构图与说明材料
```

## 环境安装

推荐使用 Python 3.9 及以上版本。

```bash
cd QuantumSecureFL
pip install -r requirements.txt
```

也可以使用 conda：

```bash
conda env create -f environment.yml
conda activate quantum-secure-fl
```

本项目不依赖真实量子硬件，QKD、量子噪声和量子拜占庭共识相关流程均为软件仿真。

## 运行方式

启动图形界面：

```bash
python main.py
```

运行命令行模式：

```bash
python main.py --cli
```

快速检查核心模块：

```bash
python quick_demo.py
```

运行完整测试：

```bash
python tests/test_all_modules.py
```

生成安全基准实验结果：

```bash
python experiments/run_security_benchmark.py
```

一键验证测试与基准实验：

```bash
python scripts/run_full_validation.py
```

运行真实医疗数据的五医院场景（首次运行自动从 UCI 下载约 3 MB 压缩包）：

```bash
python medical_federated_demo.py
```

快速验证或自定义实验：

```bash
python medical_federated_demo.py --rounds 5 --batch-size 256
python medical_federated_demo.py --rounds 100 --malicious-hospital 4 --local-epsilon 0.5 --bond-dim 16
```

结果写入 `artifacts/medical_demo/medical_federated_results.json` 和
`artifacts/medical_demo/training_history.csv`。数据来源、许可、患者级划分方法见
[`data/README.md`](data/README.md)。

运行约 3 MB 的小型 UCI Parkinson 语音数据实验：

```bash
python parkinson_federated_demo.py
```

该脚本固定使用受试者级训练/测试划分，比较单机构、干净 FedAvg、遭投毒
FedAvg 和同一投毒条件下的四层安全方案；还会执行梯度反演探针并记录通信、
恶意节点检测和区块链指标。默认结果写入 `artifacts/parkinson_demo/`。

运行邮件网关与金融机构两个小型真实场景：

```bash
python multidomain_federated_demo.py spam
python multidomain_federated_demo.py bankruptcy
```

默认分别下载约 128 KB 的 Spambase 压缩包和约 4.6 MB 的台湾企业破产数据，
执行与 Parkinson 场景相同的干净/投毒/四层安全公平对照。结果分别写入
`artifacts/spam_demo/` 和 `artifacts/bankruptcy_demo/`。

## 图形界面说明

图形界面包含 7 个页面：

1. QKD 通信：建立安全信道，并对比正常通信与窃听场景下的误码率。
2. 隐私防护：调节隐私预算和噪声比例，观察隐私预算消耗与效用变化。
3. 联邦学习：读取已验证的训练曲线、MPO 压缩和 5 折结果；恶意节点数可手动设为 0、1 或 2，投毒对照会按当前配置现场计算 FedAvg、Median 和 Krum 的更新偏移。
4. 拜占庭共识：手动调整 4–10 个共识节点、恶意节点数和签名长度，展示节点支持率、恶意节点识别和 1/3 容错边界。
5. 区块链篡改：对真实哈希链执行直接修改、单块重挖和后续整段重挖，验证 PoW、链接及检查点防护。
6. 攻防实验：集中运行窃听、模型毒化、梯度泄漏和链上篡改实验。
7. 真实数据集：在同一页面同时展示医疗 Parkinson 语音、邮件垃圾信息识别和金融企业破产预警三个场景，三者共用一段安全联合训练动画，完成后统一展示四层防护对照结果。

为方便没有量子计算背景的观众理解，界面将关键数据流改为分阶段的白话流程观测：

- QKD 页动态展示光子传输、Eve 拦截、测量基比对与 QBER 判定。
- 隐私页展示「原始梯度 → 限幅裁剪 → 注入噪声 → 安全更新」。
- 联邦学习页展示「本地训练 → 上传更新 → 异常筛查 → 聚合 → 上链」。
- 攻防页会根据攻击类型，动态切换到 QKD、差分隐私、鲁棒聚合或区块哈希防线。
- 医疗、邮件和金融数据在同一页面共用一段五步安全联合训练动画，并明确区分「原始数据」与「模型更新」。
- 三个真实数据集的结果在一张统一对照表和联合图表中展示，同时报告投毒后效用恢复、MPO 载荷节省与恶意轮次识别率。

所有页面均在点击主操作按钮后开始流程观测，过程结束前保持结果区为空，结束后再一次性展示结果。拜占庭共识页和链上篡改页在动画前保留固定的结果画布并显示「暂无结果」，执行时显示「加载中……」，动画完成后再将原有结果图与证据加载到同一区域。流程不会自动播放或循环播放，界面也不再提供独立重播按钮。

联邦学习页的标准训练与 5 折结果来自
`experiments/security_benchmark_results/security_benchmark_results.json`。页面打开时保持待开始状态，
「开始标准联邦学习」「恶意节点注入」和「运行5折验证」均在流程结束后切换到对应数据视图。
「训练参数」中的恶意节点选项支持无投毒、1 个容错内节点和 2 个超出 1/3 容错界限的压力测试；主训练按钮与恶意节点快捷按钮都会读取该选择。
如果文件缺失或格式错误，界面会显示读取失败，并且不会回退到现场训练。

真实数据集页打开时同时展示医疗、邮件和金融三张数据卡，结果区保持为空；点击「开始三类数据联合验证」后只播放一段共用安全聚合动画，结束后再一次性读取 `artifacts/` 中三个场景的固定结果，不启动现场训练进程。

## 测试与实验

`tests/test_all_modules.py` 覆盖以下内容：

- QKD 密钥生成、窃听检测、加解密一致性
- 差分隐私噪声注入、预算消耗、效用权衡
- MPO 压缩率、重构误差、解压缩一致性
- 联邦学习训练、鲁棒聚合、异常输入处理
- 区块链哈希验证、篡改检测、拜占庭共识
- 攻防实验与端到端流程
- Parkinson 受试者级数据划分、梯度反演防护与真实场景 GUI 加载

`experiments/run_security_benchmark.py` 会生成实验数据、CSV 指标表和图表，输出位置为：

```text
experiments/security_benchmark_results/
```

主要输出包括：

- `security_benchmark_results.json`
- `summary_metrics.csv`
- `kfold_results.csv`
- `summary.md`
- `figures/`

## 关键参数

| 参数 | 位置 | 说明 |
|------|------|------|
| 光子数量 | QKD 模块 | 影响密钥筛选样本量与误码率估计稳定性 |
| 窃听检测阈值 | QKD 模块 | 默认按 11% 误码率判断异常 |
| 隐私预算 epsilon | QDP 模块 | 数值越小，隐私保护越强，噪声影响越大 |
| 信道噪声比例 | QDP 模块 | 控制 Laplace 与 Gaussian 噪声混合比例 |
| MPO 键维度 | 联邦学习模块 | 控制压缩率与重构误差 |
| 聚合方法 | 联邦学习模块 | 支持 FedAvg、Median、Trimmed Mean、Krum |
| 区块链难度 | 链式记录模块 | 控制轻量 PoW 的前导零数量 |
| 恶意节点数 | 共识模块 | 用于测试拜占庭节点检测效果 |

## 实验说明

图形界面的联邦学习页默认读取预计算基准结果，避免现场训练导致卡顿或随机波动；
QKD、隐私与攻防页使用软件仿真。`medical_federated_demo.py` 使用真实公开医疗记录。
固定合成消融中，Baseline、MPO-only、QDP-only 和 QDP+MPO 四组均使用
FedAvg、学习率 0.5 和训练种子 123；QDP 噪声种子固定为 42。
完整方法仍使用 FedAvg，但为 MPO 加入压缩误差反馈：本轮丢失的重构残差会在下一轮补偿。
学习率 0.7、QDP 裁剪范数 1.0 和 MPO 误差阈值 0.0015 仅使用客户端内部验证集选定，
外部测试集不参与调参；最终对比报告 5 个随机种子的测试均值与标准差。
Median/Krum 不混入该消融表，而是在相同投毒更新下与 FedAvg 进行独立鲁棒聚合对照。
真实数据演示完成以下闭环：

1. 按患者划分测试集，确保同一患者不跨训练/测试集；训练患者再划为 5 个虚拟医院。
2. 每家医院本地计算梯度，原始病历从不离开本地数据孤岛。
3. 梯度经过裁剪与混合噪声、MPO 压缩、QKD 会话密钥派生的认证加密后传输。
4. 模拟恶意医院提交反向放大的梯度，签名投票识别后由鲁棒聚合器处理。
5. 每轮模型摘要、参与方提交哈希和共识签名写入链式账本。
6. 在同一患者级留出集上对照单医院、普通 FedAvg 与完整安全方案。

重要边界：本项目的 BB84、量子噪声和量子签名均为软件仿真；QDP 模块用于研究隐私—效用权衡，不构成经形式化审计的生产级 DP 保证。模型预测的是 30 日再入院风险，不是临床诊断结论。真实部署仍需量子硬件/可信网络、标准认证加密、正式隐私会计、医疗合规审查和外部临床验证。

## 适用场景

- 金融机构之间的联合风控建模
- 医疗机构之间的隐私保护协同训练
- 边缘设备的分布式模型训练
- 工业物联网中的多节点安全协作

## 作品信息

- 作品名称：量子安全联邦学习通信系统
- 技术栈：Python、NumPy、PyQt5、Matplotlib
- 主要方向：量子安全通信、差分隐私、联邦学习、区块链记录、攻防实验
