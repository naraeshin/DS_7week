import os
import io
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# =========================
# 단일파일 테마/스타일(설정파일 無)
# =========================
TITLE = "채널별 주요 손익 비율 (매출원가율 / 매출총이익률 / 운영비용률)"
# 폰트: 맑은 고딕 우선 (Windows 기본). macOS/Linux는 대체 폰트 사용.
FONT_FAMILY = "Malgun Gothic, 맑은 고딕, AppleGothic, Noto Sans CJK KR, Noto Sans KR, Arial"

# 통일된 팔레트
CLR_COST   = "#048BA8"   # 매출원가율
CLR_GROSS  = "#EFEA5A"   # 매출총이익률
CLR_OP     = "#F29E4C"   # 운영비용률(기본)
CLR_OP_MAX = "red"       # 운영비용률 최댓값 강조
CLR_AXIS   = "#0F172A"   # 축/텍스트
CLR_GRID   = "rgba(15, 23, 42, 0.08)"  # 연한 그리드
CLR_AVG    = "gray"      # 평균선
BG_MAIN    = "#F7F9FB"   # 페이지 배경
BG_PANEL   = "#FFFFFF"   # 카드/패널 배경
PRIMARY    = "#048BA8"   # 버튼 등 포커스 컬러

REQUIRED_COLS = ["채널", "매출액", "매출원가", "매출총이익", "운영비용"]

# =========================
# 페이지 설정
# =========================
st.set_page_config(
    page_title="채널별 손익 비율 대시보드",
    page_icon="📊",
    layout="wide",
)

# 전역 CSS (테마/폰트/버튼/배경) — 설정파일 없이 적용
st.markdown(f"""
<style>
/* 전체 폰트 */
html, body, [class*="css"] {{
    font-family: {FONT_FAMILY} !important;
    color: {CLR_AXIS};
}}

/* 배경색 */
.stApp {{
    background: {BG_MAIN};
}}

/* 컨테이너 여백 */
.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}}

/* 카드/패널 느낌의 expander */
.st-expander, .stDataFrame, .stPlotlyChart {{
    background: {BG_PANEL};
    border-radius: 12px;
    padding: 0.25rem 0.25rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}}

/* 사이드바 배경 */
section[data-testid="stSidebar"] {{
    background: {BG_PANEL};
    border-right: 1px solid rgba(0,0,0,0.06);
}}

/* 버튼 스타일 */
.stButton>button, .stDownloadButton>button {{
    background: {PRIMARY};
    color: white;
    border: 0;
    border-radius: 10px;
    padding: 0.5rem 0.9rem;
}}
.stButton>button:hover, .stDownloadButton>button:hover {{
    opacity: 0.9;
}}

/* 파일 업로더 라벨 컬러 */
[data-testid="stFileUploader"] label {{
    color: {CLR_AXIS};
}}
</style>
""", unsafe_allow_html=True)

# =========================
# 유틸 함수
# =========================
def validate_columns(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        st.error(f"필수 컬럼 누락: {missing}\n필요 컬럼: {REQUIRED_COLS}")
        st.stop()

@st.cache_data(show_spinner=False)
def load_df(file) -> pd.DataFrame:
    return pd.read_csv(file)

def compute_channel_ratios(df: pd.DataFrame) -> pd.DataFrame:
    # 채널별 합계
    grouped = df.groupby("채널", dropna=False).agg({
        "매출액": "sum",
        "매출원가": "sum",
        "매출총이익": "sum",
        "운영비용": "sum",
    }).reset_index()

    # 0 분모 보호
    safe_sales = grouped["매출액"].replace(0, 1e-12)

    grouped["매출원가율"]   = grouped["매출원가"]   / safe_sales
    grouped["매출총이익률"] = grouped["매출총이익"] / safe_sales
    grouped["운영비용률"]   = grouped["운영비용"]   / safe_sales

    # 보기 좋은 정렬(매출액 내림차순)
    grouped = grouped.sort_values("매출액", ascending=False).reset_index(drop=True)
    return grouped

def build_chart(df_ratio: pd.DataFrame) -> go.Figure:
    categories = df_ratio["채널"].astype(str).tolist()
    cost_ratio = df_ratio["매출원가율"].tolist()
    gross_ratio = df_ratio["매출총이익률"].tolist()
    op_ratio    = df_ratio["운영비용률"].tolist()

    # 운영비용률 최댓값 붉은색 + 값 라벨
    max_idx = int(pd.Series(op_ratio).idxmax())
    colors_op = [CLR_OP] * len(op_ratio)
    colors_op[max_idx] = CLR_OP_MAX
    op_avg = float(pd.Series(op_ratio).mean())

    fig = go.Figure()

    # 매출원가율
    fig.add_trace(go.Bar(
        name="매출원가율",
        x=categories, y=cost_ratio, offsetgroup=0,
        marker=dict(color=CLR_COST),
        hovertemplate="채널=%{x}<br>매출원가율=%{y:.2f}<extra></extra>"
    ))

    # 매출총이익률
    fig.add_trace(go.Bar(
        name="매출총이익률",
        x=categories, y=gross_ratio, offsetgroup=1,
        marker=dict(color=CLR_GROSS),
        hovertemplate="채널=%{x}<br>매출총이익률=%{y:.2f}<extra></extra>"
    ))

    # 운영비용률 (최댓값 라벨)
    text_vals = [""] * len(op_ratio)
    text_vals[max_idx] = f"{op_ratio[max_idx]:.2f}"
    fig.add_trace(go.Bar(
        name="운영비용률",
        x=categories, y=op_ratio, offsetgroup=2,
        marker=dict(color=colors_op),
        text=text_vals, textposition="outside", cliponaxis=False,
        hovertemplate="채널=%{x}<br>운영비용률=%{y:.2f}<extra></extra>"
    ))

    # 평균선
    fig.add_hline(
        y=op_avg, line_dash="dash", line_color=CLR_AVG,
        annotation_text=f"운영비용률 평균: {op_avg:.2f}",
        annotation_position="top left",
        annotation_font=dict(family=FONT_FAMILY, color=CLR_AVG)
    )

    # 축/그리드/폰트/배경
    fig.update_layout(
        title=dict(text=TITLE, x=0.5, font=dict(family=FONT_FAMILY, color=CLR_AXIS)),
        xaxis_title="채널",
        yaxis_title="비율",
        barmode="group",
        bargap=0.25,
        bargroupgap=0.08,
        legend_title_text="지표",
        template="plotly_white",
        font=dict(family=FONT_FAMILY, color=CLR_AXIS),
        margin=dict(l=40, r=40, t=80, b=40),
        paper_bgcolor=BG_PANEL,
        plot_bgcolor="#FFFFFF",
    )
    fig.update_xaxes(showgrid=False, linecolor=CLR_GRID, tickfont=dict(color=CLR_AXIS))
    fig.update_yaxes(showgrid=True, gridcolor=CLR_GRID, zeroline=False, tickfont=dict(color=CLR_AXIS))

    # y=0 기준선
    fig.add_hline(y=0, line_width=1, line_color=CLR_AXIS)
    return fig

def format_ratio_columns(df: pd.DataFrame, pct_cols):
    out = df.copy()
    for c in pct_cols:
        out[c] = (out[c] * 100).map(lambda x: f"{x:,.2f}%")
    return out

# =========================
# UI
# =========================
st.sidebar.header("📥 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("CSV 파일을 업로드하세요", type=["csv"])

st.title("📊 채널별 손익 비율 대시보드")
st.caption("설정파일 없이 메인 코드만으로 테마 적용 • Plotly + Streamlit • 폰트: 맑은 고딕 우선")

if uploaded_file is None:
    st.info("좌측 사이드바에서 CSV 파일을 업로드해주세요. (예: KPI_Master_Small_12M_KR.csv)")
else:
    df = load_df(uploaded_file)
    validate_columns(df)

    ratio_df = compute_channel_ratios(df)

    with st.expander("채널별 손익 비율 요약 데이터", expanded=True):
        st.dataframe(
            format_ratio_columns(
                ratio_df[["채널", "매출원가율", "매출총이익률", "운영비용률"]],
                ["매출원가율", "매출총이익률", "운영비용률"]
            ),
            use_container_width=True
        )

    fig = build_chart(ratio_df)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("⬇️ 결과 다운로드")
    # CSV
    csv_bytes = ratio_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="채널별 비율 CSV 다운로드",
        data=csv_bytes,
        file_name="channel_ratio_summary.csv",
        mime="text/csv",
        key="dl_csv"
    )

    # HTML
    html_bytes = fig.to_html(include_plotlyjs="cdn").encode("utf-8")
    st.download_button(
        label="차트 HTML 다운로드",
        data=html_bytes,
        file_name="channel_profitability_ratios.html",
        mime="text/html",
        key="dl_html"
    )

    # PNG (kaleido 필요)
    try:
        png_bytes = fig.to_image(format="png", width=1400, height=800, scale=2)
        st.download_button(
            label="차트 PNG 다운로드",
            data=png_bytes,
            file_name="channel_profitability_ratios.png",
            mime="image/png",
            key="dl_png"
        )
    except Exception as e:
        st.warning("PNG 생성에 실패했습니다. 'kaleido' 설치/폰트 설정을 확인하세요.")
        if os.environ.get("STREAMLIT_DEBUG", "0") == "1":
            st.exception(e)

st.caption("© 채널별 손익 비율 대시보드 • 통일 테마 • Plotly + Streamlit • 폰트: 맑은 고딕 우선 적용")
