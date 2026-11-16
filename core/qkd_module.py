"""BB84 密钥协商和一个轻量的混沌流加密实现。"""
import numpy as np
from typing import Tuple, List, Dict
import hashlib
import hmac
import os


class BB84Simulator:
    """BB84 协议的简化仿真器。"""
    
    BASIS = {'+': np.array([[1, 0], [0, 1]]),   # 标准基 (0/90度)
             'x': np.array([[1, 1], [1, -1]]) / np.sqrt(2)}  # 对角基 (45/135度)
    
    def __init__(self, n_photons: int = 2048, eve_active: bool = False):
        self.n_photons = n_photons
        self.eve_active = eve_active
        self.alice_bits = None
        self.alice_bases = None
        self.bob_bits = None
        self.bob_bases = None
        self.sifted_key_a = None
        self.sifted_key_b = None
        self.error_rate = 0.0
        self.final_key_a = None
        self.final_key_b = None
        self.eavesdropping_detected = False
    
    def run_protocol(self) -> Dict:
        """运行一次密钥协商。"""
        self.alice_bits = np.random.randint(0, 2, size=self.n_photons)
        self.alice_bases = np.random.choice(['+', 'x'], size=self.n_photons)
        
        received_photons = self._transmit_photons()
        
        self.bob_bases = np.random.choice(['+', 'x'], size=self.n_photons)
        self.bob_bits = self._measure_photons(received_photons, self.bob_bases)
        
        match_mask = (self.alice_bases == self.bob_bases)
        self.sifted_key_a = self.alice_bits[match_mask]
        self.sifted_key_b = self.bob_bits[match_mask]
        
        sample_size = min(512, len(self.sifted_key_a) // 4)
        if sample_size > 0:
            sample_idx = np.random.choice(len(self.sifted_key_a), size=sample_size, replace=False)
            mismatches = np.sum(self.sifted_key_a[sample_idx] != self.sifted_key_b[sample_idx])
            self.error_rate = mismatches / sample_size
        
        self.eavesdropping_detected = self.error_rate > 0.11
        
        if not self.eavesdropping_detected and len(self.sifted_key_a) > 256:
            self.final_key_a = self._privacy_amplification(self.sifted_key_a)
            self.final_key_b = self._privacy_amplification(self.sifted_key_b)
        else:
            self.final_key_a = self.final_key_b = None
        
        return {
            'n_photons': self.n_photons,
            'sifted_key_length': len(self.sifted_key_a) if self.sifted_key_a is not None else 0,
            'error_rate': round(self.error_rate * 100, 2),
            'eavesdropping_detected': self.eavesdropping_detected,
            'final_key': self.final_key_a.hex() if self.final_key_a else None,
            'eve_active': self.eve_active
        }
    
    def _transmit_photons(self) -> np.ndarray:
        """传输光子；Eve 拦截时引入约 25% 误码。"""
        photons = []
        for bit, basis in zip(self.alice_bits, self.alice_bases):
            if basis == '+':
                state = np.array([1, 0]) if bit == 0 else np.array([0, 1])
            else:
                state = np.array([1, 1]) / np.sqrt(2) if bit == 0 else np.array([1, -1]) / np.sqrt(2)
            photons.append(state)
        photons = np.array(photons)
        
        if self.eve_active:
            # 拦截-重发会放大误码率，比例略高一点方便小样本下稳定复现。
            for i in range(self.n_photons):
                if np.random.random() < 0.28:  # ~28%误码率 (>11%阈值可稳定检测)
                    photons[i] = np.abs(photons[i][::-1])
        
        return photons
    
    def _measure_photons(self, photons: np.ndarray, bases: np.ndarray) -> np.ndarray:
        bits = np.zeros(len(photons), dtype=int)
        for i in range(len(photons)):
            if bases[i] == '+':
                prob_0 = photons[i][0] ** 2
            else:
                prob_0 = ((photons[i][0] + photons[i][1]) / np.sqrt(2)) ** 2
            bits[i] = 0 if np.random.random() < prob_0 else 1
        return bits
    
    def _privacy_amplification(self, key_bits: np.ndarray) -> bytes:
        """通过哈希把筛选密钥压缩为定长密钥。"""
        bit_str = ''.join(str(b) for b in key_bits)
        return hashlib.sha256(bit_str.encode()).digest()
    
    def get_statistics(self) -> Dict:
        return {
            '光子总数': self.n_photons,
            '筛选密钥长度': len(self.sifted_key_a) if self.sifted_key_a is not None else 0,
            '误码率(%)': round(self.error_rate * 100, 2),
            '检测到窃听': self.eavesdropping_detected,
            '最终密钥长度(bit)': 256 if self.final_key_a else 0
        }


class ChaoticEncryption:
    """Logistic/Tent 映射组合成的演示用流加密器。"""
    
    def __init__(self, qkd_key: bytes, chaos_params: Dict = None):
        seed = int.from_bytes(qkd_key[:8], 'big') if len(qkd_key) >= 8 else 12345
        np.random.seed(seed & 0xFFFFFFFF)
        
        self.params = chaos_params or {
            'r_logistic': 3.99,
            'x0_logistic': 0.314159,
            'mu_tent': 1.999,
            'x0_tent': 0.271828,
        }
        self.chaos_sequence = self._generate_chaos_sequence(length=8192)
    
    def _logistic_map(self, x: float, r: float, n: int) -> np.ndarray:
        """Logistic 映射: x_{n+1} = r * x_n * (1 - x_n)"""
        seq = np.zeros(n)
        seq[0] = x
        for i in range(1, n):
            seq[i] = r * seq[i-1] * (1 - seq[i-1])
        return seq
    
    def _tent_map(self, x: float, mu: float, n: int) -> np.ndarray:
        """Tent 映射: x_{n+1} = mu * min(x, 1-x)"""
        seq = np.zeros(n)
        seq[0] = x
        for i in range(1, n):
            seq[i] = mu * min(seq[i-1], 1 - seq[i-1])
        return seq
    
    def _generate_chaos_sequence(self, length: int = 8192) -> np.ndarray:
        """生成双混沌组合序列 (用作流密码)"""
        seq1 = self._logistic_map(self.params['x0_logistic'], self.params['r_logistic'], length)
        seq2 = self._tent_map(self.params['x0_tent'], self.params['mu_tent'], length)
        combined = np.abs(seq1 - seq2)
        return (combined * 256).astype(np.uint8)
    
    def encrypt(self, data: bytes, adapt_level: str = 'normal') -> bytes:
        """用不同序列偏移执行多轮异或。"""
        rounds = {'low': 1, 'normal': 3, 'high': 7}[adapt_level]
        result = np.frombuffer(data, dtype=np.uint8).copy()
        seq_len = len(self.chaos_sequence)
        
        for r in range(rounds):
            offset = (r * 257) % seq_len
            chaos_rotated = np.concatenate([
                self.chaos_sequence[offset:], self.chaos_sequence[:offset]
            ])
            chaos_expanded = np.tile(chaos_rotated, (len(result) // seq_len) + 1)[:len(result)]
            result = np.bitwise_xor(result, chaos_expanded.astype(np.uint8))
        
        return result.tobytes()
    
    def decrypt(self, encrypted_data: bytes, adapt_level: str = 'normal') -> bytes:
        """按相反轮序执行异或。"""
        rounds = {'low': 1, 'normal': 3, 'high': 7}[adapt_level]
        result = np.frombuffer(encrypted_data, dtype=np.uint8).copy()
        seq_len = len(self.chaos_sequence)
        
        for r in range(rounds - 1, -1, -1):
            offset = (r * 257) % seq_len
            chaos_rotated = np.concatenate([
                self.chaos_sequence[offset:], self.chaos_sequence[:offset]
            ])
            chaos_expanded = np.tile(chaos_rotated, (len(result) // seq_len) + 1)[:len(result)]
            result = np.bitwise_xor(result, chaos_expanded.astype(np.uint8))
        
        return result.tobytes()
    
    def adapt_to_channel(self, noise_level: float) -> str:
        if noise_level < 0.05:
            return 'low'
        elif noise_level < 0.2:
            return 'normal'
        else:
            return 'high'


class QuantumCommunicationChannel:
    """QKD 会话密钥信道，提供随机 nonce、密钥分离与 HMAC 载荷认证。"""
    
    def __init__(self, n_photons: int = 1024):
        self.n_photons = n_photons
        self.qkd = None
        self.cipher = None
        self.session_key = None
        self.encryption_key = None
        self.authentication_key = None
        self.channel_log = []
    
    def establish(self, eve_active: bool = False) -> Dict:
        self.qkd = BB84Simulator(n_photons=self.n_photons, eve_active=eve_active)
        qkd_result = self.qkd.run_protocol()
        
        if qkd_result['eavesdropping_detected']:
            self.channel_log.append('⚠ 检测到窃听，中止密钥分发')
            return {'status': 'failed', 'reason': 'eavesdropping', **qkd_result}

        if not qkd_result.get('final_key'):
            self.channel_log.append('⚠ 筛选密钥长度不足，无法初始化加密器')
            return {'status': 'failed', 'reason': 'insufficient_key_material', **qkd_result}
        
        key_bytes = bytes.fromhex(qkd_result['final_key'])
        self.session_key = key_bytes
        self.encryption_key = hashlib.sha256(b'QuantumSecureFL|encryption|' + key_bytes).digest()
        self.authentication_key = hashlib.sha256(b'QuantumSecureFL|authentication|' + key_bytes).digest()
        self.cipher = ChaoticEncryption(qkd_key=key_bytes)
        self.channel_log.append(f'QKD 完成，误码率 {qkd_result["error_rate"]}%')
        self.channel_log.append('加密器已初始化')
        
        return {'status': 'success', **qkd_result}
    
    def _xor_session_stream(self, data: bytes, nonce: bytes, encryption_level: str) -> bytes:
        """用会话密钥、随机 nonce 和 SHAKE-256 生成一次性字节流。"""
        domain = b'QuantumSecureFL-v1|' + encryption_level.encode('ascii') + b'|'
        stream = hashlib.shake_256(domain + self.encryption_key + nonce).digest(len(data))
        return bytes(a ^ b for a, b in zip(data, stream))

    def secure_send_bytes(self, payload: bytes, noise_level: float = 0.05) -> Dict:
        """加密并认证二进制载荷，供模型梯度/MPO 张量传输使用。"""
        if self.session_key is None:
            return {'status': 'error', 'reason': 'channel_not_established'}
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            return {'status': 'error', 'reason': 'payload_must_be_bytes'}

        adapt_level = self.cipher.adapt_to_channel(noise_level)
        data = bytes(payload)
        nonce = os.urandom(16)
        encrypted = self._xor_session_stream(data, nonce, adapt_level)
        tag = hmac.new(
            self.authentication_key,
            adapt_level.encode('ascii') + nonce + encrypted,
            hashlib.sha256
        ).digest()
        frame = nonce + tag + encrypted
        self.channel_log.append(
            f'→ 发送二进制载荷 {len(data)} bytes | 加密强度: {adapt_level} | HMAC: SHA-256'
        )
        return {
            'status': 'success',
            'encrypted_payload': frame,
            'encrypted_size_bytes': len(frame),
            'plaintext_size_bytes': len(data),
            'encryption_level': adapt_level
        }

    def secure_receive_bytes(self, encrypted_payload: bytes,
                             encryption_level: str = 'normal') -> Dict:
        """验证 HMAC 后解密二进制载荷；任何篡改都会在解密前被拒绝。"""
        if self.session_key is None:
            return {'status': 'error', 'reason': 'channel_not_established'}
        try:
            frame = bytes(encrypted_payload)
            if len(frame) < 48:
                return {'status': 'failed', 'reason': 'invalid_encrypted_frame'}
            nonce, received_tag, encrypted = frame[:16], frame[16:48], frame[48:]
            expected_tag = hmac.new(
                self.authentication_key,
                encryption_level.encode('ascii') + nonce + encrypted,
                hashlib.sha256
            ).digest()
            if not hmac.compare_digest(received_tag, expected_tag):
                self.channel_log.append('⚠ 载荷认证失败，拒绝解密')
                return {'status': 'failed', 'reason': 'authentication_failed'}
            decrypted = self._xor_session_stream(encrypted, nonce, encryption_level)
            self.channel_log.append(f'← 载荷认证与解密通过: {len(decrypted)} bytes')
            return {'status': 'success', 'payload': decrypted}
        except Exception as e:
            return {'status': 'failed', 'reason': f'decryption_error: {str(e)}'}

    def secure_send(self, message: str, noise_level: float = 0.05) -> Dict:
        """安全发送 UTF-8 消息（兼容原有文本接口）。"""
        result = self.secure_send_bytes(message.encode('utf-8'), noise_level=noise_level)
        if result.get('status') != 'success':
            return result
        return {
            **result,
            'original': message,
            'encrypted_hex': result['encrypted_payload'].hex(),
        }

    def secure_receive(self, encrypted_hex: str, encryption_level: str = 'normal') -> Dict:
        """安全接收 UTF-8 消息（兼容原有文本接口）。"""
        try:
            frame = bytes.fromhex(encrypted_hex)
        except (TypeError, ValueError) as exc:
            return {'status': 'failed', 'reason': f'invalid_hex: {exc}'}
        result = self.secure_receive_bytes(frame, encryption_level=encryption_level)
        if result.get('status') != 'success':
            return result
        try:
            message = result['payload'].decode('utf-8')
        except UnicodeDecodeError as exc:
            return {'status': 'failed', 'reason': f'decoding_error: {exc}'}
        return {'status': 'success', 'message': message}
    
    def get_log(self) -> List[str]:
        return self.channel_log


def qkd_demo():
    """命令行自检入口。"""
    print('=' * 60)
    print('  QKD + chaotic encryption check')
    print('=' * 60)
    
    print('\n[normal channel]')
    channel = QuantumCommunicationChannel(n_photons=2048)
    result = channel.establish(eve_active=False)
    print(f'  状态: {result["status"]} | 误码率: {result["error_rate"]}%')
    
    msg = '模型参数梯度 vector_0x1F3A9C...'
    send_result = channel.secure_send(msg, noise_level=0.08)
    print(f'  加密后大小: {send_result["encrypted_size_bytes"]} bytes')
    recv_result = channel.secure_receive(send_result['encrypted_hex'], send_result['encryption_level'])
    print(f'  解密结果: {recv_result["message"]}')
    print(f'  一致性校验: {"通过" if recv_result["message"] == msg else "失败"}')
    
    print('\n[intercept-resend]')
    channel2 = QuantumCommunicationChannel(n_photons=2048)
    result2 = channel2.establish(eve_active=True)
    print(f'  状态: {result2["status"]} | 误码率: {result2["error_rate"]}% | 窃听检测: {result2["eavesdropping_detected"]}')
    
    print('\n  通信日志:')
    for log in channel.get_log():
        print(f'    {log}')


if __name__ == '__main__':
    qkd_demo()
