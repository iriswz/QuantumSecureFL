"""UCI 糖尿病住院记录的下载、清洗与五医院联邦划分。"""
from __future__ import annotations

import csv
import hashlib
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np


DATASET_NAME = 'Diabetes 130-US Hospitals for Years 1999-2008'
DATASET_DOI = 'https://doi.org/10.24432/C5230J'
DATASET_PAGE = 'https://archive.ics.uci.edu/dataset/296/diabetes-130-us-hospitals-for-years-1999-2008'
DATASET_URL = (
    'https://archive.ics.uci.edu/static/public/296/'
    'diabetes+130-us+hospitals+for+years+1999-2008.zip'
)


NUMERIC_FEATURES = [
    'age_midpoint',
    'time_in_hospital',
    'num_lab_procedures',
    'num_procedures',
    'num_medications',
    'number_outpatient',
    'number_emergency',
    'number_inpatient',
    'number_diagnoses',
]
ADMISSION_TYPE_VALUES = ['1', '2', '3', '4', '5', '6', '7', '8', 'other']
ADMISSION_SOURCE_GROUPS = ['referral', 'transfer', 'emergency', 'birth', 'other']
DIAGNOSIS_GROUPS = [
    'circulatory', 'respiratory', 'digestive', 'diabetes', 'injury',
    'musculoskeletal', 'genitourinary', 'neoplasm', 'other', 'missing'
]
GLUCOSE_RESULT_VALUES = ['None', 'Norm', '>200', '>300', 'other']
A1C_RESULT_VALUES = ['None', 'Norm', '>7', '>8', 'other']
INSULIN_VALUES = ['No', 'Steady', 'Up', 'Down', 'other']
BINARY_VALUES = ['No', 'Ch']
DIABETES_MED_VALUES = ['No', 'Yes']


@dataclass
class MedicalFederatedDataset:
    """模型可直接使用的五个医院数据孤岛和全局留出测试集。"""

    client_data: List[Tuple[np.ndarray, np.ndarray]]
    X_test: np.ndarray
    y_test: np.ndarray
    feature_names: List[str]
    hospital_summaries: List[Dict]
    metadata: Dict


def default_csv_path(project_root: Path | str) -> Path:
    root = Path(project_root)
    return root / 'data' / 'raw' / 'diabetes_130_us_hospitals' / 'diabetic_data.csv'


def download_diabetes_dataset(project_root: Path | str, force: bool = False) -> Path:
    """从 UCI 下载并安全解压数据集，返回主 CSV 路径。"""
    root = Path(project_root)
    raw_dir = root / 'data' / 'raw'
    extract_dir = raw_dir / 'diabetes_130_us_hospitals'
    archive_path = raw_dir / 'diabetes_130_us_hospitals.zip'
    csv_path = extract_dir / 'diabetic_data.csv'

    if csv_path.exists() and not force:
        return csv_path

    raw_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(
        DATASET_URL,
        headers={'User-Agent': 'QuantumSecureFL/1.0 (research prototype)'}
    )
    with urllib.request.urlopen(request, timeout=60) as response, archive_path.open('wb') as output:
        shutil.copyfileobj(response, output)

    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            member_path = (extract_dir / member.filename).resolve()
            if extract_dir.resolve() not in member_path.parents and member_path != extract_dir.resolve():
                raise ValueError(f'数据压缩包包含不安全路径: {member.filename}')
        archive.extractall(extract_dir)

    if not csv_path.exists():
        matches = list(extract_dir.rglob('diabetic_data.csv'))
        if len(matches) != 1:
            raise FileNotFoundError('UCI 压缩包中未找到唯一的 diabetic_data.csv')
        matches[0].replace(csv_path)
    return csv_path


def _stable_fraction(value: str, salt: str) -> float:
    digest = hashlib.sha256(f'{salt}:{value}'.encode('utf-8')).digest()
    return int.from_bytes(digest[:8], 'big') / float(2 ** 64)


def _stable_bucket(value: str, salt: str, n_buckets: int) -> int:
    digest = hashlib.sha256(f'{salt}:{value}'.encode('utf-8')).digest()
    return int.from_bytes(digest[:8], 'big') % n_buckets


def _as_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _age_midpoint(value: str) -> float:
    # UCI 年龄格式为 [0-10)、[10-20)……[90-100)。
    try:
        lower, upper = value.strip('[]()').split('-')
        return (_as_float(lower) + _as_float(upper)) / 2.0
    except (AttributeError, ValueError):
        return 50.0


def _one_hot(value: str, categories: Sequence[str]) -> List[float]:
    safe_value = value if value in categories else categories[-1]
    return [1.0 if safe_value == category else 0.0 for category in categories]


def _admission_source_group(value: str) -> str:
    if value in {'1', '2', '3'}:
        return 'referral'
    if value in {'4', '5', '6', '10', '18', '22', '25', '26'}:
        return 'transfer'
    if value == '7':
        return 'emergency'
    if value in {'11', '12', '13', '14'}:
        return 'birth'
    return 'other'


def _diagnosis_group(value: str) -> str:
    if not value or value == '?':
        return 'missing'
    if value.startswith(('V', 'E')):
        return 'other'
    try:
        code = float(value)
    except ValueError:
        return 'other'
    if int(code) == 250:
        return 'diabetes'
    if 390 <= code <= 459 or int(code) == 785:
        return 'circulatory'
    if 460 <= code <= 519 or int(code) == 786:
        return 'respiratory'
    if 520 <= code <= 579 or int(code) == 787:
        return 'digestive'
    if 800 <= code <= 999:
        return 'injury'
    if 710 <= code <= 739:
        return 'musculoskeletal'
    if 580 <= code <= 629 or int(code) == 788:
        return 'genitourinary'
    if 140 <= code <= 239:
        return 'neoplasm'
    return 'other'


def _feature_names() -> List[str]:
    names = list(NUMERIC_FEATURES)
    names += [f'admission_type={v}' for v in ADMISSION_TYPE_VALUES]
    names += [f'admission_source={v}' for v in ADMISSION_SOURCE_GROUPS]
    names += [f'primary_diagnosis={v}' for v in DIAGNOSIS_GROUPS]
    names += [f'max_glucose={v}' for v in GLUCOSE_RESULT_VALUES]
    names += [f'a1c={v}' for v in A1C_RESULT_VALUES]
    names += [f'insulin={v}' for v in INSULIN_VALUES]
    names += [f'medication_change={v}' for v in BINARY_VALUES]
    names += [f'diabetes_medication={v}' for v in DIABETES_MED_VALUES]
    return names


def _row_to_features(row: Dict[str, str]) -> List[float]:
    numeric = [
        _age_midpoint(row['age']),
        _as_float(row['time_in_hospital']),
        _as_float(row['num_lab_procedures']),
        _as_float(row['num_procedures']),
        _as_float(row['num_medications']),
        _as_float(row['number_outpatient']),
        _as_float(row['number_emergency']),
        _as_float(row['number_inpatient']),
        _as_float(row['number_diagnoses']),
    ]
    admission_type = row['admission_type_id']
    if admission_type not in ADMISSION_TYPE_VALUES[:-1]:
        admission_type = 'other'
    max_glucose = row['max_glu_serum']
    a1c = row['A1Cresult']
    insulin = row['insulin']
    change = row['change'] if row['change'] in BINARY_VALUES else 'No'
    diabetes_med = row['diabetesMed'] if row['diabetesMed'] in DIABETES_MED_VALUES else 'No'

    features = numeric
    features += _one_hot(admission_type, ADMISSION_TYPE_VALUES)
    features += _one_hot(_admission_source_group(row['admission_source_id']), ADMISSION_SOURCE_GROUPS)
    features += _one_hot(_diagnosis_group(row['diag_1']), DIAGNOSIS_GROUPS)
    features += _one_hot(max_glucose, GLUCOSE_RESULT_VALUES)
    features += _one_hot(a1c, A1C_RESULT_VALUES)
    features += _one_hot(insulin, INSULIN_VALUES)
    features += _one_hot(change, BINARY_VALUES)
    features += _one_hot(diabetes_med, DIABETES_MED_VALUES)
    return features


def _summary(hospital_id: int, y: np.ndarray, n_unique_patients: int) -> Dict:
    return {
        'hospital_id': hospital_id,
        'name': f'医院{chr(ord("A") + hospital_id)}',
        'encounters': int(len(y)),
        'unique_patients': int(n_unique_patients),
        'early_readmissions': int(np.sum(y)),
        'positive_rate_pct': round(float(np.mean(y) * 100.0), 2),
    }


def load_federated_diabetes_data(
        csv_path: Path | str,
        n_hospitals: int = 5,
        test_fraction: float = 0.2,
        seed: int = 2026) -> MedicalFederatedDataset:
    """读取 UCI 数据，并按患者划分测试集和五个虚拟医院。

    原数据因去标识化不包含医院 ID。这里用患者号的加盐 SHA-256 哈希构造
    可复现的虚拟医院孤岛；同一患者的多次住院不会跨医院或跨训练/测试集。
    """
    if n_hospitals < 2:
        raise ValueError('n_hospitals 至少为 2')
    if not 0.05 <= test_fraction <= 0.5:
        raise ValueError('test_fraction 必须在 [0.05, 0.5] 范围内')

    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f'医疗数据文件不存在: {csv_path}')

    hospital_features: List[List[List[float]]] = [[] for _ in range(n_hospitals)]
    hospital_labels: List[List[int]] = [[] for _ in range(n_hospitals)]
    hospital_patients = [set() for _ in range(n_hospitals)]
    test_features: List[List[float]] = []
    test_labels: List[int] = []
    test_patients = set()
    total_rows = 0

    split_salt = f'medical-test-{seed}'
    hospital_salt = f'virtual-hospital-{seed}'
    with csv_path.open('r', encoding='utf-8', newline='') as source:
        reader = csv.DictReader(source)
        required = {
            'patient_nbr', 'age', 'readmitted', 'time_in_hospital',
            'num_lab_procedures', 'num_procedures', 'num_medications',
            'number_outpatient', 'number_emergency', 'number_inpatient',
            'number_diagnoses', 'admission_type_id', 'admission_source_id',
            'diag_1', 'max_glu_serum', 'A1Cresult', 'insulin', 'change', 'diabetesMed'
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'医疗 CSV 缺少字段: {sorted(missing)}')

        for row in reader:
            total_rows += 1
            patient_id = row['patient_nbr']
            features = _row_to_features(row)
            label = int(row['readmitted'] == '<30')
            if _stable_fraction(patient_id, split_salt) < test_fraction:
                test_features.append(features)
                test_labels.append(label)
                test_patients.add(patient_id)
            else:
                hospital_id = _stable_bucket(patient_id, hospital_salt, n_hospitals)
                hospital_features[hospital_id].append(features)
                hospital_labels[hospital_id].append(label)
                hospital_patients[hospital_id].add(patient_id)

    feature_names = _feature_names()
    clients = []
    train_arrays = []
    for X_values, y_values in zip(hospital_features, hospital_labels):
        X = np.asarray(X_values, dtype=np.float64)
        y = np.asarray(y_values, dtype=np.int64)
        if X.ndim != 2 or X.shape[1] != len(feature_names):
            raise ValueError('医疗特征编码维度异常')
        clients.append((X, y))
        train_arrays.append(X)

    X_test = np.asarray(test_features, dtype=np.float64)
    y_test = np.asarray(test_labels, dtype=np.int64)
    numeric_count = len(NUMERIC_FEATURES)
    # 只聚合每家医院的 count/sum/sum-of-squares，不集中拼接患者级原始特征。
    total_train_count = sum(len(X) for X in train_arrays)
    numeric_sum = sum(
        (np.sum(X[:, :numeric_count], axis=0) for X in train_arrays),
        start=np.zeros(numeric_count, dtype=np.float64)
    )
    numeric_square_sum = sum(
        (np.sum(X[:, :numeric_count] ** 2, axis=0) for X in train_arrays),
        start=np.zeros(numeric_count, dtype=np.float64)
    )
    means = numeric_sum / total_train_count
    variances = np.maximum(0.0, numeric_square_sum / total_train_count - means ** 2)
    stds = np.sqrt(variances)
    stds[stds < 1e-8] = 1.0

    for X, _ in clients:
        X[:, :numeric_count] = np.clip((X[:, :numeric_count] - means) / stds, -5.0, 5.0)
    X_test[:, :numeric_count] = np.clip((X_test[:, :numeric_count] - means) / stds, -5.0, 5.0)

    hospital_summaries = [
        _summary(i, clients[i][1], len(hospital_patients[i]))
        for i in range(n_hospitals)
    ]
    metadata = {
        'dataset_name': DATASET_NAME,
        'dataset_page': DATASET_PAGE,
        'dataset_doi': DATASET_DOI,
        'license': 'CC BY 4.0',
        'raw_encounters': total_rows,
        'train_encounters': int(sum(len(y) for _, y in clients)),
        'test_encounters': int(len(y_test)),
        'train_unique_patients': int(sum(len(patients) for patients in hospital_patients)),
        'test_unique_patients': int(len(test_patients)),
        'feature_count': len(feature_names),
        'target': 'readmitted == <30 days',
        'protected_features_excluded': ['race', 'gender'],
        'hospital_partition': 'salted patient hash (virtual hospitals; source hospital ID unavailable)',
        'normalization': 'federated count/sum/sum-of-squares over training hospitals only',
        'patient_leakage_count': int(len(test_patients & set().union(*hospital_patients))),
        'seed': seed,
    }
    return MedicalFederatedDataset(
        client_data=clients,
        X_test=X_test,
        y_test=y_test,
        feature_names=feature_names,
        hospital_summaries=hospital_summaries,
        metadata=metadata,
    )
