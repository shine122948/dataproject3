import streamlit as st
import pandas as pd
import numpy as np
import requests
import folium
from folium.plugins import MousePosition
from branca.colormap import LinearColormap
from streamlit_folium import st_folium
import plotly.express as px

st.set_page_config(page_title="서울 자치구 청소년 인구 비율 대시보드", layout="wide")
st.title("🗺️ 서울 자치구 청소년 인구 비율 대시보드")
st.caption("CSV는 GitHub에서 직접 불러옵니다. 자치구별 청소년 인구 비율을 분석합니다.")

# GitHub RAW CSV URL – 실제 파일명/경로 확인 후 변경하세요
CSV_URL = "https://raw.githubusercontent.com/shine122948/dataproject3/main/studentPopulation.csv"

@st.cache_data
def load_csv_from_github(url):
    try:
        df = pd.read_csv(url, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(url, encoding='cp949')
    # 컬럼명 정리: 앞뒤 공백 제거, BOM 제거
    df.columns = df.columns.str.strip().str.replace('\ufeff', '', regex=True)
    return df

@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

df = load_csv_from_github(CSV_URL)

# 열 목록 출력해서 확인
st.write("### CSV 열 목록:", df.columns.tolist())

# 자치구 컬럼 자동 탐색 및 이름 통일
if '자치구' not in df.columns:
    for c in df.columns:
        if '자치구' in c:
            df = df.rename(columns={c: '자치구'})
            break

# 비율(%) 컬럼 탐색
ratio_cols = [c for c in df.columns if ('구성비' in c) or ('비율' in c) or ('%' in c)]
if not ratio_cols:
    st.error("적절한 비율(%) 컬럼을 찾을 수 없습니다. CSV의 열명을 확인해주세요.")
    st.stop()

# 기본 지표 선택
default_metric = ratio_cols[0]

st.sidebar.header("지표 선택")
metric = st.sidebar.selectbox("시각화할 지표", options=ratio_cols, index=0 if default_metric in ratio_cols else 0)
target_gu = st.sidebar.selectbox("자치구 강조 선택", options=df['자치구'].dropna().unique().tolist(), index=0)

# 숫자 변환 및 데이터 정리
df[metric] = pd.to_numeric(df[metric].astype(str).str.replace(',', ''), errors='coerce')
work = df[['자치구', metric]].dropna(subset=[metric])
work = work[~work['자치구'].str.contains('합계|소계', na=False)]
work = work.reset_index(drop=True)

geoj = load_geojson()

vmin, vmax = float(work[metric].min()), float(work[metric].max())
cmap = LinearColormap(colors=["#ffeaea", "#ff8080", "#ff1a1a", "#d30000"], vmin=vmin, vmax=vmax)
cmap.caption = f"{metric} (높을수록 빨강)"

value_map = dict(zip(work['자치구'], work[metric]))

m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="cartodbpositron")

folium.GeoJson(
    geoj,
    name="서울 자치구",
    style_function=lambda f: {
        "fillColor": cmap(value_map.get(f["properties"]["name"], vmin)),
        "color": "white",
        "weight": 1,
        "fillOpacity": 0.8,
    },
    tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["자치구"]),
).add_to(m)

MousePosition().add_to(m)
st_folium(m, height=560, use_container_width=True)

# 막대그래프
plot_df = work.sort_values(metric, ascending=False)
colors = ['#d30000' if gu == target_gu else '#4da6ff' for gu in plot_df['자치구']]
fig = px.bar(plot_df, x='자치구', y=metric, title=f"{metric} (자치구 비교)")
fig.update_traces(marker_color=colors)
fig.update_layout(xaxis_title="자치구", yaxis_title=metric, height=520)
st.plotly_chart(fig, use_container_width=True)

with st.expander("데이터 미리보기"):
    st.dataframe(work, use_container_width=True)

st.caption("📊 CSV 출처: GitHub 리포지토리 / GeoJSON 출처: southkorea/seoul-maps")
