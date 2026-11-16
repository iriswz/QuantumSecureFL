"""联邦训练记录的哈希链和拜占庭共识仿真。"""
import hashlib
import time
import json
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from copy import deepcopy


@dataclass
class Block:
    """单个训练轮次的链上记录。"""
    index: int
    timestamp: float
    model_hash: str
    model_metadata: Dict
    transactions: List[Dict]
    previous_hash: str
    nonce: int = 0
    consensus_signatures: List[str] = None
    
    def hash(self) -> str:
        """计算区块哈希 (SHA-256)"""
        block_dict = asdict(self)
        block_dict['consensus_signatures'] = sorted(block_dict.get('consensus_signatures') or [])
        block_dict['transactions'] = sorted(
            [json.dumps(t, sort_keys=True) for t in block_dict['transactions']]
        )
        block_string = json.dumps(block_dict, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


class Blockchain:
    """用哈希链保存联邦学习轮次记录。"""
    
    def __init__(self, difficulty: int = 3):
        self.difficulty = difficulty
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        genesis = Block(
            index=0,
            timestamp=time.time(),
            model_hash='0' * 64,
            model_metadata={'type': 'genesis', 'round': 0},
            transactions=[],
            previous_hash='0' * 64,
            nonce=0,
            consensus_signatures=['genesis_signature']
        )
        genesis.nonce = self._proof_of_work(genesis)
        self.chain.append(genesis)
    
    def _proof_of_work(self, block: Block) -> int:
        """找到一个满足难度前缀的 nonce。"""
        nonce = 0
        target = '0' * self.difficulty
        while True:
            block.nonce = nonce
            if block.hash().startswith(target):
                return nonce
            nonce += 1
    
    def add_transaction(self, client_id: int, grad_hash: str, metadata: Dict = None) -> int:
        self.pending_transactions.append({
            'client_id': client_id,
            'grad_hash': grad_hash,
            'metadata': metadata or {},
            'timestamp': time.time()
        })
        return self.chain[-1].index + 1
    
    def mine_block(self, model_params: np.ndarray, model_metadata: Dict,
                   consensus_sigs: List[str] = None) -> Block:
        """写入新区块。"""
        model_hash = hashlib.sha256(
            model_params.tobytes() if isinstance(model_params, np.ndarray)
            else str(model_params).encode()
        ).hexdigest()
        
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            model_hash=model_hash,
            model_metadata=model_metadata,
            transactions=self.pending_transactions,
            previous_hash=self.chain[-1].hash(),
            nonce=0,
            consensus_signatures=consensus_sigs or ['default_consensus']
        )
        new_block.nonce = self._proof_of_work(new_block)
        self.chain.append(new_block)
        self.pending_transactions = []
        return new_block
    
    def validate_chain(self) -> Tuple[bool, str]:
        """验证 PoW 和前后区块哈希关系。"""
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            
            target = '0' * self.difficulty
            if not curr.hash().startswith(target):
                return False, f'区块 {i} PoW 验证失败'
            
            if curr.previous_hash != prev.hash():
                return False, f'区块 {i} 与前块哈希链断裂 (可能被篡改)'
        
        return True, '区块链完整有效'
    
    def trace_model_history(self, model_hash: str = None) -> List[Dict]:
        result = []
        for block in self.chain:
            if model_hash is None or block.model_hash == model_hash:
                result.append({
                    'index': block.index,
                    'timestamp': block.timestamp,
                    'model_hash': block.model_hash,
                    'metadata': block.model_metadata,
                    'n_transactions': len(block.transactions)
                })
        return result
    
    def get_chain_summary(self) -> Dict:
        valid, msg = self.validate_chain()
        return {
            'length': len(self.chain),
            'is_valid': valid,
            'validation_msg': msg,
            'difficulty': self.difficulty,
            'total_transactions': sum(len(b.transactions) for b in self.chain),
            'last_block_hash': self.chain[-1].hash()
        }


class QuantumByzantineConsensus:
    """基于签名相似度和多数投票的拜占庭共识仿真。"""
    
    def __init__(self, n_nodes: int = 5, n_qubits: int = 32):
        self.n_nodes = n_nodes
        self.n_qubits = n_qubits
        self.max_malicious = (n_nodes - 1) // 3
        self.consensus_rounds = []
    
    def _quantum_sign(self, value_hash: str, node_id: int,
                      is_malicious: bool = False) -> Dict:
        """生成节点签名。"""
        honest_seed = int(hashlib.md5(value_hash.encode()).hexdigest()[:8], 16)
        honest_rng = np.random.RandomState(honest_seed & 0x7FFFFFFF)
        honest_bits = honest_rng.randint(0, 2, size=self.n_qubits)
        honest_bases = honest_rng.choice(['+', 'x'], size=self.n_qubits)
        
        if not is_malicious:
            bits = honest_bits
            bases = honest_bases
        else:
            bad_rng = np.random.RandomState(node_id * 10007 + 42)
            bits = bad_rng.randint(0, 2, size=self.n_qubits)
            bases = bad_rng.choice(['+', 'x'], size=self.n_qubits)
        
        return {
            'node_id': node_id,
            'bits': bits,
            'bases': bases,
            'hash': value_hash,
            'is_malicious': is_malicious
        }
    
    def reach_consensus(self, value_hash: str,
                        malicious_nodes: List[int] = None) -> Dict:
        """执行一轮共识。"""
        malicious_nodes = malicious_nodes or []
        signatures = []
        
        for node_id in range(self.n_nodes):
            sig = self._quantum_sign(
                value_hash, node_id,
                is_malicious=node_id in malicious_nodes
            )
            signatures.append(sig)
        
        votes_matrix = np.zeros((self.n_nodes, self.n_nodes), dtype=int)
        
        for i in range(self.n_nodes):
            for j in range(self.n_nodes):
                if i == j:
                    votes_matrix[i][j] = 1
                    continue
                match_bases = signatures[i]['bases'] == signatures[j]['bases']
                if match_bases.sum() == 0:
                    similarity = 0.5
                else:
                    match_bits = signatures[i]['bits'][match_bases] == signatures[j]['bits'][match_bases]
                    similarity = match_bits.mean()
                
                votes_matrix[i][j] = 1 if similarity > 0.65 else 0
        
        support_rates = votes_matrix.mean(axis=0)
        honest_threshold = 0.5
        
        detected_malicious = [i for i in range(self.n_nodes) if support_rates[i] < honest_threshold]
        honest_nodes = [i for i in range(self.n_nodes) if support_rates[i] >= honest_threshold]
        
        consensus_approved = len(honest_nodes) > self.n_nodes * 2 / 3
        
        sig_hashes = []
        for idx in honest_nodes:
            sig_str = f'{idx}-{"".join(map(str, signatures[idx]["bits"][:16]))}'
            sig_hashes.append(hashlib.sha256(sig_str.encode()).hexdigest()[:16])
        
        round_info = {
            'round': len(self.consensus_rounds),
            'value_hash': value_hash[:16] + '...',
            'n_nodes': self.n_nodes,
            'max_malicious_tolerated': self.max_malicious,
            'actual_malicious': len(malicious_nodes),
            'malicious_nodes': malicious_nodes,
            'detected_malicious': detected_malicious,
            'honest_nodes': honest_nodes,
            'support_rates': [round(float(r), 3) for r in support_rates],
            'consensus_reached': consensus_approved,
            'consensus_signatures': sig_hashes,
            'detection_accuracy': self._calc_detection_accuracy(malicious_nodes, detected_malicious)
        }
        
        self.consensus_rounds.append(round_info)
        return round_info
    
    def _calc_detection_accuracy(self, actual: List[int], detected: List[int]) -> float:
        actual_set = set(actual)
        detected_set = set(detected)
        if not actual_set:
            return 1.0 if not detected_set else 0.0
        tp = len(actual_set & detected_set)
        fp = len(detected_set - actual_set)
        fn = len(actual_set - detected_set)
        return tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 1.0
    
    def get_history(self) -> List[Dict]:
        return self.consensus_rounds


class SecureFederatedLedger:
    """训练轮次账本，组合交易、共识和哈希链。"""
    
    def __init__(self, n_nodes: int = 5, blockchain_difficulty: int = 3):
        self.blockchain = Blockchain(difficulty=blockchain_difficulty)
        self.consensus = QuantumByzantineConsensus(n_nodes=n_nodes)
        self.model_records = []
    
    def record_round(self, round_num: int, model_params: np.ndarray,
                     client_metadata: List[Dict],
                     model_accuracy: float,
                     malicious_nodes: List[int] = None) -> Dict:
        """记录一轮联邦学习。"""
        for meta in client_metadata:
            grad_hash = hashlib.sha256(
                json.dumps(meta, sort_keys=True).encode()
            ).hexdigest()
            self.blockchain.add_transaction(
                client_id=meta.get('client_id', 0),
                grad_hash=grad_hash,
                metadata=meta
            )
        
        model_hash = hashlib.sha256(model_params.tobytes()).hexdigest()
        consensus_result = self.consensus.reach_consensus(
            value_hash=model_hash,
            malicious_nodes=malicious_nodes or []
        )
        
        if not consensus_result['consensus_reached']:
            return {
                'status': 'consensus_failed',
                'round': round_num,
                'consensus': consensus_result
            }
        
        model_metadata = {
            'round': round_num,
            'accuracy': model_accuracy,
            'n_clients': len(client_metadata),
            'timestamp': time.time()
        }
        block = self.blockchain.mine_block(
            model_params=model_params,
            model_metadata=model_metadata,
            consensus_sigs=consensus_result['consensus_signatures']
        )
        
        record = {
            'status': 'success',
            'round': round_num,
            'block_index': block.index,
            'block_hash': block.hash(),
            'accuracy': model_accuracy,
            'consensus': consensus_result,
            'blockchain_valid': self.blockchain.validate_chain()[0]
        }
        self.model_records.append(record)
        return record
    
    def get_summary(self) -> Dict:
        chain_summary = self.blockchain.get_chain_summary()
        return {
            'blockchain': chain_summary,
            'consensus_rounds': len(self.consensus.consensus_rounds),
            'model_records': len(self.model_records),
            'total_malicious_detected': sum(
                len(r['consensus']['detected_malicious']) for r in self.model_records
                if 'consensus' in r
            )
        }


def blockchain_demo():
    """命令行自检入口。"""
    print('=' * 60)
    print('  blockchain + consensus check')
    print('=' * 60)
    
    ledger = SecureFederatedLedger(n_nodes=5, blockchain_difficulty=3)
    print(f'\n[初始化] 5节点共识网络 | PoW难度: {ledger.blockchain.difficulty}')
    print(f'  最大容忍恶意节点数: {ledger.consensus.max_malicious} (1/3原则)')
    
    print(f'\n[模拟] 3轮联邦学习上链 (包含恶意节点)')
    for r in range(3):
        model_params = np.random.randn(100) * 0.1
        client_metadata = [
            {'client_id': i, 'grad_size_kb': np.random.rand() * 50 + 10,
             'compression_ratio': round(np.random.rand() * 30 + 50, 2)}
            for i in range(5)
        ]
        accuracy = 65.0 + r * 5 + np.random.rand() * 3
        
        malicious = [2] if r == 1 else []
        
        result = ledger.record_round(r, model_params, client_metadata, accuracy, malicious)
        
        if result['status'] == 'success':
            print(f'  轮次 {r+1}: 区块#{result["block_index"]} | '
                  f'准确率 {accuracy:.2f}% | '
                  f'检测到恶意节点: {result["consensus"]["detected_malicious"]} | '
                  f'共识通过: {"✓" if result["consensus"]["consensus_reached"] else "✗"}')
        else:
            print(f'  轮次 {r+1}: 共识失败 | 原因: {result["status"]}')
    
    print(f'\n[区块链状态]')
    summary = ledger.get_summary()
    print(f'  链长度: {summary["blockchain"]["length"]} | '
          f'完整有效: {"✓" if summary["blockchain"]["is_valid"] else "✗"} | '
          f'交易总数: {summary["blockchain"]["total_transactions"]}')
    print(f'  最后区块哈希: {summary["blockchain"]["last_block_hash"][:32]}...')
    
    print(f'\n[防篡改演示] 手动修改第1块的模型元数据...')
    if len(ledger.blockchain.chain) > 1:
        original_hash = ledger.blockchain.chain[1].model_hash
        ledger.blockchain.chain[1].model_metadata['accuracy'] = 999.9
        valid, msg = ledger.blockchain.validate_chain()
        print(f'  验证结果: {"完整" if valid else "被检测到篡改"} | 消息: {msg}')
        ledger.blockchain.chain[1].model_metadata['accuracy'] = result.get('accuracy', 0)


if __name__ == '__main__':
    blockchain_demo()
