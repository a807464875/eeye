import streamlit as st
import pandas as pd
from itertools import combinations

# 设置页面配置
st.set_page_config(
    page_title="彩票计算器",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 页面标题
st.title('总进球玩法预测（可选择斐波那契或倍投策略）')

# 创建两列用于输入参数
col1, col2 = st.columns(2)

with col1:
    # 添加赔率输入框
    odds = st.number_input('请输入赔率', min_value=1.0, max_value=10.0, value=1.35, step=0.01)
    # 添加下注次数输入框
    days = st.number_input('请输入下注次数（天数）', min_value=1, max_value=100, value=10, step=1)
    # 添加未中奖天数输入框
    no_win_days = st.number_input('请输入未中奖天数', min_value=1, max_value=days, value=3, step=1)

with col2:
    # 添加初始投注金额输入框
    initial_bet = st.number_input('请输入初始投注金额', min_value=1, max_value=1000, value=100, step=1)
    # 添加店主提成比例输入框
    commission_rate = st.number_input('请输入店主提成比例（%）', min_value=0.0, max_value=8.0, value=5.0, step=0.1) / 100
    # 添加店主实际赔率输入框
    actual_odds = st.number_input('请输入店主实际赔率', min_value=1.0, max_value=10.0, value=1.45, step=0.01)

# 添加策略选择和倍投倍数输入
st.sidebar.subheader("选择下注策略")
strategy = st.sidebar.radio("策略", ("斐波那契", "倍投"))

if strategy == "倍投":
    multiplier = st.sidebar.number_input('请输入倍投倍数', min_value=1, max_value=99, value=2, step=1)
else:
    multiplier = None  # 斐波那契策略不需要倍数

# 计算斐波那契数列
def fibonacci(n):
    sequence = [1, 1]
    for i in range(2, n):
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

# 计算最大投注金额
if strategy == "斐波那契":
    fibonacci_sequence = fibonacci(no_win_days + 1)
    max_bet = initial_bet * fibonacci_sequence[no_win_days]
else:
    max_bet = initial_bet * (multiplier ** no_win_days)

# 显示最大投注金额
st.subheader(f'在连续 {no_win_days} 次未中奖的情况下，下一次投注金额为：{max_bet} 元')

# 生成所有未中奖天数的组合
all_combinations = list(combinations(range(days), no_win_days))

# 存储所有结果
results = []

for combo in all_combinations:
    current_bet = initial_bet
    previous_bet = 0  # 用于计算斐波那契
    total_profit = 0
    daily_profit = []
    total_bet = 0  # 记录每种结果的投注总金额

    for day in range(days):
        if day in combo:  # 未中奖
            profit = -current_bet
            # 计算下一次投注额
            if strategy == "斐波那契":
                if previous_bet == 0:  # 第一次未中奖
                    next_bet = current_bet * 2  # 第二天200
                else:
                    next_bet = current_bet + previous_bet
                previous_bet, current_bet = current_bet, next_bet
            else:  # 倍投策略
                current_bet *= multiplier
        else:  # 中奖
            profit = current_bet * odds - current_bet  # 计算盈利
            current_bet = initial_bet  # 重置投注
            previous_bet = 0

        total_profit += profit
        daily_profit.append(profit)
        total_bet += current_bet  # 累加每次投注金额

    # 计算店主收入（包括提成和赔率差）
    commission_income = total_bet * commission_rate
    odds_difference_income = sum([bet * (actual_odds - odds) for bet in daily_profit if bet > 0])
    owner_commission = commission_income + odds_difference_income

    results.append({
        "未中奖天数": combo,
        "每日盈亏": daily_profit,
        "总盈亏": total_profit,
        "投注总金额": total_bet,
        "店主提成收入": commission_income,
        "店主赔率差收入": odds_difference_income,
        "店主总收入": owner_commission
    })

# 创建DataFrame并按"总盈亏"升序排序
df = pd.DataFrame(results)
df_sorted = df.sort_values(by="总盈亏", ascending=True)

# 计算总奖金
df_sorted['总奖金'] = df_sorted['总盈亏'] + df_sorted['投注总金额']

# 统计"总盈亏"列中每个值的出现次数
profit_counts = df_sorted['总盈亏'].value_counts().reset_index()
profit_counts.columns = ['总盈亏', '出现次数']

# 计算每个结果占总数的百分比
total_combinations = len(df_sorted)
profit_counts['概率'] = profit_counts['出现次数'] / total_combinations * 100

# 计算盈亏百分比
winning_percentage = profit_counts[profit_counts['总盈亏'] > 0]['概率'].sum()
losing_percentage = profit_counts[profit_counts['总盈亏'] <= 0]['概率'].sum()

# 创建盈亏百分比表格
percentage_data = pd.DataFrame({
    '类型': ['盈利', '亏损'],
    '百分比': [winning_percentage, losing_percentage]
})

# 统计彩民总投注金额和总奖金的情况
bet_counts = df_sorted['投注总金额'].value_counts().reset_index()
bet_counts.columns = ['投注总金额', '出现次数']
bet_counts['概率'] = bet_counts['出现次数'] / total_combinations * 100

prize_counts = df_sorted['总奖金'].value_counts().reset_index()
prize_counts.columns = ['总奖金', '出现次数']
prize_counts['概率'] = prize_counts['出现次数'] / total_combinations * 100

# 创建两个主要部分：彩民数据和店主数据
st.title("彩票计算器结果展示")

st.header("彩民盈亏结果数据")
col1, col2 = st.columns(2)

with col1:
    st.subheader('彩民总投注金额情况')
    st.dataframe(bet_counts.style.format({'投注总金额': '{:.2f}', '出现次数': '{:.0f}', '概率': '{:.2f}%'}), use_container_width=True)

with col2:
    st.subheader('彩民总奖金情况')
    st.dataframe(prize_counts.style.format({'总奖金': '{:.2f}', '出现次数': '{:.0f}', '概率': '{:.2f}%'}), use_container_width=True)

# 新增彩民盈亏结果数据表格
st.header("彩民盈亏结果详细数据")
st.dataframe(profit_counts.style.format({'总盈亏': '{:.2f}', '出现次数': '{:.0f}', '概率': '{:.2f}%'}), use_container_width=True)

st.header("店主数据")
col3, col4 = st.columns(2)

with col3:
    st.subheader('店主盈亏结果数据')
    st.dataframe(profit_counts.style.format({'总盈亏': '{:.2f}', '出现次数': '{:.0f}', '概率': '{:.2f}%'}), use_container_width=True)

with col4:
    st.subheader('彩民盈亏百分比')
    st.table(percentage_data.style.format({'百分比': '{:.2f}%'}))

    # 显示总体统计信息
    total_profit = df_sorted['总盈亏'].sum()
    avg_profit = df_sorted['总盈亏'].mean()
    st.write(f'总计盈亏：{total_profit:.2f} 元')
    st.write(f'平均盈亏：{avg_profit:.2f} 元') 