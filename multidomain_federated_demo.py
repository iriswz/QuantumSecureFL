"""邮件网关和金融风控两个小型真实数据四层安全联邦对照。"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Dict, Sequence

import numpy as np

from core import download_scenario_dataset, load_federated_small_scenario
from medical_federated_demo import (
    run_plain_federated,
    run_secure_federated,
    run_single_hospital,
)
from parkinson_federated_demo import (
    _timed,
    gradient_inversion_probe,
    run_attacked_federated,
)


PROJECT_ROOT = Path(__file__).resolve().parent
SCENE_CONFIGS = {
    'spam': {
        'title': '跨邮件网关垃圾邮件协同识别',
        'client_label': '邮件网关',
        'record_label': '邮件',
        'positive_label': '垃圾邮件率',
        'learning_rate': 0.08,
        'batch_size': 256,
        'bond_dim': 16,
        'output_dir': PROJECT_ROOT / 'artifacts' / 'spam_demo',
        'result_file': 'spam_federated_results.json',
    },
    'bankruptcy': {
        'title': '跨金融机构企业破产风险预警',
        'client_label': '金融机构',
        'record_label': '企业记录',
        'positive_label': '破产样本率',
        'learning_rate': 0.08,
        'batch_size': 256,
        'bond_dim': 12,
        'output_dir': PROJECT_ROOT / 'artifacts' / 'bankruptcy_demo',
        'result_file': 'bankruptcy_federated_results.json',
    },
}


def _write_outputs(output_dir: Path, result_file: str, scene: str, dataset,
                   results: Sequence[Dict], leakage: Dict,
                   config: Dict, elapsed: float) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    secure = next(result for result in results if result['name'] == 'secure_federated')
    attacked = next(result for result in results if result['name'] == 'attacked_plain_federated')
    plain = next(result for result in results if result['name'] == 'plain_federated')
    security = secure['security']
    advantages = {
        'secure_accuracy_gain_over_attacked_points': round(
            secure['metrics']['accuracy'] - attacked['metrics']['accuracy'], 2
        ),
        'secure_balanced_accuracy_gain_over_attacked_points': round(
            secure['metrics']['balanced_accuracy'] - attacked['metrics']['balanced_accuracy'], 2
        ),
        'secure_balanced_accuracy_gap_from_clean_plain_points': round(
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
        'layer4_chain_valid': bool(security['blockchain']['valid']),
        'layer4_all_rounds_recorded': bool(security['blockchain']['all_rounds_recorded']),
    }
    payload = {
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S %z'),
        'elapsed_seconds': round(elapsed, 3),
        'scene': scene,
        'scene_title': SCENE_CONFIGS[scene]['title'],
        'experiment_scope': (
            'real public records; five organizations and all quantum-related modules are '
            'software simulations'
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
    result_path = output_dir / result_file
    result_path.write_text(
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
        'recall', 'specificity', 'f1', 'roc_auc', 'positive_prediction_rate'
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
    return result_path


def _print_summary(scene: str, dataset, results: Sequence[Dict], leakage: Dict) -> None:
    scene_config = SCENE_CONFIGS[scene]
    metadata = dataset.metadata
    print(f'\n[真实小型数据集] {metadata["dataset_name"]}')
    print(
        f'  {metadata["raw_records"]:,}条{scene_config["record_label"]} | '
        f'{metadata["feature_count"]}维 | 阳性率{metadata["raw_positive_rate_pct"]:.2f}%'
    )
    print(
        f'  训练{metadata["train_records"]:,} / 测试{metadata["test_records"]:,} | '
        f'记录泄漏={metadata["row_leakage_count"]}'
    )
    for summary in dataset.hospital_summaries:
        print(
            f'  {summary["name"]}: {summary["records"]}条 | '
            f'{scene_config["positive_label"]}{summary["positive_rate_pct"]:.2f}%'
        )
    print('\n[同一留出测试集]')
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
        f'  1 QKD: 窃听检测={security["eavesdropping_test"]["eavesdropping_detected"]}，'
        f'密文篡改拒绝={security["ciphertext_tampering_test"]["tampering_rejected"]}'
    )
    print(
        f'  2 QDP: 梯度反演NRMSE {leakage["plain_gradient_reconstruction_nrmse"]:.6f}'
        f' → {leakage["qdp_gradient_reconstruction_nrmse"]:.3f}'
    )
    print(
        f'  3 MPO+共识: 载荷节省={security["mpo"]["average_payload_saving_pct"]:.2f}% ，'
        f'恶意客户端识别={security["byzantine"]["rounds_detected"]}/'
        f'{security["byzantine"]["rounds_total"]}轮'
    )
    print(
        f'  4 区块链: 链有效={security["blockchain"]["valid"]}，'
        f'全部轮次记录={security["blockchain"]["all_rounds_recorded"]}'
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='两个小型真实跨机构四层安全联邦场景')
    parser.add_argument('scene', choices=sorted(SCENE_CONFIGS))
    parser.add_argument('--rounds', type=int, default=20)
    parser.add_argument('--batch-size', type=int)
    parser.add_argument('--learning-rate', type=float)
    parser.add_argument('--local-epsilon', type=float, default=0.5)
    parser.add_argument('--bond-dim', type=int)
    parser.add_argument('--malicious-client', type=int, default=4)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--force-download', action='store_true')
    parser.add_argument('--output-dir', type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    scene_config = SCENE_CONFIGS[args.scene]
    batch_size = args.batch_size or scene_config['batch_size']
    learning_rate = args.learning_rate or scene_config['learning_rate']
    bond_dim = args.bond_dim or scene_config['bond_dim']
    output_dir = args.output_dir or scene_config['output_dir']
    if args.rounds < 1 or batch_size < 16 or learning_rate <= 0:
        raise ValueError('rounds>=1、batch-size>=16、learning-rate>0')
    if args.local_epsilon <= 0 or bond_dim < 1:
        raise ValueError('local-epsilon 和 bond-dim 必须为正数')
    if args.malicious_client not in range(5):
        raise ValueError('malicious-client 必须为 0-4')

    started = time.time()
    print('=' * 82)
    print(f'  {scene_config["title"]}：普通联邦 vs 四层安全联邦')
    print('  数据记录真实；五机构与量子相关模块为软件仿真')
    print('=' * 82)
    data_path = download_scenario_dataset(
        PROJECT_ROOT, args.scene, force=args.force_download
    )
    dataset = load_federated_small_scenario(
        data_path, scenario=args.scene, seed=args.seed
    )
    print('\n[运行] 单机构基线...')
    single = _timed(
        run_single_hospital, dataset, args.rounds, batch_size, learning_rate, args.seed
    )
    print('[运行] 干净普通 FedAvg...')
    plain = _timed(
        run_plain_federated, dataset, args.rounds, batch_size, learning_rate, args.seed
    )
    print('[运行] 遭投毒普通 FedAvg...')
    attacked = _timed(
        run_attacked_federated, dataset, args.rounds, batch_size,
        learning_rate, args.seed, args.malicious_client
    )
    print('[运行] 同一投毒条件下的四层安全联邦...')
    secure = _timed(
        run_secure_federated, dataset, args.rounds, batch_size,
        learning_rate, args.seed,
        malicious_hospital=args.malicious_client,
        local_epsilon=args.local_epsilon,
        bond_dim=bond_dim,
    )
    leakage = gradient_inversion_probe(
        dataset, batch_size, args.local_epsilon, args.seed
    )
    results = [single, plain, attacked, secure]
    _print_summary(args.scene, dataset, results, leakage)
    config = {
        'rounds': args.rounds,
        'batch_size_per_client': batch_size,
        'learning_rate': learning_rate,
        'local_epsilon_per_round': args.local_epsilon,
        'mpo_bond_dim': bond_dim,
        'malicious_client': args.malicious_client,
        'attack_gradient_factor': -25.0,
        'decision_threshold_calibration': (
            'federated training confusion-count aggregation; objective=accuracy'
        ),
        'seed': args.seed,
    }
    path = _write_outputs(
        output_dir, scene_config['result_file'], args.scene,
        dataset, results, leakage, config, time.time() - started
    )
    print(f'\n结果已保存: {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
