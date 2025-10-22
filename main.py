
import streamlit as st
import pandas as pd
import numpy as np
import json
import requests
import folium
from folium.plugins import MousePosition
from branca.colormap import LinearColormap
from streamlit_folium import st_folium
import plotly.express as px

st.set_page_config(page_title="서울 자치구 청소년 인구 비율 대시보드", layout="wide")

st.title("🗺️ 서울 자치구 청소년 인구 비율 대시보드")
st.caption("CSV 형식: 통계청/서울시 포맷(예: '자치구별(2)' 열과 '구성비(%)' 열 포함). 이 앱은 업로드 또는 기본 예시 CSV를 파싱해 동작합니다.")

@st.cache_data
def load_csv(file):
    if file is None:
        st.info("좌측 사이드바에서 CSV를 업로드해주세요. (예: studentPopulation.csv)")
        return None

    try:
        df = pd.read_csv(file)
    except UnicodeDecodeError:
        file.seek(0)
        df = pd.read_csv(file, encoding="cp949")

    cols = df.columns.tolist()
    if '자치구별(2)' in cols and any('구성비' in str(x) for x in df.iloc[1].values):
        body = df.iloc[2:].copy().reset_index(drop=True)
        body.rename(columns={'자치구별(2)': '자치구'}, inplace=True)

        def to_num(s):
            try:
                return pd.to_numeric(str(s).replace(',', ''), errors='coerce')
            except Exception:
                return np.nan

        map_candidates = {
            '9-24세 구성비(%)': '2024.2',
            '0-18세 구성비(%)': '2024.4',
            '학령인구 구성비(%)': '2024.6',
        }
        clean = pd.DataFrame()
        clean['자치구'] = body['자치구']

        for new_col, old_col in map_candidates.items():
            if old_col in body.columns:
                clean[new_col] = body[old_col].apply(to_num)
            else:
                clean[new_col] = np.nan

        clean = clean[clean['자치구'].notna() & (clean['자치구'] != '소계') & (clean['자치구'] != '자치구별(2)')]
        clean['자치구'] = clean['자치구'].astype(str).str.strip()

        for c in ['9-24세 구성비(%)','0-18세 구성비(%)','학령인구 구성비(%)']:
            if clean[c].notna().any():
                default_metric = c
                break
        else:
            default_metric = None

        return clean, default_metric
    else:
        candidates = [c for c in cols if '자치구' in c]
        gu_col = candidates[0] if candidates else cols[0]
        ratio_candidates = [c for c in cols if '%' in c or '비율' in c or '구성비' in c]
        ratio_col = ratio_candidates[0] if ratio_candidates else cols[-1]

        df = df.rename(columns={gu_col: '자치구', ratio_col: '청소년비율(%)'})
        df['청소년비율(%)'] = pd.to_numeric(df['청소년비율(%)'], errors='coerce')
        df = df[df['자치구'].notna()]
        return df[['자치구', '청소년비율(%)']], '청소년비율(%)'

@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/southkorea/seoul-maps/master/kostat/2013/json/seoul_municipalities_geo_simple.json"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

with st.sidebar:
    st.header("데이터 업로드")
    up = st.file_uploader("자치구별 청소년 인구 CSV 업로드", type=["csv"])
    loaded = load_csv(up)
    st.markdown("—")
    st.header("지표 선택")
    if loaded is not None:
        df, default_metric = loaded
        metric_options = [c for c in df.columns if c != '자치구']
        # default_metric이 없을 때 안전 처리
        default_idx = metric_options.index(default_metric) if (default_metric in metric_options) else 0
        metric = st.selectbox("시각화할 지표", options=metric_options, index=default_idx)
    else:
        df, metric = None, None

if df is None or metric is None:
    st.stop()

work = df[['자치구', metric]].copy()
work = work.dropna(subset=[metric])
work[metric] = pd.to_numeric(work[metric], errors='coerce')
work = work.dropna(subset=[metric])
work = work[~work['자치구'].str.contains('합계|소계')]
work = work.sort_values(metric, ascending=False).reset_index(drop=True)

col_sel1, col_sel2 = st.columns([1,2])
with col_sel1:
    target_gu = st.selectbox("자치구 선택(막대 강조)", options=work['자치구'].tolist(), index=0)
with col_sel2:
    st.write("")

geoj = load_geojson()

vmin, vmax = float(work[metric].min()), float(work[metric].max())
cmap = LinearColormap(
    colors=["#ffeaea", "#ffb3b3", "#ff8080", "#ff4d4d", "#ff1a1a", "#d30000"],
    vmin=vmin, vmax=vmax
)
cmap.caption = f"{metric} (높을수록 빨강)"

value_map = dict(zip(work['자치구'], work[metric]))

m = folium.Map(location=[37.5665, 126.9780], zoom_start=11, tiles="cartodbpositron")

folium.GeoJson(
    geoj,
    name="서울 자치구",
    style_function=lambda feature: {
        "fillColor": cmap(value_map.get(feature["properties"]["name"], vmin)),
        "color": "white",
        "weight": 1,
        "fillOpacity": 0.8
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["name"],
        aliases=["자치구"],
        labels=True,
        sticky=False
    ),
    highlight_function=lambda x: {"weight": 3, "color": "#666", "fillOpacity": 0.9},
).add_to(m)

try:
    target_feat = next(f for f in geoj["features"] if f["properties"]["name"] == target_gu)
    coords = target_feat["geometry"]["coordinates"]
    def get_first_lonlat(c):
        if isinstance(c[0][0], (list, tuple)):
            lon, lat = c[0][0][0]
        else:
            lon, lat = c[0][0]
        return lat, lon
    lat, lon = get_first_lonlat(coords)
    folium.CircleMarker(location=(lat, lon), radius=8, color="#d30000", fill=True, fill_opacity=1).add_to(m)
    folium.map.Marker(
        (lat, lon),
        icon=folium.DivIcon(html=f"<div style='font-weight:700;color:#d30000;background:rgba(255,255,255,0.8);padding:2px 6px;border-radius:6px'>{target_gu}</div>")
    ).add_to(m)
except StopIteration:
    pass

MousePosition().add_to(m)
st_folium(m, height=560, use_container_width=True)
st.caption("지도 출처: southkorea/seoul-maps GeoJSON (GitHub)")

# 막대그래프
blues = px.colors.sequential.Blues
ranks = work[metric].rank(ascending=True, method='first')
rank_idx = (ranks - ranks.min()) / (ranks.max() - ranks.min() + 1e-9)
idx_scaled = (rank_idx * (len(blues)-1)).round().astype(int).clip(0, len(blues)-1)

colors = []
for gu, idx in zip(work['자치구'], idx_scaled):
    if gu == target_gu:
        colors.append('#d30000')
    else:
        colors.append(blues[int(idx)])

plot_df = work.sort_values(metric, ascending=False)
fig = px.bar(plot_df, x='자치구', y=metric, title=f"{metric} (자치구 비교)")
hovertemplate = "<b>%{{x}}</b><br>{label}: %{{y}}%<extra></extra>".format(label=metric)
fig.update_traces(marker_color=colors, hovertemplate=hovertemplate)
fig.update_layout(
    xaxis_title="자치구",
    yaxis_title=metric,
    bargap=0.15,
    showlegend=False,
    height=520
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("데이터 미리보기"):
    st.dataframe(work, use_container_width=True)

st.markdown("—")
st.caption("팁: CSV 포맷이 다르면 컬럼명을 '자치구'와 '...구성비(%)' 형태로 맞추어 주세요.")
