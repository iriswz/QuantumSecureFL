"""真实医疗五医院场景的集成测试。"""
from pathlib import Path

import numpy as np

from core import QuantumCommunicationChannel, load_federated_diabetes_data
from core.medical_data import default_csv_path
from core.fl_mpo_module import MPOCompressor
from medical_federated_demo import (
    _deserialize_gradient,
    _serialize_gradient,
    run_secure_federated,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_qkd_binary_payload_authentication_and_tamper_rejection():
    np.random.seed(2026)
    channel = QuantumCommunicationChannel(n_photons=2048)
    assert channel.establish(eve_active=False)['status'] == 'success'

    payload = np.arange(256, dtype=np.float64).tobytes()
    sent = channel.secure_send_bytes(payload)
    received = channel.secure_receive_bytes(
        sent['encrypted_payload'], sent['encryption_level']
    )
    assert received['status'] == 'success'
    assert received['payload'] == payload

    tampered = bytearray(sent['encrypted_payload'])
    tampered[-1] ^= 1
    rejected = channel.secure_receive_bytes(bytes(tampered), sent['encryption_level'])
    assert rejected['status'] == 'failed'
    assert rejected['reason'] == 'authentication_failed'


def test_medical_patient_split_and_five_hospital_shapes():
    csv_path = default_csv_path(PROJECT_ROOT)
    if not csv_path.exists():
        raise AssertionError('请先运行 medical_federated_demo.py 下载 UCI 医疗数据')
    dataset = load_federated_diabetes_data(csv_path, n_hospitals=5, seed=2026)

    assert dataset.metadata['raw_encounters'] == 101766
    assert dataset.metadata['patient_leakage_count'] == 0
    assert len(dataset.client_data) == 5
    assert dataset.X_test.shape[1] == len(dataset.feature_names) == 52
    assert sum(len(y) for _, y in dataset.client_data) + len(dataset.y_test) == 101766
    assert all(len(y) > 15000 for _, y in dataset.client_data)
    assert all('race' not in name and 'gender' not in name for name in dataset.feature_names)


def test_mpo_payload_roundtrip_is_smaller_and_bounded():
    rng = np.random.RandomState(7)
    gradient = rng.normal(0.0, 0.02, size=2834)
    compressor = MPOCompressor(bond_dim=16)
    payload, metadata = _serialize_gradient(gradient, compressor)
    reconstructed = _deserialize_gradient(payload, compressor)

    assert metadata['format'] == 'MPO'
    assert metadata['payload_bytes'] < metadata['raw_bytes']
    assert reconstructed.shape == gradient.shape
    assert np.mean((gradient - reconstructed) ** 2) < 0.001


def test_one_round_secure_medical_pipeline():
    dataset = load_federated_diabetes_data(
        default_csv_path(PROJECT_ROOT), n_hospitals=5, seed=2026
    )
    result = run_secure_federated(
        dataset=dataset,
        rounds=1,
        batch_size=128,
        learning_rate=0.2,
        seed=2026,
        malicious_hospital=4,
        local_epsilon=0.5,
        bond_dim=16,
    )
    security = result['security']
    assert security['eavesdropping_test']['eavesdropping_detected']
    assert security['ciphertext_tampering_test']['tampering_rejected']
    assert security['authenticated_transmissions'] == 5
    assert security['byzantine']['rounds_detected'] == 1
    assert security['blockchain']['valid']
    assert security['blockchain']['length'] == 2
