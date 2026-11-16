"""小型 Parkinson 五机构场景测试。"""
from pathlib import Path

from core import default_parkinson_csv_path, load_federated_parkinson_data
from parkinson_federated_demo import gradient_inversion_probe


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_parkinson_subject_split_and_client_shapes():
    csv_path = default_parkinson_csv_path(PROJECT_ROOT)
    if not csv_path.exists():
        raise AssertionError('请先运行 parkinson_federated_demo.py 下载 UCI 数据')
    dataset = load_federated_parkinson_data(csv_path, seed=2026)

    assert dataset.metadata['raw_recordings'] == 756
    assert dataset.metadata['raw_subjects'] == 252
    assert dataset.metadata['subject_leakage_count'] == 0
    assert len(dataset.client_data) == 5
    assert dataset.X_test.shape == (153, 64)
    assert sum(len(y) for _, y in dataset.client_data) == 603
    assert all(set(y.tolist()) == {0, 1} for _, y in dataset.client_data)
    assert all('gender' not in name.lower() for name in dataset.feature_names)


def test_qdp_blocks_analytic_single_record_gradient_inversion():
    dataset = load_federated_parkinson_data(
        default_parkinson_csv_path(PROJECT_ROOT), seed=2026
    )
    report = gradient_inversion_probe(
        dataset=dataset, batch_size=128, local_epsilon=0.5, seed=2026
    )

    assert report['plain_gradient_reconstruction_succeeded']
    assert report['plain_gradient_reconstruction_nrmse'] < 1e-6
    assert report['qdp_gradient_reconstruction_blocked']
    assert report['qdp_gradient_reconstruction_nrmse'] > 0.5
