import streamlit as st
import pandas as pd
import json, base64, urllib.parse
from datetime import datetime

from engine import (run_simulation, get_key_metrics, run_scenarios,
                    run_sensitivity, calc_fire_index, calc_safe_withdrawal,
                    fmt_krw, amount_to_korean, DEP_RATE, LOAN_RATE)
from charts import (chart_main, chart_composition, chart_pie, chart_cashflow,
                     chart_scenarios, chart_sensitivity, fig_to_image_bytes)
from report_pdf import generate_pdf_report
from gsheet import get_gsheet_connection, save_to_gsheet
from theme import get_css, get_header_color, get_diff_colors


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 헬퍼
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def amt(label, key, default, step=1000, help_text=None, max_val=10_000_000_000):
    val = st.number_input(label, 0, max_val, default, step=step, key=key, help=help_text)
    if val > 0: st.caption(f"💰 {amount_to_korean(val)}")
    return val

def amt_s(label, key, default, step=10, help_text=None):
    return amt(label, key, default, step, help_text, max_val=1_000_000)

def encode_params(params):
    """입력값을 URL-safe base64로 인코딩."""
    try:
        clean = {k: v for k, v in params.items() if v is not None}
        j = json.dumps(clean, ensure_ascii=False, separators=(',',':'))
        return base64.urlsafe_b64encode(j.encode()).decode()
    except Exception:
        return ""

def decode_params(encoded):
    """URL 파라미터에서 입력값 복원."""
    try:
        j = base64.urlsafe_b64decode(encoded.encode()).decode()
        return json.loads(j)
    except Exception:
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 프리셋
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRESETS = {
    "30대 직장인": dict(
        mode="detailed", age=32, gender="male", retire_age=60, life_expectancy=85,
        inflation_rate=2.5, deposit_amount=2000, deposit_rate=DEP_RATE,
        stock_amount=3000, stock_return=7.0, real_estate_amount=0,
        real_estate_return=3.0, other_assets=0, salary=350, side_income=0,
        pension_monthly=60, pension_start_age=65, fixed_cost=80, variable_cost=70,
        savings_rate=35, loans=[]),
    "40대 맞벌이": dict(
        mode="detailed", age=42, gender="male", retire_age=58, life_expectancy=85,
        inflation_rate=2.5, deposit_amount=5000, deposit_rate=DEP_RATE,
        stock_amount=8000, stock_return=7.0, real_estate_amount=50000,
        real_estate_return=3.0, other_assets=1000, salary=600, side_income=50,
        pension_monthly=100, pension_start_age=65, fixed_cost=180, variable_cost=120,
        savings_rate=25, loans=[{"amount":30000,"rate":LOAN_RATE,"years":25}]),
    "50대 은퇴준비": dict(
        mode="detailed", age=52, gender="male", retire_age=60, life_expectancy=88,
        inflation_rate=2.5, deposit_amount=10000, deposit_rate=DEP_RATE,
        stock_amount=15000, stock_return=5.0, real_estate_amount=60000,
        real_estate_return=2.0, other_assets=5000, salary=500, side_income=0,
        pension_monthly=120, pension_start_age=65, fixed_cost=150, variable_cost=100,
        savings_rate=30, loans=[{"amount":10000,"rate":3.5,"years":8}]),
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 메인 앱
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    st.set_page_config(page_title="자산 고갈 시뮬레이터", page_icon="📊", layout="centered")

    # ── 다크/라이트 모드 ──
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    dark = st.session_state.dark_mode

    st.markdown(f"<style>{get_css(dark)}</style>"
                '<meta name="viewport" content="width=device-width, initial-scale=1, '
                'maximum-scale=1, user-scalable=no">', unsafe_allow_html=True)

    # ── 상단 바: 테마 토글 ──
    hcol1, hcol2 = st.columns([4, 1])
    with hcol2:
        label = "🌙 야간" if not dark else "☀️ 주간"
        if st.button(label, key="theme_toggle", use_container_width=True):
            st.session_state.dark_mode = not dark
            st.rerun()

    # ── 헤더 ──
    hc = get_header_color(dark)
    st.markdown(f"<p style='text-align:center;color:{hc};font-size:12px;"
                f"letter-spacing:4px;font-weight:600;margin-bottom:0'>FINANCIAL RUNWAY</p>",
                unsafe_allow_html=True)
    st.title("자산 고갈 시뮬레이터")
    st.markdown("<p class='subtitle'>현재 자산과 수입·지출을 입력하면<br>"
                "자산이 언제 고갈되는지 시뮬레이션합니다</p>", unsafe_allow_html=True)

    # Google Sheets 상태
    gsheet_ok = get_gsheet_connection() is not None
    if gsheet_ok: st.caption("✅ Google Sheets 연동 — 분석 시 자동 저장")
    else: st.caption("⚠️ Sheets 미연결 — README 참고")

    # URL 파라미터 복원
    qp = st.query_params
    restored = None
    if "d" in qp:
        restored = decode_params(qp["d"])

    # ── 프리셋 ──
    with st.expander("⚡ 빠른 시작 — 프리셋 선택"):
        preset_cols = st.columns(len(PRESETS))
        for i, (name, preset) in enumerate(PRESETS.items()):
            if preset_cols[i].button(name, key=f"preset_{i}", use_container_width=True):
                for k, v in preset.items():
                    st.session_state[f"p_{k}"] = v
                st.rerun()

    # ── 모드 ──
    mode = st.radio("분석 모드", ["간단 분석","상세 분석"], horizontal=True,
                    label_visibility="collapsed",
                    index=0 if not (restored and restored.get("mode")=="detailed") else 1)
    is_simple = mode == "간단 분석"

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    # ━━ 기본 정보 ━━
    st.subheader("👤 기본 정보")
    _d = restored or {}
    age = st.number_input("현재 나이", 15, 100, _d.get("age", 35))
    gender = st.selectbox("성별", ["남성","여성"], index=0 if _d.get("gender","male")=="male" else 1)
    gender_key = "male" if gender=="남성" else "female"
    retire_age = st.number_input("은퇴 나이", 30, 100, _d.get("retire_age", 60))
    life_exp = st.number_input("기대 수명 (한국 평균 83.7세)", 60, 120, _d.get("life_expectancy", 85))
    inflation_rate = st.number_input("연간 물가상승률 (%)", 0.0, 15.0,
                                     float(_d.get("inflation_rate", 2.5)), 0.1,
                                     help="간단: 전체 지출 | 상세: 변동비100%+고정비50%")

    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    if is_simple:
        st.subheader("💰 자산 & 수입")
        total_savings = amt("총 모아놓은 자금 (만원)", "ts",
                           _d.get("total_savings", 10000), 1000, "예금+주식+부동산 등")
        monthly_income = amt_s("월 수입 — 세후 (만원)", "mi",
                               _d.get("monthly_income", 400))
        st.subheader("💸 지출")
        monthly_expense = amt_s("월 평균 지출 (만원)", "me",
                                _d.get("monthly_expense", 250))

        params = dict(mode="simple", age=age, gender=gender_key,
            retire_age=retire_age, life_expectancy=life_exp, inflation_rate=inflation_rate,
            total_savings=total_savings, monthly_income=monthly_income,
            monthly_expense=monthly_expense)
    else:
        st.subheader("🏦 보유 자산")
        st.markdown("**예금·적금**")
        deposit_amount = amt("예금 (만원)", "da", _d.get("deposit_amount",3000), 500,
                            f"평균 금리 {DEP_RATE}%")
        deposit_rate = st.number_input("예금 수익률 (%)", 0.0, 20.0,
                                       float(_d.get("deposit_rate", DEP_RATE)), 0.1)
        st.markdown("**주식·펀드·ETF**")
        stock_amount = amt("주식 (만원)", "sa", _d.get("stock_amount",4000), 500)
        stock_return = st.number_input("기대 수익률 (%)", -20.0, 30.0,
                                       float(_d.get("stock_return",7.0)), 0.5)
        st.markdown("**부동산**")
        real_estate = amt("부동산 시가 (만원)", "rea", _d.get("real_estate_amount",30000), 5000)
        re_return = st.number_input("부동산 상승률 (%)", -10.0, 20.0,
                                    float(_d.get("real_estate_return",3.0)), 0.5)
        other_assets = amt("기타 자산 (만원)", "oa", _d.get("other_assets",0), 500, "보험, 금 등")

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("📈 수입")
        salary = amt_s("월 급여 — 세후 (만원)", "sal", _d.get("salary",400))
        side_income = amt_s("부수입 (만원/월)", "si", _d.get("side_income",0))
        pension = amt_s("국민연금 예상 (만원/월)", "pen", _d.get("pension_monthly",80), 5)
        pension_start = st.number_input("연금 시작 나이", 55, 80,
                                        _d.get("pension_start_age",65))

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("💸 지출")
        st.info(f"📌 물가상승률 {inflation_rate}%: 변동비 100% · 고정비 50%")
        fixed_cost = amt_s("월 고정비 (만원) — 주거·보험·교육", "fc", _d.get("fixed_cost",120))
        variable_cost = amt_s("월 변동비 (만원) — 식비·교통·여가", "vc", _d.get("variable_cost",80))
        savings_rate = st.number_input("저축률 (%)", 0.0, 100.0,
                                       float(_d.get("savings_rate",30)), 5.0)

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
        st.subheader("🏠 대출")
        default_loans = _d.get("loans", [{"amount":5000,"rate":LOAN_RATE,"years":20}])
        num_loans = st.number_input("대출 건수", 0, 5, len(default_loans))
        loans = []
        for i in range(int(num_loans)):
            dl = default_loans[i] if i < len(default_loans) else {"amount":0,"rate":LOAN_RATE,"years":15}
            with st.expander(f"대출 {i+1}", expanded=(i==0)):
                la = amt(f"잔액 (만원)", f"la{i}", int(dl["amount"]), 1000)
                lr = st.number_input(f"이자율 (%)", 0.0, 20.0, float(dl["rate"]), 0.1, key=f"lr{i}")
                ly = st.number_input(f"남은 기간 (년)", 1, 40, int(dl["years"]), key=f"ly{i}")
                loans.append({"amount":la, "rate":lr, "years":ly})

        params = dict(mode="detailed", age=age, gender=gender_key,
            retire_age=retire_age, life_expectancy=life_exp, inflation_rate=inflation_rate,
            deposit_amount=deposit_amount, deposit_rate=deposit_rate,
            stock_amount=stock_amount, stock_return=stock_return,
            real_estate_amount=real_estate, real_estate_return=re_return,
            other_assets=other_assets, salary=salary, side_income=side_income,
            pension_monthly=pension, pension_start_age=pension_start,
            fixed_cost=fixed_cost, variable_cost=variable_cost,
            savings_rate=savings_rate, loans=loans)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 실행
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

    if st.button("🚀 시뮬레이션 실행", use_container_width=True, type="primary"):
        if age >= life_exp:
            st.error("현재 나이가 기대 수명보다 크거나 같습니다.")
            return

        with st.spinner("시뮬레이션 계산 중..."):
            df = run_simulation(params)
            dep_info, peak_info, current_info = get_key_metrics(df, life_exp)
            base, s2, s3 = run_scenarios(params)
            opt, base_sens, pess = run_sensitivity(params)
            fire = calc_fire_index(params)
            safe = calc_safe_withdrawal(params)

        # Google Sheets
        results_for_save = {"depletion": dep_info, "peak": peak_info,
                            "current": current_info, "fire": fire,
                            "safe_withdrawal": safe}
        saved = save_to_gsheet(params, results_for_save)
        if saved: st.success("✅ Google Sheets 저장 완료")

        st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

        # ━━ 요약 ━━
        st.subheader("📋 분석 결과")
        m1, m2 = st.columns(2)
        if dep_info:
            m1.metric("⚠️ 자산 고갈", f"{dep_info['year']}년",
                      f"{dep_info['age']}세", delta_color="inverse")
        else:
            m1.metric("✅ 자산 고갈", "고갈 없음", f"{life_exp}세까지 안전")
        m2.metric("📈 최대 자산", fmt_krw(peak_info["net_worth"]),
                  f"{peak_info['year']}년 ({peak_info['age']}세)")

        # 동연령 비교
        diff = current_info["net_worth"] - current_info["avg_peer"]
        pct_val = round(current_info["net_worth"]/current_info["avg_peer"]*100) if current_info["avg_peer"] else 0
        gc, rc = get_diff_colors(dark)
        dc = gc if diff >= 0 else rc
        sign = "+" if diff >= 0 else ""
        emoji = "📈" if diff >= 0 else "📉"
        st.markdown(f"""
        <div style="background:{'rgba(99,102,241,0.06)' if dark else 'rgba(79,70,229,0.04)'};
        border:1px solid {'rgba(99,102,241,0.15)' if dark else 'rgba(79,70,229,0.12)'};
        border-radius:14px;padding:14px 16px;margin:12px 0;display:flex;
        justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
            <div><div style="font-size:12px;color:{'#71717a' if dark else '#64748b'}">동연령·동성 평균 대비</div>
            <div style="font-size:17px;font-weight:700;color:{dc}">{sign}{fmt_krw(diff)} ({pct_val}%)</div></div>
            <div style="font-size:32px">{emoji}</div>
        </div>""", unsafe_allow_html=True)

        # ━━ FIRE + 안전인출 ━━
        f1, f2 = st.columns(2)
        with f1:
            if fire["years_left"] == 0:
                st.metric("🔥 FIRE 달성", "달성!", f"목표: {fmt_krw(fire['target'])}")
            elif fire["years_left"] < 0:
                st.metric("🔥 FIRE", "도달 불가", f"저축액 부족")
            else:
                st.metric("🔥 FIRE까지", f"{fire['years_left']}년",
                          f"진행률 {fire['progress']}%")
        with f2:
            if safe and safe["safe_monthly"] > 0:
                st.metric("💳 안전 인출", f"{safe['safe_monthly']:,}만원/월",
                          f"은퇴 후 {safe['years']}년간")
            else:
                st.metric("💳 안전 인출", "계산 불가", "은퇴 시 자산 부족")

        # ━━ 차트들 ━━
        plotly_cfg = {"displayModeBar": False, "scrollZoom": False}

        # 파이 차트
        fig_pie = chart_pie(params, dark)
        if fig_pie:
            st.subheader("🥧 현재 자산 구성")
            st.plotly_chart(fig_pie, use_container_width=True, config=plotly_cfg)

        # 메인 차트
        st.subheader("📊 순자산 추이")
        fig_main = chart_main(df, retire_age, dep_info, dark)
        st.plotly_chart(fig_main, use_container_width=True, config=plotly_cfg)

        # 자산 구성 변화 (상세)
        fig_comp = chart_composition(df, dark)
        if fig_comp:
            st.subheader("🏗️ 자산 구성 변화")
            st.plotly_chart(fig_comp, use_container_width=True, config=plotly_cfg)

        # 수입/지출 비교
        st.subheader("💰 월 수입 vs 지출")
        fig_cf = chart_cashflow(params, dark)
        st.plotly_chart(fig_cf, use_container_width=True, config=plotly_cfg)

        # 시나리오 비교
        st.subheader("🔀 시나리오 비교")
        st.caption("① 현재 계획 · ② 저축 강화 · ③ 은퇴 3년 연장")
        fig_sc = chart_scenarios(base, s2, s3, retire_age, dark)
        st.plotly_chart(fig_sc, use_container_width=True, config=plotly_cfg)

        d2, _, d3 = get_key_metrics(s2, life_exp), None, get_key_metrics(s3, life_exp)
        sc_txt = []
        if d2[0]:
            sc_txt.append(f"저축 강화: {d2[0]['year']}년 고갈 ({d2[0]['age']}세)")
        else:
            sc_txt.append(f"저축 강화: 고갈 없음 ✅")
        if d3[0]:
            sc_txt.append(f"은퇴 연장: {d3[0]['year']}년 고갈 ({d3[0]['age']}세)")
        else:
            sc_txt.append(f"은퇴 연장: 고갈 없음 ✅")
        st.info(" | ".join(sc_txt))

        # 민감도 분석
        st.subheader("📉 민감도 분석")
        st.caption("수익률·물가 변동에 따른 자산 추이 범위")
        fig_sens = chart_sensitivity(opt, base_sens, pess, dark)
        st.plotly_chart(fig_sens, use_container_width=True, config=plotly_cfg)

        # 물가 영향
        if inflation_rate > 0:
            with st.expander("📈 물가상승률 영향 상세"):
                el_ret = retire_age - age; el_end = life_exp - age
                if is_simple:
                    ne = params["monthly_expense"]
                    re_ = ne*((1+inflation_rate/100)**el_ret)
                    ee = ne*((1+inflation_rate/100)**el_end)
                    st.markdown(f"| 시점 | 월 지출 |\n|---|---:|\n| 현재 | **{ne:,.0f}**만원 |\n| 은퇴({retire_age}세) | **{re_:,.0f}**만원 |\n| {life_exp}세 | **{ee:,.0f}**만원 |")
                else:
                    nv,nf = params["variable_cost"], params["fixed_cost"]
                    rv=nv*((1+inflation_rate/100)**el_ret); rf=nf*((1+inflation_rate/100*0.5)**el_ret)
                    ev=nv*((1+inflation_rate/100)**el_end); ef=nf*((1+inflation_rate/100*0.5)**el_end)
                    st.markdown(f"| 구분 | 현재 | 은퇴({retire_age}세) | {life_exp}세 |\n|---|---:|---:|---:|\n| 변동비 | {nv:,.0f}만 | {rv:,.0f}만 | {ev:,.0f}만 |\n| 고정비 | {nf:,.0f}만 | {rf:,.0f}만 | {ef:,.0f}만 |\n| **합계** | **{nv+nf:,.0f}만** | **{rv+rf:,.0f}만** | **{ev+ef:,.0f}만** |")

        # 주요 시점 테이블
        st.subheader("📋 주요 시점")
        m_ages = sorted(set([age,retire_age,65,70,80,life_exp]))
        m_df = df[df["age"].isin(m_ages)].copy()
        m_df["차이"] = m_df["net_worth"] - m_df["avg_peer"]
        disp = m_df[["year","age","net_worth","avg_peer","차이"]].copy()
        disp.columns = ["연도","나이","내 순자산","동연령 평균","차이"]
        st.dataframe(disp.style.format({"내 순자산":"{:,.0f}","동연령 평균":"{:,.0f}","차이":"{:+,.0f}"}),
                     use_container_width=True, hide_index=True)

        # ━━ 다운로드 ━━
        st.subheader("📥 보고서 & 데이터")

        # PDF (차트 이미지 포함)
        with st.spinner("PDF 보고서 생성 중..."):
            chart_imgs = {}
            for name, fig_obj in [("main", fig_main), ("composition", fig_comp),
                                   ("pie", fig_pie), ("cashflow", fig_cf),
                                   ("scenarios", fig_sc), ("sensitivity", fig_sens)]:
                if fig_obj:
                    # PDF용으로 라이트 테마 차트 재생성
                    img = fig_to_image_bytes(fig_obj)
                    if img: chart_imgs[name] = img

            try:
                pdf = generate_pdf_report(df, params, dep_info, peak_info,
                                          current_info, chart_imgs)
                st.download_button("📄 PDF 보고서 다운로드", pdf,
                    f"자산시뮬레이션_{datetime.now().strftime('%Y%m%d')}.pdf",
                    "application/pdf", use_container_width=True)
            except Exception as e:
                st.warning(f"PDF 오류: {e}")

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📊 CSV 다운로드", csv,
            f"자산시뮬레이션_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv", use_container_width=True)

        # ━━ 공유 링크 ━━
        st.subheader("🔗 공유")
        encoded = encode_params(params)
        share_url = f"?d={encoded}"
        st.code(share_url, language=None)
        st.caption("위 파라미터를 앱 URL 뒤에 붙이면 동일한 설정으로 공유할 수 있습니다")

        with st.expander("전체 데이터"):
            fd = {"net_worth":"{:,.0f}","avg_peer":"{:,.0f}"}
            if "deposit" in df.columns:
                fd.update({"deposit":"{:,.0f}","stock":"{:,.0f}","real_estate":"{:,.0f}","loan":"{:,.0f}"})
            st.dataframe(df.style.format(fd), use_container_width=True, height=300)

        st.caption(f"본 시뮬레이션은 참고용이며 실제 투자 성과와 다를 수 있습니다. "
                   f"한국은행 2026.2 기준 예금 {DEP_RATE}%, 대출 {LOAN_RATE}%. "
                   f"평균자산: 2025 가계금융복지조사.")


if __name__ == "__main__":
    main()
