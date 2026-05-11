import pandas as pd


def run_backtest(df, initial_capital=100000, commission=0.00075):
    """
    根据金叉死叉信号模拟交易。

    关键假设（避免 Look-Ahead Bias）：
    - 信号在 T 日收盘后产生
    - 实际持仓状态从 T+1 日才生效
    - 用 .shift(1) 实现"延迟一天"

    持仓逻辑（状态机）：
    - 金叉日 → 切换到持仓状态（1）
    - 死叉日 → 切换到空仓状态（0）
    - 无信号日 → 维持上一次的状态（ffill 填充）

    收益计算：
    - 持仓中（position == 1）：daily_return = 当日涨跌幅
    - 空仓中（position == 0）：daily_return = 0
    - 开仓/平仓当日额外扣除 commission（默认 0.15%）

    :param df: 包含 golden_cross / death_cross 列的 DataFrame
    :param initial_capital: 初始资金（默认 10 万元，用于显示净值）
    :param commission: 单边交易费率（默认 0.00075，即每次开仓或平仓约 0.075%）
                       一次完整交易（开仓 + 平仓）总成本约 2 × commission = 0.15%

    :return: pd.DataFrame: 增加 position / daily_return / equity_curve 列
    """
    # ===== Step 1: 持仓状态（已有逻辑） =====
    target_position = pd.Series(index=df.index, dtype="float64")
    target_position[df["golden_cross"]] = 1.0
    target_position[df["death_cross"]] = 0.0
    target_position = target_position.ffill().fillna(0)
    df["position"] = target_position.shift(1).fillna(0).astype(int)

    # ===== Step 2: 每日策略收益率 =====
    # 1) 当日股价涨跌幅
    daily_pct_change = df["收盘"].pct_change().fillna(0)

    # 2) daily_return = 昨日是否持仓 × 今日涨跌幅
    #    用 position.shift(1) 实现：
    #    - 开仓日不吃涨跌（因为按当日收盘价买入，刚买就结束）
    #    - 平仓日吃涨跌（因为持仓到当日收盘卖出）
    #    这对应 T+1 收盘价交易模型
    df["daily_return"] = df["position"].shift(1).fillna(0) * daily_pct_change

    # 3) 开仓/平仓当日扣除交易成本（持仓变化 = 一次交易）
    position_change = df["position"].diff().abs().fillna(0)
    df["daily_return"] -= position_change * commission

    # ===== Step 3: 累计净值曲线 =====
    df["equity_curve"] = (1 + df["daily_return"]).cumprod()

    return df


def calculate_metrics(df):
    """
    计算策略评估指标。

    指标说明：
    - total_return: 总收益率（一年下来净值变化）
    - max_drawdown: 最大回撤（最痛苦的连续亏损幅度）
    - win_rate: 胜率（盈利交易笔数 / 总交易笔数）
    - profit_loss_ratio: 盈亏比（平均盈利 / 平均亏损）
    - num_trades: 完整交易次数（开仓 + 平仓配对）

    :param df: run_backtest 后的 DataFrame，需包含 position / equity_curve 列

    :return: dict: 各项指标的数值
    """
    #  ====================== 指标 1: 总收益率 ======================
    total_return = df["equity_curve"].iloc[-1] - 1

    # ====================== 指标 2: 最大回撤 ======================
    running_max = df["equity_curve"].cummax()  # 截至当日的历史最高净值
    drawdown = df["equity_curve"] / running_max - 1  # 每日相对历史最高的回撤
    max_drawdown = drawdown.min()

    # ================== 指标 3-5: 配对开仓平仓 → 计算单笔收益 ==================
    # 找出开仓点（0 → 1）和平仓点（1 → 0）
    position_diff = df["position"].diff()
    open_dates = df.index[position_diff == 1]  # position 增加 1 的日期
    close_dates = df.index[position_diff == -1]  # position 减少 1 的日期

    # 配对：第 N 次开仓 ↔ 第 N 次平仓
    # 注意：如果回测期结束时仍持仓，最后一次开仓没有对应平仓 → 用 zip 自动截断
    trades = list(zip(open_dates, close_dates))

    # ======= 计算每笔交易的收益率 =======
    # 初始化空列表，用于存储每一笔交易的收益率
    trade_returns = []
    # 遍历所有配对好的开仓/平仓日期（一笔交易 = 一次开仓+平仓）
    for open_d, close_d in trades:
        # 获取【开仓日】在表格中的行号，减1得到【开仓前一天】的行号
        prev_open_idx = df.index.get_loc(open_d) - 1

        # 边界处理：如果是回测第一天就开仓，没有前一天数据
        if prev_open_idx < 0:
            # 直接使用初始本金1.0作为入场净值
            entry_equity = 1.0
        else:
            # 正常情况：取开仓前一天的账户净值作为入场本金
            entry_equity = df["equity_curve"].iloc[prev_open_idx]

        # 获取平仓日当天的账户净值（出场总资产）
        exit_equity = df["equity_curve"].loc[close_d]
        # 计算单笔交易收益率：(平仓净值 ÷ 入场本金) - 1
        trade_return = exit_equity / entry_equity - 1
        # 将单笔收益率添加到列表中
        trade_returns.append(trade_return)

    # ====================== 指标3：胜率计算 ======================
    # 总交易次数 = 收益率列表的长度
    num_trades = len(trade_returns)
    # 筛选出所有盈利的交易（收益率>0）
    winning_trades = [r for r in trade_returns if r > 0]
    # 筛选出所有亏损/持平的交易（收益率≤0）
    losing_trades = [r for r in trade_returns if r <= 0]
    # 计算胜率：盈利次数/总次数；如果无交易，胜率直接为0（避免除以0报错）
    win_rate = len(winning_trades) / num_trades if num_trades > 0 else 0

    # ====================== 指标4：盈亏比计算 ======================
    # 只有同时存在盈利和亏损交易时，才计算盈亏比
    if winning_trades and losing_trades:
        # 计算平均单笔盈利：盈利总收益 ÷ 盈利笔数
        avg_win = sum(winning_trades) / len(winning_trades)
        # 计算平均单笔亏损：取绝对值（亏损为负数，方便对比）
        avg_loss = abs(sum(losing_trades) / len(losing_trades))
        # 计算盈亏比：平均盈利 ÷ 平均亏损
        profit_loss_ratio = avg_win / avg_loss
    else:
        # 全胜/全亏/无交易：无法计算盈亏比，赋值为空
        profit_loss_ratio = None

        # ====================== 返回回测核心指标 ======================
    return {
        "total_return": total_return,  # 总收益率
        "max_drawdown": max_drawdown,  # 最大回撤
        "win_rate": win_rate,  # 胜率
        "profit_loss_ratio": profit_loss_ratio,  # 盈亏比
        "num_trades": num_trades,  # 总交易次数
    }


# 模块自测
if __name__ == "__main__":
    print("=== backtest 自测 ===")
    from data_loader import load_stock_daily_data
    from signals import calculate_ma_cross

    df = load_stock_daily_data("000001")
    df = calculate_ma_cross(df)
    # 1. 运行完整的回测逻辑，给df新增持仓、每日收益、净值等列
    df = run_backtest(df)

    # ===================== 验证1：查看所有【开仓/平仓】的日期 =====================
    # 计算持仓是否发生变化（开仓/平仓 = 持仓状态改变）
    position_change = df["position"].diff().abs() > 0
    print("【持仓变化日】：")
    # 只打印【有开仓/平仓】的行，筛选关键列方便核对
    print(df[position_change][["收盘", "position", "daily_return", "equity_curve"]])

    # ===================== 验证2：计算并打印策略评估指标 =====================
    # 调用之前写的函数，计算回测指标（返回字典格式）
    metrics = calculate_metrics(df)
    print("\n【策略评估指标】：")
    # 格式化打印：总收益率（转百分比，保留2位小数）
    print(f"  总收益率:     {metrics['total_return'] * 100:>7.2f}%")
    # 格式化打印：最大回撤
    print(f"  最大回撤:     {metrics['max_drawdown'] * 100:>7.2f}%")
    # 格式化打印：胜率
    print(f"  胜率:         {metrics['win_rate'] * 100:>7.2f}%")

    # 判断盈亏比：如果能计算就打印，不能计算打印N/A
    if metrics["profit_loss_ratio"] is not None:
        print(f"  盈亏比:       {metrics['profit_loss_ratio']:>7.2f}")
    else:
        print(f"  盈亏比:       N/A")

    # 打印总交易次数（整数格式）
    print(f"  完整交易次数: {metrics['num_trades']:>7d}")
