#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成独立的区块链篡改实验结果图，不接入 GUI 或业务流程。"""

from __future__ import annotations

import csv
import json
import sys
from copy import deepcopy
from pathlib import Path

import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch


# Nature-style editable text settings. Arial Unicode MS covers Chinese labels.
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "Arial Unicode MS",
    "Arial",
    "DejaVu Sans",
    "Liberation Sans",
]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
# Static QA markers: svg.fonttype='none'; pdf.fonttype=42
plt.rcParams["font.size"] = 7.5
plt.rcParams["axes.labelsize"] = 8
plt.rcParams["axes.titlesize"] = 9
plt.rcParams["legend.fontsize"] = 7
plt.rcParams["xtick.labelsize"] = 7
plt.rcParams["ytick.labelsize"] = 7
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["legend.frameon"] = False


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
FIGURE_DIR = SCRIPT_DIR / "figures"
DATA_DIR = SCRIPT_DIR / "source_data"
MM = 1 / 25.4

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.blockchain_consensus import Blockchain  # noqa: E402


BLUE = "#0F4D92"
BLUE_LIGHT = "#6EA6D7"
ORANGE = "#D9792B"
ORANGE_LIGHT = "#F1B97A"
TEAL = "#2A8C82"
INK = "#272727"
MID = "#6B7280"
GRID = "#DDE4EC"
PALE = "#F5F7FA"


def apply_axis_style(ax: plt.Axes) -> None:
    ax.grid(axis="y", color=GRID, linewidth=0.65, alpha=0.8)
    ax.tick_params(length=3, width=0.7, colors=MID)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)
    ax.title.set_color(INK)


def add_panel_label(ax: plt.Axes, label: str) -> None:
    ax.text(
        -0.08,
        1.04,
        label,
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        ha="left",
        va="bottom",
        color=INK,
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE_DIR / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(FIGURE_DIR / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(FIGURE_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    fig.savefig(
        FIGURE_DIR / f"{stem}.tiff",
        dpi=600,
        bbox_inches="tight",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)


def catchup_probability(attacker_share: float, confirmations: int) -> float:
    """Nakamoto-style eventual catch-up probability for a z-block deficit."""
    q = float(attacker_share)
    if not 0 <= q <= 1:
        raise ValueError("attacker_share must be in [0, 1]")
    if confirmations < 1:
        raise ValueError("confirmations must be >= 1")
    if q >= 0.5:
        return 1.0
    return (q / (1.0 - q)) ** confirmations


def wilson_interval(successes: int, trials: int, z_value: float = 1.95996398454) -> tuple[float, float]:
    if trials <= 0:
        raise ValueError("trials must be positive")
    p_hat = successes / trials
    denominator = 1.0 + z_value**2 / trials
    center = (p_hat + z_value**2 / (2.0 * trials)) / denominator
    margin = (
        z_value
        * np.sqrt(p_hat * (1.0 - p_hat) / trials + z_value**2 / (4.0 * trials**2))
        / denominator
    )
    return max(0.0, center - margin), min(1.0, center + margin)


def build_hashrate_scan(seed: int = 20260811, trials: int = 10_000) -> list[dict]:
    rng = np.random.default_rng(seed)
    attacker_shares = np.arange(0.05, 0.601, 0.05)
    confirmation_options = np.arange(1, 6)
    rows: list[dict] = []

    for share in attacker_shares:
        confirmations = rng.choice(confirmation_options, size=trials, replace=True)
        probabilities = np.array(
            [catchup_probability(float(share), int(depth)) for depth in confirmations]
        )
        successes = int(np.sum(rng.random(trials) < probabilities))
        simulated_rate = successes / trials
        ci_low, ci_high = wilson_interval(successes, trials)
        theoretical_rate = float(
            np.mean([catchup_probability(float(share), int(depth)) for depth in confirmation_options])
        )
        rows.append(
            {
                "attacker_hashrate_share": round(float(share), 4),
                "trials": trials,
                "tamper_position_rule": "uniform over 5 non-genesis blocks",
                "confirmation_range": "1-5",
                "theoretical_success_rate": theoretical_rate,
                "simulated_success_rate": simulated_rate,
                "success_ci95_low": ci_low,
                "success_ci95_high": ci_high,
                "simulated_protection_rate": 1.0 - simulated_rate,
                "protection_ci95_low": 1.0 - ci_high,
                "protection_ci95_high": 1.0 - ci_low,
            }
        )
    return rows


def build_deterministic_chain(n_data_blocks: int = 5, difficulty: int = 2) -> Blockchain:
    chain = Blockchain(difficulty=difficulty)
    genesis = chain.chain[0]
    genesis.timestamp = 1_700_000_000.0
    genesis.nonce = 0
    genesis.nonce = chain._proof_of_work(genesis)

    for block_index in range(1, n_data_blocks + 1):
        params = np.linspace(-1.0, 1.0, 24) + block_index / 10.0
        block = chain.mine_block(
            params,
            {
                "round": block_index,
                "accuracy": round(70.0 + 2.5 * block_index, 1),
            },
        )
        block.timestamp = 1_700_000_000.0 + block_index * 60.0
        block.previous_hash = chain.chain[block_index - 1].hash()
        block.nonce = 0
        block.nonce = chain._proof_of_work(block)

    valid, message = chain.validate_chain()
    if not valid:
        raise RuntimeError(f"deterministic chain construction failed: {message}")
    return chain


def mutate_block(chain: Blockchain, block_index: int) -> None:
    chain.chain[block_index].model_metadata["accuracy"] = 999.9
    chain.chain[block_index].model_metadata["tampered"] = True


def remine_block(chain: Blockchain, block_index: int) -> None:
    block = chain.chain[block_index]
    block.nonce = 0
    block.nonce = chain._proof_of_work(block)


def build_position_scan() -> tuple[list[dict], dict]:
    base_chain = build_deterministic_chain()
    last_index = len(base_chain.chain) - 1
    rows: list[dict] = []
    strategies = [
        ("data_edit_only", "仅修改数据"),
        ("remine_one_block", "重挖被改区块"),
        ("remine_suffix", "重挖后续整段"),
    ]

    for block_index in range(1, last_index + 1):
        for strategy_id, strategy_label in strategies:
            attacked = deepcopy(base_chain)
            mutate_block(attacked, block_index)

            if strategy_id == "remine_one_block":
                remine_block(attacked, block_index)
            elif strategy_id == "remine_suffix":
                for suffix_index in range(block_index, last_index + 1):
                    if suffix_index > block_index:
                        attacked.chain[suffix_index].previous_hash = attacked.chain[suffix_index - 1].hash()
                    remine_block(attacked, suffix_index)

            valid, message = attacked.validate_chain()
            rows.append(
                {
                    "tampered_block": block_index,
                    "confirmations_to_tip": last_index - block_index + 1,
                    "strategy_id": strategy_id,
                    "strategy": strategy_label,
                    "detected_by_local_validation": not valid,
                    "validation_message": message,
                }
            )

    evidence_index = 3
    before = deepcopy(base_chain)
    after = deepcopy(base_chain)
    old_hash = before.chain[evidence_index].hash()
    next_stored_hash = before.chain[evidence_index + 1].previous_hash
    mutate_block(after, evidence_index)
    remine_block(after, evidence_index)
    new_hash = after.chain[evidence_index].hash()
    next_stored_after = after.chain[evidence_index + 1].previous_hash
    valid_after, message_after = after.validate_chain()

    evidence = {
        "tampered_block": evidence_index,
        "next_block": evidence_index + 1,
        "old_hash": old_hash,
        "new_hash_after_tamper_and_remine": new_hash,
        "next_block_stored_previous_hash": next_stored_after,
        "link_matched_before": next_stored_hash == old_hash,
        "link_matched_after": next_stored_after == new_hash,
        "detected": not valid_after,
        "validation_message": message_after,
        "chain_hashes_before": [block.hash() for block in before.chain[1:]],
        "chain_hashes_after": [block.hash() for block in after.chain[1:]],
    }
    return rows, evidence


def write_source_data(hashrate_rows: list[dict], position_rows: list[dict], evidence: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with (DATA_DIR / "hashrate_scan.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(hashrate_rows[0].keys()))
        writer.writeheader()
        writer.writerows(hashrate_rows)

    with (DATA_DIR / "position_detection.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(position_rows[0].keys()))
        writer.writeheader()
        writer.writerows(position_rows)

    evidence_rows = [
        {
            "link": f"B{evidence['tampered_block']} -> B{evidence['next_block']}",
            "state": "before",
            "stored_previous_hash": evidence["old_hash"],
            "recomputed_previous_hash": evidence["old_hash"],
            "matched": evidence["link_matched_before"],
        },
        {
            "link": f"B{evidence['tampered_block']} -> B{evidence['next_block']}",
            "state": "after_tamper_and_remine_one_block",
            "stored_previous_hash": evidence["next_block_stored_previous_hash"],
            "recomputed_previous_hash": evidence["new_hash_after_tamper_and_remine"],
            "matched": evidence["link_matched_after"],
        },
    ]
    with (DATA_DIR / "hash_link_evidence.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(evidence_rows[0].keys()))
        writer.writeheader()
        writer.writerows(evidence_rows)

    metadata = {
        "figure_contract": {
            "core_conclusion": (
                "本地 PoW+哈希链校验可以检出直接篡改和不完整重挖；"
                "完整重挖后续链段时，攻击风险由攻击者算力与确认深度决定。"
            ),
            "archetype": "quantitative grid with hash-link evidence",
            "target_output": "standalone report/论文附件",
            "backend": "Python/matplotlib",
            "final_size": "183 mm composite; 150-183 mm standalone panels",
            "panel_map": {
                "a": "算力占比与后续重挖成功率",
                "b": "不同篡改位置和攻击策略的本地检出矩阵",
                "c": "真实哈希摘要展示链接断裂证据",
            },
            "hero_evidence": "Monte Carlo scan with theoretical curve and Wilson 95% CI",
            "validation_evidence": "project Blockchain.validate_chain() on 5 non-genesis blocks",
        },
        "statistics": {
            "seed": 20260811,
            "trials_per_hashrate": 10000,
            "tamper_position_sampling": "uniform across 5 non-genesis blocks",
            "center": "Monte Carlo proportion",
            "interval": "two-sided Wilson 95% confidence interval",
            "catchup_model": "P=(q/(1-q))^z for q<0.5; P=1 for q>=0.5",
            "hypothesis_test": "none",
        },
        "limitations": [
            "这是攻击者追赶概率仿真，不是真实公链测量。",
            "本地链结构校验无法单独识别已完整重挖的后续链段，还需要外部共识、签名或检查点。",
            "确认深度 z 按篡改位置到链尾的区块数计算。",
        ],
        "hash_link_evidence": evidence,
    }
    (DATA_DIR / "methodology.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def plot_hashrate_panel(
    ax: plt.Axes,
    rows: list[dict],
    with_panel_label: bool = True,
    show_title: bool = True,
    show_legend: bool = True,
) -> None:
    x = np.array([row["attacker_hashrate_share"] for row in rows]) * 100.0
    theory = np.array([row["theoretical_success_rate"] for row in rows]) * 100.0
    success = np.array([row["simulated_success_rate"] for row in rows]) * 100.0
    success_low = np.array([row["success_ci95_low"] for row in rows]) * 100.0
    success_high = np.array([row["success_ci95_high"] for row in rows]) * 100.0
    protection = np.array([row["simulated_protection_rate"] for row in rows]) * 100.0
    protection_low = np.array([row["protection_ci95_low"] for row in rows]) * 100.0
    protection_high = np.array([row["protection_ci95_high"] for row in rows]) * 100.0

    ax.fill_between(x, success_low, success_high, color=ORANGE_LIGHT, alpha=0.35, linewidth=0)
    ax.fill_between(x, protection_low, protection_high, color=BLUE_LIGHT, alpha=0.25, linewidth=0)
    ax.plot(x, theory, color=ORANGE, linewidth=1.5, linestyle="--", label="理论攻击成功率")
    ax.plot(x, success, color=ORANGE, marker="o", markersize=3.5, linewidth=1.2, label="仿真攻击成功率")
    ax.plot(x, protection, color=BLUE, marker="s", markersize=3.2, linewidth=1.4, label="完整性保护率")
    ax.axvspan(50, 61, color=ORANGE_LIGHT, alpha=0.16, linewidth=0)
    ax.axvline(50, color=MID, linestyle=(0, (4, 3)), linewidth=0.9)
    ax.text(50.8, 51, "50% 算力阈值", color=MID, rotation=90, rotation_mode="anchor", va="bottom")
    ax.set_xlim(3, 61)
    ax.set_ylim(-2, 103)
    ax.set_xticks(np.arange(5, 61, 5))
    ax.set_yticks(np.arange(0, 101, 20))
    ax.set_xlabel("攻击者算力占比 q (%)")
    ax.set_ylabel("概率 / 保护率 (%)")
    if show_title:
        ax.set_title("攻击者算力越接近 50%，后续链段重写风险越高", loc="left", fontweight="bold")
    if show_legend:
        ax.legend(loc="upper left", ncol=1)
    apply_axis_style(ax)
    if with_panel_label:
        add_panel_label(ax, "a")


def position_matrix(position_rows: list[dict]) -> tuple[np.ndarray, list[str], list[int]]:
    strategy_order = ["data_edit_only", "remine_one_block", "remine_suffix"]
    strategy_labels = ["仅修改数据", "重挖被改区块", "重挖后续整段"]
    block_order = sorted({int(row["tampered_block"]) for row in position_rows})
    lookup = {
        (row["strategy_id"], int(row["tampered_block"])): int(row["detected_by_local_validation"])
        for row in position_rows
    }
    matrix = np.array([[lookup[(strategy, block)] for block in block_order] for strategy in strategy_order])
    return matrix, strategy_labels, block_order


def plot_position_panel(ax: plt.Axes, rows: list[dict], with_panel_label: bool = True) -> None:
    matrix, strategy_labels, block_order = position_matrix(rows)
    cmap = ListedColormap(["#E9EDF2", BLUE])
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
    ax.set_xticks(np.arange(len(block_order)))
    ax.set_xticklabels([f"B{block}\n({6 - block}次确认)" for block in block_order])
    ax.set_yticks(np.arange(len(strategy_labels)))
    ax.set_yticklabels(strategy_labels)
    ax.set_xlabel("被篡改区块（括号内为到链尾的确认深度）")
    ax.set_title("本地 PoW + 哈希链校验的检出边界", loc="left", fontweight="bold")
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            detected = bool(matrix[row_index, col_index])
            ax.text(
                col_index,
                row_index,
                "✓ 检出" if detected else "— 未检出",
                ha="center",
                va="center",
                color="white" if detected else MID,
                fontsize=7,
                fontweight="bold" if detected else "normal",
            )
    ax.set_xticks(np.arange(-0.5, len(block_order), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(strategy_labels), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.5)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    if with_panel_label:
        add_panel_label(ax, "b")


def draw_block(ax: plt.Axes, x: float, y: float, label: str, hash_text: str, color: str, edge: str) -> None:
    patch = FancyBboxPatch(
        (x - 0.42, y - 0.30),
        0.84,
        0.60,
        boxstyle="round,pad=0.03,rounding_size=0.06",
        facecolor=color,
        edgecolor=edge,
        linewidth=1.0,
    )
    ax.add_patch(patch)
    ax.text(x, y + 0.08, label, ha="center", va="center", fontsize=8, fontweight="bold", color=INK)
    ax.text(x, y - 0.10, hash_text, ha="center", va="center", fontsize=6.2, color=MID, family="monospace")


def plot_hash_evidence_panel(ax: plt.Axes, evidence: dict, with_panel_label: bool = True) -> None:
    old_prefix = evidence["old_hash"][:10]
    new_prefix = evidence["new_hash_after_tamper_and_remine"][:10]
    stored_prefix = evidence["next_block_stored_previous_hash"][:10]

    ax.set_xlim(-0.2, 6.2)
    ax.set_ylim(-0.15, 2.4)
    ax.axis("off")
    ax.set_title("篡改并仅重挖单个区块后，下一区块仍保留旧哈希", loc="left", fontweight="bold", pad=8)

    y_before, y_after = 1.70, 0.65
    x_positions = [0.55, 1.75, 2.95, 4.15, 5.35]
    ax.text(-0.05, y_before, "篡改前", ha="right", va="center", color=INK, fontweight="bold")
    ax.text(-0.05, y_after, "篡改后", ha="right", va="center", color=INK, fontweight="bold")

    for index, x_value in enumerate(x_positions, start=1):
        before_hash = evidence["chain_hashes_before"][index - 1][:10]
        draw_block(ax, x_value, y_before, f"B{index}", before_hash, "#EAF2FA", BLUE_LIGHT)
        if index < len(x_positions):
            ax.annotate("", xy=(x_positions[index] - 0.46, y_before), xytext=(x_value + 0.46, y_before), arrowprops={"arrowstyle": "->", "color": TEAL, "lw": 1.2})

    for index, x_value in enumerate(x_positions, start=1):
        if index == evidence["tampered_block"]:
            draw_block(ax, x_value, y_after, f"B{index} 已篡改", new_prefix, "#FFF0E2", ORANGE)
        else:
            after_hash = evidence["chain_hashes_after"][index - 1][:10]
            draw_block(ax, x_value, y_after, f"B{index}", after_hash, "#F2F4F7", "#AAB2BD")

        if index < len(x_positions):
            if index == evidence["tampered_block"]:
                midpoint = (x_value + x_positions[index]) / 2
                ax.plot([x_value + 0.46, midpoint - 0.08], [y_after, y_after], color=ORANGE, linewidth=1.5)
                ax.plot([midpoint + 0.08, x_positions[index] - 0.46], [y_after, y_after], color=ORANGE, linewidth=1.5)
                ax.text(midpoint, y_after, "×", ha="center", va="center", color=ORANGE, fontsize=13, fontweight="bold")
            else:
                ax.annotate("", xy=(x_positions[index] - 0.46, y_after), xytext=(x_value + 0.46, y_after), arrowprops={"arrowstyle": "->", "color": "#AAB2BD", "lw": 1.0})

    ax.text(4.12, 0.21, f"B4.previous_hash = {stored_prefix}…", ha="center", va="center", fontsize=6.5, color=ORANGE)
    ax.text(
        4.12,
        0.02,
        f"B3.current_hash = {new_prefix}…  →  不一致，检出链接断裂",
        ha="center",
        va="center",
        fontsize=6.5,
        color=ORANGE,
        fontweight="bold",
    )
    if with_panel_label:
        add_panel_label(ax, "c")


def make_standalone_figures(hashrate_rows: list[dict], position_rows: list[dict], evidence: dict) -> None:
    fig, ax = plt.subplots(figsize=(7.2047, 3.5433))
    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.15, top=0.82)
    plot_hashrate_panel(
        ax,
        hashrate_rows,
        with_panel_label=False,
        show_title=False,
        show_legend=False,
    )
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(0.105, 0.975),
        ncol=3,
        frameon=False,
        handlelength=2.8,
        columnspacing=1.8,
        borderaxespad=0,
    )
    save_figure(fig, "blockchain_hashrate_risk")

    fig, ax = plt.subplots(figsize=(7.2047, 3.0709), constrained_layout=True)
    plot_position_panel(ax, position_rows, with_panel_label=False)
    save_figure(fig, "blockchain_position_detection")

    fig, ax = plt.subplots(figsize=(7.2047, 3.5433), constrained_layout=True)
    plot_hash_evidence_panel(ax, evidence, with_panel_label=False)
    save_figure(fig, "blockchain_hash_break_evidence")


def make_composite_figure(hashrate_rows: list[dict], position_rows: list[dict], evidence: dict) -> None:
    fig = plt.figure(figsize=(7.2047, 6.1024), constrained_layout=True)
    grid = fig.add_gridspec(2, 2, height_ratios=[1.05, 0.82], width_ratios=[1.12, 0.88])
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, :])
    plot_hashrate_panel(ax_a, hashrate_rows)
    plot_position_panel(ax_b, position_rows)
    plot_hash_evidence_panel(ax_c, evidence)
    fig.suptitle(
        "区块链篡改防护：结构检出、攻击边界与哈希证据",
        x=0.01,
        ha="left",
        fontsize=11,
        fontweight="bold",
        color=INK,
    )
    save_figure(fig, "blockchain_tampering_overview")


def main() -> None:
    hashrate_rows = build_hashrate_scan()
    position_rows, evidence = build_position_scan()
    write_source_data(hashrate_rows, position_rows, evidence)
    make_standalone_figures(hashrate_rows, position_rows, evidence)
    make_composite_figure(hashrate_rows, position_rows, evidence)
    print(f"Generated 4 figure sets in: {FIGURE_DIR}")
    print(f"Source data written to: {DATA_DIR}")


if __name__ == "__main__":
    main()
