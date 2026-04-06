"""
시뮬레이션 엔진
- 간단/상세 모드
- 물가상승률 차등 적용 (변동비 100%, 고정비 50%)
- 시나리오 비교 (기본/저축추가/은퇴연장)
- 민감도 분석 (낙관/기본/비관)
- FIRE 지표 계산
- 월 인출 가능액 역산
"""
import pandas as pd
import copy

# ── 한국 연령·성별 평균 순자산 (2025 가계금융복지조사, 만원) ──
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
    if age <= ages[0]:  return d[ages[0]]
    if age >= ages[-1]: return d[ages[-1]]
    for i in range(len(ages)-1):
        if ages[i] <= age <= ages[i+1]:
            r = (age-ages[i]) / (ages[i+1]-ages[i])
            return round(d[ages[i]] + r*(d[ages[i+1]]-d[ages[i]]))
    return d[ages[0]]


def fmt_krw(v):
    if v == 0: return "0원"
    sign = "-" if v < 0 else ""
    a = abs(v)
    if a >= 10000: return f"{sign}{a/10000:,.1f}억"
    return f"{sign}{a:,.0f}만원"


def amount_to_korean(val_man):
    """만원 단위 → 한글 자연어. 예: 100000 → '10억원'"""
    if val_man == 0: return "0원"
    sign = "마이너스 " if val_man < 0 else ""
    won = abs(val_man) * 10000
    parts = []
    for div, nm in [(1_0000_0000_0000,"조"),(1_0000_0000,"억"),(1_0000,"만")]:
        if won >= div:
            parts.append(f"{int(won//div):,}{nm}")
            won %= div
    return sign + (" ".join(parts) + "원" if parts else f"{int(won):,}원")


def _init_loans(loans_raw):
    ls = []
    for loan in (loans_raw or []):
        b, r, yr = loan["amount"], loan["rate"]/100, loan["years"]
        mp = 0
        if b > 0 and yr > 0:
            mr = r/12; np_ = yr*12
            mp = b*mr*((1+mr)**np_)/(((1+mr)**np_)-1) if mr > 0 else b/np_
        ls.append({"bal": b, "rate": r, "mp": mp})
    return ls


def run_simulation(p, override=None):
    """
    메인 시뮬레이션. override dict로 파라미터 일부 덮어쓰기 가능 (시나리오용).
    Returns DataFrame.
    """
    params = {**p, **(override or {})}
    mode = params["mode"]
    c_age = params["age"]; retire = params["retire_age"]; life = params["life_expectancy"]
    infl = params["inflation_rate"] / 100
    gender = params["gender"]
    rows = []

    if mode == "simple":
        nw = params["total_savings"]
        m_inc = params["monthly_income"]; m_exp = params["monthly_expense"]
        avg_ret = params.get("avg_return", 4.0) / 100

        for y in range(c_age, life+1):
            el = y - c_age
            rows.append({"age":y, "year":2026+el,
                         "net_worth":round(nw), "avg_peer":interp_nw(y, gender)})
            ann_inc = m_inc*12 if y < retire else 0
            ann_exp = m_exp*12*((1+infl)**el)
            nw = nw + ann_inc - ann_exp + nw*avg_ret
    else:
        dep = params["deposit_amount"]; stk = params["stock_amount"]
        re_ = params["real_estate_amount"]; oth = params["other_assets"]
        dR = params["deposit_rate"]/100; sR = params["stock_return"]/100
        rR = params["real_estate_return"]/100
        mSal = params["salary"]; mSide = params["side_income"]
        mPen = params["pension_monthly"]; penS = params["pension_start_age"]
        mFix = params["fixed_cost"]; mVar = params["variable_cost"]
        svR = params["savings_rate"]/100

        ls = _init_loans(params.get("loans"))

        for y in range(c_age, life+1):
            el = y - c_age
            tl = sum(l["bal"] for l in ls)
            nw = dep + stk + re_ + oth - tl
            rows.append({"age":y, "year":2026+el, "net_worth":round(nw),
                          "deposit":round(dep), "stock":round(stk),
                          "real_estate":round(re_), "loan":round(tl),
                          "avg_peer":interp_nw(y, gender)})

            ann_inc = (mSal+mSide)*12 if y < retire else 0
            pen_inc = mPen*12 if y >= penS else 0
            var_exp = mVar*12*((1+infl)**el)
            fix_exp = mFix*12*((1+infl*0.5)**el)
            ann_exp = var_exp + fix_exp
            ann_loan = sum(l["mp"]*12 for l in ls if l["bal"] > 0)
            ncf = ann_inc + pen_inc - ann_exp - ann_loan

            dep += dep*dR; stk += stk*sR; re_ += re_*rR
            if ncf > 0:
                sv = ncf*svR; dep += sv*0.4; stk += sv*0.6
            else:
                deficit = ncf
                if dep+deficit >= 0: dep += deficit
                else:
                    deficit += dep; dep = 0
                    if stk+deficit >= 0: stk += deficit
                    else: deficit += stk; stk = 0; re_ += deficit
            for l in ls:
                if l["bal"] > 0:
                    l["bal"] = max(0, l["bal"] - (l["mp"]*12 - l["bal"]*l["rate"]))
            dep = max(dep, 0); stk = max(stk, 0)

    return pd.DataFrame(rows)


def get_key_metrics(df, life_exp):
    """핵심 지표 추출."""
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
    """3가지 시나리오 비교."""
    base = run_simulation(params)

    # 시나리오 2: 월 50만원 추가 저축
    if params["mode"] == "simple":
        s2 = run_simulation(params, {"monthly_expense": params["monthly_expense"] - 50})
    else:
        s2 = run_simulation(params, {"savings_rate": min(params["savings_rate"] + 15, 100)})

    # 시나리오 3: 은퇴 3년 연장
    s3 = run_simulation(params, {"retire_age": params["retire_age"] + 3})

    return base, s2, s3


def run_sensitivity(params):
    """민감도 분석: 낙관/기본/비관."""
    base = run_simulation(params)

    if params["mode"] == "simple":
        optimistic = run_simulation(params, {
            "inflation_rate": max(params["inflation_rate"] - 1, 0),
        })
        pessimistic = run_simulation(params, {
            "inflation_rate": params["inflation_rate"] + 1.5,
        })
    else:
        optimistic = run_simulation(params, {
            "stock_return": params["stock_return"] + 2,
            "real_estate_return": params["real_estate_return"] + 1,
            "inflation_rate": max(params["inflation_rate"] - 1, 0),
        })
        pessimistic = run_simulation(params, {
            "stock_return": max(params["stock_return"] - 3, -5),
            "real_estate_return": max(params["real_estate_return"] - 2, -5),
            "inflation_rate": params["inflation_rate"] + 1.5,
        })

    return optimistic, base, pessimistic


def calc_fire_index(params):
    """FIRE 지표: 연 지출의 25배 도달까지 남은 연수."""
    if params["mode"] == "simple":
        annual_exp = params["monthly_expense"] * 12
        current_nw = params["total_savings"]
        monthly_save = params["monthly_income"] - params["monthly_expense"]
    else:
        annual_exp = (params["fixed_cost"] + params["variable_cost"]) * 12
        current_nw = (params["deposit_amount"] + params["stock_amount"]
                      + params["real_estate_amount"] + params["other_assets"]
                      - sum(l["amount"] for l in params.get("loans", [])))
        monthly_save = (params["salary"] + params["side_income"]
                        - params["fixed_cost"] - params["variable_cost"])

    fire_target = annual_exp * 25
    if current_nw >= fire_target:
        return {"target": fire_target, "current": current_nw,
                "progress": 100, "years_left": 0, "monthly_save": monthly_save}

    if monthly_save <= 0:
        return {"target": fire_target, "current": current_nw,
                "progress": round(current_nw/fire_target*100, 1),
                "years_left": -1, "monthly_save": monthly_save}

    # 복리 계산으로 도달 연수 추정
    avg_return = 0.05
    years = 0
    nw = current_nw
    while nw < fire_target and years < 100:
        nw = nw * (1 + avg_return) + monthly_save * 12
        years += 1

    return {"target": fire_target, "current": current_nw,
            "progress": round(min(current_nw/fire_target*100, 100), 1),
            "years_left": years, "monthly_save": monthly_save}


def calc_safe_withdrawal(params):
    """은퇴 후 월 안전 인출 가능액 역산 (자산 고갈 방지)."""
    retire = params["retire_age"]
    life = params["life_expectancy"]
    infl = params["inflation_rate"] / 100

    # 은퇴 시점 자산 추정
    df = run_simulation(params)
    retire_row = df[df["age"] == retire]
    if retire_row.empty:
        return None

    retire_nw = retire_row.iloc[0]["net_worth"]
    if retire_nw <= 0:
        return {"retire_nw": retire_nw, "safe_monthly": 0, "years": life - retire}

    years_in_retirement = life - retire
    if years_in_retirement <= 0:
        return None

    # 은퇴 후 수입 (연금)
    pension_annual = 0
    if params["mode"] == "detailed":
        pen_start = params.get("pension_start_age", 65)
        if pen_start <= life:
            pension_years = life - max(retire, pen_start)
            if pension_years > 0:
                pension_annual = params.get("pension_monthly", 0) * 12

    # 4% 룰 기반 + 연금 고려
    avg_return = 0.03  # 은퇴 후 보수적 수익률
    # 연금수령 연수 비율
    total_available = retire_nw
    for y in range(years_in_retirement):
        total_available *= (1 + avg_return)
        total_available += pension_annual

    safe_annual = total_available / years_in_retirement * 0.85  # 안전 마진
    safe_monthly = max(0, safe_annual / 12)

    return {
        "retire_nw": retire_nw,
        "safe_monthly": round(safe_monthly),
        "years": years_in_retirement,
        "pension_monthly": params.get("pension_monthly", 0) if params["mode"] == "detailed" else 0,
    }
