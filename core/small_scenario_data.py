"""两个小型真实数据集的下载与五客户端非 IID 联邦划分。"""
from __future__ import annotations

import csv
import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from .medical_data import MedicalFederatedDataset


SCENARIOS = {
    'spam': {
        'dataset_name': 'Spambase',
        'dataset_page': 'https://archive.ics.uci.edu/dataset/94/spambase',
        'dataset_doi': 'https://doi.org/10.24432/C53G6X',
        'dataset_url': 'https://archive.ics.uci.edu/static/public/94/spambase.zip',
        'archive_name': 'spambase.zip',
        'data_file': 'spambase.data',
        'archive_size_note': 'about 128 KB ZIP; extracted data about 703 KB',
        'client_prefix': '邮件网关',
        'target': 'spam email (1=spam, 0=non-spam)',
    },
    'bankruptcy': {
        'dataset_name': 'Taiwanese Bankruptcy Prediction',
        'dataset_page': 'https://archive.ics.uci.edu/dataset/572/taiwanese+bankruptcy+prediction',
        'dataset_doi': 'https://doi.org/10.24432/C5004D',
        'dataset_url': (
            'https://archive.ics.uci.edu/static/public/572/'
            'taiwanese+bankruptcy+prediction.zip'
        ),
        'archive_name': 'taiwanese_bankruptcy_prediction.zip',
        'data_file': 'data.csv',
        'archive_size_note': 'about 4.6 MB ZIP; extracted CSV about 10.9 MB',
        'client_prefix': '金融机构',
        'target': 'company bankruptcy (1=bankrupt, 0=operating)',
    },
}


def default_scenario_data_path(project_root: Path | str, scenario: str) -> Path:
    spec = SCENARIOS.get(scenario)
    if spec is None:
        raise ValueError(f'未知场景: {scenario}')
    return Path(project_root) / 'data' / 'raw' / f'{scenario}_scenario' / spec['data_file']


def download_scenario_dataset(project_root: Path | str, scenario: str,
                              force: bool = False) -> Path:
    """从 UCI 下载并安全解压指定的小型数据集。"""
    spec = SCENARIOS.get(scenario)
    if spec is None:
        raise ValueError(f'未知场景: {scenario}')
    data_path = default_scenario_data_path(project_root, scenario)
    if data_path.exists() and not force:
        return data_path
    raw_dir = data_path.parent
    archive_path = raw_dir / spec['archive_name']
    raw_dir.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        spec['dataset_url'],
        headers={'User-Agent': 'QuantumSecureFL/1.0 (research prototype)'}
    )
    with urllib.request.urlopen(request, timeout=180) as response, archive_path.open('wb') as target:
        shutil.copyfileobj(response, target)
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            path = Path(member.filename)
            if path.is_absolute() or '..' in path.parts:
                raise ValueError(f'数据压缩包包含不安全路径: {member.filename}')
        archive.extractall(raw_dir)
    if not data_path.exists():
        matches = list(raw_dir.rglob(spec['data_file']))
        if len(matches) != 1:
            raise FileNotFoundError(f'压缩包中未找到唯一的 {spec["data_file"]}')
        matches[0].replace(data_path)
    return data_path


def _read_spambase(data_path: Path) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    values = np.loadtxt(data_path, delimiter=',', dtype=np.float64)
    if values.shape != (4601, 58):
        raise ValueError(f'Spambase 数据规模异常: {values.shape}')
    names_path = data_path.with_name('spambase.names')
    feature_names = []
    if names_path.exists():
        for line in names_path.read_text(encoding='latin-1').splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith('|') and ':' in stripped:
                feature_names.append(stripped.split(':', 1)[0].strip())
    if len(feature_names) != 57:
        feature_names = [f'email_feature_{index:02d}' for index in range(57)]
    return values[:, :-1], values[:, -1].astype(np.int64), feature_names


def _read_bankruptcy(data_path: Path) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    with data_path.open('r', encoding='utf-8-sig', newline='') as source:
        reader = csv.reader(source)
        headers = next(reader, None)
        rows = [row for row in reader if row]
    if not headers or len(headers) != 96 or len(rows) != 6819:
        raise ValueError(
            f'Bankruptcy 数据规模异常: rows={len(rows)}, columns={len(headers or [])}'
        )
    values = np.asarray(rows, dtype=np.float64)
    y = values[:, 0].astype(np.int64)
    X = values[:, 1:]
    feature_names = [name.strip() for name in headers[1:]]
    return X, y, feature_names


def _allocate_counts(total: int, weights: np.ndarray) -> np.ndarray:
    ideal = weights / np.sum(weights) * total
    counts = np.floor(ideal).astype(int)
    remainder = total - int(np.sum(counts))
    for index in np.argsort(-(ideal - counts))[:remainder]:
        counts[index] += 1
    return counts


def _partition_indices(y: np.ndarray, n_clients: int, test_fraction: float,
                       seed: int, skew: float) -> Tuple[List[np.ndarray], np.ndarray]:
    rng = np.random.RandomState(seed)
    train_by_label = {}
    test_indices = []
    for label in (0, 1):
        indices = np.flatnonzero(y == label)
        rng.shuffle(indices)
        n_test = max(1, int(round(len(indices) * test_fraction)))
        test_indices.extend(indices[:n_test].tolist())
        train_by_label[label] = indices[n_test:]

    clients: List[List[int]] = [[] for _ in range(n_clients)]
    for label, indices in train_by_label.items():
        rng.shuffle(indices)
        if label == 1:
            weights = np.linspace(1.0 + skew, 1.0 - skew, n_clients)
        else:
            weights = np.linspace(1.0 - skew, 1.0 + skew, n_clients)
        counts = _allocate_counts(len(indices), weights)
        offset = 0
        for client_id, count in enumerate(counts.tolist()):
            clients[client_id].extend(indices[offset:offset + count].tolist())
            offset += count
    arrays = []
    for client in clients:
        values = np.asarray(client, dtype=np.int64)
        rng.shuffle(values)
        if len(values) == 0 or len(np.unique(y[values])) != 2:
            raise ValueError('客户端划分必须非空且同时包含两个类别')
        arrays.append(values)
    return arrays, np.asarray(sorted(test_indices), dtype=np.int64)


def load_federated_small_scenario(
        data_path: Path | str,
        scenario: str,
        n_clients: int = 5,
        test_fraction: float = 0.2,
        seed: int = 2026) -> MedicalFederatedDataset:
    """加载真实表格数据，并构造五个预先声明的非 IID 模拟机构。"""
    if n_clients != 5:
        raise ValueError('本实验固定使用 5 个客户端')
    if not 0.1 <= test_fraction <= 0.4:
        raise ValueError('test_fraction 必须在 [0.1, 0.4]')
    data_path = Path(data_path)
    spec = SCENARIOS.get(scenario)
    if spec is None:
        raise ValueError(f'未知场景: {scenario}')
    if scenario == 'spam':
        X, y, feature_names = _read_spambase(data_path)
        skew = 0.40
    else:
        X, y, feature_names = _read_bankruptcy(data_path)
        skew = 0.30
    if not np.all(np.isfinite(X)) or set(np.unique(y).tolist()) != {0, 1}:
        raise ValueError('数据包含非有限特征或非二分类标签')

    client_indices, test_indices = _partition_indices(
        y, n_clients, test_fraction, seed, skew
    )
    train_index_set = set(np.concatenate(client_indices).tolist())
    test_index_set = set(test_indices.tolist())

    # 标准化参数只通过各客户端 count/sum/sum-of-squares 聚合得到。
    total_count = sum(len(indices) for indices in client_indices)
    feature_sum = sum(
        (np.sum(X[indices], axis=0) for indices in client_indices),
        start=np.zeros(X.shape[1], dtype=np.float64)
    )
    square_sum = sum(
        (np.sum(X[indices] ** 2, axis=0) for indices in client_indices),
        start=np.zeros(X.shape[1], dtype=np.float64)
    )
    mean = feature_sum / total_count
    variance = np.maximum(square_sum / total_count - mean ** 2, 0.0)
    std = np.sqrt(variance)
    std[std < 1e-10] = 1.0
    normalized = np.clip((X - mean) / std, -6.0, 6.0)
    clients = [(normalized[indices], y[indices]) for indices in client_indices]

    summaries = []
    for client_id, (_, labels) in enumerate(clients):
        summaries.append({
            'hospital_id': client_id,
            'name': f'{spec["client_prefix"]}{chr(ord("A") + client_id)}',
            'records': int(len(labels)),
            'positive_records': int(np.sum(labels)),
            'positive_rate_pct': round(float(np.mean(labels)) * 100.0, 2),
        })
    digest = hashlib.sha256(data_path.read_bytes()).hexdigest()
    metadata: Dict = {
        'scenario': scenario,
        'dataset_name': spec['dataset_name'],
        'dataset_page': spec['dataset_page'],
        'dataset_doi': spec['dataset_doi'],
        'license': 'CC BY 4.0',
        'archive_size_note': spec['archive_size_note'],
        'raw_records': int(len(y)),
        'feature_count': int(X.shape[1]),
        'positive_records': int(np.sum(y)),
        'raw_positive_rate_pct': round(float(np.mean(y)) * 100.0, 2),
        'train_records': int(sum(len(labels) for _, labels in clients)),
        'test_records': int(len(test_indices)),
        'row_leakage_count': len(train_index_set & test_index_set),
        'target': spec['target'],
        'client_partition': (
            'stratified row-level simulated five organizations with predeclared non-IID '
            'positive-rate shift; source organization ID is unavailable'
        ),
        'normalization': 'federated count/sum/sum-of-squares over training clients only',
        'data_sha256': digest,
        'seed': seed,
    }
    return MedicalFederatedDataset(
        client_data=clients,
        X_test=normalized[test_indices],
        y_test=y[test_indices],
        feature_names=feature_names,
        hospital_summaries=summaries,
        metadata=metadata,
    )
