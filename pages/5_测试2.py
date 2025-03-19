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
st.title('盈亏结果总览')

# 添加赔率输入框，设置默认值为1.35，最小值为1，最大值为10，步长为0.01
odds = st.number_input('请输入赔率', min_value=1.0, max_value=10.0, value=1.35, step=0.01)

# 添加下注次数输入框，设置默认值为10，最小值为1，最大值为100，步长为1
days = st.number_input('请输入下注次数（天数）', min_value=1, max_value=100, value=10, step=1)

# 添加未中奖天数输入框，设置默认值为3，最小值为1，最大值为days，步长为1
no_win_days = st.number_input('请输入未中奖天数', min_value=1, max_value=days, value=3, step=1)

# 添加初始投注金额输入框，设置默认值为100，最小值为1，最大值为1000，步长为1
initial_bet = st.number_input('请输入初始投注金额', min_value=1, max_value=1000, value=100, step=1)

# 计算斐波那契数列
def fibonacci(n):
    sequence = [1, 1]
    for i in range(2, n):
        sequence.append(sequence[-1] + sequence[-2])
    return sequence

# 计算最大投注金额
fibonacci_sequence = fibonacci(no_win_days + 1)
max_bet = initial_bet * fibonacci_sequence[no_win_days]

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
        total_bet += current_bet  # 累加每次投注金额

    results.append({
        "未中奖天数": combo,
        "每日盈亏": daily_profit,
        "总盈亏": total_profit,
        "投注总金额": total_bet  # 新增的"投注总金额"列
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

# 显示数据表格
st.subheader('盈亏结果数据')
st.dataframe(profit_counts)

# 绘制柱状图
fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(profit_counts['总盈亏'].astype(str), profit_counts['出现次数'], color='skyblue')
ax.set_xlabel('总盈亏')
ax.set_ylabel('出现次数')
ax.set_title('每个盈亏结果的出现次数')
plt.xticks(rotation=45)  # 旋转x轴标签
plt.tight_layout()  # 自动调整布局
st.pyplot(fig)

# 绘制饼图
fig, ax = plt.subplots()
ax.pie(profit_counts['百分比'], labels=profit_counts['总盈亏'].astype(str), autopct='%1.1f%%', startangle=90)
ax.set_title('每个盈亏结果占总数的百分比')
st.pyplot(fig)
