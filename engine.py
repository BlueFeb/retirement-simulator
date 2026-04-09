"""
시뮬레이션 엔진 — v3: 월 단위 통합, 실질가치, 은퇴후 소득
"""
import pandas as pd

AVG_NW = {
    "male":   {20:3000,25:5000,30:12000,35:20000,40:33000,45:40000,
               50:48000,55:52000,60:51900,65:45000,70:38000,75:30000,
               80:22000,85:16000,90:12000,95:8000,100:5000},
    "female": {20:2800,25:4800,30:11000,35:18000,40:30000,45:37000,
               50:44000,55:48000,60:47000,65:41000,70:35000,75:28000,
               80:20000,85:14000,90:10000,95:7000,100:4000},
}

DEP_RATE = 2.83
LOAN_RATE = 4.26


def interp_nw(age, gender):
    d = AVG_NW.get(gender, AVG_NW["male"])
    ages = sorted(d.keys())
    age = int(age)
    if age <= ages[0]:  return d[ages[0]]
    if age >= ages[-1]: return d[ages[-1]]
    for i in range(len(ages)-1):
        if ages[i] <= age <= ages[i+1]:
            r = (age-ages[i]) / (ages[i+1]-ages[i])
            return round(d[ages[i]] + r*(d[ages[i+1]]-d[ages[i]]))
    return d[ages[0]]


def fmt_krw(v):
    try: v = float(v)
    except (TypeError, ValueError): return "0원"
    if v == 0: return "0원"
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 10000: return f"{sign}{a/10000:,.1f}억"
    return f"{sign}{a:,.0f}만원"


def amount_to_korean(val_man):
    try: val_man = float(val_man)
    except (TypeError, ValueError): return "0원"
    if val_man == 0: return "0원"
    sign = "마이너스 " if val_man < 0 else ""
    won = abs(val_man) * 10000
    parts = []
    for div, nm in [(1_0000_0000_0000,"조"),(1_0000_0000,"억"),(1_0000,"만")]:
        if won >= div:
            parts.append(f"{int(won//div):,}{nm}")
            won %= div
    return sign + (" ".join(parts) + "원" if parts else f"{int(won):,}원")


def _safe_int(v, default=0):
    try: return int(v)
    except (TypeError, ValueError): return default

def _safe_float(v, default=0.0):
    try: return float(v)
    except (TypeError, ValueError): return default


def _init_loans(loans_raw):
    ls = []
    for loan in (loans_raw or []):
        b = _safe_float(loan.get("amount", 0))
        r = _safe_float(loan.get("rate", 0)) / 100
        yr = _safe_int(loan.get("years", 0))
        mp = 0
        if b > 0 and yr > 0:
            mr = r/12; np_ = yr*12
            if mr > 0:
                try: mp = b*mr*((1+mr)**np_)/(((1+mr)**np_)-1)
                except (OverflowError, ZeroDivisionError): mp = b / np_
            else: mp = b / np_
        ls.append({"bal": b, "rate": r, "mp": mp})
    return ls


def run_simulation(p, override=None):
    params = {**p, **(override or {})}
    mode = params.get("mode", "simple")
    c_age = _safe_int(params.get("age", 35))
    retire = _safe_int(params.get("retire_age", 60))
    life = _safe_int(params.get("life_expectancy", 85))
    infl = _safe_float(params.get("inflation_rate", 2.5)) / 100
    gender = params.get("gender", "male")

    if c_age >= life:
        return pd.DataFrame([{"age":c_age,"year":2026,"net_worth":0,"real_net_worth":0,"avg_peer":interp_nw(c_age,gender)}])

    rows = []

    if mode == "simple":
        nw = _safe_float(params.get("total_savings", 0))
        m_inc = _safe_float(params.get("monthly_income", 0))
        m_exp = _safe_float(params.get("monthly_expense", 0))
        # 은퇴 후 부분 소득 (#14)
        m_retire_inc = _safe_float(params.get("retire_income", 0))
        ann_ret = _safe_float(params.get("avg_return", DEP_RATE)) / 100
        monthly_ret = (1 + ann_ret) ** (1/12) - 1

        for y in range(c_age, life+1):
            el = y - c_age
            # 실질가치: 현재 가치 기준으로 할인
            deflator = (1 + infl) ** el if infl > 0 else 1
            real_nw = round(nw / deflator) if deflator > 0 else round(nw)
            rows.append({"age":y, "year":2026+el,
                         "net_worth":round(nw), "real_net_worth":real_nw,
                         "avg_peer":interp_nw(y, gender)})
            # 월 단위 계산 — 물가상승 반영
            # 지출: 물가 100% 반영
            m_exp_now = m_exp * ((1 + infl) ** el)
            # 수입: 급여는 물가의 70% 인상, 은퇴 후 소득은 물가 50% 인상
            if y < retire:
                m_inc_now = m_inc * ((1 + infl * 0.7) ** el)
            else:
                m_inc_now = m_retire_inc * ((1 + infl * 0.5) ** el)
            for _ in range(12):
                # 수익률은 양수 자산에만 적용 (마이너스면 수익 없음)
                if nw > 0:
                    nw = nw * (1 + monthly_ret) + m_inc_now - m_exp_now
                else:
                    nw = nw + m_inc_now - m_exp_now

    else:
        # ━━ 상세 모드 — 월 단위로 전환 (#16) ━━
        dep = _safe_float(params.get("deposit_amount", 0))
        stk = _safe_float(params.get("stock_amount", 0))
        re_ = _safe_float(params.get("real_estate_amount", 0))
        oth = _safe_float(params.get("other_assets", 0))
        dR_ann = _safe_float(params.get("deposit_rate", 2.83)) / 100
        sR_ann = _safe_float(params.get("stock_return", 10)) / 100
        rR_ann = _safe_float(params.get("real_estate_return", 2.5)) / 100

        if "avg_return" in params:
            unified = _safe_float(params["avg_return"]) / 100
            dR_ann = unified; sR_ann = unified; rR_ann = unified

        # 월 복리 수익률
        dR_m = (1 + dR_ann) ** (1/12) - 1
        sR_m = (1 + sR_ann) ** (1/12) - 1
        rR_m = (1 + rR_ann) ** (1/12) - 1

        mSal = _safe_float(params.get("salary", 0))
        mSide = _safe_float(params.get("side_income", 0))
        mPen = _safe_float(params.get("pension_monthly", 0))
        penS = _safe_int(params.get("pension_start_age", 65))
        mFix = _safe_float(params.get("fixed_cost", 0))
        mVar = _safe_float(params.get("variable_cost", 0))
        svR = _safe_float(params.get("savings_rate", 30)) / 100
        # 은퇴 후 부분 소득 (#14)
        m_retire_inc = _safe_float(params.get("retire_income", 0))

        ls = _init_loans(params.get("loans"))

        for y in range(c_age, life+1):
            el = y - c_age
            tl = sum(l["bal"] for l in ls)
            nw = dep + stk + re_ + oth - tl
            deflator = (1 + infl) ** el if infl > 0 else 1
            real_nw = round(nw / deflator) if deflator > 0 else round(nw)

            rows.append({"age":y, "year":2026+el, "net_worth":round(nw),
                          "real_net_worth":real_nw,
                          "deposit":round(dep), "stock":round(stk),
                          "real_estate":round(re_), "loan":round(tl),
                          "avg_peer":interp_nw(y, gender)})

            # 월별 계산 — 물가상승 반영
            # 지출: 변동비 물가 100%, 고정비 물가 50%
            m_var_now = mVar * ((1 + infl) ** el)
            m_fix_now = mFix * ((1 + infl * 0.5) ** el)
            m_exp_now = m_var_now + m_fix_now
            # 수입: 급여+부수입 물가의 70% 인상, 연금 물가 100% 연동, 은퇴후소득 물가 50%
            if y < retire:
                m_inc_now = (mSal + mSide) * ((1 + infl * 0.7) ** el)
            else:
                m_inc_now = m_retire_inc * ((1 + infl * 0.5) ** el)
            m_pen_now = mPen * ((1 + infl) ** el) if y >= penS else 0
            m_loan_pay = sum(l["mp"] for l in ls if l["bal"] > 0)

            for _ in range(12):
                # 자산별 월 수익
                dep *= (1 + dR_m)
                stk *= (1 + sR_m)
                re_ *= (1 + rR_m)

                # 월 순현금흐름
                ncf = m_inc_now + m_pen_now - m_exp_now - m_loan_pay

                if ncf > 0:
                    sv = ncf * svR
                    dep += sv * 0.4
                    stk += sv * 0.6
                else:
                    deficit = ncf
                    if dep + deficit >= 0:
                        dep += deficit
                    else:
                        deficit += dep; dep = 0
                        if stk + deficit >= 0:
                            stk += deficit
                        else:
                            deficit += stk; stk = 0
                            re_ += deficit

                # 대출 상환
                for l in ls:
                    if l["bal"] > 0:
                        interest = l["bal"] * l["rate"] / 12
                        principal = l["mp"] - interest
                        l["bal"] = max(0, l["bal"] - principal)

            dep = max(dep, 0); stk = max(stk, 0); re_ = max(re_, 0)

    return pd.DataFrame(rows)


def get_key_metrics(df, life_exp):
    if df.empty:
        return None, {"net_worth":0,"age":0,"year":2026}, {"net_worth":0,"avg_peer":0}
    dep_df = df[df["net_worth"] <= 0].head(1)
    dep_info = None
    if not dep_df.empty:
        dep_info = {"year":int(dep_df.iloc[0]["year"]), "age":int(dep_df.iloc[0]["age"])}
    pk = df.loc[df["net_worth"].idxmax()]
    peak_info = {"net_worth":int(pk["net_worth"]), "age":int(pk["age"]), "year":int(pk["year"])}
    cur = df.iloc[0]
    current_info = {"net_worth":int(cur["net_worth"]), "avg_peer":int(cur["avg_peer"])}
    return dep_info, peak_info, current_info


def run_scenarios(params):
    base = run_simulation(params)
    if params.get("mode") == "simple":
        s2 = run_simulation(params, {"monthly_expense": max(0, _safe_float(params.get("monthly_expense",0)) - 50)})
    else:
        s2 = run_simulation(params, {"savings_rate": min(_safe_float(params.get("savings_rate",30)) + 15, 100)})
    s3 = run_simulation(params, {"retire_age": _safe_int(params.get("retire_age",60)) + 3})
    return base, s2, s3


def run_sensitivity(params):
    base = run_simulation(params)
    ir = _safe_float(params.get("inflation_rate", 2.5))
    if params.get("mode") == "simple":
        opt = run_simulation(params, {"inflation_rate": max(ir - 1, 0)})
        pess = run_simulation(params, {"inflation_rate": ir + 1.5})
    else:
        sr = _safe_float(params.get("stock_return", 10))
        rr = _safe_float(params.get("real_estate_return", 2.5))
        opt = run_simulation(params, {"stock_return":sr+2, "real_estate_return":rr+1, "inflation_rate":max(ir-1,0)})
        pess = run_simulation(params, {"stock_return":max(sr-3,-5), "real_estate_return":max(rr-2,-5), "inflation_rate":ir+1.5})
    return opt, base, pess


def calc_fire_index(params):
    try:
        if params.get("mode") == "simple":
            annual_exp = _safe_float(params.get("monthly_expense",0)) * 12
            current_nw = _safe_float(params.get("total_savings",0))
            monthly_save = _safe_float(params.get("monthly_income",0)) - _safe_float(params.get("monthly_expense",0))
        else:
            annual_exp = (_safe_float(params.get("fixed_cost",0)) + _safe_float(params.get("variable_cost",0))) * 12
            current_nw = (_safe_float(params.get("deposit_amount",0)) + _safe_float(params.get("stock_amount",0))
                          + _safe_float(params.get("real_estate_amount",0)) + _safe_float(params.get("other_assets",0))
                          - sum(_safe_float(l.get("amount",0)) for l in params.get("loans", [])))
            monthly_save = (_safe_float(params.get("salary",0)) + _safe_float(params.get("side_income",0))
                            - _safe_float(params.get("fixed_cost",0)) - _safe_float(params.get("variable_cost",0)))
        fire_target = annual_exp * 25
        if fire_target <= 0:
            return {"target":0, "current":current_nw, "progress":100, "years_left":0, "monthly_save":monthly_save}
        if current_nw >= fire_target:
            return {"target":fire_target, "current":current_nw, "progress":100, "years_left":0, "monthly_save":monthly_save}
        if monthly_save <= 0:
            progress = round(current_nw/fire_target*100, 1) if fire_target > 0 else 0
            return {"target":fire_target, "current":current_nw, "progress":progress, "years_left":-1, "monthly_save":monthly_save}
        nw = current_nw; years = 0
        while nw < fire_target and years < 100:
            nw = nw * 1.05 + monthly_save * 12; years += 1
        progress = round(min(current_nw/fire_target*100, 100), 1)
        return {"target":fire_target, "current":current_nw, "progress":progress, "years_left":years, "monthly_save":monthly_save}
    except Exception:
        return {"target":0, "current":0, "progress":0, "years_left":-1, "monthly_save":0}


def calc_safe_withdrawal(params):
    try:
        retire = _safe_int(params.get("retire_age", 60))
        life = _safe_int(params.get("life_expectancy", 85))
        years_in_retirement = life - retire
        if years_in_retirement <= 0:
            return {"retire_nw":0, "safe_monthly":0, "years":0, "pension_monthly":0}
        df = run_simulation(params)
        retire_row = df[df["age"] == retire]
        if retire_row.empty:
            return {"retire_nw":0, "safe_monthly":0, "years":years_in_retirement, "pension_monthly":0}
        retire_nw = float(retire_row.iloc[0]["net_worth"])
        if retire_nw <= 0:
            return {"retire_nw":retire_nw, "safe_monthly":0, "years":years_in_retirement, "pension_monthly":0}
        pension_annual = 0
        if params.get("mode") == "detailed":
            pen_start = _safe_int(params.get("pension_start_age", 65))
            if pen_start <= life:
                pension_years = life - max(retire, pen_start)
                if pension_years > 0:
                    pension_annual = _safe_float(params.get("pension_monthly", 0)) * 12
        total_available = retire_nw
        for y in range(years_in_retirement):
            total_available *= 1.03; total_available += pension_annual
        safe_monthly = max(0, total_available / years_in_retirement * 0.85 / 12)
        pm = _safe_float(params.get("pension_monthly", 0)) if params.get("mode") == "detailed" else 0
        return {"retire_nw":retire_nw, "safe_monthly":round(safe_monthly), "years":years_in_retirement, "pension_monthly":pm}
    except Exception:
        return {"retire_nw":0, "safe_monthly":0, "years":0, "pension_monthly":0}
