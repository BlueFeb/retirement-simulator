"""
차트 생성 모듈
- Plotly 인터랙티브 차트 (화면용)
- 정적 이미지 export (PDF 보고서용)
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

from engine import fmt_krw


def _get_colors(dark_mode):
    if dark_mode:
        return {
            "bg": "rgba(12,15,20,0.6)", "paper": "rgba(0,0,0,0)",
            "text": "#e4e4e7", "grid": "rgba(255,255,255,0.04)",
            "axis": "rgba(255,255,255,0.06)", "template": "plotly_dark",
            "indigo": "#6366f1", "yellow": "#fbbf24", "green": "#34d399",
            "red": "#f87171", "gray": "#71717a",
            "indigo_fill": "rgba(99,102,241,0.1)",
            "yellow_fill": "rgba(251,191,36,0.05)",
        }
    else:
        return {
            "bg": "#ffffff", "paper": "#ffffff",
            "text": "#1e293b", "grid": "rgba(0,0,0,0.06)",
            "axis": "rgba(0,0,0,0.1)", "template": "plotly_white",
            "indigo": "#4f46e5", "yellow": "#d97706", "green": "#059669",
            "red": "#dc2626", "gray": "#64748b",
            "indigo_fill": "rgba(79,70,229,0.08)",
            "yellow_fill": "rgba(217,119,6,0.05)",
        }


def chart_main(df, retire_age, dep_info, dark_mode=False):
    """메인 순자산 추이 차트."""
    c = _get_colors(dark_mode)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["age"], y=df["avg_peer"], mode="lines", name="동연령 평균",
        line=dict(color=c["yellow"], width=2, dash="dot"),
        fill="tozeroy", fillcolor=c["yellow_fill"]))
    fig.add_trace(go.Scatter(
        x=df["age"], y=df["net_worth"], mode="lines", name="내 순자산",
        line=dict(color=c["indigo"], width=3),
        fill="tozeroy", fillcolor=c["indigo_fill"]))
    fig.add_vline(x=retire_age, line_dash="dash", line_color=c["yellow"],
                  annotation_text="은퇴", annotation_font_color=c["yellow"])
    if dep_info:
        fig.add_vline(x=dep_info["age"], line_dash="dash", line_color=c["red"],
                      annotation_text="고갈", annotation_font_color=c["red"])
    fig.add_hline(y=0, line_color=c["grid"])
    fig.update_layout(
        template=c["template"], paper_bgcolor=c["paper"], plot_bgcolor=c["bg"],
        height=350, margin=dict(l=5,r=5,t=30,b=40),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),
        xaxis_title="나이", yaxis_title="만원", xaxis=dict(dtick=10),
        yaxis=dict(tickformat=","), hovermode="x unified", dragmode=False,
        font=dict(color=c["text"]))
    return fig


def chart_composition(df, dark_mode=False):
    """자산 구성 스택 차트 (상세 모드)."""
    if "deposit" not in df.columns:
        return None
    c = _get_colors(dark_mode)
    fig = go.Figure()
    for nm, col, color in [("예금","deposit",c["green"]),
                            ("주식","stock",c["indigo"]),
                            ("부동산","real_estate",c["yellow"])]:
        fig.add_trace(go.Scatter(
            x=df["age"], y=df[col], mode="lines",
            name=nm, stackgroup="one", line=dict(color=color)))
    fig.add_trace(go.Scatter(
        x=df["age"], y=-df["loan"], mode="lines",
        name="대출", line=dict(color=c["red"], dash="dot")))
    fig.update_layout(
        template=c["template"], paper_bgcolor=c["paper"], plot_bgcolor=c["bg"],
        height=300, margin=dict(l=5,r=5,t=30,b=40),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),
        xaxis_title="나이", yaxis=dict(tickformat=","),
        hovermode="x unified", dragmode=False, font=dict(color=c["text"]))
    return fig


def chart_pie(params, dark_mode=False):
    """현재 자산 구성 파이 차트."""
    if params["mode"] == "simple":
        return None
    c = _get_colors(dark_mode)
    labels = []; values = []; colors = []
    items = [
        ("예금·적금", params["deposit_amount"], c["green"]),
        ("주식·펀드", params["stock_amount"], c["indigo"]),
        ("부동산", params["real_estate_amount"], c["yellow"]),
        ("기타 자산", params["other_assets"], "#a78bfa"),
    ]
    for name, val, color in items:
        if val > 0:
            labels.append(name); values.append(val); colors.append(color)

    total_loan = sum(l["amount"] for l in params.get("loans", []))
    if total_loan > 0:
        labels.append("대출 (부채)"); values.append(total_loan); colors.append(c["red"])

    if not values:
        return None

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        marker=dict(colors=colors),
        hole=0.45, textinfo="label+percent",
        textfont=dict(size=11)))
    fig.update_layout(
        template=c["template"], paper_bgcolor=c["paper"],
        height=300, margin=dict(l=10,r=10,t=30,b=10),
        showlegend=False, font=dict(color=c["text"]))
    return fig


def chart_cashflow(params, dark_mode=False):
    """월 수입 vs 지출 워터폴 차트 (은퇴 전/후)."""
    c = _get_colors(dark_mode)

    if params["mode"] == "simple":
        inc = params["monthly_income"]
        exp = params["monthly_expense"]
        # 은퇴 전
        cats_pre = ["급여", "지출", "잔여"]
        vals_pre = [inc, -exp, inc - exp]
        # 은퇴 후
        cats_post = ["급여", "지출", "부족분"]
        vals_post = [0, -exp, -exp]
    else:
        sal = params["salary"] + params["side_income"]
        pen = params["pension_monthly"]
        exp = params["fixed_cost"] + params["variable_cost"]
        loan_mp = 0
        for l in params.get("loans", []):
            if l["amount"] > 0 and l["years"] > 0:
                mr = l["rate"]/100/12; np_ = l["years"]*12
                if mr > 0:
                    loan_mp += l["amount"]*mr*((1+mr)**np_)/(((1+mr)**np_)-1)
        cats_pre = ["급여+부수입", "고정비", "변동비", "대출상환", "잔여"]
        vals_pre = [sal, -params["fixed_cost"], -params["variable_cost"],
                    -round(loan_mp), round(sal - exp - loan_mp)]
        cats_post = ["국민연금", "고정비", "변동비", "부족분"]
        vals_post = [pen, -params["fixed_cost"], -params["variable_cost"],
                     round(pen - exp)]

    fig = make_subplots(rows=1, cols=2, subplot_titles=["은퇴 전 (월)", "은퇴 후 (월)"],
                        horizontal_spacing=0.15)

    colors_pre = [c["green"] if v >= 0 else c["red"] for v in vals_pre]
    colors_post = [c["green"] if v >= 0 else c["red"] for v in vals_post]

    fig.add_trace(go.Bar(x=cats_pre, y=vals_pre,
                          marker_color=colors_pre, name="은퇴 전",
                          text=[f"{v:+,}" for v in vals_pre], textposition="outside"),
                  row=1, col=1)
    fig.add_trace(go.Bar(x=cats_post, y=vals_post,
                          marker_color=colors_post, name="은퇴 후",
                          text=[f"{v:+,}" for v in vals_post], textposition="outside"),
                  row=1, col=2)

    fig.update_layout(
        template=c["template"], paper_bgcolor=c["paper"], plot_bgcolor=c["bg"],
        height=320, margin=dict(l=5,r=5,t=40,b=30),
        showlegend=False, font=dict(color=c["text"], size=11))
    fig.update_yaxes(tickformat=",", title="만원")
    return fig


def chart_scenarios(base, s2, s3, retire_age, dark_mode=False):
    """3가지 시나리오 비교 차트."""
    c = _get_colors(dark_mode)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=base["age"], y=base["net_worth"],
        mode="lines", name="현재 계획", line=dict(color=c["indigo"], width=3)))
    fig.add_trace(go.Scatter(x=s2["age"], y=s2["net_worth"],
        mode="lines", name="저축 강화", line=dict(color=c["green"], width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=s3["age"], y=s3["net_worth"],
        mode="lines", name="은퇴 3년 연장", line=dict(color=c["yellow"], width=2, dash="dot")))
    fig.add_hline(y=0, line_color=c["grid"])
    fig.add_vline(x=retire_age, line_dash="dash", line_color=c["gray"],
                  annotation_text="은퇴", annotation_font_color=c["gray"])
    fig.update_layout(
        template=c["template"], paper_bgcolor=c["paper"], plot_bgcolor=c["bg"],
        height=320, margin=dict(l=5,r=5,t=30,b=40),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),
        xaxis_title="나이", yaxis=dict(tickformat=","),
        hovermode="x unified", dragmode=False, font=dict(color=c["text"]))
    return fig


def chart_sensitivity(opt, base, pess, dark_mode=False):
    """민감도 분석 차트: 낙관/기본/비관."""
    c = _get_colors(dark_mode)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=opt["age"], y=opt["net_worth"],
        mode="lines", name="낙관", line=dict(color=c["green"], width=1.5),
        fill="tonexty" if False else None))
    fig.add_trace(go.Scatter(x=base["age"], y=base["net_worth"],
        mode="lines", name="기본", line=dict(color=c["indigo"], width=3)))
    fig.add_trace(go.Scatter(x=pess["age"], y=pess["net_worth"],
        mode="lines", name="비관", line=dict(color=c["red"], width=1.5)))

    # 낙관-비관 사이 영역 채우기
    fig.add_trace(go.Scatter(
        x=list(opt["age"]) + list(pess["age"])[::-1],
        y=list(opt["net_worth"]) + list(pess["net_worth"])[::-1],
        fill="toself", fillcolor="rgba(99,102,241,0.06)",
        line=dict(width=0), name="변동 범위", showlegend=True))

    fig.add_hline(y=0, line_color=c["grid"])
    fig.update_layout(
        template=c["template"], paper_bgcolor=c["paper"], plot_bgcolor=c["bg"],
        height=320, margin=dict(l=5,r=5,t=30,b=40),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),
        xaxis_title="나이", yaxis=dict(tickformat=","),
        hovermode="x unified", dragmode=False, font=dict(color=c["text"]))
    return fig


def fig_to_image_bytes(fig, width=700, height=350):
    """Plotly 차트를 PNG 바이트로 변환 (PDF 삽입용)."""
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        # kaleido 없으면 None 반환
        return None
