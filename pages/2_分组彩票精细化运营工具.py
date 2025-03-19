import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(layout="wide")  # 设置宽屏模式


def main():
    # 居中标题
    st.markdown("""
        <h1 style="text-align: center;">体彩店主精细化运营工具</h1>
    """, unsafe_allow_html=True)
    st.markdown("#### （同一日期同组数据覆盖，含体彩提成等）")

    base_excel_file = "bet_records"  # 基础文件名

    # 初始化全局记录：所有组的数据存储在 session_state['records']
    if 'records' not in st.session_state:
        st.session_state['records'] = []
        st.info("系统将根据组别分别存储记录。")

    # ========= 在左侧录入区顶部增加组别选择和刷新按钮 =========
    group_options = [f"组{i}" for i in range(1, 31)]
    selected_group = st.selectbox("请选择组别", group_options, index=0)

    if st.button("刷新当前组数据", key="refresh_data"):
        group_excel_file = f"{base_excel_file}_{selected_group}.xlsx"
        if os.path.exists(group_excel_file):
            df_refresh = pd.read_excel(group_excel_file, engine="openpyxl")
            st.session_state['records'] = df_refresh.to_dict('records')
            st.success(f"【{selected_group}】数据已刷新，记录数：{len(st.session_state['records'])}")
        else:
            st.error(f"未找到文件 {group_excel_file}，刷新失败！")

    # ========= 两列布局：左侧录入，右侧展示统计 =========
    col_left, col_right = st.columns([1, 3])

    # ========= 1. 左侧：录入新投注记录 =========
    with col_left:
        st.subheader("录入新投注")
        bet_date = st.date_input("投注日期", value=datetime.date.today())
        bet_amount = st.number_input("下单金额(元)（单个彩民）", min_value=1.0, step=1.0)
        play_type = st.selectbox("玩法", ["二串一", "总进球"])
        given_odds = st.number_input("给彩民赔率", min_value=1.0, max_value=100.0, value=2.0, step=0.1)
        official_odds = st.number_input("体彩实际赔付赔率", min_value=1.0, max_value=3.0, value=1.5, step=0.01)
        commission = st.number_input("体彩提成（例如0.05代表5%）", min_value=0.0, max_value=0.08, value=0.05, step=0.001)
        is_win = st.selectbox("是否中奖", ["否", "是"])
        num_bettors = st.number_input("彩民数量", min_value=1, value=30, step=1)

        if st.button("保存记录", key="save_record"):
            new_date = bet_date.strftime("%Y-%m-%d")
            new_record = {
                "日期": new_date,
                "组别": selected_group,  # 新增组别字段
                "下单金额": bet_amount,  # 单个彩民投注金额
                "玩法": play_type,
                "给彩民赔率": given_odds,
                "体彩实际赔付赔率": official_odds,
                "体彩提成": commission,
                "是否中奖": is_win,
                "彩民数量": num_bettors  # 新增字段
            }
            # 检查是否已有同一日期、同一组别的记录；若有则覆盖更新，否则追加
            record_updated = False
            for idx, rec in enumerate(st.session_state['records']):
                if rec.get("日期") == new_date and rec.get("组别") == selected_group:
                    st.session_state['records'][idx] = new_record
                    record_updated = True
                    break
            if not record_updated:
                st.session_state['records'].append(new_record)
            if record_updated:
                st.success(f"【{selected_group}】日期 {new_date} 的记录已覆盖更新！")
            else:
                st.success(f"【{selected_group}】新记录已保存到内存！")

            # 写回 Excel：仅保存当前组的数据到独立文件
            df_all = pd.DataFrame([r for r in st.session_state['records'] if r.get("组别") == selected_group])
            group_excel_file = f"{base_excel_file}_{selected_group}.xlsx"
            df_all.to_excel(group_excel_file, index=False, engine='openpyxl')
            st.info(f"【{selected_group}】数据已写入 {group_excel_file}")

    # ========= 2. 统计部分 =========
    # 分析当前选中组别的记录
    df = pd.DataFrame([r for r in st.session_state['records'] if r.get("组别") == selected_group])
    if df.empty:
        st.warning(f"【{selected_group}】暂无投注记录，无法统计。")
        return

    # 确保“彩民数量”列存在，否则默认设置为30
    if '彩民数量' not in df.columns:
        df['彩民数量'] = 30

    # 盈亏计算函数：
    # 若中奖：
    #   每个彩民盈亏 = (下单金额 × 给彩民赔率 - 下单金额)
    #   店主盈亏 = [下单金额 × (体彩实际赔付赔率 - 给彩民赔率)] + (下单金额 × 体彩提成)
    #   最后均乘以彩民数量
    # 若未中奖：
    #   每个彩民盈亏 = -下单金额
    #   店主盈亏 = 下单金额 × 体彩提成
    def calc_profits(row):
        bet = row['下单金额']
        given_odds = row.get('给彩民赔率', 2.0)
        official_odds = row.get('体彩实际赔付赔率', 1.0)
        commission = row.get('体彩提成', 0)
        win_flag = row['是否中奖']
        num = row.get('彩民数量', 30)
        if win_flag == '是':
            user_profit = (bet * given_odds - bet) * num
            host_profit = (bet * (official_odds - given_odds) + bet * commission) * num
        else:
            user_profit = -bet * num
            host_profit = bet * commission * num
        return pd.Series([user_profit, host_profit])

    df[['彩民盈亏', '店主盈亏']] = df.apply(calc_profits, axis=1)

    # ========= 3. 统计指标 =========
    total_bet_amount = (df['下单金额'] * df['彩民数量']).sum()
    total_user_profit = df['彩民盈亏'].sum()
    mask_total_goals = (df['玩法'] == '总进球')
    user_profit_total_goals = df.loc[mask_total_goals, '彩民盈亏'].sum()
    mask_erchuanyi = (df['玩法'] == '二串一')
    user_profit_erchuanyi = df.loc[mask_erchuanyi, '彩民盈亏'].sum()

    erchuanyi_count = df[mask_erchuanyi].shape[0]
    erchuanyi_win_count = df[mask_erchuanyi & (df['是否中奖'] == '是')].shape[0]
    erchuanyi_win_rate = erchuanyi_win_count / erchuanyi_count if erchuanyi_count > 0 else 0

    total_goals_count = df[mask_total_goals].shape[0]
    total_goals_win_count = df[mask_total_goals & (df['是否中奖'] == '是')].shape[0]
    total_goals_win_rate = total_goals_win_count / total_goals_count if total_goals_count > 0 else 0

    host_profit_total_goals = df.loc[mask_total_goals, '店主盈亏'].sum()
    host_profit_erchuanyi = df.loc[mask_erchuanyi, '店主盈亏'].sum()
    host_profit_total = df['店主盈亏'].sum()

    # 计算单个彩民盈亏情况 = 总彩民盈亏 / 总彩民数量
    total_bettors = df['彩民数量'].sum()
    single_bettor_profit = total_user_profit / total_bettors if total_bettors > 0 else 0

    # ========= 4. 构造四列表格展示统计指标 =========
    table_data = [
        ["彩民累计下单金额", f"{total_bet_amount:.2f} 元", "二串一中奖率", f"{erchuanyi_win_rate * 100:.2f}%"],
        ["彩民累计盈亏情况", f"{total_user_profit:.2f} 元", "总进球中奖率", f"{total_goals_win_rate * 100:.2f}%"],
        ["彩民总进球盈亏情况", f"{user_profit_total_goals:.2f} 元", "总进球盈亏情况",
         f"{host_profit_total_goals:.2f} 元"],
        ["彩民二串一盈亏情况", f"{user_profit_erchuanyi:.2f} 元", "二串一盈亏情况", f"{host_profit_erchuanyi:.2f} 元"],
        ["单个彩民盈亏情况", f"{single_bettor_profit:.2f} 元", "总盈利情况", f"{host_profit_total:.2f} 元"]
    ]
    df_table = pd.DataFrame(
        table_data,
        columns=["彩民端项目", "彩民端数据", "店主端项目", "店主端数据"]
    )

    # ========= 5. 在右侧展示统计指标总览与明细 =========
    with col_right:
        st.markdown("### 统计指标总览（4 列）")
        st.table(df_table)

        st.markdown("---")
        st.markdown("### 明细记录（含盈亏列）")
        st.dataframe(df)


if __name__ == "__main__":
    main()
