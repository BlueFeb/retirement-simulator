import streamlit as st
import pandas as pd
import json, base64
from datetime import datetime

from engine import (run_simulation, get_key_metrics, run_scenarios,
                    run_sensitivity, calc_fire_index, calc_safe_withdrawal,
                    fmt_krw, amount_to_korean, DEP_RATE, LOAN_RATE)
from charts import (chart_combined, chart_composition, chart_pie, chart_cashflow,
                     chart_sensitivity, generate_chart_images_for_pdf,
                     ALL_SCENARIO_LABELS)
from report_pdf import generate_pdf_report
from gsheet import get_gsheet_connection, save_to_gsheet
from theme import get_css, get_header_color, get_diff_colors

D_AGE=35; D_RETIRE=60; D_LIFE=85; D_INFL=2.5
D_TS=10000; D_MI=400; D_ME=250
D_DA=3000; D_DR=2.83; D_SA=4000; D_SR=10.0
D_REA=30000; D_RR=2.5; D_OA=0
D_SAL=400; D_SI=0; D_PEN=80; D_PS=65
D_FC=120; D_VC=80; D_SVR=30.0; D_NL=1
D_LA=5000; D_LR=LOAN_RATE; D_LY=20

def _v(key, default):
    return st.session_state.get(key, default)

def amt(label, key, default, step=1000, help_text=None, max_val=10_000_000_000):
    val = st.number_input(label, min_value=0, max_value=max_val,
                          value=_v(key, default), step=step, key=key, help=help_text)
    if val and val > 0:
        st.caption(f"\U0001f4b0 {amount_to_korean(val)}")
    return val

def amt_s(label, key, default, step=10, help_text=None):
    return amt(label, key, default, step, help_text, 1_000_000)

def encode_params(params):
    try:
        j = json.dumps({k:v for k,v in params.items() if v is not None}, ensure_ascii=False, separators=(',',':'))
        return base64.urlsafe_b64encode(j.encode()).decode()
    except Exception: return ""

PRESETS = {
    "30\ub300 \ub3c5\uc2e0": dict(age=30,retire=60,life=85,infl=2.5,da=1500,dr=2.83,sa=2000,sr=10.0,
        rea=0,rr=2.5,oa=0,sal=300,si=0,pen=50,ps=65,fc=60,vc=60,svr=40.0,nl=0),
    "40\ub300 \uc678\ubc8c\uc774": dict(age=42,retire=60,life=85,infl=2.5,da=5000,dr=2.83,sa=5000,sr=10.0,
        rea=40000,rr=2.5,oa=1000,sal=450,si=0,pen=90,ps=65,fc=150,vc=100,svr=20.0,nl=1,
        la0=25000,lr0=LOAN_RATE,ly0=22),
    "40\ub300 \ub9de\ubc8c\uc774": dict(age=42,retire=58,life=85,infl=2.5,da=8000,dr=2.83,sa=12000,sr=10.0,
        rea=60000,rr=2.5,oa=2000,sal=700,si=50,pen=120,ps=65,fc=200,vc=150,svr=25.0,nl=1,
        la0=35000,lr0=LOAN_RATE,ly0=25),
    "50\ub300 \ub178\ud6c4\uc900\ube44": dict(age=52,retire=60,life=88,infl=2.5,da=15000,dr=2.83,sa=20000,sr=10.0,
        rea=70000,rr=2.5,oa=5000,sal=500,si=0,pen=130,ps=65,fc=150,vc=100,svr=30.0,nl=1,
        la0=8000,lr0=3.5,ly0=8),
}

def apply_preset(preset):
    for k, v in preset.items():
        st.session_state[k] = v
    for ck in ["results","pdf_cache","csv_cache"]:
        st.session_state.pop(ck, None)

def main():
    st.set_page_config(page_title="\uc790\uc0b0 \uace0\uac08 \uc2dc\ubbac\ub808\uc774\ud130", page_icon="\U0001f4ca", layout="centered")
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    dark = st.session_state.dark_mode
    st.markdown(f"<style>{get_css(dark)}</style>", unsafe_allow_html=True)

    _, tc = st.columns([4,1])
    with tc:
        if st.button("\U0001f319 \uc57c\uac04" if not dark else "\u2600\ufe0f \uc8fc\uac04", key="theme_toggle"):
            st.session_state.dark_mode = not dark; st.rerun()

    hc = get_header_color(dark)
    st.markdown(f"<p style='text-align:center;color:{hc};font-size:12px;letter-spacing:4px;font-weight:600;margin-bottom:0'>FINANCIAL RUNWAY</p>", unsafe_allow_html=True)
    st.title("\uc790\uc0b0 \uace0\uac08 \uc2dc\ubbac\ub808\uc774\ud130")
    st.markdown("<p class='subtitle'>\ud604\uc7ac \uc790\uc0b0\uacfc \uc218\uc785\xb7\uc9c0\ucd9c\uc744 \uc785\ub825\ud558\uba74<br>\uc790\uc0b0\uc774 \uc5b8\uc81c \uace0\uac08\ub418\ub294\uc9c0 \uc2dc\ubbac\ub808\uc774\uc158\ud569\ub2c8\ub2e4</p>", unsafe_allow_html=True)

    gsheet_ok = get_gsheet_connection() is not None
    if not gsheet_ok:
        err = st.session_state.get("gsheet_error", "")
        if err: st.caption(f"\u26a0\ufe0f Sheets \ubbf8\uc5f0\uacb0 \u2014 {err}")

    with st.expander("\u26a1 \ube60\ub978 \uc2dc\uc791 \u2014 \ud504\ub9ac\uc14b"):
        r1c1, r1c2 = st.columns(2); r2c1, r2c2 = st.columns(2)
        for col, (name, preset) in zip([r1c1,r1c2,r2c1,r2c2], PRESETS.items()):
            if col.button(name, key=f"p_{name}"):
                apply_preset(preset); st.rerun()

    mode = st.radio("\ubd84\uc11d \ubaa8\ub4dc", ["\uac04\ub2e8 \ubd84\uc11d","\uc0c1\uc138 \ubd84\uc11d"], horizontal=True, label_visibility="collapsed")
    is_simple = mode == "\uac04\ub2e8 \ubd84\uc11d"
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    st.subheader("\U0001f464 \uae30\ubcf8 \uc815\ubcf4")
    age = st.number_input("\ud604\uc7ac \ub098\uc774", min_value=15, max_value=100, value=_v("age",D_AGE), key="age")
    gender = st.selectbox("\uc131\ubcc4", ["\ub0a8\uc131","\uc5ec\uc131"])
    gender_key = "male" if gender=="\ub0a8\uc131" else "female"
    retire_age = st.number_input("\uc740\ud1f4 \ub098\uc774", min_value=30, max_value=100, value=_v("retire",D_RETIRE), key="retire")
    life_exp = st.number_input("\uae30\ub300 \uc218\uba85 (\ud55c\uad6d \ud3c9\uade0 83.7\uc138)", min_value=60, max_value=120, value=_v("life",D_LIFE), key="life")
    inflation_rate = st.number_input("\uc5f0\uac04 \ubb3c\uac00\uc0c1\uc2b9\ub960 (%)", min_value=0.0, max_value=15.0, value=_v("infl",D_INFL), step=0.1, key="infl",
                                     help="\uac04\ub2e8: \uc804\uccb4 \uc9c0\ucd9c | \uc0c1\uc138: \ubcc0\ub3d9\ube44100%+\uace0\uc815\ube5450%")
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    if is_simple:
        st.subheader("\U0001f4b0 \uc790\uc0b0 & \uc218\uc785")
        total_savings = amt("\ucd1d \ubaa8\uc544\ub193\uc740 \uc790\uae08 (\ub9cc\uc6d0)","ts",D_TS,1000,"\uc608\uae08+\uc8fc\uc2dd+\ubd80\ub3d9\uc0b0 \ub4f1")
        monthly_income = amt_s("\uc6d4 \uc218\uc785 \u2014 \uc138\ud6c4 (\ub9cc\uc6d0)","mi",D_MI)
        st.subheader("\U0001f4b8 \uc9c0\ucd9c")
        monthly_expense = amt_s("\uc6d4 \ud3c9\uade0 \uc9c0\ucd9c (\ub9cc\uc6d0)","me",D_ME)
        st.subheader("💰 은퇴 후 소득")
        retire_income = amt_s("은퇴 후 월 소득 (만원)", "ri", 0, 10, "파트타임, 임대 수입 등")
        params = dict(mode="simple",age=age,gender=gender_key,retire_age=retire_age,
                      life_expectancy=life_exp,inflation_rate=inflation_rate,
                      total_savings=total_savings,monthly_income=monthly_income,
                      monthly_expense=monthly_expense,retire_income=retire_income)
    else:
        st.subheader("\U0001f3e6 \ubcf4\uc720 \uc790\uc0b0")
        st.markdown("**\uc608\uae08\xb7\uc801\uae08**")
        deposit_amount = amt("\uc608\uae08 (\ub9cc\uc6d0)","da",D_DA,500,"\ud55c\uad6d \uc608\uae08 \ud3c9\uade0 2.83%")
        deposit_rate = st.number_input("\uc608\uae08 \uc218\uc775\ub960 (%)",min_value=0.0,max_value=20.0,value=_v("dr",D_DR),step=0.1,key="dr")
        st.markdown("**\uc8fc\uc2dd\xb7\ud380\ub4dc\xb7ETF**")
        stock_amount = amt("\uc8fc\uc2dd (\ub9cc\uc6d0)","sa",D_SA,500)
        stock_return = st.number_input("\uae30\ub300 \uc218\uc775\ub960 (%) \u2014 S&P500 \uc7a5\uae30 \ud3c9\uade0 10%",min_value=-20.0,max_value=30.0,value=_v("sr",D_SR),step=0.5,key="sr")
        st.markdown("**\ubd80\ub3d9\uc0b0**")
        real_estate = amt("\ubd80\ub3d9\uc0b0 \uc2dc\uac00 (\ub9cc\uc6d0)","rea",D_REA,5000)
        re_return = st.number_input("\ubd80\ub3d9\uc0b0 \uc0c1\uc2b9\ub960 (%) \u2014 \ud55c\uad6d \uc7a5\uae30 \ud3c9\uade0 2.5%",min_value=-10.0,max_value=20.0,value=_v("rr",D_RR),step=0.5,key="rr")
        other_assets = amt("\uae30\ud0c0 \uc790\uc0b0 (\ub9cc\uc6d0)","oa",D_OA,500,"\ubcf4\ud5d8, \uae08 \ub4f1")
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("\U0001f4c8 \uc218\uc785")
        salary = amt_s("\uc6d4 \uae09\uc5ec \u2014 \uc138\ud6c4 (\ub9cc\uc6d0)","sal",D_SAL)
        side_income = amt_s("\ubd80\uc218\uc785 (\ub9cc\uc6d0/\uc6d4)","si",D_SI)
        pension = amt_s("\uad6d\ubbfc\uc5f0\uae08 \uc608\uc0c1 (\ub9cc\uc6d0/\uc6d4)","pen",D_PEN,5)
        pension_start = st.number_input("\uc5f0\uae08 \uc2dc\uc791 \ub098\uc774",min_value=55,max_value=80,value=_v("ps",D_PS),key="ps")
        retire_income = amt_s("은퇴 후 월 소득 (만원)", "ri", 0, 10, "파트타임, 임대 수입 등")
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("\U0001f4b8 \uc9c0\ucd9c")
        st.info(f"\U0001f4cc \ubb3c\uac00\uc0c1\uc2b9\ub960 {inflation_rate}%: \ubcc0\ub3d9\ube44 100% \xb7 \uace0\uc815\ube44 50%")
        fixed_cost = amt_s("\uc6d4 \uace0\uc815\ube44 (\ub9cc\uc6d0) \u2014 \uc8fc\uac70\xb7\ubcf4\ud5d8\xb7\uad50\uc721","fc",D_FC)
        variable_cost = amt_s("\uc6d4 \ubcc0\ub3d9\ube44 (\ub9cc\uc6d0) \u2014 \uc2dd\ube44\xb7\uad50\ud1b5\xb7\uc5ec\uac00","vc",D_VC)
        savings_rate = st.number_input("\uc800\ucd95\ub960 (%)",min_value=0.0,max_value=100.0,value=_v("svr",D_SVR),step=5.0,key="svr")
        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("\U0001f3e0 \ub300\ucd9c")
        num_loans = st.number_input("\ub300\ucd9c \uac74\uc218",min_value=0,max_value=5,value=_v("nl",D_NL),key="nl")
        loans = []
        for i in range(int(num_loans)):
            with st.expander(f"\ub300\ucd9c {i+1}", expanded=(i==0)):
                la = amt(f"\uc794\uc561 (\ub9cc\uc6d0)",f"la{i}",D_LA,1000)
                lr = st.number_input(f"\uc774\uc790\uc728 (%)",min_value=0.0,max_value=20.0,value=_v(f"lr{i}",D_LR),step=0.1,key=f"lr{i}")
                ly = st.number_input(f"\ub0a8\uc740 \uae30\uac04 (\ub144)",min_value=1,max_value=40,value=_v(f"ly{i}",D_LY),key=f"ly{i}")
                loans.append({"amount":la,"rate":lr,"years":ly})
        params = dict(mode="detailed",age=age,gender=gender_key,retire_age=retire_age,
                      life_expectancy=life_exp,inflation_rate=inflation_rate,
                      deposit_amount=deposit_amount,deposit_rate=deposit_rate,
                      stock_amount=stock_amount,stock_return=stock_return,
                      real_estate_amount=real_estate,real_estate_return=re_return,
                      other_assets=other_assets,salary=salary,side_income=side_income,
                      pension_monthly=pension,pension_start_age=pension_start,
                      fixed_cost=fixed_cost,variable_cost=variable_cost,
                      savings_rate=savings_rate,loans=loans,retire_income=retire_income)

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    if st.button("\U0001f680 \uc2dc\ubbac\ub808\uc774\uc158 \uc2e4\ud589", type="primary"):
        if age >= life_exp:
            st.error("\ud604\uc7ac \ub098\uc774\uac00 \uae30\ub300 \uc218\uba85\ubcf4\ub2e4 \ud06c\uac70\ub098 \uac19\uc2b5\ub2c8\ub2e4."); return
        with st.spinner("\uacc4\uc0b0 \uc911..."):
            try:
                df = run_simulation(params)
                dep_info, peak_info, current_info = get_key_metrics(df, life_exp)
                _, s2, s3 = run_scenarios(params)
                ret5 = run_simulation(params, {"avg_return": 5.0})
                ret10 = run_simulation(params, {"avg_return": 10.0})
                ret15 = run_simulation(params, {"avg_return": 15.0})
                opt, base_sens, pess = run_sensitivity(params)
                fire = calc_fire_index(params)
                safe = calc_safe_withdrawal(params)
            except Exception as e:
                st.error(f"\uacc4\uc0b0 \uc624\ub958: {e}"); return

        scenarios = {
            "\ud604\uc7ac \uacc4\ud68d (\uc740\ud589\uc774\uc790)": df,
            "\ub3d9\uc5f0\ub839 \ud3c9\uade0": df,
            "\uc800\ucd95 \uac15\ud654": s2,
            "\uc740\ud1f4 3\ub144 \uc5f0\uc7a5": s3,
            "\ub9e4\ub144 5% \uc218\uc775": ret5,
            "\ub9e4\ub144 10% \uc218\uc775": ret10,
            "\ub9e4\ub144 15% \uc218\uc775": ret15,
            "실질 순자산 (현재가치)": df,
        }
        st.session_state["results"] = dict(
            df=df, dep_info=dep_info, peak_info=peak_info,
            current_info=current_info, scenarios=scenarios,
            opt=opt, base_sens=base_sens, pess=pess,
            fire=fire, safe=safe, params=params)
        st.session_state.pop("pdf_cache", None)
        st.session_state.pop("csv_cache", None)
        try:
            saved, msg = save_to_gsheet(params,
                {"depletion":dep_info,"peak":peak_info,"current":current_info,"fire":fire,"safe_withdrawal":safe})
            if not saved: st.warning(f"\u26a0\ufe0f Sheets: {msg}")
        except Exception: pass

    if "results" not in st.session_state:
        return

    r = st.session_state["results"]
    df=r["df"]; dep_info=r["dep_info"]; peak_info=r["peak_info"]
    current_info=r["current_info"]; scenarios=r["scenarios"]
    opt=r["opt"]; base_sens=r["base_sens"]; pess=r["pess"]
    fire=r["fire"]; safe=r["safe"]; params=r["params"]

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    st.subheader("\U0001f4cb \ubd84\uc11d \uacb0\uacfc")
    m1, m2 = st.columns(2)
    if dep_info:
        m1.metric("\u26a0\ufe0f \uc790\uc0b0 \uace0\uac08",f"{dep_info['year']}\ub144",f"{dep_info['age']}\uc138",delta_color="inverse")
    else:
        m1.metric("\u2705 \uc790\uc0b0 \uace0\uac08","\uace0\uac08 \uc5c6\uc74c",f"{params['life_expectancy']}\uc138\uae4c\uc9c0 \uc548\uc804")
    m2.metric("\U0001f4c8 \ucd5c\ub300 \uc790\uc0b0",fmt_krw(peak_info["net_worth"]),
              f"{peak_info['year']}\ub144 ({peak_info['age']}\uc138)")

    diff = current_info["net_worth"]-current_info["avg_peer"]
    avg = current_info["avg_peer"]
    pct_val = round(current_info["net_worth"]/avg*100) if avg and avg!=0 else 0
    gc,rc = get_diff_colors(dark); dc = gc if diff>=0 else rc
    sign="+" if diff>=0 else ""; emoji="\U0001f4c8" if diff>=0 else "\U0001f4c9"
    bg_c = 'rgba(99,102,241,0.06)' if dark else 'rgba(79,70,229,0.04)'
    bd_c = 'rgba(99,102,241,0.15)' if dark else 'rgba(79,70,229,0.12)'
    sub_c = '#71717a' if dark else '#64748b'
    st.markdown(f"""<div style="background:{bg_c};border:1px solid {bd_c};
    border-radius:14px;padding:14px 16px;margin:12px 0;display:flex;
    justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <div><div style="font-size:12px;color:{sub_c}">\ub3d9\uc5f0\ub839\xb7\ub3d9\uc131 \ud3c9\uade0 \ub300\ube44</div>
        <div style="font-size:17px;font-weight:700;color:{dc}">{sign}{fmt_krw(diff)} ({pct_val}%)</div></div>
        <div style="font-size:32px">{emoji}</div></div>""", unsafe_allow_html=True)

    f1, f2 = st.columns(2)
    with f1:
        yl = fire.get("years_left",-1)
        if yl==0: st.metric("\U0001f525 FIRE","\ub2ec\uc131!",f"\ubaa9\ud45c: {fmt_krw(fire.get('target',0))}")
        elif yl<0: st.metric("\U0001f525 FIRE","\ub3c4\ub2ec \ubd88\uac00","\uc800\ucd95\uc561 \ubd80\uc871")
        else: st.metric("\U0001f525 FIRE\uae4c\uc9c0",f"{yl}\ub144",f"\uc9c4\ud589\ub960 {fire.get('progress',0)}%")
    with f2:
        sm = safe.get("safe_monthly",0) if safe else 0
        sy = safe.get("years",0) if safe else 0
        if sm>0: st.metric("\U0001f4b3 \uc548\uc804 \uc778\ucd9c",f"{sm:,}\ub9cc\uc6d0/\uc6d4",f"\uc740\ud1f4 \ud6c4 {sy}\ub144\uac04")
        else: st.metric("\U0001f4b3 \uc548\uc804 \uc778\ucd9c","\uacc4\uc0b0 \ubd88\uac00","\uc740\ud1f4 \uc2dc \uc790\uc0b0 \ubd80\uc871")

    pcfg = {"displayModeBar":False,"scrollZoom":False}

    try:
        fig_pie = chart_pie(params, dark)
        if fig_pie:
            st.subheader("\U0001f967 \ud604\uc7ac \uc790\uc0b0 \uad6c\uc131")
            st.plotly_chart(fig_pie, use_container_width=True, config=pcfg)
    except Exception: pass

    # ━━ 통합 순자산 추이 & 시나리오 비교 ━━
    try:
        st.subheader("\U0001f4ca \uc21c\uc790\uc0b0 \ucd94\uc774 & \uc2dc\ub098\ub9ac\uc624 \ube44\uad50")
        all_labels = ALL_SCENARIO_LABELS
        default_on = ["\ud604\uc7ac \uacc4\ud68d (\uc740\ud589\uc774\uc790)", "\ub3d9\uc5f0\ub839 \ud3c9\uade0"]
        selected = st.multiselect("\ud45c\uc2dc\ud560 \uc2dc\ub098\ub9ac\uc624", options=all_labels, default=default_on, key="scenario_toggle")
        if selected:
            fig = chart_combined(scenarios, selected, params["retire_age"], dep_info, dark)
            st.plotly_chart(fig, use_container_width=True, config=pcfg)
            parts = []
            for label in selected:
                if label == "\ub3d9\uc5f0\ub839 \ud3c9\uade0": continue
                sdf = scenarios.get(label)
                if sdf is None: continue
                dm, _, _ = get_key_metrics(sdf, params["life_expectancy"])
                txt = "\uace0\uac08 \uc5c6\uc74c \u2705" if not dm else f"{dm['year']}\ub144 ({dm['age']}\uc138)"
                parts.append(f"{label}: {txt}")
            if parts: st.info(" | ".join(parts))
        else:
            st.info("\uc704\uc5d0\uc11c \uc2dc\ub098\ub9ac\uc624\ub97c \ud558\ub098 \uc774\uc0c1 \uc120\ud0dd\ud558\uc138\uc694")
    except Exception as e:
        st.warning(f"\ucc28\ud2b8 \uc624\ub958: {e}")

    try:
        fig_comp = chart_composition(df, dark)
        if fig_comp:
            st.subheader("\U0001f3d7\ufe0f \uc790\uc0b0 \uad6c\uc131 \ubcc0\ud654")
            st.plotly_chart(fig_comp, use_container_width=True, config=pcfg)
    except Exception: pass

    try:
        st.subheader("\U0001f4b0 \uc6d4 \uc218\uc785 vs \uc9c0\ucd9c")
        st.plotly_chart(chart_cashflow(params, dark), use_container_width=True, config=pcfg)
    except Exception: pass

    try:
        st.subheader("\U0001f4c9 \ubbfc\uac10\ub3c4 \ubd84\uc11d")
        st.plotly_chart(chart_sensitivity(opt, base_sens, pess, dark), use_container_width=True, config=pcfg)
    except Exception: pass

    try:
        if params.get("inflation_rate",0) > 0:
            with st.expander("\U0001f4c8 \ubb3c\uac00\uc0c1\uc2b9\ub960 \uc601\ud5a5 \uc0c1\uc138"):
                el_ret=params["retire_age"]-params["age"]; el_end=params["life_expectancy"]-params["age"]
                ir = params["inflation_rate"]/100
                if params["mode"]=="simple":
                    ne=params["monthly_expense"]
                    st.markdown(f"| \uc2dc\uc810 | \uc6d4 \uc9c0\ucd9c |\n|---|---:|\n| \ud604\uc7ac | **{ne:,.0f}**\ub9cc\uc6d0 |\n"
                                f"| \uc740\ud1f4({params['retire_age']}\uc138) | **{ne*((1+ir)**el_ret):,.0f}**\ub9cc\uc6d0 |\n"
                                f"| {params['life_expectancy']}\uc138 | **{ne*((1+ir)**el_end):,.0f}**\ub9cc\uc6d0 |")
                else:
                    nv=params["variable_cost"]; nf=params["fixed_cost"]
                    rv_=nv*((1+ir)**el_ret); rf=nf*((1+ir*0.5)**el_ret)
                    ev=nv*((1+ir)**el_end); ef=nf*((1+ir*0.5)**el_end)
                    st.markdown(f"| \uad6c\ubd84 | \ud604\uc7ac | \uc740\ud1f4({params['retire_age']}\uc138) | {params['life_expectancy']}\uc138 |\n|---|---:|---:|---:|\n"
                                f"| \ubcc0\ub3d9\ube44 | {nv:,.0f}\ub9cc | {rv_:,.0f}\ub9cc | {ev:,.0f}\ub9cc |\n"
                                f"| \uace0\uc815\ube44 | {nf:,.0f}\ub9cc | {rf:,.0f}\ub9cc | {ef:,.0f}\ub9cc |\n"
                                f"| **\ud569\uacc4** | **{nv+nf:,.0f}\ub9cc** | **{rv_+rf:,.0f}\ub9cc** | **{ev+ef:,.0f}\ub9cc** |")
    except Exception: pass

    try:
        st.subheader("\U0001f4cb \uc8fc\uc694 \uc2dc\uc810")
        m_ages = sorted(set([params["age"],params["retire_age"],65,70,80,params["life_expectancy"]]))
        m_df = df[df["age"].isin(m_ages)].copy(); m_df["\ucc28\uc774"]=m_df["net_worth"]-m_df["avg_peer"]
        disp = m_df[["year","age","net_worth","avg_peer","\ucc28\uc774"]].copy()
        disp.columns = ["\uc5f0\ub3c4","\ub098\uc774","\ub0b4 \uc21c\uc790\uc0b0","\ub3d9\uc5f0\ub839 \ud3c9\uade0","\ucc28\uc774"]
        st.dataframe(disp.style.format({"\ub0b4 \uc21c\uc790\uc0b0":"{:,.0f}","\ub3d9\uc5f0\ub839 \ud3c9\uade0":"{:,.0f}","\ucc28\uc774":"{:+,.0f}"}),
                     use_container_width=True, hide_index=True)
    except Exception: pass

    st.subheader("\U0001f4e5 \ubcf4\uace0\uc11c & \ub370\uc774\ud130")
    if "pdf_cache" not in st.session_state:
        try:
            chart_imgs = generate_chart_images_for_pdf(
                df, params, dep_info, params["retire_age"],
                scenarios_dict=scenarios, base_df=df, opt_df=opt, pess_df=pess)
            st.session_state["pdf_cache"] = generate_pdf_report(
                df, params, dep_info, peak_info, current_info, chart_imgs)
        except Exception as e:
            st.error(f"PDF \uc0dd\uc131 \uc624\ub958: {e}")
            st.session_state["pdf_cache"] = None
    if st.session_state.get("pdf_cache"):
        st.download_button("\U0001f4c4 PDF \ubcf4\uace0\uc11c \ub2e4\uc6b4\ub85c\ub4dc (\ucc28\ud2b8 \ud3ec\ud568)",
            st.session_state["pdf_cache"],
            f"\uc790\uc0b0\uc2dc\ubbac\ub808\uc774\uc158_{datetime.now().strftime('%Y%m%d')}.pdf",
            "application/pdf", use_container_width=True)
    if "csv_cache" not in st.session_state:
        st.session_state["csv_cache"] = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("\U0001f4ca CSV \ub2e4\uc6b4\ub85c\ub4dc", st.session_state["csv_cache"],
        f"\uc790\uc0b0\uc2dc\ubbac\ub808\uc774\uc158_{datetime.now().strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)

    st.subheader("\U0001f517 \uacf5\uc720")
    st.code(f"?d={encode_params(params)}", language=None)
    st.caption("\uc704 \ud30c\ub77c\ubbf8\ud130\ub97c \uc571 URL \ub4a4\uc5d0 \ubd99\uc774\uba74 \ub3d9\uc77c \uc124\uc815\uc73c\ub85c \uacf5\uc720 \uac00\ub2a5")

    with st.expander("\uc804\uccb4 \ub370\uc774\ud130"):
        fd = {"net_worth":"{:,.0f}","avg_peer":"{:,.0f}"}
        if "deposit" in df.columns:
            fd.update({"deposit":"{:,.0f}","stock":"{:,.0f}","real_estate":"{:,.0f}","loan":"{:,.0f}"})
        st.dataframe(df.style.format(fd), use_container_width=True, height=300)

    st.caption(f"\ubcf8 \uc2dc\ubbac\ub808\uc774\uc158\uc740 \ucc38\uace0\uc6a9\uc774\uba70 \uc2e4\uc81c \ud22c\uc790 \uc131\uacfc\uc640 \ub2e4\ub97c \uc218 \uc788\uc2b5\ub2c8\ub2e4. "
               f"\ud55c\uad6d\uc740\ud589 2026.2 \uc608\uae08 {DEP_RATE}%, \ub300\ucd9c {LOAN_RATE}%. \ud3c9\uade0\uc790\uc0b0: 2025 \uac00\uacc4\uae08\uc735\ubcf5\uc9c0\uc870\uc0ac.")

if __name__ == "__main__":
    main()
