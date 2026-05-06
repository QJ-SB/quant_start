import time
import os
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt


def fetch_daily_with_retry(symbol, start_date, end_date, max_retries=5):
    """
    股票日线拉取函数，自动重试。

    :param symbol:股票代码
    :param start_date:起始日期
    :param end_date:截止日期
    :param max_retries:最大重试次数

    :return:pd.DataFrame: 日线数据 dataframe
            RuntimeError：拉取失败，终止
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

    :param symbol:股票代码
    :param force_refresh:是否强制从网络拉取新数据刷新（默认：否）

    :return:pd.DataFrame: 日线数据 dataframe
    """

    # 拼接具体缓存路径
    cache_path = os.path.join(CACHE_DIR, f"{symbol}.csv")

    # 1. 如果缓存存在且"不强制刷新_on" → 直接读 CSV
    if os.path.exists(cache_path) and not force_refresh:
        df = pd.read_csv(cache_path, dtype={"股票代码": str})
    else:
        # 2. 否则，开手机热点 → 从 akshare 拉 → 存 CSV
        print("从akshare拉取新数据")

        # 自动计算格式化的：起始和截止日期
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

        # 从网络拉取最新日线数据（自建函数）
        df = fetch_daily_with_retry(
            symbol=symbol, start_date=start_date, end_date=end_date
        )
        # 刷新到CSV缓存文件
        df.to_csv(path_or_buf=cache_path, index=False)

    # 把“日期”类型改为-datatime，并设置为索引-index
    df["日期"] = pd.to_datetime(df["日期"])
    df = df.set_index("日期")

    return df


def calculate_ma_cross(df, short_window=5, long_window=20):
    """
    计算 MA 均线及金叉死叉信号。

    :param df: 日线数据 DataFrame
    :param short_window: 短期均线窗口（默认5日均线）
    :param long_window: 长期均线窗口（默认20日均线）
    :return: 增加了 MA 列和 cross 列的 DataFrame
    """

    # 在df里计算并新增 “MA_short”和 “MA_long”列
    df[f"MA{short_window}"] = df["收盘"].rolling(window=short_window).mean()
    df[f"MA{long_window}"] = df["收盘"].rolling(window=long_window).mean()

    # 分别得到“短期均线”和“长期均线”dataframe
    short_ma = df[f"MA{short_window}"]
    long_ma = df[f"MA{long_window}"]

    # 计算“金叉”和“死叉”产生的具体日期
    df["golden_cross"] = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
    df["death_cross"] = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))

    # 把加工好的df返回出去
    return df


# 【拉取数据形成dataframe，并在终端打印】
# 创建缓存根目录
CACHE_DIR = "daily_data_cache"  # 根目录名称
os.makedirs(name=CACHE_DIR, exist_ok=True)

# 调用股票日数据拉取函数，从缓存or网络（自建函数）
daily_data = load_stock_daily_data(symbol="000001")

# 计算均线交叉日（默认：5天均线，20天均线）
daily_data_with_ma_cross = calculate_ma_cross(
    df=daily_data, short_window=5, long_window=20
)

# 分别打印“金叉”和“死叉”出现的：日期、收盘价
df = daily_data_with_ma_cross  # 统一简化命名，利于后续工作
print("【金叉】：")
print(df[df["golden_cross"]][["收盘", "MA5", "MA20"]])
print("\n【死叉】：")
print(df[df["death_cross"]][["收盘", "MA5", "MA20"]])


# 【画K线图】
# 全局中文适配
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
# ========== v0.3 画图：主图 + 副图 ==========
# 1. 创建画布和两个子图
fig, (ax1, ax2) = plt.subplots(
    nrows=2,
    ncols=1,
    figsize=(14, 8),
    sharex=True,
    gridspec_kw={"height_ratios": [3, 1]},
)

# 2. 主图（ax1）：收盘价 + MA5 + MA20
ax1.plot(df["收盘"], label="收盘价", color="black")
ax1.plot(df["MA5"], label="MA5", color="orange")
ax1.plot(df["MA20"], label="MA20", color="purple")

# 3. 主图：金叉死叉标记
golden_cross_points = df[df["golden_cross"]]
ax1.scatter(
    x=golden_cross_points.index,
    y=golden_cross_points["收盘"] * 0.98,
    marker="^",
    s=100,
    label="金叉",
    color="red",
    zorder=5,
)
death_cross_points = df[df["death_cross"]]
ax1.scatter(
    x=death_cross_points.index,
    y=death_cross_points["收盘"] * 1.02,
    marker="v",
    s=100,
    label="死叉",
    color="green",
    zorder=5,
)

# 4. 主图：补全元素
ax1.set_title("平安银行（000001）- MA Cross Strategy")
ax1.set_ylabel("价格")
ax1.legend()
ax1.grid(True)

# 5. 副图（ax2）：成交量柱状图
volume_in_wan_shou = df["成交量"] / 10000  # 单位换算：手 → 万手
ax2.bar(
    x=df.index,
    height=volume_in_wan_shou,
    color="gray",
    alpha=0.6,
)

# 6. 副图：补全元素
ax2.set_xlabel("日期")
ax2.set_ylabel("成交量（万手）")
ax2.grid(True)

# 7. 保存 + 展示
plt.tight_layout()  # 自动调整子图间距，避免重叠
plt.savefig("images/ma_cross_demo.png", dpi=150, bbox_inches="tight")
plt.show()  # 展示
