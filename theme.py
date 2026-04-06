"""
테마 (주간/야간 모드) CSS
"""

COMMON_CSS = """
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
/* 아이콘 폰트를 덮어쓰지 않도록 body/input/button 등에만 적용 */
body, p, h1, h2, h3, h4, h5, h6, span, div, li, td, th, label,
input, textarea, select, button, a {
    font-family: 'Pretendard', -apple-system, 'Apple SD Gothic Neo', sans-serif !important;
}
/* Streamlit 아이콘/화살표 폰트 보호 */
[data-testid="stExpanderToggleIcon"],
.st-emotion-cache-1gulkj5,
svg, i, [class*="icon"], [class*="arrow"], [class*="Icon"],
[data-baseweb] svg {
    font-family: inherit !important;
}
.stApp > div > div > div > div { max-width: 720px; margin: 0 auto; }
[data-testid="stSidebar"] { display: none; }

div[data-testid="stMetricValue"] { font-size: 22px !important; }
input[type="number"], .stSelectbox > div > div {
    min-height: 44px !important; font-size: 16px !important;
}
.stButton > button { min-height: 52px !important; font-size: 16px !important; border-radius: 12px !important; }
.stButton > button[kind="primary"] { font-weight: 700 !important; font-size: 17px !important; }
.stDownloadButton > button { min-height: 48px !important; font-size: 15px !important; border-radius: 12px !important; }
.stRadio label { padding: 10px 16px !important; min-height: 44px !important; }
button[data-testid="stNumberInput-StepUp"],
button[data-testid="stNumberInput-StepDown"] { min-width: 36px !important; min-height: 36px !important; }
.js-plotly-plot .plotly .modebar { display: none !important; }
.streamlit-expanderHeader { min-height: 48px !important; font-size: 15px !important; }

@media (max-width: 600px) {
    div[data-testid="column"] { width: 100% !important; flex: 100% !important; min-width: 100% !important; }
    h1 { font-size: 22px !important; }
    h2, .stSubheader { font-size: 17px !important; }
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
.subtitle { color: #64748b; }
.section-divider { border-color: rgba(0,0,0,0.08); }
"""

DARK_CSS = COMMON_CSS + """
div[data-testid="stMetric"] {
    background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.2);
    border-radius: 14px; padding: 14px 16px;
}
.subtitle { color: #71717a; }
.section-divider { border-color: rgba(255,255,255,0.06); }
"""

def get_css(dark_mode):
    return DARK_CSS if dark_mode else LIGHT_CSS

def get_header_color(dark_mode):
    return "#6366f1" if dark_mode else "#4f46e5"

def get_diff_colors(dark_mode):
    if dark_mode:
        return "#34d399", "#f87171"
    return "#059669", "#dc2626"
