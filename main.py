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

# ✅ GitHub CSV URL
CSV_URL = "https://raw.githubusercontent.com/your-username/your-repo/main/studentPopulation.csv"

@st.cache_data
def load_csv_from_github(url):
    try:
        df = pd.read_csv(url, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(url, encoding='cp949')
    return df

@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

# CSV 불러오기
df = load_csv_from_github(CSV_URL)

# ✅ 컬럼명 자동 감지
cols = df.columns.tolist()
if '자치구' not in cols:
    # '자치구별(2)' 등 변형 대응
    for c in cols:
        if '자치구' in c:
            df = df.rename(columns={c: '자치구'})
            break

# 비율 컬럼 자동 탐색
ratio_cols = [c for c in df.columns if '%' in c or '비율' in c or '구성비' in c]
metric = ratio_cols[0] if ratio_cols else df.columns[-1]

# 숫자형으로 변환
df[metric] = pd.to_numeric(df[metric], errors='coerce')
df = df.dropna(subset=[metric])
df = df[~df['자치구'].str.contains('소계|합계')]

# 선택된 지표 표시
st.sidebar.header("지표 선택")
metric = st.sidebar.selectbox("시각화할 지표", options=ratio_cols, index=0 if ratio_cols else 0)

# 선택된 자치구
target_gu = st.sidebar.selectbox("자치구 강조 선택", options=df['자치구'].tolist(), index=0)

# 지도 시각화
geoj = load_geojson()
vmin, vmax = float(df[metric].min()), float(df[metric].max())
cmap = LinearColormap(colors=["#ffeaea", "#ff8080", "#ff1a1a", "#d30000"], vmin=vmin, vmax=vmax)
cmap.caption = f"{metric} (높을수록 빨강)"

value_map = dict(zip(df['자치구'], df[metric]))
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
plot_df = df.sort_values(metric, ascending=False)
colors = ["#d30000" if g == target_gu else "#4da6ff" for g in plot_df["자치구"]]
fig = px.bar(plot_df, x="자치구", y=metric, title=f"{metric} (자치구 비교)")
fig.update_traces(marker_color=colors)
fig.update_layout(xaxis_title="자치구", yaxis_title=metric, height=520)
st.plotly_chart(fig, use_container_width=True)

# 데이터 미리보기
with st.expander("데이터 미리보기"):
    st.dataframe(df, use_container_width=True)

st.caption("📊 CSV 출처: GitHub 리포지토리 / GeoJSON 출처: southkorea/seoul-maps")
