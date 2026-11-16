"""差分隐私噪声与隐私预算管理。"""
import numpy as np
from typing import List, Tuple, Dict, Optional, Callable
from dataclasses import dataclass
import math


@dataclass
class PrivacyBudget:
    """记录总预算、松弛项和已使用预算。"""
    epsilon: float
    delta: float = 1e-5
    used: float = 0.0
    
    def consume(self, eps: float) -> bool:
        if self.used + eps > self.epsilon:
            return False
        self.used += eps
        return True
    
    def remaining(self) -> float:
        return max(0.0, self.epsilon - self.used)


class QuantumNoiseGenerator:
    """生成用于差分隐私的混合噪声。"""
    
    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)
    
    def channel_noise(self, shape: Tuple[int, ...], scale: float = 1.0) -> np.ndarray:
        """Laplace 噪声。"""
        return self.rng.laplace(loc=0.0, scale=scale, size=shape)
    
    def measurement_noise(self, shape: Tuple[int, ...], scale: float = 1.0) -> np.ndarray:
        """Gaussian 噪声。"""
        return self.rng.normal(loc=0.0, scale=scale, size=shape)
    
    def hybrid_noise(self, shape: Tuple[int, ...], 
                     channel_ratio: float = 0.6,
                     scale: float = 1.0) -> np.ndarray:
        """按比例混合 Laplace 与 Gaussian 噪声。"""
        ch_noise = self.channel_noise(shape, scale * channel_ratio)
        me_noise = self.measurement_noise(shape, scale * (1 - channel_ratio))
        return ch_noise + me_noise


class QuantumDifferentialPrivacy:
    """给梯度或参数加噪，并跟踪隐私预算。"""
    
    def __init__(self, epsilon: float = 2.0, channel_ratio: float = 0.65,
                 sensitivity: float = 1.0, clip_norm: float = 1.0,
                 noise_seed: Optional[int] = None):
        self.budget = PrivacyBudget(epsilon=epsilon)
        resolved_seed = np.random.randint(1, 99999) if noise_seed is None else int(noise_seed)
        self.noise_gen = QuantumNoiseGenerator(seed=resolved_seed)
        self.channel_ratio = channel_ratio
        self.sensitivity = sensitivity
        self.clip_norm = clip_norm
        self.noise_history = []
    
    def _compute_noise_scale(self, local_epsilon: float, n_params: int) -> float:
        """根据局部预算计算噪声尺度。"""
        quantum_amplification = 1.0 + self.channel_ratio * 0.3
        base_scale = self.sensitivity / (local_epsilon + 1e-8)
        return base_scale / quantum_amplification * np.sqrt(n_params / 1000.0)
    
    def apply_privacy(self, params: np.ndarray, local_epsilon: float = None) -> np.ndarray:
        """对模型参数或梯度加噪。"""
        remaining = self.budget.remaining()
        if remaining <= 0:
            raise ValueError('隐私预算已耗尽，无法继续注入差分隐私噪声')

        requested_epsilon = local_epsilon
        if local_epsilon is None:
            local_epsilon = min(remaining, max(0.01, remaining * 0.02))
        elif local_epsilon <= 0 or not np.isfinite(local_epsilon):
            raise ValueError('local_epsilon 必须是正的有限数值')
        elif local_epsilon > remaining:
            local_epsilon = remaining
        
        params_norm = np.linalg.norm(params)
        if params_norm > self.clip_norm:
            params_clipped = params * (self.clip_norm / params_norm)
        else:
            params_clipped = params
        
        scale = self._compute_noise_scale(local_epsilon, params.size)
        
        noise = self.noise_gen.hybrid_noise(
            shape=params.shape,
            channel_ratio=self.channel_ratio,
            scale=scale
        )
        
        noisy_params = params_clipped + noise
        
        consumed = self.budget.consume(local_epsilon)
        if not consumed:
            raise ValueError('隐私预算不足，无法完成本次噪声注入')
        
        self.noise_history.append({
            'step': len(self.noise_history),
            'requested_epsilon': round(requested_epsilon if requested_epsilon is not None else local_epsilon, 4),
            'local_epsilon': round(local_epsilon, 4),
            'noise_scale': round(scale, 6),
            'noise_magnitude': round(float(np.linalg.norm(noise)), 4),
            'SNR_before': round(float(np.linalg.norm(params_clipped) / (np.linalg.norm(noise) + 1e-8)), 4),
            'budget_used': round(self.budget.used, 4),
            'budget_remaining': round(self.budget.remaining(), 4)
        })
        
        return noisy_params
    
    def apply_privacy_scalar(self, value: float, local_epsilon: float = None) -> float:
        arr = np.array([value])
        return float(self.apply_privacy(arr, local_epsilon)[0])
    
    def get_privacy_report(self) -> Dict:
        return {
            'total_epsilon': self.budget.epsilon,
            'delta': self.budget.delta,
            'budget_used': round(self.budget.used, 4),
            'budget_remaining': round(self.budget.remaining(), 4),
            'privacy_level': self._privacy_level(),
            'noise_rounds': len(self.noise_history),
            'channel_ratio': self.channel_ratio
        }
    
    def _privacy_level(self) -> str:
        used_ratio = self.budget.used / self.budget.epsilon if self.budget.epsilon > 0 else 1.0
        if used_ratio < 0.3:
            return '强隐私保护'
        elif used_ratio < 0.6:
            return '中等隐私保护'
        elif used_ratio < 0.9:
            return '弱隐私保护'
        else:
            return '隐私预算耗尽'
    
    def privacy_utility_tradeoff(self, epsilon_range: List[float] = None) -> Dict:
        """扫描不同 epsilon 下的噪声与效用损失。"""
        if epsilon_range is None:
            epsilon_range = [0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
        
        result = {'epsilon': [], 'noise_scale': [], 'utility_loss': [], 'privacy_risk': []}
        
        sample_params = np.random.randn(100) * 0.1
        
        for eps in epsilon_range:
            scale = self._compute_noise_scale(eps, sample_params.size)
            noise = self.noise_gen.hybrid_noise(sample_params.shape, self.channel_ratio, scale)
            
            signal_power = np.linalg.norm(sample_params)
            noise_power = np.linalg.norm(noise)
            snr = signal_power / (noise_power + 1e-8)
            utility_loss = 1.0 / (1.0 + snr)
            
            privacy_risk = min(1.0, 1.0 / (eps + 0.5))
            
            result['epsilon'].append(round(eps, 2))
            result['noise_scale'].append(round(scale, 6))
            result['utility_loss'].append(round(utility_loss * 100, 2))
            result['privacy_risk'].append(round(privacy_risk * 100, 2))
        
        return result
    
    def get_noise_history(self) -> List[Dict]:
        return self.noise_history
    
    def reset(self, new_epsilon: float = None):
        if new_epsilon is not None:
            self.budget = PrivacyBudget(epsilon=new_epsilon)
        else:
            self.budget = PrivacyBudget(epsilon=self.budget.epsilon)
        self.noise_history = []


def qdp_demo():
    """命令行自检入口。"""
    print('=' * 60)
    print('  QDP noise check')
    print('=' * 60)
    
    qdp = QuantumDifferentialPrivacy(epsilon=5.0, channel_ratio=0.65)
    print(f'\n[初始化] 总隐私预算 ε={qdp.budget.epsilon}, 混合噪声比例={qdp.channel_ratio}')
    
    print('\n[模拟] 对模型梯度注入量子差分隐私噪声 (5轮训练)')
    for i in range(5):
        grad = np.random.randn(50) * 0.5
        noisy_grad = qdp.apply_privacy(grad, local_epsilon=0.8)
        
        report = qdp.get_privacy_report()
        history = qdp.noise_history[-1]
        print(f'  第{i+1}轮: ε消耗={history["local_epsilon"]}, '
              f'噪声强度={history["noise_magnitude"]}, '
              f'剩余预算={report["budget_remaining"]}, '
              f'等级={report["privacy_level"]}')
    
    print('\n[隐私-效用权衡分析]')
    tradeoff = qdp.privacy_utility_tradeoff()
    print(f'  {"ε":>6} | {"噪声强度":>10} | {"效用损失(%)":>10} | {"隐私风险(%)":>10}')
    print(f'  {"-"*6} | {"-"*10} | {"-"*12} | {"-"*12}')
    for i in range(len(tradeoff['epsilon'])):
        print(f'  {tradeoff["epsilon"][i]:>6} | {tradeoff["noise_scale"][i]:>10.6f} | '
              f'{tradeoff["utility_loss"][i]:>12.2f} | {tradeoff["privacy_risk"][i]:>12.2f}')
    
    print(f'\n[隐私报告] {qdp.get_privacy_report()}')


if __name__ == '__main__':
    qdp_demo()
