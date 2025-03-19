import streamlit as st
import matplotlib.pyplot as plt
from itertools import combinations
import matplotlib.font_manager as fm
import pandas as pd

# 尝试加载黑体字体
font_path = 'C:/Windows/Fonts/simhei.ttf'  # 更新为黑体字体路径
try:
    prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = prop.get_name()
except FileNotFoundError:
    print(f"字体文件未找到：{font_path}，将使用默认字体")
    # 使用默认字体
    plt.rcParams['font.family'] = 'sans-serif'

plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 设置页面标题
st.title('总进球盈亏结果总览（基于斐波那契投注法，不开倒车）')

# 添加赔率输入框，设置默认值为1.35，最小值为1，最大值为10，步长为0.01
odds = st.number_input('请输入赔率', min_value=1.0, max_value=10.0, value=1.35, step=0.01)

# 添加下注次数输入框，设置默认值为10，最小值为1，最大值为100，步长为1
days = st.number_input('请输入下注次数（天数）', min_value=1, max_value=100, value=10, step=1)

# 添加未中奖天数输入框，设置默认值为3，最小值为1，最大值为days，步长为1
no_win_days = st.number_input('请输入未中奖天数', min_value=1, max_value=days, value=3, step=1)

# 初始参数
initial_bet = 100  # 起投金额

# 生成所有未中奖天数的组合
all_combinations = list(combinations(range(days), no_win_days))

# 存储所有结果
results = []

for combo in all_combinations:
    current_bet = initial_bet
    previous_bet = 0  # 用于计算斐波那契
    total_profit = 0
    daily_profit = []

    for day in range(days):
        if day in combo:  # 未中奖
            profit = -current_bet
            # 计算下一次投注额
            if previous_bet == 0:  # 第一次未中奖
                next_bet = current_bet * 2  # 第二天200
            else:
                next_bet = current_bet + previous_bet
            previous_bet, current_bet = current_bet, next_bet
        else:  # 中奖
            profit = current_bet * odds - current_bet  # 计算盈利
            current_bet = initial_bet  # 重置投注
            previous_bet = 0

        total_profit += profit
        daily_profit.append(profit)

    results.append({
        "未中奖天数": combo,
        "每日盈亏": daily_profit,
        "总盈亏": total_profit
    })

# 创建DataFrame并按"总盈亏"升序排序
df = pd.DataFrame(results)
df_sorted = df.sort_values(by="总盈亏", ascending=True)

# 统计"总盈亏"列中每个值的出现次数
profit_counts = df_sorted['总盈亏'].value_counts().reset_index()
profit_counts.columns = ['总盈亏', '出现次数']

# 计算每个结果占总数的百分比
total_combinations = len(df_sorted)
profit_counts['百分比'] = profit_counts['出现次数'] / total_combinations * 100

# 计算"盈"的概率总和和"亏"的概率总和
profit_counts['盈亏类型'] = profit_counts['总盈亏'].apply(lambda x: '盈' if x > 0 else '亏')
probability_sum = profit_counts.groupby('盈亏类型')['百分比'].sum().reset_index()

# 显示数据表格
st.subheader('盈亏结果数据')
st.dataframe(profit_counts)

# 显示盈亏类型的概率总和
st.subheader('盈亏类型的概率总和')
st.dataframe(probability_sum)

# 绘制柱状图
fig, ax = plt.subplots()
ax.bar(profit_counts['总盈亏'].astype(str), profit_counts['出现次数'], color='skyblue')
ax.set_xlabel('总盈亏')
ax.set_ylabel('出现次数')
ax.set_title('每个盈亏结果的出现次数')
st.pyplot(fig)

# 绘制饼图
fig, ax = plt.subplots()
ax.pie(profit_counts['百分比'], labels=profit_counts['总盈亏'].astype(str), autopct='%1.1f%%', startangle=90)
ax.set_title('每个盈亏结果占总数的百分比')
st.pyplot(fig)
