"""端到端仿真脚本。"""
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.scientific_qkd import ScientificBB84Simulator
from core.scientific_qdp import QuantumDifferentialPrivacy
from core.scientific_mpo import ScientificMPOCompressor
from core.scientific_byzantine import QuantumByzantineConsensus
from core.scientific_attack import ScientificAttackTester


def run_complete_simulation():
    """运行端到端仿真。"""
    print('=' * 80)
    print('  Quantum secure FL simulation')
    print('=' * 80)
    
    print('\n' + '=' * 80)
    print('  【阶段1】BB84量子密钥分发协议')
    print('=' * 80)
    
    print('\n[场景A] 正常通信（无窃听）')
    qkd_normal = ScientificBB84Simulator(n_photons=2048)
    result_normal = qkd_normal.run_protocol(eve_active=False)
    
    print(f'  光子数: {result_normal["n_photons"]}')
    print(f'  匹配比特数: {result_normal["matched_bits"]}')
    print(f'  误码率: {result_normal["error_rate"]}%')
    print(f'  最终密钥: {result_normal["final_key"][:32]}...')
    print(f'  状态: {"✓ 成功" if result_normal["status"] == "success" else "✗ 失败"}')
    
    print('\n[场景B] Eve中间人窃听攻击')
    qkd_eve = ScientificBB84Simulator(n_photons=2048)
    result_eve = qkd_eve.run_protocol(eve_active=True)
    
    print(f'  光子数: {result_eve["n_photons"]}')
    print(f'  匹配比特数: {result_eve["matched_bits"]}')
    print(f'  误码率: {result_eve["error_rate"]}%')
    print(f'  检测到窃听: {"✓ 是" if result_eve["eavesdropping_detected"] else "✗ 否"}')
    print(f'  状态: {"✗ 中止" if result_eve["eavesdropping_detected"] else "✓ 成功"}')
    
    print('\n' + '=' * 80)
    print('  【阶段2】量子差分隐私保护')
    print('=' * 80)
    
    qdp = QuantumDifferentialPrivacy(epsilon=5.0, channel_ratio=0.65)
    print(f'\n初始化参数: ε={qdp.budget.epsilon}, δ={qdp.budget.delta}')
    print(f'噪声混合: 信道噪声{qdp.channel_ratio*100:.0f}% + 测量噪声{(1-qdp.channel_ratio)*100:.0f}%')
    
    print('\n[梯度隐私保护过程]')
    for i in range(5):
        grad = np.random.randn(100) * 0.5
        noisy_grad = qdp.apply_privacy(grad, epsilon=0.8)
        
        noise_info = qdp.noise_history[-1]
        print(f'  轮次{i+1}: SNR={noise_info["signal_to_noise_ratio"]:.2f}, '
              f'剩余预算={noise_info["budget_remaining"]:.2f}, '
              f'等级={qdp.get_privacy_report()["privacy_level"]}')
    
    print('\n' + '=' * 80)
    print('  【阶段3】MPO矩阵乘积算符压缩')
    print('=' * 80)
    
    np.random.seed(42)
    weights = np.random.randn(32, 64, 16)
    print(f'\n原始模型参数: 形状={weights.shape}, 参数数={weights.size}')
    
    mpo = ScientificMPOCompressor()
    tradeoff = mpo.analyze_compression_tradeoff(weights, ranks=[2, 4, 8, 16])
    
    print('\n[压缩率-误差权衡]')
    print(f'  {"秩R":>6} | {"压缩率(%)":>12} | {"重建误差":>12}')
    print(f'  {"-"*8} | {"-"*12} | {"-"*12}')
    for i in range(len(tradeoff['rank'])):
        print(f'  {tradeoff["rank"][i]:>6} | '
              f'{tradeoff["compression_ratio"][i]:>12.2f} | '
              f'{tradeoff["reconstruction_error"][i]:>12.2e}')
    
    print('\n' + '=' * 80)
    print('  【阶段4】量子拜占庭共识')
    print('=' * 80)
    
    byz = QuantumByzantineConsensus(n_nodes=5, n_malicious=1)
    result = byz.run_consensus(b'federated_gradient_update')
    
    print(f'\n[共识结果]')
    print(f'  节点数: {byz.n_nodes}, 恶意节点数: {byz.n_malicious}')
    print(f'  共识值: {result["consensus_value"]}')
    print(f'  检测到恶意节点: {result["malicious_nodes_detected"]}')
    print(f'  检测准确率: {result["detection_accuracy"] * 100:.2f}%')
    print(f'  共识达成: {"✓ 是" if result["consensus_reached"] else "✗ 否"}')
    
    print('\n' + '=' * 80)
    print('  【阶段5】攻防对抗测试')
    print('=' * 80)
    
    attacker = ScientificAttackTester(seed=42)
    attack_results = attacker.run_all_attacks()
    
    print(f'\n[攻防测试结果]')
    print(f'  {"攻击类型":<20} | {"攻击强度":>8} | {"防护成功率":>10} | {"攻击成功率":>10}')
    print(f'  {"-"*20} | {"-"*8} | {"-"*10} | {"-"*10}')
    for r in attack_results:
        print(f'  {r.attack_name:<20} | {r.attack_strength:>8.2f} | '
              f'{r.protection_success_rate * 100:>9.2f}% | '
              f'{r.success_probability * 100:>9.2f}%')
    
    print(f'\n[关键指标说明]')
    print(f'  • 量子窃听检测率: {attack_results[0].details["检测率(%)"]:.2f}% (漏检率 {attack_results[0].details["漏检率(%)"]:.2f}%)')
    print(f'  • 模型毒化防护率: {attack_results[1].protection_success_rate * 100:.2f}% (攻击成功率 {attack_results[1].success_probability * 100:.2f}%)')
    print(f'  • 梯度逆向防护率: {attack_results[2].protection_success_rate * 100:.2f}% (平均还原质量 {attack_results[2].details["平均还原质量"]:.4f})')
    print(f'  • 区块链篡改防护率: {attack_results[3].protection_success_rate * 100:.2f}% (篡改成功率 {attack_results[3].success_probability * 100:.4f}%)')
    
    print('\n' + '=' * 80)
    print('  【综合分析】量子安全联邦学习完整链路')
    print('=' * 80)
    
    print("""

┌─────────────────────────────────────────────────────────────────────────────┐
│                    量子安全联邦学习完整链路                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 1: QKD通信加密                                                      │
│    └─ BB84协议 → 256位量子密钥 → 信息论安全                                  │
│    └─ 误码率阈值11%检测窃听                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 2: 量子差分隐私                                                      │
│    └─ ε-差分隐私保证 → 可量化隐私预算                                        │
│    └─ 信道噪声+测量噪声混合注入                                             │
│    └─ 梯度裁剪控制敏感度                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 3: MPO张量压缩                                                       │
│    └─ 矩阵乘积算符分解 → 压缩率>60%                                         │
│    └─ SVD截断控制重建误差                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Layer 4: 量子拜占庭共识                                                    │
│    └─ 量子签名不可伪造                                                      │
│    └─ 容忍1/3恶意节点                                                      │
│    └─ 分布式一致性保证                                                      │
└─────────────────────────────────────────────────────────────────────────────┘

核心技术指标汇总：
─────────────────────────────────────────────────────────────────────────────
QKD密钥分发:     256位 | 误码率<1%(正常) | 误码率>28%(窃听)
差分隐私:        ε=0.1~10可调 | 混合噪声模型 | 预算可追踪
MPO压缩:         D=2~32可调 | 压缩率>90%(D=2) | 误差可控
拜占庭共识:      n≥3t+1 | 检测准确率100% | 信息论安全
─────────────────────────────────────────────────────────────────────────────

物理原理总结：
─────────────────────────────────────────────────────────────────────────────
1. 量子不可克隆定理 → QKD安全性基础
2. 量子测量概率性 → 差分隐私噪声来源
3. 张量网络理论 → MPO压缩数学基础
4. 拜占庭容错理论 → 分布式共识保证
─────────────────────────────────────────────────────────────────────────────
    """)
    
    print('=' * 80)
    print('  科学仿真演示完成')
    print('=' * 80)


if __name__ == '__main__':
    run_complete_simulation()
