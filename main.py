# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import MousePosition
from branca.colormap import LinearColormap

st.set_page_config(page_title="서울 자치구 청소년 인구 비율 대시보드", layout="wide")
st.title("🗺️ 서울 자치구 청소년 인구 비율 대시보드")

@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/shine122948/dataproject3/main/studentPopulation.csv"
    df = pd.read_csv(url)
    st.write("🔍 CSV 열 이름:", df.columns.tolist())
    
    # 열 이름 정리
    df = df.rename(columns={
        '자치구별': '자치구',
        '총인구 (명)': '총인구',
        '9세-24세 (명)': '청소년인구'
    })
    
    # 청소년 비율 계산
    df['청소년비율(%)'] = df['청소년인구'] / df['총인구'] * 100
    
    return df

df = load_data()

# 표시
st.subheader("📊 서울 자치구별 청소년 인구 현황")
st.dataframe(df)

# 막대그래프
fig = px.bar(
    df,
    x="자치구",
    y="청소년비율(%)",
    title="서울 자치구별 청소년 인구 비율(%)",
    text_auto=".2f"
)
st.plotly_chart(fig, use_container_width=True)

# 지도 시각화
st.subheader("🗺️ 자치구별 청소년 인구 비율 지도")

# 지도 중심 (서울 중심 좌표)
m = folium.Map(location=[37.5665, 126.9780], zoom_start=11)

colormap = LinearColormap(
    colors=['#e0f3f8', '#abd9e9', '#74add1', '#4575b4'],
    vmin=df['청소년비율(%)'].min(),
    vmax=df['청소년비율(%)'].max(),
    caption="청소년 인구 비율(%)"
)

for _, row in df.iterrows():
    tooltip = f"{row['자치구']}: {row['청소년비율(%)']:.2f}%"
    folium.CircleMarker(
        location=[37.5665 + (hash(row['자치구']) % 100 - 50) * 0.001, 126.9780 + (hash(row['자치구']) % 100 - 50) * 0.001],
        radius=8,
        color=colormap(row['청소년비율(%)']),
        fill=True,
        fill_opacity=0.8,
        tooltip=tooltip
    ).add_to(m)

colormap.add_to(m)
MousePosition().add_to(m)
st_folium(m, width=1000, height=600)
