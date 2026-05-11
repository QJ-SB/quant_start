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
         + 策略净值曲线（如果 df 中有 equity_curve 列，用右 Y 轴显示）
    副图：成交量柱状图

    :param df: 数据 DataFrame，需包含以下列：
               收盘 / MA5 / MA20 / golden_cross / death_cross / 成交量
               可选：equity_curve（策略净值曲线，会在主图右轴显示）
    :param save_path: 图片保存路径（默认 "images/ma_cross_demo.png"）

    :return: None（副作用：保存 PNG 到磁盘 + 弹窗显示）
    """
    # ============== 1. 创建绘图画布与上下子图 ==============
    # 创建2行1列的子图，共享X轴；主图:副图高度比例=3:1
    fig, (ax1, ax2) = plt.subplots(
        nrows=2,
        ncols=1,
        figsize=(14, 8),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    # ============== 2. 主图左轴：绘制价格与均线 ==============
    # 绘制收盘价曲线
    ax1.plot(df["收盘"], label="收盘价", color="black")
    # 绘制5日均线曲线
    ax1.plot(df["MA5"], label="MA5", color="orange")
    # 绘制20日均线曲线
    ax1.plot(df["MA20"], label="MA20", color="purple")

    # ============== 3. 主图：标记金叉、死叉信号点 ==============
    # 筛选出所有金叉信号的数据
    golden_cross_points = df[df["golden_cross"]]
    # 绘制金叉标记（红色上三角，标注在收盘价下方2%位置）
    ax1.scatter(
        x=golden_cross_points.index,
        y=golden_cross_points["收盘"] * 0.98,
        marker="^",
        s=100,
        label="金叉",
        color="red",
        zorder=5,
    )
    # 筛选出所有死叉信号的数据
    death_cross_points = df[df["death_cross"]]
    # 绘制死叉标记（绿色下三角，标注在收盘价上方2%位置）
    ax1.scatter(
        x=death_cross_points.index,
        y=death_cross_points["收盘"] * 1.02,
        marker="v",
        s=100,
        label="死叉",
        color="green",
        zorder=5,
    )

    # ============== 4. 主图左轴：设置标题、标签、图例、网格 ==============
    ax1.set_title("平安银行（000001）- MA Cross Strategy with Backtest")
    ax1.set_ylabel("价格", color="black")
    ax1.legend(loc="upper left")
    ax1.grid(True)

    # ============== 5. 主图右轴：绘制策略净值曲线（双Y轴） ==============
    # 判断数据中是否存在净值曲线，存在则绘制
    if "equity_curve" in df.columns:
        # 创建共享X轴的右侧Y轴
        ax1_right = ax1.twinx()
        # 绘制策略净值虚线曲线
        ax1_right.plot(
            df["equity_curve"],
            label="策略净值",
            color="blue",
            linestyle="--",
            linewidth=1.5,
            alpha=0.8,
        )
        # 绘制净值基准线（初始本金=1.0）
        ax1_right.axhline(y=1.0, color="gray", linestyle=":", alpha=0.5, linewidth=1)
        # 设置右轴标签与颜色
        ax1_right.set_ylabel("策略净值（起点=1.0）", color="blue")
        # 设置右轴刻度颜色
        ax1_right.tick_params(axis="y", labelcolor="blue")
        # 显示右轴图例
        ax1_right.legend(loc="upper right")

    # ============== 6. 副图：绘制成交量柱状图 ==============
    # 成交量单位转换：手 → 万手
    volume_in_wan_shou = df["成交量"] / 10000
    # 绘制灰色半透明成交量柱状图
    ax2.bar(
        x=df.index,
        height=volume_in_wan_shou,
        color="gray",
        alpha=0.6,
    )

    # ============== 7. 副图：设置坐标轴标签、网格 ==============
    ax2.set_xlabel("日期")
    ax2.set_ylabel("成交量（万手）")
    ax2.grid(True)

    # ============== 8. 图表优化、保存与展示 ==============
    # 自动调整图表布局，防止元素重叠
    plt.tight_layout()
    # 保存图片到指定路径，设置清晰度
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    # 弹窗展示绘制好的图表
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
