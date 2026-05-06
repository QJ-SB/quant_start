"""
data_loader.py — 数据获取层

负责从 akshare 拉取 A 股日线数据，带本地 CSV 缓存机制。
对外暴露：load_stock_daily_data 函数
"""

import time
import os
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd

# 缓存根目录（模块内部常量）
CACHE_DIR = "daily_data_cache"
os.makedirs(name=CACHE_DIR, exist_ok=True)


def fetch_daily_with_retry(symbol, start_date, end_date, max_retries=5):
    """
    股票日线拉取函数，自动重试。

    :param symbol: 股票代码
    :param start_date: 起始日期
    :param end_date: 截止日期
    :param max_retries: 最大重试次数

    :return: pd.DataFrame: 日线数据
    :raises RuntimeError: 连续 max_retries 次拉取失败
    """
    for i in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            print(f"第{i + 1}次拉取成功")
            return df
        except Exception as e:
            print(f"第{i + 1}次拉取失败：{type(e).__name__} - {e}")
            if i < max_retries - 1:
                time.sleep(3)

    raise RuntimeError(f"连续{max_retries}次拉取失败，终止尝试")


def load_stock_daily_data(symbol, force_refresh=False):
    """
    加载股票日线数据，优先读本地缓存。

    :param symbol: 股票代码
    :param force_refresh: 是否强制从网络拉取新数据刷新（默认：否）

    :return: pd.DataFrame: 日线数据（日期作 index）
    """
    cache_path = os.path.join(CACHE_DIR, f"{symbol}.csv")

    if os.path.exists(cache_path) and not force_refresh:
        df = pd.read_csv(cache_path, dtype={"股票代码": str})
    else:
        print("从akshare拉取新数据")
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        df = fetch_daily_with_retry(
            symbol=symbol, start_date=start_date, end_date=end_date
        )
        df.to_csv(path_or_buf=cache_path, index=False)

    df["日期"] = pd.to_datetime(df["日期"])
    df = df.set_index("日期")

    return df


# 模块自测：直接运行此文件时执行
if __name__ == "__main__":
    print("=== data_loader 自测 ===")
    df = load_stock_daily_data("000001")
    print(f"加载成功，数据形状：{df.shape}")
    print(df.head())
