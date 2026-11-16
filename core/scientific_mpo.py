"""基于 SVD 截断的矩阵压缩实现。"""
import numpy as np
from typing import List, Tuple, Dict
from dataclasses import dataclass


@dataclass
class MPOCompressionResult:
    """MPO 压缩结果。"""
    original_size: int
    compressed_size: int
    compression_ratio: float
    reconstruction_error: float
    rank: int
    U: np.ndarray
    S: np.ndarray
    Vt: np.ndarray


class ScientificMPOCompressor:
    """SVD 低秩压缩器。"""
    
    def __init__(self, max_rank: int = 8, svd_tolerance: float = 1e-10):
        self.max_rank = max_rank
        self.svd_tolerance = svd_tolerance
        self.compression_history = []
    
    def _svd_truncate(self, matrix: np.ndarray, max_rank: int, tolerance: float) -> Tuple:
        """SVD 分解并截断到指定秩。"""
        U, S, Vt = np.linalg.svd(matrix, full_matrices=False)
        
        valid_mask = S > tolerance
        n_effective = min(np.sum(valid_mask), max_rank)
        
        n_effective = max(1, n_effective)
        
        U_trunc = U[:, :n_effective]
        S_trunc = S[:n_effective]
        Vt_trunc = Vt[:n_effective, :]
        
        return U_trunc, S_trunc, Vt_trunc, n_effective
    
    def compress(self, tensor: np.ndarray) -> MPOCompressionResult:
        """把张量压缩为低秩矩阵近似。"""
        original_shape = tensor.shape
        original_size = tensor.size
        
        if len(original_shape) > 2:
            if original_shape[0] >= original_shape[-1]:
                matrix = tensor.reshape(original_shape[0], -1)
            else:
                matrix = tensor.reshape(-1, original_shape[-1])
        else:
            matrix = tensor.copy()
        
        U, S, Vt, rank = self._svd_truncate(matrix, self.max_rank, self.svd_tolerance)
        
        compressed_size = U.size + S.size + Vt.size
        compression_ratio = compressed_size / original_size
        
        reconstructed = U @ np.diag(S) @ Vt
        reconstruction_error = float(np.mean((matrix - reconstructed) ** 2))
        
        self.compression_history.append({
            'original_shape': original_shape,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': round(compression_ratio * 100, 2),
            'reconstruction_error': reconstruction_error,
            'rank': rank
        })
        
        return MPOCompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            reconstruction_error=reconstruction_error,
            rank=rank,
            U=U,
            S=S,
            Vt=Vt
        )
    
    def decompress(self, result: MPOCompressionResult) -> np.ndarray:
        """从压缩结果重建矩阵。"""
        return result.U @ np.diag(result.S) @ result.Vt
    
    def analyze_compression_tradeoff(self, tensor: np.ndarray,
                                     ranks: List[int] = None) -> Dict:
        """比较不同秩的压缩率和重建误差。"""
        if ranks is None:
            ranks = [2, 4, 8, 16, 32]
        
        results = {
            'rank': [],
            'compression_ratio': [],
            'reconstruction_error': [],
            'compressed_size': []
        }
        
        original_size = tensor.size
        
        for r in ranks:
            self.max_rank = r
            result = self.compress(tensor)
            
            results['rank'].append(r)
            results['compression_ratio'].append(round((1 - result.compression_ratio) * 100, 2))
            results['reconstruction_error'].append(round(result.reconstruction_error, 10))
            results['compressed_size'].append(result.compressed_size)
        
        return results


def mpo_scientific_demo():
    """命令行自检入口。"""
    print('=' * 70)
    print('  SVD compression check')
    print('=' * 70)
    
    np.random.seed(42)
    weights = np.random.randn(32, 64)
    print(f'\n原始矩阵形状: {weights.shape}')
    print(f'原始参数数量: {weights.size}')
    
    print('\n【压缩率-误差权衡分析】')
    mpo = ScientificMPOCompressor()
    tradeoff = mpo.analyze_compression_tradeoff(weights, ranks=[2, 4, 8, 16, 32])
    
    print(f'  {"秩R":>6} | {"压缩率(%)":>12} | {"压缩后大小":>14} | {"重建误差":>12}')
    print(f'  {"-"*6} | {"-"*12} | {"-"*14} | {"-"*12}')
    
    for i in range(len(tradeoff['rank'])):
        print(f'  {tradeoff["rank"][i]:>6} | '
              f'{tradeoff["compression_ratio"][i]:>12.2f} | '
              f'{tradeoff["compressed_size"][i]:>14} | '
              f'{tradeoff["reconstruction_error"][i]:>12.2e}')
    
    print('\n【压缩过程演示】')
    mpo_detailed = ScientificMPOCompressor(max_rank=8)
    result = mpo_detailed.compress(weights)
    
    print(f'  原始大小: {result.original_size}')
    print(f'  压缩后大小: {result.compressed_size}')
    print(f'  压缩率: {(1 - result.compression_ratio) * 100:.2f}%')
    print(f'  保留秩: {result.rank}')
    print(f'  重建误差: {result.reconstruction_error:.2e}')
    
    reconstructed = mpo_detailed.decompress(result)
    max_error = np.max(np.abs(weights - reconstructed))
    print(f'  最大重建误差: {max_error:.2e}')
    
    print('\n' + '=' * 70)
    print('  SVD压缩原理说明')
    print('=' * 70)
    print("""
SVD（奇异值分解）压缩原理：

矩阵分解形式：
    M_{m×n} = U_{m×r} @ Σ_{r×r} @ V^T_{r×n}

其中：
- U: 左奇异向量矩阵
- Σ: 对角矩阵，对角元素为奇异值（按降序排列）
- V^T: 右奇异向量矩阵
- r: 保留的奇异值数量（秩）

压缩效果：
- 原参数数量: m × n
- 压缩后参数数量: m×r + r + r×n = r(m + n + 1)
- 当 r << min(m,n) 时，压缩效果显著

截断策略：
- 保留最大的r个奇异值
- 舍弃小奇异值引入可控的重建误差
- 误差与保留的奇异值数量成反比

应用场景：
- 高维模型参数压缩
- 数据降维
- 图像压缩
- 联邦学习通信优化
    """.strip())


if __name__ == '__main__':
    mpo_scientific_demo()
