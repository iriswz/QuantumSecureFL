# Security Benchmark Summary

## Key Results

- QKD Eve detection rate: 100.0%
- QKD normal/eavesdropping error: 0.00% / 20.79%
- QDP epsilon=1.0 attack success rate: 0.0%
- Adaptive MPO communication saving: 92.32%
- Five-seed baseline test accuracy: 90.13% ± 1.63%
- Five-seed proposed test accuracy: 91.53% ± 0.98%
- Proposed accuracy gain vs baseline: +1.40 percentage points
- Proposed average communication saving: 23.54%
- Validation-only selection: 91.50% vs 90.25% with test data excluded
- Comparison controls: 四组控制消融统一使用 FedAvg、学习率 0.5 和训练种子 123；优化方案仍使用 FedAvg，并加入 MPO 误差反馈与验证集选定的学习率 0.7。
- 5-fold Secure FL accuracy: 90.27% ± 1.93%
- Median/Krum poisoning reduction: 94.6% / 95.0%

## Generated Figures

- `figures/qkd_error_rates.png`
- `figures/qdp_attack_success.png`
- `figures/mpo_communication_saving.png`
- `figures/fl_training_curves.png`
- `figures/ablation_study.png`
- `figures/robust_aggregation.png`
