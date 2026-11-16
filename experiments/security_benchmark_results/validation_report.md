# Full Validation Report

- Overall status: PASS
- Test command: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 tests/test_all_modules.py`
- Test return code: 0
- Test elapsed: 0.94s
- Benchmark command: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 experiments/run_security_benchmark.py`
- Benchmark return code: 0
- Benchmark elapsed: 1.71s

## Benchmark Highlights

- QKD Eve detection rate: 100.0%
- QKD normal/eavesdropping error: 0.00% / 20.79%
- QDP epsilon=1 attack success rate: 0.0%
- Adaptive MPO communication saving: 92.32%
- Five-seed baseline test accuracy: 90.13% ± 1.63%
- Five-seed proposed test accuracy: 91.53% ± 0.98%
- Proposed vs baseline accuracy delta: +1.40%
- Proposed/baseline final loss: 0.266 / 0.322
- Proposed average communication saving: 23.54%
- Validation-only model selection: {'validation_boundary': '每个客户端前80%样本用于训练、后20%用于验证；300条外部测试样本不参与配置选择。', 'validation_seeds': [121, 122, 123, 124, 125], 'minimum_avg_communication_saving_pct': 20.0, 'selected_config': {'aggregation_method': 'fedavg', 'learning_rate': 0.7, 'qdp_clip_norm': 1.0, 'mpo_max_reconstruction_error': 0.0015, 'compression_error_feedback': True}, 'validation_baseline_final_accuracy': 90.25, 'validation_baseline_final_accuracy_std': 3.2, 'validation_proposed_final_accuracy': 91.5, 'validation_proposed_final_accuracy_std': 1.66, 'validation_proposed_avg_communication_saving_pct': 23.06}
- Ablation controls: 四组控制消融统一使用 FedAvg、学习率 0.5 和训练种子 123；优化方案仍使用 FedAvg，并加入 MPO 误差反馈与验证集选定的学习率 0.7。
- Median/Krum poisoning reduction: 94.6% / 95.0%

## Test Output Tail

```text
        └─ 平均梯度传输大小(KB): 1.66
        └─ 参数更新范数: 0.014238
  [32m✓[0m T19 联邦学习隐私预算                                       PASS       联邦学习轮次正确记录隐私预算
        └─ 噪声注入次数: 5
        └─ 预算已用: 0.9608
        └─ 预算剩余: 9.0392
        └─ 轮次记录剩余预算: 9.0392
  [32m✓[0m T20 联邦学习异常输入                                       PASS       异常输入均抛出明确 ValueError
        └─ 客户端数量: 客户端数量不匹配: 期望 2, 实际 1
        └─ 特征维度: client 0 特征维度不匹配: 期望 4, 实际 5
        └─ 标签越界: client 0 标签越界: 标签必须在 [0, 2] 范围内
  [32m✓[0m T24 联邦学习K折交叉验证                                     PASS       k折交叉验证结果结构与准确率统计正常
        └─ 折数: 5
        └─ 平均准确率(%): 47.002
        └─ 准确率标准差(%): 13.3912
        └─ 逐折准确率(%): [65.0, 61.67, 36.67, 36.67, 35.0]
  [32m✓[0m T22 MPO自适应跳过                                       PASS       小模型在误差阈值下自动跳过不划算压缩
        └─ 是否压缩: False
        └─ 跳过原因: compression_not_beneficial
        └─ 最佳候选节省率(%): 71.28
        └─ 最佳候选误差: 0.04562707
  [32m✓[0m T25 MPO压缩误差反馈                                      PASS       压缩残差已保存，可在下一轮更新中补偿
        └─ 聚合方式: fedavg
        └─ 通信节省(%): 71.28
        └─ 残差范数: [0.51700629, 0.40297009, 0.43714727]
  [32m✓[0m T23 鲁棒聚合抗毒化                                        PASS       鲁棒聚合显著降低恶意梯度影响
        └─ FedAvg扰动范数: 8.8456
        └─ Median扰动范数: 0.4797
        └─ Krum扰动范数: 0.4454
  [32m✓[0m T10 区块链链结构                                         PASS       区块链链结构完整有效
        └─ 链长度: 4
        └─ 链验证: 有效
        └─ 最后区块哈希: 000a4775b8d819b5...
  [32m✓[0m T11 篡改检测                                           PASS       成功识别区块链数据篡改
        └─ 篡改前验证: 有效
        └─ 篡改后验证: 检测到篡改
        └─ 检测消息: 区块 1 PoW 验证失败
  [32m✓[0m T12 拜占庭共识                                          PASS       拜占庭共识成功识别恶意节点
        └─ 实际恶意节点: {4, 5}
        └─ 检测到恶意节点: {4, 5}
        └─ 识别准确率: 1.0
        └─ 共识达成: True
  [32m✓[0m T13 窃听攻击防护                                         PASS       窃听攻击被成功检测
        └─ 窃听检测: 成功
        └─ 误码率(%): 21.19
  [32m✓[0m T14 模型毒化防护                                         PASS       拜占庭共识成功识别毒化攻击
        └─ 识别恶意节点次数: 3
  [32m✓[0m T15 梯度泄漏防护                                         PASS       差分隐私有效抑制梯度泄漏攻击
        └─ 扫描ε点数: 6
        └─ 低ε隐私保护: 是
  [32m✓[0m T16 端到端系统集成                                        PASS       端到端系统集成成功
        └─ QKD通信: 正常
        └─ 区块链有效: 是
        └─ 训练轮次: 3
        └─ 最终准确率(%): 21.88

  总体评估: [32m✓[0m PASS
======================================================================

  所有核心测试通过
```

## Benchmark Output Tail

```text
[privacy] gradient leakage
    ε=  0.1: MSE=10.3319, 余弦相似度=-0.0130, 攻击率=0.0%, 防护✓
    ε=  0.5: MSE=0.5470, 余弦相似度=0.0797, 攻击率=0.0%, 防护✓
    ε=  1.0: MSE=0.2588, 余弦相似度=0.0874, 攻击率=0.0%, 防护✓
    ε=  3.0: MSE=0.1715, 余弦相似度=0.2273, 攻击率=0.0%, 防护✓
    ε=  5.0: MSE=0.1641, 余弦相似度=0.3893, 攻击率=0.0%, 防护✓
    ε= 10.0: MSE=0.1621, 余弦相似度=0.6373, 攻击率=43.3%, 防护✗
======================================================================
  安全基准与对照实验完成
======================================================================
  结果JSON: /Users/qx/Desktop/信息安全/QuantumSecureFL/experiments/security_benchmark_results/security_benchmark_results.json
  摘要报告: /Users/qx/Desktop/信息安全/QuantumSecureFL/experiments/security_benchmark_results/summary.md
  指标CSV: /Users/qx/Desktop/信息安全/QuantumSecureFL/experiments/security_benchmark_results/summary_metrics.csv
  消融CSV: /Users/qx/Desktop/信息安全/QuantumSecureFL/experiments/security_benchmark_results/ablation_results.csv
  K折CSV: /Users/qx/Desktop/信息安全/QuantumSecureFL/experiments/security_benchmark_results/kfold_results.csv
  图表目录: /Users/qx/Desktop/信息安全/QuantumSecureFL/experiments/security_benchmark_results/figures
======================================================================
```
