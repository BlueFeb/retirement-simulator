"""
맞춤형 조언 생성 모듈
따뜻한 반말 응원 톤의 개인 조언을 제공합니다.
"""
from engine import fmt_krw, _safe_float, _safe_int, get_key_metrics, run_simulation


def generate_advice(df, params, dep_info, peak_info, current_info, scenarios, fire):
    tips = []
    mode = params.get("mode", "simple")
    age = _safe_int(params.get("age", 35))
    retire = _safe_int(params.get("retire_age", 60))
    life = _safe_int(params.get("life_expectancy", 85))
    years_to_retire = retire - age

    nw = current_info["net_worth"]
    peer = current_info["avg_peer"]
    diff = nw - peer
    diff_pct = round(nw / peer * 100) if peer > 0 else 0

    # 1. 전체 상황 요약
    if dep_info:
        dep_age = dep_info["age"]
        dep_year = dep_info["year"]
        if dep_age <= retire:
            tips.append({"icon":"🚨","title":"지금 흐름이면 은퇴 전에 자산이 바닥날 수 있어",
                "body":(f"현재 패턴이 이어지면 {dep_year}년({dep_age}세)에 자산이 소진돼. "
                        f"은퇴 예정({retire}세)보다 {retire - dep_age}년이나 앞서서 바닥나는 거야. "
                        f"좀 놀랄 수 있지만, 지금 알게 된 게 오히려 다행이야! "
                        f"아래 시나리오들 보면 작은 변화로도 크게 달라질 수 있어.")})
        elif dep_age <= 70:
            tips.append({"icon":"⚠️","title":f"{dep_age}세쯤 자산이 바닥날 수 있어",
                "body":(f"지금 흐름대로라면 {dep_year}년({dep_age}세)에 자산이 소진돼. "
                        f"은퇴 후 약 {dep_age - retire}년 뒤야. "
                        f"아직 시간이 있으니까, 미리 준비하면 훨씬 여유로운 노후를 만들 수 있어!")})
        elif dep_age <= life:
            tips.append({"icon":"💡","title":f"자산이 {dep_age}세까지는 버텨주는데, 조금만 더 늘려보자",
                "body":(f"현재 계획대로면 {dep_age}세까지는 괜찮아. "
                        f"다만 기대수명({life}세)까지 {life - dep_age}년의 공백이 생길 수 있거든. "
                        f"작은 조정만으로도 이 공백을 메울 수 있으니까 너무 걱정 마!")})
    else:
        final_nw = int(df.iloc[-1]["net_worth"])
        tips.append({"icon":"🎉","title":"대단해! 기대수명까지 자산이 충분히 유지돼",
            "body":(f"현재 계획대로라면 {life}세에도 약 {fmt_krw(final_nw)}가 남아. "
                    f"정말 잘 관리하고 있는 거야! "
                    f"더 여유로운 노후를 원한다면 아래 시나리오들도 한번 살펴봐.")})

    # 2. 동연령 비교
    if diff >= 0:
        if diff_pct >= 150:
            tips.append({"icon":"🏆","title":f"같은 나이 평균보다 {diff_pct - 100}%나 더 많아!",
                "body":(f"동연령 평균({fmt_krw(peer)})보다 {fmt_krw(diff)} 더 갖고 있어. "
                        f"여기까지 오느라 정말 수고했어. 이 흐름 그대로 유지하면 돼!")})
        else:
            tips.append({"icon":"👍","title":"같은 나이 평균 이상이야, 잘하고 있어!",
                "body":(f"동연령 평균({fmt_krw(peer)}) 대비 {fmt_krw(diff)} 더 많아. "
                        f"꾸준히 잘 해온 결과야. 자신감 가져도 돼!")})
    else:
        gap = abs(diff)
        monthly_gap = round(gap / max(years_to_retire * 12, 12))
        tips.append({"icon":"📊","title":"동연령 평균과 차이가 있지만, 따라잡을 수 있어",
            "body":(f"지금 같은 나이 평균({fmt_krw(peer)})보다 {fmt_krw(gap)} 적어. "
                    f"하지만 매달 {monthly_gap:,}만원씩만 추가로 모으면 은퇴 전에 따라잡을 수 있어. "
                    f"작은 금액이라도 복리로 불어나면 생각보다 빨리 좁혀져!")})

    # 3. 지출 절감 효과
    if dep_info:
        s2 = scenarios.get("저축 강화")
        if s2 is not None:
            d2, _, _ = get_key_metrics(s2, life)
            el = "변동비" if mode == "detailed" else "지출"
            if not d2:
                tips.append({"icon":"✂️","title":"한 달에 50만원만 아끼면 고갈이 완전히 사라져!",
                    "body":(f"{el}을 월 50만원만 줄이면 기대수명까지 자산이 유지돼. "
                            f"외식 줄이기, 구독 정리, 커피값 아끼기... "
                            f"하나씩 점검해 보면 의외로 쉽게 찾을 수 있을 거야.")})
            elif d2["age"] > dep_info["age"]:
                delay = d2["age"] - dep_info["age"]
                tips.append({"icon":"✂️","title":f"월 50만원 절약하면 {delay}년을 더 벌 수 있어",
                    "body":(f"{el}을 월 50만원 줄이면 "
                            f"자산 소진이 {dep_info['age']}세 → {d2['age']}세로 "
                            f"{delay}년 늦춰져. 작지 않은 차이지?")})

    # 4. 은퇴 연장 효과
    if dep_info:
        s3 = scenarios.get("은퇴 3년 연장")
        if s3 is not None:
            d3, _, _ = get_key_metrics(s3, life)
            if not d3:
                tips.append({"icon":"⏰","title":"3년만 더 일하면 자산 고갈이 사라져!",
                    "body":(f"은퇴를 {retire}세 → {retire+3}세로 3년만 늦추면 "
                            f"기대수명까지 자산이 유지돼. "
                            f"3년간의 추가 수입과 지출 기간 단축이 합쳐져서 효과가 정말 커!")})
            elif d3["age"] > dep_info["age"]:
                delay = d3["age"] - dep_info["age"]
                tips.append({"icon":"⏰","title":f"은퇴를 3년 늦추면 {delay}년이나 더 여유가 생겨",
                    "body":(f"은퇴를 {retire}세 → {retire+3}세로 조정하면 "
                            f"자산 소진이 {dep_info['age']}세 → {d3['age']}세로 늦춰져. "
                            f"건강이 허락한다면 고려해 볼 만한 선택이야.")})

    # 5. 수익률 시나리오
    r5 = scenarios.get("매년 5% 수익")
    if r5 is not None and dep_info:
        d5, _, _ = get_key_metrics(r5, life)
        if not d5:
            tips.append({"icon":"📈","title":"자산 수익률을 좀 더 높여볼까?",
                "body":(f"연 5% 수익률로 운용하면 기대수명까지 자산이 유지돼. "
                        f"예적금 위주에서 인덱스 펀드나 ETF를 조금씩 섞는 것만으로도 "
                        f"장기적으로 4~6% 수익을 기대할 수 있어. 한번 알아보는 건 어때?")})
        elif d5["age"] > dep_info["age"]:
            delay = d5["age"] - dep_info["age"]
            tips.append({"icon":"📈","title":f"수익률을 5%까지 올리면 {delay}년 더 버틸 수 있어",
                "body":(f"자산 수익률을 연 5%까지 높이면 소진 시점이 {delay}년 늦춰져. "
                        f"분산 투자로 리스크를 관리하면서 수익률을 높이는 전략, "
                        f"요즘은 공부할 자료도 많으니까 한번 살펴봐!")})
    elif r5 is not None and not dep_info:
        final_base = int(df.iloc[-1]["net_worth"])
        final_5 = int(r5.iloc[-1]["net_worth"])
        if final_5 > final_base * 1.3:
            extra = final_5 - final_base
            tips.append({"icon":"📈","title":"수익률을 조금만 높이면 노후가 훨씬 넉넉해져",
                "body":(f"연 5% 수익률로 운용하면 {life}세 자산이 "
                        f"{fmt_krw(final_base)} → {fmt_krw(final_5)}로 "
                        f"{fmt_krw(extra)}나 더 늘어나. 여유로운 노후를 위해 투자 공부 한번 해볼까?")})

    # 6. 은퇴 후 소득 제안
    retire_inc = _safe_float(params.get("retire_income", 0))
    if retire_inc == 0 and dep_info:
        for test_inc in [50, 100, 150, 200, 300]:
            test_df = run_simulation(params, {"retire_income": test_inc})
            td, _, _ = get_key_metrics(test_df, life)
            if not td:
                tips.append({"icon":"💼","title":f"은퇴 후에 월 {test_inc}만원만 벌면 충분해!",
                    "body":(f"은퇴하고도 파트타임이나 프리랜서, 임대 수입 등으로 "
                            f"월 {test_inc}만원만 벌면 자산 고갈을 막을 수 있어. "
                            f"경험과 전문성을 살린 일을 미리 준비해 두면 어떨까?")})
                break

    # 7. FIRE
    if fire:
        yl = fire.get("years_left", -1)
        if yl == 0:
            tips.append({"icon":"🔥","title":"FIRE 달성! 이미 경제적 독립 상태야!",
                "body":(f"순자산이 FIRE 목표({fmt_krw(fire.get('target',0))})를 넘었어. "
                        f"원하면 지금이라도 경제적 자유를 누릴 수 있는 상태야. 축하해! 🎊")})
        elif 0 < yl <= 5:
            tips.append({"icon":"🔥","title":f"FIRE까지 {yl}년 남았어! 거의 다 왔어!",
                "body":(f"이 페이스 유지하면 {yl}년 후 경제적 독립에 도달해. "
                        f"조금만 더 힘내자, 끝이 보여!")})

    # 8. 대출
    if mode == "detailed":
        loans = params.get("loans", [])
        total_interest = 0
        for l in loans:
            amt = _safe_float(l.get("amount", 0))
            rate = _safe_float(l.get("rate", 0)) / 100
            years = _safe_int(l.get("years", 0))
            if amt > 0 and years > 0 and rate > 0:
                mr = rate / 12; np_ = years * 12
                mp = amt * mr * ((1+mr)**np_) / (((1+mr)**np_) - 1)
                total_interest += mp * np_ - amt
        if total_interest > 1000:
            tips.append({"icon":"🏦","title":f"대출 이자만 총 {fmt_krw(round(total_interest))}를 내게 돼",
                "body":(f"대출을 끝까지 갚으면 이자로만 {fmt_krw(round(total_interest))}가 나가. "
                        f"여유 자금이 생기면 일부라도 조기 상환하는 걸 고려해 봐. "
                        f"이자 줄이는 게 가장 확실한 절약이야!")})

    # 9. 마무리 격려
    if dep_info:
        tips.append({"icon":"💪","title":"이렇게 확인한 것만으로도 이미 한 발 앞서 있는 거야",
            "body":("대부분의 사람들은 미래 재정을 점검하지 않아. "
                    "지금 이렇게 확인하고 있다는 것 자체가 이미 좋은 출발이야. "
                    "위의 시나리오들 참고해서 작은 변화부터 시작해 봐. "
                    "작은 조정이 수십 년 뒤에는 정말 큰 차이를 만들어!")})
    else:
        tips.append({"icon":"🌟","title":"앞으로도 가끔 점검해 보면 좋겠다!",
            "body":("재정 계획은 한 번 세우면 끝이 아니라, 상황에 따라 조정하는 게 중요해. "
                    "1~2년에 한 번 이 시뮬레이션을 다시 돌려보면 "
                    "더 정확하고 안정적인 노후를 준비할 수 있을 거야. 화이팅!")})

    return tips
