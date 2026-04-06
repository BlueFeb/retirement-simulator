"""
Google Sheets 자동 저장 모듈
"""
import json
from datetime import datetime
import streamlit as st


def get_gsheet_connection():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes)
        client = gspread.authorize(creds)
        return client.open(st.secrets["google_sheets"]["spreadsheet_name"])
    except Exception:
        return None


def save_to_gsheet(inputs, results):
    spreadsheet = get_gsheet_connection()
    if spreadsheet is None:
        return False
    try:
        try:
            ws = spreadsheet.worksheet("시뮬레이션_기록")
        except Exception:
            ws = spreadsheet.add_worksheet(title="시뮬레이션_기록", rows=1000, cols=35)
            ws.update("A1", [[
                "기록일시","모드","나이","성별","은퇴","기대수명",
                "총자산","월수입","월지출",
                "예금","예금%","주식","주식%","부동산","부동산%","기타",
                "급여","부수입","연금","연금시작",
                "고정비","변동비","저축률","물가상승률","대출JSON",
                "고갈연도","고갈나이","최대자산","최대나이","순자산","평균",
                "FIRE진행률","안전인출액","시나리오메모"]])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        m = inputs.get("mode","simple")
        g = "남성" if inputs.get("gender")=="male" else "여성"
        row = [now, "간단" if m=="simple" else "상세",
               inputs.get("age",""), g,
               inputs.get("retire_age",""), inputs.get("life_expectancy","")]

        if m == "simple":
            row += [inputs.get("total_savings",""), inputs.get("monthly_income",""),
                    inputs.get("monthly_expense",""),
                    "","","","","","","","","","","",
                    "","","",inputs.get("inflation_rate",""),""]
        else:
            row += ["","","",
                    inputs.get("deposit_amount",""), inputs.get("deposit_rate",""),
                    inputs.get("stock_amount",""), inputs.get("stock_return",""),
                    inputs.get("real_estate_amount",""), inputs.get("real_estate_return",""),
                    inputs.get("other_assets",""),
                    inputs.get("salary",""), inputs.get("side_income",""),
                    inputs.get("pension_monthly",""), inputs.get("pension_start_age",""),
                    inputs.get("fixed_cost",""), inputs.get("variable_cost",""),
                    inputs.get("savings_rate",""), inputs.get("inflation_rate",""),
                    json.dumps(inputs.get("loans",[]),ensure_ascii=False)]

        dep = results.get("depletion")
        pk = results.get("peak")
        cur = results.get("current")
        fire = results.get("fire", {})
        safe = results.get("safe_withdrawal", {})

        row += [dep["year"] if dep else "없음", dep["age"] if dep else "",
                pk["net_worth"] if pk else "", pk["age"] if pk else "",
                cur["net_worth"] if cur else "", cur["avg_peer"] if cur else "",
                fire.get("progress",""), safe.get("safe_monthly",""), ""]

        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.warning(f"Sheets 오류: {e}")
        return False
