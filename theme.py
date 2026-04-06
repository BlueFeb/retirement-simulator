"""
테마 — 주간/야간 CSS
핵심: Pretendard를 span, div에 적용하면 Streamlit 아이콘이 깨짐.
     텍스트 입력/출력 요소에만 적용하고, 나머지는 Streamlit 기본 폰트를 유지.
"""

COMMON_CSS = """
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

/*
 * ⚠️ span, div 에는 절대 font-family를 적용하지 않음!
 * Streamlit expander 화살표, metric delta, number input +-
 * 등이 모두 span/div 안의 특수 문자/SVG로 렌더링됨.
 * 여기에 Pretendard를 강제하면 아이콘이 깨져서 □ 또는 글자로 보임.
 */
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
.section-divider { border: none; border-top: 1px solid; margin: 20px 0; }
"""

LIGHT_CSS = COMMON_CSS + """
div[data-testid="stMetric"] {
    background: rgba(79,70,229,0.06); border: 1px solid rgba(79,70,229,0.15);
    border-radius: 14px; padding: 14px 16px;
}
.subtitle { color: #64748b !important; }
.section-divider { border-color: rgba(0,0,0,0.08); }

/* 라이트 모드: 배경 흰색 + 모든 텍스트 어둡게 강제 */
.stApp, [data-testid="stAppViewContainer"], section[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background-color: #ffffff !important;
    color: #1e293b !important;
}
[data-testid="stHeader"] { background-color: #ffffff !important; }

/* 모든 텍스트 요소에 어두운 색 강제 */
p, h1, h2, h3, h4, h5, h6, label, li, td, th,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"],
[data-testid="stMetricDelta"], [data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stText"], [data-testid="stCaptionContainer"],
.stRadio label, .stSelectbox label, .stNumberInput label,
[data-baseweb="select"] *, [data-baseweb="input"] *,
.stExpander summary, .stExpander [data-testid="stExpanderDetails"],
[data-testid="stInfo"] p, [data-testid="stAlert"] p {
    color: #1e293b !important;
}
.stCaption p, [data-testid="stCaptionContainer"] p { color: #64748b !important; }

/* 입력 필드 텍스트/배경 */
input, textarea, select, [data-baseweb="input"] input,
[data-baseweb="select"] [data-baseweb="tag"] {
    color: #1e293b !important;
    background-color: #ffffff !important;
}

/* 버튼 텍스트 */
.stButton > button:not([kind="primary"]) { color: #1e293b !important; }
.stDownloadButton > button { color: #1e293b !important; }

/* expander 배경 */
[data-testid="stExpander"] { background-color: #f8fafc !important; border-radius: 12px; }

/* 테이블 */
[data-testid="stDataFrame"] { color: #1e293b !important; }
"""

DARK_CSS = COMMON_CSS + """
div[data-testid="stMetric"] {
    background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2);
    border-radius: 14px; padding: 14px 16px;
}
.subtitle { color: #71717a; }
.section-divider { border-color: rgba(255,255,255,0.06); }

/* 다크 모드 배경/텍스트 강제 */
.stApp, [data-testid="stAppViewContainer"], section[data-testid="stMain"] {
    background-color: #0c0f14 !important;
    color: #e4e4e7 !important;
}
[data-testid="stHeader"] { background-color: #0c0f14 !important; }
p, h1, h2, h3, h4, h5, h6, label, li, td, th {
    color: #e4e4e7 !important;
}
.stCaption p { color: #71717a !important; }
"""

def get_css(dark_mode):
    return DARK_CSS if dark_mode else LIGHT_CSS

def get_header_color(dark_mode):
    return "#6366f1" if dark_mode else "#4f46e5"

def get_diff_colors(dark_mode):
    if dark_mode: return "#34d399", "#f87171"
    return "#059669", "#dc2626"
