"""五医院糖尿病患者 30 日再入院风险安全联邦学习演示。

本脚本使用真实公开医疗数据，但 QKD、量子噪声、量子签名和区块链均为
本地软件仿真。输出只能用于科研/教学验证，不能用于临床决策。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import struct
import time
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np

from core import (
    FederatedLearningServer,
    MPOCompressor,
    QuantumCommunicationChannel,
    QuantumDifferentialPrivacy,
    SecureFederatedLedger,
    SimpleNNModel,
    download_diabetes_dataset,
    load_federated_diabetes_data,
)
from core.blockchain_consensus import QuantumByzantineConsensus
from core.fl_mpo_module import MPOCompressionResult


PROJECT_ROOT = Path(__file__).resolve().parent


def _make_model(input_dim: int, seed: int) -> SimpleNNModel:
    np.random.seed(seed)
    return SimpleNNModel(input_dim=input_dim, hidden_dim=48, output_dim=2)


def _balanced_batch(X: np.ndarray, y: np.ndarray, batch_size: int,
                    rng: np.random.RandomState) -> Tuple[np.ndarray, np.ndarray]:
    """医院只在本地构造类别均衡批次，原始数据不会离开客户端。"""
    positive = np.flatnonzero(y == 1)
    negative = np.flatnonzero(y == 0)
    if len(positive) == 0 or len(negative) == 0:
        indices = rng.choice(len(y), size=batch_size, replace=len(y) < batch_size)
    else:
        n_positive = batch_size // 2
        n_negative = batch_size - n_positive
        pos_indices = rng.choice(positive, size=n_positive, replace=len(positive) < n_positive)
        neg_indices = rng.choice(negative, size=n_negative, replace=len(negative) < n_negative)
        indices = np.concatenate([pos_indices, neg_indices])
        rng.shuffle(indices)
    return X[indices], y[indices]


def _flatten_gradients(gradients: Dict[str, np.ndarray]) -> np.ndarray:
    return np.concatenate([gradients[key].ravel() for key in ('W1', 'b1', 'W2', 'b2')])


def _auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    """用 Mann-Whitney U 统计量计算二分类 ROC-AUC（含并列分数处理）。"""
    y_true = np.asarray(y_true, dtype=np.int64)
    scores = np.asarray(scores, dtype=np.float64)
    order = np.argsort(scores, kind='mergesort')
    sorted_scores = scores[order]
    ranks = np.empty(len(scores), dtype=np.float64)
    start = 0
    while start < len(scores):
        end = start + 1
        while end < len(scores) and sorted_scores[end] == sorted_scores[start]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        ranks[order[start:end]] = average_rank
        start = end
    positives = y_true == 1
    n_positive = int(np.sum(positives))
    n_negative = len(y_true) - n_positive
    if n_positive == 0 or n_negative == 0:
        return 0.5
    rank_sum = float(np.sum(ranks[positives]))
    value = (rank_sum - n_positive * (n_positive + 1) / 2.0) / (n_positive * n_negative)
    return float(value)


def evaluate_model(model: SimpleNNModel, X: np.ndarray, y: np.ndarray,
                   threshold: float = 0.5) -> Dict:
    probabilities = model.forward(X)[:, 1]
    predictions = (probabilities >= threshold).astype(np.int64)
    tp = int(np.sum((predictions == 1) & (y == 1)))
    tn = int(np.sum((predictions == 0) & (y == 0)))
    fp = int(np.sum((predictions == 1) & (y == 0)))
    fn = int(np.sum((predictions == 0) & (y == 1)))
    accuracy = (tp + tn) / max(1, len(y))
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    specificity = tn / max(1, tn + fp)
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    return {
        'accuracy': round(accuracy * 100.0, 2),
        'balanced_accuracy': round((recall + specificity) * 50.0, 2),
        'precision': round(precision * 100.0, 2),
        'recall': round(recall * 100.0, 2),
        'specificity': round(specificity * 100.0, 2),
        'f1': round(f1 * 100.0, 2),
        'roc_auc': round(_auc(y, probabilities), 4),
        'positive_prediction_rate': round(float(np.mean(predictions)) * 100.0, 2),
        'confusion_matrix': {'tn': tn, 'fp': fp, 'fn': fn, 'tp': tp},
        'n_samples': int(len(y)),
    }


def select_federated_decision_threshold(
        model: SimpleNNModel,
        client_data: Sequence[Tuple[np.ndarray, np.ndarray]]) -> float:
    """仅聚合各客户端候选阈值的混淆计数，选择训练端准确率最高的阈值。

    服务端不需要原始样本或单条预测分数，测试集也不参与阈值选择。
    当准确率并列时，优先平衡准确率更高且更接近 0.5 的候选值。
    """
    thresholds = np.linspace(0.05, 0.95, 181, dtype=np.float64)
    tp = np.zeros_like(thresholds, dtype=np.int64)
    tn = np.zeros_like(thresholds, dtype=np.int64)
    fp = np.zeros_like(thresholds, dtype=np.int64)
    fn = np.zeros_like(thresholds, dtype=np.int64)

    for X, y in client_data:
        labels = np.asarray(y, dtype=np.int64)
        probabilities = model.forward(X)[:, 1]
        predictions = probabilities[:, None] >= thresholds[None, :]
        positives = labels[:, None] == 1
        negatives = ~positives
        tp += np.sum(predictions & positives, axis=0)
        tn += np.sum((~predictions) & negatives, axis=0)
        fp += np.sum(predictions & negatives, axis=0)
        fn += np.sum((~predictions) & positives, axis=0)

    accuracy = (tp + tn) / np.maximum(tp + tn + fp + fn, 1)
    recall = tp / np.maximum(tp + fn, 1)
    specificity = tn / np.maximum(tn + fp, 1)
    balanced_accuracy = 0.5 * (recall + specificity)
    best_index = max(
        range(len(thresholds)),
        key=lambda index: (
            float(accuracy[index]),
            float(balanced_accuracy[index]),
            -abs(float(thresholds[index]) - 0.5),
        ),
    )
    return float(thresholds[best_index])


def evaluate_with_federated_threshold(model: SimpleNNModel, client_data,
                                      X_test: np.ndarray, y_test: np.ndarray) -> Dict:
    """用训练端统计标定阈值后，再一次性评估独立测试集。"""
    threshold = select_federated_decision_threshold(model, client_data)
    metrics = evaluate_model(model, X_test, y_test, threshold=threshold)
    metrics['decision_threshold'] = round(threshold, 4)
    metrics['threshold_calibration'] = (
        'federated training confusion-count aggregation; objective=accuracy'
    )
    return metrics


def _serialize_gradient(gradient: np.ndarray, compressor: MPOCompressor) -> Tuple[bytes, Dict]:
    """把梯度编码为原始向量或 MPO 张量链；仅在确实节省字节时使用 MPO。"""
    gradient = np.asarray(gradient, dtype='<f8')
    compressed = compressor.compress(gradient)
    header = json.dumps({
        'original_size': compressed.original_size,
        'compressed_size': compressed.compressed_size,
        'compression_ratio': compressed.compression_ratio,
        'reconstruction_error': compressed.reconstruction_error,
        'bond_dim': compressed.bond_dim,
        'shapes': [list(tensor.shape) for tensor in compressed.mpo_tensors],
    }, separators=(',', ':')).encode('utf-8')
    mpo_payload = (
        b'MPO1' + struct.pack('>I', len(header)) + header +
        b''.join(np.asarray(tensor, dtype='<f8').tobytes() for tensor in compressed.mpo_tensors)
    )
    raw_payload = b'RAW1' + struct.pack('>I', gradient.size) + gradient.tobytes()

    if len(mpo_payload) < len(raw_payload):
        return mpo_payload, {
            'format': 'MPO',
            'raw_bytes': len(raw_payload),
            'payload_bytes': len(mpo_payload),
            'saving_pct': round((1.0 - len(mpo_payload) / len(raw_payload)) * 100.0, 2),
            'reconstruction_error': float(compressed.reconstruction_error),
            'bond_dim': int(compressed.bond_dim),
        }
    return raw_payload, {
        'format': 'RAW',
        'raw_bytes': len(raw_payload),
        'payload_bytes': len(raw_payload),
        'saving_pct': 0.0,
        'reconstruction_error': 0.0,
        'bond_dim': None,
    }


def _deserialize_gradient(payload: bytes, compressor: MPOCompressor) -> np.ndarray:
    if payload.startswith(b'RAW1'):
        if len(payload) < 8:
            raise ValueError('RAW 梯度载荷过短')
        size = struct.unpack('>I', payload[4:8])[0]
        data = np.frombuffer(payload[8:], dtype='<f8')
        if len(data) != size:
            raise ValueError('RAW 梯度载荷长度不一致')
        return data.astype(np.float64, copy=True)

    if not payload.startswith(b'MPO1') or len(payload) < 8:
        raise ValueError('未知梯度载荷格式')
    header_size = struct.unpack('>I', payload[4:8])[0]
    header_end = 8 + header_size
    if header_end > len(payload):
        raise ValueError('MPO 梯度头部越界')
    metadata = json.loads(payload[8:header_end].decode('utf-8'))
    values = np.frombuffer(payload[header_end:], dtype='<f8')
    tensors = []
    offset = 0
    for shape in metadata['shapes']:
        count = int(np.prod(shape))
        if offset + count > len(values):
            raise ValueError('MPO 张量载荷长度不足')
        tensors.append(values[offset:offset + count].reshape(shape).astype(np.float64, copy=True))
        offset += count
    if offset != len(values):
        raise ValueError('MPO 张量载荷含多余数据')
    result = MPOCompressionResult(
        original_size=int(metadata['original_size']),
        compressed_size=int(metadata['compressed_size']),
        compression_ratio=float(metadata['compression_ratio']),
        reconstruction_error=float(metadata['reconstruction_error']),
        bond_dim=int(metadata['bond_dim']),
        mpo_tensors=tensors,
    )
    return compressor.decompress(result, result.original_size)


def run_single_hospital(dataset, rounds: int, batch_size: int,
                        learning_rate: float, seed: int) -> Dict:
    model = _make_model(len(dataset.feature_names), seed)
    rng = np.random.RandomState(seed + 11)
    X, y = dataset.client_data[0]
    history = []
    for round_index in range(rounds):
        X_batch, y_batch = _balanced_batch(X, y, batch_size, rng)
        gradient = _flatten_gradients(model.compute_gradients(X_batch, y_batch))
        model.load_flat_params(model.flatten_params() - learning_rate * gradient)
        metrics = evaluate_with_federated_threshold(
            model, [(X, y)], dataset.X_test, dataset.y_test
        )
        history.append({'round': round_index + 1, **metrics})
    return {
        'name': 'single_hospital',
        'description': '仅医院A本地训练（不共享原始数据）',
        'metrics': history[-1],
        'history': history,
    }


def run_plain_federated(dataset, rounds: int, batch_size: int,
                        learning_rate: float, seed: int) -> Dict:
    model = _make_model(len(dataset.feature_names), seed)
    server = FederatedLearningServer(model_template=model, n_clients=len(dataset.client_data))
    rngs = [np.random.RandomState(seed + 100 + i) for i in range(len(dataset.client_data))]
    history = []
    for round_index in range(rounds):
        batches = [
            _balanced_batch(X, y, batch_size, rngs[i])
            for i, (X, y) in enumerate(dataset.client_data)
        ]
        server.train_round(batches, lr=learning_rate)
        metrics = evaluate_with_federated_threshold(
            server.model, dataset.client_data, dataset.X_test, dataset.y_test
        )
        history.append({'round': round_index + 1, **metrics})
    return {
        'name': 'plain_federated',
        'description': '5家医院 FedAvg（无四层安全机制的效用上界）',
        'metrics': history[-1],
        'history': history,
    }


def _establish_channels(n_hospitals: int, seed: int) -> Tuple[List[QuantumCommunicationChannel], List[Dict]]:
    channels = []
    reports = []
    for hospital_id in range(n_hospitals):
        np.random.seed(seed + 1000 + hospital_id)
        channel = QuantumCommunicationChannel(n_photons=2048)
        report = channel.establish(eve_active=False)
        if report.get('status') != 'success':
            raise RuntimeError(f'医院{hospital_id} QKD 信道建立失败: {report}')
        channels.append(channel)
        reports.append({
            'hospital_id': hospital_id,
            'status': report['status'],
            'qber_pct': report['error_rate'],
            'sifted_key_length': report['sifted_key_length'],
            'final_key_bits': 256,
        })
    return channels, reports


def _eavesdropping_check(seed: int) -> Dict:
    np.random.seed(seed + 9999)
    attacked = QuantumCommunicationChannel(n_photons=4096)
    report = attacked.establish(eve_active=True)
    return {
        'status': report.get('status'),
        'qber_pct': report.get('error_rate'),
        'eavesdropping_detected': report.get('eavesdropping_detected', False),
        'key_discarded': report.get('final_key') is None,
    }


def _ciphertext_tampering_check(channel: QuantumCommunicationChannel) -> Dict:
    """模拟链路攻击者翻转密文一位，验证认证标签会在解密前拒绝载荷。"""
    sent = channel.secure_send_bytes(b'gradient-payload-integrity-check')
    if sent.get('status') != 'success':
        return {'tampering_rejected': False, 'reason': sent.get('reason')}
    tampered = bytearray(sent['encrypted_payload'])
    tampered[-1] ^= 0x01
    received = channel.secure_receive_bytes(bytes(tampered), sent['encryption_level'])
    return {
        'tampering_rejected': received.get('reason') == 'authentication_failed',
        'receiver_status': received.get('status'),
        'reason': received.get('reason'),
    }


def run_secure_federated(dataset, rounds: int, batch_size: int,
                         learning_rate: float, seed: int,
                         malicious_hospital: int | None,
                         local_epsilon: float = 0.5,
                         bond_dim: int = 16) -> Dict:
    n_hospitals = len(dataset.client_data)
    channels, qkd_reports = _establish_channels(n_hospitals, seed)
    eavesdropping = _eavesdropping_check(seed)
    ciphertext_tampering = _ciphertext_tampering_check(channels[0])
    model = _make_model(len(dataset.feature_names), seed)
    global_params = model.flatten_params().copy()
    rngs = [np.random.RandomState(seed + 200 + i) for i in range(n_hospitals)]
    compressors = [MPOCompressor(bond_dim=bond_dim) for _ in range(n_hospitals)]
    qdp_clients = []
    for hospital_id in range(n_hospitals):
        np.random.seed(seed + 300 + hospital_id)
        qdp_clients.append(QuantumDifferentialPrivacy(
            epsilon=rounds * local_epsilon + 1e-9,
            channel_ratio=0.65,
            sensitivity=2.0 / batch_size,
            clip_norm=1.0,
        ))

    consensus = QuantumByzantineConsensus(n_nodes=n_hospitals, n_qubits=256)
    ledger = SecureFederatedLedger(n_nodes=n_hospitals, blockchain_difficulty=2)
    history = []
    compression_records = []
    detected_total = 0
    authenticated_transmissions = 0
    rejected_transmissions = 0

    for round_index in range(rounds):
        received_gradients = []
        client_metadata = []
        malicious_nodes = [] if malicious_hospital is None else [malicious_hospital]

        for hospital_id, (X, y) in enumerate(dataset.client_data):
            local_model = _make_model(len(dataset.feature_names), seed + 5000 + hospital_id)
            local_model.load_flat_params(global_params)
            X_batch, y_batch = _balanced_batch(X, y, batch_size, rngs[hospital_id])
            gradient = _flatten_gradients(local_model.compute_gradients(X_batch, y_batch))
            gradient = qdp_clients[hospital_id].apply_privacy(
                gradient, local_epsilon=local_epsilon
            )

            # 恶意医院在隐私处理后反向放大梯度，并用不一致签名参与共识。
            if hospital_id == malicious_hospital:
                gradient = -25.0 * gradient

            payload, compression = _serialize_gradient(gradient, compressors[hospital_id])
            sent = channels[hospital_id].secure_send_bytes(payload, noise_level=0.05)
            if sent.get('status') != 'success':
                rejected_transmissions += 1
                continue
            received = channels[hospital_id].secure_receive_bytes(
                sent['encrypted_payload'], sent['encryption_level']
            )
            if received.get('status') != 'success':
                rejected_transmissions += 1
                continue
            authenticated_transmissions += 1
            received_gradient = _deserialize_gradient(received['payload'], compressors[hospital_id])
            received_gradients.append((hospital_id, received_gradient))
            wire_saving = (
                1.0 - sent['encrypted_size_bytes'] /
                max(1, compression['raw_bytes'] + 48)
            ) * 100.0
            record = {
                'round': round_index + 1,
                'hospital_id': hospital_id,
                **compression,
                'encrypted_wire_bytes': sent['encrypted_size_bytes'],
                'wire_saving_pct': round(wire_saving, 2),
                'authenticated': True,
            }
            compression_records.append(record)
            client_metadata.append({
                'client_id': hospital_id,
                'hospital_name': dataset.hospital_summaries[hospital_id]['name'],
                'batch_size': batch_size,
                'payload_hash': hashlib.sha256(payload).hexdigest(),
                'payload_bytes': compression['payload_bytes'],
                'mpo_saving_pct': compression['saving_pct'],
                'qkd_qber_pct': qkd_reports[hospital_id]['qber_pct'],
                'authenticated': True,
            })

        bundle_hash = hashlib.sha256(
            b''.join(gradient.tobytes() for _, gradient in received_gradients)
        ).hexdigest()
        consensus_result = consensus.reach_consensus(bundle_hash, malicious_nodes=malicious_nodes)
        detected = set(consensus_result['detected_malicious'])
        detected_total += len(detected & set(malicious_nodes))
        accepted = [gradient for node_id, gradient in received_gradients if node_id not in detected]
        if not accepted:
            raise RuntimeError(f'第 {round_index + 1} 轮没有可聚合的诚实梯度')

        # 签名投票先剔除异常节点，逐坐标中位数再提供第二道鲁棒聚合保护。
        aggregate = np.median(np.vstack(accepted), axis=0)
        global_params -= learning_rate * aggregate
        model.load_flat_params(global_params)
        metrics = evaluate_with_federated_threshold(
            model, dataset.client_data, dataset.X_test, dataset.y_test
        )

        ledger_result = ledger.record_round(
            round_num=round_index + 1,
            model_params=global_params,
            client_metadata=client_metadata,
            model_accuracy=metrics['balanced_accuracy'],
            malicious_nodes=malicious_nodes,
        )
        history.append({
            'round': round_index + 1,
            **metrics,
            'detected_malicious': sorted(detected),
            'consensus_reached': bool(consensus_result['consensus_reached']),
            'block_index': ledger_result.get('block_index'),
        })

    chain_valid, chain_message = ledger.blockchain.validate_chain()
    used_mpo = [record for record in compression_records if record['format'] == 'MPO']
    avg_saving = float(np.mean([r['saving_pct'] for r in compression_records]))
    avg_wire_saving = float(np.mean([r['wire_saving_pct'] for r in compression_records]))
    max_reconstruction_error = max(r['reconstruction_error'] for r in compression_records)
    return {
        'name': 'secure_federated',
        'description': 'QKD认证加密 + 量子差分隐私 + MPO + 拜占庭共识 + 区块链',
        'metrics': history[-1],
        'history': history,
        'security': {
            'implementation_scope': 'local software simulation; not quantum hardware',
            'qkd_channels': qkd_reports,
            'eavesdropping_test': eavesdropping,
            'ciphertext_tampering_test': ciphertext_tampering,
            'authenticated_transmissions': authenticated_transmissions,
            'rejected_transmissions': rejected_transmissions,
            'qdp': {
                'local_epsilon_per_round': local_epsilon,
                'delta': qdp_clients[0].budget.delta,
                'per_hospital_reports': [qdp.get_privacy_report() for qdp in qdp_clients],
            },
            'mpo': {
                'bond_dim': bond_dim,
                'mpo_transmission_rate_pct': round(len(used_mpo) / len(compression_records) * 100.0, 2),
                'average_payload_saving_pct': round(avg_saving, 2),
                'average_wire_saving_pct': round(avg_wire_saving, 2),
                'max_reconstruction_mse': max_reconstruction_error,
            },
            'byzantine': {
                'malicious_hospital': malicious_hospital,
                'max_malicious_tolerated': consensus.max_malicious,
                'rounds_detected': detected_total,
                'rounds_total': rounds if malicious_hospital is not None else 0,
            },
            'blockchain': {
                **ledger.blockchain.get_chain_summary(),
                'validation': chain_message,
                'all_rounds_recorded': len(ledger.model_records) == rounds,
                'valid': chain_valid,
            },
        },
        'compression_records': compression_records,
    }


def _print_dataset_summary(dataset) -> None:
    metadata = dataset.metadata
    print('\n[真实数据集]')
    print(f'  {metadata["dataset_name"]}')
    print(f'  原始住院记录: {metadata["raw_encounters"]:,} | 特征维度: {metadata["feature_count"]}')
    print(
        f'  训练: {metadata["train_encounters"]:,} | 测试: {metadata["test_encounters"]:,} | '
        f'患者跨集合泄漏: {metadata["patient_leakage_count"]}'
    )
    for summary in dataset.hospital_summaries:
        print(
            f'  {summary["name"]}: {summary["encounters"]:,} 条记录 / '
            f'{summary["unique_patients"]:,} 位患者 / '
            f'30日再入院率 {summary["positive_rate_pct"]:.2f}%'
        )


def _print_comparison(results: Sequence[Dict]) -> None:
    print('\n[模型对照：同一患者级留出测试集]')
    print('  {:<20} {:>9} {:>9} {:>9} {:>9} {:>9}'.format(
        '方案', '准确率', '平衡准确率', '召回率', 'F1', 'ROC-AUC'
    ))
    for result in results:
        metrics = result['metrics']
        print('  {:<20} {:>8.2f}% {:>8.2f}% {:>8.2f}% {:>8.2f}% {:>9.4f}'.format(
            result['name'], metrics['accuracy'], metrics['balanced_accuracy'],
            metrics['recall'], metrics['f1'], metrics['roc_auc']
        ))


def _write_outputs(output_dir: Path, dataset, results: Sequence[Dict],
                   config: Dict, elapsed_seconds: float) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S %z'),
        'elapsed_seconds': round(elapsed_seconds, 3),
        'clinical_use_warning': 'Research simulation only; not for clinical decision-making.',
        'config': config,
        'dataset': {
            **dataset.metadata,
            'hospital_summaries': dataset.hospital_summaries,
            'feature_names': dataset.feature_names,
        },
        'results': [{k: v for k, v in result.items() if k != 'compression_records'} for result in results],
    }
    json_path = output_dir / 'medical_federated_results.json'
    json_path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=lambda value: value.item() if isinstance(value, np.generic) else str(value),
        ),
        encoding='utf-8'
    )

    csv_path = output_dir / 'training_history.csv'
    with csv_path.open('w', encoding='utf-8', newline='') as target:
        fieldnames = [
            'scheme', 'round', 'accuracy', 'balanced_accuracy', 'precision',
            'recall', 'specificity', 'f1', 'roc_auc', 'positive_prediction_rate'
        ]
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            for row in result['history']:
                writer.writerow({
                    'scheme': result['name'],
                    **{key: row.get(key) for key in fieldnames if key != 'scheme'}
                })
    return json_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='运行真实医疗数据上的五医院量子安全联邦学习演示'
    )
    parser.add_argument('--rounds', type=int, default=100, help='训练轮数（默认 100）')
    parser.add_argument('--batch-size', type=int, default=1024, help='每家医院每轮本地批量')
    parser.add_argument('--learning-rate', type=float, default=0.2, help='学习率')
    parser.add_argument('--seed', type=int, default=2026, help='可复现实验随机种子')
    parser.add_argument(
        '--malicious-hospital', type=int, default=4,
        help='恶意医院编号 0-4；设为 -1 表示不注入攻击（默认 4，即医院E）'
    )
    parser.add_argument('--local-epsilon', type=float, default=0.5, help='每家医院每轮隐私预算 ε')
    parser.add_argument('--bond-dim', type=int, default=16, help='MPO 最大键维度')
    parser.add_argument('--force-download', action='store_true', help='强制重新下载 UCI 数据')
    parser.add_argument(
        '--output-dir', type=Path,
        default=PROJECT_ROOT / 'artifacts' / 'medical_demo',
        help='结果输出目录'
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.rounds < 1 or args.batch_size < 16 or args.learning_rate <= 0:
        raise ValueError('rounds>=1、batch-size>=16 且 learning-rate>0')
    if args.local_epsilon <= 0 or args.bond_dim < 1:
        raise ValueError('local-epsilon 和 bond-dim 必须为正数')
    malicious_hospital = None if args.malicious_hospital < 0 else args.malicious_hospital
    if malicious_hospital is not None and malicious_hospital not in range(5):
        raise ValueError('malicious-hospital 必须是 -1 或 0-4')

    started = time.time()
    print('=' * 76)
    print('  五医院糖尿病患者 30 日再入院风险：量子安全联邦学习真实数据演示')
    print('  注意：量子与链上模块均为软件仿真；本程序不能用于临床决策')
    print('=' * 76)
    csv_path = download_diabetes_dataset(PROJECT_ROOT, force=args.force_download)
    dataset = load_federated_diabetes_data(csv_path, n_hospitals=5, seed=args.seed)
    _print_dataset_summary(dataset)

    print('\n[训练] 单医院基线...')
    single = run_single_hospital(
        dataset, args.rounds, args.batch_size, args.learning_rate, args.seed
    )
    print('[训练] 五医院普通 FedAvg...')
    plain = run_plain_federated(
        dataset, args.rounds, args.batch_size, args.learning_rate, args.seed
    )
    print('[训练] 五医院四层安全联邦学习...')
    secure = run_secure_federated(
        dataset, args.rounds, args.batch_size, args.learning_rate, args.seed,
        malicious_hospital=malicious_hospital,
        local_epsilon=args.local_epsilon,
        bond_dim=args.bond_dim,
    )
    results = [single, plain, secure]
    _print_comparison(results)

    security = secure['security']
    print('\n[四层防线验证]')
    print(
        f'  1. QKD: {len(security["qkd_channels"])} 条信道建立成功；'
        f'窃听检测={security["eavesdropping_test"]["eavesdropping_detected"]}，'
        f'被攻击密钥丢弃={security["eavesdropping_test"]["key_discarded"]}，'
        f'密文篡改拒绝={security["ciphertext_tampering_test"]["tampering_rejected"]}'
    )
    print(
        f'  2. QDP: 每院每轮 ε={security["qdp"]["local_epsilon_per_round"]}，'
        f'共注入 {sum(r["noise_rounds"] for r in security["qdp"]["per_hospital_reports"])} 次噪声'
    )
    print(
        f'  3. MPO+共识: 平均载荷节省 {security["mpo"]["average_payload_saving_pct"]:.2f}%；'
        f'恶意医院被识别 {security["byzantine"]["rounds_detected"]}/'
        f'{security["byzantine"]["rounds_total"]} 轮'
    )
    print(
        f'  4. 区块链: 链长 {security["blockchain"]["length"]}，'
        f'完整性验证={security["blockchain"]["valid"]}'
    )

    config = {
        'rounds': args.rounds,
        'batch_size_per_hospital': args.batch_size,
        'learning_rate': args.learning_rate,
        'seed': args.seed,
        'malicious_hospital': malicious_hospital,
        'local_epsilon_per_round': args.local_epsilon,
        'mpo_bond_dim': args.bond_dim,
        'decision_threshold_calibration': (
            'federated training confusion-count aggregation; objective=accuracy'
        ),
    }
    json_path = _write_outputs(args.output_dir, dataset, results, config, time.time() - started)
    print(f'\n结果已保存: {json_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
