import streamlit as st
import pandas as pd
import folium
from folium.plugins import MousePosition
from branca.colormap import LinearColormap
from streamlit_folium import st_folium
import plotly.express as px
import requests

st.set_page_config(page_title="서울 자치구별 청소년 인구 비율 대시보드", layout="wide")

st.title("🗺️ 서울 자치구별 청소년 인구 비율 대시보드")
st.caption("서울 각 자치구의 청소년 인구 구성비를 시각화합니다. (데이터 출처: dataproject3 깃허브 저장소)")

# 🔹 CSV 불러오기 (GitHub raw URL)
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/shine122948/dataproject3/refs/heads/main/requirements.txt"
    # 위 <YOUR_GITHUB_USERNAME> 부분을 본인 깃허브 ID로 바꿔주세요.
    st.write("🔍 CSV 열 이름:", df.columns.tolist())

    try:
        df = pd.read_csv(url)
    except UnicodeDecodeError:
        df = pd.read_csv(url, encoding='utf-8-sig')

    # 통계청 형식 (상단 2행 헤더) 정리
    df = df.iloc[2:].copy()
    df.rename(columns={'자치구별': '자치구'}, inplace=True)
    df = df[df['자치구'].notna() & (df['자치구'] != '소계')]
    df['자치구'] = df['자치구'].astype(str).str.strip()
    df['청소년비율(%)'] = pd.to_numeric(df['2024.2'], errors='coerce')  # 9~24세 구성비
    return df[['자치구', '청소년비율(%)']]

df = load_data()

# 🔹 GeoJSON 불러오기
@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    r = requests.get(url)
    return r.json()

geo = load_geojson()

# 🔹 지도 표시
st.subheader("🌍 서울 자치구별 청소년 인구 비율 (Folium 지도)")

vmin, vmax = df['청소년비율(%)'].min(), df['청소년비율(%)'].max()
cmap = LinearColormap(
    colors=["#ffeaea", "#ffb3b3", "#ff8080", "#ff4d4d", "#ff1a1a", "#d30000"],
    vmin=vmin, vmax=vmax
)
cmap.caption = "청소년 인구 비율 (%)"

m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="cartodbpositron")

value_map = dict(zip(df['자치구'], df['청소년비율(%)']))

folium.GeoJson(
    geo,
    name="서울 자치구",
    style_function=lambda feature: {
        "fillColor": cmap(value_map.get(feature["properties"]["name"], vmin)),
        "color": "white",
        "weight": 1,
        "fillOpacity": 0.8,
    },
    tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["자치구"], labels=True),
).add_to(m)

MousePosition().add_to(m)
st_folium(m, height=600, use_container_width=True)

# 🔹 막대그래프 (Plotly)
st.subheader("📊 자치구별 청소년 인구 비율 (Bar Chart)")

df_sorted = df.sort_values("청소년비율(%)", ascending=False)
colors = ["#d30000" if i == 0 else "#ff8080" for i in range(len(df_sorted))]

fig = px.bar(
    df_sorted,
    x="자치구",
    y="청소년비율(%)",
    color="청소년비율(%)",
    color_continuous_scale="Reds",
    title="서울 자치구별 청소년 인구 비율 (%)",
)
fig.update_layout(xaxis_title="자치구", yaxis_title="청소년 인구 비율 (%)", height=500)
st.plotly_chart(fig, use_container_width=True)

# 🔹 데이터 미리보기
with st.expander("데이터 미리보기"):
    st.dataframe(df)
