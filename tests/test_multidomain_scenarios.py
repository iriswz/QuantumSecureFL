"""邮件网关与金融机构两个真实场景测试。"""
from pathlib import Path

from core import default_scenario_data_path, load_federated_small_scenario


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_spambase_five_gateway_partition():
    dataset = load_federated_small_scenario(
        default_scenario_data_path(PROJECT_ROOT, 'spam'), 'spam', seed=2026
    )
    assert dataset.metadata['raw_records'] == 4601
    assert dataset.metadata['feature_count'] == 57
    assert dataset.metadata['train_records'] == 3680
    assert dataset.metadata['test_records'] == 921
    assert dataset.metadata['row_leakage_count'] == 0
    assert len(dataset.client_data) == 5
    assert all(set(labels.tolist()) == {0, 1} for _, labels in dataset.client_data)


def test_bankruptcy_five_financial_institution_partition():
    dataset = load_federated_small_scenario(
        default_scenario_data_path(PROJECT_ROOT, 'bankruptcy'),
        'bankruptcy', seed=2026
    )
    assert dataset.metadata['raw_records'] == 6819
    assert dataset.metadata['feature_count'] == 95
    assert dataset.metadata['train_records'] == 5455
    assert dataset.metadata['test_records'] == 1364
    assert dataset.metadata['row_leakage_count'] == 0
    assert len(dataset.client_data) == 5
    assert all(set(labels.tolist()) == {0, 1} for _, labels in dataset.client_data)
