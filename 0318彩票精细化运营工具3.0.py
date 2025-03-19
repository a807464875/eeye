import streamlit as st
import pandas as pd
import datetime
import os

# 宽屏模式
st.set_page_config(layout="wide")


def main():
    # 使用 HTML 居中标题
    st.markdown("""
           <h1 style="text-align: center;">
               体彩店主精细化运营工具
           </h1>
       """, unsafe_allow_html=True)

    st.markdown("#### （同一日期数据覆盖，含体彩提成等）")

    # 修改 Excel 文件存储路径
    if 'records' not in st.session_state:
        st.session_state['records'] = []
    
    # 使用 Streamlit 的文件上传功能
    uploaded_file = st.file_uploader("上传现有记录(Excel文件)", type=['xlsx'])
    if uploaded_file is not None:
        df_init = pd.read_excel(uploaded_file, engine='openpyxl')
        st.session_state['records'] = df_init.to_dict('records')
        st.success(f"已加载 {len(st.session_state['records'])} 条记录")

    # 两列布局：左侧输入，右侧展示结果
    col_left, col_right = st.columns([1, 3])  # 左列宽度1, 右列宽度3

    # ========= 1. 左侧：录入新投注记录 =========
    with col_left:
        st.subheader("录入新投注")
        bet_date = st.date_input("投注日期", value=datetime.date.today())
        bet_amount = st.number_input("下单金额(元)", min_value=1.0, step=1.0)
        play_type = st.selectbox("玩法", ["二串一", "总进球"])
        given_odds = st.number_input("给彩民赔率", min_value=1.0, max_value=100.0, value=2.0, step=0.1)
        official_odds = st.number_input("体彩实际赔付赔率", min_value=1.0, max_value=3.0, value=1.5, step=0.01)
        commission = st.number_input("体彩提成（例如0.05代表5%）", min_value=0.0, max_value=0.08, value=0.05, step=0.001)
        is_win = st.selectbox("是否中奖", ["否", "是"])

        if st.button("保存记录", key="save_record"):
            new_date = bet_date.strftime("%Y-%m-%d")
            new_record = {
                "日期": new_date,
                "下单金额": bet_amount,
                "玩法": play_type,
                "给彩民赔率": given_odds,
                "体彩实际赔付赔率": official_odds,
                "体彩提成": commission,
                "是否中奖": is_win
            }
            # 检查是否已有同一日期的记录；若有则覆盖，否则追加
            record_updated = False
            for idx, rec in enumerate(st.session_state['records']):
                if rec.get("日期") == new_date:
                    st.session_state['records'][idx] = new_record
                    record_updated = True
                    break
            if not record_updated:
                st.session_state['records'].append(new_record)
            if record_updated:
                st.success(f"日期 {new_date} 的记录已覆盖更新！")
            else:
                st.success("新记录已保存到内存！")

            # 修改保存逻辑，改为下载文件
            if st.button("导出数据"):
                df_all = pd.DataFrame(st.session_state['records'])
                # 转换为 Excel
                output = pd.ExcelWriter('bet_records.xlsx', engine='openpyxl')
                df_all.to_excel(output, index=False)
                output.save()
                
                with open('bet_records.xlsx', 'rb') as f:
                    st.download_button(
                        label="下载 Excel 文件",
                        data=f,
                        file_name='bet_records.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )

    # 若没有记录，停止后续统计
    if len(st.session_state['records']) == 0:
        st.warning("暂无投注记录，无法统计。")
        return

    # ========= 2. 计算盈亏统计 =========
    df = pd.DataFrame(st.session_state['records'])

    # 盈亏计算函数（示例：中奖时，店主盈亏 = [下单金额*(体彩实际赔率-给彩民赔率)]*(1-提成)，未中则店主盈亏 = 下单金额*提成）
    def calc_profits(row):
        bet = row['下单金额']
        given_odds = row.get('给彩民赔率', 2.0)
        official_odds = row.get('体彩实际赔付赔率', 1.0)
        commission = row.get('体彩提成', 0)
        win_flag = row['是否中奖']
        if win_flag == '是':
            user_profit = bet * given_odds - bet
            host_profit = (bet * (official_odds - given_odds)) * (1 - commission)
        else:
            user_profit = -bet
            host_profit = bet * commission
        return pd.Series([user_profit, host_profit])

    df[['彩民盈亏', '店主盈亏']] = df.apply(calc_profits, axis=1)

    # 统计指标
    # 彩民端
    total_bet_amount = df['下单金额'].sum()
    total_user_profit = df['彩民盈亏'].sum()
    mask_total_goals = (df['玩法'] == '总进球')
    user_profit_total_goals = df.loc[mask_total_goals, '彩民盈亏'].sum()
    mask_erchuanyi = (df['玩法'] == '二串一')
    user_profit_erchuanyi = df.loc[mask_erchuanyi, '彩民盈亏'].sum()

    # 店主端
    erchuanyi_count = df[mask_erchuanyi].shape[0]
    erchuanyi_win_count = df[mask_erchuanyi & (df['是否中奖'] == '是')].shape[0]
    erchuanyi_win_rate = erchuanyi_win_count / erchuanyi_count if erchuanyi_count > 0 else 0

    total_goals_count = df[mask_total_goals].shape[0]
    total_goals_win_count = df[mask_total_goals & (df['是否中奖'] == '是')].shape[0]
    total_goals_win_rate = total_goals_win_count / total_goals_count if total_goals_count > 0 else 0

    host_profit_total_goals = df.loc[mask_total_goals, '店主盈亏'].sum()
    host_profit_erchuanyi = df.loc[mask_erchuanyi, '店主盈亏'].sum()
    host_profit_total = df['店主盈亏'].sum()

    # ========= 3. 在右侧显示"4列表格"与明细 =========
    with col_right:
        st.markdown("### 统计指标总览（4 列）")
        # 组装表格数据：彩民端2列、店主端2列
        table_data = [
            ["彩民累计下单金额", f"{total_bet_amount:.2f} 元", "二串一中奖率", f"{erchuanyi_win_rate * 100:.2f}%"],
            ["彩民累计盈亏情况", f"{total_user_profit:.2f} 元", "总进球中奖率", f"{total_goals_win_rate * 100:.2f}%"],
            ["彩民总进球盈亏情况", f"{user_profit_total_goals:.2f} 元", "总进球盈亏情况",
             f"{host_profit_total_goals:.2f} 元"],
            ["彩民二串一盈亏情况", f"{user_profit_erchuanyi:.2f} 元", "二串一盈亏情况",
             f"{host_profit_erchuanyi:.2f} 元"],
            ["", "", "总盈利情况", f"{host_profit_total:.2f} 元"]
        ]
        df_table = pd.DataFrame(
            table_data,
            columns=["彩民端项目", "彩民端数据", "店主端项目", "店主端数据"]
        )
        st.table(df_table)

        st.markdown("---")
        st.markdown("### 明细记录（含盈亏列）")
        st.dataframe(df)


if __name__ == "__main__":
    main()
