"""
test_calculate_metrics.py — calculate_metrics 函数的单元测试

测试覆盖：
- 5 个核心指标的正确性
- 2 个边界场景（第一个信号是死叉、未来函数偏差防御）

运行方式：
    项目根目录下 → pytest
    或者：
    pytest tests/test_calculate_metrics.py
"""

import sys
import os
import pandas as pd

# 让测试代码能 import 主代码（把项目根目录加入 sys.path）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_stock_daily_data
from signals import calculate_ma_cross
from backtest import run_backtest, calculate_metrics


# ========== fixture：所有测试共享一份数据 ==========
def _build_test_df():
    """
    构建测试用 DataFrame（基于真实平安银行数据）。
    所有测试共享这份数据，避免重复加载。
    """
    df = load_stock_daily_data("000001")
    df = calculate_ma_cross(df)
    df = run_backtest(df)
    return df


# ========== 第 1 个测试 —— 开机检查 ==========
def test_smoke_calculate_metrics_runs():
    """烟雾测试：calculate_metrics 函数能跑通，返回字典格式"""
    df = _build_test_df()
    metrics = calculate_metrics(df)

    # 验证返回值类型
    assert isinstance(metrics, dict), "calculate_metrics 应该返回 dict"

    # 验证 5 个关键 key 都在
    expected_keys = {
        "total_return",
        "max_drawdown",
        "win_rate",
        "profit_loss_ratio",
        "num_trades",
    }
    actual_keys = set(metrics.keys())
    assert expected_keys.issubset(
        actual_keys
    ), f"缺少必需的 key：{expected_keys - actual_keys}"


# ========================================================
# 辅助函数：构造迷你测试 DataFrame
# ========================================================
def _build_mini_df(closing_prices, positions, dates=None):
    """
    构造一个迷你 DataFrame 用于测试。

    :param closing_prices: 收盘价列表
    :param positions: 持仓状态列表（必须和 closing_prices 等长）
    :param dates: 日期列表（默认连续工作日）
    :return: 已经跑过 run_backtest 的 DataFrame（含 daily_return / equity_curve）
    """
    n = len(closing_prices)
    if dates is None:
        dates = pd.date_range("2026-01-02", periods=n, freq="B")  # B = 工作日

    df = pd.DataFrame(
        {
            "收盘": closing_prices,
            "position": positions,
        },
        index=dates,
    )

    # 手动计算 daily_return 和 equity_curve（模拟 run_backtest 的逻辑）
    commission = 0.00075
    daily_pct_change = df["收盘"].pct_change().fillna(0)
    df["daily_return"] = df["position"].shift(1).fillna(0) * daily_pct_change
    position_change = df["position"].diff().abs().fillna(0)
    df["daily_return"] -= position_change * commission
    df["equity_curve"] = (1 + df["daily_return"]).cumprod()

    return df


# ========================================================
# 测试 1：总收益率
# ========================================================
def test_total_return():
    """总收益率应该等于 equity_curve.iloc[-1] - 1"""
    df = _build_mini_df(
        closing_prices=[10.0, 10.5, 11.0],
        positions=[0, 1, 1],  # 第 2 天开仓（position 从 0 → 1），一直持仓
    )
    metrics = calculate_metrics(df)

    expected = df["equity_curve"].iloc[-1] - 1
    assert (
        abs(metrics["total_return"] - expected) < 1e-9
    ), f"total_return 不匹配：期望 {expected}, 实际 {metrics['total_return']}"


# ========================================================
# 测试 2：最大回撤
# ========================================================
def test_max_drawdown():
    """MDD 应该是 cummax 算法的结果——先涨后跌的场景"""
    # 构造净值序列：先涨到 1.20，再跌到 0.90 —— MDD 应该是 -25%
    df = pd.DataFrame(
        {
            "position": [1, 1, 1, 1, 1],
            "equity_curve": [1.0, 1.1, 1.2, 1.0, 0.9],  # 先涨后跌
        },
        index=pd.date_range("2026-01-02", periods=5, freq="B"),
    )

    metrics = calculate_metrics(df)

    # 从 1.2 跌到 0.9 → MDD = (0.9 - 1.2) / 1.2 = -25%
    expected_mdd = -0.25
    assert (
        abs(metrics["max_drawdown"] - expected_mdd) < 1e-9
    ), f"MDD 不匹配：期望 {expected_mdd}, 实际 {metrics['max_drawdown']}"


# ========================================================
# 测试 3：交易次数
# ========================================================
def test_num_trades():
    """交易次数应该等于完整的开仓-平仓配对数量"""
    # position 变化 3 次开仓 + 3 次平仓 → 应该是 3 笔完整交易
    df = _build_mini_df(
        closing_prices=[10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 14.5],
        positions=[0, 1, 1, 0, 0, 1, 1, 0, 1, 0],
        # 开仓日：1, 5, 8；平仓日：3, 7, 9 → 3 对
    )
    metrics = calculate_metrics(df)

    assert (
        metrics["num_trades"] == 3
    ), f"交易次数不匹配：期望 3, 实际 {metrics['num_trades']}"


# ========================================================
# 测试 4：第一个信号是死叉时不应该崩
# ========================================================
def test_first_signal_is_death_cross():
    """
    真实数据场景：平安银行第一个信号是 2025-07-23 死叉
    必须保证 calculate_metrics 不会因为这个边界而崩
    （这是之前 cumsum 边界 bug 的真实场景，作为回归测试保留）
    """
    df = _build_test_df()  # 用真实数据
    metrics = calculate_metrics(df)

    # 验证：交易次数应该 > 0（不会被边界 bug 卡成 0）
    assert metrics["num_trades"] > 0, "交易次数为 0—可能是 cumsum 边界 bug 复发"

    # 验证：position 列里既有 0 又有 1（说明状态机正常切换）
    assert df["position"].max() == 1, "position 应该至少出现过 1（持仓）"
    assert df["position"].min() == 0, "position 应该至少出现过 0（空仓）"


# ========================================================
# 测试 5：无未来函数偏差
# ========================================================
def test_no_lookahead_bias():
    """
    信号 T 日产生 → T 日 position 还没生效 → T+1 日才生效
    构造一个金叉信号在第 2 天，验证 position 第 3 天才变 1
    """
    # 手动构造 df（不走 run_backtest），直接验证 run_backtest 的语义
    from backtest import run_backtest as do_backtest

    df = pd.DataFrame(
        {
            "收盘": [10.0, 10.5, 10.8, 11.0, 11.2],
            "golden_cross": [False, True, False, False, False],  # 第 2 天金叉
            "death_cross": [False, False, False, False, False],
        },
        index=pd.date_range("2026-01-02", periods=5, freq="B"),
    )

    df = do_backtest(df)

    # 关键断言：金叉信号 T 日（index=1） position 应该还是 0
    assert (
        df["position"].iloc[1] == 0
    ), "信号 T 日 position 应该 = 0（未来函数偏差防御）"

    # T+1 日（index=2）position 应该变 1
    assert df["position"].iloc[2] == 1, "信号 T+1 日 position 应该 = 1（shift 后生效）"


# ========================================================
# 测试 6：胜率 + 盈亏比
# ========================================================
def test_win_rate_and_pl_ratio():
    """
    构造 2 笔交易：1 笔赚（+10%），1 笔亏（-5%）
    胜率应该 = 1/2 = 50%
    盈亏比应该 = 10% / 5% = 2.0
    """
    # 第 1 笔：10 → 11（涨 10%）
    # 第 2 笔：11 → 10.45（跌 5%）
    df = _build_mini_df(
        closing_prices=[
            10.0,
            10.0,
            11.0,  # 第 1 天空仓，第 2 天开仓（按 T+1 收盘价），第 3 天涨到 11
            11.0,  # 第 4 天平仓
            11.0,
            11.0,
            10.45,  # 第 5 天空仓持续，第 6 天开仓，第 7 天跌到 10.45
            10.45,  # 第 8 天平仓
        ],
        positions=[0, 1, 1, 0, 0, 1, 1, 0],
    )
    metrics = calculate_metrics(df)

    # 应该有 2 笔交易
    assert metrics["num_trades"] == 2, f"交易次数应该是 2，实际 {metrics['num_trades']}"

    # 胜率：50%
    assert (
        abs(metrics["win_rate"] - 0.5) < 1e-9
    ), f"胜率应该是 0.5，实际 {metrics['win_rate']}"

    # 盈亏比：约 2.0 (扣完手续费后会略小)
    # 第 1 笔毛利约 +10%, 扣 2 次 commission ≈ +9.85%
    # 第 2 笔毛亏约 -5%, 扣 2 次 commission ≈ -5.15%
    # 盈亏比 ≈ 9.85 / 5.15 ≈ 1.91
    # 允许较大误差范围
    assert (
        1.5 < metrics["profit_loss_ratio"] < 2.5
    ), f"盈亏比应该约为 1.9 左右，实际 {metrics['profit_loss_ratio']}"
