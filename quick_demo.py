"""快速自检脚本。"""
import numpy as np
from core import (
    QuantumCommunicationChannel,
    QuantumDifferentialPrivacy,
    MPOCompressor, SimpleNNModel,
    SecureFederatedLedger
)

print('='*60)
print('  QuantumSecureFL quick check')
print('='*60)

channel = QuantumCommunicationChannel(n_photons=1024)
res = channel.establish(eve_active=False)
print(f'[1] QKD: status={res["status"]}, error_rate={res["error_rate"]}%')
msg = '测试模型参数_梯度向量_batch32_中文验证'
send = channel.secure_send(msg)
recv = channel.secure_receive(send['encrypted_hex'], send['encryption_level'])
print(f'[2] encryption round trip: {recv["message"] == msg}')

qdp = QuantumDifferentialPrivacy(epsilon=2.0, channel_ratio=0.65)
grad = np.random.randn(100) * 0.5
noisy = qdp.apply_privacy(grad, local_epsilon=1.0)
print(f'[3] differential privacy: SNR={np.linalg.norm(grad)/np.linalg.norm(noisy-grad+1e-8):.3f}, budget_left={qdp.budget.remaining():.2f}')

model = SimpleNNModel(input_dim=16, hidden_dim=32, output_dim=5)
params = model.flatten_params()
mpo = MPOCompressor(bond_dim=8)
result = mpo.compress(params)
print(f'[4] MPO: {result.original_size} -> {result.compressed_size} params, saving={(1-result.compression_ratio)*100:.1f}%')

ledger = SecureFederatedLedger(n_nodes=5, blockchain_difficulty=3)
for i in range(3):
    params = np.random.randn(100)
    client_meta = [{'client_id': c} for c in range(5)]
    rec = ledger.record_round(i, params, client_meta, 65.0+i)
valid, msg = ledger.blockchain.validate_chain()
print(f'[5] ledger: blocks={len(ledger.blockchain.chain)}, valid={valid}')

print()
print('='*60)
print('  quick check finished')
print('  运行 "python main.py" 启动完整 PyQt 可视化界面')
print('  运行 "python tests/test_all_modules.py" 执行完整测试')
print('='*60)
