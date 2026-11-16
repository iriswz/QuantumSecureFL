# 区块链篡改结果图（独立附件）

本目录不与程序 GUI 或业务流程集成，仅用于报告、论文和答辩演示。

## 结果图

1. `blockchain_hashrate_risk`：攻击者算力占比与后续链段重写成功率。
2. `blockchain_position_detection`：不同篡改位置、不同重挖策略下的本地校验检出矩阵。
3. `blockchain_hash_break_evidence`：用真实 SHA-256 摘要展示 `previous_hash` 与重算哈希不一致。
4. `blockchain_tampering_overview`：三个证据面板的综合版。

每张图同时导出 SVG、PDF、300 dpi PNG 和 600 dpi LZW-TIFF。SVG 中的文字保持可编辑。

## 实验定义

- 算力扫描：每个算力点 10,000 次 Monte Carlo 试验，篡改位置在 5 个非创世区块中均匀采样。
- 攻击概率：当 `q < 0.5` 时使用 `P = (q / (1 - q))^z`；当 `q >= 0.5` 时设为 1。
- 不确定性：仿真比例展示双侧 Wilson 95% 置信区间。
- 位置扫描：直接调用项目 `Blockchain.validate_chain()` 校验 PoW 和前后哈希链接。

## 必须保留的边界说明

本地链结构校验可以稳定检出直接篡改和只重挖一个历史区块的攻击；如果攻击者能从篡改点开始完整重挖后续链段，仅靠本地哈希链无法判断哪条历史才是真实历史。实际系统还需要外部共识、多方签名或不可回滚检查点。

## 复现

```bash
python artifacts/blockchain_tampering_figures/generate_figures.py
```

源数据位于 `source_data/`，其中 `methodology.json` 记录了统计口径、图形契约和限制条件。
