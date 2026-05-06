"""
visualization.py — 可视化层

负责把策略数据画成主图+副图的双子图布局。
对外暴露：plot_ma_cross 函数
"""

import matplotlib.pyplot as plt

# 全局中文适配（模块加载时立即生效）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False


def plot_ma_cross(df, save_path="images/ma_cross_demo.png"):
    """
    画 MA 均线交叉策略图（主图 + 副图）。

    主图：收盘价 + MA5 + MA20 + 金叉死叉标记
    副图：成交量柱状图

    :param df: 数据 DataFrame，需包含以下列：
               收盘 / MA5 / MA20 / golden_cross / death_cross / 成交量
    :param save_path: 图片保存路径（默认 "images/ma_cross_demo.png"）

    :return: None（副作用：保存 PNG 到磁盘 + 弹窗显示）
    """
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
    volume_in_wan_shou = df["成交量"] / 10000
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
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.show()


# 模块自测：直接运行此文件时执行
if __name__ == "__main__":
    print("=== visualization 自测 ===")
    from data_loader import load_stock_daily_data
    from signals import calculate_ma_cross

    df = load_stock_daily_data("000001")
    df = calculate_ma_cross(df)
    plot_ma_cross(df)
    print("画图完成，PNG 已保存到 images/ma_cross_demo.png")
