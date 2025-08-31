import pandas as pd
import glob
import os
import streamlit as st
import altair as alt
from datetime import datetime
import re

@st.cache_data
def get_data():
    output_filename = 'mf_all_data.csv'
    
    regenerate_csv = True
    if os.path.exists(output_filename):
        try:
            temp_df = pd.read_csv(output_filename, nrows=0)
            if '集計期間' in temp_df.columns:
                regenerate_csv = False
        except pd.errors.EmptyDataError:
            regenerate_csv = True

    if not regenerate_csv:
        st.info(f"既存の {output_filename} を読み込みます。")
        df = pd.read_csv(output_filename)
    else:
        st.info(f"{output_filename} を再生成します...")
        csv_dir = 'csv'
        csv_pattern = os.path.join(csv_dir, '*.csv')
        csv_files = glob.glob(csv_pattern)
        csv_files.sort()

        if not csv_files:
            st.error("csvディレクトリにファイルが見つかりません。")
            return None

        df_list = []
        for file in csv_files:
            try:
                df_chunk = pd.read_csv(file, encoding='cp932')
                match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{4}-\d{2}-\d{2})', os.path.basename(file))
                if match:
                    df_chunk['集計期間'] = match.group(1)
                else:
                    df_chunk['集計期間'] = '不明'
                df_list.append(df_chunk)
            except Exception as e:
                st.warning(f"ファイル {file} の読み込み中にエラー: {e}")

        if not df_list:
            st.error("有効なデータが読み込めませんでした。")
            return None

        first_df_cols = df_list[0].columns.tolist()
        cols = ['集計期間'] + [col for col in first_df_cols if col != '集計期間']
        
        reordered_df_list = []
        for df_item in df_list:
             reordered_df_list.append(df_item.reindex(columns=cols))
        
        df = pd.concat(reordered_df_list, ignore_index=True)
        df.to_csv(output_filename, index=False, encoding='utf-8')
        st.success(f"新しい {output_filename} が生成されました。")

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

    st.sidebar.header('フィルター')
    
    # --- New: Filter by '集計期間' ---
    period_options = ['全期間'] + sorted(df['集計期間'].unique().tolist(), reverse=True)
    selected_period = st.sidebar.selectbox('集計期間を選択', period_options)

    if selected_period == '全期間':
        filtered_df = df
        title_period = '全期間'
    else:
        filtered_df = df[df['集計期間'] == selected_period]
        title_period = selected_period

    st.header(f'{title_period}の概要')

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

if __name__ == "__main__":
    main()
