"""
HairShield - Smart Response. Cleaner Seas.
Mobile-first Streamlit dashboard for a school science exhibition.

TWO KINDS OF DATA LIVE IN THIS APP - keep them separate:
  1. SIMULATED  : the 5 mL exhibition demo (fixed numbers, no real image analysis).
  2. REPORTED   : values taken from the research paper
                  "Employing Hair Mats as a Sustainable Approach for Oil Spill Remediation".
Nothing here is real AI. Uploaded pictures are preview-only.
"""

import base64
import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, UnidentifiedImageError

st.set_page_config(page_title="HairShield", page_icon="🌊", layout="centered")

# =============================================================================
# 1. DATA
# =============================================================================
# ---- SIMULATED exhibition demo (5 mL spill) ---------------------------------
DATA = pd.DataFrame(
    {
        "time": [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0],
        "contained": [250, 210, 160, 90, 40, 15, 2],
        "uncontained": [1000, 820, 550, 280, 110, 35, 8],
        "status": [
            "Oil spilled into the water",
            "Hair mat introduced to the spill",
            "Rapid oil soaking observed",
            "Visible clearing of the water patch",
            "Hair mat turning dark",
            "Minor oil traces remain",
            "Clear water surface achieved",
        ],
    }
)
LAST = len(DATA) - 1
CONFIDENCE = "96%"
OIL_QTY = "5 mL"
START_C = int(DATA.loc[0, "contained"])
START_U = int(DATA.loc[0, "uncontained"])

# ---- REPORTED research values (copied exactly as given - do not "correct") --
HAIR_MASS = [0.5, 1.0, 1.5, 2.0, 2.5]  # grams of hair
UPTAKE = {  # grams of oil taken up
    "Cooking oil": [5.6, 6.4, 7.55, 8.7, 19.5],
    "Petrol": [0.9, 1.8, 2.5, 3.2, 5.9],
    "Diesel": [2.7, 3.5, 6.0, 8.5, 9.7],
}
OIL_ORDER = ["Cooking oil", "Petrol", "Diesel"]
STYLE = {  # colour + marker + dash so series differ even without colour vision
    "Cooking oil": dict(color="#ffd166", symbol="circle", dash="solid"),
    "Petrol": dict(color="#ff8a8a", symbol="square", dash="dash"),
    "Diesel": dict(color="#7fe7ff", symbol="diamond", dash="dot"),
}
# Experiment 2 (boom): the paper's chart axis reads "Volume of Liquid (in g.)"
LIQUID_UNIT = "grams (g), as written on the paper's axis even though it says “volume”"
LIQUID_INITIAL = 150
LIQUID_REMAINING = {"Cooking oil": 88.8, "Petrol": 127.5, "Diesel": 115.2}
BOOM_INITIAL_G = 20
BOOM_FINAL_G = {"Cooking oil": 128.3, "Petrol": 102.8, "Diesel": 114.7}
# Experiment 3: boom mass (g) after each contact time
BOOM_TIME_MIN = [1, 2, 5, 7, 10]
BOOM_MASS_TIME = {
    "Cooking oil": [35.7, 51.4, 83.6, 105.3, 128.3],
    "Petrol": [33.6, 47.2, 72.0, 89.4, 102.8],
    "Diesel": [34.9, 49.8, 78.7, 98.2, 114.7],
}

# =============================================================================
# 2. SESSION STATE + CALLBACKS
# =============================================================================
for _k, _v in {"stage": 0, "idx": 0, "img_raw": None}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


def notify(msg: str):
    try:
        st.toast(msg)
    except Exception:  # very old Streamlit versions have no toast
        pass


def deploy_boom():
    st.session_state.stage = 1
    notify("✅ Hair boom deployed (simulated)")


def deploy_mat():
    st.session_state.stage = 2
    notify("✅ Hair mat deployed (simulated)")


def start_verification():
    st.session_state.stage = 3
    st.session_state.idx = 0
    notify("⏳ Verification started (simulated)")


def advance():
    st.session_state.idx = min(LAST, st.session_state.idx + 1)


def skip_to_final():
    st.session_state.stage = 3
    st.session_state.idx = LAST


def reset_demo():
    st.session_state.stage = 0
    st.session_state.idx = 0
    notify("↺ Demo reset")


# =============================================================================
# 3. STYLING
# =============================================================================
CSS = """
#MainMenu, footer {visibility: hidden;}
.stApp {background: radial-gradient(circle at 50% 0%, #0f3a66 0%, #071a33 45%, #040d1c 100%);
    color:#eaf6ff; font-family:'Segoe UI','Helvetica Neue',Arial,sans-serif;}
.block-container {max-width: 620px; padding: 1rem 1rem 3rem 1rem;}
.stApp [data-testid="stMarkdownContainer"] p, .stApp li {color:#eaf6ff;}

/* header: plain solid colours (no gradient-clipped text, which can render invisible) */
.hs-header {display:flex; align-items:center; gap:12px; padding:12px 14px; border-radius:16px;
    background:#0a2447; border:1px solid #2ea8ff; box-shadow:0 0 18px rgba(46,168,255,.3);}
.hs-header img {width:46px; height:46px; flex:0 0 46px;}
.hs-name {font-size:1.7rem; font-weight:800; color:#ffffff; line-height:1.05; letter-spacing:.5px;}
.hs-tag {font-size:.85rem; color:#9fe3ff; margin-top:2px;}
.hs-status {text-align:center; font-size:.7rem; letter-spacing:1.5px; color:#5dffb0;
    border:1px solid rgba(93,255,176,.5); border-radius:999px; padding:6px 10px;
    background:rgba(93,255,176,.08); width:fit-content; margin:10px auto 6px auto;}

.hs-section {font-size:.78rem; letter-spacing:2px; color:#7fe7ff; margin:22px 0 8px 0; font-weight:700;}
.hs-card {background:linear-gradient(160deg, rgba(20,70,120,.55), rgba(8,28,58,.9));
    border:1px solid rgba(80,200,255,.40); border-radius:16px; padding:14px;
    box-shadow:0 0 18px rgba(46,168,255,.15);}
.hs-card-head {display:flex; justify-content:space-between; align-items:center; gap:8px;
    flex-wrap:wrap; margin-bottom:10px;}
.hs-card-title {font-weight:800; letter-spacing:1.2px; font-size:.95rem; color:#fff;}
.badge {font-size:.6rem; letter-spacing:1.2px; font-weight:700; padding:3px 8px; border-radius:999px;
    border:1px solid; white-space:nowrap; display:inline-block;}
.b-sim {color:#ffd166; border-color:#ffd166; background:rgba(255,209,102,.1);}
.b-rep {color:#7fe7ff; border-color:#7fe7ff; background:rgba(127,231,255,.1);}
.b-calc {color:#c9b6ff; border-color:#c9b6ff; background:rgba(201,182,255,.1);}
.b-qual {color:#ff9f6b; border-color:#ff9f6b; background:rgba(255,159,107,.1);}
.hs-img {width:100%; border-radius:12px; border:1px solid rgba(80,200,255,.5); display:block;
    max-height:260px; object-fit:cover;}
.hs-placeholder {border:2px dashed rgba(80,200,255,.5); border-radius:12px; padding:30px 10px;
    text-align:center; color:#b9e3f7; letter-spacing:1.2px; font-size:.8rem; background:rgba(8,28,58,.5);}
.hs-chips {display:flex; gap:6px; flex-wrap:wrap; margin:10px 0;}
.chip {font-size:.7rem; font-weight:700; letter-spacing:.8px; padding:6px 10px; border-radius:999px; border:1px solid;}
.chip-cyan {color:#7fe7ff; border-color:#7fe7ff; background:rgba(127,231,255,.10);}
.chip-red {color:#ff8a8a; border-color:#ff8a8a; background:rgba(255,107,107,.12);}
.chip-green {color:#5dffb0; border-color:#5dffb0; background:rgba(93,255,176,.12);}
.chip-yellow {color:#ffd166; border-color:#ffd166; background:rgba(255,209,102,.12);}
.chip-grey {color:#9db4c9; border-color:#4b6580; background:rgba(75,101,128,.15);}
.hs-grid {display:grid; grid-template-columns:1fr 1fr; gap:8px;}
.metric {background:rgba(5,20,42,.75); border:1px solid rgba(80,200,255,.28); border-radius:12px; padding:9px 10px;}
.metric .lbl {font-size:.58rem; letter-spacing:1px; color:#9fcbe8;}
.metric .val {font-size:1.3rem; font-weight:800; color:#fff; line-height:1.25;}
.metric .sub {font-size:.6rem; color:#8fb3cf;}
.metric.red .val {color:#ff8a8a;} .metric.green .val {color:#5dffb0;} .metric.cyan .val {color:#7fe7ff;}
.reco {margin-top:10px; border:1px solid rgba(255,209,102,.5); border-radius:12px;
    background:rgba(255,209,102,.07); padding:9px 12px;}
.reco .lbl {font-size:.58rem; letter-spacing:1.3px; color:#ffd166;}
.reco .txt {font-weight:700; color:#fff; font-size:.9rem;}
.steps {display:flex; gap:5px; margin:2px 0 10px 0;}
.step {flex:1; text-align:center; font-size:.58rem; letter-spacing:.5px; padding:7px 1px; border-radius:9px;
    border:1px solid #35516e; color:#8aa7c2; background:rgba(5,20,42,.6);}
.step.done {color:#5dffb0; border-color:#5dffb0;}
.step.now {color:#7fe7ff; border-color:#7fe7ff; box-shadow:0 0 10px rgba(127,231,255,.35);}
.explain {color:#d5ecf9; font-size:.88rem; margin-top:10px; line-height:1.45;}
.pbar {height:12px; border-radius:999px; background:rgba(5,20,42,.9); border:1px solid rgba(80,200,255,.35);
    overflow:hidden; margin-top:6px;}
.pbar > div {height:100%; background:linear-gradient(90deg,#2ea8ff,#5dffb0); border-radius:999px;}
.plabel {display:flex; justify-content:space-between; font-size:.7rem; color:#b9e3f7; letter-spacing:.8px;}
.note {font-size:.72rem; color:#9fbdd6; margin-top:8px; line-height:1.45;}
.cap {font-size:.8rem; color:#d5ecf9; line-height:1.5; margin-top:6px;}
.cap b {color:#7fe7ff;}

/* compact timeline */
.tl {display:flex; align-items:stretch; gap:10px; padding:8px 10px; margin-bottom:6px; border-radius:12px;
    background:rgba(5,20,42,.7); border:1px solid rgba(80,200,255,.2);}
.tl .t {flex:0 0 52px; font-weight:800; color:#fff; font-size:.85rem; align-self:center;}
.tl .b {flex:1; min-width:0;}
.tl .v {display:flex; flex-wrap:wrap; gap:4px 12px; font-size:.78rem;}
.tl .v .g {color:#5dffb0;} .tl .v .r {color:#ff8a8a;}
.tl .s {font-size:.75rem; color:#c5deee; margin-top:2px;}
.tl .d {flex:0 0 12px; width:12px; height:12px; border-radius:50%; align-self:center; background:#4b6580;}
.tl.done .d {background:#5dffb0;} .tl.now {border-color:#7fe7ff; background:rgba(46,168,255,.22);}
.tl.now .d {background:#7fe7ff; box-shadow:0 0 8px #7fe7ff;} .tl.pending {opacity:.55;}

.final {text-align:center; padding:18px 12px; border-radius:16px;}
.final.ok {border:1px solid #5dffb0; background:linear-gradient(160deg, rgba(20,110,80,.45), rgba(8,40,40,.9));
    box-shadow:0 0 22px rgba(93,255,176,.3);}
.final.wait {border:1px dashed #4b6580; background:rgba(5,20,42,.6); color:#9db4c9; font-size:.85rem;}
.final .big {font-size:1.05rem; font-weight:800; letter-spacing:1px; color:#5dffb0;}
.final .small {font-size:.8rem; color:#d5ecf9; margin-top:6px;}

/* research helpers */
.tbl {width:100%; border-collapse:collapse; font-size:.78rem; margin-top:6px;}
.tbl th {color:#7fe7ff; font-size:.62rem; letter-spacing:.8px; text-align:left; padding:5px 4px;
    border-bottom:1px solid rgba(80,200,255,.4);}
.tbl td {padding:5px 4px; border-bottom:1px solid rgba(80,200,255,.12); color:#e4f3fb;}
.phases {display:flex; gap:6px; align-items:center; margin:8px 0;}
.phase {flex:1; text-align:center; font-size:.72rem; padding:10px 4px; border-radius:10px;
    border:1px dashed #ff9f6b; color:#ffd2b8; background:rgba(255,159,107,.07);}
.arrow {color:#ff9f6b; font-weight:800;}

/* buttons */
.stButton > button {width:100%; min-height:3.3rem; border-radius:12px; font-weight:700; letter-spacing:2px;
    font-size:.8rem; text-transform:uppercase; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    box-shadow:none;}
.stButton > button p, .stButton > button span {color:inherit !important; font-size:.8rem; letter-spacing:2px;}
.stButton > button[kind="primary"], .stButton > button[data-testid="stBaseButton-primary"] {
    color:#7fe7ff; background:#0d3a4a; border:1px solid #2fb4c9;}
.stButton > button[kind="secondary"], .stButton > button[data-testid="stBaseButton-secondary"] {
    color:#cfe3f3; background:rgba(8,20,40,.6); border:1px solid #2b4a6b;}
.stButton > button:hover {filter:brightness(1.2); border-color:#7fe7ff; color:#fff;}
.stButton > button:disabled {color:#7e9bb8; background:#13243a; border-color:#35516e; filter:none;}

/* response simulator (section 02) */
.sim-top {display:flex; justify-content:space-between; align-items:flex-start; gap:10px; flex-wrap:wrap;
    margin:26px 0 12px 0;}
.sim-eyebrow {font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.68rem;
    letter-spacing:3px; color:#8fa9c3;}
.sim-h {font-size:1.55rem; font-weight:800; color:#fff; letter-spacing:-.4px; line-height:1.15; margin-top:6px;}
.sim-sub {font-size:.88rem; color:#a9bfd4; margin-top:4px;}
.sim-badge {font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:.66rem;
    letter-spacing:2px; font-weight:700; color:#ffd166; border:1px solid #7a5d2a; background:#2b2414;
    border-radius:8px; padding:8px 10px; white-space:nowrap;}
.st-key-sim_panel {background:#0e1f3a; border:1px solid #1f4268; border-radius:20px; padding:16px;
    box-shadow:0 0 22px rgba(30,100,170,.15);}
.sim-scn {display:inline-block; font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    font-size:.7rem; letter-spacing:1.5px; color:#7fe7ff; border:1px solid #2a6a86; border-radius:8px;
    padding:7px 10px; background:rgba(127,231,255,.05);}
.sim-title {font-size:1.45rem; font-weight:800; color:#fff; letter-spacing:-.4px; margin:14px 0 6px 0;
    line-height:1.2;}
.sim-body {font-size:.92rem; color:#a9bfd4; line-height:1.5; margin-bottom:12px;}
.sim-vis {position:relative; border-radius:16px; overflow:hidden; border:1px solid #2b5d8f;}
.sim-vis img {width:100%; display:block;}
.sim-vlabel {position:absolute; left:12px; bottom:9px; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    font-size:.6rem; letter-spacing:2px; color:#a9c8e3;}
.sim-steps {position:relative; display:flex; margin:20px 0 14px 0;}
.sim-line {position:absolute; top:17px; left:12.5%; right:12.5%; height:1px; background:#24476b;}
.sim-step {flex:1; text-align:center; position:relative; z-index:1; min-width:0;}
.sim-c {width:34px; height:34px; border-radius:50%; border:1px solid #2b4a6b; background:#0e1f3a;
    margin:0 auto; display:flex; align-items:center; justify-content:center; color:#7d97b3;
    font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.78rem;}
.sim-step.done .sim-c {border-color:#2a8a9c; color:#7fe7ff;}
.sim-step.now .sim-c {border-color:#59d3e6; color:#7fe7ff; background:#12384a;
    box-shadow:0 0 0 3px rgba(89,211,230,.18);}
.sim-n {font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.62rem; letter-spacing:1.6px;
    color:#8aa4be; margin-top:8px;}
.sim-step.now .sim-n {color:#fff;}
.sim-d {font-size:.68rem; color:#8fa9c3; margin-top:2px; line-height:1.25;}
.sim-rule {height:1px; background:#1f4268; margin:12px 0;}
.sim-curl {font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.72rem; letter-spacing:3px;
    color:#8fa9c3;}
.sim-curn {font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.8rem; letter-spacing:2px;
    color:#7fe7ff; font-weight:800; margin-left:14px;}
.sim-stat {font-size:.9rem; color:#cfe3f3; margin:6px 0 12px 0; line-height:1.45;}
.sim-foot {font-size:.74rem; color:#9fb5ca; line-height:1.5;}

[data-testid="stFileUploader"] section {background:rgba(8,28,58,.7); border:1px dashed rgba(80,200,255,.6);
    border-radius:14px;}
[data-testid="stFileUploader"] label, [data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span {color:#d5ecf9 !important;}
[data-testid="stExpander"] {border:1px solid rgba(80,200,255,.35); border-radius:14px;
    background:rgba(8,28,58,.55);}
[data-testid="stExpander"] summary p {font-weight:700; color:#fff; font-size:.92rem;}

@media (max-width: 480px) {
    .block-container {padding-left:.6rem; padding-right:.6rem;}
    .hs-name {font-size:1.45rem;} .hs-grid .metric .val {font-size:1.15rem;}
}
"""
st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)


# =============================================================================
# 4. HELPERS
# =============================================================================
def html(s: str):
    """Render HTML; strip leading spaces so Markdown does not treat it as a code block."""
    st.markdown(" ".join(line.strip() for line in s.strip().splitlines()), unsafe_allow_html=True)


def fmt(v) -> str:
    return f"{int(v):,} cm²"


def tmin(t) -> str:
    return f"{t:g} min"


def image_to_data_uri(raw: bytes) -> str:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    img.thumbnail((800, 800))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


# Self-contained logo: an inline SVG encoded into the page (no file / URL needed)
LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#7fe7ff"/><stop offset="1" stop-color="#1b78d0"/></linearGradient></defs>'
    '<path d="M32 4 L56 13 V32 C56 46 46 56 32 60 C18 56 8 46 8 32 V13 Z" fill="#0b2a52" '
    'stroke="url(#g)" stroke-width="3"/>'
    '<path d="M32 16 C24 27 22 32 22 36 a10 10 0 0 0 20 0 C42 32 40 27 32 16 Z" fill="url(#g)"/>'
    '<path d="M18 46 q7 -6 14 0 t14 0" fill="none" stroke="#ffffff" stroke-width="2.5" '
    'stroke-linecap="round"/></svg>'
)
LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(LOGO_SVG.encode()).decode()

# Charts: no zoom, no pan, no toolbar. Tooltips still work on tap/hover.
PLOT_CONFIG = {"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "showTips": False}


def style_fig(fig, title, xtitle, ytitle, height=320):
    fig.update_layout(
        title=dict(text=title, font=dict(size=13, color="#eaf6ff"), x=0.02, y=0.97, yanchor="top"),
        paper_bgcolor="#071a33", plot_bgcolor="#0a2447",
        font=dict(color="#d5ecf9", size=11), height=height,
        margin=dict(l=6, r=6, t=82, b=6), dragmode=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=10)),
        hoverlabel=dict(font_size=12),
    )
    fig.update_xaxes(title=xtitle, fixedrange=True, gridcolor="#143a66", zeroline=False, automargin=True)
    fig.update_yaxes(title=ytitle, fixedrange=True, gridcolor="#143a66", zeroline=False, automargin=True)
    return fig


def show(fig, key):
    try:
        st.plotly_chart(fig, use_container_width=True, config=PLOT_CONFIG, key=key)
    except Exception:  # newer Streamlit versions replaced this argument
        st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG, key=key)


# =============================================================================
# 5. HEADER
# =============================================================================
html(f"""<div class="hs-header"><img src="{LOGO_URI}" alt="HairShield logo"/>
    <div><div class="hs-name">HairShield</div>
    <div class="hs-tag">Smart Response. Cleaner Seas.</div></div></div>
    <div class="hs-status">● OCEAN MONITORING SYSTEM ONLINE</div>""")

# =============================================================================
# 6. IMAGE UPLOAD
# =============================================================================
html('<div class="hs-section">📡 IMAGE UPLOAD</div>')
uploaded = st.file_uploader("Upload oil spill image", type=["jpg", "jpeg", "png"],
                            label_visibility="collapsed")
if uploaded is not None:
    try:
        raw = uploaded.getvalue()
        Image.open(io.BytesIO(raw)).verify()
        if raw != st.session_state.img_raw:
            st.session_state.img_raw = raw
            st.session_state.stage = 0
            st.session_state.idx = 0
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        st.error("⚠️ That file could not be read as an image. Please upload a JPG or PNG.")

has_image = st.session_state.img_raw is not None
stage = st.session_state.stage
idx = st.session_state.idx
complete = stage == 3 and idx == LAST

if stage == 3:
    cur_c, cur_u = int(DATA.loc[idx, "contained"]), int(DATA.loc[idx, "uncontained"])
else:
    cur_c, cur_u = START_C, START_U

# =============================================================================
# 7. ANALYSIS CARD (fixed, simulated result)
# =============================================================================
html('<div class="hs-section">🧠 ANALYSIS</div>')
if has_image:
    try:
        img_html = f'<img class="hs-img" alt="Uploaded preview" src="{image_to_data_uri(st.session_state.img_raw)}"/>'
    except Exception:
        img_html = '<div class="hs-placeholder">IMAGE PREVIEW UNAVAILABLE</div>'
    chips = """<div class="hs-chips"><span class="chip chip-cyan">✔ IMAGE RECEIVED</span>
        <span class="chip chip-red">⚠ OIL SPILL DETECTED</span>
        <span class="chip chip-yellow">SIMULATED DETECTION</span></div>"""
    cls = "green" if complete else "red"
    note = "simulated · current" if stage == 3 else "simulated · initial"
    metrics = f"""<div class="hs-grid">
        <div class="metric cyan"><div class="lbl">DEMO CONFIDENCE</div><div class="val">{CONFIDENCE}</div>
            <div class="sub">fixed demo value</div></div>
        <div class="metric cyan"><div class="lbl">SIMULATED OIL QUANTITY</div><div class="val">{OIL_QTY}</div>
            <div class="sub">demo value</div></div>
        <div class="metric {cls}"><div class="lbl">AREA · CONTAINED</div><div class="val">{fmt(cur_c)}</div>
            <div class="sub">{note}</div></div>
        <div class="metric {cls}"><div class="lbl">AREA · UNCONTAINED</div><div class="val">{fmt(cur_u)}</div>
            <div class="sub">{note}</div></div></div>
        <div class="reco"><div class="lbl">RECOMMENDED RESPONSE</div>
        <div class="txt">Deploy hair booms, followed by hair mesh mats.</div></div>"""
else:
    img_html = '<div class="hs-placeholder">UPLOAD OIL SPILL IMAGE TO BEGIN ANALYSIS</div>'
    chips = '<div class="hs-chips"><span class="chip chip-grey">AWAITING IMAGE</span></div>'
    metrics = ""

html(f"""<div class="hs-card"><div class="hs-card-head">
    <span class="hs-card-title">AI OIL SPILL ANALYSIS</span>
    <span class="badge b-sim">SIMULATION MODE · DEMO DATA</span></div>
    {img_html}{chips}{metrics}
    <div class="note">The picture is only a preview. No AI or image measurement is performed — every
    image gives the same pre-set demo result.</div></div>""")

# =============================================================================
# 8. HAIRSHIELD RESPONSE SIMULATOR  (recreated from the Hatchable "section 02")
#    stage numbers used internally: 0 = DETECT, 1 = CONTAIN, 2 = ABSORB, 3 = VERIFY
# =============================================================================
STAGES = [
    dict(name="DETECT", sub="Identify spill", title="Oil spill scenario detected",
         body="Start the demo to see how a hair boom can help contain surface spread.",
         status="A possible spill is identified in this simulated scenario."),
    dict(name="CONTAIN", sub="Deploy hair boom", title="Hair boom deployed",
         body="The boom forms a floating barrier around the spill to help stop it spreading across the surface.",
         status="A hair boom is placed around the spill in this simulated scenario."),
    dict(name="ABSORB", sub="Use hair mat", title="Hair mat absorbing",
         body="A hair mesh mat is placed inside the boom to soak up the remaining floating oil.",
         status="A hair mat is absorbing oil in this simulated scenario."),
    dict(name="VERIFY", sub="Review outcome", title="Reviewing outcome",
         body="Step through the simulated readings to watch the spill area shrink over time.",
         status=""),
]


def water_svg(stage_no: int, area_ratio: float, done: bool) -> str:
    """Self-contained 'model water surface' picture (SVG), drawn for the current stage."""
    scale = max(area_ratio, 0.0) ** 0.5 if stage_no == 3 else 1.0
    scale = max(scale, 0.07)
    rx, ry = 46 * scale, 27 * scale
    ring = "#5dffb0" if done else "#7fe7ff"
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 220">',
        '<defs>'
        '<linearGradient id="w" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1d5688"/>'
        '<stop offset="1" stop-color="#0a2547"/></linearGradient>'
        '<radialGradient id="gl" cx="50%" cy="45%" r="55%"><stop offset="0" stop-color="#4f9be0" stop-opacity=".45"/>'
        '<stop offset="1" stop-color="#4f9be0" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="oil" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#151a22"/>'
        '<stop offset=".6" stop-color="#27292b"/><stop offset="1" stop-color="#9a7f4b"/></radialGradient>'
        '<pattern id="mesh" width="8" height="8" patternUnits="userSpaceOnUse">'
        '<path d="M0 0L8 8M8 0L0 8" stroke="#ffffff" stroke-opacity=".22" stroke-width="1"/></pattern>'
        '</defs>',
        '<rect width="400" height="220" fill="url(#w)"/><rect width="400" height="220" fill="url(#gl)"/>',
        '<line x1="0" y1="72" x2="400" y2="132" stroke="#8fc3ee" stroke-opacity=".25"/>',
        '<line x1="0" y1="160" x2="400" y2="22" stroke="#8fc3ee" stroke-opacity=".25"/>',
    ]
    if stage_no >= 1:  # boom: floating barrier around the spill
        parts.append('<ellipse cx="200" cy="110" rx="74" ry="46" fill="#7fe7ff" fill-opacity=".07"/>')
    parts.append(f'<ellipse cx="200" cy="110" rx="{rx + 6:.1f}" ry="{ry + 6:.1f}" fill="#9a7f4b" fill-opacity=".25"/>')
    parts.append(f'<ellipse cx="200" cy="110" rx="{rx:.1f}" ry="{ry:.1f}" fill="url(#oil)"/>')
    if stage_no >= 2:  # hair mesh mat
        parts.append('<ellipse cx="200" cy="110" rx="56" ry="34" fill="#8a6038" fill-opacity=".45" '
                     'stroke="#c79a62" stroke-width="2"/>'
                     '<ellipse cx="200" cy="110" rx="56" ry="34" fill="url(#mesh)"/>')
    if stage_no >= 1:
        parts.append(f'<ellipse cx="200" cy="110" rx="74" ry="46" fill="none" stroke="{ring}" '
                     'stroke-width="4" stroke-dasharray="10 5"/>')
    parts.append("</svg>")
    return "".join(parts)


sim_ratio = (cur_c / START_C) if stage == 3 else 1.0
sim_uri = "data:image/svg+xml;base64," + base64.b64encode(
    water_svg(stage, sim_ratio, complete).encode()).decode()

cur = STAGES[stage]
if stage == 3:
    if complete:
        cur = dict(cur, title="Spill controlled — cleanup successful",
                   body=f"Simulated outcome: the demo spill area falls from {fmt(START_C)} to "
                        f"{fmt(DATA.loc[LAST, 'contained'])} with the boom and mat.",
                   status="Simulated outcome only — not a real-world measurement.")
    else:
        cur = dict(cur, status=f"Simulated reading {idx + 1} of {len(DATA)} at "
                               f"{tmin(DATA.loc[idx, 'time'])}: {DATA.loc[idx, 'status']}.")

steps_html = ""
for i, stg in enumerate(STAGES):
    cl = "now" if i == stage else ("done" if i < stage or complete else "")
    steps_html += (f'<div class="sim-step {cl}"><div class="sim-c">{i + 1:02d}</div>'
                   f'<div class="sim-n">{stg["name"]}</div><div class="sim-d">{stg["sub"]}</div></div>')

# header (sits above the card, like the original)
html("""<div class="sim-top"><div><div class="sim-eyebrow">02 / EXHIBITION DEMONSTRATION</div>
    <div class="sim-h">HairShield Response Simulator</div>
    <div class="sim-sub">Step through the proposed cleanup method for your physical model.</div></div>
    <span class="sim-badge">SIMULATION ONLY</span></div>""")

try:
    panel = st.container(key="sim_panel")
except TypeError:  # older Streamlit without container keys
    panel = st.container()

with panel:
    html(f"""<span class="sim-scn">SCENARIO HS-005</span>
        <div class="sim-title">{cur['title']}</div>
        <div class="sim-body">{cur['body']}</div>
        <div class="sim-vis"><img src="{sim_uri}" alt="Model water surface (simulation)"/>
        <span class="sim-vlabel">MODEL WATER SURFACE</span></div>
        <div class="sim-steps"><div class="sim-line"></div>{steps_html}</div>
        <div class="sim-rule"></div>
        <div><span class="sim-curl">CURRENT STAGE</span><span class="sim-curn">{stage + 1:02d} / 04</span></div>
        <div class="sim-stat">{cur['status']}</div>""")

    b1, b2 = st.columns([2, 1])
    with b1:
        if stage == 0:
            st.button("DEPLOY HAIR BOOM", type="primary", on_click=deploy_boom, key="b_boom")
        elif stage == 1:
            st.button("DEPLOY HAIR MAT", type="primary", on_click=deploy_mat, key="b_mat")
        elif stage == 2:
            st.button("REVIEW OUTCOME", type="primary", on_click=start_verification, key="b_verify")
        elif not complete:
            st.button("NEXT READING ▶", type="primary", on_click=advance, key="b_next")
            st.button("SKIP TO FINAL ⏭", on_click=skip_to_final, key="b_skip")
        else:
            st.button("DEMO COMPLETE ✔", type="primary", disabled=True, key="b_done")
    with b2:
        st.button("↺ RESET", on_click=reset_demo, key="b_reset")

    html("""<div class="sim-rule"></div><div class="sim-foot">This is an interactive school-project simulation.
        It does not deploy equipment, measure real water, or verify real-world cleanup.</div>""")

# =============================================================================
# 9. CLEANUP MONITORING (simulated)
# =============================================================================
html('<div class="hs-section">📉 CLEANUP MONITORING</div>')
pct = round((START_C - cur_c) / START_C * 100) if stage == 3 else 0
html(f"""<div class="hs-card"><div class="hs-card-head"><span class="hs-card-title">PROGRESS</span>
    <span class="badge b-sim">SIMULATED DEMONSTRATION</span></div>
    <div class="plabel"><span>CLEANUP PROGRESS (MOCK)</span><span>{pct}%</span></div>
    <div class="pbar"><div style="width:{pct}%"></div></div></div>""")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=DATA["time"], y=DATA["contained"], name="Contained boom", mode="lines+markers",
    line=dict(color="#5dffb0", width=3), marker=dict(size=7, symbol="circle"),
    hovertemplate="Contained: %{y} cm²<extra></extra>"))
fig.add_trace(go.Scatter(
    x=DATA["time"], y=DATA["uncontained"], name="Uncontained spread", mode="lines+markers",
    line=dict(color="#ff8a8a", width=3, dash="dash"), marker=dict(size=7, symbol="square"),
    hovertemplate="Uncontained: %{y} cm²<extra></extra>"))
if stage == 3:
    t = DATA.loc[idx, "time"]
    fig.add_trace(go.Scatter(
        x=[t, t], y=[DATA.loc[idx, "contained"], DATA.loc[idx, "uncontained"]], mode="markers",
        showlegend=False, hoverinfo="skip",
        marker=dict(size=15, color="rgba(0,0,0,0)", line=dict(color="#ffffff", width=3))))
style_fig(fig, "Simulated spill area during cleanup", "Elapsed time (min)", "Spill area (cm²)", height=320)
fig.update_layout(hovermode="x unified")
show(fig, "sim_chart")
html("""<div class="cap"><b>Simulated demonstration.</b> These numbers are fixed demo values for a 5 mL spill,
    used to show how the exhibition model behaves. They are <b>not</b> real-world measured performance and
    do not prove real oil-spill cleanup effectiveness.</div>""")

html('<div class="hs-section" style="margin-top:14px">🕒 TIMELINE</div>')
rows = ""
for i, r in DATA.iterrows():
    if stage == 3:
        cl = "now" if (i == idx and not complete) else ("done" if i <= idx else "pending")
    else:
        cl = ""
    rows += (f'<div class="tl {cl}"><div class="t">{tmin(r["time"])}</div><div class="b"><div class="v">'
             f'<span class="g">Contained {fmt(r["contained"])}</span>'
             f'<span class="r">Uncontained {fmt(r["uncontained"])}</span></div>'
             f'<div class="s">{r["status"]}</div></div><div class="d"></div></div>')
html(rows)
html('<div class="note">Simulated timeline · mock cleanup data. Dot colour: grey = waiting, '
     'cyan = current reading, green = reached.</div>')

html('<div class="hs-section">🏁 FINAL RESULT</div>')
if complete:
    rc = round((1 - DATA.loc[LAST, "contained"] / START_C) * 100, 1)
    ru = round((1 - DATA.loc[LAST, "uncontained"] / START_U) * 100, 1)
    html(f"""<div class="final ok"><div class="big">✔ SPILL CONTROLLED — CLEANUP SUCCESSFUL</div>
        <div class="small">Contained: {fmt(START_C)} → {fmt(DATA.loc[LAST, 'contained'])} ({rc}% smaller)<br>
        Uncontained: {fmt(START_U)} → {fmt(DATA.loc[LAST, 'uncontained'])} ({ru}% smaller)</div>
        <div class="note">Simulated demo result — not a measured outcome.</div></div>""")
else:
    html('<div class="final wait">FINAL RESULT PENDING — complete the stages above.</div>')

# =============================================================================
# 10. RESEARCH & EXPERIMENTAL RESULTS (numbers read from the charts inside the paper)
# =============================================================================
html('<div class="hs-section" style="margin-top:30px">🔬 RESEARCH &amp; EXPERIMENTAL RESULTS</div>')
html("""<div class="hs-card"><div class="hs-card-head"><span class="hs-card-title">ABOUT THIS SECTION</span>
    <span class="badge b-rep">REPORTED DATA</span></div>
    <div class="cap">Values below are the numbers behind the charts in the research document <i>“Employing Hair Mats
    as a Sustainable Approach for Oil Spill Remediation”</i> (M. K. Dhaliwal). They are separate from the simulated
    5 mL exhibition demo above and have not been independently verified by this project.</div>
    <div class="hs-chips"><span class="badge b-rep">REPORTED</span><span class="badge b-calc">CALCULATED</span>
    <span class="badge b-sim">SIMULATED</span></div>
    <div class="note">Tap a heading below to open it. Charts are fixed: no zoom or pan.</div></div>""")

# ---- Set-up --------------------------------------------------------------------
with st.expander("Experimental set-up (from the paper)", expanded=False):
    html('<span class="badge b-rep">REPORTED</span>')
    html("""<table class="tbl"><tr><th></th><th>EXP. 1</th><th>EXP. 2</th><th>EXP. 3</th></tr>
        <tr><td>Water</td><td>100 mL</td><td>100 mL</td><td>100 mL</td></tr>
        <tr><td>Oil</td><td>20 mL</td><td>50 mL</td><td>50 mL</td></tr>
        <tr><td>Hair</td><td>0.5–2.5 g</td><td>20 g boom</td><td>20 g boom</td></tr>
        <tr><td>Time</td><td>10 min</td><td>10 min</td><td>1, 2, 5, 7, 10 min</td></tr></table>
        <div class="cap">Oils tested: cooking oil, petrol (called “petroleum” in the method) and diesel. The scale
        precision is ±0.1 g. No stirring.<br>
        <b>How “oil absorbed” is worked out:</b> final hair mass minus initial hair mass. This is a weight change, so
        it cannot tell oil apart from any water or liquid held on the hair. The paper also gives a formula for
        absorption efficiency (%), but reports no efficiency values, so none are charted here.</div>""")

# ---- Chart A -------------------------------------------------------------------
with st.expander("A · Hair mass vs. oil uptake (Experiment 1)", expanded=False):
    html('<span class="badge b-rep">REPORTED</span>')
    fa = go.Figure()
    for oil in OIL_ORDER:
        s = STYLE[oil]
        fa.add_trace(go.Scatter(
            x=HAIR_MASS, y=UPTAKE[oil], name=oil, mode="lines+markers",
            line=dict(color=s["color"], width=3, dash=s["dash"]),
            marker=dict(size=8, symbol=s["symbol"], color=s["color"]),
            hovertemplate=f"{oil}: " + "%{y} g<extra></extra>"))
    style_fig(fa, "Oil uptake by hair mass", "Hair mass (g)", "Oil absorbed (g)", height=330)
    fa.update_xaxes(tickvals=HAIR_MASS)
    fa.update_layout(hovermode="x unified")
    show(fa, "chart_a")
    html("""<div class="cap"><b>What it shows:</b> reported uptake rises with hair mass for all three oils, and is
        highest for cooking oil, then diesel, then petrol. The paper notes a pronounced increase at 2.5 g for every
        oil and suggests a non-linear relationship beyond some threshold.<br>
        <b>What it cannot show:</b> where any threshold lies (only five masses, no repeats or error bars given), or
        how this scales to real spills at sea.<br>
        <b>Check:</b> 20 mL of cooking oil weighs roughly 18 g (assuming a typical density near 0.9 g/mL), yet 19.5 g
        was reported at 2.5 g of hair. Because uptake is a mass change, it may include retained water. The value is
        kept exactly as reported.</div>""")

# ---- Chart B -------------------------------------------------------------------
with st.expander("B · Compare oil types at each hair mass", expanded=False):
    html('<span class="badge b-rep">REPORTED</span> <span class="badge b-calc">HIGHEST = CALCULATED</span>')
    labels = [f"{m:g} g" for m in HAIR_MASS]
    winners = []
    for j in range(len(HAIR_MASS)):
        vals = {o: UPTAKE[o][j] for o in OIL_ORDER}
        winners.append(max(vals, key=vals.get))
    fb = go.Figure()
    for oil in OIL_ORDER:
        widths = [3 if winners[j] == oil else 0 for j in range(len(HAIR_MASS))]
        fb.add_trace(go.Bar(
            x=labels, y=UPTAKE[oil], name=oil, marker_color=STYLE[oil]["color"],
            marker_line=dict(color="#ffffff", width=widths),
            text=[f"{v:g}" for v in UPTAKE[oil]], textposition="outside", cliponaxis=False,
            textfont=dict(size=9), hovertemplate=f"{oil}: " + "%{y} g<extra></extra>"))
    style_fig(fb, "Oil uptake by oil type (white outline = highest)", "Hair mass", "Oil absorbed (g)", height=340)
    fb.update_layout(barmode="group", bargap=0.2, bargroupgap=0.05)
    fb.update_yaxes(range=[0, 22.5])
    show(fb, "chart_b")
    trs = "".join(f"<tr><td>{HAIR_MASS[j]:g} g</td><td>{winners[j]}</td>"
                  f"<td>{max(UPTAKE[o][j] for o in OIL_ORDER):g} g</td></tr>" for j in range(len(HAIR_MASS)))
    html(f"""<table class="tbl"><tr><th>HAIR MASS</th><th>HIGHEST UPTAKE</th><th>VALUE</th></tr>{trs}</table>
        <div class="cap"><b>What it shows:</b> the same reported values side by side. Cooking oil is highest at all
        five masses, consistent with the paper's ranking (cooking oil, diesel, petrol). At 2.0 g, diesel (8.5 g) is
        close to cooking oil (8.7 g).<br>
        <b>What it cannot show:</b> whether differences are statistically meaningful (no repeat trials given).</div>""")

# ---- Chart C -------------------------------------------------------------------
with st.expander("C · Hair-boom liquid residue (Experiment 2)", expanded=False):
    html('<span class="badge b-rep">REPORTED</span> <span class="badge b-calc">DIFFERENCE = CALCULATED</span>')
    fc = go.Figure()
    fc.add_trace(go.Bar(
        x=OIL_ORDER, y=[LIQUID_INITIAL] * 3, name="Initial", marker_color="#4b79a8",
        text=[f"{LIQUID_INITIAL}"] * 3, textposition="outside", cliponaxis=False, textfont=dict(size=10),
        hovertemplate="Initial: %{y} g<extra></extra>"))
    fc.add_trace(go.Bar(
        x=OIL_ORDER, y=[LIQUID_REMAINING[o] for o in OIL_ORDER], name="Remaining", marker_color="#7fe7ff",
        text=[f"{LIQUID_REMAINING[o]:g}" for o in OIL_ORDER], textposition="outside", cliponaxis=False,
        textfont=dict(size=10), hovertemplate="Remaining: %{y} g<extra></extra>"))
    style_fig(fc, "Liquid before and after hair boom", "Oil type", "Volume of liquid (in g)", height=330)
    fc.update_layout(barmode="group", bargap=0.25)
    fc.update_yaxes(range=[0, 175])
    show(fc, "chart_c")
    trs = "".join(f"<tr><td>{o}</td><td>{LIQUID_INITIAL}</td><td>{LIQUID_REMAINING[o]:g}</td>"
                  f"<td>{LIQUID_INITIAL - LIQUID_REMAINING[o]:.1f}</td></tr>" for o in OIL_ORDER)
    html(f"""<table class="tbl"><tr><th>OIL</th><th>INITIAL</th><th>REMAINING</th><th>DIFFERENCE (calc.)</th></tr>
        {trs}</table>
        <div class="cap"><b>What the numbers are:</b> the paper's chart is titled “Effectiveness of Hair Booms in
        Absorbing Oil Residue”, and its axis reads “Volume of Liquid (in g.)” — so the unit is {LIQUID_UNIT}.
        The starting value of 150 matches the 100 mL water + 50 mL oil of Experiment 2 (our inference), so the
        measurement appears to cover the whole oil–water liquid, not oil alone.<br>
        <b>Not established:</b> that the difference is pure oil absorption. The difference column is simple
        subtraction by this app, not a value reported in the paper.</div>""")

# ---- Chart D -------------------------------------------------------------------
with st.expander("D · Hair-boom mass before and after (Experiment 2)", expanded=False):
    html('<span class="badge b-rep">REPORTED</span> <span class="badge b-calc">GAIN = CALCULATED</span>')
    fd = go.Figure()
    fd.add_trace(go.Bar(
        x=OIL_ORDER, y=[BOOM_INITIAL_G] * 3, name="Initial", marker_color="#4b79a8",
        text=[f"{BOOM_INITIAL_G}"] * 3, textposition="outside", cliponaxis=False, textfont=dict(size=10),
        hovertemplate="Initial: %{y} g<extra></extra>"))
    fd.add_trace(go.Bar(
        x=OIL_ORDER, y=[BOOM_FINAL_G[o] for o in OIL_ORDER], name="Final", marker_color="#ffd166",
        text=[f"{BOOM_FINAL_G[o]:g}" for o in OIL_ORDER], textposition="outside", cliponaxis=False,
        textfont=dict(size=10), hovertemplate="Final: %{y} g<extra></extra>"))
    style_fig(fd, "Hair-boom mass before and after", "Oil type", "Mass of hair booms (g)", height=330)
    fd.update_layout(barmode="group", bargap=0.25)
    fd.update_yaxes(range=[0, 150])
    show(fd, "chart_d")
    trs = "".join(
        f"<tr><td>{o}</td><td>{BOOM_FINAL_G[o] - BOOM_INITIAL_G:.1f}</td>"
        f"<td>{LIQUID_INITIAL - LIQUID_REMAINING[o]:.1f}</td></tr>" for o in OIL_ORDER)
    html(f"""<div class="cap"><b>What it shows:</b> values reported in the research: the boom starts at
        {BOOM_INITIAL_G} g and ends heaviest with cooking oil, then diesel, then petrol — the same ranking as chart C.
        These are not independently verified results.</div>
        <table class="tbl"><tr><th>OIL</th><th>BOOM MASS GAIN (calc., g)</th><th>LIQUID REMOVED, CHART C (calc., g)</th></tr>
        {trs}</table>
        <div class="cap"><b>Unresolved inconsistency:</b> if both were measured in grams from the same container, the
        boom's gain and the liquid removed would be similar, but the boom gain is much larger for every oil. The paper
        does not explain this (the boom may hold more than removed oil, or the measures differ). Both are shown exactly
        as reported and have not been reconciled, so these figures alone should not be read as an absorption
        percentage.</div>""")

# ---- Chart E -------------------------------------------------------------------
with st.expander("E · Hair-boom mass over time (Experiment 3)", expanded=False):
    html('<span class="badge b-rep">REPORTED</span> <span class="badge b-calc">RATES = CALCULATED</span>')
    fe = go.Figure()
    for oil in OIL_ORDER:
        s = STYLE[oil]
        fe.add_trace(go.Scatter(
            x=BOOM_TIME_MIN, y=BOOM_MASS_TIME[oil], name=oil, mode="lines+markers",
            line=dict(color=s["color"], width=3, dash=s["dash"]),
            marker=dict(size=8, symbol=s["symbol"], color=s["color"]),
            hovertemplate=f"{oil}: " + "%{y} g<extra></extra>"))
    style_fig(fe, "Hair-boom mass with contact time", "Contact time (min)", "Mass of hair booms (g)", height=330)
    fe.update_xaxes(tickvals=BOOM_TIME_MIN)
    fe.update_layout(hovermode="x unified")
    show(fe, "chart_e")

    edges = [0] + BOOM_TIME_MIN
    heads = "".join(f"<th>{edges[k]}→{edges[k + 1]}</th>" for k in range(len(BOOM_TIME_MIN)))
    trs = ""
    for oil in OIL_ORDER:
        masses = [BOOM_INITIAL_G] + BOOM_MASS_TIME[oil]
        cells = "".join(
            f"<td>{(masses[k + 1] - masses[k]) / (edges[k + 1] - edges[k]):.1f}</td>"
            for k in range(len(BOOM_TIME_MIN)))
        trs += f"<tr><td>{oil}</td>{cells}</tr>"
    html(f"""<table class="tbl"><tr><th>g / min (calc.)</th>{heads}</tr>{trs}</table>
        <div class="cap"><b>What it shows:</b> the paper describes uptake as rapid at first, then gradually slowing as
        the boom nears saturation. The reported masses agree with the slowing: the average gain per minute (table,
        interval in minutes, first interval starts from the 20 g initial mass) is largest at the start and smallest
        in the 7→10 min interval, with a small uptick between 2→5 and 5→7 min. The 10 min values match chart D.<br>
        <b>What it cannot show:</b> that saturation was reached — the mass is still rising at 10 minutes. Readings are
        total boom mass, not pure oil, and no repeat trials are given.</div>""")

# =============================================================================
# 11. FOOTER
# =============================================================================
html("""<div class="note" style="text-align:center;margin-top:26px">HairShield · The analysis card and cleanup
    demo use fixed SIMULATED data and no real AI. Research values are as reported in the source paper and
    have not been independently verified. Real AI detection and real-world measurements may be added in a future
    version.</div>""")
