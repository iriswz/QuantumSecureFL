"""小型真实 Parkinson 语音数据上的四层安全联邦学习对照实验。"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Dict, Sequence

import numpy as np

from core import (
    QuantumDifferentialPrivacy,
    SimpleNNModel,
    download_parkinson_dataset,
    load_federated_parkinson_data,
)
from medical_federated_demo import (
    _balanced_batch,
    _flatten_gradients,
    _make_model,
    evaluate_with_federated_threshold,
    run_plain_federated,
    run_secure_federated,
    run_single_hospital,
)


PROJECT_ROOT = Path(__file__).resolve().parent


def run_attacked_federated(dataset, rounds: int, batch_size: int,
                           learning_rate: float, seed: int,
                           malicious_client: int, attack_factor: float = -25.0) -> Dict:
    """普通 FedAvg 在一个客户端反向放大梯度时的对照。"""
    model = _make_model(len(dataset.feature_names), seed)
    global_params = model.flatten_params().copy()
    rngs = [np.random.RandomState(seed + 900 + i) for i in range(len(dataset.client_data))]
    history = []
    for round_index in range(rounds):
        gradients = []
        for client_id, (X, y) in enumerate(dataset.client_data):
            local_model = _make_model(len(dataset.feature_names), seed + 9000 + client_id)
            local_model.load_flat_params(global_params)
            X_batch, y_batch = _balanced_batch(X, y, batch_size, rngs[client_id])
            gradient = _flatten_gradients(local_model.compute_gradients(X_batch, y_batch))
            if client_id == malicious_client:
                gradient = attack_factor * gradient
            gradients.append(gradient)
        global_params -= learning_rate * np.mean(np.vstack(gradients), axis=0)
        model.load_flat_params(global_params)
        history.append({
            'round': round_index + 1,
            **evaluate_with_federated_threshold(
                model, dataset.client_data, dataset.X_test, dataset.y_test
            ),
        })
    return {
        'name': 'attacked_plain_federated',
        'description': '普通 FedAvg + 单个客户端反向放大梯度（无共识过滤）',
        'metrics': history[-1],
        'history': history,
        'attack': {'malicious_client': malicious_client, 'gradient_factor': attack_factor},
    }


def gradient_inversion_probe(dataset, batch_size: int, local_epsilon: float,
                             seed: int) -> Dict:
    """利用单样本首层梯度的秩一结构，比较明文梯度与加噪梯度的可反演性。"""
    input_dim = len(dataset.feature_names)
    model = _make_model(input_dim, seed + 12000)
    X, y = dataset.client_data[0]
    sample = X[0:1]
    label = y[0:1]
    gradients = model.compute_gradients(sample, label)
    clean_flat = _flatten_gradients(gradients)

    def reconstruct(flat: np.ndarray) -> np.ndarray:
        w1_size = input_dim * model.hidden_dim
        W1 = flat[:w1_size].reshape(input_dim, model.hidden_dim)
        b1 = flat[w1_size:w1_size + model.hidden_dim]
        column = int(np.argmax(np.abs(b1)))
        denominator = b1[column]
        if abs(denominator) < 1e-12:
            return np.zeros(input_dim, dtype=np.float64)
        return W1[:, column] / denominator

    clean_reconstruction = reconstruct(clean_flat)
    np.random.seed(seed + 13000)
    privacy = QuantumDifferentialPrivacy(
        epsilon=local_epsilon + 1e-9,
        channel_ratio=0.65,
        sensitivity=2.0 / batch_size,
        clip_norm=1.0,
    )
    protected_flat = privacy.apply_privacy(clean_flat, local_epsilon=local_epsilon)
    protected_reconstruction = reconstruct(protected_flat)
    scale = max(float(np.linalg.norm(sample[0])), 1e-12)
    clean_nrmse = float(np.linalg.norm(clean_reconstruction - sample[0]) / scale)
    protected_nrmse = float(np.linalg.norm(protected_reconstruction - sample[0]) / scale)
    cosine = float(np.dot(clean_flat, protected_flat) / (
        max(np.linalg.norm(clean_flat) * np.linalg.norm(protected_flat), 1e-12)
    ))
    return {
        'attack': 'analytic single-record first-layer gradient inversion',
        'scope': 'empirical leakage probe, not a formal DP audit',
        'plain_gradient_reconstruction_nrmse': round(clean_nrmse, 8),
        'qdp_gradient_reconstruction_nrmse': round(protected_nrmse, 8),
        'reconstruction_nrmse_increase': round(protected_nrmse - clean_nrmse, 8),
        'plain_gradient_reconstruction_succeeded': bool(clean_nrmse < 0.1),
        'qdp_gradient_reconstruction_blocked': bool(protected_nrmse >= 0.1),
        'clean_to_protected_gradient_cosine': round(cosine, 6),
        'qdp_noise_scale': privacy.get_noise_history()[0]['noise_scale'],
    }


def _timed(callable_, *args, **kwargs):
    started = time.perf_counter()
    result = callable_(*args, **kwargs)
    result['runtime_seconds'] = round(time.perf_counter() - started, 3)
    return result


def _write_outputs(output_dir: Path, dataset, results: Sequence[Dict],
                   leakage: Dict, config: Dict, elapsed: float) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    secure = next(result for result in results if result['name'] == 'secure_federated')
    attacked = next(result for result in results if result['name'] == 'attacked_plain_federated')
    plain = next(result for result in results if result['name'] == 'plain_federated')
    security = secure['security']
    advantages = {
        'utility_under_attack_balanced_accuracy_gain_points': round(
            secure['metrics']['balanced_accuracy'] - attacked['metrics']['balanced_accuracy'], 2
        ),
        'secure_vs_clean_plain_balanced_accuracy_gap_points': round(
            secure['metrics']['balanced_accuracy'] - plain['metrics']['balanced_accuracy'], 2
        ),
        'layer1_eavesdropping_detected': bool(
            security['eavesdropping_test']['eavesdropping_detected']
        ),
        'layer1_ciphertext_tampering_rejected': bool(
            security['ciphertext_tampering_test']['tampering_rejected']
        ),
        'layer2_plain_gradient_reconstruction_nrmse': (
            leakage['plain_gradient_reconstruction_nrmse']
        ),
        'layer2_qdp_gradient_reconstruction_nrmse': (
            leakage['qdp_gradient_reconstruction_nrmse']
        ),
        'layer2_qdp_gradient_reconstruction_blocked': (
            leakage['qdp_gradient_reconstruction_blocked']
        ),
        'layer3_mpo_payload_saving_pct': security['mpo']['average_payload_saving_pct'],
        'layer3_malicious_round_detection_rate_pct': round(
            100.0 * security['byzantine']['rounds_detected'] /
            max(1, security['byzantine']['rounds_total']), 2
        ),
        'layer4_chain_valid': security['blockchain']['valid'],
        'layer4_all_rounds_recorded': security['blockchain']['all_rounds_recorded'],
    }
    payload = {
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S %z'),
        'elapsed_seconds': round(elapsed, 3),
        'experiment_scope': (
            'real public voice records; five organizations and all quantum-related modules '
            'are software simulations; not for clinical use'
        ),
        'config': config,
        'dataset': {**dataset.metadata, 'client_summaries': dataset.hospital_summaries},
        'gradient_leakage_probe': leakage,
        'four_layer_advantages': advantages,
        'results': [
            {key: value for key, value in result.items() if key != 'compression_records'}
            for result in results
        ],
    }
    json_path = output_dir / 'parkinson_federated_results.json'
    json_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=lambda value: value.item() if isinstance(value, np.generic) else str(value),
        ),
        encoding='utf-8'
    )
    fields = [
        'scheme', 'round', 'accuracy', 'balanced_accuracy', 'precision',
        'recall', 'specificity', 'f1', 'roc_auc', 'positive_prediction_rate',
        'decision_threshold'
    ]
    with (output_dir / 'training_history.csv').open('w', encoding='utf-8', newline='') as target:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        for result in results:
            for row in result['history']:
                writer.writerow({
                    'scheme': result['name'],
                    **{field: row.get(field) for field in fields if field != 'scheme'}
                })
    return json_path


def _print_summary(dataset, results: Sequence[Dict], leakage: Dict) -> None:
    meta = dataset.metadata
    print('\n[真实小型数据集]')
    print(
        f'  {meta["dataset_name"]}: {meta["raw_recordings"]}条录音 / '
        f'{meta["raw_subjects"]}名受试者 / 原始{meta["source_feature_count"]}维'
    )
    print(
        f'  训练{meta["train_recordings"]} / 测试{meta["test_recordings"]} | '
        f'受试者泄漏={meta["subject_leakage_count"]} | 模型输入{meta["model_feature_count"]}维'
    )
    for summary in dataset.hospital_summaries:
        print(
            f'  {summary["name"]}: {summary["recordings"]}条 / '
            f'{summary["subjects"]}人 / PD率{summary["positive_rate_pct"]:.1f}%'
        )

    print('\n[同一受试者级测试集]')
    print('  {:<26} {:>9} {:>11} {:>9} {:>9} {:>9}'.format(
        '方案', '准确率', '平衡准确率', '召回率', 'F1', 'ROC-AUC'
    ))
    for result in results:
        metrics = result['metrics']
        print('  {:<26} {:>8.2f}% {:>10.2f}% {:>8.2f}% {:>8.2f}% {:>9.4f}'.format(
            result['name'], metrics['accuracy'], metrics['balanced_accuracy'],
            metrics['recall'], metrics['f1'], metrics['roc_auc']
        ))

    secure = next(result for result in results if result['name'] == 'secure_federated')
    security = secure['security']
    print('\n[四层优势证据]')
    print(
        f'  1 QKD认证加密: 窃听检测={security["eavesdropping_test"]["eavesdropping_detected"]}，'
        f'密文篡改拒绝={security["ciphertext_tampering_test"]["tampering_rejected"]}'
    )
    print(
        f'  2 QDP: 明文梯度反演NRMSE={leakage["plain_gradient_reconstruction_nrmse"]:.6f}，'
        f'加噪后={leakage["qdp_gradient_reconstruction_nrmse"]:.3f}'
    )
    print(
        f'  3 MPO+共识: 载荷节省={security["mpo"]["average_payload_saving_pct"]:.2f}% ，'
        f'恶意客户端识别={security["byzantine"]["rounds_detected"]}/'
        f'{security["byzantine"]["rounds_total"]}轮'
    )
    print(
        f'  4 区块链: 链有效={security["blockchain"]["valid"]}，'
        f'全部训练轮已记录={security["blockchain"]["all_rounds_recorded"]}'
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Parkinson真实小数据四层安全联邦对照')
    parser.add_argument('--rounds', type=int, default=20)
    parser.add_argument('--batch-size', type=int, default=128)
    parser.add_argument('--learning-rate', type=float, default=0.08)
    parser.add_argument('--projection-dim', type=int, default=64)
    parser.add_argument('--local-epsilon', type=float, default=0.5)
    parser.add_argument('--bond-dim', type=int, default=16)
    parser.add_argument('--malicious-client', type=int, default=4)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--force-download', action='store_true')
    parser.add_argument(
        '--output-dir', type=Path,
        default=PROJECT_ROOT / 'artifacts' / 'parkinson_demo'
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.rounds < 1 or args.batch_size < 16 or args.learning_rate <= 0:
        raise ValueError('rounds>=1、batch-size>=16、learning-rate>0')
    if args.malicious_client not in range(5):
        raise ValueError('malicious-client 必须为 0-4')
    started = time.time()
    print('=' * 82)
    print('  UCI Parkinson 语音识别：普通联邦 vs 四层安全联邦（小型真实数据）')
    print('  客户端/量子相关模块为软件仿真；不用于临床诊断')
    print('=' * 82)
    csv_path = download_parkinson_dataset(PROJECT_ROOT, force=args.force_download)
    dataset = load_federated_parkinson_data(
        csv_path, projection_dim=args.projection_dim, seed=args.seed
    )
    print('\n[运行] 单机构基线...')
    single = _timed(
        run_single_hospital, dataset, args.rounds, args.batch_size,
        args.learning_rate, args.seed
    )
    print('[运行] 干净普通 FedAvg（效用上界）...')
    plain = _timed(
        run_plain_federated, dataset, args.rounds, args.batch_size,
        args.learning_rate, args.seed
    )
    print('[运行] 遭投毒的普通 FedAvg...')
    attacked = _timed(
        run_attacked_federated, dataset, args.rounds, args.batch_size,
        args.learning_rate, args.seed, args.malicious_client
    )
    print('[运行] 同一投毒条件下的四层安全联邦...')
    secure = _timed(
        run_secure_federated, dataset, args.rounds, args.batch_size,
        args.learning_rate, args.seed,
        malicious_hospital=args.malicious_client,
        local_epsilon=args.local_epsilon,
        bond_dim=args.bond_dim,
    )
    leakage = gradient_inversion_probe(
        dataset, args.batch_size, args.local_epsilon, args.seed
    )
    results = [single, plain, attacked, secure]
    _print_summary(dataset, results, leakage)
    config = {
        'rounds': args.rounds,
        'batch_size_per_client': args.batch_size,
        'learning_rate': args.learning_rate,
        'projection_dim': args.projection_dim,
        'local_epsilon_per_round': args.local_epsilon,
        'mpo_bond_dim': args.bond_dim,
        'malicious_client': args.malicious_client,
        'attack_gradient_factor': -25.0,
        'decision_threshold_calibration': (
            'federated training confusion-count aggregation; objective=accuracy'
        ),
        'seed': args.seed,
    }
    result_path = _write_outputs(
        args.output_dir, dataset, results, leakage, config, time.time() - started
    )
    print(f'\n结果已保存: {result_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
