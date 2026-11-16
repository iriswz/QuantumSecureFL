"""汇总 Parkinson 真实场景的五个固定随机种子结果。"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def summarize() -> Path:
    result_root = PROJECT_ROOT / 'artifacts' / 'parkinson_demo' / 'multiseed'
    files = sorted(result_root.glob('seed_*/parkinson_federated_results.json'))
    if not files:
        raise FileNotFoundError('未找到 Parkinson 多种子结果')

    rows = []
    all_checks = {
        'eavesdropping_detected': True,
        'ciphertext_tampering_rejected': True,
        'malicious_client_detected_every_round': True,
        'blockchain_valid': True,
        'all_rounds_recorded': True,
    }
    protocol = None
    dataset_name = None
    for path in files:
        data = json.loads(path.read_text(encoding='utf-8'))
        protocol = data['config']
        dataset_name = data['dataset']['dataset_name']
        metrics = {item['name']: item['metrics'] for item in data['results']}
        advantages = data['four_layer_advantages']
        rows.append({
            'seed': data['config']['seed'],
            'clean_plain_balanced_accuracy': metrics['plain_federated']['balanced_accuracy'],
            'attacked_plain_balanced_accuracy': metrics['attacked_plain_federated']['balanced_accuracy'],
            'secure_balanced_accuracy': metrics['secure_federated']['balanced_accuracy'],
            'secure_gain_over_attacked_balanced_accuracy_points': (
                advantages['utility_under_attack_balanced_accuracy_gain_points']
            ),
            'secure_minus_clean_plain_balanced_accuracy_points': (
                advantages['secure_vs_clean_plain_balanced_accuracy_gap_points']
            ),
            'attacked_plain_accuracy': metrics['attacked_plain_federated']['accuracy'],
            'secure_accuracy': metrics['secure_federated']['accuracy'],
            'secure_gain_over_attacked_accuracy_points': round(
                metrics['secure_federated']['accuracy']
                - metrics['attacked_plain_federated']['accuracy'], 2
            ),
            'secure_decision_threshold': metrics['secure_federated']['decision_threshold'],
            'plain_gradient_reconstruction_nrmse': (
                advantages['layer2_plain_gradient_reconstruction_nrmse']
            ),
            'qdp_gradient_reconstruction_nrmse': (
                advantages['layer2_qdp_gradient_reconstruction_nrmse']
            ),
            'mpo_payload_saving_pct': advantages['layer3_mpo_payload_saving_pct'],
            'malicious_round_detection_rate_pct': (
                advantages['layer3_malicious_round_detection_rate_pct']
            ),
        })
        all_checks['eavesdropping_detected'] &= advantages['layer1_eavesdropping_detected']
        all_checks['ciphertext_tampering_rejected'] &= (
            advantages['layer1_ciphertext_tampering_rejected']
        )
        all_checks['malicious_client_detected_every_round'] &= (
            advantages['layer3_malicious_round_detection_rate_pct'] == 100.0
        )
        all_checks['blockchain_valid'] &= advantages['layer4_chain_valid']
        all_checks['all_rounds_recorded'] &= advantages['layer4_all_rounds_recorded']

    numeric_keys = [key for key in rows[0] if key != 'seed']
    aggregate_mean = {}
    aggregate_sample_std = {}
    for key in numeric_keys:
        values = np.asarray([row[key] for row in rows], dtype=np.float64)
        aggregate_mean[key] = round(float(np.mean(values)), 3)
        aggregate_sample_std[key] = round(float(np.std(values, ddof=1)), 3)

    payload = {
        'dataset': dataset_name,
        'seeds': [row['seed'] for row in rows],
        'protocol': protocol,
        'per_seed': rows,
        'aggregate_mean': aggregate_mean,
        'aggregate_sample_std': aggregate_sample_std,
        'all_seeds': all_checks,
        'scope_warning': (
            'Five organizations and all quantum-related components are software simulations; '
            'the decision threshold is calibrated only from federated training confusion counts.'
        ),
    }
    output = PROJECT_ROOT / 'artifacts' / 'parkinson_demo' / 'multiseed_summary.json'
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return output


if __name__ == '__main__':
    print(summarize())
