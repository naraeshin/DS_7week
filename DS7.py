import io
import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ----------------------------
# 페이지 설정
# ----------------------------
st.set_page_config(
    page_title="채널별 손익 비율 대시보드",
    page_icon="📊",
    layout="wide",
)

TITLE = "채널별 주요 손익 비율 (매출원가율 / 매출총이익률 / 운영비용률)"
FONT_FAMILY = "Malgun Gothic, 맑은 고딕, AppleGothic, Noto Sans CJK KR, Noto Sans KR, Arial"
REQUIRED_COLS = ["채널", "매출액", "매출원가", "매출총이익", "운영비용"]

# ----------------------------
# 사이드바 - 파일 업로드
# ----------------------------
st.sidebar.header("📥 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("CSV 파일을 업로드하세요", type=["csv"])

st.title("📊 채널별 손익 비율 대시보드")
st.caption("업로드한 CSV에서 채널별 매출원가율/매출총이익률/운영비용률을 계산하고 시각화합니다.")

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

    # 분모 0 보호
    safe_sales = grouped["매출액"].replace(0, 1e-12)

    grouped["매출원가율"]   = grouped["매출원가"]   / safe_sales
    grouped["매출총이익률"] = grouped["매출총이익"] / safe_sales
    grouped["운영비용률"]   = grouped["운영비용"]   / safe_sales

    # 보기 좋게 정렬 (매출액 내림차순)
    grouped = grouped.sort_values("매출액", ascending=False).reset_index(drop=True)
    return grouped

def build_chart(df_ratio: pd.DataFrame) -> go.Figure:
    categories = df_ratio["채널"].astype(str).tolist()
    cost_ratio = df_ratio["매출원가율"].tolist()
    gross_ratio = df_ratio["매출총이익률"].tolist()
    op_ratio    = df_ratio["운영비용률"].tolist()

    # 운영비용률 최대 채널 붉은색 처리 + 값 라벨
    max_idx = int(pd.Series(op_ratio).idxmax())
    colors_op = ["#636EFA"] * len(op_ratio)  # 기본색
    colors_op[max_idx] = "red"

    op_avg = float(pd.Series(op_ratio).mean())

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="매출원가율",
        x=categories, y=cost_ratio, offsetgroup=0,
        hovertemplate="채널=%{x}<br>매출원가율=%{y:.2f}<extra></extra>"
    ))

    fig.add_trace(go.Bar(
        name="매출총이익률",
        x=categories, y=gross_ratio, offsetgroup=1,
        hovertemplate="채널=%{x}<br>매출총이익률=%{y:.2f}<extra></extra>"
    ))

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
    fig.add_hline(y=op_avg, line_dash="dash", line_color="gray",
                  annotation_text=f"운영비용률 평균: {op_avg:.2f}",
                  annotation_position="top left")

    fig.update_layout(
        title=dict(text=TITLE, x=0.5),
        xaxis_title="채널",
        yaxis_title="비율",
        barmode="group",
        bargap=0.25,
        bargroupgap=0.08,
        legend_title_text="지표",
        template="plotly_white",
        font=dict(family=FONT_FAMILY),
        margin=dict(l=40, r=40, t=80, b=40),
    )
    fig.add_hline(y=0, line_width=1, line_color="black")
    return fig

def format_ratio_columns(df: pd.DataFrame, pct_cols):
    out = df.copy()
    for c in pct_cols:
        out[c] = (out[c] * 100).map(lambda x: f"{x:,.2f}%")
    return out

# ----------------------------
# 본문 UI
# ----------------------------
if uploaded_file is None:
    st.info("좌측 사이드바에서 CSV 파일을 업로드해주세요. (예: KPI_Master_Small_12M_KR.csv)")
else:
    df = load_df(uploaded_file)
    validate_columns(df)

    # 계산
    ratio_df = compute_channel_ratios(df)

    # 결과 테이블
    with st.expander("채널별 손익 비율 요약 데이터", expanded=True):
        st.dataframe(
            format_ratio_columns(
                ratio_df[["채널", "매출원가율", "매출총이익률", "운영비용률"]],
                ["매출원가율", "매출총이익률", "운영비용률"]
            ),
            use_container_width=True
        )

    # 차트
    fig = build_chart(ratio_df)
    st.plotly_chart(fig, use_container_width=True)

    # ----------------------------
    # 다운로드 섹션
    # ----------------------------
    st.subheader("⬇️ 결과 다운로드")

    # CSV
    csv_bytes = ratio_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        label="채널별 비율 CSV 다운로드",
        data=csv_bytes,
        file_name="channel_ratio_summary.csv",
        mime="text/csv"
    )

    # HTML
    html_bytes = fig.to_html(include_plotlyjs="cdn").encode("utf-8")
    st.download_button(
        label="차트 HTML 다운로드",
        data=html_bytes,
        file_name="channel_profitability_ratios.html",
        mime="text/html"
    )

    # PNG (kaleido 필요)
    try:
        png_bytes = fig.to_image(format="png", width=1400, height=800, scale=2)
        st.download_button(
            label="차트 PNG 다운로드",
            data=png_bytes,
            file_name="channel_profitability_ratios.png",
            mime="image/png"
        )
    except Exception as e:
        st.warning("PNG 생성에 실패했습니다. 서버에 'kaleido'가 설치되어 있는지 확인하세요.")
        if os.environ.get("STREAMLIT_DEBUG", "0") == "1":
            st.exception(e)

# 푸터
st.caption("© 채널별 손익 비율 대시보드 • Plotly + Streamlit • 폰트: 맑은 고딕 우선 적용")
