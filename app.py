import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import os

# 页面基础配置
st.set_page_config(page_title="5G 信号可视化看板", layout="wide")
st.title("📡 5G 路测信号 3D 可视化看板")

@st.cache_data
def load_data(filepath: str) -> pd.DataFrame:
    """
    加载 5G 路测数据并进行基础预处理。
    添加颜色映射：> -90dBm 绿色, < -110dBm 红色, 其余为黄色。
    """
    df = pd.read_csv(filepath)
    
    def assign_color(rsrp):
        if rsrp > -90:
            return [0, 255, 0, 160]   # 绿色
        elif rsrp < -110:
            return [255, 0, 0, 160]   # 红色
        else:
            return [255, 200, 0, 160] # 黄色
            
    df['color'] = df['RSRP_dBm'].apply(assign_color)
    return df

def filter_data(df: pd.DataFrame, bands: list, rsrp_min: float, rsrp_max: float) -> pd.DataFrame:
    """根据侧边栏条件过滤基站数据。"""
    mask = (df['Band'].isin(bands)) & (df['RSRP_dBm'] >= rsrp_min) & (df['RSRP_dBm'] <= rsrp_max)
    return df[mask]

# 容错加载数据
data_path = 'data/signal_samples.csv' if os.path.exists('data/signal_samples.csv') else 'signal_samples.csv'
try:
    raw_df = load_data(data_path)
except Exception as e:
    st.error(f"数据加载失败，请检查文件路径。错误信息: {e}")
    st.stop()

# --- 侧边栏联动筛选 (进阶关卡) ---
st.sidebar.header("🎛️ 基站与信号筛选")
all_bands = raw_df['Band'].unique().tolist()
selected_bands = st.sidebar.multiselect("📡 频段筛选 (Band)", all_bands, default=all_bands)

min_rsrp, max_rsrp = float(raw_df['RSRP_dBm'].min()), float(raw_df['RSRP_dBm'].max())
selected_rsrp = st.sidebar.slider("📶 RSRP 范围 (dBm)", min_rsrp, max_rsrp, (min_rsrp, max_rsrp))

# 获取过滤后数据
df = filter_data(raw_df, selected_bands, selected_rsrp[0], selected_rsrp[1])
st.sidebar.markdown(f"**当前过滤后数据量:** {len(df)} 条")

# --- 核心视图区 ---
if df.empty:
    st.warning("⚠️ 当前筛选条件下无数据，请放宽侧边栏的限制范围。")
else:
    # 极客视觉体验：3D 地图 (进阶关卡)
    st.subheader("🗺️ 5G 信号 3D 空间分布图")
    st.markdown("说明：**柱子颜色**代表 RSRP 信号强度 (绿>黄>红)，**柱子高度**代表 Download_Mbps 下载速率。")

    # PyDeck 3D 图层
    layer = pdk.Layer(
        "ColumnLayer",
        data=df,
        get_position=["Longitude", "Latitude"],
        get_elevation="Download_Mbps",
        elevation_scale=8,
        radius=30,
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
    )

    view_state = pdk.ViewState(
        longitude=df["Longitude"].mean(),
        latitude=df["Latitude"].mean(),
        zoom=13,
        pitch=45,
        bearing=15,
    )

    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "基站ID: {CellID}\n频段: {Band}\n类型: {TerminalType}\nRSRP: {RSRP_dBm} dBm\n下载速率: {Download_Mbps} Mbps"}
    )
    st.pydeck_chart(r)

    # --- 数据概览图表 (基础关卡) ---
    st.subheader("📊 区域信号与终端统计")
    col1, col2 = st.columns(2)

    with col1:
        term_df = df['TerminalType'].value_counts().reset_index()
        term_df.columns = ['TerminalType', 'Count']
        fig_pie = px.pie(term_df, values='Count', names='TerminalType', title='不同类型终端接入占比', hole=0.3)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        band_df = df['Band'].value_counts().reset_index()
        band_df.columns = ['Band', 'Count']
        fig_bar = px.bar(band_df, x='Band', y='Count', color='Band', title='各频段基站调度数量分布')
        st.plotly_chart(fig_bar, use_container_width=True)
