import pandas as pd
import glob
import os
import streamlit as st
import altair as alt
from datetime import datetime

@st.cache_data
def get_data():
    output_filename = 'mf_all_data.csv'
    if not os.path.exists(output_filename):
        st.error(f"{output_filename} not found. Please run the initial script to generate it.")
        return None
    
    df = pd.read_csv(output_filename)
    # Basic data cleaning and preparation
    df = df[(df['計算対象'] == 1) & (df['振替'] == 0)]
    df['日付'] = pd.to_datetime(df['日付'])
    df = df[pd.to_numeric(df['金額（円）'], errors='coerce').notnull()]
    df['金額（円）'] = df['金額（円）'].astype(int)
    return df

def main():
    st.set_page_config(layout="wide")
    st.title('家計分析ダッシュボード')

    df = get_data()
    if df is None:
        return

    # --- Sidebar Filters ---
    st.sidebar.header('フィルター')
    min_date = df['日付'].min().date()
    max_date = df['日付'].max().date()

    start_date = st.sidebar.date_input('開始日', min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input('終了日', max_date, min_value=min_date, max_value=max_date)

    if start_date > end_date:
        st.sidebar.error('エラー: 終了日は開始日以降に設定してください。')
        return

    # --- Data Filtering ---
    filtered_df = df[(df['日付'].dt.date >= start_date) & (df['日付'].dt.date <= end_date)]
    title_period = f"{start_date.strftime('%Y/%m/%d')} - {end_date.strftime('%Y/%m/%d')}"

    st.header(f'{title_period}の概要')

    # Separate income and expenses
    income_df = filtered_df[filtered_df['金額（円）'] > 0]
    expenses_df = filtered_df[filtered_df['金額（円）'] < 0].copy()
    expenses_df['金額（円）'] = expenses_df['金額（円）'].abs()

    total_income = income_df['金額（円）'].sum()
    total_expense = expenses_df['金額（円）'].sum()
    balance = total_income - total_expense

    col1, col2, col3 = st.columns(3)
    col1.metric("総収入", f"{total_income:,.0f} 円")
    col2.metric("総支出", f"{total_expense:,.0f} 円")
    col3.metric("収支", f"{balance:,.0f} 円")

    # --- Category Pie Chart ---
    st.header('支出の割合')
    category_expenses = expenses_df.groupby('大項目')['金額（円）'].sum().sort_values(ascending=False).reset_index()
    if not category_expenses.empty:
        pie_chart = alt.Chart(category_expenses).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="金額（円）", type="quantitative"),
            color=alt.Color(field="大項目", type="nominal", title="カテゴリ"),
            tooltip=['大項目', '金額（円）']
        ).properties(
            width=500,
            height=350
        )
        st.altair_chart(pie_chart, use_container_width=True)
    else:
        st.write("この期間の支出データはありません。")

    # --- Drill-down Analysis ---
    st.header('ドリルダウン分析')
    if not expenses_df.empty:
        major_categories = ['すべてのカテゴリ'] + list(expenses_df['大項目'].unique())
        selected_major_category = st.selectbox('分析したい大項目を選択', major_categories)

        if selected_major_category != 'すべてのカテゴリ':
            drilldown_df = expenses_df[expenses_df['大項目'] == selected_major_category]
        else:
            drilldown_df = expenses_df

        st.subheader(f'「{selected_major_category}」の中項目別支出')
        sub_category_expenses = drilldown_df.groupby('中項目')['金額（円）'].sum().sort_values(ascending=False)
        st.bar_chart(sub_category_expenses)

        st.write(f"「{selected_major_category}」の明細データ")
        st.dataframe(drilldown_df[['日付', '内容', '金額（円）', '中項目']].sort_values('日付', ascending=False), use_container_width=True)
    else:
        st.write("表示する支出データはありません。")

    # --- Time Series Analysis ---
    st.header('期間内の推移')
    time_unit = 'Y' # Default to year
    time_delta = end_date - start_date
    if time_delta.days <= 90:
        time_unit = 'D' # Day
    elif time_delta.days <= 365 * 2:
        time_unit = 'M' # Month

    if not filtered_df.empty:
        income_ts = income_df.set_index('日付').resample(time_unit)['金額（円）'].sum()
        expense_ts = expenses_df.set_index('日付').resample(time_unit)['金額（円）'].sum()
        ts_chart_data = pd.DataFrame({'収入': income_ts, '支出': expense_ts}).fillna(0)
        st.bar_chart(ts_chart_data)

if __name__ == "__main__":
    main()