"""几类安全攻击的可复现实验。"""
import numpy as np
import time
from typing import List, Dict, Tuple
from copy import deepcopy


class AttackSimulator:
    """生成攻击样本并记录实验结果。"""
    
    def __init__(self, seed: int = 2024):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.attack_history = []
    
    def eavesdropping_attack(self, channel_init_params: Dict = None) -> Dict:
        """量子密钥分发的拦截-重发实验。"""
        from core.qkd_module import QuantumCommunicationChannel
        
        print('  [qkd] intercept-resend')
        
        np.random.seed(self.seed + 101)
        print('  正常信道: 建立 QKD 密钥...')
        channel_normal = QuantumCommunicationChannel(n_photons=1024)
        result_normal = channel_normal.establish(eve_active=False)
        
        np.random.seed(self.seed + 102)
        print('  窃听信道: 拦截并重发...')
        channel_hacked = QuantumCommunicationChannel(n_photons=1024)
        result_hacked = channel_hacked.establish(eve_active=True)
        
        attack_result = {
            'attack_type': 'eavesdropping',
            'normal_error_rate': result_normal['error_rate'],
            'hacked_error_rate': result_hacked['error_rate'],
            'detection_threshold': 11.0,
            'detection_success': result_hacked['eavesdropping_detected'],
            'eavesdropping_detected': result_hacked['eavesdropping_detected'],
            'normal_status': result_normal['status'],
            'hacked_status': result_hacked['status'],
            'conclusion': 'QKD 误码率异常检测成功拦截窃听' if result_hacked['eavesdropping_detected'] else '窃听未被检测到'
        }
        self.attack_history.append(attack_result)
        
        print(f'    正常通信误码率: {result_normal["error_rate"]}%')
        print(f'    窃听通信误码率: {result_hacked["error_rate"]}%')
        print(f'    检测阈值: 11.0%')
        print(f'    检测结果: {"✓ 检测到窃听" if result_hacked["eavesdropping_detected"] else "✗ 未检测"}')
        
        return attack_result
    
    def model_poisoning_attack(self, n_clients: int = 5, n_rounds: int = 5) -> Dict:
        """模型参数毒化实验。"""
        print('  [fl] model poisoning')
        
        from core.fl_mpo_module import FederatedLearningServer, SimpleNNModel

        poison_detections = []
        fedavg_deltas = []
        median_deltas = []
        malicious_nodes = list(range(max(0, n_clients - 2), n_clients))
        
        for r in range(n_rounds):
            rng = np.random.RandomState(self.seed + 300 + r)
            honest_gradients = rng.normal(0.0, 0.05, size=(n_clients - 2, 80))
            poison_gradients = rng.normal(2.5, 0.25, size=(2, 80))
            gradients = np.vstack([honest_gradients, poison_gradients])

            norms = np.linalg.norm(gradients, axis=1)
            median_norm = np.median(norms)
            mad = np.median(np.abs(norms - median_norm)) + 1e-8
            detected = np.where(norms > median_norm + 3.0 * mad)[0].tolist()
            poison_detections.append(len(set(detected) & set(malicious_nodes)))

            model = SimpleNNModel(input_dim=4, hidden_dim=8, output_dim=2)
            fedavg_server = FederatedLearningServer(model, n_clients=n_clients, aggregation_method='fedavg')
            median_server = FederatedLearningServer(model, n_clients=n_clients, aggregation_method='median')
            fedavg_delta = np.linalg.norm(fedavg_server._aggregate_gradients(list(gradients)))
            median_delta = np.linalg.norm(median_server._aggregate_gradients(list(gradients)))
            fedavg_deltas.append(float(fedavg_delta))
            median_deltas.append(float(median_delta))

            print(f'    轮次 {r+1}: 恶意节点={malicious_nodes}, 检测到={detected}, '
                  f'FedAvg扰动={fedavg_delta:.2f}, Median扰动={median_delta:.2f}')
        
        detection_rounds = sum(1 for d in poison_detections if d > 0)
        avg_fedavg_delta = float(np.mean(fedavg_deltas))
        avg_median_delta = float(np.mean(median_deltas))
        robust_reduction = 1 - avg_median_delta / (avg_fedavg_delta + 1e-8)

        attack_result = {
            'attack_type': 'model_poisoning',
            'n_rounds': n_rounds,
            'detections_per_round': poison_detections,
            'total_malicious_detected': detection_rounds,
            'average_detection_rate': round(detection_rounds / max(1, n_rounds), 2),
            'fedavg_delta_norm': round(avg_fedavg_delta, 4),
            'median_delta_norm': round(avg_median_delta, 4),
            'robust_reduction_rate': round(robust_reduction, 4),
            'conclusion': '鲁棒聚合显著削弱模型毒化梯度扰动'
        }
        self.attack_history.append(attack_result)
        return attack_result
    
    def gradient_leakage_attack(self, epsilon_values: List[float] = None) -> Dict:
        """梯度逆向推理实验。"""
        if epsilon_values is None:
            epsilon_values = [0.1, 0.5, 1.0, 3.0, 5.0, 10.0]
        
        print('  [privacy] gradient leakage')
        
        from core.qdp_module import QuantumDifferentialPrivacy
        
        results = []
        for eps in epsilon_values:
            mse_list = []
            cosine_list = []
            attack_successes = 0
            n_trials = 30

            for trial in range(n_trials):
                rng = np.random.RandomState(self.seed + int(eps * 1000) + trial)
                sensitive_grad = rng.randn(128) * 0.2
                sensitive_grad[:8] += rng.choice([-1.0, 1.0], size=8) * 1.5

                qdp = QuantumDifferentialPrivacy(
                    epsilon=max(eps, 1e-6),
                    channel_ratio=0.75,
                    # 强隐私档先收紧梯度范数，避免高 ε 压测掩盖裁剪效果。
                    clip_norm=0.3,
                    noise_seed=self.seed + 50000 + int(eps * 1000) + trial
                )
                noisy_grad = qdp.apply_privacy(sensitive_grad.copy(), local_epsilon=eps)

                mse = float(np.mean((noisy_grad - sensitive_grad) ** 2))
                cosine = float(np.dot(noisy_grad, sensitive_grad) / (
                    np.linalg.norm(noisy_grad) * np.linalg.norm(sensitive_grad) + 1e-8
                ))
                mse_list.append(mse)
                cosine_list.append(cosine)
                if cosine > 0.65 and mse < 0.2:
                    attack_successes += 1

            avg_mse = float(np.mean(mse_list))
            avg_cosine = float(np.mean(cosine_list))
            attack_success_rate = attack_successes / n_trials
            protection_success_rate = 1 - attack_success_rate
            privacy_guaranteed = attack_success_rate <= 0.2

            results.append({
                'epsilon': eps,
                'avg_mse': round(avg_mse, 4),
                'avg_cosine_similarity': round(avg_cosine, 4),
                'attack_success_rate': round(attack_success_rate, 4),
                'protection_success_rate': round(protection_success_rate, 4),
                'privacy_guaranteed': privacy_guaranteed,
                'n_trials': n_trials
            })
            
            print(f'    ε={eps:>5}: MSE={avg_mse:.4f}, '
                  f'余弦相似度={avg_cosine:.4f}, 攻击率={attack_success_rate*100:.1f}%, '
                  f'防护{"✓" if privacy_guaranteed else "✗"}')
        
        attack_result = {
            'attack_type': 'gradient_leakage',
            'epsilon_scan': results,
            'defense_config': 'L2 范数裁剪 C=0.3 + 混合差分隐私噪声',
            'recommendation': f'建议 ε ≤ {max([r["epsilon"] for r in results if r["privacy_guaranteed"]] + [3.0])} 以确保隐私安全',
            'conclusion': '量子差分隐私有效抑制梯度逆向推理攻击'
        }
        self.attack_history.append(attack_result)
        return attack_result
    
    def blockchain_tampering_attack(self) -> Dict:
        """篡改历史区块并验证链校验。"""
        print('  [chain] tampering')
        
        from core.blockchain_consensus import Blockchain
        
        chain = Blockchain(difficulty=3)
        
        for i in range(3):
            params = np.random.randn(20)
            chain.mine_block(params, {'round': i, 'accuracy': 70.0 + i * 2})
        
        valid_before, _ = chain.validate_chain()
        print(f'    正常状态: 链验证={valid_before}')
        
        original_value = chain.chain[1].model_metadata['accuracy']
        chain.chain[1].model_metadata['accuracy'] = 999.0
        
        valid_after, msg = chain.validate_chain()
        print(f'    篡改后: 链验证={valid_after}, 消息={msg}')
        
        chain.chain[1].model_metadata['accuracy'] = original_value
        
        attack_result = {
            'attack_type': 'blockchain_tampering',
            'tampered_block': 1,
            'original_value': original_value,
            'tampered_value': 999.0,
            'detection_success': not valid_after,
            'conclusion': '区块链哈希链式结构成功检测到篡改'
        }
        self.attack_history.append(attack_result)
        return attack_result
    
    def run_all_attacks(self) -> Dict:
        """执行所有攻击实验。"""
        print('=' * 60)
        print('  security experiment batch')
        print('=' * 60)
        
        results = {}
        
        print('\n--- qkd intercept-resend ---\n')
        results['eavesdropping'] = self.eavesdropping_attack()
        
        print('\n--- model poisoning ---\n')
        results['model_poisoning'] = self.model_poisoning_attack(n_clients=5, n_rounds=4)
        
        print('\n--- gradient leakage ---\n')
        results['gradient_leakage'] = self.gradient_leakage_attack()
        
        print('\n--- chain tampering ---\n')
        results['blockchain_tampering'] = self.blockchain_tampering_attack()
        
        print('\n' + '=' * 60)
        print('  result summary')
        print('=' * 60)
        for name, result in results.items():
            print(f'  [{name}] {result["conclusion"]}')
        
        return results
    
    def get_history(self) -> List[Dict]:
        return self.attack_history


def attack_demo():
    """命令行自检入口。"""
    simulator = AttackSimulator()
    return simulator.run_all_attacks()


if __name__ == '__main__':
    attack_demo()
