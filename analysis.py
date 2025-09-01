import pandas as pd
import glob
import os
import streamlit as st
import altair as alt
from datetime import datetime
import re

# データ取得と前処理をキャッシュする関数
# force_regenerate が True の場合、またはファイルが存在しない場合にのみ実行される
@st.cache_data
def get_data(force_regenerate=False):
    output_filename = 'mf_all_data.csv'
    csv_dir = 'csv'

    # 再生成が必要かどうかを判断
    regenerate = force_regenerate or not os.path.exists(output_filename)

    if regenerate:
        st.info(f"`{csv_dir}` ディレクトリのCSVから {output_filename} を生成・更新します...")
        if not os.path.isdir(csv_dir):
            st.error(f"ディレクトリ '{csv_dir}' が見つかりません。")
            return None
            
        csv_pattern = os.path.join(csv_dir, '*.csv')
        csv_files = glob.glob(csv_pattern)
        csv_files.sort()

        if not csv_files:
            st.error(f"{csv_dir} ディレクトリにCSVファイルが見つかりません。")
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
    else:
        st.info(f"既存の {output_filename} を読み込みます。")

    # ファイルからデータを読み込む
    try:
        df = pd.read_csv(output_filename)
    except FileNotFoundError:
        # このケースは基本的には発生しないはずだが、念のため
        st.error(f"{output_filename} が見つかりません。")
        return None

    # データの後処理
    df = df[(df['計算対象'] == 1) & (df['振替'] == 0)]
    df['日付'] = pd.to_datetime(df['日付'])
    df = df[pd.to_numeric(df['金額（円）'], errors='coerce').notnull()]
    df['金額（円）'] = df['金額（円）'].astype(int)
    return df

def main():
    st.set_page_config(layout="wide")
    st.title('家計分析ダッシュボード')

    output_filename = 'mf_all_data.csv'

    st.sidebar.header('データ操作')
    force_regenerate = st.sidebar.button('`mf_all_data.csv` を生成・更新')

    # ファイルが存在せず、再生成ボタンも押されていない場合はメッセージを表示
    if not os.path.exists(output_filename) and not force_regenerate:
        st.info('データファイル `mf_all_data.csv` が見つかりません。サイドバーの「`mf_all_data.csv` を生成・更新」ボタンを押して、`csv/` ディレクトリからデータを生成してください。')
        return

    # ボタンが押されたらキャッシュをクリアして get_data を再実行
    if force_regenerate:
        st.cache_data.clear()

    df = get_data(force_regenerate=force_regenerate)
    
    if df is None:
        # get_data 内でエラーが発生した場合
        return

    st.sidebar.header('フィルター')
    
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

    # --- 分析モード選択 ---
    st.sidebar.markdown("---")
    analysis_mode = st.sidebar.selectbox('分析対象を選択', ['支出', '収入'])

    if analysis_mode == '支出':
        analysis_df = expenses_df
        subject_title = "支出"
    else:
        analysis_df = income_df
        subject_title = "収入"

    # --- 内訳分析 --- 
    st.header(f'{subject_title}の割合')
    if not analysis_df.empty:
        all_major_categories = list(analysis_df['大項目'].unique())
        default_selected_categories = all_major_categories # デフォルトで全て選択

        selected_pie_categories = st.multiselect(
            f'円グラフに含める{subject_title}の大項目を選択',
            all_major_categories,
            default=default_selected_categories
        )

        if selected_pie_categories:
            pie_chart_df = analysis_df[analysis_df['大項目'].isin(selected_pie_categories)]
            category_data = pie_chart_df.groupby('大項目')['金額（円）'].sum().sort_values(ascending=False).reset_index()

            if not category_data.empty:
                pie_chart = alt.Chart(category_data).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="金額（円）", type="quantitative"),
                    color=alt.Color(field="大項目", type="nominal", title="カテゴリ"),
                    tooltip=['大項目', '金額（円）']
                ).properties(
                    width=500,
                    height=350
                )
                st.altair_chart(pie_chart, use_container_width=True)
            else:
                st.write(f"選択されたカテゴリの{subject_title}データはありません。")
        else:
            st.write(f"円グラフに表示する{subject_title}の大項目を1つ以上選択してください。")
    else:
        st.write(f"この期間の{subject_title}データはありません。")

    st.header(f'{subject_title}のドリルダウン分析')
    if not analysis_df.empty:
        major_categories = list(analysis_df['大項目'].unique())
        selected_major_categories = st.multiselect(f'分析したい{subject_title}の大項目を選択（複数選択可）', major_categories)

        if selected_major_categories:
            drilldown_df = analysis_df[analysis_df['大項目'].isin(selected_major_categories)]
            title_categories = ", ".join(selected_major_categories)
            st.subheader(f'「{title_categories}」の中項目別{subject_title}')
        else:
            drilldown_df = analysis_df
            st.subheader(f'すべての中項目別{subject_title}')

        sub_category_data = drilldown_df.groupby('中項目')['金額（円）'].sum().sort_values(ascending=False)
        st.bar_chart(sub_category_data)

        if selected_major_categories:
            st.write(f"「{title_categories}」の明細データ")
        else:
            st.write("すべての明細データ")
        st.dataframe(drilldown_df[['日付', '内容', '金額（円）', '中項目']].sort_values('日付', ascending=False), use_container_width=True)
    else:
        st.write(f"表示する{subject_title}データはありません。")

if __name__ == "__main__":
    main()
