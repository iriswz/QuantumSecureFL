"""联邦学习里的 MPO 参数压缩和简单 MLP 训练逻辑。"""
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


@dataclass
class MPOCompressionResult:
    """MPO 压缩结果。"""
    original_size: int
    compressed_size: int
    compression_ratio: float
    reconstruction_error: float
    bond_dim: int
    mpo_tensors: List[np.ndarray]
    compression_skipped: bool = False


class MPOCompressor:
    """用顺序 SVD 把参数向量近似为张量链。"""
    
    def __init__(self, bond_dim: int = 8, max_sites: int = 8):
        self.bond_dim = bond_dim
        self.max_sites = max_sites
        self.compression_history = []
    
    def compress(self, params: np.ndarray) -> MPOCompressionResult:
        """对模型参数做 MPO 压缩。"""
        original_shape = params.shape
        original_size = params.size
        flat = params.flatten().astype(np.float64)
        
        L = self._optimal_sites(flat.size)
        d = self._optimal_local_dim(flat.size, L)
        
        pad_size = d ** L
        if flat.size < pad_size:
            padded = np.zeros(pad_size, dtype=np.float64)
            padded[:flat.size] = flat
        else:
            padded = flat[:pad_size]
        tensor = padded.reshape([d] * L)
        
        mpo_tensors = []
        current = tensor
        running_dim = 1
        
        for i in range(L):
            if i == 0:
                rest_dim = d ** (L - 1)
                M = current.reshape(d, rest_dim)
                U, S, Vt = np.linalg.svd(M, full_matrices=False)
                D_actual = min(self.bond_dim, len(S))
                U_trunc = U[:, :D_actual]
                S_trunc = np.diag(S[:D_actual])
                Vt_trunc = Vt[:D_actual, :]
                
                mpo_tensors.append(U_trunc.reshape(1, d, D_actual))
                current = (S_trunc @ Vt_trunc).reshape(D_actual, *[d] * (L - 1))
                running_dim = D_actual
            elif i < L - 1:
                rest_dims = L - i - 1
                M = current.reshape(running_dim * d, d ** rest_dims)
                U, S, Vt = np.linalg.svd(M, full_matrices=False)
                D_actual = min(self.bond_dim, len(S))
                U_trunc = U[:, :D_actual]
                S_trunc = np.diag(S[:D_actual])
                Vt_trunc = Vt[:D_actual, :]
                
                mpo_tensors.append(U_trunc.reshape(running_dim, d, D_actual))
                current = (S_trunc @ Vt_trunc).reshape(D_actual, *[d] * rest_dims)
                running_dim = D_actual
            else:
                mpo_tensors.append(current.reshape(running_dim, d, 1))
        
        compressed_size = sum(t.size for t in mpo_tensors)
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        reconstructed_full = self._reconstruct_from_mpo(mpo_tensors, L, d)
        reconstructed = reconstructed_full[:flat.size]
        error = float(np.mean((flat - reconstructed) ** 2))
        
        result = MPOCompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            reconstruction_error=error,
            bond_dim=self.bond_dim,
            mpo_tensors=mpo_tensors
        )
        
        self.compression_history.append({
            'step': len(self.compression_history),
            'original_shape': original_shape,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'ratio': round(compression_ratio * 100, 2),
            'error': error
        })
        
        return result
    
    def decompress(self, result: MPOCompressionResult, original_size: int) -> np.ndarray:
        """从 MPO 压缩结果恢复参数向量。"""
        L = len(result.mpo_tensors)
        d = result.mpo_tensors[0].shape[1]
        
        reconstructed_full = self._reconstruct_from_mpo(result.mpo_tensors, L, d)
        return reconstructed_full[:original_size]
    
    def _reconstruct_from_mpo(self, mpo_tensors: List[np.ndarray], L: int, d: int) -> np.ndarray:
        """从张量链重构向量。"""
        result = mpo_tensors[0]  # (1, d, D1)
        for i in range(1, L):
            next_tensor = mpo_tensors[i]  # (D_prev, d, D_next)
            result = np.tensordot(result, next_tensor, axes=([-1], [0]))
        
        result = result.squeeze()
        flat_size = d ** L
        return result.reshape(flat_size)
    
    def _optimal_sites(self, total_size: int) -> int:
        """根据参数数量选择张量链长度。"""
        for L in range(2, self.max_sites + 1):
            d = int(np.ceil(total_size ** (1 / L)))
            if 4 <= d <= 64:
                return L
        return min(self.max_sites, max(2, int(np.log2(total_size)) // 2))
    
    def _optimal_local_dim(self, total_size: int, L: int) -> int:
        d = int(np.ceil(total_size ** (1 / L)))
        return max(4, min(64, d))
    
    def scan_bond_dims(self, params: np.ndarray, 
                       dims: List[int] = None) -> Dict:
        """扫描不同键维度，返回压缩率和误差。"""
        if dims is None:
            dims = [2, 4, 8, 16, 32]
        
        results = {'bond_dim': [], 'ratio': [], 'error': [], 'size_kb': []}
        for d in dims:
            self.bond_dim = d
            r = self.compress(params)
            results['bond_dim'].append(d)
            results['ratio'].append(round((1 - r.compression_ratio) * 100, 2))
            results['error'].append(round(r.reconstruction_error, 8))
            results['size_kb'].append(round(r.compressed_size * 8 / 1024, 2))
        
        return results

    def adaptive_compress(self, params: np.ndarray, dims: List[int] = None,
                          max_reconstruction_error: float = 0.001) -> Dict:
        """自适应选择最划算的 MPO 压缩配置。

        小模型或低秩收益不足时可能出现压缩后更大的情况，此时直接跳过压缩。
        """
        if dims is None:
            dims = [2, 4, 8, 16]

        original_bond_dim = self.bond_dim
        candidates = []
        for dim in dims:
            self.bond_dim = dim
            compressed = self.compress(params)
            saving_pct = (1 - compressed.compression_ratio) * 100
            candidates.append((saving_pct, compressed))

        self.bond_dim = original_bond_dim

        valid = [
            (saving, compressed) for saving, compressed in candidates
            if saving > 0 and compressed.reconstruction_error <= max_reconstruction_error
        ]
        if not valid:
            best_saving, best_result = max(candidates, key=lambda item: item[0])
            return {
                'use_compression': False,
                'result': None,
                'selected_bond_dim': None,
                'compression_ratio': 1.0,
                'communication_saving_pct': 0.0,
                'reconstruction_error': 0.0,
                'skipped_reason': 'compression_not_beneficial',
                'best_candidate_saving_pct': round(float(best_saving), 2),
                'best_candidate_error': round(float(best_result.reconstruction_error), 8)
            }

        best_saving, best_result = max(valid, key=lambda item: item[0])
        return {
            'use_compression': True,
            'result': best_result,
            'selected_bond_dim': int(best_result.bond_dim),
            'compression_ratio': float(best_result.compression_ratio),
            'communication_saving_pct': round(float(best_saving), 2),
            'reconstruction_error': float(best_result.reconstruction_error),
            'skipped_reason': None
        }
    
    def get_history(self) -> List[Dict]:
        return self.compression_history


class SimpleNNModel:
    """两层 MLP。"""
    
    def __init__(self, input_dim: int = 32, hidden_dim: int = 64, output_dim: int = 10):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.params = self._init_params()
    
    def _init_params(self) -> Dict[str, np.ndarray]:
        scale1 = np.sqrt(2.0 / (self.input_dim + self.hidden_dim))
        scale2 = np.sqrt(2.0 / (self.hidden_dim + self.output_dim))
        return {
            'W1': np.random.randn(self.input_dim, self.hidden_dim) * scale1,
            'b1': np.zeros(self.hidden_dim),
            'W2': np.random.randn(self.hidden_dim, self.output_dim) * scale2,
            'b2': np.zeros(self.output_dim)
        }
    
    def forward(self, X: np.ndarray) -> np.ndarray:
        z1 = X @ self.params['W1'] + self.params['b1']
        a1 = np.maximum(0, z1)
        z2 = a1 @ self.params['W2'] + self.params['b2']
        e_z = np.exp(z2 - np.max(z2, axis=1, keepdims=True))
        return e_z / np.sum(e_z, axis=1, keepdims=True)

    def loss(self, X: np.ndarray, y: np.ndarray) -> float:
        probs = self.forward(X)
        clipped = np.clip(probs[np.arange(len(y)), y], 1e-12, 1.0)
        return float(-np.mean(np.log(clipped)))
    
    def compute_gradients(self, X: np.ndarray, y: np.ndarray) -> Dict[str, np.ndarray]:
        """计算交叉熵损失的梯度。"""
        m = X.shape[0]
        z1 = X @ self.params['W1'] + self.params['b1']
        a1 = np.maximum(0, z1)
        z2 = a1 @ self.params['W2'] + self.params['b2']
        e_z = np.exp(z2 - np.max(z2, axis=1, keepdims=True))
        probs = e_z / np.sum(e_z, axis=1, keepdims=True)
        
        dz2 = probs.copy()
        dz2[np.arange(m), y] -= 1
        dz2 /= m
        
        dW2 = a1.T @ dz2
        db2 = np.sum(dz2, axis=0)
        
        da1 = dz2 @ self.params['W2'].T
        dz1 = da1 * (z1 > 0)
        
        dW1 = X.T @ dz1
        db1 = np.sum(dz1, axis=0)
        
        return {'W1': dW1, 'b1': db1, 'W2': dW2, 'b2': db2}
    
    def flatten_params(self) -> np.ndarray:
        return np.concatenate([p.flatten() for p in self.params.values()])
    
    def load_flat_params(self, flat: np.ndarray):
        idx = 0
        for key in ['W1', 'b1', 'W2', 'b2']:
            shape = self.params[key].shape
            size = int(np.prod(shape))
            self.params[key] = flat[idx:idx + size].reshape(shape).copy()
            idx += size
    
    def total_params(self) -> int:
        return int(sum(p.size for p in self.params.values()))


class FederatedLearningServer:
    """负责客户端梯度聚合、可选加噪和可选压缩。"""
    
    def __init__(self, model_template: SimpleNNModel, n_clients: int = 5,
                 qdp_module=None, mpo_compressor=None, aggregation_method: str = 'fedavg',
                 mpo_max_reconstruction_error: float = 0.001,
                 compression_error_feedback: bool = False):
        self.model = model_template
        self.n_clients = n_clients
        self.qdp = qdp_module
        self.mpo = mpo_compressor
        self.aggregation_method = aggregation_method
        self.mpo_max_reconstruction_error = mpo_max_reconstruction_error
        self.compression_error_feedback = bool(compression_error_feedback)
        self._compression_residuals: List[Optional[np.ndarray]] = [
            None for _ in range(n_clients)
        ]
        self.global_params = model_template.flatten_params().copy()
        self.round_history = []
    
    def train_round(self, client_data: List[Tuple[np.ndarray, np.ndarray]],
                    lr: float = 0.01) -> Dict:
        """执行一轮联邦训练。"""
        self._validate_train_inputs(client_data, lr)
        
        all_gradients = []
        client_info = []
        
        for i, (X, y) in enumerate(client_data):
            X, y = self._validate_batch(X, y, name=f'client {i}')
            client_model = SimpleNNModel(
                self.model.input_dim, self.model.hidden_dim, self.model.output_dim
            )
            client_model.load_flat_params(self.global_params)
            grads = client_model.compute_gradients(X, y)
            grad_flat = np.concatenate([g.flatten() for g in grads.values()])
            
            if self.qdp is not None:
                grad_flat = self.qdp.apply_privacy(grad_flat, local_epsilon=None)
            
            grad_size_before = grad_flat.size * 8 / 1024  # KiB
            
            if self.mpo is not None:
                compression_input = grad_flat
                if self.compression_error_feedback:
                    residual = self._compression_residuals[i]
                    if residual is None or residual.shape != grad_flat.shape:
                        residual = np.zeros_like(grad_flat)
                    compression_input = grad_flat + residual

                adaptive = self.mpo.adaptive_compress(
                    compression_input,
                    max_reconstruction_error=self.mpo_max_reconstruction_error
                )
                compress_result = adaptive['result']
                if adaptive['use_compression']:
                    grad_decompressed = self.mpo.decompress(
                        compress_result, compression_input.size
                    )
                    grad_size_after = compress_result.compressed_size * 8 / 1024
                    ratio = compress_result.compression_ratio
                    recon_error = compress_result.reconstruction_error
                    selected_bond_dim = adaptive['selected_bond_dim']
                    skipped_reason = None
                    if self.compression_error_feedback:
                        self._compression_residuals[i] = (
                            compression_input - grad_decompressed
                        )
                else:
                    grad_decompressed = compression_input
                    grad_size_after = grad_size_before
                    ratio = 1.0
                    recon_error = 0.0
                    selected_bond_dim = None
                    skipped_reason = adaptive['skipped_reason']
                    if self.compression_error_feedback:
                        self._compression_residuals[i] = np.zeros_like(grad_flat)

                feedback_residual_norm = (
                    float(np.linalg.norm(self._compression_residuals[i]))
                    if self.compression_error_feedback else 0.0
                )

                all_gradients.append(grad_decompressed)
                client_info.append({
                    'client_id': i,
                    'grad_size_before_kb': float(round(grad_size_before, 2)),
                    'grad_size_after_kb': float(round(grad_size_after, 2)),
                    'compression_ratio': float(round(ratio * 100, 2)),
                    'communication_saving_pct': float(round((1 - ratio) * 100, 2)),
                    'recon_error': float(round(recon_error, 8)),
                    'selected_bond_dim': selected_bond_dim,
                    'compression_skipped': not adaptive['use_compression'],
                    'skipped_reason': skipped_reason,
                    'error_feedback_enabled': self.compression_error_feedback,
                    'feedback_residual_norm': round(feedback_residual_norm, 8)
                })
            else:
                all_gradients.append(grad_flat)
                client_info.append({
                    'client_id': i,
                    'no_compression': True,
                    'grad_size_before_kb': float(round(grad_size_before, 2)),
                    'grad_size_after_kb': float(round(grad_size_before, 2)),
                    'communication_saving_pct': 0.0
                })
        
        avg_grad = self._aggregate_gradients(all_gradients)
        
        self.global_params -= lr * avg_grad
        self.model.load_flat_params(self.global_params)

        grad_size_before_values = [c['grad_size_before_kb'] for c in client_info]
        grad_size_after_values = [c['grad_size_after_kb'] for c in client_info]
        compression_values = [c['compression_ratio'] for c in client_info if 'compression_ratio' in c]
        recon_errors = [c['recon_error'] for c in client_info if 'recon_error' in c]

        avg_compression_ratio = float(round(np.mean(compression_values), 2)) if compression_values else 0.0
        avg_recon_error = float(round(np.mean(recon_errors), 8)) if recon_errors else 0.0
        avg_grad_before = float(round(np.mean(grad_size_before_values), 2))
        avg_grad_after = float(round(np.mean(grad_size_after_values), 2))
        communication_saving = float(round(100 - avg_compression_ratio, 2)) if self.mpo else 0.0

        privacy_budget_remaining = None
        privacy_budget_used = None
        if self.qdp is not None and hasattr(self.qdp, 'get_privacy_report'):
            privacy_report = self.qdp.get_privacy_report()
            privacy_budget_remaining = float(privacy_report.get('budget_remaining', 0.0))
            privacy_budget_used = float(privacy_report.get('budget_used', 0.0))
        
        round_info = {
            'round': len(self.round_history),
            'clients': client_info,
            'avg_compression_ratio': avg_compression_ratio,
            'avg_recon_error': avg_recon_error,
            'communication_saving_pct': communication_saving,
            'avg_grad_size_before_kb': avg_grad_before,
            'avg_grad_size_after_kb': avg_grad_after,
            'privacy_budget_remaining': privacy_budget_remaining,
            'privacy_budget_used': privacy_budget_used,
            'aggregation_method': self.aggregation_method,
            'global_param_norm': float(round(float(np.linalg.norm(self.global_params)), 4))
        }
        self.round_history.append(round_info)
        
        return round_info
    
    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> Dict:
        X_test, y_test = self._validate_batch(X_test, y_test, name='evaluation')
        self.model.load_flat_params(self.global_params)
        probs = self.model.forward(X_test)
        preds = np.argmax(probs, axis=1)
        accuracy = np.mean(preds == y_test)
        loss = self.model.loss(X_test, y_test)
        return {
            'accuracy': float(round(float(accuracy) * 100, 2)),
            'loss': float(round(loss, 6)),
            'n_samples': int(len(y_test))
        }
    
    def get_history(self) -> List[Dict]:
        return self.round_history

    def _aggregate_gradients(self, gradients: List[np.ndarray]) -> np.ndarray:
        """聚合客户端梯度，支持普通 FedAvg 和简单鲁棒聚合。"""
        stacked = np.vstack(gradients)
        method = self.aggregation_method.lower()

        if method == 'fedavg':
            return np.mean(stacked, axis=0)
        if method == 'median':
            return np.median(stacked, axis=0)
        if method == 'trimmed_mean':
            if stacked.shape[0] < 3:
                return np.mean(stacked, axis=0)
            sorted_values = np.sort(stacked, axis=0)
            return np.mean(sorted_values[1:-1], axis=0)
        if method == 'krum':
            return self._krum(stacked)

        raise ValueError(f'未知聚合方法: {self.aggregation_method}')

    def _krum(self, gradients: np.ndarray) -> np.ndarray:
        """简化 Krum：选择与其他梯度距离总和最小的客户端梯度。"""
        n_clients = gradients.shape[0]
        if n_clients <= 2:
            return np.mean(gradients, axis=0)

        scores = []
        neighbor_count = max(1, n_clients - 2)
        for i in range(n_clients):
            distances = np.sum((gradients[i] - gradients) ** 2, axis=1)
            nearest = np.sort(distances)[1:neighbor_count + 1]
            scores.append(float(np.sum(nearest)))
        return gradients[int(np.argmin(scores))]

    def _validate_train_inputs(self, client_data: List[Tuple[np.ndarray, np.ndarray]], lr: float):
        """验证联邦训练入口参数，避免底层矩阵异常泄漏到用户侧。"""
        if not isinstance(client_data, list):
            raise ValueError('client_data 必须是客户端数据列表')
        if len(client_data) != self.n_clients:
            raise ValueError(f'客户端数量不匹配: 期望 {self.n_clients}, 实际 {len(client_data)}')
        if not np.isscalar(lr) or not np.isfinite(lr) or lr <= 0:
            raise ValueError('学习率 lr 必须是正的有限数值')

    def _validate_batch(self, X: np.ndarray, y: np.ndarray, name: str = 'batch') -> Tuple[np.ndarray, np.ndarray]:
        """验证一个客户端或评估批次的数据形状、标签和数值。"""
        X = np.asarray(X)
        y = np.asarray(y)

        if X.ndim != 2:
            raise ValueError(f'{name} 的 X 必须是二维数组')
        if y.ndim != 1:
            raise ValueError(f'{name} 的 y 必须是一维标签数组')
        if X.shape[0] == 0:
            raise ValueError(f'{name} 不能为空')
        if X.shape[0] != y.shape[0]:
            raise ValueError(f'{name} 样本数不匹配: X={X.shape[0]}, y={y.shape[0]}')
        if X.shape[1] != self.model.input_dim:
            raise ValueError(
                f'{name} 特征维度不匹配: 期望 {self.model.input_dim}, 实际 {X.shape[1]}'
            )
        if not np.all(np.isfinite(X)):
            raise ValueError(f'{name} 的 X 包含 NaN 或 Inf')
        if not np.issubdtype(y.dtype, np.integer):
            raise ValueError(f'{name} 的 y 必须是整数类别标签')
        if not np.all(np.isfinite(y)):
            raise ValueError(f'{name} 的 y 包含 NaN 或 Inf')
        if np.any(y < 0) or np.any(y >= self.model.output_dim):
            raise ValueError(
                f'{name} 标签越界: 标签必须在 [0, {self.model.output_dim - 1}] 范围内'
            )

        return X.astype(np.float64, copy=False), y.astype(np.int64, copy=False)


def mpo_fl_demo():
    """命令行自检入口。"""
    print('=' * 60)
    print('  MPO + federated learning check')
    print('=' * 60)
    
    print(f'\n[初始化]')
    model = SimpleNNModel(input_dim=32, hidden_dim=64, output_dim=10)
    print(f'  模型结构: 32 → 64 → 10 | 总参数: {model.total_params()}')
    
    mpo = MPOCompressor(bond_dim=8)
    
    print(f'\n[MPO 压缩率-误差分析] (键维度 D 扫描)')
    test_params = model.flatten_params()
    scan_result = mpo.scan_bond_dims(test_params, dims=[2, 4, 8, 16, 32])
    print(f'  {"D":>4} | {"压缩率(%)":>10} | {"压缩后大小(KB)":>14} | {"重构误差":>12}')
    print(f'  {"-"*4} | {"-"*10} | {"-"*14} | {"-"*12}')
    for i in range(len(scan_result['bond_dim'])):
        print(f'  {scan_result["bond_dim"][i]:>4} | {scan_result["ratio"][i]:>10.2f} | '
              f'{scan_result["size_kb"][i]:>14.2f} | {scan_result["error"][i]:>12.2e}')
    
    print(f'\n[联邦学习模拟] 5个客户端, 3轮训练')
    from core.qdp_module import QuantumDifferentialPrivacy
    qdp = QuantumDifferentialPrivacy(epsilon=3.0, channel_ratio=0.6)
    
    mpo2 = MPOCompressor(bond_dim=8)
    server = FederatedLearningServer(model_template=model, n_clients=5,
                                     qdp_module=qdp, mpo_compressor=mpo2)
    
    np.random.seed(123)
    X_test = np.random.randn(100, 32)
    y_test = np.random.randint(0, 10, size=100)
    
    for r in range(3):
        client_data = []
        for _ in range(5):
            X = np.random.randn(32, 32)
            y = np.random.randint(0, 10, size=32)
            client_data.append((X, y))
        
        info = server.train_round(client_data, lr=0.05)
        eval_result = server.evaluate(X_test, y_test)
        print(f'  轮次 {r+1}: 平均压缩率={info["avg_compression_ratio"]}%, '
              f'模型准确率={eval_result["accuracy"]}%')
    
    print(f'\n[隐私报告] {qdp.get_privacy_report()}')


if __name__ == '__main__':
    mpo_fl_demo()
