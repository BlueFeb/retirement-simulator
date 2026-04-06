import streamlit as st
import pandas as pd
import json, base64
from datetime import datetime

from engine import (run_simulation, get_key_metrics, run_scenarios,
                    run_sensitivity, calc_fire_index, calc_safe_withdrawal,
                    fmt_krw, amount_to_korean, DEP_RATE, LOAN_RATE)
from charts import (chart_main, chart_composition, chart_pie, chart_cashflow,
                     chart_scenarios, chart_sensitivity,
                     generate_chart_images_for_pdf)
from report_pdf import generate_pdf_report
from gsheet import get_gsheet_connection, save_to_gsheet
from theme import get_css, get_header_color, get_diff_colors


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 기본값 — session_state 키와 1:1 매핑
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DEFAULTS = dict(
    age=35, retire=60, life=85, infl=2.5,
    ts=10000, mi=400, me=250,
    da=3000, dr=DEP_RATE, sa=4000, sr=7.0,
    rea=30000, rr=3.0, oa=0,
    sal=400, si=0, pen=80, ps=65,
    fc=120, vc=80, svr=30.0, nl=1,
    la0=5000, lr0=LOAN_RATE, ly0=20,
)


def init_defaults():
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 프리셋 — session_state 키와 동일한 이름 사용
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRESETS = {
    "30대 독신": dict(
        age=30, retire=60, life=85, infl=2.5,
        da=1500, dr=DEP_RATE, sa=2000, sr=7.0,
        rea=0, rr=3.0, oa=0,
        sal=300, si=0, pen=50, ps=65,
        fc=60, vc=60, svr=40.0, nl=0),
    "40대 외벌이": dict(
        age=42, retire=60, life=85, infl=2.5,
        da=5000, dr=DEP_RATE, sa=5000, sr=6.0,
        rea=40000, rr=2.5, oa=1000,
        sal=450, si=0, pen=90, ps=65,
        fc=150, vc=100, svr=20.0, nl=1,
        la0=25000, lr0=LOAN_RATE, ly0=22),
    "40대 맞벌이": dict(
        age=42, retire=58, life=85, infl=2.5,
        da=8000, dr=DEP_RATE, sa=12000, sr=7.0,
        rea=60000, rr=3.0, oa=2000,
        sal=700, si=50, pen=120, ps=65,
        fc=200, vc=150, svr=25.0, nl=1,
        la0=35000, lr0=LOAN_RATE, ly0=25),
    "50대 노후준비": dict(
        age=52, retire=60, life=88, infl=2.5,
        da=15000, dr=DEP_RATE, sa=20000, sr=5.0,
        rea=70000, rr=2.0, oa=5000,
        sal=500, si=0, pen=130, ps=65,
        fc=150, vc=100, svr=30.0, nl=1,
        la0=8000, lr0=3.5, ly0=8),
}


def apply_preset(preset):
    """프리셋 → session_state. 위젯 key와 동일한 이름이므로 충돌 없음."""
    for k, v in preset.items():
        st.session_state[k] = v
    # 결과 캐시 초기화
    for ck in ["results", "pdf_cache", "csv_cache"]:
        st.session_state.pop(ck, None)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 금액 입력 + 한글 표시
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def amt(label, key, step=1000, help_text=None, max_val=10_000_000_000):
    """number_input wrapper — default는 session_state에서만 관리."""
    val = st.number_input(label, min_value=0, max_value=max_val, step=step, key=key, help=help_text)
    if val and val > 0:
        st.caption(f"💰 {amount_to_korean(val)}")
    return val

def amt_s(label, key, step=10, help_text=None):
    return amt(label, key, step, help_text, 1_000_000)


def encode_params(params):
    try:
        j = json.dumps({k:v for k,v in params.items() if v is not None}, ensure_ascii=False, separators=(',',':'))
        return base64.urlsafe_b64encode(j.encode()).decode()
    except Exception:
        return ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    st.set_page_config(page_title="자산 고갈 시뮬레이터", page_icon="📊", layout="centered")
    init_defaults()

    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    dark = st.session_state.dark_mode

    st.markdown(f"<style>{get_css(dark)}</style>", unsafe_allow_html=True)

    # 테마 토글
    _, tc = st.columns([4,1])
    with tc:
        if st.button("🌙 야간" if not dark else "☀️ 주간", key="theme_toggle"):
            st.session_state.dark_mode = not dark
            st.rerun()

    # 헤더
    hc = get_header_color(dark)
    st.markdown(f"<p style='text-align:center;color:{hc};font-size:12px;letter-spacing:4px;"
                f"font-weight:600;margin-bottom:0'>FINANCIAL RUNWAY</p>", unsafe_allow_html=True)
    st.title("자산 고갈 시뮬레이터")
    st.markdown("<p class='subtitle'>현재 자산과 수입·지출을 입력하면<br>"
                "자산이 언제 고갈되는지 시뮬레이션합니다</p>", unsafe_allow_html=True)

    # Sheets — 에러일 때만 표시
    gsheet_ok = get_gsheet_connection() is not None
    if not gsheet_ok:
        err = st.session_state.get("gsheet_error", "")
        if err:
            st.caption(f"⚠️ Sheets 미연결 — {err}")

    # 프리셋 (4개 → 2x2로 모바일 대응)
    with st.expander("⚡ 빠른 시작 — 프리셋"):
        r1c1, r1c2 = st.columns(2)
        r2c1, r2c2 = st.columns(2)
        preset_items = list(PRESETS.items())
        for col, (name, preset) in zip([r1c1, r1c2, r2c1, r2c2], preset_items):
            if col.button(name, key=f"p_{name}"):
                apply_preset(preset)
                st.rerun()

    # 모드 — session_state 충돌 방지: key 없이 사용
    mode_options = ["간단 분석", "상세 분석"]
    mode = st.radio("분석 모드", mode_options, horizontal=True, label_visibility="collapsed")
    is_simple = mode == "간단 분석"

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ━━ 입력 ━━
    st.subheader("👤 기본 정보")
    age = st.number_input("현재 나이", min_value=15, max_value=100, key="age")
    gender = st.selectbox("성별", ["남성","여성"])
    gender_key = "male" if gender=="남성" else "female"
    retire_age = st.number_input("은퇴 나이", min_value=30, max_value=100, key="retire")
    life_exp = st.number_input("기대 수명 (한국 평균 83.7세)", min_value=60, max_value=120, key="life")
    inflation_rate = st.number_input("연간 물가상승률 (%)", min_value=0.0, max_value=15.0, step=0.1, key="infl",
                                     help="간단: 전체 지출 | 상세: 변동비100%+고정비50%")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    if is_simple:
        st.subheader("💰 자산 & 수입")
        total_savings = amt("총 모아놓은 자금 (만원)", "ts", 1000, "예금+주식+부동산 등")
        monthly_income = amt_s("월 수입 — 세후 (만원)", "mi")
        st.subheader("💸 지출")
        monthly_expense = amt_s("월 평균 지출 (만원)", "me")
        params = dict(mode="simple", age=age, gender=gender_key, retire_age=retire_age,
                      life_expectancy=life_exp, inflation_rate=inflation_rate,
                      total_savings=total_savings, monthly_income=monthly_income,
                      monthly_expense=monthly_expense)
    else:
        st.subheader("🏦 보유 자산")
        st.markdown("**예금·적금**")
        deposit_amount = amt("예금 (만원)", "da", 500, f"평균 금리 {DEP_RATE}%")
        deposit_rate = st.number_input("예금 수익률 (%)", min_value=0.0, max_value=20.0, step=0.1, key="dr")
        st.markdown("**주식·펀드·ETF**")
        stock_amount = amt("주식 (만원)", "sa", 500)
        stock_return = st.number_input("기대 수익률 (%)", min_value=-20.0, max_value=30.0, step=0.5, key="sr")
        st.markdown("**부동산**")
        real_estate = amt("부동산 시가 (만원)", "rea", 5000)
        re_return = st.number_input("부동산 상승률 (%)", min_value=-10.0, max_value=20.0, step=0.5, key="rr")
        other_assets = amt("기타 자산 (만원)", "oa", 500, "보험, 금 등")

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("📈 수입")
        salary = amt_s("월 급여 — 세후 (만원)", "sal")
        side_income = amt_s("부수입 (만원/월)", "si")
        pension = amt_s("국민연금 예상 (만원/월)", "pen", 5)
        pension_start = st.number_input("연금 시작 나이", min_value=55, max_value=80, key="ps")

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("💸 지출")
        st.info(f"📌 물가상승률 {inflation_rate}%: 변동비 100% · 고정비 50%")
        fixed_cost = amt_s("월 고정비 (만원) — 주거·보험·교육", "fc")
        variable_cost = amt_s("월 변동비 (만원) — 식비·교통·여가", "vc")
        savings_rate = st.number_input("저축률 (%)", min_value=0.0, max_value=100.0, step=5.0, key="svr")

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("🏠 대출")
        num_loans = st.number_input("대출 건수", min_value=0, max_value=5, key="nl")
        loans = []
        for i in range(int(num_loans)):
            # 새 대출 슬롯의 기본값 보장
            if f"la{i}" not in st.session_state: st.session_state[f"la{i}"] = 5000
            if f"lr{i}" not in st.session_state: st.session_state[f"lr{i}"] = LOAN_RATE
            if f"ly{i}" not in st.session_state: st.session_state[f"ly{i}"] = 20
            with st.expander(f"대출 {i+1}", expanded=(i==0)):
                la = amt(f"잔액 (만원)", f"la{i}", 1000)
                lr = st.number_input(f"이자율 (%)", min_value=0.0, max_value=20.0, step=0.1, key=f"lr{i}")
                ly = st.number_input(f"남은 기간 (년)", min_value=1, max_value=40, key=f"ly{i}")
                loans.append({"amount":la, "rate":lr, "years":ly})

        params = dict(mode="detailed", age=age, gender=gender_key, retire_age=retire_age,
                      life_expectancy=life_exp, inflation_rate=inflation_rate,
                      deposit_amount=deposit_amount, deposit_rate=deposit_rate,
                      stock_amount=stock_amount, stock_return=stock_return,
                      real_estate_amount=real_estate, real_estate_return=re_return,
                      other_assets=other_assets, salary=salary, side_income=side_income,
                      pension_monthly=pension, pension_start_age=pension_start,
                      fixed_cost=fixed_cost, variable_cost=variable_cost,
                      savings_rate=savings_rate, loans=loans)

    # ━━ 실행 ━━
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    if st.button("🚀 시뮬레이션 실행", type="primary"):
        if age >= life_exp:
            st.error("현재 나이가 기대 수명보다 크거나 같습니다.")
            return

        with st.spinner("계산 중..."):
            try:
                df = run_simulation(params)
                dep_info, peak_info, current_info = get_key_metrics(df, life_exp)
                base, s2, s3 = run_scenarios(params)
                opt, base_sens, pess = run_sensitivity(params)
                fire = calc_fire_index(params)
                safe = calc_safe_withdrawal(params)
            except Exception as e:
                st.error(f"계산 오류: {e}")
                return

        st.session_state["results"] = dict(
            df=df, dep_info=dep_info, peak_info=peak_info,
            current_info=current_info, base=base, s2=s2, s3=s3,
            opt=opt, base_sens=base_sens, pess=pess,
            fire=fire, safe=safe, params=params)
        st.session_state.pop("pdf_cache", None)
        st.session_state.pop("csv_cache", None)

        # Sheets — 에러만 표시
        try:
            saved, msg = save_to_gsheet(params,
                {"depletion":dep_info,"peak":peak_info,"current":current_info,"fire":fire,"safe_withdrawal":safe})
            if not saved:
                st.warning(f"⚠️ Sheets: {msg}")
        except Exception:
            pass  # Sheets 에러로 앱이 죽지 않도록

    # ━━ 결과 표시 ━━
    if "results" not in st.session_state:
        return

    r = st.session_state["results"]
    df = r["df"]; dep_info = r["dep_info"]; peak_info = r["peak_info"]
    current_info = r["current_info"]; base = r["base"]; s2 = r["s2"]; s3 = r["s3"]
    opt = r["opt"]; base_sens = r["base_sens"]; pess = r["pess"]
    fire = r["fire"]; safe = r["safe"]; params = r["params"]

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # 요약
    st.subheader("📋 분석 결과")
    m1, m2 = st.columns(2)
    if dep_info:
        m1.metric("⚠️ 자산 고갈", f"{dep_info['year']}년", f"{dep_info['age']}세", delta_color="inverse")
    else:
        m1.metric("✅ 자산 고갈", "고갈 없음", f"{params['life_expectancy']}세까지 안전")
    m2.metric("📈 최대 자산", fmt_krw(peak_info["net_worth"]),
              f"{peak_info['year']}년 ({peak_info['age']}세)")

    # 동연령 비교
    diff = current_info["net_worth"] - current_info["avg_peer"]
    avg = current_info["avg_peer"]
    pct_val = round(current_info["net_worth"] / avg * 100) if avg and avg != 0 else 0
    gc, rc = get_diff_colors(dark)
    dc = gc if diff >= 0 else rc
    sign = "+" if diff >= 0 else ""
    emoji = "📈" if diff >= 0 else "📉"
    bg_c = 'rgba(99,102,241,0.06)' if dark else 'rgba(79,70,229,0.04)'
    bd_c = 'rgba(99,102,241,0.15)' if dark else 'rgba(79,70,229,0.12)'
    sub_c = '#71717a' if dark else '#64748b'
    st.markdown(f"""<div style="background:{bg_c};border:1px solid {bd_c};
    border-radius:14px;padding:14px 16px;margin:12px 0;display:flex;
    justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
        <div><div style="font-size:12px;color:{sub_c}">동연령·동성 평균 대비</div>
        <div style="font-size:17px;font-weight:700;color:{dc}">{sign}{fmt_krw(diff)} ({pct_val}%)</div></div>
        <div style="font-size:32px">{emoji}</div></div>""", unsafe_allow_html=True)

    # FIRE + 안전인출
    f1, f2 = st.columns(2)
    with f1:
        yl = fire.get("years_left", -1)
        if yl == 0:
            st.metric("🔥 FIRE", "달성!", f"목표: {fmt_krw(fire.get('target',0))}")
        elif yl < 0:
            st.metric("🔥 FIRE", "도달 불가", "저축액 부족")
        else:
            st.metric("🔥 FIRE까지", f"{yl}년", f"진행률 {fire.get('progress',0)}%")
    with f2:
        sm = safe.get("safe_monthly", 0) if safe else 0
        sy = safe.get("years", 0) if safe else 0
        if sm > 0:
            st.metric("💳 안전 인출", f"{sm:,}만원/월", f"은퇴 후 {sy}년간")
        else:
            st.metric("💳 안전 인출", "계산 불가", "은퇴 시 자산 부족")

    # 차트
    pcfg = {"displayModeBar": False, "scrollZoom": False}

    try:
        fig_pie = chart_pie(params, dark)
        if fig_pie:
            st.subheader("🥧 현재 자산 구성")
            st.plotly_chart(fig_pie, use_container_width=True, config=pcfg)
    except Exception:
        pass

    try:
        st.subheader("📊 순자산 추이")
        fig_main = chart_main(df, params["retire_age"], dep_info, dark)
        st.plotly_chart(fig_main, use_container_width=True, config=pcfg)
    except Exception as e:
        st.warning(f"차트 오류: {e}")

    try:
        fig_comp = chart_composition(df, dark)
        if fig_comp:
            st.subheader("🏗️ 자산 구성 변화")
            st.plotly_chart(fig_comp, use_container_width=True, config=pcfg)
    except Exception:
        pass

    try:
        st.subheader("💰 월 수입 vs 지출")
        st.plotly_chart(chart_cashflow(params, dark), use_container_width=True, config=pcfg)
    except Exception:
        pass

    try:
        st.subheader("🔀 시나리오 비교")
        st.caption("① 현재 계획 · ② 저축 강화 · ③ 은퇴 3년 연장")
        st.plotly_chart(chart_scenarios(base, s2, s3, params["retire_age"], dark),
                        use_container_width=True, config=pcfg)
        d2_m, _, _ = get_key_metrics(s2, params["life_expectancy"])
        d3_m, _, _ = get_key_metrics(s3, params["life_expectancy"])
        d2_txt = "고갈 없음 ✅" if not d2_m else f"{d2_m['year']}년 ({d2_m['age']}세)"
        d3_txt = "고갈 없음 ✅" if not d3_m else f"{d3_m['year']}년 ({d3_m['age']}세)"
        st.info(f"저축 강화: {d2_txt} | 은퇴 연장: {d3_txt}")
    except Exception:
        pass

    try:
        st.subheader("📉 민감도 분석")
        st.plotly_chart(chart_sensitivity(opt, base_sens, pess, dark),
                        use_container_width=True, config=pcfg)
    except Exception:
        pass

    # 물가 영향
    try:
        if params.get("inflation_rate", 0) > 0:
            with st.expander("📈 물가상승률 영향 상세"):
                el_ret = params["retire_age"] - params["age"]
                el_end = params["life_expectancy"] - params["age"]
                ir = params["inflation_rate"] / 100
                if params["mode"] == "simple":
                    ne = params["monthly_expense"]
                    re_exp = ne * ((1+ir)**el_ret)
                    end_exp = ne * ((1+ir)**el_end)
                    st.markdown(f"| 시점 | 월 지출 |\n|---|---:|\n"
                                f"| 현재 | **{ne:,.0f}**만원 |\n"
                                f"| 은퇴({params['retire_age']}세) | **{re_exp:,.0f}**만원 |\n"
                                f"| {params['life_expectancy']}세 | **{end_exp:,.0f}**만원 |")
                else:
                    nv = params["variable_cost"]; nf = params["fixed_cost"]
                    rv = nv*((1+ir)**el_ret); rf = nf*((1+ir*0.5)**el_ret)
                    ev = nv*((1+ir)**el_end); ef = nf*((1+ir*0.5)**el_end)
                    st.markdown(
                        f"| 구분 | 현재 | 은퇴({params['retire_age']}세) | {params['life_expectancy']}세 |\n"
                        f"|---|---:|---:|---:|\n"
                        f"| 변동비 | {nv:,.0f}만 | {rv:,.0f}만 | {ev:,.0f}만 |\n"
                        f"| 고정비 | {nf:,.0f}만 | {rf:,.0f}만 | {ef:,.0f}만 |\n"
                        f"| **합계** | **{nv+nf:,.0f}만** | **{rv+rf:,.0f}만** | **{ev+ef:,.0f}만** |")
    except Exception:
        pass

    # 주요 시점 테이블
    try:
        st.subheader("📋 주요 시점")
        m_ages = sorted(set([params["age"], params["retire_age"], 65, 70, 80, params["life_expectancy"]]))
        m_df = df[df["age"].isin(m_ages)].copy()
        m_df["차이"] = m_df["net_worth"] - m_df["avg_peer"]
        disp = m_df[["year","age","net_worth","avg_peer","차이"]].copy()
        disp.columns = ["연도","나이","내 순자산","동연령 평균","차이"]
        st.dataframe(disp.style.format({"내 순자산":"{:,.0f}","동연령 평균":"{:,.0f}","차이":"{:+,.0f}"}),
                     use_container_width=True, hide_index=True)
    except Exception:
        pass

    # ━━ 다운로드 ━━
    st.subheader("📥 보고서 & 데이터")

    # PDF 캐싱
    if "pdf_cache" not in st.session_state:
        try:
            chart_imgs = generate_chart_images_for_pdf(
                df, params, dep_info, params["retire_age"],
                base_df=base, s2_df=s2, s3_df=s3, opt_df=opt, pess_df=pess)
            st.session_state["pdf_cache"] = generate_pdf_report(
                df, params, dep_info, peak_info, current_info, chart_imgs)
        except Exception as e:
            st.error(f"PDF 생성 오류: {e}")
            st.session_state["pdf_cache"] = None

    if st.session_state.get("pdf_cache"):
        st.download_button("📄 PDF 보고서 다운로드 (차트 포함)",
            st.session_state["pdf_cache"],
            f"자산시뮬레이션_{datetime.now().strftime('%Y%m%d')}.pdf",
            "application/pdf", use_container_width=True)

    # CSV 캐싱
    if "csv_cache" not in st.session_state:
        st.session_state["csv_cache"] = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button("📊 CSV 다운로드",
        st.session_state["csv_cache"],
        f"자산시뮬레이션_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv", use_container_width=True)

    # 공유
    st.subheader("🔗 공유")
    st.code(f"?d={encode_params(params)}", language=None)
    st.caption("위 파라미터를 앱 URL 뒤에 붙이면 동일 설정으로 공유 가능")

    with st.expander("전체 데이터"):
        fd = {"net_worth":"{:,.0f}", "avg_peer":"{:,.0f}"}
        if "deposit" in df.columns:
            fd.update({"deposit":"{:,.0f}","stock":"{:,.0f}","real_estate":"{:,.0f}","loan":"{:,.0f}"})
        st.dataframe(df.style.format(fd), use_container_width=True, height=300)

    st.caption(f"본 시뮬레이션은 참고용이며 실제 투자 성과와 다를 수 있습니다. "
               f"한국은행 2026.2 예금 {DEP_RATE}%, 대출 {LOAN_RATE}%. 평균자산: 2025 가계금융복지조사.")


if __name__ == "__main__":
    main()
