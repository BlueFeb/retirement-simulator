"""
Google Sheets 자동 저장 모듈 — 디버깅 로그 포함
"""
import json
from datetime import datetime
import streamlit as st


def get_gsheet_connection():
    """Google Sheets 연결. 실패 시 에러 메시지를 st.session_state에 저장."""
    try:
        # secrets 키 존재 확인
        if "gcp_service_account" not in st.secrets:
            st.session_state["gsheet_error"] = "secrets에 [gcp_service_account] 섹션이 없습니다"
            return None
        if "google_sheets" not in st.secrets:
            st.session_state["gsheet_error"] = "secrets에 [google_sheets] 섹션이 없습니다"
            return None

        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]

        creds_dict = dict(st.secrets["gcp_service_account"])

        # 필수 키 검증
        required_keys = ["type", "project_id", "private_key", "client_email",
                         "token_uri"]
        missing = [k for k in required_keys if k not in creds_dict]
        if missing:
            st.session_state["gsheet_error"] = f"secrets에 누락된 키: {', '.join(missing)}"
            return None

        # private_key 형식 검증
        pk = creds_dict.get("private_key", "")
        if "BEGIN PRIVATE KEY" not in pk:
            st.session_state["gsheet_error"] = (
                "private_key 형식 오류. "
                "JSON 파일에서 private_key 값을 그대로 복사했는지 확인하세요. "
                "-----BEGIN PRIVATE KEY----- 로 시작해야 합니다."
            )
            return None

        # client_email 형식 검증
        email = creds_dict.get("client_email", "")
        if "@" not in email or ".iam.gserviceaccount.com" not in email:
            st.session_state["gsheet_error"] = (
                f"client_email 형식 오류: '{email[:30]}...'. "
                "xxx@project-id.iam.gserviceaccount.com 형태여야 합니다."
            )
            return None

        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        sheet_name = st.secrets["google_sheets"]["spreadsheet_name"]
        spreadsheet = client.open(sheet_name)

        st.session_state["gsheet_error"] = None
        return spreadsheet

    except Exception as e:
        err_str = str(e)
        # 구체적인 에러 안내
        if "invalid_grant" in err_str:
            hint = (
                "invalid_grant 에러 — 가능한 원인:\n"
                "1. private_key를 복사할 때 \\n이 실제 줄바꿈으로 바뀌었을 수 있음\n"
                "2. 서비스 계정이 삭제되었거나 비활성화됨\n"
                "3. JSON 파일의 내용이 잘려서 들어감\n\n"
                "해결법: GCP Console → 서비스 계정 → 키 탭에서 "
                "새 JSON 키를 다시 생성하고 secrets에 다시 붙여넣기"
            )
            st.session_state["gsheet_error"] = hint
        elif "not found" in err_str.lower() and "spreadsheet" in err_str.lower():
            st.session_state["gsheet_error"] = (
                f"스프레드시트를 찾을 수 없음. 이름이 정확히 "
                f"'{st.secrets['google_sheets']['spreadsheet_name']}'인지, "
                f"서비스 계정({creds_dict.get('client_email','?')})이 "
                f"편집자로 공유되어 있는지 확인하세요."
            )
        else:
            st.session_state["gsheet_error"] = f"연결 실패: {err_str}"
        return None


def save_to_gsheet(inputs, results):
    """시뮬레이션 결과 저장. 성공/실패 + 에러 메시지 반환."""
    spreadsheet = get_gsheet_connection()
    if spreadsheet is None:
        err = st.session_state.get("gsheet_error", "알 수 없는 오류")
        return False, err

    try:
        # 시트 가져오거나 생성
        try:
            ws = spreadsheet.worksheet("시뮬레이션_기록")
        except Exception:
            ws = spreadsheet.add_worksheet(title="시뮬레이션_기록", rows=1000, cols=35)
            headers = [
                "기록일시","모드","나이","성별","은퇴","기대수명",
                "총자산","월수입","월지출",
                "예금","예금%","주식","주식%","부동산","부동산%","기타",
                "급여","부수입","연금","연금시작",
                "고정비","변동비","(미사용)","물가상승률","대출JSON",
                "고갈연도","고갈나이","최대자산","최대나이","순자산","평균",
                "FIRE진행률","안전인출액","메모"]
            ws.update("A1", [headers])

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        m = inputs.get("mode", "simple")
        g = "남성" if inputs.get("gender") == "male" else "여성"

        row = [now, "간단" if m == "simple" else "상세",
               str(inputs.get("age", "")), g,
               str(inputs.get("retire_age", "")),
               str(inputs.get("life_expectancy", ""))]

        if m == "simple":
            row += [
                str(inputs.get("total_savings", "")),
                str(inputs.get("monthly_income", "")),
                str(inputs.get("monthly_expense", "")),
                "", "", "", "", "", "", "",
                "", "", "", "",
                "", "", "",
                str(inputs.get("inflation_rate", "")),
                ""
            ]
        else:
            row += [
                "", "", "",
                str(inputs.get("deposit_amount", "")),
                str(inputs.get("deposit_rate", "")),
                str(inputs.get("stock_amount", "")),
                str(inputs.get("stock_return", "")),
                str(inputs.get("real_estate_amount", "")),
                str(inputs.get("real_estate_return", "")),
                str(inputs.get("other_assets", "")),
                str(inputs.get("salary", "")),
                str(inputs.get("side_income", "")),
                str(inputs.get("pension_monthly", "")),
                str(inputs.get("pension_start_age", "")),
                str(inputs.get("fixed_cost", "")),
                str(inputs.get("variable_cost", "")),
                "",
                str(inputs.get("inflation_rate", "")),
                json.dumps(inputs.get("loans", []), ensure_ascii=False)
            ]

        dep = results.get("depletion")
        pk = results.get("peak", {})
        cur = results.get("current", {})
        fire = results.get("fire", {})
        safe = results.get("safe_withdrawal", {})

        row += [
            str(dep["year"]) if dep else "없음",
            str(dep["age"]) if dep else "",
            str(pk.get("net_worth", "")),
            str(pk.get("age", "")),
            str(cur.get("net_worth", "")),
            str(cur.get("avg_peer", "")),
            str(fire.get("progress", "")),
            str(safe.get("safe_monthly", "") if safe else ""),
            ""
        ]

        ws.append_row(row, value_input_option="USER_ENTERED")
        return True, "저장 완료"

    except Exception as e:
        return False, f"저장 실패: {str(e)}"
