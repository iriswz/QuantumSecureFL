"""更接近 BB84 物理过程的协议仿真。"""
import numpy as np
from typing import Dict, Tuple, List
import hashlib


class ScientificBB84Simulator:
    """BB84 协议仿真。"""
    
    # BB84 的 Z 基与 X 基。
    BASIS_Z0 = np.array([1, 0], dtype=complex)
    BASIS_Z1 = np.array([0, 1], dtype=complex)
    BASIS_X0 = (BASIS_Z0 + BASIS_Z1) / np.sqrt(2)
    BASIS_X1 = (BASIS_Z0 - BASIS_Z1) / np.sqrt(2)
    
    def __init__(self, n_photons: int = 2048):
        self.n_photons = n_photons
        self.alice_bits = None
        self.alice_bases = None
        self.bob_bases = None
        self.bob_bits = None
        self.sifted_key = None
        self.final_key = None
        self.error_rate = 0.0
        self.eavesdropping_detected = False
        self.eve_active = False
    
    def _random_bits(self, n: int) -> np.ndarray:
        return np.random.randint(0, 2, size=n)
    
    def _random_bases(self, n: int) -> np.ndarray:
        return np.random.choice(['Z', 'X'], size=n)
    
    def _prepare_photon(self, bit: int, basis: str) -> np.ndarray:
        if basis == 'Z':
            return self.BASIS_Z0 if bit == 0 else self.BASIS_Z1
        else:
            return self.BASIS_X0 if bit == 0 else self.BASIS_X1
    
    def _measure_photon(self, photon: np.ndarray, basis: str) -> int:
        if basis == 'Z':
            prob0 = np.abs(np.dot(self.BASIS_Z0.conj(), photon)) ** 2
        else:
            prob0 = np.abs(np.dot(self.BASIS_X0.conj(), photon)) ** 2
        
        return 0 if np.random.random() < prob0 else 1
    
    def _eve_intercept_resend(self, photon: np.ndarray) -> np.ndarray:
        eve_basis = np.random.choice(['Z', 'X'])
        measured_bit = self._measure_photon(photon, eve_basis)
        return self._prepare_photon(measured_bit, eve_basis)
    
    def run_protocol(self, eve_active: bool = False) -> Dict:
        """执行一次 BB84 协议。"""
        self.eve_active = eve_active
        
        self.alice_bits = self._random_bits(self.n_photons)
        self.alice_bases = self._random_bases(self.n_photons)
        
        photons = [self._prepare_photon(bit, basis) 
                   for bit, basis in zip(self.alice_bits, self.alice_bases)]
        
        if eve_active:
            photons = [self._eve_intercept_resend(ph) for ph in photons]
        
        self.bob_bases = self._random_bases(self.n_photons)
        self.bob_bits = np.array([
            self._measure_photon(ph, basis)
            for ph, basis in zip(photons, self.bob_bases)
        ])
        
        match_mask = self.alice_bases == self.bob_bases
        matched_bits_a = self.alice_bits[match_mask]
        matched_bits_b = self.bob_bits[match_mask]
        
        sample_size = min(512, len(matched_bits_a) // 4)
        if sample_size > 0:
            sample_idx = np.random.choice(len(matched_bits_a), size=sample_size, replace=False)
            mismatches = np.sum(matched_bits_a[sample_idx] != matched_bits_b[sample_idx])
            self.error_rate = mismatches / sample_size
        else:
            self.error_rate = 0.0
        
        self.eavesdropping_detected = self.error_rate > 0.11
        
        self.sifted_key = matched_bits_a if not self.eavesdropping_detected else None
        
        if self.sifted_key is not None and len(self.sifted_key) >= 256:
            bit_str = ''.join(str(b) for b in self.sifted_key)
            self.final_key = hashlib.sha256(bit_str.encode()).digest()
        else:
            self.final_key = None
        
        return {
            'status': 'success' if self.final_key else 'failed',
            'n_photons': self.n_photons,
            'matched_bits': len(matched_bits_a),
            'error_rate': round(self.error_rate * 100, 2),
            'eavesdropping_detected': self.eavesdropping_detected,
            'final_key': self.final_key.hex() if self.final_key else None,
            'eve_active': eve_active
        }
    
    def get_physics_explanation(self) -> str:
        return """
BB84协议物理原理：
1. 量子态不可克隆：无法精确复制未知量子态
2. 测量坍缩：测量会使量子态坍缩到测量基矢的本征态
3. 基矢不匹配时的概率性：当测量基矢与制备基矢不同时，
   测量结果有50%概率错误，这是量子力学的基本特性
4. Eve窃听必然引入噪声：Eve必须测量才能获取信息，
   但她的测量基矢有50%概率与Alice不匹配，导致约25%误码率
        """.strip()


class QuantumChannelNoise:
    """量子信道噪声模型。"""
    
    def __init__(self, bit_flip_prob: float = 0.01, phase_damping: float = 0.001):
        self.bit_flip_prob = bit_flip_prob
        self.phase_damping = phase_damping
    
    def apply_noise(self, photon: np.ndarray) -> np.ndarray:
        """模拟位翻转和相位阻尼。"""
        noisy = photon.copy()

        if np.random.random() < self.bit_flip_prob:
            noisy = np.array([noisy[1], noisy[0]])  # Pauli-X

        if np.random.random() < self.phase_damping:
            noisy[1] *= -1  # 相位翻转
        
        return noisy


def qkd_scientific_demo():
    """命令行自检入口。"""
    print('=' * 70)
    print('  BB84 protocol check')
    print('=' * 70)
    
    print('\n【场景1】正常通信（无窃听）')
    qkd = ScientificBB84Simulator(n_photons=2048)
    result = qkd.run_protocol(eve_active=False)
    
    print(f'  光子数: {result["n_photons"]}')
    print(f'  匹配比特数: {result["matched_bits"]}')
    print(f'  误码率: {result["error_rate"]}%')
    print(f'  最终密钥: {result["final_key"][:32]}...')
    print(f'  状态: {result["status"]}')
    
    print('\n【场景2】Eve中间人窃听攻击')
    qkd_eve = ScientificBB84Simulator(n_photons=2048)
    result_eve = qkd_eve.run_protocol(eve_active=True)
    
    print(f'  光子数: {result_eve["n_photons"]}')
    print(f'  匹配比特数: {result_eve["matched_bits"]}')
    print(f'  误码率: {result_eve["error_rate"]}%')
    print(f'  检测到窃听: {"✓ 是" if result_eve["eavesdropping_detected"] else "✗ 否"}')
    print(f'  最终密钥: {result_eve["final_key"]}')
    print(f'  状态: {"✗ 中止" if result_eve["eavesdropping_detected"] else result_eve["status"]}')
    
    print('\n' + '=' * 70)
    print('  物理原理说明')
    print('=' * 70)
    print(qkd.get_physics_explanation())


if __name__ == '__main__':
    qkd_scientific_demo()
