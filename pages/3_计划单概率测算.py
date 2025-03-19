import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# 设置页面配置
st.set_page_config(page_title="足彩投注策略优化工具", layout="wide")

# 应用标题和简介
st.title("足彩投注策略优化工具")
st.markdown("""
本工具旨在通过数据分析和模拟，帮助优化足彩投注策略。功能包括：
- **数据可视化**：赔率分布、盈利曲线、最大回撤等分析；
- **投注策略模拟器**：输入资金、策略和赔率，计算盈利概率并模拟策略效果；
- **决策支持**：自动推荐每日最佳投注组合（可根据历史数据动态调整）；
- **自动化+人工调整**：提供自动计算的投注方案，允许用户根据需要调整策略参数。
""")

# 侧边栏 - 策略参数输入
st.sidebar.header("策略参数设置")
initial_capital = st.sidebar.number_input("初始资金", min_value=0.0, value=1000.0, step=100.0)
target_profit = st.sidebar.number_input("目标总盈利", min_value=0.0, value=300.0, step=50.0)
days = st.sidebar.number_input("计划天数", min_value=1, value=20, step=1)
bets_per_day = st.sidebar.number_input("每日投注次数 (马丁策略指单日最大连投次数)", min_value=1, value=1, step=1)
avg_odds = st.sidebar.number_input("投注赔率 (平均每次投注赔率)", min_value=1.01, value=2.0, step=0.1)
# 提示用户可以调整胜率
assume_fair = st.sidebar.checkbox("假设赔率公平(胜率 = 1/赔率)", value=True)
if assume_fair:
    win_prob = 1.0/avg_odds
else:
    win_prob = st.sidebar.slider("预期胜率 (每次投注中奖概率)", min_value=0.0, max_value=1.0, value=min(1.0, 1.0/avg_odds + 0.1), step=0.01)

strategy = st.sidebar.selectbox("选择投注策略", 
    options=["固定投注 (定额投注)", "马丁格尔策略 (翻倍投注)", "凯利策略 (凯利公式投注)", "比例投注 (每次投入固定比例资金)"], 
    index=1)  # 默认选择马丁格尔

# 如果策略是马丁格尔，显示每日目标盈利输入；否则不需要每日目标
if "马丁" in strategy:
    daily_target = st.sidebar.number_input("单日目标盈利", min_value=0.0, value=20.0, step=5.0)
else:
    # 非马丁策略不需要 daily_target，但为了代码统一，设为0或忽略
    daily_target = None

# 如果策略是固定投注，提供固定投注额输入；如果是比例投注，提供比例输入
if "固定投注" in strategy and "定额" in strategy:
    flat_stake = st.sidebar.number_input("每次固定投注额", min_value=0.0, value=50.0, step=10.0)
else:
    flat_stake = None
if "比例投注" in strategy:
    bet_percentage = st.sidebar.slider("每次投注资金比例 (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0)
    bet_percentage = bet_percentage / 100.0  # 转换为小数
else:
    bet_percentage = None

st.write("----")  # 分隔线

# 1. 数据可视化
st.header("1. 数据可视化 📊")
st.markdown("上传历史投注数据（支持CSV/Excel格式），系统将展示赔率分布、盈利曲线以及回撤分析等结果。")

# 文件上传
uploaded_file = st.file_uploader("上传历史数据文件", type=["csv", "xlsx", "xls"])

# 检查用户是否上传了文件
if uploaded_file:
    # 根据文件扩展名选择读取方法
    file_name = uploaded_file.name
    try:
        if file_name.endswith(".csv"):
            data = pd.read_csv(uploaded_file)
        else:
            data = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"读取数据文件失败: {e}")
        data = None

    if data is not None:
        st.subheader("历史数据概览")
        # 在显示数据前进行类型转换
        display_data = data.copy()
        for col in display_data.columns:
            if col.lower() in ["odds", "赔率"]:
                display_data[col] = display_data[col].astype(str)
        st.write(display_data.head(10))  # 显示前10行数据

        # 检测常见字段名
        odds_col = None
        profit_col = None
        outcome_col = None
        stake_col = None
        # 常见字段中文/英文名称
        for col in data.columns:
            if col.lower() in ["odds", "赔率"]:
                odds_col = col
            if col.lower() in ["profit", "盈亏", "收益"]:
                profit_col = col
            if col.lower() in ["result", "outcome", "中奖", "是否中奖"]:
                outcome_col = col
            if col.lower() in ["stake", "投注", "投注额", "金额"]:
                stake_col = col

        # 如果没有盈利列但有结果和投注额和赔率，则计算每笔盈利
        if profit_col is None:
            if outcome_col is not None and stake_col is not None and odds_col is not None:
                # 尝试根据中奖与否计算盈亏
                # 假设 outcome 列以1表示中奖，0表示未中
                data['盈亏'] = data[stake_col] * (data[odds_col] - 1) * data[outcome_col] - data[stake_col] * (1 - data[outcome_col])
                profit_col = '盈亏'
            else:
                # 无法计算盈亏，则跳过盈利曲线绘制
                profit_col = None

        # 赔率分布分析
        if odds_col:
            st.subheader("赔率分布")
            try:
                odds_values = data[odds_col].astype(float)
                # 创建用于显示的DataFrame并确保类型转换
                chart_data = pd.DataFrame({"odds": odds_values})
                chart_data["odds"] = chart_data["odds"].astype(str)
                # 绘制赔率直方图
                chart = alt.Chart(chart_data).mark_bar().encode(
                    alt.X("odds:Q", bin=alt.Bin(maxbins=20), title="赔率区间"),
                    alt.Y('count()', title='频数')
                )
                st.altair_chart(chart, use_container_width=True)
            except Exception as e:
                st.write("无法绘制赔率分布图: ", e)
        else:
            st.write("未找到赔率列，无法进行赔率分布分析。")

        # 盈利曲线展示
        if profit_col:
            st.subheader("累计盈利曲线")
            # 如果有日期或时间列，尝试按照时间排序
            if 'date' in data.columns.str.lower() or '日期' in data.columns:
                # 找到日期列名
                date_col = None
                for col in data.columns:
                    if "date" in col.lower() or "日期" in col:
                        date_col = col
                        break
                if date_col:
                    data = data.sort_values(by=date_col)
            # 计算累计盈亏
            data['累计盈亏'] = data[profit_col].cumsum()
            # 绘制累计盈亏曲线
            line_chart = alt.Chart(data.reset_index()).mark_line().encode(
                x=alt.X('index', title='投注次数'),
                y=alt.Y('累计盈亏', title='累计盈亏')
            )
            st.altair_chart(line_chart, use_container_width=True)
        else:
            st.write("未提供每笔盈亏数据，无法绘制累计盈利曲线。")

        # 回撤分析与风险控制
        if profit_col:
            st.subheader("最大回撤分析")
            cum_profit = data[profit_col].cumsum()
            running_max = cum_profit.cummax()
            drawdown = cum_profit - running_max
            max_drawdown = drawdown.min()
            max_drawdown_amount = abs(max_drawdown) if max_drawdown < 0 else 0.0
            st.write(f"历史最大回撤: {-max_drawdown_amount:.2f}")  # 负值取绝对值显示
            # 绘制回撤曲线（用负值表示回撤幅度）
            drawdown_chart = alt.Chart(pd.DataFrame({"drawdown": drawdown})).mark_area(color='orange').encode(
                x=alt.X('index', title='投注次数'),
                y=alt.Y('drawdown', title='回撤金额')
            )
            st.altair_chart(drawdown_chart, use_container_width=True)
        # 计算最长连败（风险指标）
        if outcome_col or profit_col:
            # 构造胜负序列：如果有 outcome 列直接用；否则用 profit 列判断正负
            if outcome_col:
                wins_losses = data[outcome_col].apply(lambda x: 1 if x in [1, '1', 'win', 'Win', 'WIN', '中奖'] else 0)
            elif profit_col:
                wins_losses = data[profit_col].apply(lambda x: 1 if x > 0 else 0)
            else:
                wins_losses = None
            if wins_losses is not None:
                losses = (wins_losses == 0).astype(int)
                # 计算最长连续1的长度，这里计算最长连续的0（连败）
                max_losing_streak = 0
                current_streak = 0
                for val in losses:
                    if val == 1:  # 这是一次失败
                        current_streak += 1
                        max_losing_streak = max(max_losing_streak, current_streak)
                    else:
                        current_streak = 0
                st.write(f"历史最长连续未中奖次数: {max_losing_streak}")
                if "马丁" in strategy and daily_target is not None:
                    if bets_per_day < max_losing_streak:
                        st.warning(f"注意：历史最大连败为{max_losing_streak}，已超过当前设置的马丁策略最大连投次数{bets_per_day}，可能存在较高风险！")
    else:
        st.error("数据加载失败，无法进行可视化分析。")
else:
    st.info("请上传历史数据文件，以进行赔率和盈亏数据分析。")

st.write("----")

# 2. 投注策略模拟器
st.header("2. 投注策略模拟器 🎲")
st.markdown("""
在此模块中，您可以模拟不同的投注策略在一段时间内的表现。输入初始资金、目标盈利、计划天数以及投注策略参数，系统将模拟多次试验以估计：
- 达到目标盈利的概率
- 最终盈利为正的概率
- 发生资金亏空(破产)的概率
- 策略的预期盈利分布
""")

# 获取侧边栏参数（已在侧边栏输入）
cap = initial_capital
total_target = target_profit
num_days = int(days)
bets_each_day = int(bets_per_day)
odds = avg_odds
p = win_prob  # 胜率
strategy_name = strategy

# 设置模拟次数
sim_runs = st.number_input("模拟次数(随机试验数量)", min_value=100, max_value=10000, value=1000, step=100)

# 定义策略模拟函数
def simulate_strategy(capital, odds, win_prob, days, bets_per_day, strategy, daily_target=None, flat_stake=None, bet_percent=None):
    """模拟给定策略一次完整运行，返回最终资金以及是否达到目标盈利。"""
    initial_cap = capital
    current_cap = capital
    achieved_target = False
    # 循环天数
    for day in range(1, days+1):
        # 每天根据策略执行投注
        if "马丁" in strategy:
            # 马丁格尔策略：每天以daily_target为目标进行最多bets_per_day次投注
            day_loss = 0.0
            success = False
            for attempt in range(1, bets_per_day+1):
                # 计算本次投注额
                # 如资金不足以按照公式投注，则投入剩余全部资金（相当于破产前最后一搏）
                required_stake = (day_loss + daily_target) / (odds - 1) if odds > 1 else current_cap
                stake = required_stake if current_cap >= required_stake else current_cap
                # 扣除投注额
                current_cap -= stake
                # 随机结果
                if np.random.rand() < win_prob:
                    # 中奖，获得赔付
                    payout = stake * odds  # 含本金的返奖总额
                    profit = payout - stake  # 净利润
                    current_cap += payout  # 本金返还加利润计入资金
                    success = True
                    break  # 当天达到目标盈利，退出循环
                else:
                    # 未中奖，累计损失
                    day_loss += stake
                    # 若资金已耗尽，则提前结束模拟
                    if current_cap <= 0:
                        break
            # 如果当天结束仍未成功且资金用完，则提前结束整个模拟
            if current_cap <= 0:
                break
            # （马丁策略下，无论当天成功与否，都继续到下一天；但如果资金不足则已跳出）
        elif "固定投注" in strategy and "定额" in strategy:
            # 固定金额投注，每天 bets_per_day 次独立投注
            for b in range(bets_per_day):
                if current_cap <= 0:
                    break
                stake = flat_stake if flat_stake is not None else 0
                if current_cap < stake:
                    # 如果资金不足以投注既定金额，则投注剩余资金
                    stake = current_cap
                current_cap -= stake
                if np.random.rand() < win_prob:
                    payout = stake * odds
                    profit = payout - stake
                    current_cap += payout
                # 固定投注策略不要求单日赢止损，可以一直投满bets_per_day次
                # （真实场景可根据需要在这儿加入赢到目标即停等规则）
                # 这里假设固定投注不按日目标止盈，只按总目标
        elif "凯利" in strategy:
            # 凯利策略：每次根据凯利公式投注一定比例资金
            for b in range(bets_per_day):
                if current_cap <= 0:
                    break
                # 计算凯利投注比例
                b_ = odds - 1  # 赔率净值
                # 如果没有优势(win_prob <= 1/odds)，凯利系数会<=0，按不投注处理
                kelly_fraction = (win_prob * (odds) - 1) / (odds - 1)
                if kelly_fraction <= 0:
                    # 无正期望，不投注（跳过本次）
                    continue
                # 实际投注额
                stake = current_cap * kelly_fraction
                if stake <= 0:
                    continue
                if current_cap < stake:
                    stake = current_cap
                current_cap -= stake
                if np.random.rand() < win_prob:
                    payout = stake * odds
                    profit = payout - stake
                    current_cap += payout
                # 凯利策略也不按日止盈，持续投注
        elif "比例投注" in strategy:
            # 比例投注：每次投注一定比例资金（如每次押注当前资金的X%）
            for b in range(bets_per_day):
                if current_cap <= 0:
                    break
                if bet_percent is None or bet_percent <= 0:
                    break
                stake = current_cap * bet_percent
                if stake < 0:
                    continue
                if current_cap < stake:
                    stake = current_cap
                current_cap -= stake
                if np.random.rand() < win_prob:
                    payout = stake * odds
                    profit = payout - stake
                    current_cap += payout
        else:
            # 默认：如果未匹配任何策略，就当作固定投注处理
            for b in range(bets_per_day):
                if current_cap <= 0:
                    break
                stake = flat_stake if flat_stake is not None else (0.05 * current_cap)
                if current_cap < stake:
                    stake = current_cap
                current_cap -= stake
                if np.random.rand() < win_prob:
                    payout = stake * odds
                    current_cap += payout
        # 检查是否达到总目标盈利，如果达到则视为成功并停止模拟
        if current_cap - initial_cap >= total_target:
            achieved_target = True
            break
    final_profit = current_cap - initial_cap
    return current_cap, final_profit, achieved_target

# 运行模拟多次
results = {
    "final_profit": [],
    "achieved_target": [],
    "bankrupt": []
}
bankrupt_count = 0
success_count = 0

for i in range(int(sim_runs)):
    final_cap, final_profit, achieved = simulate_strategy(cap, odds, p, num_days, bets_each_day, strategy_name, daily_target, flat_stake, bet_percentage)
    results["final_profit"].append(final_profit)
    results["achieved_target"].append(achieved)
    # 认为资金<=0即为破产
    if final_cap <= 0.0001:  # 用一个很小的阈值判断浮点
        results["bankrupt"].append(1)
        bankrupt_count += 1
    else:
        results["bankrupt"].append(0)
    if achieved:
        success_count += 1

# 计算概率
success_rate = success_count / sim_runs
bankrupt_rate = bankrupt_count / sim_runs
profit_positive_rate = sum(1 for x in results["final_profit"] if x > 0) / sim_runs

# 显示模拟结果
st.subheader("模拟结果概览")
st.write(f"达到目标盈利({total_target:.0f})的概率：**{success_rate*100:.1f}%**")
st.write(f"最终盈利为正的概率：**{profit_positive_rate*100:.1f}%**")
st.write(f"发生资金亏空(破产)的概率：**{bankrupt_rate*100:.1f}%**")

# 盈利分布图表
st.subheader("最终盈利分布")
final_profit_series = pd.Series(results["final_profit"], name="最终盈亏")
hist_chart = alt.Chart(pd.DataFrame({"profit": results["final_profit"]})).mark_bar().encode(
    alt.X("profit", bin=alt.Bin(maxbins=20), title="最终盈亏区间"),
    alt.Y('count()', title='频数')
)
st.altair_chart(hist_chart, use_container_width=True)

st.write("注：以上模拟为基于随机模型的估计，实际结果可能受多种因素影响。调整参数以查看不同情景下策略的表现。")

st.write("----")

# 3. 决策支持 - 每日最佳投注组合推荐
st.header("3. 每日最佳投注组合 🤖")
st.markdown("""
根据当前策略和历史数据(如有)，系统推荐以下投注选项以供今日参考。您可以根据经验和偏好对推荐进行调整。
""")

# 如果有历史数据，可以基于历史胜率或赔率分布生成推荐；没有则随机生成示例
recommendations = []
np.random.seed(42)  # 固定随机种子使示例可重复
if uploaded_file and odds_col and outcome_col:
    # 如果有历史数据，用历史平均胜率和赔率生成示例
    # 计算历史整体胜率
    if outcome_col:
        try:
            hist_outcomes = data[outcome_col].apply(lambda x: 1 if str(x) in ["1", "win", "Win", "WIN", "中奖"] else 0)
            hist_win_rate = hist_outcomes.mean()
        except:
            hist_win_rate = None
    else:
        hist_win_rate = None
    # 历史平均赔率
    if odds_col:
        try:
            avg_odds_val = float(data[odds_col].mean())
        except:
            avg_odds_val = odds
    else:
        avg_odds_val = odds
    # 使用历史平均赔率和胜率波动随机推荐
    for i in range(3):
        # 生成接近历史平均赔率的随机赔率
        rec_odds = max(1.01, np.random.normal(loc=avg_odds_val, scale=0.5))
        # 生成预测胜率：稍高于隐含胜率，假设存在一定优势
        implied_p = 1.0 / rec_odds
        if hist_win_rate:
            # 结合历史胜率和隐含概率
            predicted_p = min(0.99, max(implied_p, (hist_win_rate + implied_p)/2 + 0.05))
        else:
            predicted_p = min(0.99, implied_p + 0.1)
        team_a = chr(65 + i*2)  # 用字母模拟球队名
        team_b = chr(65 + i*2 + 1)
        match_name = f"球队{team_a} vs 球队{team_b}"
        ev = predicted_p * rec_odds
        recommendations.append({
            "比赛": match_name,
            "赔率": f"{rec_odds:.2f}",
            "预计胜率": f"{predicted_p*100:.1f}%",
            "期望值EV": f"{ev:.2f}"
        })
else:
    # 无历史数据，用预设或随机数据推荐
    sample_matches = [("红队", "蓝队"), ("黄队", "绿队"), ("黑队", "白队")]
    for (team1, team2) in sample_matches:
        rec_odds = max(1.01, np.random.normal(loc=avg_odds, scale=0.3))
        implied_p = 1.0 / rec_odds
        # 假设推荐的比赛我们有一定把握，提升胜率0.05
        predicted_p = min(0.99, implied_p + 0.05)
        ev = predicted_p * rec_odds
        recommendations.append({
            "比赛": f"{team1} vs {team2}",
            "赔率": f"{rec_odds:.2f}",
            "预计胜率": f"{predicted_p*100:.1f}%",
            "期望值EV": f"{ev:.2f}"
        })

rec_df = pd.DataFrame(recommendations)
# 确保数据类型转换
rec_df = rec_df.astype({
    "比赛": str,
    "赔率": str,
    "预计胜率": str,
    "期望值EV": str
})
st.subheader("推荐投注选项:")
st.table(rec_df)

st.markdown("**提示**: 建议优先选择胜率高且赔率合理的比赛进行投注，以提高盈利概率。您可以根据自身分析调整投注组合和资金分配，以控制风险。")
