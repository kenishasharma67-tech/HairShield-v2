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
# Boom experiment. The unit of the "liquid value" is NOT stated in the information
# supplied to the developer - confirm it in the paper and edit LIQUID_UNIT below.
LIQUID_UNIT = "units as reported in the paper"
LIQUID_INITIAL = 150
LIQUID_REMAINING = {"Cooking oil": 88.8, "Petrol": 127.5, "Diesel": 115.2}
BOOM_INITIAL_G = 20
BOOM_FINAL_G = {"Cooking oil": 128.3, "Petrol": 102.8, "Diesel": 114.7}
CONTACT_TIMES_MIN = [1, 2, 5, 7, 10]

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
.stApp p, .stApp li, .stApp span, .stApp label {color:#eaf6ff;}

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

/* buttons: large tap targets */
.stButton > button {width:100%; min-height:3.4rem; border-radius:14px; font-weight:800; letter-spacing:1.2px;
    font-size:1rem; border:1px solid #7fe7ff; color:#04122a;
    background:linear-gradient(90deg,#7fe7ff,#2ea8ff); box-shadow:0 0 14px rgba(46,168,255,.4);}
.stButton > button:hover {border-color:#fff; color:#04122a; filter:brightness(1.08);}
.stButton > button:disabled {background:#1a2f48; color:#7e9bb8; border-color:#35516e; box-shadow:none;}
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
# 8. DEPLOY HAIR BOOM CARD
#    (Hatchable reference was not available - this is a clean placeholder design.
#     Everything for the card lives in this one block so it is easy to swap.)
# =============================================================================
html('<div class="hs-section">🛟 DEPLOY HAIR BOOM</div>')

if not has_image:
    d_chip, d_text = '<span class="chip chip-grey">STANDBY</span>', "Upload an image to enable deployment."
elif stage == 0:
    d_chip = '<span class="chip chip-red">⚠ OIL SPILL DETECTED</span>'
    d_text = (f"Initial spill area: {fmt(START_C)} with containment, {fmt(START_U)} without. "
              "Deploy the hair boom to contain the oil.")
elif stage == 1:
    d_chip = '<span class="chip chip-cyan">🛡 HAIR BOOM DEPLOYED</span>'
    d_text = "The boom forms a floating barrier around the spill and stops the oil spreading."
elif stage == 2:
    d_chip = '<span class="chip chip-cyan">🧽 HAIR MAT DEPLOYED</span>'
    d_text = "The hair mesh mat absorbs the remaining floating oil inside the boom."
elif not complete:
    d_chip = '<span class="chip chip-yellow">⏳ VERIFYING CLEANUP</span>'
    d_text = f"Mock reading at {tmin(DATA.loc[idx, 'time'])}: {DATA.loc[idx, 'status']}."
else:
    d_chip = '<span class="chip chip-green">✔ SPILL CONTROLLED — CLEANUP SUCCESSFUL</span>'
    d_text = f"Mock reading at 5 min: {DATA.loc[LAST, 'status']}."

step_html = ""
for i, name in enumerate(["DETECT", "CONTAIN", "ABSORB", "VERIFY"]):
    cl = "" if not has_image else ("done" if (complete or i < stage) else ("now" if i == stage else ""))
    step_html += f'<div class="step {cl}">{i + 1}. {name}</div>'

html(f"""<div class="hs-card"><div class="hs-card-head"><span class="hs-card-title">DEPLOYMENT STATUS</span>
    <span class="badge b-sim">SIMULATED</span></div>
    <div class="steps">{step_html}</div>
    <div class="hs-chips" style="margin:0">{d_chip}</div>
    <div class="explain">{d_text}</div></div>""")

if not has_image:
    st.button("DEPLOY HAIR BOOM", disabled=True, key="b_disabled")
elif stage == 0:
    st.button("DEPLOY HAIR BOOM", on_click=deploy_boom, key="b_boom")
elif stage == 1:
    st.button("DEPLOY HAIR MAT", on_click=deploy_mat, key="b_mat")
elif stage == 2:
    st.button("START CLEANUP VERIFICATION", on_click=start_verification, key="b_verify")
elif not complete:
    st.button("NEXT READING ▶", on_click=advance, key="b_next")
    st.button("SKIP TO FINAL ⏭", on_click=skip_to_final, key="b_skip")
if has_image and stage > 0:
    st.button("↺ RESET DEMO", on_click=reset_demo, key="b_reset")

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
# 10. RESEARCH & EXPERIMENTAL RESULTS
# =============================================================================
html('<div class="hs-section" style="margin-top:30px">🔬 RESEARCH &amp; EXPERIMENTAL RESULTS</div>')
html("""<div class="hs-card"><div class="hs-card-head"><span class="hs-card-title">ABOUT THIS SECTION</span>
    <span class="badge b-rep">REPORTED DATA</span></div>
    <div class="cap">Values below are as reported in the research paper <i>“Employing Hair Mats as a
    Sustainable Approach for Oil Spill Remediation”</i>. They are separate from the simulated 5 mL
    exhibition demo above and have not been independently verified by this project.</div>
    <div class="hs-chips"><span class="badge b-rep">REPORTED</span><span class="badge b-calc">CALCULATED</span>
    <span class="badge b-qual">QUALITATIVE</span><span class="badge b-sim">SIMULATED</span></div>
    <div class="note">Tap a heading below to open its chart. Charts are fixed: no zoom or pan.</div></div>""")

# ---- Chart A -----------------------------------------------------------------
with st.expander("A · Hair mass vs. oil uptake", expanded=False):
    html('<span class="badge b-rep">REPORTED</span>')
    fa = go.Figure()
    for oil in OIL_ORDER:
        s = STYLE[oil]
        fa.add_trace(go.Scatter(
            x=HAIR_MASS, y=UPTAKE[oil], name=oil, mode="lines+markers",
            line=dict(color=s["color"], width=3, dash=s["dash"]),
            marker=dict(size=8, symbol=s["symbol"], color=s["color"]),
            hovertemplate=f"{oil}: " + "%{y} g<extra></extra>"))
    style_fig(fa, "Oil uptake by hair mass", "Hair mass (g)", "Oil uptake (g)", height=330)
    fa.update_xaxes(tickvals=HAIR_MASS)
    fa.update_layout(hovermode="x unified")
    show(fa, "chart_a")
    html("""<div class="cap"><b>What it shows:</b> reported uptake generally rises as hair mass increases, and the
        amount differs by oil type — cooking oil is highest at every tested mass. The cooking-oil value at
        2.5 g (19.5 g) is a large jump from 2.0 g (8.7 g); it is kept exactly as reported.<br>
        <b>What it cannot show:</b> why the jump occurs, how repeatable it is (no error bars were supplied), or
        how the results scale to real spills at sea.</div>""")

# ---- Chart B -----------------------------------------------------------------
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
    style_fig(fb, "Oil uptake by oil type (white outline = highest)", "Hair mass", "Oil uptake (g)", height=340)
    fb.update_layout(barmode="group", bargap=0.2, bargroupgap=0.05)
    fb.update_yaxes(range=[0, 22.5])
    show(fb, "chart_b")
    trs = "".join(f"<tr><td>{HAIR_MASS[j]:g} g</td><td>{winners[j]}</td>"
                  f"<td>{max(UPTAKE[o][j] for o in OIL_ORDER):g} g</td></tr>" for j in range(len(HAIR_MASS)))
    html(f"""<table class="tbl"><tr><th>HAIR MASS</th><th>HIGHEST UPTAKE</th><th>VALUE</th></tr>{trs}</table>
        <div class="cap"><b>What it shows:</b> side-by-side reported values; cooking oil is highest at all five
        masses. At 2.0 g, diesel (8.5 g) is close to cooking oil (8.7 g).<br>
        <b>What it cannot show:</b> whether differences are statistically significant, since repeat trials were
        not supplied.</div>""")

# ---- Chart C -----------------------------------------------------------------
with st.expander("C · Hair-boom liquid residue", expanded=False):
    html('<span class="badge b-rep">REPORTED</span> <span class="badge b-calc">DIFFERENCE = CALCULATED</span>')
    fc = go.Figure()
    fc.add_trace(go.Bar(
        x=OIL_ORDER, y=[LIQUID_INITIAL] * 3, name="Initial liquid value", marker_color="#4b79a8",
        text=[f"{LIQUID_INITIAL}"] * 3, textposition="outside", cliponaxis=False, textfont=dict(size=10),
        hovertemplate="Initial: %{y}<extra></extra>"))
    fc.add_trace(go.Bar(
        x=OIL_ORDER, y=[LIQUID_REMAINING[o] for o in OIL_ORDER], name="Remaining liquid value",
        marker_color="#7fe7ff", text=[f"{LIQUID_REMAINING[o]:g}" for o in OIL_ORDER],
        textposition="outside", cliponaxis=False, textfont=dict(size=10),
        hovertemplate="Remaining: %{y}<extra></extra>"))
    style_fig(fc, "Liquid remaining after hair-boom experiment", "Oil type", "Liquid value (as reported)", height=330)
    fc.update_layout(barmode="group", bargap=0.25)
    fc.update_yaxes(range=[0, 175])
    show(fc, "chart_c")
    trs = "".join(f"<tr><td>{o}</td><td>{LIQUID_INITIAL}</td><td>{LIQUID_REMAINING[o]:g}</td>"
                  f"<td>{LIQUID_INITIAL - LIQUID_REMAINING[o]:.1f}</td></tr>" for o in OIL_ORDER)
    html(f"""<table class="tbl"><tr><th>OIL</th><th>INITIAL</th><th>REMAINING</th><th>DIFFERENCE (calc.)</th></tr>
        {trs}</table>
        <div class="cap"><b>What the numbers are:</b> a reported “liquid value” before and after the boom
        experiment (unit: {LIQUID_UNIT}). A lower remaining value means more liquid was removed from the test
        container. <b>Not established:</b> that the difference is pure oil absorption — the source excerpt does
        not separate oil from any water or other liquid, so the app does not make that claim. The difference
        column is simple subtraction by this app, not a reported result.</div>""")

# ---- Chart D -----------------------------------------------------------------
with st.expander("D · Hair-boom mass before and after", expanded=False):
    html('<span class="badge b-rep">REPORTED</span> <span class="badge b-calc">GAIN = CALCULATED</span>')
    fd = go.Figure()
    fd.add_trace(go.Bar(
        x=OIL_ORDER, y=[BOOM_INITIAL_G] * 3, name="Initial boom mass", marker_color="#4b79a8",
        text=[f"{BOOM_INITIAL_G}"] * 3, textposition="outside", cliponaxis=False, textfont=dict(size=10),
        hovertemplate="Initial: %{y} g<extra></extra>"))
    fd.add_trace(go.Bar(
        x=OIL_ORDER, y=[BOOM_FINAL_G[o] for o in OIL_ORDER], name="Final boom mass",
        marker_color="#ffd166", text=[f"{BOOM_FINAL_G[o]:g}" for o in OIL_ORDER],
        textposition="outside", cliponaxis=False, textfont=dict(size=10),
        hovertemplate="Final: %{y} g<extra></extra>"))
    style_fig(fd, "Hair-boom mass before and after", "Oil type", "Boom mass (g)", height=330)
    fd.update_layout(barmode="group", bargap=0.25)
    fd.update_yaxes(range=[0, 150])
    show(fd, "chart_d")
    trs = "".join(f"<tr><td>{o}</td><td>{BOOM_INITIAL_G}</td><td>{BOOM_FINAL_G[o]:g}</td>"
                  f"<td>{BOOM_FINAL_G[o] - BOOM_INITIAL_G:.1f}</td></tr>" for o in OIL_ORDER)
    html(f"""<table class="tbl"><tr><th>OIL</th><th>INITIAL (g)</th><th>FINAL (g)</th><th>GAIN (calc., g)</th></tr>
        {trs}</table>
        <div class="cap"><b>What it shows:</b> values <i>reported in the research</i> for the boom's mass before
        and after the experiment; the ranking (cooking oil &gt; diesel &gt; petrol) matches chart C. These are not
        independently verified results.<br>
        <b>Note:</b> chart C and chart D use different measurements (a liquid value vs. boom mass), and the
        calculated changes are not numerically identical. Both are shown as reported and have not been
        reconciled. Final mass may include more than oil (e.g. trapped water), which the source
        excerpt does not separate.</div>""")

# ---- Chart E -----------------------------------------------------------------
with st.expander("E · Absorption over time (qualitative only)", expanded=False):
    html('<span class="badge b-qual">QUALITATIVE — NOT DATA</span>')
    times = " · ".join(f"{t} min" for t in CONTACT_TIMES_MIN)
    html(f"""<div class="cap">The research tested contact times of <b>{times}</b> and describes absorption as
        <b>initially rapid, then gradually slowing toward saturation</b>.</div>
        <div class="phases"><div class="phase">Rapid early uptake</div><div class="arrow">→</div>
        <div class="phase">Uptake slows</div><div class="arrow">→</div>
        <div class="phase">Approaches saturation</div></div>
        <div class="cap"><b>No numeric chart is shown:</b> exact absorption values for these times were not
        available in the material used to build this app, and this app does not invent data points. The strip above
        is an illustration of the described trend only — it does not map stages to specific minutes.
        If the paper contains a table of values for these times, they can be added as a proper chart.</div>""")

# =============================================================================
# 11. FOOTER
# =============================================================================
html("""<div class="note" style="text-align:center;margin-top:26px">HairShield · The analysis card and cleanup
    demo use fixed SIMULATED data and no real AI. Research values are as reported in the source paper and
    have not been independently verified. Real AI detection and real-world measurements may be added in a future
    version.</div>""")
