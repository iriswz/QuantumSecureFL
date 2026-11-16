"""UCI Parkinson 语音分类数据的下载、受试者级划分与五客户端构造。"""
from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from .medical_data import MedicalFederatedDataset


DATASET_NAME = "Parkinson's Disease Classification"
DATASET_PAGE = 'https://archive.ics.uci.edu/dataset/470/parkinson+s+disease+classification'
DATASET_DOI = 'https://doi.org/10.24432/C5MS4X'
DATASET_URL = (
    'https://archive.ics.uci.edu/static/public/470/'
    'parkinson+s+disease+classification.zip'
)


def default_parkinson_csv_path(project_root: Path | str) -> Path:
    return (
        Path(project_root) / 'data' / 'raw' /
        'parkinson_disease_classification' / 'pd_speech_features.csv'
    )


def download_parkinson_dataset(project_root: Path | str, force: bool = False) -> Path:
    """下载约 3 MB 的 UCI 压缩包并提取 CSV。"""
    csv_path = default_parkinson_csv_path(project_root)
    if csv_path.exists() and not force:
        return csv_path

    raw_dir = csv_path.parent
    zip_path = raw_dir / 'parkinson_disease_classification.zip'
    rar_path = raw_dir / 'pd_speech_features.rar'
    raw_dir.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(
        DATASET_URL,
        headers={'User-Agent': 'QuantumSecureFL/1.0 (research prototype)'}
    )
    with urllib.request.urlopen(request, timeout=120) as response, zip_path.open('wb') as target:
        shutil.copyfileobj(response, target)

    with zipfile.ZipFile(zip_path) as archive:
        members = archive.infolist()
        if len(members) != 1 or Path(members[0].filename).name != rar_path.name:
            raise ValueError('UCI 压缩包结构与预期不一致')
        if Path(members[0].filename).is_absolute() or '..' in Path(members[0].filename).parts:
            raise ValueError('UCI 压缩包包含不安全路径')
        archive.extract(members[0], raw_dir)

    extractor = shutil.which('bsdtar') or shutil.which('unar')
    if extractor is None:
        raise RuntimeError('提取 RAR 需要 bsdtar 或 unar')
    if Path(extractor).name == 'unar':
        command = [extractor, '-force-overwrite', '-output-directory', str(raw_dir), str(rar_path)]
    else:
        command = [extractor, '-xf', str(rar_path), '-C', str(raw_dir)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    if not csv_path.exists():
        raise FileNotFoundError('RAR 中未找到 pd_speech_features.csv')
    return csv_path


def _read_records(csv_path: Path) -> Tuple[List[str], List[Tuple[int, np.ndarray, int]], str]:
    with csv_path.open('r', encoding='utf-8-sig', newline='') as source:
        reader = csv.reader(source)
        next(reader, None)  # 第一行是特征组名称。
        headers = next(reader, None)
        if not headers or headers[0] != 'id' or headers[-1] != 'class':
            raise ValueError('Parkinson CSV 表头与预期不一致')
        feature_indices = [
            index for index, name in enumerate(headers)
            if name not in {'id', 'gender', 'class'}
        ]
        feature_names = [headers[index] for index in feature_indices]
        records = []
        digest = hashlib.sha256()
        for row in reader:
            if not row:
                continue
            if len(row) != len(headers):
                raise ValueError('Parkinson CSV 存在列数异常的记录')
            digest.update((','.join(row) + '\n').encode('utf-8'))
            subject_id = int(row[0])
            label = int(row[-1])
            features = np.asarray([float(row[index]) for index in feature_indices], dtype=np.float64)
            if label not in {0, 1} or not np.all(np.isfinite(features)):
                raise ValueError('Parkinson CSV 存在非法标签或非有限特征')
            records.append((subject_id, features, label))
    return feature_names, records, digest.hexdigest()


def _subject_partition(records: List[Tuple[int, np.ndarray, int]], n_clients: int,
                       test_fraction: float, seed: int) -> Tuple[List[List[int]], List[int]]:
    subject_labels: Dict[int, int] = {}
    for subject_id, _, label in records:
        previous = subject_labels.setdefault(subject_id, label)
        if previous != label:
            raise ValueError(f'受试者 {subject_id} 的标签不一致')

    rng = np.random.RandomState(seed)
    train_by_label: Dict[int, List[int]] = {}
    test_subjects: List[int] = []
    for label in (0, 1):
        subjects = np.asarray(sorted(
            subject_id for subject_id, value in subject_labels.items() if value == label
        ), dtype=np.int64)
        rng.shuffle(subjects)
        n_test = max(1, int(round(len(subjects) * test_fraction)))
        test_subjects.extend(subjects[:n_test].tolist())
        train_by_label[label] = subjects[n_test:].tolist()

    # 模拟五个非独立同分布机构：病例阳性率有差异，但每个机构均含两类受试者。
    client_subjects: List[List[int]] = [[] for _ in range(n_clients)]
    for label, subjects in train_by_label.items():
        rng.shuffle(subjects)
        if label == 1:
            weights = np.linspace(1.35, 0.65, n_clients)
        else:
            weights = np.linspace(0.65, 1.35, n_clients)
        ideal = weights / np.sum(weights) * len(subjects)
        counts = np.floor(ideal).astype(int)
        for index in np.argsort(-(ideal - counts))[:len(subjects) - int(np.sum(counts))]:
            counts[index] += 1
        offset = 0
        for client_id, count in enumerate(counts.tolist()):
            client_subjects[client_id].extend(subjects[offset:offset + count])
            offset += count

    if any(len(subjects) == 0 for subjects in client_subjects):
        raise ValueError('五客户端划分产生空客户端')
    return client_subjects, sorted(test_subjects)


def load_federated_parkinson_data(
        csv_path: Path | str,
        n_clients: int = 5,
        test_fraction: float = 0.2,
        projection_dim: int = 64,
        seed: int = 2026) -> MedicalFederatedDataset:
    """按受试者划分测试集和五个模拟机构，并执行公开随机投影。"""
    if n_clients != 5:
        raise ValueError('本演示固定使用 5 个客户端')
    if not 0.1 <= test_fraction <= 0.4:
        raise ValueError('test_fraction 必须在 [0.1, 0.4]')
    if projection_dim < 16:
        raise ValueError('projection_dim 至少为 16')

    csv_path = Path(csv_path)
    feature_names, records, data_sha256 = _read_records(csv_path)
    if len(records) != 756 or len(feature_names) != 752:
        raise ValueError(
            f'数据规模异常: records={len(records)}, features={len(feature_names)}'
        )

    client_subjects, test_subjects = _subject_partition(
        records, n_clients, test_fraction, seed
    )
    subject_to_client = {
        subject_id: client_id
        for client_id, subjects in enumerate(client_subjects)
        for subject_id in subjects
    }
    test_set = set(test_subjects)
    raw_clients: List[List[Tuple[np.ndarray, int, int]]] = [[] for _ in range(n_clients)]
    raw_test: List[Tuple[np.ndarray, int, int]] = []
    for subject_id, features, label in records:
        if subject_id in test_set:
            raw_test.append((features, label, subject_id))
        else:
            raw_clients[subject_to_client[subject_id]].append((features, label, subject_id))

    # 只需聚合各客户端的 count/sum/sum-of-squares，不汇集原始语音特征。
    total_count = sum(len(items) for items in raw_clients)
    feature_sum = sum(
        (np.sum(np.vstack([row[0] for row in items]), axis=0) for items in raw_clients),
        start=np.zeros(len(feature_names), dtype=np.float64)
    )
    square_sum = sum(
        (np.sum(np.vstack([row[0] for row in items]) ** 2, axis=0) for items in raw_clients),
        start=np.zeros(len(feature_names), dtype=np.float64)
    )
    mean = feature_sum / total_count
    variance = np.maximum(square_sum / total_count - mean ** 2, 0.0)
    std = np.sqrt(variance)
    std[std < 1e-10] = 1.0

    rng = np.random.RandomState(seed + 7000)
    projection = rng.choice([-1.0, 1.0], size=(len(feature_names), projection_dim))
    projection /= np.sqrt(len(feature_names))

    def transform(items: List[Tuple[np.ndarray, int, int]]) -> Tuple[np.ndarray, np.ndarray]:
        X = np.vstack([row[0] for row in items])
        X = np.clip((X - mean) / std, -6.0, 6.0) @ projection
        y = np.asarray([row[1] for row in items], dtype=np.int64)
        return X.astype(np.float64), y

    clients = [transform(items) for items in raw_clients]
    X_test, y_test = transform(raw_test)
    train_subjects = set(subject_to_client)
    hospital_summaries = []
    for client_id, (X, y) in enumerate(clients):
        subject_ids = sorted(client_subjects[client_id])
        hospital_summaries.append({
            'hospital_id': client_id,
            'name': f'机构{chr(ord("A") + client_id)}',
            'recordings': int(len(y)),
            'subjects': len(subject_ids),
            'parkinson_recordings': int(np.sum(y)),
            'positive_rate_pct': round(float(np.mean(y)) * 100.0, 2),
        })

    metadata = {
        'dataset_name': DATASET_NAME,
        'dataset_page': DATASET_PAGE,
        'dataset_doi': DATASET_DOI,
        'license': 'CC BY 4.0',
        'archive_size_note': 'about 3 MB ZIP; extracted CSV about 5.1 MB',
        'raw_recordings': len(records),
        'raw_subjects': len({row[0] for row in records}),
        'source_feature_count': len(feature_names),
        'model_feature_count': projection_dim,
        'train_recordings': int(sum(len(y) for _, y in clients)),
        'test_recordings': int(len(y_test)),
        'train_subjects': len(train_subjects),
        'test_subjects': len(test_set),
        'subject_leakage_count': len(train_subjects & test_set),
        'target': 'Parkinson disease class (1=PD, 0=healthy)',
        'protected_features_excluded': ['gender'],
        'client_partition': (
            'subject-level simulated five organizations with predeclared non-IID case mix; '
            'the source dataset has no organization ID'
        ),
        'normalization': 'federated count/sum/sum-of-squares over training clients only',
        'projection': f'public seeded Rademacher projection 752->{projection_dim}',
        'data_rows_sha256': data_sha256,
        'seed': seed,
    }
    return MedicalFederatedDataset(
        client_data=clients,
        X_test=X_test,
        y_test=y_test,
        feature_names=[f'voice_rp_{index:03d}' for index in range(projection_dim)],
        hospital_summaries=hospital_summaries,
        metadata=metadata,
    )
