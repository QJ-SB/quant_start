"""
main.py — 主入口

串联：数据加载 → 信号计算 → 可视化
"""

from data_loader import load_stock_daily_data
from signals import calculate_ma_cross
from visualization import plot_ma_cross


def main(symbol="000001"):
    """
    运行 MA 交叉策略 demo。

    :param symbol: 股票代码（默认平安银行 000001）
    """
    # Step 1: 加载数据（带缓存）
    df = load_stock_daily_data(symbol)

    # Step 2: 计算 MA 均线和金叉死叉信号
    df = calculate_ma_cross(df, short_window=5, long_window=20)

    # Step 3: 打印金叉死叉信号
    print("【金叉】：")
    print(df[df["golden_cross"]][["收盘", "MA5", "MA20"]])
    print("\n【死叉】：")
    print(df[df["death_cross"]][["收盘", "MA5", "MA20"]])

    # Step 4: 画图（保存 + 弹窗）
    plot_ma_cross(df)


if __name__ == "__main__":
    main()
