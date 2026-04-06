"""
PDF 보고서 — CID 한글 폰트 + matplotlib 차트 이미지
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

from engine import fmt_krw

pdfmetrics.registerFont(UnicodeCIDFont("HYGothic-Medium"))
FONT = "HYGothic-Medium"

INDIGO=HexColor("#4338ca"); GREEN=HexColor("#059669")
RED=HexColor("#dc2626"); GRAY=HexColor("#64748b")
LIGHT=HexColor("#f1f5f9"); WHITE=HexColor("#ffffff"); BORDER=HexColor("#cbd5e1"); DARK=HexColor("#1e293b")

S_TITLE = ParagraphStyle("t",fontName=FONT,fontSize=18,leading=26,textColor=INDIGO,alignment=TA_CENTER,spaceAfter=3*mm)
S_SUB   = ParagraphStyle("s",fontName=FONT,fontSize=9,leading=13,textColor=GRAY,alignment=TA_CENTER,spaceAfter=6*mm)
S_H2    = ParagraphStyle("h",fontName=FONT,fontSize=12,leading=17,textColor=INDIGO,spaceBefore=6*mm,spaceAfter=3*mm)
S_BODY  = ParagraphStyle("b",fontName=FONT,fontSize=9,leading=14,textColor=DARK,spaceAfter=2*mm)
S_FOOT  = ParagraphStyle("f",fontName=FONT,fontSize=7.5,leading=11,textColor=GRAY,alignment=TA_CENTER,spaceBefore=4*mm)

def _bts():
    return [("FONTNAME",(0,0),(-1,-1),FONT),("FONTSIZE",(0,0),(-1,-1),9),
            ("BACKGROUND",(0,0),(-1,0),INDIGO),("TEXTCOLOR",(0,0),(-1,0),WHITE),
            ("GRID",(0,0),(-1,-1),0.5,BORDER),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),2.5*mm),("BOTTOMPADDING",(0,0),(-1,-1),2.5*mm),
            ("LEFTPADDING",(0,0),(-1,-1),2*mm)]

def _add_img(el, img_bytes, w_mm=160):
    if img_bytes:
        img = Image(io.BytesIO(img_bytes), width=w_mm*mm, height=w_mm*mm*0.5)
        el.append(img)
        el.append(Spacer(1, 3*mm))


def generate_pdf_report(df, params, dep_info, peak_info, current_info,
                         chart_images=None):
    chart_images = chart_images or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf,pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,
                            topMargin=18*mm,bottomMargin=18*mm)
    el = []

    # 타이틀
    el.append(Paragraph("자산 고갈 시뮬레이션 보고서", S_TITLE))
    now_s = datetime.now().strftime("%Y년 %m월 %d일")
    age=params.get("age",""); gl="남성" if params.get("gender")=="male" else "여성"
    ret=params.get("retire_age",""); life=params.get("life_expectancy","")
    ml="간단" if params.get("mode")=="simple" else "상세"
    el.append(Paragraph(f"{now_s} | {gl} {age}세 | 은퇴 {ret}세 | 기대수명 {life}세 | {ml} 분석", S_SUB))
    el.append(HRFlowable(width="100%",thickness=1,color=BORDER,spaceAfter=4*mm))

    # 핵심 요약
    el.append(Paragraph("핵심 요약", S_H2))
    dep_t = f"{dep_info['year']}년 ({dep_info['age']}세)" if dep_info else "고갈 없음"
    pk_t = f"{fmt_krw(peak_info['net_worth'])} ({peak_info['year']}년, {peak_info['age']}세)"
    diff = current_info["net_worth"] - current_info["avg_peer"]
    diff_t = f"{'+'if diff>=0 else''}{fmt_krw(diff)}"
    sd = [["항목","결과"],["자산 고갈",dep_t],["최대 자산",pk_t],
          ["현재 순자산",fmt_krw(current_info["net_worth"])],
          ["동연령 평균",fmt_krw(current_info["avg_peer"])],["평균 대비",diff_t]]
    st = _bts()+[("BACKGROUND",(0,1),(0,-1),LIGHT),
                  ("TEXTCOLOR",(1,1),(1,1),RED if dep_info else GREEN),
                  ("TEXTCOLOR",(1,5),(1,5),GREEN if diff>=0 else RED)]
    t = Table(sd,colWidths=[48*mm,112*mm]); t.setStyle(TableStyle(st)); el.append(t)

    # 파이 차트
    if chart_images.get("pie"):
        el.append(Paragraph("현재 자산 구성", S_H2))
        _add_img(el, chart_images["pie"], 110)

    # 메인 차트
    if chart_images.get("main"):
        el.append(Paragraph("순자산 추이", S_H2))
        _add_img(el, chart_images["main"])

    # 주요 시점 테이블
    el.append(Paragraph("주요 시점별 자산", S_H2))
    m_ages = sorted(set([int(age),int(ret),65,70,80,int(life)]))
    mdf = df[df["age"].isin(m_ages)]
    md = [["연도","나이","내 순자산","동연령 평균","차이"]]
    ms = _bts()+[("ALIGN",(2,1),(-1,-1),"RIGHT")]
    for idx,(_,row) in enumerate(mdf.iterrows()):
        d=int(row["net_worth"]-row["avg_peer"])
        md.append([f"{int(row['year'])}년",f"{int(row['age'])}세",fmt_krw(row["net_worth"]),
                   fmt_krw(row["avg_peer"]),f"{'+'if d>=0 else''}{fmt_krw(d)}"])
        ri=idx+1
        if row["net_worth"]<0: ms.append(("TEXTCOLOR",(2,ri),(2,ri),RED))
        ms.append(("TEXTCOLOR",(4,ri),(4,ri),GREEN if d>=0 else RED))
        if ri%2==0: ms.append(("BACKGROUND",(0,ri),(-1,ri),LIGHT))
    mt=Table(md,colWidths=[27*mm,18*mm,38*mm,38*mm,38*mm])
    mt.setStyle(TableStyle(ms)); el.append(mt)

    # 페이지 브레이크 + 추가 차트들
    has_extra = any(chart_images.get(k) for k in ["composition","cashflow","scenarios","sensitivity"])
    if has_extra:
        el.append(PageBreak())

    if chart_images.get("composition"):
        el.append(Paragraph("자산 구성 변화", S_H2))
        _add_img(el, chart_images["composition"])

    if chart_images.get("scenarios"):
        el.append(Paragraph("시나리오 비교", S_H2))
        el.append(Paragraph("① 현재 계획  ② 저축 강화  ③ 은퇴 3년 연장", S_BODY))
        _add_img(el, chart_images["scenarios"])

    if chart_images.get("sensitivity"):
        el.append(Paragraph("민감도 분석 (낙관 / 기본 / 비관)", S_H2))
        _add_img(el, chart_images["sensitivity"])

    # 입력 조건
    el.append(Paragraph("입력 조건", S_H2))
    if params.get("mode")=="simple":
        cd=[["항목","값"],
            ["총 자산",f"{params.get('total_savings',0):,.0f}만원"],
            ["월 수입",f"{params.get('monthly_income',0):,.0f}만원"],
            ["월 지출",f"{params.get('monthly_expense',0):,.0f}만원"],
            ["물가상승률",f"{params.get('inflation_rate',0)}%"]]
    else:
        cd=[["항목","값"],
            ["예금",f"{params.get('deposit_amount',0):,.0f}만원 ({params.get('deposit_rate',0)}%)"],
            ["주식",f"{params.get('stock_amount',0):,.0f}만원 ({params.get('stock_return',0)}%)"],
            ["부동산",f"{params.get('real_estate_amount',0):,.0f}만원 ({params.get('real_estate_return',0)}%)"],
            ["급여",f"{params.get('salary',0):,.0f}만원/월"],
            ["연금",f"{params.get('pension_monthly',0):,.0f}만원/월 ({params.get('pension_start_age',65)}세~)"],
            ["고정비",f"{params.get('fixed_cost',0):,.0f}만원 (물가50%)"],
            ["변동비",f"{params.get('variable_cost',0):,.0f}만원 (물가100%)"],
            ["물가상승률",f"{params.get('inflation_rate',0)}%"]]
        for i,l in enumerate(params.get("loans",[])):
            cd.append([f"대출{i+1}",f"{l['amount']:,.0f}만원/{l['rate']}%/{l['years']}년"])
    cs=_bts()+[("BACKGROUND",(0,1),(0,-1),LIGHT)]
    ct=Table(cd,colWidths=[42*mm,118*mm]); ct.setStyle(TableStyle(cs)); el.append(ct)

    # 면책
    el.append(Spacer(1,4*mm))
    el.append(HRFlowable(width="100%",thickness=0.5,color=BORDER,spaceAfter=2*mm))
    el.append(Paragraph("본 보고서는 참고용이며 실제 투자 성과와 다를 수 있습니다. "
        "한국은행 2026.2 기준 예금 2.83%, 대출 4.26%. 평균자산: 2025 가계금융복지조사.", S_FOOT))

    doc.build(el)
    buf.seek(0)
    return buf.read()
