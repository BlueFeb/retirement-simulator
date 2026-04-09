"""차트 생성 모듈 — v3: hover 상세, 실질가치 토글"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from engine import fmt_krw

def _get_colors(dark_mode):
    if dark_mode:
        return {"bg":"rgba(12,15,20,0.6)","paper":"rgba(0,0,0,0)","text":"#e4e4e7","grid":"rgba(255,255,255,0.04)",
                "template":"plotly_dark","indigo":"#6366f1","yellow":"#fbbf24","green":"#34d399",
                "red":"#f87171","gray":"#71717a","indigo_fill":"rgba(99,102,241,0.1)","yellow_fill":"rgba(251,191,36,0.05)"}
    return {"bg":"#ffffff","paper":"#ffffff","text":"#1e293b","grid":"rgba(0,0,0,0.06)",
            "template":"plotly_white","indigo":"#4f46e5","yellow":"#d97706","green":"#059669",
            "red":"#dc2626","gray":"#64748b","indigo_fill":"rgba(79,70,229,0.08)","yellow_fill":"rgba(217,119,6,0.05)"}

SCENARIO_STYLES = {
    "현재 계획 (은행이자)": {"color_key":"indigo","dash":"solid","width":3,"fill":False},
    "동연령 평균":          {"color_key":"yellow","dash":"dot","width":2,"fill":False},
    "저축 강화":            {"color_key":"green","dash":"dash","width":2,"fill":False},
    "은퇴 3년 연장":        {"color_key":"gray","dash":"dot","width":2,"fill":False},
    "매년 5% 수익":         {"color":"#06b6d4","dash":"dash","width":1.8,"fill":False},
    "매년 10% 수익":        {"color":"#f59e0b","dash":"dash","width":1.8,"fill":False},
    "매년 15% 수익":        {"color":"#ec4899","dash":"dash","width":1.8,"fill":False},
    "실질 순자산 (현재가치)": {"color":"#a78bfa","dash":"dashdot","width":2,"fill":False},
}

ALL_SCENARIO_LABELS = list(SCENARIO_STYLES.keys())

def _fmt_hover(v):
    """hover용 금액 포맷"""
    if abs(v) >= 10000:
        return f"{v/10000:,.1f}억"
    return f"{v:,.0f}만원"

def chart_combined(scenarios, selected, retire_age, dep_info, dark_mode=False):
    c = _get_colors(dark_mode)
    fig = go.Figure()
    for label in selected:
        if label not in scenarios or scenarios[label] is None: continue
        sdf = scenarios[label]
        style = SCENARIO_STYLES.get(label, {})
        lc = style.get("color", c.get(style.get("color_key","gray"),"#888"))

        # 데이터 컬럼
        if label == "동연령 평균":
            y_data = sdf["avg_peer"]
        elif label == "실질 순자산 (현재가치)":
            y_data = sdf["real_net_worth"] if "real_net_worth" in sdf.columns else sdf["net_worth"]
        else:
            y_data = sdf["net_worth"]

        # hover 상세 (#17)
        hover_texts = []
        for _, row in sdf.iterrows():
            age_v = int(row["age"]); year_v = int(row["year"])
            nw_v = _fmt_hover(row["net_worth"])
            peer_v = _fmt_hover(row["avg_peer"])
            real_v = _fmt_hover(row.get("real_net_worth", row["net_worth"]))
            parts = [f"<b>{year_v}년 ({age_v}세)</b>",
                     f"순자산: {nw_v}",
                     f"동연령: {peer_v}",
                     f"실질가치: {real_v}"]
            if "deposit" in sdf.columns:
                parts.append(f"예금: {_fmt_hover(row['deposit'])}")
                parts.append(f"주식: {_fmt_hover(row['stock'])}")
                parts.append(f"부동산: {_fmt_hover(row['real_estate'])}")
                parts.append(f"대출: {_fmt_hover(row['loan'])}")
            hover_texts.append("<br>".join(parts))

        kw = dict(x=sdf["age"], y=y_data, mode="lines", name=label,
                  line=dict(color=lc, width=style.get("width",2), dash=style.get("dash","solid")),
                  hovertext=hover_texts, hoverinfo="text")
        if style.get("fill") and label == "현재 계획 (은행이자)":
            kw["fill"] = "tozeroy"; kw["fillcolor"] = c["indigo_fill"]
        fig.add_trace(go.Scatter(**kw))

    fig.add_vline(x=retire_age, line_dash="dash", line_color=c["yellow"],
                  annotation_text="은퇴", annotation_font_color=c["yellow"])
    if dep_info:
        fig.add_vline(x=dep_info["age"], line_dash="dash", line_color=c["red"],
                      annotation_text="고갈", annotation_font_color=c["red"])
    fig.add_hline(y=0, line_color=c["grid"])
    fig.update_layout(template=c["template"], paper_bgcolor=c["paper"], plot_bgcolor=c["bg"],
        height=420, margin=dict(l=5,r=5,t=30,b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
        xaxis_title="나이", yaxis_title="만원", xaxis=dict(dtick=10),
        yaxis=dict(tickformat=","), hovermode="x", dragmode=False, font=dict(color=c["text"]))
    return fig

def chart_composition(df, dark_mode=False):
    if "deposit" not in df.columns: return None
    c = _get_colors(dark_mode); fig = go.Figure()
    for nm,col,color in [("예금","deposit",c["green"]),("주식","stock",c["indigo"]),("부동산","real_estate",c["yellow"])]:
        fig.add_trace(go.Scatter(x=df["age"],y=df[col],mode="lines",name=nm,stackgroup="one",line=dict(color=color)))
    fig.add_trace(go.Scatter(x=df["age"],y=-df["loan"],mode="lines",name="대출",line=dict(color=c["red"],dash="dot")))
    fig.update_layout(template=c["template"],paper_bgcolor=c["paper"],plot_bgcolor=c["bg"],height=300,
        margin=dict(l=5,r=5,t=30,b=40),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),
        xaxis_title="나이",yaxis=dict(tickformat=","),hovermode="x unified",dragmode=False,font=dict(color=c["text"]))
    return fig

def chart_pie(params, dark_mode=False):
    if params["mode"]=="simple": return None
    c = _get_colors(dark_mode); labels=[]; values=[]; colors=[]
    for name,val,color in [("예금·적금",params["deposit_amount"],c["green"]),("주식·펀드",params["stock_amount"],c["indigo"]),
                            ("부동산",params["real_estate_amount"],c["yellow"]),("기타",params["other_assets"],"#a78bfa")]:
        if val>0: labels.append(name); values.append(val); colors.append(color)
    tl = sum(l["amount"] for l in params.get("loans",[]))
    if tl>0: labels.append("대출"); values.append(tl); colors.append(c["red"])
    if not values: return None
    fig = go.Figure(go.Pie(labels=labels,values=values,marker=dict(colors=colors),hole=0.45,textinfo="label+percent",textfont=dict(size=11)))
    fig.update_layout(template=c["template"],paper_bgcolor=c["paper"],height=300,margin=dict(l=10,r=10,t=30,b=10),showlegend=False,font=dict(color=c["text"]))
    return fig

def chart_cashflow(params, dark_mode=False):
    c = _get_colors(dark_mode)
    retire_inc = params.get("retire_income", 0)
    if params["mode"]=="simple":
        inc=params["monthly_income"]; exp=params["monthly_expense"]
        cats_pre=["급여","지출","잔여"]; vals_pre=[inc,-exp,inc-exp]
        post_inc = retire_inc
        cats_post=["은퇴후소득","지출","부족분"] if post_inc > 0 else ["급여","지출","부족분"]
        vals_post=[post_inc,-exp,post_inc-exp]
    else:
        sal=params["salary"]+params["side_income"]; pen=params["pension_monthly"]
        exp=params["fixed_cost"]+params["variable_cost"]; loan_mp=0
        for l in params.get("loans",[]):
            if l["amount"]>0 and l["years"]>0:
                mr=l["rate"]/100/12; np_=l["years"]*12
                loan_mp += l["amount"]*mr*((1+mr)**np_)/(((1+mr)**np_)-1) if mr>0 else l["amount"]/np_
        cats_pre=["급여+부수입","고정비","변동비","대출","잔여"]
        vals_pre=[sal,-params["fixed_cost"],-params["variable_cost"],-round(loan_mp),round(sal-exp-loan_mp)]
        post_inc = retire_inc + pen
        cats_post=["연금+소득","고정비","변동비","부족분"]
        vals_post=[round(post_inc),-params["fixed_cost"],-params["variable_cost"],round(post_inc-exp)]
    fig = make_subplots(rows=1,cols=2,subplot_titles=["은퇴 전 (월)","은퇴 후 (월)"],horizontal_spacing=0.15)
    fig.add_trace(go.Bar(x=cats_pre,y=vals_pre,marker_color=[c["green"] if v>=0 else c["red"] for v in vals_pre],
        text=[f"{v:+,}" for v in vals_pre],textposition="outside"),row=1,col=1)
    fig.add_trace(go.Bar(x=cats_post,y=vals_post,marker_color=[c["green"] if v>=0 else c["red"] for v in vals_post],
        text=[f"{v:+,}" for v in vals_post],textposition="outside"),row=1,col=2)
    fig.update_layout(template=c["template"],paper_bgcolor=c["paper"],plot_bgcolor=c["bg"],height=320,
        margin=dict(l=5,r=5,t=40,b=30),showlegend=False,font=dict(color=c["text"],size=11))
    fig.update_yaxes(tickformat=",",title="만원"); return fig

def chart_sensitivity(opt, base, pess, dark_mode=False):
    c = _get_colors(dark_mode); fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(opt["age"])+list(pess["age"])[::-1],y=list(opt["net_worth"])+list(pess["net_worth"])[::-1],
        fill="toself",fillcolor="rgba(99,102,241,0.06)",line=dict(width=0),name="변동 범위"))
    fig.add_trace(go.Scatter(x=opt["age"],y=opt["net_worth"],mode="lines",name="낙관",line=dict(color=c["green"],width=1.5)))
    fig.add_trace(go.Scatter(x=base["age"],y=base["net_worth"],mode="lines",name="기본",line=dict(color=c["indigo"],width=3)))
    fig.add_trace(go.Scatter(x=pess["age"],y=pess["net_worth"],mode="lines",name="비관",line=dict(color=c["red"],width=1.5)))
    fig.add_hline(y=0,line_color=c["grid"])
    fig.update_layout(template=c["template"],paper_bgcolor=c["paper"],plot_bgcolor=c["bg"],height=320,
        margin=dict(l=5,r=5,t=30,b=40),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=11)),
        xaxis_title="나이",yaxis=dict(tickformat=","),hovermode="x unified",dragmode=False,font=dict(color=c["text"]))
    return fig

def generate_chart_images_for_pdf(df, params, dep_info, retire_age, scenarios_dict=None, base_df=None, opt_df=None, pess_df=None, **kw):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt, matplotlib.ticker as ticker, matplotlib.font_manager as fm
    matplotlib.rcParams["axes.unicode_minus"] = False
    noto = [p for p in fm.findSystemFonts() if "NotoSansCJK" in p or "NotoSans" in p]
    if noto: matplotlib.rcParams["font.family"] = fm.FontProperties(fname=noto[0]).get_name()
    else:
        for fn in ["Noto Sans CJK JP","NanumGothic","DejaVu Sans"]:
            try: matplotlib.rcParams["font.family"] = fn; break
            except: continue
    imgs = {}
    def _save(fig, name):
        buf = io.BytesIO(); fig.savefig(buf,format="png",dpi=150,bbox_inches="tight",facecolor="white",edgecolor="none")
        plt.close(fig); buf.seek(0); imgs[name] = buf.read()
    def _yt(val,pos):
        if abs(val)>=10000: return f"{val/10000:.0f}억"
        if abs(val)>=1000: return f"{val/1000:.0f}천"
        return f"{val:.0f}"
    fig,ax = plt.subplots(figsize=(7,4))
    if scenarios_dict:
        styles = [("현재 계획 (은행이자)","#4f46e5","-",2.5),("동연령 평균","#d97706","--",1.5),
                  ("저축 강화","#059669","--",1.5),("은퇴 3년 연장","#64748b",":",1.5),
                  ("매년 5% 수익","#06b6d4","--",1.5),("매년 10% 수익","#f59e0b","--",1.5),
                  ("매년 15% 수익","#ec4899","--",1.5),("실질 순자산 (현재가치)","#a78bfa","-.",1.5)]
        for label,color,ls,lw in styles:
            sdf = scenarios_dict.get(label)
            if sdf is None: continue
            if label=="동연령 평균": col="avg_peer"
            elif label=="실질 순자산 (현재가치)": col="real_net_worth"
            else: col="net_worth"
            if col not in sdf.columns: continue
            ax.plot(sdf["age"],sdf[col],linestyle=ls,color=color,linewidth=lw,label=label,alpha=0.85)
    else:
        ax.plot(df["age"],df["avg_peer"],"--",color="#d97706",linewidth=1.5,label="동연령 평균")
        ax.plot(df["age"],df["net_worth"],color="#4f46e5",linewidth=2.5,label="내 순자산")
    ax.axvline(x=retire_age,color="#d97706",linestyle="--",alpha=0.5)
    if dep_info: ax.axvline(x=dep_info["age"],color="#dc2626",linestyle="--",alpha=0.5)
    ax.axhline(y=0,color="gray",linewidth=0.5); ax.set_xlabel("나이"); ax.set_ylabel("만원")
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(_yt)); ax.legend(fontsize=7,loc="upper left"); ax.grid(alpha=0.15)
    ax.set_title("순자산 추이 & 시나리오 비교",fontsize=13,fontweight="bold",color="#4338ca"); _save(fig,"main")
    if params.get("mode")=="detailed":
        labels=[]; sizes=[]; colors=[]
        for nm,val,cc in [("예금",params.get("deposit_amount",0),"#059669"),("주식",params.get("stock_amount",0),"#4f46e5"),
                          ("부동산",params.get("real_estate_amount",0),"#d97706"),("기타",params.get("other_assets",0),"#a78bfa")]:
            if val>0: labels.append(nm); sizes.append(val); colors.append(cc)
        tl = sum(l.get("amount",0) for l in params.get("loans",[]))
        if tl>0: labels.append("대출"); sizes.append(tl); colors.append("#dc2626")
        if sizes:
            fig,ax = plt.subplots(figsize=(5,3)); ax.pie(sizes,labels=labels,colors=colors,autopct="%1.0f%%",startangle=90,pctdistance=0.75,wedgeprops=dict(width=0.45))
            ax.set_title("현재 자산 구성",fontsize=13,fontweight="bold",color="#4338ca"); _save(fig,"pie")
    if "deposit" in df.columns:
        fig,ax = plt.subplots(figsize=(7,3)); ax.stackplot(df["age"],df["deposit"],df["stock"],df["real_estate"],labels=["예금","주식","부동산"],colors=["#059669","#4f46e5","#d97706"],alpha=0.7)
        ax.plot(df["age"],-df["loan"],"--",color="#dc2626",linewidth=1.5,label="대출"); ax.set_xlabel("나이"); ax.yaxis.set_major_formatter(ticker.FuncFormatter(_yt))
        ax.legend(fontsize=8); ax.grid(alpha=0.15); ax.set_title("자산 구성 변화",fontsize=13,fontweight="bold",color="#4338ca"); _save(fig,"composition")
    if opt_df is not None and pess_df is not None and base_df is not None:
        fig,ax = plt.subplots(figsize=(7,3)); ax.fill_between(opt_df["age"],opt_df["net_worth"],pess_df["net_worth"],alpha=0.08,color="#4f46e5")
        ax.plot(opt_df["age"],opt_df["net_worth"],color="#059669",linewidth=1,label="낙관")
        ax.plot(base_df["age"],base_df["net_worth"],color="#4f46e5",linewidth=2.5,label="기본")
        ax.plot(pess_df["age"],pess_df["net_worth"],color="#dc2626",linewidth=1,label="비관"); ax.axhline(y=0,color="gray",linewidth=0.5)
        ax.set_xlabel("나이"); ax.yaxis.set_major_formatter(ticker.FuncFormatter(_yt)); ax.legend(fontsize=9); ax.grid(alpha=0.15)
        ax.set_title("민감도 분석",fontsize=13,fontweight="bold",color="#4338ca"); _save(fig,"sensitivity")
    return imgs
