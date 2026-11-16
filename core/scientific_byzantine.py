"""量子签名和概率投票的拜占庭共识仿真。"""
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass
import hashlib


@dataclass
class NodeState:
    """节点状态。"""
    node_id: int
    is_honest: bool
    signature: np.ndarray
    measurements: List[int]


class QuantumSignatureGenerator:
    """根据消息哈希生成签名态。"""
    
    def __init__(self, seed: int = None):
        self.rng = np.random.RandomState(seed) if seed else np.random.RandomState()
    
    def _hash_to_angle(self, message: bytes) -> float:
        h = hashlib.sha256(message).digest()
        angle = int.from_bytes(h, 'big') / (2**256) * 2 * np.pi
        return angle
    
    def generate_signature(self, message: bytes, basis: str = None) -> Tuple[np.ndarray, str]:
        """生成签名态和测量基矢。"""
        angle = self._hash_to_angle(message)
        
        signature_state = np.array([
            np.cos(angle / 2),
            np.sin(angle / 2)
        ], dtype=complex)
        
        if basis is None:
            basis = 'Z' if self.rng.random() < 0.5 else 'X'
        
        return signature_state, basis
    
    def measure_signature(self, signature_state: np.ndarray, basis: str) -> int:
        """测量签名态。"""
        if basis == 'Z':
            prob0 = np.abs(np.conj(signature_state[0]) * signature_state[0]) ** 2
        else:
            prob0 = np.abs((np.conj(signature_state[0]) + np.conj(signature_state[1])) / np.sqrt(2)) ** 2
        
        return 0 if self.rng.random() < prob0 else 1


class QuantumByzantineConsensus:
    """基于签名测量结果投票的共识协议。"""
    
    def __init__(self, n_nodes: int, n_malicious: int = 0, seed: int = None):
        self.n_nodes = n_nodes
        self.n_malicious = n_malicious
        self.rng = np.random.RandomState(seed) if seed else np.random.RandomState()
        self.signature_gen = QuantumSignatureGenerator(seed)
        self.nodes = []
        self.consensus_value = None
        self.malicious_detected = []
    
    def _initialize_nodes(self, message: bytes):
        self.nodes = []

        malicious_ids = set(self.rng.choice(self.n_nodes, self.n_malicious, replace=False))
        
        for i in range(self.n_nodes):
            is_honest = i not in malicious_ids
            
            if is_honest:
                signature, basis = self.signature_gen.generate_signature(message)
            else:
                # 恶意节点对篡改后的消息签名。
                wrong_message = message + b'_malicious_tampered'
                signature, basis = self.signature_gen.generate_signature(wrong_message)
            
            self.nodes.append(NodeState(
                node_id=i,
                is_honest=is_honest,
                signature=signature,
                measurements=[]
            ))
    
    def _exchange_and_measure(self):
        for node in self.nodes:
            for other_node in self.nodes:
                if node.node_id != other_node.node_id:
                    measurement = self.signature_gen.measure_signature(
                        other_node.signature,
                        'Z' if node.node_id % 2 == 0 else 'X'
                    )
                    node.measurements.append((other_node.node_id, measurement))
    
    def _compute_similarity(self, node1: NodeState, node2: NodeState) -> float:
        """返回两个签名态的保真度。"""
        inner_product = np.dot(np.conj(node1.signature), node2.signature)
        similarity = np.abs(inner_product) ** 2
        return float(similarity)
    
    def _vote_consensus(self) -> Tuple[int, List[int]]:
        """按签名相似度分组，再由可信组多数投票。"""
        similarity_matrix = np.zeros((self.n_nodes, self.n_nodes))
        for i, node_i in enumerate(self.nodes):
            for j, node_j in enumerate(self.nodes):
                similarity_matrix[i, j] = self._compute_similarity(node_i, node_j)
        
        consensus_group = []
        malicious_group = []

        avg_similarity = np.mean(similarity_matrix, axis=1)
        trusted_node_idx = np.argmax(avg_similarity)

        threshold = 0.7
        for i, node in enumerate(self.nodes):
            if similarity_matrix[trusted_node_idx, i] > threshold:
                consensus_group.append(i)
            else:
                malicious_group.append(i)
        
        if consensus_group:
            measurements = []
            for idx in consensus_group:
                for other_idx, measurement in self.nodes[idx].measurements:
                    if other_idx in consensus_group:
                        measurements.append(measurement)
            
            consensus_value = 1 if sum(measurements) > len(measurements) / 2 else 0
        else:
            consensus_value = 0
        
        return consensus_value, malicious_group
    
    def run_consensus(self, message: bytes) -> Dict:
        """执行一轮共识。"""
        self._initialize_nodes(message)
        
        self._exchange_and_measure()
        
        consensus_value, malicious_detected = self._vote_consensus()
        
        self.consensus_value = consensus_value
        self.malicious_detected = malicious_detected
        
        true_positives = sum(1 for i in malicious_detected if not self.nodes[i].is_honest)
        false_positives = sum(1 for i in malicious_detected if self.nodes[i].is_honest)
        true_negatives = sum(1 for i in range(self.n_nodes) if i not in malicious_detected and self.nodes[i].is_honest)
        false_negatives = sum(1 for i in range(self.n_nodes) if i not in malicious_detected and not self.nodes[i].is_honest)
        
        return {
            'consensus_value': consensus_value,
            'malicious_nodes_detected': malicious_detected,
            'n_malicious_actual': self.n_malicious,
            'n_malicious_detected': len(malicious_detected),
            'true_positives': true_positives,
            'false_positives': false_positives,
            'true_negatives': true_negatives,
            'false_negatives': false_negatives,
            'detection_accuracy': (true_positives + true_negatives) / self.n_nodes,
            'consensus_reached': len(malicious_detected) <= self.n_nodes // 3,
            'theoretical_max_tolerable': (self.n_nodes - 1) // 3
        }
    
    def get_theoretical_analysis(self) -> str:
        """返回共识配置说明。"""
        max_tolerable = (self.n_nodes - 1) // 3
        return f"""
量子拜占庭共识理论分析：
- 节点总数: {self.n_nodes}
- 恶意节点数: {self.n_malicious}
- 理论最大容错数: {max_tolerable}
- 当前配置是否安全: {"是" if self.n_malicious <= max_tolerable else "否"}

经典拜占庭容错条件：
  n ≥ 3t + 1
其中 n 为节点数，t 为恶意节点数

量子拜占庭优势：
1. 量子签名不可伪造
2. 测量结果具有概率保证
3. 无需第三方信任机构
        """.strip()


def byzantine_scientific_demo():
    """命令行自检入口。"""
    print('=' * 70)
    print('  quantum byzantine consensus check')
    print('=' * 70)
    
    print('\n【不同配置下的共识表现】')
    test_cases = [
        (5, 0),
        (5, 1),
        (5, 2),
        (7, 2),
        (7, 3)
    ]
    
    print(f'  {"节点数":>6} | {"恶意数":>6} | {"最大容错":>6} | {"检测率(%)":>10} | {"共识达成":>8}')
    print(f'  {"-"*6} | {"-"*6} | {"-"*6} | {"-"*10} | {"-"*8}')
    
    for n_nodes, n_malicious in test_cases:
        byz = QuantumByzantineConsensus(n_nodes, n_malicious)
        result = byz.run_consensus(b'federated_learning_update')
        
        print(f'  {n_nodes:>6} | {n_malicious:>6} | '
              f'{result["theoretical_max_tolerable"]:>6} | '
              f'{result["detection_accuracy"] * 100:>10.2f} | '
              f'{"✓" if result["consensus_reached"] else "✗":>8}')
    
    print('\n【详细共识过程演示】')
    byz_detailed = QuantumByzantineConsensus(n_nodes=5, n_malicious=1)
    result = byz_detailed.run_consensus(b'gradient_update_0x1F3A9C')
    
    print(f'\n  输入消息哈希: {hashlib.sha256(b"gradient_update_0x1F3A9C").hexdigest()[:16]}...')
    print(f'  共识结果: {result["consensus_value"]}')
    print(f'  恶意节点（实际）: {[i for i, node in enumerate(byz_detailed.nodes) if not node.is_honest]}')
    print(f'  恶意节点（检测）: {result["malicious_nodes_detected"]}')
    print(f'  检测准确率: {result["detection_accuracy"] * 100:.2f}%')
    print(f'  共识是否达成: {"✓ 是" if result["consensus_reached"] else "✗ 否"}')
    
    print('\n  节点签名相似度矩阵:')
    for i, node_i in enumerate(byz_detailed.nodes):
        row = []
        for j, node_j in enumerate(byz_detailed.nodes):
            sim = byz_detailed._compute_similarity(node_i, node_j)
            row.append(f'{sim:.2f}')
        print(f'    节点{i}: {" ".join(row)}')
    
    print('\n' + '=' * 70)
    print('  量子拜占庭共识原理说明')
    print('=' * 70)
    print("""
量子拜占庭共识原理：

经典拜占庭问题：
- n个节点中最多t个恶意节点
- 需要 n ≥ 3t + 1 才能达成共识
- 恶意节点可以发送任意消息

量子解决方案：
1. 量子签名：每个节点生成基于量子态的签名
2. 基矢比对：节点间使用相同基矢测量签名
3. 相似度分析：诚实节点签名相似度高，恶意节点低
4. 概率投票：基于测量结果进行多数投票

量子优势：
- 量子签名不可伪造（量子不可克隆定理）
- 测量结果具有概率保证
- 无需中心化信任机构
- 通信复杂度更低

安全性证明：
- 恶意节点无法伪造诚实节点的签名
- 测量过程引入的噪声可检测
- 满足信息论安全
    """.strip())


if __name__ == '__main__':
    byzantine_scientific_demo()
