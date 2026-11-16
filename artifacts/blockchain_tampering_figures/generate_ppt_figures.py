#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成适合 16:9 PPT 的区块链篡改独立图片。"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
OUTPUT_DIR = SCRIPT_DIR / "ppt_figures"
SOURCE_DIR = SCRIPT_DIR / "ppt_source_data"
sys.path.insert(0, str(SCRIPT_DIR))

import generate_figures as base  # noqa: E402


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
plt.rcParams["font.size"] = 16
plt.rcParams["axes.labelsize"] = 18
plt.rcParams["axes.titlesize"] = 20
plt.rcParams["legend.fontsize"] = 15
plt.rcParams["xtick.labelsize"] = 15
plt.rcParams["ytick.labelsize"] = 15
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.linewidth"] = 1.2
plt.rcParams["legend.frameon"] = False


BLUE = "#0F4D92"
BLUE_MID = "#3775BA"
BLUE_LIGHT = "#88B7DF"
ORANGE = "#D9792B"
ORANGE_LIGHT = "#F3C99E"
TEAL = "#2A8C82"
INK = "#272727"
MID = "#6B7280"
GRID = "#DDE4EC"
PALE = "#F3F6F9"
SLIDE_SIZE = (8.0, 4.5)  # 16:9; 300 dpi -> 2400 x 1350 px


def style_axis(ax: plt.Axes, grid_axis: str = "y") -> None:
    ax.grid(axis=grid_axis, color=GRID, linewidth=1.0, alpha=0.9)
    ax.set_axisbelow(True)
    ax.tick_params(length=5, width=1.0, colors=MID)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)


def save_slide(fig: plt.Figure, stem: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_DIR / f"{stem}.png", dpi=300, facecolor="white")
    fig.savefig(OUTPUT_DIR / f"{stem}.svg", facecolor="white")
    fig.savefig(OUTPUT_DIR / f"{stem}.pdf", facecolor="white")
    plt.close(fig)


def figure_hashrate_risk(rows: list[dict]) -> None:
    x = np.array([row["attacker_hashrate_share"] for row in rows]) * 100
    theory = np.array([row["theoretical_success_rate"] for row in rows]) * 100
    success = np.array([row["simulated_success_rate"] for row in rows]) * 100
    success_low = np.array([row["success_ci95_low"] for row in rows]) * 100
    success_high = np.array([row["success_ci95_high"] for row in rows]) * 100
    protection = np.array([row["simulated_protection_rate"] for row in rows]) * 100
    protection_low = np.array([row["protection_ci95_low"] for row in rows]) * 100
    protection_high = np.array([row["protection_ci95_high"] for row in rows]) * 100

    fig, ax = plt.subplots(figsize=SLIDE_SIZE)
    fig.subplots_adjust(left=0.105, right=0.975, bottom=0.17, top=0.78)
    ax.fill_between(x, success_low, success_high, color=ORANGE_LIGHT, alpha=0.40, linewidth=0)
    ax.fill_between(x, protection_low, protection_high, color=BLUE_LIGHT, alpha=0.25, linewidth=0)
    line_theory, = ax.plot(
        x,
        theory,
        color=MID,
        linewidth=2.2,
        linestyle="--",
        label="理论重写概率",
        zorder=2,
    )
    line_success, = ax.plot(
        x,
        success,
        color=ORANGE,
        marker="o",
        markersize=7,
        linewidth=2.2,
        label="Monte Carlo 仿真",
        zorder=3,
    )
    line_protection, = ax.plot(
        x,
        protection,
        color=BLUE,
        marker="s",
        markersize=6.5,
        linewidth=2.5,
        label="完整性保护率",
        zorder=3,
    )
    ax.axvspan(50, 61, color=ORANGE_LIGHT, alpha=0.22, linewidth=0)
    ax.axvline(50, color=MID, linestyle=(0, (4, 3)), linewidth=1.5)
    ax.text(50.8, 48, "50% 算力阈值", color=MID, rotation=90, rotation_mode="anchor", va="bottom", fontsize=14)
    ax.set_xlim(3, 61)
    ax.set_ylim(-2, 103)
    ax.set_xticks(np.arange(5, 61, 5))
    ax.set_yticks(np.arange(0, 101, 20))
    ax.set_xlabel("攻击者算力占比 q (%)")
    ax.set_ylabel("概率 / 保护率 (%)")
    style_axis(ax)
    fig.legend(
        [line_success, line_protection],
        ["Monte Carlo 仿真", "完整性保护率"],
        loc="upper center",
        bbox_to_anchor=(0.54, 0.96),
        ncol=2,
        handlelength=2.6,
        columnspacing=2.6,
    )
    save_slide(fig, "01_hashrate_risk")


def figure_confirmation_depth() -> None:
    confirmations = np.arange(1, 11)
    shares = [0.10, 0.20, 0.30, 0.40, 0.45]
    colors = ["#B8D5EC", "#88B7DF", "#568FCA", BLUE, ORANGE]

    fig, ax = plt.subplots(figsize=SLIDE_SIZE)
    fig.subplots_adjust(left=0.105, right=0.975, bottom=0.17, top=0.78)
    handles = []
    labels = []
    for share, color in zip(shares, colors):
        risks = np.array([base.catchup_probability(share, int(depth)) for depth in confirmations]) * 100
        line, = ax.plot(confirmations, risks, marker="o", markersize=6.5, linewidth=2.4, color=color)
        handles.append(line)
        labels.append(f"q={share * 100:.0f}%")

    ax.set_xlim(0.7, 10.3)
    ax.set_ylim(-2, 86)
    ax.set_xticks(confirmations)
    ax.set_yticks(np.arange(0, 81, 20))
    ax.set_xlabel("确认深度 z（需重挖的区块数）")
    ax.set_ylabel("后续链段重写成功率 (%)")
    style_axis(ax)
    fig.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.53, 0.96),
        ncol=5,
        handlelength=1.8,
        columnspacing=1.0,
        fontsize=13,
    )
    save_slide(fig, "02_confirmation_depth")


def figure_risk_heatmap() -> None:
    shares = np.array([0.10, 0.20, 0.30, 0.40, 0.45, 0.50])
    confirmations = np.arange(1, 11)
    matrix = np.array(
        [[base.catchup_probability(float(share), int(depth)) * 100 for depth in confirmations] for share in shares]
    )
    cmap = LinearSegmentedColormap.from_list("tamper_risk", ["#F7FAFC", "#F4D5B7", ORANGE, "#8F2D1F"])

    fig, ax = plt.subplots(figsize=SLIDE_SIZE)
    fig.subplots_adjust(left=0.11, right=0.91, bottom=0.18, top=0.94)
    image = ax.imshow(matrix, cmap=cmap, vmin=0, vmax=100, aspect="auto", interpolation="nearest")
    ax.set_xticks(np.arange(len(confirmations)))
    ax.set_xticklabels(confirmations)
    ax.set_yticks(np.arange(len(shares)))
    ax.set_yticklabels([f"{share * 100:.0f}%" for share in shares])
    ax.set_xlabel("确认深度 z", fontsize=14, labelpad=7)
    ax.set_ylabel("攻击者算力占比 q", fontsize=13, labelpad=7)
    ax.tick_params(axis="both", which="major", labelsize=12)
    ax.set_xticks(np.arange(-0.5, len(confirmations), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(shares), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1.2)
    ax.tick_params(which="minor", bottom=False, left=False)
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            value = matrix[row_index, col_index]
            ax.text(
                col_index,
                row_index,
                f"{value:.0f}",
                ha="center",
                va="center",
                fontsize=10,
                color="white" if value >= 48 else INK,
                fontweight="bold" if value >= 75 else "normal",
            )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.035, pad=0.025)
    colorbar.set_label("攻击成功率 (%)", fontsize=13, labelpad=8)
    colorbar.ax.tick_params(labelsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    save_slide(fig, "03_hashrate_confirmation_heatmap")


def figure_strategy_detection(position_rows: list[dict]) -> None:
    strategy_ids = ["data_edit_only", "remine_one_block", "remine_suffix"]
    labels = ["仅修改数据", "重挖被改区块", "重挖后续整段"]
    values = []
    counts = []
    for strategy_id in strategy_ids:
        selected = [row for row in position_rows if row["strategy_id"] == strategy_id]
        detected = sum(bool(row["detected_by_local_validation"]) for row in selected)
        counts.append((detected, len(selected)))
        values.append(detected / len(selected) * 100)

    fig, ax = plt.subplots(figsize=SLIDE_SIZE)
    fig.subplots_adjust(left=0.23, right=0.95, bottom=0.22, top=0.92)
    y = np.arange(len(labels))
    bars = ax.barh(y, values, height=0.58, color=[BLUE, TEAL, ORANGE_LIGHT], edgecolor="none")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 108)
    ax.set_xticks(np.arange(0, 101, 20))
    ax.set_xlabel("本地链结构校验检出率 (%)")
    style_axis(ax, grid_axis="x")
    for bar, value, (detected, total) in zip(bars, values, counts):
        label_inside = value >= 95
        ax.text(
            value - 2.0 if label_inside else value + 2.0,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.0f}%  ({detected}/{total})",
            va="center",
            ha="right" if label_inside else "left",
            fontsize=16,
            fontweight="bold",
            color="white" if label_inside else INK,
        )
    ax.text(0.01, 0.025, "n=5 个篡改位置", transform=ax.transAxes, fontsize=13, color=MID, ha="left")
    save_slide(fig, "04_attack_strategy_detection")


def figure_position_matrix(position_rows: list[dict]) -> None:
    matrix, strategy_labels, block_order = base.position_matrix(position_rows)
    cmap = ListedColormap(["#E9EDF2", BLUE])

    fig, ax = plt.subplots(figsize=SLIDE_SIZE)
    fig.subplots_adjust(left=0.23, right=0.97, bottom=0.27, top=0.86)
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=1, aspect="auto", interpolation="nearest")
    ax.set_xticks(np.arange(len(block_order)))
    ax.set_xticklabels([f"B{block}\n({6 - block}次确认)" for block in block_order])
    ax.set_yticks(np.arange(len(strategy_labels)))
    ax.set_yticklabels(strategy_labels)
    ax.set_xlabel("被篡改区块（括号内为到链尾的确认深度）")
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            detected = bool(matrix[row_index, col_index])
            ax.text(
                col_index,
                row_index,
                "✓ 检出" if detected else "— 未检出",
                ha="center",
                va="center",
                fontsize=15,
                fontweight="bold" if detected else "normal",
                color="white" if detected else MID,
            )
    ax.set_xticks(np.arange(-0.5, len(block_order), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(strategy_labels), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.legend(
        handles=[Patch(facecolor=BLUE, label="检出"), Patch(facecolor="#E9EDF2", edgecolor="#C9D1DA", label="未检出")],
        loc="upper center",
        bbox_to_anchor=(0.57, 0.97),
        ncol=2,
        handlelength=1.4,
    )
    save_slide(fig, "05_tamper_position_matrix")


def draw_block(ax: plt.Axes, x: float, y: float, label: str, hash_text: str, face: str, edge: str) -> None:
    width, height = 1.42, 0.72
    patch = FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width,
        height,
        boxstyle="round,pad=0.03,rounding_size=0.08",
        facecolor=face,
        edgecolor=edge,
        linewidth=2.0,
    )
    ax.add_patch(patch)
    ax.text(x, y + 0.12, label, ha="center", va="center", fontsize=17, fontweight="bold", color=INK)
    ax.text(x, y - 0.15, hash_text, ha="center", va="center", fontsize=13, color=MID, family="monospace")


def figure_hash_break(evidence: dict) -> None:
    fig, ax = plt.subplots(figsize=SLIDE_SIZE)
    fig.subplots_adjust(left=0.03, right=0.985, bottom=0.06, top=0.96)
    ax.set_xlim(-0.90, 9.75)
    ax.set_ylim(-0.15, 4.35)
    ax.axis("off")

    x_positions = [0.85, 2.75, 4.65, 6.55, 8.45]
    y_before, y_after = 3.25, 1.45
    ax.text(-0.78, y_before, "篡改前", ha="left", va="center", fontsize=18, fontweight="bold", color=INK)
    ax.text(-0.78, y_after, "篡改后", ha="left", va="center", fontsize=18, fontweight="bold", color=INK)

    for index, x_value in enumerate(x_positions, start=1):
        before_hash = evidence["chain_hashes_before"][index - 1][:10]
        draw_block(ax, x_value, y_before, f"B{index}", before_hash, "#EAF2FA", BLUE_LIGHT)
        if index < len(x_positions):
            ax.annotate(
                "",
                xy=(x_positions[index] - 0.77, y_before),
                xytext=(x_value + 0.77, y_before),
                arrowprops={"arrowstyle": "->", "color": TEAL, "lw": 2.2},
            )

    for index, x_value in enumerate(x_positions, start=1):
        after_hash = evidence["chain_hashes_after"][index - 1][:10]
        if index == evidence["tampered_block"]:
            draw_block(ax, x_value, y_after, f"B{index} 已篡改", after_hash, "#FFF0E2", ORANGE)
        else:
            draw_block(ax, x_value, y_after, f"B{index}", after_hash, PALE, "#AAB2BD")

        if index < len(x_positions):
            if index == evidence["tampered_block"]:
                midpoint = (x_value + x_positions[index]) / 2
                ax.plot([x_value + 0.77, midpoint - 0.14], [y_after, y_after], color=ORANGE, linewidth=2.6)
                ax.plot([midpoint + 0.14, x_positions[index] - 0.77], [y_after, y_after], color=ORANGE, linewidth=2.6)
                ax.text(midpoint, y_after, "×", ha="center", va="center", color=ORANGE, fontsize=26, fontweight="bold")
            else:
                ax.annotate(
                    "",
                    xy=(x_positions[index] - 0.77, y_after),
                    xytext=(x_value + 0.77, y_after),
                    arrowprops={"arrowstyle": "->", "color": "#AAB2BD", "lw": 2.0},
                )

    stored_prefix = evidence["next_block_stored_previous_hash"][:10]
    new_prefix = evidence["new_hash_after_tamper_and_remine"][:10]
    ax.text(5.60, 0.60, f"B4.previous_hash = {stored_prefix}…", ha="center", va="center", fontsize=14, color=ORANGE)
    ax.text(
        5.60,
        0.20,
        f"B3.current_hash = {new_prefix}…  →  不一致，检出链接断裂",
        ha="center",
        va="center",
        fontsize=14,
        color=ORANGE,
        fontweight="bold",
    )
    save_slide(fig, "06_hash_chain_break")


def write_source_data(position_rows: list[dict]) -> None:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    confirmations = np.arange(1, 11)
    shares = [0.10, 0.20, 0.30, 0.40, 0.45, 0.50]
    with (SOURCE_DIR / "confirmation_risk_grid.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["attacker_hashrate_share", "confirmations", "attack_success_rate"],
        )
        writer.writeheader()
        for share in shares:
            for depth in confirmations:
                writer.writerow(
                    {
                        "attacker_hashrate_share": share,
                        "confirmations": int(depth),
                        "attack_success_rate": base.catchup_probability(share, int(depth)),
                    }
                )
    with (SOURCE_DIR / "strategy_detection_summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["strategy_id", "detected_positions", "total_positions", "detection_rate"],
        )
        writer.writeheader()
        for strategy_id in ["data_edit_only", "remine_one_block", "remine_suffix"]:
            selected = [row for row in position_rows if row["strategy_id"] == strategy_id]
            detected = sum(bool(row["detected_by_local_validation"]) for row in selected)
            writer.writerow(
                {
                    "strategy_id": strategy_id,
                    "detected_positions": detected,
                    "total_positions": len(selected),
                    "detection_rate": detected / len(selected),
                }
            )


def main() -> None:
    hashrate_rows = base.build_hashrate_scan(seed=20260811, trials=10_000)
    position_rows, evidence = base.build_position_scan()
    write_source_data(position_rows)
    figure_hashrate_risk(hashrate_rows)
    figure_confirmation_depth()
    figure_risk_heatmap()
    figure_strategy_detection(position_rows)
    figure_position_matrix(position_rows)
    figure_hash_break(evidence)
    print(f"Generated 6 PPT figures in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
