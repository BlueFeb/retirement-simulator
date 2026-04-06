"""
테마 — 주간/야간 CSS

전략:
- config.toml에서 base="light" 설정 → 주간모드는 Streamlit 네이티브 라이트 테마 사용
- 주간모드 CSS는 최소한의 보조만 (폰트, 터치 영역, 카드 스타일)
- 야간모드 CSS만 배경/텍스트 색상을 전면 override
"""

# 공통 (폰트, 모바일 최적화 — 색상 관련 없음)
COMMON_CSS = """
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

body, p, h1, h2, h3, h4, h5, h6,
li, td, th, label,
input, textarea, select,
.stMarkdown, .stCaption p,
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"],
.stRadio label span {
    font-family: 'Pretendard', -apple-system, 'Apple SD Gothic Neo', sans-serif !important;
}

.stApp > header { visibility: hidden; }
[data-testid="stSidebar"] { display: none; }

div[data-testid="stMetricValue"] { font-size: 22px !important; }
input[type="number"], .stSelectbox [data-baseweb="select"] {
    min-height: 44px !important; font-size: 16px !important;
}
.stButton > button { min-height: 52px !important; font-size: 16px !important; border-radius: 12px !important; }
.stButton > button[kind="primary"] { font-weight: 700 !important; font-size: 17px !important; }
.stDownloadButton > button { min-height: 48px !important; font-size: 15px !important; border-radius: 12px !important; }
button[data-testid="stNumberInput-StepUp"],
button[data-testid="stNumberInput-StepDown"] { min-width: 36px !important; min-height: 36px !important; }
.js-plotly-plot .plotly .modebar { display: none !important; }

@media (max-width: 600px) {
    div[data-testid="column"] { width: 100% !important; flex: 100% !important; min-width: 100% !important; }
    h1 { font-size: 22px !important; }
    h2 { font-size: 17px !important; }
    div[data-testid="stMetricValue"] { font-size: 20px !important; }
    .block-container { padding: 1rem 0.8rem !important; }
}
h1 { text-align: center; }
.subtitle { text-align: center; font-size: 14px; margin-bottom: 20px; }
.section-divider { border: none; border-top: 1px solid rgba(0,0,0,0.08); margin: 20px 0; }
"""

# 주간 모드 — Streamlit 네이티브 라이트 테마 그대로 사용, 카드만 보조
LIGHT_CSS = COMMON_CSS + """
div[data-testid="stMetric"] {
    background: rgba(79,70,229,0.06);
    border: 1px solid rgba(79,70,229,0.15);
    border-radius: 14px; padding: 14px 16px;
}
.subtitle { color: #64748b; }
"""

# 야간 모드 — 모든 색상 전면 override (와일드카드 사용)
DARK_CSS = COMMON_CSS + """
/* 전체 배경 */
.stApp, .stApp > *, [data-testid="stAppViewContainer"],
section[data-testid="stMain"], [data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlock"], [data-testid="stHeader"],
[data-testid="stBottom"] { background-color: #0c0f14 !important; }

/* 전체 텍스트 — 와일드카드로 확실히 */
.stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
.stApp label, .stApp li, .stApp td, .stApp th,
.stApp [data-testid="stMarkdownContainer"] *,
.stApp [data-testid="stMetricValue"], .stApp [data-testid="stMetricLabel"],
.stApp [data-testid="stMetricDelta"] *,
.stApp [data-testid="stText"],
.stApp .stRadio label *, .stApp .stSelectbox label,
.stApp .stNumberInput label,
.stApp [data-testid="stExpanderDetails"] *,
.stApp summary *, .stApp [data-testid="stInfo"] *,
.stApp [data-testid="stAlert"] * {
    color: #e4e4e7 !important;
}
.stApp .stCaption p, .stApp [data-testid="stCaptionContainer"] * {
    color: #71717a !important;
}

/* 입력 필드 */
.stApp input, .stApp textarea, .stApp select,
.stApp [data-baseweb="input"] *, .stApp [data-baseweb="select"] * {
    color: #e4e4e7 !important;
    background-color: #1a1f2e !important;
}
.stApp [data-baseweb="popover"] * { background-color: #1a1f2e !important; color: #e4e4e7 !important; }

/* 버튼 */
.stApp .stButton > button:not([kind="primary"]) { color: #e4e4e7 !important; background-color: #1a1f2e !important; }
.stApp .stDownloadButton > button { color: #e4e4e7 !important; background-color: #1a1f2e !important; }

/* 카드/metric */
.stApp div[data-testid="stMetric"] {
    background: rgba(99,102,241,0.08) !important;
    border: 1px solid rgba(99,102,241,0.2) !important;
    border-radius: 14px; padding: 14px 16px;
}

/* expander */
.stApp [data-testid="stExpander"] { background-color: #12161e !important; border-color: rgba(255,255,255,0.06) !important; }

/* radio/selectbox 옵션 */
.stApp [role="radiogroup"] label { color: #e4e4e7 !important; }
.stApp [data-baseweb="radio"] * { color: #e4e4e7 !important; }

/* 구분선 */
.stApp .section-divider { border-color: rgba(255,255,255,0.06) !important; }
.stApp .subtitle { color: #71717a !important; }

/* 테이블 */
.stApp [data-testid="stDataFrame"] * { color: #e4e4e7 !important; }
.stApp [data-testid="stTable"] * { color: #e4e4e7 !important; }
"""

def get_css(dark_mode):
    return DARK_CSS if dark_mode else LIGHT_CSS

def get_header_color(dark_mode):
    return "#6366f1" if dark_mode else "#4f46e5"

def get_diff_colors(dark_mode):
    if dark_mode: return "#34d399", "#f87171"
    return "#059669", "#dc2626"
