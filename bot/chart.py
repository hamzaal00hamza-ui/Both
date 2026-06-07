"""
رسم بياني للأرباح اليومية باستخدام matplotlib.
ينتج صورة PNG في الذاكرة (BytesIO) جاهزة لإرسالها عبر تلغرام.
"""
import io
import logging
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from . import database as db

logger = logging.getLogger(__name__)


def _fmt_syp(value: float, _pos=None) -> str:
    """يُنسّق المبالغ بالليرة لمحاور الرسم."""
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def build_profit_chart_png(days: int = 30) -> Optional[bytes]:
    """ينشئ رسم بياني للأرباح اليومية ويرجع بايتات PNG.
    يرجع None لو في خطأ."""
    try:
        series = db.get_daily_profit_series(days=days)
    except Exception as e:
        logger.warning("get_daily_profit_series failed: %s", e)
        return None

    labels = series["labels"]
    revenue = series["revenue"]
    cost = series["cost_syp"]
    profit = series["profit"]

    total_revenue = sum(revenue)
    total_cost = sum(cost)
    total_profit = sum(profit)
    margin = (total_profit / total_revenue * 100.0) if total_revenue > 0 else 0.0

    # ===== إعداد الرسم =====
    plt.style.use("dark_background")
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(12, 8), gridspec_kw={"height_ratios": [3, 2]}
    )
    fig.patch.set_facecolor("#1a1a2e")

    x = list(range(len(labels)))

    # ===== الرسم العلوي: مبيعات vs تكلفة (أعمدة) =====
    bar_width = 0.4
    ax1.bar(
        [i - bar_width / 2 for i in x],
        revenue,
        width=bar_width,
        label="Revenue",
        color="#4ade80",
        alpha=0.9,
    )
    ax1.bar(
        [i + bar_width / 2 for i in x],
        cost,
        width=bar_width,
        label="Cost",
        color="#f87171",
        alpha=0.9,
    )
    ax1.set_facecolor("#16213e")
    ax1.set_title(
        f"Revenue vs Cost - Last {days} Days\n"
        f"Total Revenue: {total_revenue:,.0f} SYP   "
        f"Net Profit: {total_profit:,.0f} SYP   "
        f"Margin: {margin:.1f}%",
        fontsize=13,
        color="white",
        pad=15,
    )
    ax1.set_ylabel("Amount (SYP)", color="#cbd5e1", fontsize=10)
    ax1.yaxis.set_major_formatter(FuncFormatter(_fmt_syp))
    ax1.legend(loc="upper left", facecolor="#0f3460", edgecolor="none", labelcolor="white")
    ax1.grid(True, alpha=0.15, linestyle="--")
    ax1.tick_params(colors="#cbd5e1")
    for spine in ax1.spines.values():
        spine.set_color("#475569")

    # ===== الرسم السفلي: الربح اليومي (خط + تعبئة) =====
    ax2.fill_between(x, profit, alpha=0.3, color="#fbbf24")
    ax2.plot(
        x,
        profit,
        marker="o",
        markersize=5,
        linewidth=2,
        color="#fbbf24",
        label="Daily Profit",
    )
    ax2.axhline(0, color="#64748b", linestyle="-", linewidth=0.8, alpha=0.6)
    ax2.set_facecolor("#16213e")
    ax2.set_title("Daily Net Profit", fontsize=11, color="white", pad=10)
    ax2.set_xlabel("Date", color="#cbd5e1", fontsize=10)
    ax2.set_ylabel("Profit (SYP)", color="#cbd5e1", fontsize=10)
    ax2.yaxis.set_major_formatter(FuncFormatter(_fmt_syp))
    ax2.grid(True, alpha=0.15, linestyle="--")
    ax2.tick_params(colors="#cbd5e1")
    for spine in ax2.spines.values():
        spine.set_color("#475569")

    # ===== ضبط محور x (التواريخ) =====
    step = max(1, len(labels) // 12)
    tick_positions = list(range(0, len(labels), step))
    tick_labels = [labels[i] for i in tick_positions]
    for ax in (ax1, ax2):
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha="right", color="#cbd5e1", fontsize=9)
        ax.set_xlim(-0.5, len(labels) - 0.5)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
