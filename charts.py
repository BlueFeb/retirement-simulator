"""
차트 생성 모듈
- Plotly 인터랙티브 차트 (화면용)
- matplotlib 정적 이미지 (PDF 보고서용 — kaleido 불필요)
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
            "template": "plotly_dark",
            "indigo": "#6366f1", "yellow": "#fbbf24", "green": "#34d399",
            "red": "#f87171", "gray": "#71717a",
            "indigo_fill": "rgba(99,102,241,0.1)",
            "yellow_fill": "rgba(251,191,36,0.05)",
        }
    return {
        "bg": "#ffffff", "paper": "#ffffff",
        "text": "#1e293b", "grid": "rgba(0,0,0,0.06)",
        "template": "plotly_white",
        "indigo": "#4f46e5", "yellow": "#d97706", "green": "#059669",
        "red": "#dc2626", "gray": "#64748b",
        "indigo_fill": "rgba(79,70,229,0.08)",
        "yellow_fill": "rgba(217,119,6,0.05)",
    }


def chart_main(df, retire_age, dep_info, dark_mode=False, return_variants=None):
    """메인 순자산 추이 차트. return_variants: list of (label, df) for simple mode return rate comparison."""
    c = _get_colors(dark_mode)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["age"], y=df["avg_peer"], mode="lines", name="동연령 평균",
        line=dict(color=c["yellow"], width=2, dash="dot"),
        fill="tozeroy", fillcolor=c["yellow_fill"]))
    fig.add_trace(go.Scatter(
        x=df["age"], y=df["net_worth"], mode="lines", name="내 순자산 (현재)",
        line=dict(color=c["indigo"], width=3),
        fill="tozeroy", fillcolor=c["indigo_fill"]))

    # 수익률별 변형 라인 (간단 모드)
    if return_variants:
        variant_colors = ["#06b6d4", "#f59e0b", "#ec4899"]  # cyan, amber, pink
        for i, (label, vdf) in enumerate(return_variants):
            color = variant_colors[i % len(variant_colors)]
            fig.add_trace(go.Scatter(
                x=vdf["age"], y=vdf["net_worth"], mode="lines", name=label,
                line=dict(color=color, width=1.5, dash="dash"),
                opacity=0.7))

    fig.add_vline(x=retire_age, line_dash="dash", line_color=c["yellow"],
                  annotation_text="은퇴", annotation_font_color=c["yellow"])
    if dep_info:
        fig.add_vline(x=dep_info["age"], line_dash="dash", line_color=c["red"],
                      annotation_text="고갈", annotation_font_color=c["red"])
    fig.add_hline(y=0, line_color=c["grid"])
    fig.update_layout(
        template=c["template"], paper_bgcolor=c["paper"], plot_bgcolor=c["bg"],
        height=400, margin=dict(l=5,r=5,t=30,b=40),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=10)),
        xaxis_title="나이", yaxis_title="만원", xaxis=dict(dtick=10),
        yaxis=dict(tickformat=","), hovermode="x unified", dragmode=False,
        font=dict(color=c["text"]))
    return fig


def chart_composition(df, dark_mode=False):
    if "deposit" not in df.columns: return None
    c = _get_colors(dark_mode)
    fig = go.Figure()
    for nm, col, color in [("예금","deposit",c["green"]),("주식","stock",c["indigo"]),("부동산","real_estate",c["yellow"])]:
        fig.add_trace(go.Scatter(x=df["age"],y=df[col],mode="lines",name=nm,stackgroup="one",line=dict(color=color)))
    fig.add_trace(go.Scatter(x=df["age"],y=-df["loan"],mode="lines",name="대출",line=dict(color=c["red"],dash="dot")))
    fig.update_layout(template=c["template"],paper_bgcolor=c["paper"],plot_bgcolor=c["bg"],height=300,
        margin=dict(l=5,r=5,t=30,b=40),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),
        xaxis_title="나이",yaxis=dict(tickformat=","),hovermode="x unified",dragmode=False,font=dict(color=c["text"]))
    return fig


def chart_pie(params, dark_mode=False):
    if params["mode"] == "simple": return None
    c = _get_colors(dark_mode)
    labels=[]; values=[]; colors=[]
    for name,val,color in [("예금·적금",params["deposit_amount"],c["green"]),
                            ("주식·펀드",params["stock_amount"],c["indigo"]),
                            ("부동산",params["real_estate_amount"],c["yellow"]),
                            ("기타 자산",params["other_assets"],"#a78bfa")]:
        if val > 0: labels.append(name); values.append(val); colors.append(color)
    tl = sum(l["amount"] for l in params.get("loans",[]))
    if tl > 0: labels.append("대출"); values.append(tl); colors.append(c["red"])
    if not values: return None
    fig = go.Figure(go.Pie(labels=labels,values=values,marker=dict(colors=colors),hole=0.45,
        textinfo="label+percent",textfont=dict(size=11)))
    fig.update_layout(template=c["template"],paper_bgcolor=c["paper"],height=300,
        margin=dict(l=10,r=10,t=30,b=10),showlegend=False,font=dict(color=c["text"]))
    return fig


def chart_cashflow(params, dark_mode=False):
    c = _get_colors(dark_mode)
    if params["mode"] == "simple":
        inc=params["monthly_income"]; exp=params["monthly_expense"]
        cats_pre=["급여","지출","잔여"]; vals_pre=[inc,-exp,inc-exp]
        cats_post=["급여","지출","부족분"]; vals_post=[0,-exp,-exp]
    else:
        sal=params["salary"]+params["side_income"]; pen=params["pension_monthly"]
        exp=params["fixed_cost"]+params["variable_cost"]; loan_mp=0
        for l in params.get("loans",[]):
            if l["amount"]>0 and l["years"]>0:
                mr=l["rate"]/100/12; np_=l["years"]*12
                loan_mp += l["amount"]*mr*((1+mr)**np_)/(((1+mr)**np_)-1) if mr>0 else l["amount"]/np_
        cats_pre=["급여+부수입","고정비","변동비","대출","잔여"]
        vals_pre=[sal,-params["fixed_cost"],-params["variable_cost"],-round(loan_mp),round(sal-exp-loan_mp)]
        cats_post=["국민연금","고정비","변동비","부족분"]
        vals_post=[pen,-params["fixed_cost"],-params["variable_cost"],round(pen-exp)]

    fig = make_subplots(rows=1,cols=2,subplot_titles=["은퇴 전 (월)","은퇴 후 (월)"],horizontal_spacing=0.15)
    fig.add_trace(go.Bar(x=cats_pre,y=vals_pre,marker_color=[c["green"] if v>=0 else c["red"] for v in vals_pre],
        text=[f"{v:+,}" for v in vals_pre],textposition="outside"),row=1,col=1)
    fig.add_trace(go.Bar(x=cats_post,y=vals_post,marker_color=[c["green"] if v>=0 else c["red"] for v in vals_post],
        text=[f"{v:+,}" for v in vals_post],textposition="outside"),row=1,col=2)
    fig.update_layout(template=c["template"],paper_bgcolor=c["paper"],plot_bgcolor=c["bg"],height=320,
        margin=dict(l=5,r=5,t=40,b=30),showlegend=False,font=dict(color=c["text"],size=11))
    fig.update_yaxes(tickformat=",",title="만원")
    return fig


def chart_scenarios(base, s2, s3, retire_age, dark_mode=False):
    c = _get_colors(dark_mode)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=base["age"],y=base["net_worth"],mode="lines",name="현재 계획",line=dict(color=c["indigo"],width=3)))
    fig.add_trace(go.Scatter(x=s2["age"],y=s2["net_worth"],mode="lines",name="저축 강화",line=dict(color=c["green"],width=2,dash="dash")))
    fig.add_trace(go.Scatter(x=s3["age"],y=s3["net_worth"],mode="lines",name="은퇴 3년 연장",line=dict(color=c["yellow"],width=2,dash="dot")))
    fig.add_hline(y=0,line_color=c["grid"])
    fig.add_vline(x=retire_age,line_dash="dash",line_color=c["gray"],annotation_text="은퇴",annotation_font_color=c["gray"])
    fig.update_layout(template=c["template"],paper_bgcolor=c["paper"],plot_bgcolor=c["bg"],height=320,
        margin=dict(l=5,r=5,t=30,b=40),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),
        xaxis_title="나이",yaxis=dict(tickformat=","),hovermode="x unified",dragmode=False,font=dict(color=c["text"]))
    return fig


def chart_sensitivity(opt, base, pess, dark_mode=False):
    c = _get_colors(dark_mode)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(opt["age"])+list(pess["age"])[::-1],
        y=list(opt["net_worth"])+list(pess["net_worth"])[::-1],
        fill="toself",fillcolor="rgba(99,102,241,0.06)",line=dict(width=0),name="변동 범위"))
    fig.add_trace(go.Scatter(x=opt["age"],y=opt["net_worth"],mode="lines",name="낙관",line=dict(color=c["green"],width=1.5)))
    fig.add_trace(go.Scatter(x=base["age"],y=base["net_worth"],mode="lines",name="기본",line=dict(color=c["indigo"],width=3)))
    fig.add_trace(go.Scatter(x=pess["age"],y=pess["net_worth"],mode="lines",name="비관",line=dict(color=c["red"],width=1.5)))
    fig.add_hline(y=0,line_color=c["grid"])
    fig.update_layout(template=c["template"],paper_bgcolor=c["paper"],plot_bgcolor=c["bg"],height=320,
        margin=dict(l=5,r=5,t=30,b=40),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),
        xaxis_title="나이",yaxis=dict(tickformat=","),hovermode="x unified",dragmode=False,font=dict(color=c["text"]))
    return fig


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PDF용 matplotlib 정적 차트 (kaleido 불필요!)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_chart_images_for_pdf(df, params, dep_info, retire_age,
                                  base_df=None, s2_df=None, s3_df=None,
                                  opt_df=None, pess_df=None):
    """matplotlib로 PDF용 차트 이미지 생성. dict of {name: png_bytes} 반환."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    import numpy as np

    # 한글 폰트 설정
    matplotlib.rcParams["axes.unicode_minus"] = False
    import matplotlib.font_manager as fm
    # Noto Sans CJK 폰트 직접 탐색 (Streamlit Cloud에서 packages.txt로 설치됨)
    noto_paths = [p for p in fm.findSystemFonts() if "NotoSansCJK" in p or "NotoSans" in p]
    if noto_paths:
        prop = fm.FontProperties(fname=noto_paths[0])
        matplotlib.rcParams["font.family"] = prop.get_name()
    else:
        # fallback 시도
        for fname in ["Noto Sans CJK JP", "Noto Sans CJK KR", "NanumGothic",
                       "Malgun Gothic", "AppleGothic", "DejaVu Sans"]:
            try:
                matplotlib.rcParams["font.family"] = fname
                break
            except Exception:
                continue

    imgs = {}

    def _save(fig, name):
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                    facecolor="white", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        imgs[name] = buf.read()

    def _fmt_ytick(val, pos):
        if abs(val) >= 10000: return f"{val/10000:.0f}억"
        if abs(val) >= 1000: return f"{val/1000:.0f}천"
        return f"{val:.0f}"

    # 1. 메인 순자산 추이
    fig, ax = plt.subplots(figsize=(7, 3.5))
    ax.fill_between(df["age"], df["avg_peer"], alpha=0.08, color="#d97706")
    ax.plot(df["age"], df["avg_peer"], "--", color="#d97706", linewidth=1.5, label="동연령 평균")
    ax.fill_between(df["age"], df["net_worth"], alpha=0.1, color="#4f46e5")
    ax.plot(df["age"], df["net_worth"], color="#4f46e5", linewidth=2.5, label="내 순자산 (현재)")

    # 간단 모드: 수익률 5%, 10%, 15% 변형
    if params.get("mode") == "simple":
        from engine import run_simulation as _run_sim
        variant_colors = ["#06b6d4", "#f59e0b", "#ec4899"]
        for rate, vc in zip([5, 10, 15], variant_colors):
            try:
                vdf = _run_sim(params, {"avg_return": float(rate)})
                ax.plot(vdf["age"], vdf["net_worth"], "--", color=vc, linewidth=1.2,
                        alpha=0.7, label=f"수익률 {rate}%")
            except Exception:
                pass

    ax.axvline(x=retire_age, color="#d97706", linestyle="--", alpha=0.5)
    ax.text(retire_age+0.5, ax.get_ylim()[1]*0.9, "은퇴", fontsize=9, color="#d97706")
    if dep_info:
        ax.axvline(x=dep_info["age"], color="#dc2626", linestyle="--", alpha=0.5)
        ax.text(dep_info["age"]+0.5, ax.get_ylim()[1]*0.85, "고갈", fontsize=9, color="#dc2626")
    ax.axhline(y=0, color="gray", linewidth=0.5)
    ax.set_xlabel("나이"); ax.set_ylabel("만원")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_fmt_ytick))
    ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=0.15)
    ax.set_title("순자산 추이", fontsize=13, fontweight="bold", color="#4338ca")
    _save(fig, "main")

    # 2. 자산 구성 파이 (상세 모드)
    if params["mode"] == "detailed":
        labels=[]; sizes=[]; colors=[]
        for nm,val,c in [("예금",params["deposit_amount"],"#059669"),
                          ("주식",params["stock_amount"],"#4f46e5"),
                          ("부동산",params["real_estate_amount"],"#d97706"),
                          ("기타",params["other_assets"],"#a78bfa")]:
            if val > 0: labels.append(nm); sizes.append(val); colors.append(c)
        tl = sum(l["amount"] for l in params.get("loans",[]))
        if tl > 0: labels.append("대출"); sizes.append(tl); colors.append("#dc2626")
        if sizes:
            fig, ax = plt.subplots(figsize=(5, 3))
            ax.pie(sizes, labels=labels, colors=colors, autopct="%1.0f%%",
                   startangle=90, pctdistance=0.75, wedgeprops=dict(width=0.45))
            ax.set_title("현재 자산 구성", fontsize=13, fontweight="bold", color="#4338ca")
            _save(fig, "pie")

    # 3. 자산 구성 변화 (상세 모드)
    if "deposit" in df.columns:
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.stackplot(df["age"], df["deposit"], df["stock"], df["real_estate"],
                     labels=["예금","주식","부동산"], colors=["#059669","#4f46e5","#d97706"], alpha=0.7)
        ax.plot(df["age"], -df["loan"], "--", color="#dc2626", linewidth=1.5, label="대출")
        ax.set_xlabel("나이"); ax.yaxis.set_major_formatter(ticker.FuncFormatter(_fmt_ytick))
        ax.legend(fontsize=8); ax.grid(alpha=0.15)
        ax.set_title("자산 구성 변화", fontsize=13, fontweight="bold", color="#4338ca")
        _save(fig, "composition")

    # 4. 시나리오 비교
    if base_df is not None and s2_df is not None and s3_df is not None:
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.plot(base_df["age"], base_df["net_worth"], color="#4f46e5", linewidth=2.5, label="현재 계획")
        ax.plot(s2_df["age"], s2_df["net_worth"], "--", color="#059669", linewidth=1.5, label="저축 강화")
        ax.plot(s3_df["age"], s3_df["net_worth"], ":", color="#d97706", linewidth=1.5, label="은퇴 3년 연장")
        ax.axhline(y=0, color="gray", linewidth=0.5)
        ax.axvline(x=retire_age, color="gray", linestyle="--", alpha=0.3)
        ax.set_xlabel("나이"); ax.yaxis.set_major_formatter(ticker.FuncFormatter(_fmt_ytick))
        ax.legend(fontsize=9); ax.grid(alpha=0.15)
        ax.set_title("시나리오 비교", fontsize=13, fontweight="bold", color="#4338ca")
        _save(fig, "scenarios")

    # 5. 민감도 분석
    if opt_df is not None and pess_df is not None and base_df is not None:
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.fill_between(opt_df["age"], opt_df["net_worth"], pess_df["net_worth"],
                        alpha=0.08, color="#4f46e5", label="변동 범위")
        ax.plot(opt_df["age"], opt_df["net_worth"], color="#059669", linewidth=1, label="낙관")
        ax.plot(base_df["age"], base_df["net_worth"], color="#4f46e5", linewidth=2.5, label="기본")
        ax.plot(pess_df["age"], pess_df["net_worth"], color="#dc2626", linewidth=1, label="비관")
        ax.axhline(y=0, color="gray", linewidth=0.5)
        ax.set_xlabel("나이"); ax.yaxis.set_major_formatter(ticker.FuncFormatter(_fmt_ytick))
        ax.legend(fontsize=9); ax.grid(alpha=0.15)
        ax.set_title("민감도 분석", fontsize=13, fontweight="bold", color="#4338ca")
        _save(fig, "sensitivity")

    return imgs
