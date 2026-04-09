"""
맞춤형 조언 생성 모듈
시뮬레이션 결과를 바탕으로 따뜻하고 현실적인 조언을 제공합니다.
"""
from engine import fmt_krw, _safe_float, _safe_int, get_key_metrics, run_simulation


def generate_advice(df, params, dep_info, peak_info, current_info, scenarios, fire):
    """시뮬레이션 결과를 분석하여 맞춤형 조언 리스트를 생성합니다."""
    tips = []
    mode = params.get("mode", "simple")
    age = _safe_int(params.get("age", 35))
    retire = _safe_int(params.get("retire_age", 60))
    life = _safe_int(params.get("life_expectancy", 85))
    years_to_retire = retire - age
    years_in_retire = life - retire

    # 현재 순자산 & 동연령 비교
    nw = current_info["net_worth"]
    peer = current_info["avg_peer"]
    diff = nw - peer
    diff_pct = round(nw / peer * 100) if peer > 0 else 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 전체 상황 요약 (항상 표시)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if dep_info:
        dep_age = dep_info["age"]
        dep_year = dep_info["year"]
        years_until_dep = dep_age - age

        if dep_age <= retire:
            tips.append({
                "icon": "🚨",
                "title": "은퇴 전에 자산이 소진될 수 있어요",
                "body": (f"현재 패턴이 유지되면 **{dep_year}년({dep_age}세)**에 자산이 소진됩니다. "
                         f"은퇴 예정({retire}세)보다 **{retire - dep_age}년 먼저**입니다. "
                         f"지금부터 지출을 줄이거나 수입을 늘리는 조정이 필요합니다.")
            })
        elif dep_age <= 70:
            tips.append({
                "icon": "⚠️",
                "title": f"{dep_age}세에 자산이 소진될 수 있어요",
                "body": (f"현재 패턴대로라면 **{dep_year}년({dep_age}세)**에 자산이 바닥납니다. "
                         f"은퇴 후 약 **{dep_age - retire}년** 뒤입니다. "
                         f"노후 생활의 안정을 위해 미리 대비하면 훨씬 여유로워질 수 있습니다.")
            })
        elif dep_age <= life:
            tips.append({
                "icon": "💡",
                "title": f"기대수명 전에 자산이 소진될 수 있어요",
                "body": (f"현재 계획대로라면 **{dep_year}년({dep_age}세)**까지 자산이 유지됩니다. "
                         f"기대수명({life}세)까지 **{life - dep_age}년**의 공백이 생길 수 있으므로, "
                         f"작은 조정만으로도 안정적인 노후를 만들 수 있습니다.")
            })
    else:
        final_nw = int(df.iloc[-1]["net_worth"])
        tips.append({
            "icon": "🎉",
            "title": "자산이 기대수명까지 유지됩니다!",
            "body": (f"현재 계획대로라면 **{life}세**에도 약 **{fmt_krw(final_nw)}**의 자산이 남습니다. "
                     f"매우 안정적인 재정 계획입니다. "
                     f"혹시 더 일찍 은퇴하거나 여유로운 노후를 원하신다면 추가 시나리오를 확인해 보세요.")
        })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 동연령 비교 (항상 표시)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if diff >= 0:
        if diff_pct >= 150:
            tips.append({
                "icon": "🏆",
                "title": f"동연령 평균보다 {diff_pct - 100}% 더 많은 자산을 보유하고 계세요",
                "body": (f"같은 나이·성별 평균({fmt_krw(peer)})보다 **{fmt_krw(diff)}** 많습니다. "
                         f"지금까지 잘 관리해 오신 결과입니다. 이 흐름을 유지하시면 됩니다.")
            })
        else:
            tips.append({
                "icon": "👍",
                "title": "동연령 평균 이상의 자산을 보유하고 계세요",
                "body": (f"같은 나이·성별 평균({fmt_krw(peer)}) 대비 **{fmt_krw(diff)}** 많습니다. "
                         f"꾸준히 잘 관리하고 계십니다.")
            })
    else:
        gap = abs(diff)
        monthly_gap = round(gap / max(years_to_retire * 12, 12))
        tips.append({
            "icon": "📊",
            "title": "동연령 평균과의 차이를 좁혀볼까요?",
            "body": (f"현재 같은 나이·성별 평균({fmt_krw(peer)})보다 **{fmt_krw(gap)}** 적습니다. "
                     f"매달 약 **{monthly_gap:,}만원**씩 추가로 저축하면 은퇴 전까지 따라잡을 수 있습니다. "
                     f"작은 금액이라도 꾸준히 하면 복리 효과가 큽니다.")
        })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. 지출 절감 효과 (고갈 시에만)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if dep_info:
        s2 = scenarios.get("저축 강화")
        if s2 is not None:
            d2, _, _ = get_key_metrics(s2, life)
            if not d2:
                tips.append({
                    "icon": "✂️",
                    "title": "월 50만원 절감으로 고갈을 막을 수 있어요",
                    "body": (f"{'변동비' if mode == 'detailed' else '지출'}을 월 50만원만 줄이면 "
                             f"**기대수명까지 자산이 유지**됩니다. "
                             f"외식이나 구독 서비스 등 작은 부분부터 점검해 보시면 생각보다 쉽게 찾을 수 있습니다.")
                })
            elif d2["age"] > dep_info["age"]:
                delay = d2["age"] - dep_info["age"]
                tips.append({
                    "icon": "✂️",
                    "title": f"월 50만원 절감으로 {delay}년 더 버틸 수 있어요",
                    "body": (f"{'변동비' if mode == 'detailed' else '지출'}을 월 50만원 줄이면 "
                             f"자산 소진 시점이 **{dep_info['age']}세 → {d2['age']}세**로 "
                             f"**{delay}년** 늦춰집니다.")
                })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. 은퇴 연장 효과 (고갈 시에만)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if dep_info:
        s3 = scenarios.get("은퇴 3년 연장")
        if s3 is not None:
            d3, _, _ = get_key_metrics(s3, life)
            if not d3:
                tips.append({
                    "icon": "⏰",
                    "title": "3년만 더 일하면 자산 고갈을 막을 수 있어요",
                    "body": (f"은퇴를 {retire}세 → {retire+3}세로 3년 늦추면 "
                             f"**기대수명까지 자산이 유지**됩니다. "
                             f"3년간의 추가 수입과 지출 기간 단축이 합쳐져 큰 효과를 냅니다.")
                })
            elif d3["age"] > dep_info["age"]:
                delay = d3["age"] - dep_info["age"]
                tips.append({
                    "icon": "⏰",
                    "title": f"은퇴를 3년 늦추면 {delay}년 더 여유가 생겨요",
                    "body": (f"은퇴를 {retire}세 → {retire+3}세로 조정하면 "
                             f"자산 소진 시점이 **{dep_info['age']}세 → {d3['age']}세**로 늦춰집니다.")
                })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. 수익률 시나리오 효과
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    r5 = scenarios.get("매년 5% 수익")
    r10 = scenarios.get("매년 10% 수익")
    if r5 is not None and dep_info:
        d5, _, _ = get_key_metrics(r5, life)
        if not d5:
            tips.append({
                "icon": "📈",
                "title": "연 5% 수익률이면 자산 고갈이 사라져요",
                "body": (f"자산을 연 5% 수익률로 운용하면 **기대수명까지 자산이 유지**됩니다. "
                         f"예·적금 위주에서 인덱스 펀드나 ETF를 섞는 것만으로도 "
                         f"장기적으로 4~6% 수익을 기대할 수 있습니다.")
            })
        elif d5["age"] > dep_info["age"]:
            delay = d5["age"] - dep_info["age"]
            tips.append({
                "icon": "📈",
                "title": f"연 5% 수익률로 {delay}년 더 유지할 수 있어요",
                "body": (f"자산 운용 수익률을 연 5%까지 올리면 "
                         f"자산 소진 시점이 **{delay}년** 늦춰집니다. "
                         f"분산 투자로 리스크를 관리하면서 수익률을 높이는 전략을 검토해 보세요.")
            })
    elif r5 is not None and not dep_info:
        # 고갈이 없는 안정적 상황에서 수익률 효과
        final_base = int(df.iloc[-1]["net_worth"])
        final_5 = int(r5.iloc[-1]["net_worth"])
        if final_5 > final_base * 1.3:
            extra = final_5 - final_base
            tips.append({
                "icon": "📈",
                "title": "투자 수익률을 높이면 노후가 더 넉넉해져요",
                "body": (f"연 5% 수익률로 운용하면 {life}세 자산이 "
                         f"**{fmt_krw(final_base)} → {fmt_krw(final_5)}**로 "
                         f"**{fmt_krw(extra)}** 더 늘어납니다.")
            })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 6. 은퇴 후 소득 제안
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    retire_inc = _safe_float(params.get("retire_income", 0))
    if retire_inc == 0 and dep_info:
        # 은퇴 후 소득이 0인데 고갈이 발생하는 경우
        # 얼마의 은퇴 후 소득이 있으면 고갈을 막을 수 있는지 역산
        for test_inc in [50, 100, 150, 200, 300]:
            test_df = run_simulation(params, {"retire_income": test_inc})
            td, _, _ = get_key_metrics(test_df, life)
            if not td:
                tips.append({
                    "icon": "💼",
                    "title": f"은퇴 후 월 {test_inc}만원의 소득이면 충분해요",
                    "body": (f"은퇴 후 파트타임이나 임대 수입 등으로 "
                             f"**월 {test_inc}만원**만 벌면 자산 고갈을 막을 수 있습니다. "
                             f"프리랜서, 컨설팅, 임대 수입, 온라인 비즈니스 등 "
                             f"다양한 방법을 미리 준비해 보시는 것도 좋습니다.")
                })
                break

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 7. FIRE 관련
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if fire:
        yl = fire.get("years_left", -1)
        if yl == 0:
            tips.append({
                "icon": "🔥",
                "title": "FIRE 목표를 이미 달성하셨어요!",
                "body": (f"현재 순자산이 FIRE 목표(**{fmt_krw(fire.get('target',0))}**)를 넘었습니다. "
                         f"원하신다면 지금이라도 경제적 독립이 가능한 상태입니다. "
                         f"축하합니다! 🎊")
            })
        elif 0 < yl <= 5:
            tips.append({
                "icon": "🔥",
                "title": f"FIRE까지 {yl}년 남았어요!",
                "body": (f"현재 페이스를 유지하면 **{yl}년 후** "
                         f"경제적 독립(FIRE)에 도달합니다. 거의 다 왔습니다!")
            })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 8. 대출 관련 (상세 모드)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if mode == "detailed":
        loans = params.get("loans", [])
        total_loan = sum(_safe_float(l.get("amount", 0)) for l in loans)
        if total_loan > 0:
            total_interest = 0
            for l in loans:
                amt = _safe_float(l.get("amount", 0))
                rate = _safe_float(l.get("rate", 0)) / 100
                years = _safe_int(l.get("years", 0))
                if amt > 0 and years > 0 and rate > 0:
                    mr = rate / 12
                    np_ = years * 12
                    mp = amt * mr * ((1+mr)**np_) / (((1+mr)**np_) - 1)
                    total_interest += mp * np_ - amt
            if total_interest > 0:
                tips.append({
                    "icon": "🏦",
                    "title": f"대출 이자만 총 {fmt_krw(round(total_interest))}를 내게 됩니다",
                    "body": (f"현재 대출을 끝까지 상환하면 이자로만 **{fmt_krw(round(total_interest))}**를 지출합니다. "
                             f"여유 자금이 생기면 일부 조기 상환을 고려해 보세요. "
                             f"이자 부담을 줄이는 것이 가장 확실한 절약입니다.")
                })

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 9. 마무리 격려 (항상)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if dep_info:
        tips.append({
            "icon": "💪",
            "title": "지금 확인한 것만으로도 큰 한 걸음이에요",
            "body": ("대부분의 사람들은 미래 재정을 점검하지 않습니다. "
                     "지금 이렇게 확인하고 계신다는 것 자체가 이미 좋은 출발입니다. "
                     "위의 시나리오들을 참고해서 작은 변화부터 시작해 보세요. "
                     "작은 조정이 수십 년 뒤에는 큰 차이를 만듭니다.")
        })
    else:
        tips.append({
            "icon": "🌟",
            "title": "앞으로도 꾸준히 점검해 보세요",
            "body": ("재정 계획은 한 번 세우면 끝이 아니라, 상황 변화에 따라 조정하는 것이 중요합니다. "
                     "1~2년에 한 번 이 시뮬레이션을 다시 돌려보시면 "
                     "더 정확하고 안정적인 노후를 준비할 수 있습니다.")
        })

    return tips
