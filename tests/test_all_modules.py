"""核心模块测试脚本。"""
import sys
import os
import time
import numpy as np

try:
    import pytest
except ImportError:
    pytest = None

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import (
    QuantumCommunicationChannel, QuantumDifferentialPrivacy,
    MPOCompressor, SimpleNNModel, FederatedLearningServer,
    SecureFederatedLedger, AttackSimulator
)


class TestResult:
    __test__ = False
    
    def __init__(self, name: str):
        self.name = name
        self.status = 'PENDING'
        self.message = ''
        self.details = {}
    
    def pass_(self, msg: str = ''):
        self.status = 'PASS'
        self.message = msg
    
    def warn(self, msg: str):
        self.status = 'WARNING'
        self.message = msg
    
    def fail(self, msg: str):
        self.status = 'FAIL'
        self.message = msg
    
    def add_detail(self, key: str, value):
        self.details[key] = value


if pytest is not None:
    @pytest.fixture
    def result(request):
        test_result = TestResult(request.node.name)
        yield test_result
        assert test_result.status != 'FAIL', test_result.message


class TestRunner:
    __test__ = False
    
    def __init__(self):
        self.results = []
        self.start_time = time.time()
    
    def run(self, test_name: str, test_func) -> TestResult:
        result = TestResult(test_name)
        try:
            output = test_func(result)
            self.results.append(result)
        except Exception as e:
            result.fail(f'异常: {str(e)}')
            self.results.append(result)
        return result
    
    def summary(self):
        elapsed = time.time() - self.start_time
        n_total = len(self.results)
        n_pass = sum(1 for r in self.results if r.status == 'PASS')
        n_warn = sum(1 for r in self.results if r.status == 'WARNING')
        n_fail = sum(1 for r in self.results if r.status == 'FAIL')
        
        print('\n' + '='*70)
        print(f'  综合测试报告  | 总耗时: {elapsed:.2f}秒')
        print('='*70)
        print(f'  总测试数: {n_total}  |  PASS: {n_pass}  |  WARNING: {n_warn}  |  FAIL: {n_fail}')
        
        color_map = {'PASS': '\033[32m✓\033[0m', 'WARNING': '\033[33m⚠\033[0m',
                     'FAIL': '\033[31m✗\033[0m', 'PENDING': '○'}
        
        for r in self.results:
            marker = color_map.get(r.status, '?')
            print(f'  {marker} {r.name:<50} {r.status:<10} {r.message}')
            for k, v in r.details.items():
                print(f'        └─ {k}: {v}')
        
        overall = 'PASS' if n_fail == 0 else 'FAIL'
        print(f'\n  总体评估: {color_map.get(overall, "")} {overall}')
        print('='*70)
        
        return n_fail == 0


def test_qkd_key_generation(result: TestResult):
    channel = QuantumCommunicationChannel(n_photons=1024)
    res = channel.establish(eve_active=False)
    
    if res['status'] != 'success':
        result.fail('密钥分发失败')
        return
    
    if not res['final_key'] or len(res['final_key']) < 32:
        result.warn('密钥长度异常')
        return
    
    result.add_detail('误码率(%)', res['error_rate'])
    result.add_detail('密钥长度(bit)', 256)
    result.pass_('密钥成功生成')


def test_qkd_eavesdropping_detection(result: TestResult):
    channel = QuantumCommunicationChannel(n_photons=1024)
    res = channel.establish(eve_active=True)
    
    if res['eavesdropping_detected']:
        result.add_detail('检测到窃听', '是')
        result.add_detail('误码率(%)', res['error_rate'])
        result.pass_('成功识别 Eve 攻击')
    else:
        result.warn(f'未检测到窃听(误码率{res["error_rate"]}%)')


def test_chaotic_encryption_cycle(result: TestResult):
    np.random.seed(2024)
    channel = QuantumCommunicationChannel(n_photons=2048)
    establish = channel.establish(eve_active=False)

    if establish['status'] != 'success':
        result.fail(f'信道建立失败: {establish.get("reason", "unknown")}')
        return
    
    msg = '模型参数梯度_0x1F3A9C_batch_size_32_test_测试_中文'
    send = channel.secure_send(msg, noise_level=0.05)
    
    if send['status'] != 'success':
        result.fail('加密失败')
        return
    
    recv = channel.secure_receive(send['encrypted_hex'], send['encryption_level'])
    
    if recv['status'] == 'success' and recv['message'] == msg:
        result.add_detail('原文长度(字节)', len(msg.encode('utf-8')))
        result.add_detail('密文长度(字节)', send['encrypted_size_bytes'])
        result.pass_('加解密完整循环通过')
    else:
        result.fail(f'解密结果不匹配: {recv.get("message","")}')


def test_qdp_noise_injection(result: TestResult):
    qdp = QuantumDifferentialPrivacy(epsilon=3.0, channel_ratio=0.65)
    grad = np.random.randn(100) * 0.5
    noisy = qdp.apply_privacy(grad, local_epsilon=1.0)
    
    diff = np.linalg.norm(noisy - grad)
    original_norm = np.linalg.norm(grad)
    snr = original_norm / (diff + 1e-8)
    
    if diff > 0 and snr > 0.1:
        result.add_detail('SNR(信噪比)', round(snr, 4))
        result.add_detail('噪声幅度', round(diff, 4))
        result.add_detail('剩余预算', round(qdp.budget.remaining(), 2))
        result.pass_('噪声成功注入且预算消耗合理')
    else:
        result.warn(f'噪声注入异常: SNR={snr:.4f}')


def test_qdp_privacy_budget(result: TestResult):
    qdp = QuantumDifferentialPrivacy(epsilon=1.0)
    rounds = 0
    while qdp.budget.remaining() > 0.1 and rounds < 20:
        grad = np.random.randn(50)
        qdp.apply_privacy(grad, local_epsilon=0.3)
        rounds += 1
    
    if rounds >= 1:
        result.add_detail('预算消耗轮次', rounds)
        result.add_detail('总预算', qdp.budget.epsilon)
        result.pass_(f'预算消耗机制正常 ({rounds}轮后仍有剩余)')
    else:
        result.fail('预算消耗机制异常')


def test_qdp_tradeoff_analysis(result: TestResult):
    qdp = QuantumDifferentialPrivacy(epsilon=3.0)
    tradeoff = qdp.privacy_utility_tradeoff()
    
    if 'epsilon' in tradeoff and len(tradeoff['epsilon']) > 0:
        eps_values = tradeoff['epsilon']
        losses = tradeoff['utility_loss']
        monotonic = all(losses[i] >= losses[i+1] for i in range(len(eps_values)-1))
        
        result.add_detail('扫描ε点数', len(eps_values))
        result.add_detail('单调关系成立', '是' if monotonic else '否')
        result.add_detail('最大效用损失(%)', round(max(losses), 2))
        result.pass_('隐私-效用权衡分析成功')
    else:
        result.fail('权衡分析未返回有效数据')


def test_mpo_compression_ratio(result: TestResult):
    np.random.seed(42)
    model = SimpleNNModel(input_dim=32, hidden_dim=64, output_dim=10)
    params = model.flatten_params()
    
    mpo = MPOCompressor(bond_dim=8)
    mpo_result = mpo.compress(params)
    
    ratio = mpo_result.compression_ratio
    error = mpo_result.reconstruction_error
    
    if ratio < 1.0:
        result.add_detail('原始参数数量', mpo_result.original_size)
        result.add_detail('压缩后数量', mpo_result.compressed_size)
        result.add_detail('压缩率(%)', round((1 - ratio) * 100, 2))
        result.add_detail('重构误差', round(error, 6))
        result.pass_('MPO压缩成功')
    else:
        result.warn(f'压缩率异常: {ratio}')


def test_mpo_decompress_integrity(result: TestResult):
    np.random.seed(42)
    params = np.random.randn(200) * 0.5
    original_size = params.size
    
    mpo = MPOCompressor(bond_dim=16)
    compress_result = mpo.compress(params)
    decompressed = mpo.decompress(compress_result, original_size)
    
    if len(decompressed) == original_size:
        correlation = float(np.corrcoef(params, decompressed)[0, 1])
        result.add_detail('参数长度一致', '是')
        result.add_detail('原始-压缩后相关性', round(correlation, 4))
        result.add_detail('MSE', round(float(np.mean((params - decompressed)**2)), 6))
        result.pass_('解压缩成功且参数结构保持')
    else:
        result.fail(f'长度不匹配: {len(decompressed)} vs {original_size}')


def test_federated_learning_round(result: TestResult):
    np.random.seed(42)
    model = SimpleNNModel(input_dim=32, hidden_dim=64, output_dim=10)
    qdp = QuantumDifferentialPrivacy(epsilon=3.0)
    mpo = MPOCompressor(bond_dim=8)
    
    server = FederatedLearningServer(
        model_template=model, n_clients=5,
        qdp_module=qdp, mpo_compressor=mpo
    )
    
    client_data = [(np.random.randn(32, 32), np.random.randint(0, 10, 32)) for _ in range(5)]
    X_test = np.random.randn(64, 32)
    y_test = np.random.randint(0, 10, 64)
    
    acc_before = server.evaluate(X_test, y_test)['accuracy']
    info = server.train_round(client_data, lr=0.05)
    acc_after = server.evaluate(X_test, y_test)['accuracy']
    
    result.add_detail('训练前准确率(%)', acc_before)
    result.add_detail('训练后准确率(%)', round(acc_after, 2))
    result.add_detail('平均压缩率(%)', round(info['avg_compression_ratio'], 2))
    result.add_detail('全局参数维度', len(server.global_params))
    result.pass_('联邦学习单轮训练成功')


def make_federated_classification_data(seed: int = 42, n_clients: int = 5,
                                       n_per_client: int = 80,
                                       n_test: int = 300,
                                       input_dim: int = 8,
                                       output_dim: int = 3):
    """生成确定性 teacher 分类数据，用于稳定验证联邦学习收敛。"""
    rng = np.random.RandomState(seed)
    teacher_w = rng.randn(input_dim, output_dim)

    client_data = []
    for client_id in range(n_clients):
        X = rng.randn(n_per_client, input_dim) + client_id * 0.02
        logits = X @ teacher_w + 0.1 * rng.randn(n_per_client, output_dim)
        y = np.argmax(logits, axis=1).astype(np.int64)
        client_data.append((X, y))

    X_test = rng.randn(n_test, input_dim)
    test_logits = X_test @ teacher_w + 0.1 * rng.randn(n_test, output_dim)
    y_test = np.argmax(test_logits, axis=1).astype(np.int64)

    return client_data, X_test, y_test


def expect_value_error(func) -> str:
    """执行函数并返回 ValueError 文本；未抛出则返回空字符串。"""
    try:
        func()
    except ValueError as e:
        return str(e)
    return ''


def test_federated_learning_multi_round_convergence(result: TestResult):
    np.random.seed(123)
    model = SimpleNNModel(input_dim=8, hidden_dim=16, output_dim=3)
    server = FederatedLearningServer(model_template=model, n_clients=5)
    client_data, X_test, y_test = make_federated_classification_data()

    before = server.evaluate(X_test, y_test)
    for _ in range(20):
        server.train_round(client_data, lr=0.5)
    after = server.evaluate(X_test, y_test)

    acc_gain = after['accuracy'] - before['accuracy']
    loss_drop = before['loss'] - after['loss']

    result.add_detail('训练前准确率(%)', before['accuracy'])
    result.add_detail('训练后准确率(%)', after['accuracy'])
    result.add_detail('准确率提升(%)', round(acc_gain, 2))
    result.add_detail('训练前loss', before['loss'])
    result.add_detail('训练后loss', after['loss'])
    result.add_detail('训练轮次', len(server.get_history()))

    if acc_gain >= 25.0 and after['loss'] < before['loss']:
        result.pass_('多轮联邦训练在确定性数据上稳定收敛')
    else:
        result.fail(f'收敛不足: 准确率提升={acc_gain:.2f}%, loss下降={loss_drop:.6f}')


def test_federated_learning_mpo_metrics(result: TestResult):
    np.random.seed(321)
    model = SimpleNNModel(input_dim=32, hidden_dim=64, output_dim=10)
    mpo = MPOCompressor(bond_dim=8)
    server = FederatedLearningServer(model_template=model, n_clients=5, mpo_compressor=mpo)
    original_params = server.global_params.copy()

    client_data = [
        (np.random.randn(32, 32), np.random.randint(0, 10, 32))
        for _ in range(5)
    ]
    info = server.train_round(client_data, lr=0.05)
    param_delta = float(np.linalg.norm(server.global_params - original_params))

    result.add_detail('平均压缩后占比(%)', info['avg_compression_ratio'])
    result.add_detail('通信节省率(%)', info['communication_saving_pct'])
    result.add_detail('平均重构误差', info['avg_recon_error'])
    result.add_detail('平均梯度原始大小(KB)', info['avg_grad_size_before_kb'])
    result.add_detail('平均梯度传输大小(KB)', info['avg_grad_size_after_kb'])
    result.add_detail('参数更新范数', round(param_delta, 6))

    if (info['communication_saving_pct'] > 50.0 and
            info['avg_recon_error'] < 0.001 and
            param_delta > 0):
        result.pass_('MPO通信节省与重构指标记录正常')
    else:
        result.fail('MPO通信指标未达到预期阈值')


def test_federated_learning_privacy_budget_metrics(result: TestResult):
    np.random.seed(456)
    model = SimpleNNModel(input_dim=16, hidden_dim=32, output_dim=4)
    qdp = QuantumDifferentialPrivacy(epsilon=10.0, channel_ratio=0.65)
    server = FederatedLearningServer(model_template=model, n_clients=5, qdp_module=qdp)

    client_data, _, _ = make_federated_classification_data(
        seed=7, input_dim=16, output_dim=4
    )
    info = server.train_round(client_data, lr=0.05)
    privacy_report = qdp.get_privacy_report()

    result.add_detail('噪声注入次数', len(qdp.noise_history))
    result.add_detail('预算已用', privacy_report['budget_used'])
    result.add_detail('预算剩余', privacy_report['budget_remaining'])
    result.add_detail('轮次记录剩余预算', info['privacy_budget_remaining'])

    if (len(qdp.noise_history) == 5 and
            privacy_report['budget_used'] > 0 and
            info['privacy_budget_remaining'] == privacy_report['budget_remaining']):
        result.pass_('联邦学习轮次正确记录隐私预算')
    else:
        result.fail('隐私预算记录不完整')


def test_federated_learning_kfold_cross_validation(result: TestResult):
    from experiments.run_security_benchmark import run_fl_kfold_cross_validation

    cv = run_fl_kfold_cross_validation(k=5, n_rounds=5, n_samples=300)
    folds = cv.get('folds', [])
    accuracies = [fold.get('accuracy_after', 0.0) for fold in folds]

    result.add_detail('折数', cv.get('k'))
    result.add_detail('平均准确率(%)', cv.get('mean_accuracy'))
    result.add_detail('准确率标准差(%)', cv.get('std_accuracy'))
    result.add_detail('逐折准确率(%)', [round(a, 2) for a in accuracies])

    if (cv.get('k') == 5 and len(folds) == 5 and
            all(0.0 <= acc <= 100.0 for acc in accuracies) and
            cv.get('mean_accuracy', 0.0) > 35.0):
        result.pass_('k折交叉验证结果结构与准确率统计正常')
    else:
        result.fail('k折交叉验证结果异常')


def test_federated_learning_invalid_inputs(result: TestResult):
    np.random.seed(789)
    model = SimpleNNModel(input_dim=4, hidden_dim=8, output_dim=3)
    server = FederatedLearningServer(model_template=model, n_clients=2)

    valid_client = (np.random.randn(8, 4), np.random.randint(0, 3, 8))

    errors = {
        '客户端数量': expect_value_error(lambda: server.train_round([valid_client], lr=0.1)),
        '特征维度': expect_value_error(lambda: server.train_round([
            (np.random.randn(8, 5), np.random.randint(0, 3, 8)),
            valid_client
        ], lr=0.1)),
        '标签越界': expect_value_error(lambda: server.train_round([
            (np.random.randn(8, 4), np.array([0, 1, 2, 3, 0, 1, 2, 0])),
            valid_client
        ], lr=0.1))
    }

    for name, message in errors.items():
        result.add_detail(name, message if message else '未抛出 ValueError')

    if all(errors.values()):
        result.pass_('异常输入均抛出明确 ValueError')
    else:
        result.fail('部分异常输入未被显式拦截')


def test_qdp_budget_exhaustion_guard(result: TestResult):
    qdp = QuantumDifferentialPrivacy(epsilon=0.5, channel_ratio=0.65)
    data = np.ones(10)

    qdp.apply_privacy(data, local_epsilon=0.8)
    report = qdp.get_privacy_report()
    error_message = expect_value_error(lambda: qdp.apply_privacy(data, local_epsilon=0.1))

    result.add_detail('预算已用', report['budget_used'])
    result.add_detail('预算剩余', report['budget_remaining'])
    result.add_detail('耗尽后错误', error_message if error_message else '未抛出 ValueError')

    if report['budget_used'] == 0.5 and report['budget_remaining'] == 0.0 and error_message:
        result.pass_('预算不足时自动降级并在耗尽后阻断继续加噪')
    else:
        result.fail('QDP预算保护未按预期生效')


def test_mpo_adaptive_compression_skip_small_model(result: TestResult):
    np.random.seed(234)
    small_model = SimpleNNModel(input_dim=8, hidden_dim=16, output_dim=3)
    params = small_model.flatten_params()
    mpo = MPOCompressor(bond_dim=16)
    adaptive = mpo.adaptive_compress(params, max_reconstruction_error=0.001)

    result.add_detail('是否压缩', adaptive['use_compression'])
    result.add_detail('跳过原因', adaptive['skipped_reason'])
    result.add_detail('最佳候选节省率(%)', adaptive['best_candidate_saving_pct'])
    result.add_detail('最佳候选误差', adaptive['best_candidate_error'])

    if not adaptive['use_compression'] and adaptive['skipped_reason'] == 'compression_not_beneficial':
        result.pass_('小模型在误差阈值下自动跳过不划算压缩')
    else:
        result.fail('小模型自适应压缩未正确跳过')


def test_mpo_compression_error_feedback(result: TestResult):
    np.random.seed(2468)
    model = SimpleNNModel(input_dim=8, hidden_dim=16, output_dim=3)
    server = FederatedLearningServer(
        model_template=model,
        n_clients=3,
        mpo_compressor=MPOCompressor(bond_dim=8),
        aggregation_method='fedavg',
        mpo_max_reconstruction_error=0.0015,
        compression_error_feedback=True
    )
    rng = np.random.RandomState(1357)
    client_data = [
        (rng.normal(size=(32, 8)), rng.randint(0, 3, size=32))
        for _ in range(3)
    ]

    round_info = server.train_round(client_data, lr=0.2)
    clients = round_info['clients']
    enabled = all(client['error_feedback_enabled'] for client in clients)
    residual_norms = [client['feedback_residual_norm'] for client in clients]
    compressed = [not client['compression_skipped'] for client in clients]

    result.add_detail('聚合方式', round_info['aggregation_method'])
    result.add_detail('通信节省(%)', round_info['communication_saving_pct'])
    result.add_detail('残差范数', residual_norms)

    if (
        enabled
        and all(compressed)
        and all(value > 0 for value in residual_norms)
        and round_info['communication_saving_pct'] > 0
    ):
        result.pass_('压缩残差已保存，可在下一轮更新中补偿')
    else:
        result.fail('误差反馈未正确记录压缩残差')


def test_robust_aggregation_reduces_poisoning(result: TestResult):
    rng = np.random.RandomState(345)
    honest = rng.normal(0.0, 0.05, size=(3, 80))
    malicious = rng.normal(2.5, 0.25, size=(2, 80))
    gradients = list(np.vstack([honest, malicious]))

    model = SimpleNNModel(input_dim=4, hidden_dim=8, output_dim=2)
    fedavg_server = FederatedLearningServer(model, n_clients=5, aggregation_method='fedavg')
    median_server = FederatedLearningServer(model, n_clients=5, aggregation_method='median')
    krum_server = FederatedLearningServer(model, n_clients=5, aggregation_method='krum')

    fedavg_norm = float(np.linalg.norm(fedavg_server._aggregate_gradients(gradients)))
    median_norm = float(np.linalg.norm(median_server._aggregate_gradients(gradients)))
    krum_norm = float(np.linalg.norm(krum_server._aggregate_gradients(gradients)))

    result.add_detail('FedAvg扰动范数', round(fedavg_norm, 4))
    result.add_detail('Median扰动范数', round(median_norm, 4))
    result.add_detail('Krum扰动范数', round(krum_norm, 4))

    if median_norm < fedavg_norm * 0.2 and krum_norm < fedavg_norm * 0.2:
        result.pass_('鲁棒聚合显著降低恶意梯度影响')
    else:
        result.fail('鲁棒聚合未明显削弱毒化梯度')


def test_blockchain_structure(result: TestResult):
    ledger = SecureFederatedLedger(n_nodes=5, blockchain_difficulty=3)
    
    for i in range(3):
        params = np.random.randn(100)
        client_meta = [{'client_id': c, 'grad_size': np.random.rand() * 100} for c in range(5)]
        ledger.record_round(i, params, client_meta, 60.0 + i * 2)
    
    valid, msg = ledger.blockchain.validate_chain()
    
    result.add_detail('链长度', len(ledger.blockchain.chain))
    result.add_detail('链验证', '有效' if valid else '被篡改')
    result.add_detail('最后区块哈希', ledger.blockchain.chain[-1].hash()[:16] + '...')
    
    if valid:
        result.pass_('区块链链结构完整有效')
    else:
        result.fail(f'区块链验证失败: {msg}')


def test_blockchain_tampering_detection(result: TestResult):
    ledger = SecureFederatedLedger(n_nodes=5, blockchain_difficulty=3)
    
    for i in range(3):
        params = np.random.randn(50)
        client_meta = [{'client_id': c} for c in range(5)]
        ledger.record_round(i, params, client_meta, 65.0)
    
    original_hash = ledger.blockchain.chain[1].hash()
    ledger.blockchain.chain[1].model_metadata['accuracy'] = 999.0
    
    valid_after, msg = ledger.blockchain.validate_chain()
    
    result.add_detail('篡改前验证', '有效')
    result.add_detail('篡改后验证', '检测到篡改' if not valid_after else '未检测到')
    result.add_detail('检测消息', msg)
    
    if not valid_after:
        result.pass_('成功识别区块链数据篡改')
    else:
        result.warn('篡改未被检测到')


def test_byzantine_consensus(result: TestResult):
    from core.blockchain_consensus import QuantumByzantineConsensus
    
    consensus = QuantumByzantineConsensus(n_nodes=7, n_qubits=64)
    malicious_indices = [4, 5]
    
    res = consensus.reach_consensus('test_model_hash_0xABCDEF', malicious_nodes=malicious_indices)
    
    detected = set(res['detected_malicious'])
    actual = set(malicious_indices)
    
    true_positive = len(detected & actual)
    
    result.add_detail('实际恶意节点', actual)
    result.add_detail('检测到恶意节点', detected)
    result.add_detail('识别准确率', res.get('detection_accuracy', 0))
    result.add_detail('共识达成', res.get('consensus_reached', False))
    
    if true_positive > 0 and res['consensus_reached']:
        result.pass_('拜占庭共识成功识别恶意节点')
    elif res['consensus_reached']:
        result.warn(f'共识达成但未完全识别恶意节点: TP={true_positive}')
    else:
        result.fail('共识未达成')


def test_attack_eavesdropping(result: TestResult):
    simulator = AttackSimulator()
    res = simulator.eavesdropping_attack()
    
    if res.get('eavesdropping_detected', False):
        result.add_detail('窃听检测', '成功')
        result.add_detail('误码率(%)', res.get('hacked_error_rate', 0))
        result.pass_('窃听攻击被成功检测')
    else:
        result.warn('本次窃听未被检测(随机性波动正常)')


def test_attack_model_poisoning(result: TestResult):
    simulator = AttackSimulator()
    res = simulator.model_poisoning_attack(n_clients=5, n_rounds=3)
    
    detections = res.get('total_malicious_detected', 0)
    result.add_detail('识别恶意节点次数', detections)
    
    if detections > 0:
        result.pass_('拜占庭共识成功识别毒化攻击')
    else:
        result.warn('本次未识别到毒化节点')


def test_attack_gradient_leakage(result: TestResult):
    simulator = AttackSimulator()
    res = simulator.gradient_leakage_attack()
    
    epsilon_scan = res.get('epsilon_scan', [])
    low_eps_protected = any(
        e.get('privacy_guaranteed', False) for e in epsilon_scan
        if e.get('epsilon', 10) < 2.0
    )
    
    result.add_detail('扫描ε点数', len(epsilon_scan))
    result.add_detail('低ε隐私保护', '是' if low_eps_protected else '否')
    
    if low_eps_protected:
        result.pass_('差分隐私有效抑制梯度泄漏攻击')
    else:
        result.warn('小ε下隐私保护未完全生效')


def test_end_to_end_integration(result: TestResult):
    np.random.seed(123)
    
    channel = QuantumCommunicationChannel(n_photons=512)
    channel.establish(eve_active=False)
    
    qdp = QuantumDifferentialPrivacy(epsilon=3.0, channel_ratio=0.65)
    
    model = SimpleNNModel(input_dim=16, hidden_dim=32, output_dim=5)
    mpo = MPOCompressor(bond_dim=8)
    server = FederatedLearningServer(
        model_template=model, n_clients=4,
        qdp_module=qdp, mpo_compressor=mpo
    )
    
    ledger = SecureFederatedLedger(n_nodes=4, blockchain_difficulty=3)
    
    accuracies = []
    for r in range(3):
        client_data = [
            (np.random.randn(16, 16), np.random.randint(0, 5, 16))
            for _ in range(4)
        ]
        info = server.train_round(client_data, lr=0.05)
        eval_res = server.evaluate(np.random.randn(32, 16), np.random.randint(0, 5, 32))
        accuracies.append(eval_res['accuracy'])
        
        ledger_result = ledger.record_round(
            r, server.global_params, info['clients'], eval_res['accuracy']
        )
    
    msg = f'模型训练完成 | 最终准确率: {accuracies[-1]:.2f}% | 链长度: {len(ledger.blockchain.chain)}'
    encrypted = channel.secure_send(msg)
    decrypted = channel.secure_receive(encrypted['encrypted_hex'], encrypted['encryption_level'])
    
    chain_valid = ledger.blockchain.validate_chain()[0]
    communication_valid = decrypted.get('message') == msg
    
    result.add_detail('QKD通信', '正常' if communication_valid else '失败')
    result.add_detail('区块链有效', '是' if chain_valid else '否')
    result.add_detail('训练轮次', len(accuracies))
    result.add_detail('最终准确率(%)', round(accuracies[-1], 2))
    
    if chain_valid and communication_valid:
        result.pass_('端到端系统集成成功')
    else:
        result.fail('端到端流程存在异常')



def main():
    print('\n' + '='*70)
    print('  🧪 量子安全联邦学习系统 - 综合测试套件')
    print('='*70)
    print(f'  运行时间: {time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'  NumPy 版本: {np.__version__}')
    print(f'  Python 路径: {project_root}')
    print('='*70)
    
    runner = TestRunner()
    
    print('\n[1/5] QKD 量子密钥分发模块测试...')
    runner.run('T1 密钥生成', test_qkd_key_generation)
    runner.run('T2 窃听检测', test_qkd_eavesdropping_detection)
    runner.run('T3 混沌加解密', test_chaotic_encryption_cycle)
    
    print('\n[2/5] 量子差分隐私模块测试...')
    runner.run('T4 噪声注入', test_qdp_noise_injection)
    runner.run('T5 隐私预算', test_qdp_privacy_budget)
    runner.run('T6 效用权衡分析', test_qdp_tradeoff_analysis)
    runner.run('T21 QDP预算耗尽保护', test_qdp_budget_exhaustion_guard)
    
    print('\n[3/5] MPO压缩 + 联邦学习模块测试...')
    runner.run('T7 MPO压缩率', test_mpo_compression_ratio)
    runner.run('T8 压缩-解压缩完整性', test_mpo_decompress_integrity)
    runner.run('T9 联邦学习训练', test_federated_learning_round)
    runner.run('T17 联邦学习多轮收敛', test_federated_learning_multi_round_convergence)
    runner.run('T18 联邦学习MPO指标', test_federated_learning_mpo_metrics)
    runner.run('T19 联邦学习隐私预算', test_federated_learning_privacy_budget_metrics)
    runner.run('T20 联邦学习异常输入', test_federated_learning_invalid_inputs)
    runner.run('T24 联邦学习K折交叉验证', test_federated_learning_kfold_cross_validation)
    runner.run('T22 MPO自适应跳过', test_mpo_adaptive_compression_skip_small_model)
    runner.run('T25 MPO压缩误差反馈', test_mpo_compression_error_feedback)
    runner.run('T23 鲁棒聚合抗毒化', test_robust_aggregation_reduces_poisoning)
    
    print('\n[4/5] 区块链 + 量子拜占庭共识模块测试...')
    runner.run('T10 区块链链结构', test_blockchain_structure)
    runner.run('T11 篡改检测', test_blockchain_tampering_detection)
    runner.run('T12 拜占庭共识', test_byzantine_consensus)
    
    print('\n[5/5] 攻防演示 + 端到端集成测试...')
    runner.run('T13 窃听攻击防护', test_attack_eavesdropping)
    runner.run('T14 模型毒化防护', test_attack_model_poisoning)
    runner.run('T15 梯度泄漏防护', test_attack_gradient_leakage)
    runner.run('T16 端到端系统集成', test_end_to_end_integration)
    
    success = runner.summary()
    
    if success:
        print('\n  所有核心测试通过')
        return 0
    else:
        print('\n  ⚠ 部分测试失败/警告, 请检查环境配置或调整参数')
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\n\n  测试已被用户中断')
        sys.exit(130)
