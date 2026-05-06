"""
signals.py — 信号计算层

负责在日线数据上计算技术指标和交易信号。
对外暴露：calculate_ma_cross 函数
"""

import pandas as pd


def calculate_ma_cross(df, short_window=5, long_window=20):
    """
    计算 MA 均线及金叉死叉信号。

    在传入的 DataFrame 上新增 4 列：
    - MA{short_window}: 短期均线
    - MA{long_window}: 长期均线
    - golden_cross: 金叉信号（布尔值）
    - death_cross: 死叉信号（布尔值）

    :param df: 日线数据 DataFrame，需要包含"收盘"列
    :param short_window: 短期均线窗口（默认 5 日）
    :param long_window: 长期均线窗口（默认 20 日）

    :return: pd.DataFrame: 增加了 MA 列和 cross 列的 DataFrame
    """
    df[f"MA{short_window}"] = df["收盘"].rolling(window=short_window).mean()
    df[f"MA{long_window}"] = df["收盘"].rolling(window=long_window).mean()

    short_ma = df[f"MA{short_window}"]
    long_ma = df[f"MA{long_window}"]

    df["golden_cross"] = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
    df["death_cross"] = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))

    return df


# 模块自测：直接运行此文件时执行
if __name__ == "__main__":
    print("=== signals 自测 ===")
    from data_loader import load_stock_daily_data

    df = load_stock_daily_data("000001")
    df = calculate_ma_cross(df)

    print("【金叉】：")
    print(df[df["golden_cross"]][["收盘", "MA5", "MA20"]])
    print("\n【死叉】：")
    print(df[df["death_cross"]][["收盘", "MA5", "MA20"]])
