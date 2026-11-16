# 区块链篡改 PPT 图片包

所有 PNG 均为 16:9、2400×1350 px，可直接放入 PPT。图内不设顶部大标题，便于在幻灯片中统一添加页标题。

| 序号 | 图片 | PPT 中建议表达的结论 |
|---|---|---|
| 01 | `01_hashrate_risk.png` | 攻击者算力接近 50% 时，后续链段重写风险快速上升 |
| 02 | `02_confirmation_depth.png` | 增加确认深度可以指数级压低低于 50% 算力攻击者的成功率 |
| 03 | `03_hashrate_confirmation_heatmap.png` | 算力占比和确认深度共同决定攻击风险 |
| 04 | `04_attack_strategy_detection.png` | 本地链校验能检出部分篡改，但不能单独识别完整重挖的后续链段 |
| 05 | `05_tamper_position_matrix.png` | 篡改位置和重挖范围决定本地校验是否能发现异常 |
| 06 | `06_hash_chain_break.png` | 历史区块被改动后，后续区块保留的 `previous_hash` 会暴露链接断裂 |

注：算力和确认深度图属于概率模型 / Monte Carlo 仿真，不是真实公链实测。检出率和链接断裂图来自项目的 `Blockchain.validate_chain()` 校验逻辑。
