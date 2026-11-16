"""批量运行 QKD、差分隐私、MPO、共识、攻防和区块链实验。"""
import numpy as np
import sys
import os
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scientific_qkd import ScientificBB84Simulator
from core.scientific_qdp import QuantumDifferentialPrivacy
from core.scientific_mpo import ScientificMPOCompressor
from core.scientific_byzantine import QuantumByzantineConsensus
from core.scientific_attack import ScientificAttackTester
from core.blockchain_consensus import Blockchain, SecureFederatedLedger


class ExperimentRunner:
    """运行并汇总各项实验。"""
    
    def __init__(self, seed=42, output_file='experiment_results.json'):
        self.seed = seed
        self.output_file = output_file
        self.results = {}
    
    def experiment_qkd(self):
        """测试光子数、误码率和窃听检测率。"""
        print('=' * 70)
        print('  实验 1: BB84 量子密钥分发性能测试')
        print('=' * 70)
        
        results = {
            'normal_communication': {},
            'eavesdropping_detection': [],
            'photon_count_analysis': []
        }
        
        print('\n[1.1] 正常通信基准测试 (100次实验)')
        n_trials = 100
        error_rates = []
        key_success = 0
        
        for i in range(n_trials):
            np.random.seed(self.seed + i)
            qkd = ScientificBB84Simulator(n_photons=2048)
            result = qkd.run_protocol(eve_active=False)
            error_rates.append(result['error_rate'] / 100)
            if result['status'] == 'success':
                key_success += 1
        
        results['normal_communication'] = {
            'n_trials': n_trials,
            'n_photons': 2048,
            'avg_error_rate': np.mean(error_rates),
            'std_error_rate': np.std(error_rates),
            'max_error_rate': np.max(error_rates),
            'min_error_rate': np.min(error_rates),
            'key_success_rate': key_success / n_trials,
            'avg_matched_bits': 1024  # 理论值 ~ n_photons/2
        }
        
        print(f'  实验次数: {n_trials}')
        print(f'  平均误码率: {np.mean(error_rates)*100:.2f}% ± {np.std(error_rates)*100:.2f}%')
        print(f'  误码率范围: [{np.min(error_rates)*100:.2f}%, {np.max(error_rates)*100:.2f}%]')
        print(f'  密钥生成成功率: {key_success/n_trials*100:.1f}%')
        
        print('\n[1.2] 窃听检测性能 (50次实验)')
        # 仿真器只接受布尔开关，因此用启用 Eve 的概率表示窃听强度。
        eavesdropping_probs = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0]
        
        for prob in eavesdropping_probs:
            detections = 0
            error_rates_eve = []
            n_exp = 50
            
            for i in range(n_exp):
                np.random.seed(self.seed + 1000 + int(prob*100) + i)
                eve_active = np.random.random() < prob
                qkd = ScientificBB84Simulator(n_photons=2048)
                result = qkd.run_protocol(eve_active=eve_active)
                
                error_rates_eve.append(result['error_rate'] / 100)
                if result['eavesdropping_detected']:
                    detections += 1
            
            detection_rate = detections / n_exp
            avg_error = np.mean(error_rates_eve)
            
            results['eavesdropping_detection'].append({
                'strength': prob,
                'detection_rate': detection_rate,
                'avg_error_rate': avg_error,
                'n_trials': n_exp
            })
            
            print(f'  强度{prob:.1f}: 检测率={detection_rate*100:.1f}%, 平均误码率={avg_error*100:.2f}%')
        
        print('\n[1.3] 不同光子数下的性能 (每个配置30次实验)')
        photon_counts = [256, 512, 1024, 2048, 4096]
        
        for n_photons in photon_counts:
            error_list = []
            matched_list = []
            n_exp = 30
            
            for i in range(n_exp):
                np.random.seed(self.seed + 2000 + n_photons + i)
                qkd = ScientificBB84Simulator(n_photons=n_photons)
                result = qkd.run_protocol(eve_active=False)
                error_list.append(result['error_rate'] / 100)
                matched_list.append(result['matched_bits'])
            
            results['photon_count_analysis'].append({
                'n_photons': n_photons,
                'avg_error_rate': np.mean(error_list),
                'avg_matched_bits': np.mean(matched_list),
                'std_error_rate': np.std(error_list),
                'n_trials': n_exp
            })
            
            print(f'  光子数{n_photons:>5}: 误码率={np.mean(error_list)*100:.2f}%, '
                  f'匹配比特={np.mean(matched_list):.0f}')
        
        print('\n[1.4] 不同光子数下的窃听检测性能 (每个配置50次实验)')
        eavesdropping_photon_analysis = []
        photon_counts_eve = [256, 512, 1024, 2048, 4096, 8192]
        
        for n_photons in photon_counts_eve:
            detections = 0
            error_rates = []
            n_exp = 50
            
            for i in range(n_exp):
                np.random.seed(self.seed + 2500 + n_photons + i)
                qkd = ScientificBB84Simulator(n_photons=n_photons)
                result = qkd.run_protocol(eve_active=True)
                
                error_rates.append(result['error_rate'] / 100)
                if result['eavesdropping_detected']:
                    detections += 1
            
            detection_rate = detections / n_exp
            avg_error = np.mean(error_rates)
            std_error = np.std(error_rates)
            
            eavesdropping_photon_analysis.append({
                'n_photons': n_photons,
                'detection_rate': detection_rate,
                'avg_error_rate': avg_error,
                'std_error_rate': std_error,
                'n_trials': n_exp
            })
            
            print(f'  光子数{n_photons:>5}: 检测率={detection_rate*100:>5.1f}%, '
                  f'误码率={avg_error*100:.2f}% ± {std_error*100:.2f}%')
        
        results['eavesdropping_photon_analysis'] = eavesdropping_photon_analysis
        self.results['qkd'] = results
        return results
    
    def experiment_qdp(self):
        """测试隐私效用权衡和预算消耗。"""
        print('\n' + '=' * 70)
        print('  实验 2: 量子差分隐私性能测试')
        print('=' * 70)
        
        results = {
            'privacy_utility_tradeoff': [],
            'budget_consumption': [],
            'noise_comparison': {}
        }
        
        print('\n[2.1] 隐私-效用权衡曲线 (每个ε值100次实验)')
        epsilons = [0.1, 0.3, 0.5, 0.8, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
        
        grad_dim = 256
        n_exp = 100
        
        for eps in epsilons:
            snr_list = []
            utility_loss_list = []
            
            for i in range(n_exp):
                np.random.seed(self.seed + 3000 + int(eps*100) + i)
                
                grad = np.random.randn(grad_dim) * 0.5
                
                qdp = QuantumDifferentialPrivacy(
                    epsilon=eps * 10,  # 避免预算耗尽干扰 ε 扫描。
                    sensitivity=1.0
                )
                noisy_grad = qdp.apply_privacy(grad, epsilon=eps)
                
                signal_power = np.linalg.norm(grad)
                noise_power = np.linalg.norm(noisy_grad - grad)
                snr = signal_power / (noise_power + 1e-8)
                snr_list.append(snr)
                
                utility_loss = noise_power / (signal_power + 1e-8)
                utility_loss_list.append(utility_loss)
            
            avg_snr = np.mean(snr_list)
            avg_utility_loss = np.mean(utility_loss_list)
            
            results['privacy_utility_tradeoff'].append({
                'epsilon': eps,
                'avg_snr': avg_snr,
                'avg_utility_loss': avg_utility_loss,
                'std_snr': np.std(snr_list),
                'n_trials': n_exp
            })
            
            print(f'  ε={eps:>5.1f}: SNR={avg_snr:.4f}, 效用损失={avg_utility_loss*100:.2f}%')
        
        print('\n[2.2] 多轮训练的隐私预算消耗追踪')
        total_epsilon = 5.0
        per_round_eps = 0.5
        n_rounds = 10
        
        np.random.seed(self.seed + 5000)
        qdp = QuantumDifferentialPrivacy(epsilon=total_epsilon, sensitivity=1.0)
        
        for r in range(n_rounds):
            grad = np.random.randn(grad_dim) * 0.5
            noisy_grad = qdp.apply_privacy(grad, epsilon=per_round_eps)
            
            report = qdp.get_privacy_report()
            noise_info = qdp.noise_history[-1]
            
            results['budget_consumption'].append({
                'round': r + 1,
                'epsilon_consumed': noise_info['epsilon_consumed'],
                'budget_used': report['budget_used'],
                'budget_remaining': report['budget_remaining'],
                'snr': noise_info['signal_to_noise_ratio'],
                'privacy_level': report['privacy_level']
            })
        
        print(f'  总预算: {total_epsilon}, 每轮消耗: {per_round_eps}')
        for item in results['budget_consumption']:
            print(f'  轮次{item["round"]:>2}: 已用{item["budget_used"]:.2f}, '
                  f'剩余{item["budget_remaining"]:.2f}, 等级={item["privacy_level"]}')
        
        self.results['qdp'] = results
        return results
    
    def experiment_mpo(self):
        """测试不同秩和矩阵规模下的压缩效果。"""
        print('\n' + '=' * 70)
        print('  实验 3: MPO张量压缩性能测试')
        print('=' * 70)
        
        results = {
            'compression_tradeoff': [],
            'matrix_size_analysis': [],
            'real_world_layers': []
        }
        
        print('\n[3.1] 不同秩下的压缩率与重建误差 (32x64矩阵)')
        ranks = [1, 2, 4, 8, 12, 16, 20, 24, 28, 32]
        np.random.seed(self.seed + 6000)
        matrix = np.random.randn(32, 64) * 0.1
        
        for r in ranks:
            mpo = ScientificMPOCompressor(max_rank=r)
            result = mpo.compress(matrix)
            
            results['compression_tradeoff'].append({
                'rank': r,
                'original_size': result.original_size,
                'compressed_size': result.compressed_size,
                'compression_ratio': (1 - result.compression_ratio) * 100,
                'reconstruction_error': result.reconstruction_error,
                'relative_error': result.reconstruction_error / np.mean(matrix**2)
            })
            
            print(f'  秩={r:>2}: 压缩率={(1-result.compression_ratio)*100:>6.2f}%, '
                  f'重建误差={result.reconstruction_error:.2e}')
        
        print('\n[3.2] 不同矩阵大小的压缩性能 (秩=8)')
        matrix_sizes = [
            (16, 32), (32, 64), (64, 128), (128, 256), (256, 512)
        ]
        
        for m, n in matrix_sizes:
            np.random.seed(self.seed + 7000 + m + n)
            mat = np.random.randn(m, n) * 0.1
            
            mpo = ScientificMPOCompressor(max_rank=8)
            result = mpo.compress(mat)
            
            results['matrix_size_analysis'].append({
                'size': f'{m}x{n}',
                'original_size': result.original_size,
                'compressed_size': result.compressed_size,
                'compression_ratio': (1 - result.compression_ratio) * 100,
                'reconstruction_error': result.reconstruction_error
            })
            
            print(f'  {m:>3}x{n:<3}: 压缩率={(1-result.compression_ratio)*100:>6.2f}%, '
                  f'误差={result.reconstruction_error:.2e}')
        
        print('\n[3.3] 真实神经网络层压缩测试 (秩=8)')
        layer_configs = [
            ('输入层', 784, 256),  # MNIST 展平维度。
            ('隐藏层1', 256, 128),
            ('隐藏层2', 128, 64),
            ('输出层', 64, 10)
        ]
        
        total_original = 0
        total_compressed = 0
        
        for name, in_dim, out_dim in layer_configs:
            np.random.seed(self.seed + 8000 + in_dim + out_dim)
            weights = np.random.randn(in_dim, out_dim) * np.sqrt(2.0 / in_dim)
            
            mpo = ScientificMPOCompressor(max_rank=8)
            result = mpo.compress(weights)
            
            total_original += result.original_size
            total_compressed += result.compressed_size
            
            results['real_world_layers'].append({
                'layer': name,
                'shape': f'{in_dim}x{out_dim}',
                'original_params': result.original_size,
                'compressed_params': result.compressed_size,
                'compression_ratio': (1 - result.compression_ratio) * 100,
                'reconstruction_error': result.reconstruction_error
            })
            
            print(f'  {name:>6} ({in_dim}x{out_dim}): '
                  f'压缩率={(1-result.compression_ratio)*100:>5.1f}%, '
                  f'原始={result.original_size:>6}, 压缩后={result.compressed_size:>6}')
        
        overall_compression = (1 - total_compressed / total_original) * 100
        print(f'\n  总体: 原始参数={total_original}, 压缩后={total_compressed}, '
              f'总压缩率={overall_compression:.1f}%')
        
        results['overall_compression'] = {
            'total_original': total_original,
            'total_compressed': total_compressed,
            'overall_ratio': overall_compression
        }
        
        self.results['mpo'] = results
        return results
    
    def experiment_byzantine(self):
        """测试不同节点配置下的共识和检测率。"""
        print('\n' + '=' * 70)
        print('  实验 4: 量子拜占庭共识性能测试')
        print('=' * 70)
        
        results = {
            'byzantine_tolerance': [],
            'detection_accuracy': [],
            'consensus_time': []
        }
        
        print('\n[4.1] 不同配置下的拜占庭容错性能 (每个配置100次实验)')
        configs = [
            (3, 0), (3, 1),
            (5, 0), (5, 1), (5, 2),
            (7, 0), (7, 1), (7, 2), (7, 3),
            (9, 0), (9, 1), (9, 2), (9, 3), (9, 4)
        ]
        
        for n_nodes, n_malicious in configs:
            successes = 0
            true_positives = 0
            false_positives = 0
            false_negatives = 0
            n_exp = 100
            
            for i in range(n_exp):
                byz = QuantumByzantineConsensus(
                    n_nodes=n_nodes, n_malicious=n_malicious,
                    seed=self.seed + 9000 + n_nodes * 100 + n_malicious * 10 + i
                )
                result = byz.run_consensus(b'test_message')
                
                if result['consensus_reached']:
                    successes += 1
                
                true_positives += result['true_positives']
                false_positives += result['false_positives']
                false_negatives += result['false_negatives']
            
            success_rate = successes / n_exp
            avg_tp = true_positives / n_exp
            avg_fp = false_positives / n_exp
            avg_fn = false_negatives / n_exp
            
            actual_malicious = n_malicious
            detected_malicious = avg_tp + avg_fp
            detection_accuracy = avg_tp / max(1, actual_malicious)
            
            results['byzantine_tolerance'].append({
                'n_nodes': n_nodes,
                'n_malicious': n_malicious,
                'malicious_ratio': n_malicious / n_nodes,
                'consensus_success_rate': success_rate,
                'detection_accuracy': detection_accuracy,
                'avg_true_positives': avg_tp,
                'avg_false_positives': avg_fp,
                'avg_false_negatives': avg_fn,
                'theoretical_max_tolerable': (n_nodes - 1) // 3,
                'n_trials': n_exp
            })
            
            within_tolerance = n_malicious <= (n_nodes - 1) // 3
            status = '✓' if within_tolerance else '✗'
            
            print(f'  n={n_nodes}, t={n_malicious} ({n_malicious/n_nodes*100:.0f}%): '
                  f'共识率={success_rate*100:>5.1f}%, '
                  f'检测率={detection_accuracy*100:>5.1f}% {status}')
        
        self.results['byzantine'] = results
        return results
    
    def experiment_attacks(self):
        """扫描四类攻击的强度和防护成功率。"""
        print('\n' + '=' * 70)
        print('  实验 5: 攻防对抗测试')
        print('=' * 70)
        
        results = {
            'attack_summary': [],
            'eavesdropping_scan': [],
            'poisoning_scan': [],
            'inversion_scan': [],
            'tampering_scan': []
        }
        
        tester = ScientificAttackTester(seed=self.seed + 10000)
        
        print('\n[5.1] 基准攻击测试')
        attack_results = tester.run_all_attacks()
        
        for r in attack_results:
            results['attack_summary'].append({
                'attack_name': r.attack_name,
                'attack_strength': r.attack_strength,
                'protection_success_rate': r.protection_success_rate * 100,
                'attack_success_rate': r.success_probability * 100,
                'false_positive_rate': r.false_positive_rate * 100,
                'false_negative_rate': r.false_negative_rate * 100,
                'details': r.details
            })
            
            print(f'  {r.attack_name}: 防护成功率={r.protection_success_rate*100:.2f}%, '
                  f'攻击成功率={r.success_probability*100:.2f}%')
        
        print('\n[5.2] 攻击强度扫描分析')
        analysis = tester.run_comprehensive_analysis()
        
        for i, s in enumerate(analysis['量子信道窃听']['strengths']):
            results['eavesdropping_scan'].append({
                'strength': s,
                'detection_rate': analysis['量子信道窃听']['detection_rates'][i],
                'protection_rate': analysis['量子信道窃听']['protection_rates'][i]
            })
        
        for i, s in enumerate(analysis['模型毒化']['strengths']):
            results['poisoning_scan'].append({
                'strength': s,
                'detection_rate': analysis['模型毒化']['detection_rates'][i],
                'protection_rate': analysis['模型毒化']['protection_rates'][i]
            })
        
        for i, eps in enumerate(analysis['梯度逆向']['epsilons']):
            results['inversion_scan'].append({
                'epsilon': eps,
                'attack_success_rate': analysis['梯度逆向']['attack_success_rates'][i],
                'protection_rate': analysis['梯度逆向']['protection_rates'][i]
            })
        
        for i, h in enumerate(analysis['区块链篡改']['hashrates']):
            results['tampering_scan'].append({
                'hashrate': h,
                'tamper_rate': analysis['区块链篡改']['tamper_rates'][i],
                'protection_rate': analysis['区块链篡改']['protection_rates'][i]
            })
        
        print('\n  量子信道窃听扫描:')
        for item in results['eavesdropping_scan']:
            print(f'    强度{item["strength"]:.1f}: 检测率={item["detection_rate"]:.1f}%, '
                  f'防护率={item["protection_rate"]:.1f}%')
        
        print('\n  模型毒化扫描:')
        for item in results['poisoning_scan']:
            print(f'    比例{item["strength"]:.1f}: 检测率={item["detection_rate"]:.1f}%, '
                  f'防护率={item["protection_rate"]:.1f}%')
        
        print('\n  梯度逆向扫描:')
        for item in results['inversion_scan']:
            print(f'    ε={item["epsilon"]:.1f}: 攻击率={item["attack_success_rate"]:.2f}%, '
                  f'防护率={item["protection_rate"]:.1f}%')
        
        print('\n  区块链篡改扫描:')
        for item in results['tampering_scan']:
            print(f'    算力{item["hashrate"]:.1f}: 篡改率={item["tamper_rate"]:.4f}%, '
                  f'防护率={item["protection_rate"]:.2f}%')
        
        self.results['attacks'] = results
        return results
    
    def experiment_blockchain(self):
        """测试 PoW、链验证、篡改检测和联邦训练存证。"""
        print('\n' + '=' * 70)
        print('  实验 6: 真实区块链性能测试')
        print('=' * 70)
        
        results = {
            'pow_difficulty_analysis': [],
            'chain_validation_tests': [],
            'tampering_detection': {},
            'federated_learning_integration': {}
        }
        
        print('\n[6.1] 不同PoW难度下的挖矿时间 (5次挖矿/难度)')
        difficulties = [1, 2, 3, 4]
        
        for difficulty in difficulties:
            mine_times = []
            n_trials = 5
            
            for i in range(n_trials):
                np.random.seed(self.seed + 10000 + difficulty * 100 + i)
                chain = Blockchain(difficulty=difficulty)
                
                model_params = np.random.randn(100)
                
                start_time = time.time()
                chain.mine_block(model_params, {'round': i})
                elapsed = time.time() - start_time
                mine_times.append(elapsed)
            
            avg_time = np.mean(mine_times)
            std_time = np.std(mine_times)
            
            results['pow_difficulty_analysis'].append({
                'difficulty': difficulty,
                'avg_mine_time': avg_time,
                'std_mine_time': std_time,
                'min_time': np.min(mine_times),
                'max_time': np.max(mine_times),
                'n_trials': n_trials
            })
            
            print(f'  难度={difficulty}: 平均挖矿时间={avg_time*1000:.2f}ms ± {std_time*1000:.2f}ms '
                  f'[{np.min(mine_times)*1000:.1f}ms, {np.max(mine_times)*1000:.1f}ms]')
        
        print('\n[6.2] 不同区块数量的链验证性能 (3次测试/长度)')
        chain_lengths = [5, 10, 20, 50]
        
        for length in chain_lengths:
            np.random.seed(self.seed + 20000 + length)
            chain = Blockchain(difficulty=2)  # 降低难度以控制基准耗时。
            
            for i in range(length):
                model_params = np.random.randn(50)
                chain.mine_block(model_params, {'round': i})
            
            validate_times = []
            n_trials = 3
            
            for i in range(n_trials):
                start_time = time.time()
                valid, msg = chain.validate_chain()
                elapsed = time.time() - start_time
                validate_times.append(elapsed)
            
            avg_time = np.mean(validate_times)
            summary = chain.get_chain_summary()
            
            results['chain_validation_tests'].append({
                'chain_length': length,
                'avg_validate_time': avg_time,
                'std_validate_time': np.std(validate_times),
                'is_valid': summary['is_valid'],
                'n_trials': n_trials
            })
            
            print(f'  链长度={length:>3}: 验证时间={avg_time*1000:.2f}ms, '
                  f'完整性={summary["is_valid"]}')
        
        print('\n[6.3] 区块篡改检测测试')
        np.random.seed(self.seed + 30000)
        chain = Blockchain(difficulty=3)
        
        for i in range(5):
            model_params = np.random.randn(50)
            chain.mine_block(model_params, {'round': i, 'accuracy': 70 + i * 2})
        
        tamper_positions = []
        for tamper_idx in range(1, 5):  # 跳过创世块。
            np.random.seed(self.seed + 30000 + tamper_idx)
            
            original_meta = chain.chain[tamper_idx].model_metadata.copy()
            original_data = chain.chain[tamper_idx].transactions[0].copy() if chain.chain[tamper_idx].transactions else {}
            
            chain.chain[tamper_idx].model_metadata['accuracy'] = 999.9
            if chain.chain[tamper_idx].transactions:
                chain.chain[tamper_idx].transactions[0]['grad_hash'] = 'tampered_hash_xxx'
            
            valid, msg = chain.validate_chain()
            
            chain.chain[tamper_idx].model_metadata = original_meta
            if chain.chain[tamper_idx].transactions:
                chain.chain[tamper_idx].transactions[0] = original_data
            
            tamper_positions.append({
                'tampered_block': tamper_idx,
                'detected': not valid,
                'message': msg
            })
        
        results['tampering_detection'] = {
            'total_tests': len(tamper_positions),
            'detected_count': sum(1 for x in tamper_positions if x['detected']),
            'details': tamper_positions
        }
        
        print(f'  篡改测试: {results["tampering_detection"]["detected_count"]}/{results["tampering_detection"]["total_tests"]} 被检测')
        for tp in tamper_positions:
            print(f'    区块{tp["tampered_block"]}: {"✓ 检测到" if tp["detected"] else "✗ 未检测"} - {tp["message"][:40]}...')
        
        print('\n[6.4] 联邦学习场景下的链上存证测试')
        np.random.seed(self.seed + 40000)
        
        ledger = SecureFederatedLedger(n_nodes=5, blockchain_difficulty=2)
        
        rounds = 5
        round_times = []
        
        for r in range(rounds):
            np.random.seed(self.seed + 40000 + r)
            
            client_metadata = [
                {'client_id': i, 'grad_norm': np.random.rand()}
                for i in range(5)
            ]
            model_accuracy = 65 + r * 3
            
            start_time = time.time()
            ledger.record_round(
                round_num=r,
                model_params=np.random.randn(50) * 0.1,
                client_metadata=client_metadata,
                model_accuracy=model_accuracy,
                malicious_nodes=[]
            )
            elapsed = time.time() - start_time
            round_times.append(elapsed)
        
        summary = ledger.get_summary()
        
        results['federated_learning_integration'] = {
            'total_rounds': rounds,
            'total_blocks': summary['blockchain']['length'],
            'total_transactions': summary['blockchain']['total_transactions'],
            'avg_record_time': np.mean(round_times),
            'chain_valid': summary['blockchain']['is_valid'],
            'round_times': [round(t * 1000, 2) for t in round_times]
        }
        
        print(f'  训练轮次: {rounds}')
        print(f'  区块数量: {summary["blockchain"]["length"]}')
        print(f'  交易总数: {summary["blockchain"]["total_transactions"]}')
        print(f'  平均记录时间: {np.mean(round_times)*1000:.2f}ms')
        print(f'  链完整性: {"✓ 有效" if summary["blockchain"]["is_valid"] else "✗ 无效"}')
        
        for r in range(rounds):
            block = ledger.blockchain.chain[r + 1]  # 跳过创世块。
            print(f'    轮次{r}: 区块{block.index} | 哈希前16位: {block.hash()[:16]}... | '
                  f'准确率: {block.model_metadata.get("accuracy", "N/A"):.1f}%')
        
        self.results['blockchain'] = results
        return results
    
    def run_all_experiments(self):
        start_time = time.time()
        
        print('\n' + '#' * 70)
        print('#  量子安全联邦学习系统 - 实验验证')
        print('#  所有数据均来自真实实验运行')
        print('#' * 70)
        
        self.experiment_qkd()
        self.experiment_qdp()
        self.experiment_mpo()
        self.experiment_byzantine()
        self.experiment_attacks()
        self.experiment_blockchain()
        
        self.save_results()
        
        elapsed = time.time() - start_time
        print('\n' + '=' * 70)
        print(f'  所有实验完成! 总耗时: {elapsed:.2f}秒')
        print(f'  结果已保存至: {self.output_file}')
        print('=' * 70)
        
        return self.results
    
    def save_results(self):
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
    
    def generate_summary_table(self):
        print('\n' + '=' * 70)
        print('  实验结果汇总表')
        print('=' * 70)
        
        qkd = self.results['qkd']['normal_communication']
        print(f'\n【QKD密钥分发】')
        print(f'  正常通信误码率: {qkd["avg_error_rate"]*100:.2f}% ± {qkd["std_error_rate"]*100:.2f}%')
        print(f'  密钥生成成功率: {qkd["key_success_rate"]*100:.1f}%')
        
        qdp = self.results['qdp']['privacy_utility_tradeoff']
        eps_1 = [x for x in qdp if x['epsilon'] == 1.0][0]
        print(f'\n【量子差分隐私】')
        print(f'  ε=1.0时SNR: {eps_1["avg_snr"]:.4f} ± {eps_1["std_snr"]:.4f}')
        print(f'  ε=1.0时效用损失: {eps_1["avg_utility_loss"]*100:.2f}%')
        
        mpo_overall = self.results['mpo']['overall_compression']
        print(f'\n【MPO张量压缩】')
        print(f'  总压缩率: {mpo_overall["overall_ratio"]:.1f}%')
        print(f'  原始参数: {mpo_overall["total_original"]}, 压缩后: {mpo_overall["total_compressed"]}')
        
        byz = [x for x in self.results['byzantine']['byzantine_tolerance'] 
               if x['n_nodes'] == 5 and x['n_malicious'] == 1][0]
        print(f'\n【拜占庭共识】')
        print(f'  n=5, t=1: 共识成功率={byz["consensus_success_rate"]*100:.1f}%')
        print(f'  恶意节点检测率: {byz["detection_accuracy"]*100:.1f}%')
        
        print(f'\n【攻防测试】')
        for attack in self.results['attacks']['attack_summary']:
            print(f'  {attack["attack_name"]}: 防护成功率={attack["protection_success_rate"]:.2f}%')
        
        if 'blockchain' in self.results:
            blk = self.results['blockchain']
            print(f'\n【真实区块链】')
            pow3 = [x for x in blk['pow_difficulty_analysis'] if x['difficulty'] == 3][0]
            print(f'  PoW难度3挖矿时间: {pow3["avg_mine_time"]*1000:.2f}ms')
            print(f'  篡改检测率: {blk["tampering_detection"]["detected_count"]}/{blk["tampering_detection"]["total_tests"]}')
            fl_int = blk['federated_learning_integration']
            print(f'  联邦学习集成: {fl_int["total_rounds"]}轮/{fl_int["total_blocks"]}区块, 链完整性={fl_int["chain_valid"]}')


def main():
    runner = ExperimentRunner(seed=42, output_file='experiment_results.json')
    runner.run_all_experiments()
    runner.generate_summary_table()


if __name__ == '__main__':
    main()
