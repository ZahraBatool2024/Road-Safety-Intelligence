"""Brand constants and global CSS (deep-navy theme matching the logo: teal + gold on navy)."""
from pathlib import Path

APP_NAME = "Road Safety Intelligence"
TAGLINE = "AI-powered near-miss analytics"
ASSETS = Path(__file__).resolve().parent.parent / "assets"

# palette (taken from the logo)
NAVY, NAVY_2 = "#021730", "#0A2646"
TEAL, GOLD = "#3FD6BE", "#E9C46A"
INK, MUTED = "#F2F8FB", "#A9C0D3"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', 'Segoe UI', sans-serif; }
.stApp { background:
    radial-gradient(1000px 520px at 85% -10%, rgba(63,214,190,.10), transparent 60%),
    radial-gradient(900px 480px at -5% 105%, rgba(233,196,106,.07), transparent 60%),
    linear-gradient(180deg, #03193A 0%, #021226 100%) fixed; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 3.4rem; max-width: 1240px; }
h1, h2, h3, h4 { color:#F2F8FB; letter-spacing:-.01em; }
p, li, label, .stMarkdown { color:#D5E4EE; }
[data-testid="stCaptionContainer"] { color:#A9C0D3; }

/* ---------- top bar: logo left, navigation right ---------- */
header[data-testid="stHeader"] { background: rgba(2,23,48,.88); backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(63,214,190,.16); height: 4.6rem; }
img[data-testid="stHeaderLogo"], [data-testid="stHeaderLogo"] { height: 3.4rem !important; width:auto !important; max-width:none !important; }
[data-testid="stLogoLink"] { flex-shrink: 0; }
header[data-testid="stHeader"] [data-testid="stToolbar"] nav,
header[data-testid="stHeader"] [data-testid="stToolbar"] nav > div { justify-content: flex-end; }
header[data-testid="stHeader"] [data-testid="stToolbar"] nav > *:first-child { margin-left: auto; }
[data-testid="stTopNavLink"] { font-weight: 600; letter-spacing: .01em; }

/* ---------- hero ---------- */
.hero { position:relative; overflow:hidden; padding: 2.8rem 2.5rem; border-radius: 24px; margin-bottom: 1.8rem;
  background: radial-gradient(700px 320px at 92% -20%, rgba(63,214,190,.22), transparent 62%),
              radial-gradient(600px 300px at 0% 130%, rgba(233,196,106,.14), transparent 60%),
              linear-gradient(135deg, #0B2748 0%, #08203D 100%);
  border: 1px solid rgba(63,214,190,.22); box-shadow: 0 18px 48px rgba(0,0,0,.35), inset 0 1px 0 rgba(255,255,255,.05); }
.hero::after { content:""; position:absolute; right:-40px; top:-40px; width:260px; height:260px; border-radius:50%;
  border:1px dashed rgba(233,196,106,.28); }
.hero .eyebrow { color:#E9C46A; font-weight:700; letter-spacing:.16em; font-size:.78rem; text-transform:uppercase; }
.hero h1 { font-size: 2.7rem; line-height:1.1; margin:.55rem 0 .85rem; font-weight:800; letter-spacing:-.025em; color:#F2F8FB; }
.hero h1 span { background:linear-gradient(90deg,#3FD6BE,#E9C46A); -webkit-background-clip:text; background-clip:text; color:transparent; }
.hero p  { color:#B9CDDD; font-size:1.08rem; max-width: 720px; margin:0; }

/* ---------- cards ---------- */
.kcard, .kpi { background: linear-gradient(160deg, rgba(14,48,88,.72), rgba(8,32,62,.72));
  border:1px solid rgba(63,214,190,.16); border-radius:16px; box-shadow: 0 10px 28px rgba(0,0,0,.28); }
.kcard { padding:1.15rem 1.25rem; height:100%; transition: transform .18s ease, border-color .18s ease; }
.kcard:hover { transform: translateY(-3px); border-color: rgba(233,196,106,.45); }
.kcard .ic { font-size:1.4rem; }
.kcard h4 { margin:.4rem 0 .25rem; font-size:1.02rem; font-weight:700; color:#F2F8FB; }
.kcard p  { margin:0; color:#A9C0D3; font-size:.92rem; line-height:1.5; }
.kpi { padding:1rem 1.2rem; }
.kpi .v { font-size:1.95rem; font-weight:800; letter-spacing:-.02em; color:#F2F8FB; }
.kpi .l { color:#A9C0D3; font-size:.76rem; text-transform:uppercase; letter-spacing:.11em; font-weight:700; }
.kpi.alert .v { color:#F5C451; }
.step { display:flex; gap:.85rem; align-items:flex-start; margin:.65rem 0; }
.step .n { min-width:30px; height:30px; border-radius:50%; background:linear-gradient(135deg,#3FD6BE,#E9C46A);
  color:#021730; font-weight:800; display:flex; align-items:center; justify-content:center; font-size:.85rem; }
.step b { display:block; color:#F2F8FB; } .step span { color:#A9C0D3; font-size:.92rem; }
.finding { border-left:4px solid #E9C46A; border-radius:12px; padding:.9rem 1.1rem; margin:.2rem 0 1rem;
  background: linear-gradient(90deg, rgba(233,196,106,.12), rgba(233,196,106,.03)); color:#E8F3F8; font-size:.98rem; }
.finding b { color:#E9C46A; letter-spacing:.06em; font-size:.74rem; text-transform:uppercase; display:block; margin-bottom:.2rem; }
.empty { text-align:center; padding:3rem 1rem; border:1.5px dashed rgba(63,214,190,.35); border-radius:16px;
  color:#B9CDDD; background:rgba(10,38,70,.45); }
.footnote { color:#7F98AE; font-size:.82rem; margin-top:2rem; text-align:center; }
</style>
"""
