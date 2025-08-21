import argparse
import os
import sys
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ------------------------------------------------------------
# 설정
# ------------------------------------------------------------
APP_TITLE = "채널별 주요 손익 비율 (매출원가율 / 매출총이익률 / 운영비용률)"
OUTPUT_HTML = "channel_profitability_ratios.html"
OUTPUT_PNG = "channel_profitability_ratios.png"
OUTPUT_CSV = "channel_ratio_summary.csv"

# Plotly 폰트 설정: 맑은 고딕 우선, 미설치 환경을 대비해 대체 폰트 지정
FONT_FAMILY = "Malgun Gothic, 맑은 고딕, AppleGothic, Noto Sans CJK KR, Noto Sans KR, Arial"

# ------------------------------------------------------------
# 유틸: 파일 선택(선택형)
# ------------------------------------------------------------
def pick_file_dialog():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="KPI CSV 파일을 선택하세요",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        return path
    except Exception:
        return None

# ------------------------------------------------------------
# 데이터 로드
# ------------------------------------------------------------
def load_data(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {csv_path}")
    df = pd.read_csv(csv_path, encoding="utf-8")
    return df

# ------------------------------------------------------------
# 검증
# ------------------------------------------------------------
REQUIRED_COLS = ["채널", "매출액", "매출원가", "매출총이익", "운영비용"]

def validate_columns(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"필수 컬럼 누락: {missing}\n"
                         f"필요 컬럼: {REQUIRED_COLS}")

# ------------------------------------------------------------
# 계산
# ------------------------------------------------------------
def compute_channel_ratios(df: pd.DataFrame) -> pd.DataFrame:
    # 채널별 합계
    grouped = df.groupby("채널", dropna=False).agg({
        "매출액": "sum",
        "매출원가": "sum",
        "매출총이익": "sum",
        "운영비용": "sum"
    }).reset_index()

    # 0 매출 안전 처리(0이면 분모를 매우 작은 값으로)
    safe_sales = grouped["매출액"].replace(0, 1e-12)

    grouped["매출원가율"] = grouped["매출원가"] / safe_sales
    grouped["매출총이익률"] = grouped["매출총이익"] / safe_sales
    grouped["운영비용률"] = grouped["운영비용"] / safe_sales

    # 보기 좋게 정렬(매출액 기준 내림차순)
    grouped = grouped.sort_values("매출액", ascending=False).reset_index(drop=True)

    return grouped

# ------------------------------------------------------------
# 시각화 (Plotly)
# ------------------------------------------------------------
def build_chart(df_ratio: pd.DataFrame):
    categories = df_ratio["채널"].astype(str).tolist()

    cost_ratio = df_ratio["매출원가율"].tolist()
    gross_ratio = df_ratio["매출총이익률"].tolist()
    op_ratio = df_ratio["운영비용률"].tolist()

    # 운영비용률 최대 채널 하이라이트(빨간색)
    max_idx = int(pd.Series(op_ratio).idxmax())
    colors_op = []
    for i, _ in enumerate(op_ratio):
        colors_op.append("red" if i == max_idx else "#636EFA")  # Plotly 기본 팔레트 중 파랑 대체

    # 평균선
    op_avg = float(pd.Series(op_ratio).mean())

    fig = go.Figure()

    # 매출원가율
    fig.add_trace(go.Bar(
        name="매출원가율",
        x=categories,
        y=cost_ratio,
        offsetgroup=0,
        marker=dict(line=dict(width=0)),
        hovertemplate="채널=%{x}<br>매출원가율=%{y:.2f}<extra></extra>"
    ))

    # 매출총이익률
    fig.add_trace(go.Bar(
        name="매출총이익률",
        x=categories,
        y=gross_ratio,
        offsetgroup=1,
        marker=dict(line=dict(width=0)),
        hovertemplate="채널=%{x}<br>매출총이익률=%{y:.2f}<extra></extra>"
    ))

    # 운영비용률 (최대값 붉은색 + 레이블)
    # text는 최대값에만 표시
    text_vals = ["" for _ in op_ratio]
    text_vals[max_idx] = f"{op_ratio[max_idx]:.2f}"

    fig.add_trace(go.Bar(
        name="운영비용률",
        x=categories,
        y=op_ratio,
        offsetgroup=2,
        marker=dict(color=colors_op),
        text=text_vals,
        textposition="outside",
        cliponaxis=False,
        hovertemplate="채널=%{x}<br>운영비용률=%{y:.2f}<extra></extra>"
    ))

    # 평균선
    fig.add_hline(y=op_avg, line_dash="dash", line_color="gray", annotation_text=f"운영비용률 평균: {op_avg:.2f}")

    # 레이아웃
    fig.update_layout(
        title=dict(text=APP_TITLE, x=0.5),
        xaxis_title="채널",
        yaxis_title="비율",
        barmode="group",
        bargap=0.25,
        bargroupgap=0.08,
        legend_title_text="지표",
        template="plotly_white",
        font=dict(family=FONT_FAMILY),
        margin=dict(l=60, r=40, t=80, b=60),
        hoverlabel=dict(font_family=FONT_FAMILY)
    )

    # y=0 기준선 강조
    fig.add_hline(y=0, line_width=1, line_color="black")

    return fig

# ------------------------------------------------------------
# 저장
# ------------------------------------------------------------
def save_outputs(fig: go.Figure, df_ratio: pd.DataFrame):
    # HTML(인터랙티브)
    fig.write_html(OUTPUT_HTML, include_plotlyjs="cdn")
    # PNG(정적) - kaleido 필요
    try:
        fig.write_image(OUTPUT_PNG, scale=2, width=1200, height=700)
    except Exception as e:
        print(f"[경고] PNG 저장 실패(아마도 kaleido 미설치/폰트문제): {e}")
    # 요약 테이블 CSV
    # 소수점 6자리 고정(원하면 변경)
    df_export = df_ratio.copy()
    for col in ["매출원가율", "매출총이익률", "운영비용률"]:
        df_export[col] = df_export[col].round(6)
    df_export.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

# ------------------------------------------------------------
# 메인
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="채널별 손익 비율 자동화 스크립트")
    parser.add_argument("--file", type=str, help="입력 CSV 파일 경로 (예: KPI_Master_Small_12M_KR.csv)")
    args = parser.parse_args()

    csv_path = args.file
    if not csv_path:
        csv_path = pick_file_dialog()
    if not csv_path:
        print("CSV 파일이 선택되지 않았습니다. --file 옵션으로 경로를 지정하거나 파일 선택창에서 선택하세요.")
        sys.exit(1)

    print(f"[정보] 파일 로드: {csv_path}")
    df = load_data(csv_path)
    validate_columns(df)

    print("[정보] 채널별 비율 계산 중...")
    df_ratio = compute_channel_ratios(df)

    print("[정보] 차트 생성 중...")
    fig = build_chart(df_ratio)

    print(f"[정보] 결과 저장: {OUTPUT_HTML}, {OUTPUT_PNG}, {OUTPUT_CSV}")
    save_outputs(fig, df_ratio)

    print("[완료] 생성된 파일을 확인하세요:")
    print(f" - {os.path.abspath(OUTPUT_HTML)}")
    print(f" - {os.path.abspath(OUTPUT_PNG)}")
    print(f" - {os.path.abspath(OUTPUT_CSV)}")

if __name__ == "__main__":
    main()
