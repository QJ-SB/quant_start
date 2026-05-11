"""
main.py — 主入口

串联：数据加载 → 信号计算 → 回测 → 评估 → 可视化
"""

from data_loader import load_stock_daily_data
from signals import calculate_ma_cross
from backtest import run_backtest, calculate_metrics
from visualization import plot_ma_cross


def main(symbol="000001"):
    """
    运行 MA 交叉策略 demo + 完整回测评估。

    :param symbol: 股票代码（默认平安银行 000001）
    """
    # Step 1: 加载数据
    df = load_stock_daily_data(symbol)

    # Step 2: 计算 MA 均线和金叉死叉信号
    df = calculate_ma_cross(df, short_window=5, long_window=20)

    # Step 3: 回测 + 评估
    df = run_backtest(df)
    metrics = calculate_metrics(df)

    # Step 4: 打印金叉死叉信号
    print("【金叉】：")
    print(df[df["golden_cross"]][["收盘", "MA5", "MA20"]])
    print("\n【死叉】：")
    print(df[df["death_cross"]][["收盘", "MA5", "MA20"]])

    # Step 5: 打印策略评估指标
    print("\n【策略评估指标】：")
    print(f"  总收益率:     {metrics['total_return'] * 100:>7.2f}%")
    print(f"  最大回撤:     {metrics['max_drawdown'] * 100:>7.2f}%")
    print(f"  胜率:         {metrics['win_rate'] * 100:>7.2f}%")
    if metrics["profit_loss_ratio"] is not None:
        print(f"  盈亏比:       {metrics['profit_loss_ratio']:>7.2f}")
    else:
        print(f"  盈亏比:       N/A")
    print(f"  完整交易次数: {metrics['num_trades']:>7d}")

    # Step 6: 画图（含净值曲线）
    plot_ma_cross(df)


if __name__ == "__main__":
    main()
