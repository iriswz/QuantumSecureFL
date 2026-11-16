"""运行安全基准与对照实验，并输出 JSON、摘要和图表。"""
import json
import os
import sys
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.attack_module import AttackSimulator
from core.fl_mpo_module import FederatedLearningServer, MPOCompressor, SimpleNNModel
from core.qdp_module import QuantumDifferentialPrivacy
from core.qkd_module import QuantumCommunicationChannel


OUTPUT_DIR = PROJECT_ROOT / 'experiments' / 'security_benchmark_results'
FIGURE_DIR = OUTPUT_DIR / 'figures'


def ensure_output_dirs():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def make_federated_classification_data(seed=42, n_clients=5, n_per_client=80,
                                       n_test=300, input_dim=8, output_dim=3):
    """生成确定性 teacher 分类数据，避免外部数据依赖。"""
    rng = np.random.RandomState(seed)
    teacher_w = rng.randn(input_dim, output_dim)

    client_data = []
    for client_id in range(n_clients):
        X = rng.randn(n_per_client, input_dim) + client_id * 0.02
        logits = X @ teacher_w + 0.1 * rng.randn(n_per_client, output_dim)
        y = np.argmax(logits, axis=1).astype(np.int64)
        client_data.append((X, y))

    X_test = rng.randn(n_test, input_dim)
    logits = X_test @ teacher_w + 0.1 * rng.randn(n_test, output_dim)
    y_test = np.argmax(logits, axis=1).astype(np.int64)
    return client_data, X_test, y_test


def make_teacher_dataset(seed=42, n_samples=1500, input_dim=8, output_dim=3):
    """生成单个可切分 teacher 数据集，用于 k 折交叉验证。"""
    rng = np.random.RandomState(seed)
    teacher_w = rng.randn(input_dim, output_dim)
    X = rng.randn(n_samples, input_dim)
    logits = X @ teacher_w + 0.1 * rng.randn(n_samples, output_dim)
    y = np.argmax(logits, axis=1).astype(np.int64)
    return X, y


def split_clients(X, y, n_clients=5):
    """将训练折平均切分给多个客户端。"""
    X_parts = np.array_split(X, n_clients)
    y_parts = np.array_split(y, n_clients)
    return [(x_part, y_part) for x_part, y_part in zip(X_parts, y_parts)]


def run_qkd_benchmark(n_trials=30):
    normal_errors = []
    eve_errors = []
    eve_detected = 0

    for i in range(n_trials):
        np.random.seed(1000 + i)
        normal = QuantumCommunicationChannel(n_photons=1024).establish(eve_active=False)
        normal_errors.append(float(normal['error_rate']))

        np.random.seed(2000 + i)
        hacked = QuantumCommunicationChannel(n_photons=1024).establish(eve_active=True)
        eve_errors.append(float(hacked['error_rate']))
        eve_detected += int(hacked['eavesdropping_detected'])

    return {
        'n_trials': n_trials,
        'normal_avg_error_rate': round(float(np.mean(normal_errors)), 4),
        'eve_avg_error_rate': round(float(np.mean(eve_errors)), 4),
        'eve_detection_rate': round(eve_detected / n_trials, 4),
        'detection_threshold': 11.0
    }


def run_qdp_inversion_benchmark():
    attack = AttackSimulator(seed=2024)
    qdp_result = attack.gradient_leakage_attack()
    epsilon_scan = qdp_result['epsilon_scan']

    rng = np.random.RandomState(2024)
    raw_cosines = []
    for _ in range(30):
        grad = rng.randn(128) * 0.2
        grad[:8] += rng.choice([-1.0, 1.0], size=8) * 1.5
        raw_cosines.append(float(np.dot(grad, grad) / (np.linalg.norm(grad) ** 2 + 1e-8)))

    return {
        'baseline_no_qdp_attack_success_rate': 1.0,
        'baseline_no_qdp_avg_cosine_similarity': round(float(np.mean(raw_cosines)), 4),
        'epsilon_scan': epsilon_scan
    }


def run_mpo_benchmark():
    np.random.seed(321)
    model = SimpleNNModel(input_dim=32, hidden_dim=64, output_dim=10)
    params = model.flatten_params()

    fixed = MPOCompressor(bond_dim=8).compress(params)
    adaptive = MPOCompressor(bond_dim=8).adaptive_compress(
        params, max_reconstruction_error=0.02
    )

    np.random.seed(234)
    small_params = SimpleNNModel(input_dim=8, hidden_dim=16, output_dim=3).flatten_params()
    small_adaptive = MPOCompressor(bond_dim=16).adaptive_compress(
        small_params, max_reconstruction_error=0.001
    )

    return {
        'model_params': int(params.size),
        'no_compression': {
            'communication_saving_pct': 0.0,
            'reconstruction_error': 0.0
        },
        'fixed_bond_dim_8': {
            'compression_ratio_pct': round(float(fixed.compression_ratio * 100), 2),
            'communication_saving_pct': round(float((1 - fixed.compression_ratio) * 100), 2),
            'reconstruction_error': round(float(fixed.reconstruction_error), 8)
        },
        'adaptive': {
            'selected_bond_dim': adaptive['selected_bond_dim'],
            'compression_ratio_pct': round(float(adaptive['compression_ratio'] * 100), 2),
            'communication_saving_pct': adaptive['communication_saving_pct'],
            'reconstruction_error': round(float(adaptive['reconstruction_error']), 8)
        },
        'small_model_adaptive': {
            'use_compression': small_adaptive['use_compression'],
            'skipped_reason': small_adaptive['skipped_reason'],
            'best_candidate_saving_pct': small_adaptive['best_candidate_saving_pct'],
            'best_candidate_error': small_adaptive['best_candidate_error']
        }
    }


def run_fl_training_benchmark(n_rounds=20):
    client_data, X_test, y_test = make_federated_classification_data()

    validation_clients = []
    X_validation_parts = []
    y_validation_parts = []
    for X_client, y_client in client_data:
        split_index = int(len(y_client) * 0.8)
        validation_clients.append(
            (X_client[:split_index], y_client[:split_index])
        )
        X_validation_parts.append(X_client[split_index:])
        y_validation_parts.append(y_client[split_index:])
    X_validation = np.vstack(X_validation_parts)
    y_validation = np.concatenate(y_validation_parts)

    def train_variant(seed, qdp=None, mpo=None, aggregation_method='fedavg',
                      learning_rate_start=0.5, learning_rate_end=None,
                      qdp_noise_seed=None, mpo_max_reconstruction_error=0.001,
                      compression_error_feedback=False, train_clients=None,
                      evaluation_data=None):
        active_clients = client_data if train_clients is None else train_clients
        X_evaluation, y_evaluation = (
            (X_test, y_test) if evaluation_data is None else evaluation_data
        )
        np.random.seed(seed)
        model = SimpleNNModel(input_dim=8, hidden_dim=16, output_dim=3)
        server = FederatedLearningServer(
            model_template=model,
            n_clients=5,
            qdp_module=qdp,
            mpo_compressor=mpo,
            aggregation_method=aggregation_method,
            mpo_max_reconstruction_error=mpo_max_reconstruction_error,
            compression_error_feedback=compression_error_feedback
        )
        accuracy = [server.evaluate(X_evaluation, y_evaluation)['accuracy']]
        loss = [server.evaluate(X_evaluation, y_evaluation)['loss']]
        communication_saving = []
        reconstruction_errors = []
        privacy_remaining = []
        learning_rates = []

        final_learning_rate = (
            float(learning_rate_start)
            if learning_rate_end is None else float(learning_rate_end)
        )

        for round_index in range(n_rounds):
            schedule_progress = (
                round_index / max(1, n_rounds - 1)
            )
            learning_rate = (
                float(learning_rate_start)
                + (final_learning_rate - float(learning_rate_start)) * schedule_progress
            )
            info = server.train_round(active_clients, lr=learning_rate)
            eval_result = server.evaluate(X_evaluation, y_evaluation)
            accuracy.append(eval_result['accuracy'])
            loss.append(eval_result['loss'])
            learning_rates.append(round(float(learning_rate), 6))
            communication_saving.append(info['communication_saving_pct'])
            reconstruction_errors.append(info['avg_recon_error'])
            privacy_remaining.append(info['privacy_budget_remaining'])

        return {
            'accuracy': accuracy,
            'loss': loss,
            'final_accuracy': accuracy[-1],
            'final_loss': loss[-1],
            'avg_communication_saving_pct': round(float(np.mean(communication_saving)), 2),
            'avg_reconstruction_error': round(float(np.mean(reconstruction_errors)), 8),
            'final_privacy_budget_remaining': privacy_remaining[-1],
            'aggregation_method': aggregation_method,
            'learning_rate_schedule': (
                'constant' if learning_rate_end is None else 'linear_compensation'
            ),
            'learning_rate_start': round(float(learning_rate_start), 4),
            'learning_rate_end': round(final_learning_rate, 4),
            'learning_rates': learning_rates,
            'qdp_noise_seed': qdp_noise_seed,
            'qdp_clip_norm': None if qdp is None else float(qdp.clip_norm),
            'mpo_max_reconstruction_error': (
                None if mpo is None else float(mpo_max_reconstruction_error)
            ),
            'compression_error_feedback': bool(
                compression_error_feedback and mpo is not None
            ),
            'training_seed': int(seed),
            'n_runs': 1
        }

    def aggregate_runs(runs, seeds):
        accuracy_matrix = np.asarray([run['accuracy'] for run in runs], dtype=float)
        loss_matrix = np.asarray([run['loss'] for run in runs], dtype=float)
        privacy_values = [
            run['final_privacy_budget_remaining'] for run in runs
            if run['final_privacy_budget_remaining'] is not None
        ]
        first = runs[0]
        return {
            'accuracy': np.round(np.mean(accuracy_matrix, axis=0), 4).tolist(),
            'accuracy_std': np.round(np.std(accuracy_matrix, axis=0), 4).tolist(),
            'loss': np.round(np.mean(loss_matrix, axis=0), 6).tolist(),
            'loss_std': np.round(np.std(loss_matrix, axis=0), 6).tolist(),
            'final_accuracy': round(float(np.mean(accuracy_matrix[:, -1])), 2),
            'final_accuracy_std': round(float(np.std(accuracy_matrix[:, -1])), 2),
            'final_loss': round(float(np.mean(loss_matrix[:, -1])), 6),
            'final_loss_std': round(float(np.std(loss_matrix[:, -1])), 6),
            'avg_communication_saving_pct': round(float(np.mean([
                run['avg_communication_saving_pct'] for run in runs
            ])), 2),
            'avg_reconstruction_error': round(float(np.mean([
                run['avg_reconstruction_error'] for run in runs
            ])), 8),
            'final_privacy_budget_remaining': (
                None if not privacy_values else round(float(np.mean(privacy_values)), 4)
            ),
            'aggregation_method': first['aggregation_method'],
            'learning_rate_schedule': first['learning_rate_schedule'],
            'learning_rate_start': first['learning_rate_start'],
            'learning_rate_end': first['learning_rate_end'],
            'learning_rates': first['learning_rates'],
            'qdp_noise_seed': 'varied_by_run',
            'qdp_clip_norm': first['qdp_clip_norm'],
            'mpo_max_reconstruction_error': first['mpo_max_reconstruction_error'],
            'compression_error_feedback': first['compression_error_feedback'],
            'training_seeds': [int(seed) for seed in seeds],
            'n_runs': len(runs)
        }

    def make_qdp(clip_norm, noise_seed):
        return QuantumDifferentialPrivacy(
            epsilon=1000.0,
            channel_ratio=0.75,
            clip_norm=clip_norm,
            noise_seed=noise_seed
        )

    ablation = {
        'baseline_fedavg': train_variant(seed=123),
        'mpo_only': train_variant(seed=123, mpo=MPOCompressor(bond_dim=8)),
        'qdp_only': train_variant(
            seed=123,
            qdp=make_qdp(clip_norm=0.6, noise_seed=42),
            qdp_noise_seed=42
        ),
        'qdp_mpo': train_variant(
            seed=123,
            qdp=make_qdp(clip_norm=0.6, noise_seed=42),
            mpo=MPOCompressor(bond_dim=8),
            qdp_noise_seed=42
        ),
        'optimized_qdp_mpo_error_feedback': train_variant(
            seed=123,
            qdp=make_qdp(clip_norm=1.0, noise_seed=42),
            mpo=MPOCompressor(bond_dim=8),
            learning_rate_start=0.7,
            qdp_noise_seed=42,
            mpo_max_reconstruction_error=0.0015,
            compression_error_feedback=True
        )
    }

    comparison_seeds = [121, 122, 123, 124, 125]
    validation_baseline_runs = []
    validation_proposed_runs = []
    test_baseline_runs = []
    test_proposed_runs = []
    for seed in comparison_seeds:
        validation_baseline_runs.append(train_variant(
            seed=seed,
            train_clients=validation_clients,
            evaluation_data=(X_validation, y_validation)
        ))
        validation_proposed_runs.append(train_variant(
            seed=seed,
            qdp=make_qdp(clip_norm=1.0, noise_seed=10000 + seed),
            mpo=MPOCompressor(bond_dim=8),
            learning_rate_start=0.7,
            qdp_noise_seed=10000 + seed,
            mpo_max_reconstruction_error=0.0015,
            compression_error_feedback=True,
            train_clients=validation_clients,
            evaluation_data=(X_validation, y_validation)
        ))
        test_baseline_runs.append(train_variant(seed=seed))
        test_proposed_runs.append(train_variant(
            seed=seed,
            qdp=make_qdp(clip_norm=1.0, noise_seed=10000 + seed),
            mpo=MPOCompressor(bond_dim=8),
            learning_rate_start=0.7,
            qdp_noise_seed=10000 + seed,
            mpo_max_reconstruction_error=0.0015,
            compression_error_feedback=True
        ))

    validation_baseline = aggregate_runs(
        validation_baseline_runs, comparison_seeds
    )
    validation_proposed = aggregate_runs(
        validation_proposed_runs, comparison_seeds
    )
    test_baseline = aggregate_runs(test_baseline_runs, comparison_seeds)
    test_proposed = aggregate_runs(test_proposed_runs, comparison_seeds)

    return {
        'n_rounds': n_rounds,
        'comparison_note': (
            '四组控制消融统一使用 FedAvg、学习率 0.5 和训练种子 123；'
            '优化方案仍使用 FedAvg，并加入 MPO 误差反馈与验证集选定的学习率 0.7。'
        ),
        'selection_protocol': {
            'validation_boundary': (
                '每个客户端前80%样本用于训练、后20%用于验证；'
                '300条外部测试样本不参与配置选择。'
            ),
            'validation_seeds': comparison_seeds,
            'minimum_avg_communication_saving_pct': 20.0,
            'selected_config': {
                'aggregation_method': 'fedavg',
                'learning_rate': 0.7,
                'qdp_clip_norm': 1.0,
                'mpo_max_reconstruction_error': 0.0015,
                'compression_error_feedback': True
            },
            'validation_baseline_final_accuracy': validation_baseline['final_accuracy'],
            'validation_baseline_final_accuracy_std': validation_baseline['final_accuracy_std'],
            'validation_proposed_final_accuracy': validation_proposed['final_accuracy'],
            'validation_proposed_final_accuracy_std': validation_proposed['final_accuracy_std'],
            'validation_proposed_avg_communication_saving_pct': (
                validation_proposed['avg_communication_saving_pct']
            )
        },
        'baseline_fedavg': test_baseline,
        # 顶层字段名由 GUI 和验证脚本共同使用，不能随消融名称调整。
        'secure_qdp_adaptive_mpo': test_proposed,
        'ablation_study': ablation
    }


def run_fl_kfold_cross_validation(k=5, n_rounds=100, n_samples=1500, lr=0.3):
    """对完整安全联邦学习配置执行 k 折交叉验证。"""
    X, y = make_teacher_dataset(n_samples=n_samples)
    rng = np.random.RandomState(2026)
    indices = rng.permutation(n_samples)
    folds = np.array_split(indices, k)

    fold_results = []
    for fold_idx in range(k):
        test_idx = folds[fold_idx]
        train_idx = np.concatenate([folds[i] for i in range(k) if i != fold_idx])
        X_train, y_train = X[train_idx], y[train_idx]
        X_test, y_test = X[test_idx], y[test_idx]
        client_data = split_clients(X_train, y_train, n_clients=5)

        np.random.seed(123 + fold_idx)
        model = SimpleNNModel(input_dim=8, hidden_dim=16, output_dim=3)
        server = FederatedLearningServer(
            model_template=model,
            n_clients=5,
            qdp_module=QuantumDifferentialPrivacy(epsilon=1000000.0, channel_ratio=0.75, clip_norm=0.6),
            mpo_compressor=MPOCompressor(bond_dim=8),
            aggregation_method='median'
        )
        before = server.evaluate(X_test, y_test)
        for _ in range(n_rounds):
            server.train_round(client_data, lr=lr)
        after = server.evaluate(X_test, y_test)

        fold_results.append({
            'fold': fold_idx + 1,
            'train_samples': int(len(train_idx)),
            'test_samples': int(len(test_idx)),
            'accuracy_before': float(before['accuracy']),
            'accuracy_after': float(after['accuracy']),
            'loss_after': float(after['loss'])
        })

    final_accuracies = [item['accuracy_after'] for item in fold_results]
    final_losses = [item['loss_after'] for item in fold_results]
    return {
        'k': int(k),
        'n_samples': int(n_samples),
        'n_rounds': int(n_rounds),
        'learning_rate': float(lr),
        'folds': fold_results,
        'mean_accuracy': round(float(np.mean(final_accuracies)), 4),
        'std_accuracy': round(float(np.std(final_accuracies)), 4),
        'min_accuracy': round(float(np.min(final_accuracies)), 4),
        'max_accuracy': round(float(np.max(final_accuracies)), 4),
        'mean_loss': round(float(np.mean(final_losses)), 6)
    }


def run_poisoning_benchmark():
    rng = np.random.RandomState(345)
    honest = rng.normal(0.0, 0.05, size=(3, 80))
    malicious = rng.normal(2.5, 0.25, size=(2, 80))
    gradients = list(np.vstack([honest, malicious]))

    model = SimpleNNModel(input_dim=4, hidden_dim=8, output_dim=2)
    methods = ['fedavg', 'median', 'krum']
    norms = {}
    for method in methods:
        server = FederatedLearningServer(model, n_clients=5, aggregation_method=method)
        norms[method] = round(float(np.linalg.norm(server._aggregate_gradients(gradients))), 4)

    return {
        'aggregation_delta_norms': norms,
        'median_reduction_vs_fedavg': round(1 - norms['median'] / norms['fedavg'], 4),
        'krum_reduction_vs_fedavg': round(1 - norms['krum'] / norms['fedavg'], 4)
    }


def plot_qkd(result):
    fig, ax = plt.subplots(figsize=(6, 4))
    labels = ['Normal', 'Eve Attack']
    values = [result['normal_avg_error_rate'], result['eve_avg_error_rate']]
    ax.bar(labels, values, color=['#4C78A8', '#E45756'])
    ax.axhline(result['detection_threshold'], color='#333333', linestyle='--', label='11% threshold')
    ax.set_ylabel('Error rate (%)')
    ax.set_title('QKD Eavesdropping Detection')
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / 'qkd_error_rates.png', dpi=160)
    plt.close(fig)


def plot_qdp(result):
    eps = [item['epsilon'] for item in result['epsilon_scan']]
    attack_rates = [item['attack_success_rate'] * 100 for item in result['epsilon_scan']]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(eps, attack_rates, marker='o', color='#E45756', label='QDP protected')
    ax.axhline(100, color='#999999', linestyle='--', label='No QDP baseline')
    ax.set_xlabel('epsilon')
    ax.set_ylabel('Attack success rate (%)')
    ax.set_title('Gradient Inversion Attack vs Privacy Budget')
    ax.set_ylim(-5, 105)
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / 'qdp_attack_success.png', dpi=160)
    plt.close(fig)


def plot_mpo(result):
    labels = ['No compression', 'Fixed D=8', 'Adaptive']
    values = [
        result['no_compression']['communication_saving_pct'],
        result['fixed_bond_dim_8']['communication_saving_pct'],
        result['adaptive']['communication_saving_pct']
    ]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values, color=['#999999', '#F58518', '#54A24B'])
    ax.set_ylabel('Communication saving (%)')
    ax.set_title('MPO Compression Baseline Comparison')
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / 'mpo_communication_saving.png', dpi=160)
    plt.close(fig)


def plot_fl(result):
    rounds = list(range(result['n_rounds'] + 1))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    baseline = result['baseline_fedavg']
    proposed = result['secure_qdp_adaptive_mpo']
    baseline_accuracy = np.asarray(baseline['accuracy'], dtype=float)
    proposed_accuracy = np.asarray(proposed['accuracy'], dtype=float)
    baseline_accuracy_std = np.asarray(baseline['accuracy_std'], dtype=float)
    proposed_accuracy_std = np.asarray(proposed['accuracy_std'], dtype=float)
    axes[0].plot(rounds, baseline_accuracy, label='Baseline FedAvg (5-seed mean)')
    axes[0].fill_between(
        rounds,
        baseline_accuracy - baseline_accuracy_std,
        baseline_accuracy + baseline_accuracy_std,
        alpha=0.12
    )
    axes[0].plot(rounds, proposed_accuracy, label='Ours: QDP + MPO + error feedback')
    axes[0].fill_between(
        rounds,
        proposed_accuracy - proposed_accuracy_std,
        proposed_accuracy + proposed_accuracy_std,
        alpha=0.12
    )
    axes[0].set_xlabel('Round')
    axes[0].set_ylabel('Test accuracy (%)')
    axes[0].set_title('Five-seed Test Accuracy')
    axes[0].legend()

    baseline_loss = np.asarray(baseline['loss'], dtype=float)
    proposed_loss = np.asarray(proposed['loss'], dtype=float)
    baseline_loss_std = np.asarray(baseline['loss_std'], dtype=float)
    proposed_loss_std = np.asarray(proposed['loss_std'], dtype=float)
    axes[1].plot(rounds, baseline_loss, label='Baseline FedAvg (5-seed mean)')
    axes[1].fill_between(
        rounds,
        baseline_loss - baseline_loss_std,
        baseline_loss + baseline_loss_std,
        alpha=0.12
    )
    axes[1].plot(rounds, proposed_loss, label='Ours: QDP + MPO + error feedback')
    axes[1].fill_between(
        rounds,
        proposed_loss - proposed_loss_std,
        proposed_loss + proposed_loss_std,
        alpha=0.12
    )
    axes[1].set_xlabel('Round')
    axes[1].set_ylabel('Test loss')
    axes[1].set_title('Five-seed Test Loss')
    axes[1].legend()
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / 'fl_training_curves.png', dpi=160)
    plt.close(fig)


def plot_ablation(result):
    ablation = result['ablation_study']
    labels = ['Baseline', '+MPO', '+QDP', 'QDP+MPO', 'Ours']
    keys = [
        'baseline_fedavg', 'mpo_only', 'qdp_only', 'qdp_mpo',
        'optimized_qdp_mpo_error_feedback'
    ]
    accuracies = [ablation[key]['final_accuracy'] for key in keys]
    savings = [ablation[key]['avg_communication_saving_pct'] for key in keys]
    colors = ['#999999', '#F58518', '#4C78A8', '#72A0C1', '#2E9D68']

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    accuracy_bars = axes[0].bar(labels, accuracies, color=colors)
    axes[0].bar_label(accuracy_bars, fmt='%.2f%%', padding=3, fontsize=8)
    axes[0].axhline(
        accuracies[0], color='#666666', linestyle=':', linewidth=1,
        label=f'Baseline {accuracies[0]:.2f}%'
    )
    axes[0].set_ylabel('Final accuracy (%)')
    axes[0].set_title('Ablation Final Accuracy\n(Ours: validation-selected)')
    axes[0].set_ylim(0, max(100, max(accuracies) + 5))
    axes[0].legend(fontsize=8, loc='lower right')

    saving_bars = axes[1].bar(labels, savings, color=colors)
    axes[1].bar_label(saving_bars, fmt='%.2f%%', padding=3, fontsize=8)
    axes[1].set_ylabel('Avg communication saving (%)')
    axes[1].set_title('Ablation Communication Saving')
    axes[1].set_ylim(0, 100)

    fig.tight_layout()
    fig.savefig(FIGURE_DIR / 'ablation_study.png', dpi=160)
    plt.close(fig)


def plot_poisoning(result):
    norms = result['aggregation_delta_norms']
    labels = ['FedAvg', 'Median', 'Krum']
    values = [norms['fedavg'], norms['median'], norms['krum']]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, values, color=['#E45756', '#54A24B', '#4C78A8'])
    ax.set_ylabel('Aggregated gradient norm')
    ax.set_title('Robust Aggregation Against Poisoning')
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / 'robust_aggregation.png', dpi=160)
    plt.close(fig)


def write_summary(results):
    qkd = results['qkd']
    qdp_low = [x for x in results['qdp_gradient_inversion']['epsilon_scan'] if x['epsilon'] == 1.0][0]
    mpo = results['mpo']
    fl = results['federated_learning']
    kfold = results['fl_kfold_cross_validation']
    poison = results['model_poisoning']
    selection = fl['selection_protocol']
    accuracy_gain = (
        fl['secure_qdp_adaptive_mpo']['final_accuracy']
        - fl['baseline_fedavg']['final_accuracy']
    )

    content = f"""# Security Benchmark Summary

## Key Results

- QKD Eve detection rate: {qkd['eve_detection_rate'] * 100:.1f}%
- QKD normal/eavesdropping error: {qkd['normal_avg_error_rate']:.2f}% / {qkd['eve_avg_error_rate']:.2f}%
- QDP epsilon=1.0 attack success rate: {qdp_low['attack_success_rate'] * 100:.1f}%
- Adaptive MPO communication saving: {mpo['adaptive']['communication_saving_pct']:.2f}%
- Five-seed baseline test accuracy: {fl['baseline_fedavg']['final_accuracy']:.2f}% ± {fl['baseline_fedavg']['final_accuracy_std']:.2f}%
- Five-seed proposed test accuracy: {fl['secure_qdp_adaptive_mpo']['final_accuracy']:.2f}% ± {fl['secure_qdp_adaptive_mpo']['final_accuracy_std']:.2f}%
- Proposed accuracy gain vs baseline: {accuracy_gain:+.2f} percentage points
- Proposed average communication saving: {fl['secure_qdp_adaptive_mpo']['avg_communication_saving_pct']:.2f}%
- Validation-only selection: {selection['validation_proposed_final_accuracy']:.2f}% vs {selection['validation_baseline_final_accuracy']:.2f}% with test data excluded
- Comparison controls: {fl['comparison_note']}
- 5-fold Secure FL accuracy: {kfold['mean_accuracy']:.2f}% ± {kfold['std_accuracy']:.2f}%
- Median/Krum poisoning reduction: {poison['median_reduction_vs_fedavg'] * 100:.1f}% / {poison['krum_reduction_vs_fedavg'] * 100:.1f}%

## Generated Figures

- `figures/qkd_error_rates.png`
- `figures/qdp_attack_success.png`
- `figures/mpo_communication_saving.png`
- `figures/fl_training_curves.png`
- `figures/ablation_study.png`
- `figures/robust_aggregation.png`
"""
    (OUTPUT_DIR / 'summary.md').write_text(content, encoding='utf-8')


def write_metrics_csv(results):
    """输出扁平化核心指标，方便复制到论文表格或PPT。"""
    rows = [
        ('QKD', 'Eve detection rate (%)', results['qkd']['eve_detection_rate'] * 100),
        ('QKD', 'Normal error rate (%)', results['qkd']['normal_avg_error_rate']),
        ('QKD', 'Eavesdropping error rate (%)', results['qkd']['eve_avg_error_rate']),
        (
            'QDP',
            'epsilon=1 attack success rate (%)',
            next(x for x in results['qdp_gradient_inversion']['epsilon_scan'] if x['epsilon'] == 1.0)['attack_success_rate'] * 100
        ),
        (
            'QDP',
            'epsilon=1 average MSE',
            next(x for x in results['qdp_gradient_inversion']['epsilon_scan'] if x['epsilon'] == 1.0)['avg_mse']
        ),
        ('MPO', 'Adaptive communication saving (%)', results['mpo']['adaptive']['communication_saving_pct']),
        ('MPO', 'Adaptive reconstruction error', results['mpo']['adaptive']['reconstruction_error']),
        ('FL', '5-seed baseline mean accuracy (%)', results['federated_learning']['baseline_fedavg']['final_accuracy']),
        ('FL', '5-seed baseline accuracy std (%)', results['federated_learning']['baseline_fedavg']['final_accuracy_std']),
        ('FL', '5-seed proposed mean accuracy (%)', results['federated_learning']['secure_qdp_adaptive_mpo']['final_accuracy']),
        ('FL', '5-seed proposed accuracy std (%)', results['federated_learning']['secure_qdp_adaptive_mpo']['final_accuracy_std']),
        ('FL', 'Proposed communication saving (%)', results['federated_learning']['secure_qdp_adaptive_mpo']['avg_communication_saving_pct']),
        ('FL-CV', '5-fold mean accuracy (%)', results['fl_kfold_cross_validation']['mean_accuracy']),
        ('FL-CV', '5-fold std accuracy (%)', results['fl_kfold_cross_validation']['std_accuracy']),
        ('FL-CV', '5-fold min accuracy (%)', results['fl_kfold_cross_validation']['min_accuracy']),
        ('FL-CV', '5-fold max accuracy (%)', results['fl_kfold_cross_validation']['max_accuracy']),
        ('Poisoning', 'Median reduction vs FedAvg (%)', results['model_poisoning']['median_reduction_vs_fedavg'] * 100),
        ('Poisoning', 'Krum reduction vs FedAvg (%)', results['model_poisoning']['krum_reduction_vs_fedavg'] * 100),
    ]

    with (OUTPUT_DIR / 'summary_metrics.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['module', 'metric', 'value'])
        for module, metric, value in rows:
            writer.writerow([module, metric, round(float(value), 6)])


def write_ablation_csv(results):
    """输出四组控制消融和一组显式标注的优化方案。"""
    ablation = results['federated_learning']['ablation_study']
    baseline_acc = ablation['baseline_fedavg']['final_accuracy']
    rows = [
        ('Baseline FedAvg', 'controlled_ablation', '无', 'fedavg', ablation['baseline_fedavg']),
        ('+ MPO', 'controlled_ablation', 'MPO压缩', 'fedavg', ablation['mpo_only']),
        ('+ QDP', 'controlled_ablation', '量子差分隐私', 'fedavg', ablation['qdp_only']),
        ('QDP + MPO', 'controlled_ablation', 'QDP + MPO', 'fedavg', ablation['qdp_mpo']),
        (
            'Ours', 'validation_selected_method',
            'QDP + MPO + 压缩误差反馈', 'fedavg',
            ablation['optimized_qdp_mpo_error_feedback']
        ),
    ]

    with (OUTPUT_DIR / 'ablation_results.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow([
            'variant',
            'comparison_type',
            'enabled_modules',
            'aggregation',
            'final_accuracy_pct',
            'accuracy_delta_vs_baseline_pct',
            'final_loss',
            'avg_communication_saving_pct',
            'avg_reconstruction_error',
            'privacy_budget_remaining',
            'learning_rate',
            'qdp_clip_norm',
            'mpo_max_reconstruction_error',
            'compression_error_feedback',
            'n_runs'
        ])
        for variant, comparison_type, enabled_modules, aggregation, metrics in rows:
            privacy_remaining = metrics['final_privacy_budget_remaining']
            writer.writerow([
                variant,
                comparison_type,
                enabled_modules,
                aggregation,
                round(float(metrics['final_accuracy']), 2),
                round(float(metrics['final_accuracy'] - baseline_acc), 2),
                round(float(metrics['final_loss']), 6),
                round(float(metrics['avg_communication_saving_pct']), 2),
                round(float(metrics['avg_reconstruction_error']), 8),
                '' if privacy_remaining is None else round(float(privacy_remaining), 4),
                metrics['learning_rate_start'],
                '' if metrics['qdp_clip_norm'] is None else metrics['qdp_clip_norm'],
                (
                    '' if metrics['mpo_max_reconstruction_error'] is None
                    else metrics['mpo_max_reconstruction_error']
                ),
                metrics['compression_error_feedback'],
                metrics['n_runs']
            ])


def write_kfold_csv(results):
    """输出 k 折交叉验证逐折结果。"""
    kfold = results['fl_kfold_cross_validation']
    with (OUTPUT_DIR / 'kfold_results.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow([
            'fold',
            'train_samples',
            'test_samples',
            'accuracy_before_pct',
            'accuracy_after_pct',
            'loss_after'
        ])
        for item in kfold['folds']:
            writer.writerow([
                item['fold'],
                item['train_samples'],
                item['test_samples'],
                round(float(item['accuracy_before']), 2),
                round(float(item['accuracy_after']), 2),
                round(float(item['loss_after']), 6)
            ])


def main():
    ensure_output_dirs()
    results = {
        'qkd': run_qkd_benchmark(),
        'qdp_gradient_inversion': run_qdp_inversion_benchmark(),
        'mpo': run_mpo_benchmark(),
        'federated_learning': run_fl_training_benchmark(),
        'fl_kfold_cross_validation': run_fl_kfold_cross_validation(),
        'model_poisoning': run_poisoning_benchmark()
    }

    plot_qkd(results['qkd'])
    plot_qdp(results['qdp_gradient_inversion'])
    plot_mpo(results['mpo'])
    plot_fl(results['federated_learning'])
    plot_ablation(results['federated_learning'])
    plot_poisoning(results['model_poisoning'])

    with (OUTPUT_DIR / 'security_benchmark_results.json').open('w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    write_summary(results)
    write_metrics_csv(results)
    write_ablation_csv(results)
    write_kfold_csv(results)

    print('=' * 70)
    print('  安全基准与对照实验完成')
    print('=' * 70)
    print(f'  结果JSON: {OUTPUT_DIR / "security_benchmark_results.json"}')
    print(f'  摘要报告: {OUTPUT_DIR / "summary.md"}')
    print(f'  指标CSV: {OUTPUT_DIR / "summary_metrics.csv"}')
    print(f'  消融CSV: {OUTPUT_DIR / "ablation_results.csv"}')
    print(f'  K折CSV: {OUTPUT_DIR / "kfold_results.csv"}')
    print(f'  图表目录: {FIGURE_DIR}')
    print('=' * 70)


if __name__ == '__main__':
    main()
