"""
Skill Swap - teens trade skills in 15-minute sessions.
Streamlit front end, Groq for the AI parts (lesson plans, first messages, Swap Coach chat).

Run:
    pip install -r requirements.txt
    export GROQ_API_KEY="your key"      # or paste it in the sidebar, or use .streamlit/secrets.toml
    streamlit run app.py
"""
import html
import json
import os
import zlib

import streamlit as st
import streamlit.components.v1 as components

try:
    from groq import Groq
except ImportError:  # the app still runs, only the AI features are off
    Groq = None

st.set_page_config(page_title="Skill Swap", page_icon="🎴", layout="wide")
ss = st.session_state

# --------------------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------------------
CATS = {
    "music": ("Music", "#ff8fc3"),
    "art": ("Art & design", "#b49cff"),
    "code": ("Code", "#6fd3ff"),
    "words": ("Words", "#ffd84d"),
    "life": ("Life skills", "#b9f05a"),
    "brain": ("Brain games", "#ffa467"),
}
SKILLS = {
    "Guitar basics": "music", "Beatmaking": "music", "Songwriting": "music", "Ukulele": "music",
    "Photoshop": "art", "Digital drawing": "art", "Calligraphy": "art", "Figma": "art", "Video editing": "art",
    "Python": "code", "HTML & CSS": "code",
    "Spanish chat": "words", "Public speaking": "words", "Creative writing": "words",
    "Baking": "life", "Knitting": "life",
    "Chess openings": "brain", "Mental math": "brain", "Rubik's cube": "brain",
}
THEMES = {
    "Sunset": ("#ff8fc3", "#ffa467"),
    "Ocean": ("#6fd3ff", "#b49cff"),
    "Lime": ("#b9f05a", "#6fd3ff"),
    "Gold": ("#ffd84d", "#ff8fc3"),
    "Grape": ("#b49cff", "#ff8fc3"),
}
KUDOS = ["Patient", "Clear steps", "Funny", "Fast learner", "Great energy"]
LEVELS = ["Rookie", "Regular", "Mentor", "Legend"]
TAG_COLORS = {"perfect": "#b9f05a", "learn": "#6fd3ff", "give": "#ff8fc3", "you": "#ffd84d"}
TAG_TEXT = {"perfect": "Perfect swap", "learn": "You can learn", "give": "Wants your skill"}
MATCH_RANK = {"perfect": 0, "learn": 1, "give": 2, "none": 3}
MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

PEOPLE = [
    dict(id="maya", name="Maya R.", tagline="Night-owl illustrator", theme="Grape",
         teaches=["Photoshop", "Digital drawing"], wants=["Guitar basics"], taught=26, rating="4.9", reply="10m",
         slots=["Today 6:00 PM", "Tomorrow 4:30 PM", "Sat 11:00 AM"]),
    dict(id="leo", name="Leo T.", tagline="Beat tinkerer", theme="Sunset",
         teaches=["Beatmaking", "Video editing"], wants=["Python", "Chess openings"], taught=14, rating="4.8", reply="25m",
         slots=["Today 7:30 PM", "Fri 5:00 PM", "Sun 2:00 PM"]),
    dict(id="priya", name="Priya S.", tagline="Python and pizza", theme="Ocean",
         teaches=["Python", "HTML & CSS"], wants=["Spanish chat", "Rubik's cube"], taught=31, rating="5.0", reply="5m",
         slots=["Today 5:15 PM", "Tomorrow 6:00 PM", "Sat 3:00 PM"]),
    dict(id="diego", name="Diego M.", tagline="Spanish with jokes", theme="Gold",
         teaches=["Spanish chat", "Public speaking"], wants=["Photoshop", "Video editing"], taught=9, rating="4.7", reply="1h",
         slots=["Tomorrow 5:00 PM", "Fri 6:30 PM", "Sat 10:00 AM"]),
    dict(id="zara", name="Zara A.", tagline="Cake scientist", theme="Lime",
         teaches=["Baking", "Knitting"], wants=["Python", "Public speaking"], taught=17, rating="4.9", reply="15m",
         slots=["Today 6:45 PM", "Thu 4:00 PM", "Sun 11:30 AM"]),
    dict(id="omar", name="Omar H.", tagline="Chess club captain", theme="Ocean",
         teaches=["Chess openings", "Mental math"], wants=["Guitar basics", "Beatmaking"], taught=5, rating="4.6", reply="40m",
         slots=["Tomorrow 7:00 PM", "Fri 4:00 PM", "Sat 1:00 PM"]),
    dict(id="nina", name="Nina W.", tagline="Cube solver, 14 seconds", theme="Sunset",
         teaches=["Rubik's cube", "Calligraphy", "Creative writing"], wants=["Figma", "Baking"], taught=14, rating="4.8", reply="30m",
         slots=["Today 8:00 PM", "Thu 5:30 PM", "Sun 4:00 PM"]),
    dict(id="kai", name="Kai L.", tagline="Sunday songwriter", theme="Grape",
         teaches=["Songwriting", "Ukulele"], wants=["Video editing", "Rubik's cube"], taught=21, rating="4.9", reply="20m",
         slots=["Tomorrow 3:30 PM", "Fri 7:00 PM", "Sat 5:00 PM"]),
]
BY_ID = {p["id"]: p for p in PEOPLE}

BADGES = [
    dict(name="First Swap", desc="Finish your first 15-minute swap.", glyph="1st", color="#b9f05a", goal=1, val=lambda s: s["done"]),
    dict(name="Triple Threat", desc="Finish 3 swaps.", glyph="x3", color="#6fd3ff", goal=3, val=lambda s: s["done"]),
    dict(name="Ten Deep", desc="Finish 10 swaps.", glyph="x10", color="#ffd84d", goal=10, val=lambda s: s["done"]),
    dict(name="Cross-Trainer", desc="Learn from 3 different areas.", glyph="3+", color="#b49cff", goal=3, val=lambda s: s["cats"]),
    dict(name="Multi-talent", desc="Teach 3 different skills.", glyph="Mix", color="#ffa467", goal=3, val=lambda s: s["taught"]),
    dict(name="Collector", desc="Collect 5 cards in your binder.", glyph="5", color="#ff8fc3", goal=5, val=lambda s: len(s["collected"])),
    dict(name="Full Binder", desc="Collect every card in the deck.", glyph="All", color="#6fd3ff", goal=len(PEOPLE), val=lambda s: len(s["collected"])),
    dict(name="Good Vibes", desc="Give kudos 5 times.", glyph="+5", color="#b9f05a", goal=5, val=lambda s: s["kudos"]),
]

SEED_SESSIONS = [
    dict(id="s1", personId="omar", learn="Chess openings", teach="Guitar basics", slot="Last Sat", status="done", kudos=["Patient"]),
    dict(id="s2", personId="priya", learn="Python", teach="Rubik's cube", slot="Last Thu", status="done", kudos=["Clear steps"]),
    dict(id="s3", personId="maya", learn="Photoshop", teach="Guitar basics", slot="Today 6:00 PM", status="booked", kudos=[]),
]

SYSTEM_PROMPT = (
    "You are Swap Coach inside Skill Swap, an app where teenagers aged 13 to 17 trade skills in short "
    "15-minute sessions (7 minutes each way plus a 1-minute wrap-up) in a moderated group room. "
    "Be friendly, concrete and brief, in simple language. Keep everything age-appropriate and safe. "
    "Never ask for or encourage sharing personal details (full name, address, phone number, school, social handles) "
    "and never suggest meeting in person. If someone seems unsafe or upset, tell them to talk to a trusted adult."
)

# --------------------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------------------
def init_state():
    ss.setdefault("profile", dict(name="Alex K.", tagline="Garage guitarist", theme="Ocean",
                                  teaches=["Guitar basics", "Rubik's cube"], wants=["Photoshop", "Python"]))
    ss.setdefault("sessions", [dict(s) for s in SEED_SESSIONS])
    ss.setdefault("plans", {})
    ss.setdefault("coach", [])
    ss.setdefault("api_key", "")


def stats():
    done = [s for s in ss.sessions if s["status"] == "done"]
    kudos = sum(len(s["kudos"]) for s in done)
    xp = len(done) * 50 + kudos * 10
    collected = []
    for s in done:
        if s["personId"] not in collected:
            collected.append(s["personId"])
    return dict(
        done=len(done), kudos=kudos, xp=xp, collected=collected,
        cats=len({SKILLS.get(s["learn"], "art") for s in done}),
        taught=len({s["teach"] for s in done}),
        lvl=xp // 150 + 1, into=xp % 150,
    )


def unlocked_names():
    st_ = stats()
    return {b["name"] for b in BADGES if b["val"](st_) >= b["goal"]}


def rarity(n, me=False):
    if me:
        return "holo" if n >= 8 else "rare" if n >= 3 else "common"
    return "holo" if n >= 25 else "rare" if n >= 10 else "common"


def match_of(p):
    me = ss.profile
    give = [s for s in me["teaches"] if s in p["wants"]]
    get = [s for s in p["teaches"] if s in me["wants"]]
    kind = "perfect" if give and get else "learn" if get else "give" if give else "none"
    return dict(give=give, get=get, kind=kind)


# --------------------------------------------------------------------------------------
# Groq
# --------------------------------------------------------------------------------------
def resolve_api_key():
    if ss.get("api_key"):
        return ss.api_key.strip()
    if os.getenv("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"].strip()
    try:
        return str(st.secrets["GROQ_API_KEY"]).strip()
    except Exception:
        return ""


def llm(messages, temperature=0.7, max_tokens=700):
    """Returns (text, error). Exactly one of them is None."""
    if Groq is None:
        return None, "The groq package is not installed. Run: pip install -r requirements.txt"
    key = resolve_api_key()
    if not key:
        return None, "Add your Groq API key in the sidebar (or set GROQ_API_KEY) to use the AI features."
    try:
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model=ss.get("model", MODELS[0]),
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content, None
    except Exception as exc:  # network, auth, rate limit
        return None, f"Groq error: {exc}"


def ask(prompt, **kw):
    return llm([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}], **kw)


# --------------------------------------------------------------------------------------
# HTML builders (kept on one line each: Streamlit treats indented HTML as a code block)
# --------------------------------------------------------------------------------------
def esc(s):
    return html.escape(str(s), quote=True)


def sticker(skill, want=False):
    color = CATS[SKILLS.get(skill, "art")][1]
    return f'<span class="stk{" want" if want else ""}" style="--cat:{color}">{esc(skill)}</span>'


def avatar_svg(pid, name, theme):
    c1, c2 = THEMES[theme]
    h = zlib.crc32(pid.encode())

    def r(n):
        return ((h >> (n * 3)) % 100) / 100

    ini = esc((name.strip()[:1] or "?").upper())
    return "".join([
        '<svg viewBox="0 0 250 150" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="250" height="150" fill="{c2}"/>',
        f'<circle cx="{40 + r(1) * 70:.0f}" cy="{30 + r(2) * 50:.0f}" r="{50 + r(3) * 34:.0f}" fill="{c1}"/>',
        f'<rect x="{150 + r(4) * 50:.0f}" y="{50 + r(5) * 50:.0f}" width="90" height="90" rx="{10 + r(6) * 30:.0f}" '
        f'transform="rotate({r(7) * 40 - 20:.0f} 200 100)" fill="#1b1730" opacity=".16"/>',
        f'<path d="M0 150 Q 60 {90 + r(8) * 30:.0f} 125 120 T 250 {100 + r(9) * 30:.0f} V150Z" fill="#1b1730" opacity=".2"/>',
        '<text x="125" y="110" text-anchor="middle" font-family="Bricolage Grotesque, Arial Black, sans-serif" '
        f'font-weight="800" font-size="104" fill="#ffffff" stroke="#1b1730" stroke-width="5" paint-order="stroke">{ini}</text>',
        "</svg>",
    ])


def card_html(p, tag=None, stats_row=None, rar=None, mini=False):
    f1, f2 = THEMES[p["theme"]]
    rar = rar or rarity(p["taught"])
    stats_row = stats_row or [(p["taught"], "Swaps"), (p["rating"], "Rating"), (p["reply"], "Replies")]
    teaches = "".join(sticker(s) for s in p["teaches"]) or '<span class="muted">Pick a skill</span>'
    wants = "".join(sticker(s, True) for s in p["wants"]) or '<span class="muted">Pick a skill</span>'
    tag_html = ""
    if tag:
        tag_html = f'<span class="tag" style="background:{TAG_COLORS[tag[0]]}">{esc(tag[1])}</span>'
    body = ""
    if not mini:
        stats_html = "".join(f"<div><b>{esc(v)}</b><span>{esc(l)}</span></div>" for v, l in stats_row)
        body = (
            f'<div class="grp"><span class="lbl">Teaches</span><div class="stks">{teaches}</div></div>'
            f'<div class="grp"><span class="lbl">Wants to learn</span><div class="stks">{wants}</div></div>'
            f'<div class="stats">{stats_html}</div>'
        )
    tg = "" if mini else f'<div class="tg">{esc(p["tagline"])}</div>'
    return (
        f'<div class="card" style="--f1:{f1};--f2:{f2}"><div class="card-in">'
        f'<div class="topline"><span class="rar rar-{rar}">{rar.title()}</span>{tag_html}</div>'
        f'<div class="art">{avatar_svg(p["id"], p["name"], p["theme"])}</div>'
        f'<div><div class="nm">{esc(p["name"])}</div>{tg}</div>{body}</div></div>'
    )


def my_person():
    P = ss.profile
    return dict(id="me", name=P["name"] or "You", tagline=P["tagline"] or "Add a tagline", theme=P["theme"],
                teaches=P["teaches"], wants=P["wants"], taught=stats()["done"], rating="-", reply="-")


def my_card_html():
    s = stats()
    return card_html(my_person(), tag=("you", f"Level {s['lvl']}"),
                     stats_row=[(s["done"], "Swaps"), (s["kudos"], "Kudos"), (s["xp"], "XP")],
                     rar=rarity(s["done"], me=True))


def medal_html(b, on):
    cls = "medal" if on else "medal off"
    return (f'<svg class="{cls}" viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">'
            f'<polygon points="40,4 72,22 72,58 40,76 8,58 8,22" fill="{b["color"]}" stroke="#f4f1ff" stroke-width="3" stroke-linejoin="round"/>'
            f'<text x="40" y="49" text-anchor="middle" font-family="Bricolage Grotesque, Arial Black, sans-serif" '
            f'font-weight="800" font-size="22" fill="#1b1730">{esc(b["glyph"])}</text></svg>')


def session_row_html(s):
    p = BY_ID[s["personId"]]
    kudos = ""
    if s["status"] == "done" and s["kudos"]:
        kudos = '<div class="rline"><span class="lbl">Kudos</span>' + "".join(f'<span class="kudo">{esc(k)}</span>' for k in s["kudos"]) + "</div>"
    return (
        f'<div class="srow"><div class="mav">{avatar_svg(p["id"], p["name"], p["theme"])}</div>'
        f'<div><div><b>{esc(p["name"])}</b> <span class="muted">{esc(s["slot"])}</span></div>'
        f'<div class="rline"><span class="lbl">You learn</span>{sticker(s["learn"])}<span class="lbl">You teach</span>{sticker(s["teach"])}</div>'
        f'{kudos}</div></div>'
    )


TIMER_HTML = """
<div style="font-family:Figtree,system-ui,sans-serif;text-align:center;color:#f4f1ff;background:#171325;border:2px solid #443b69;border-radius:18px;padding:18px">
  <div id="t" style="font-size:58px;font-weight:800;letter-spacing:-.03em;font-variant-numeric:tabular-nums">15:00</div>
  <div style="height:10px;border-radius:99px;background:#272142;border:2px solid #f4f1ff;overflow:hidden;margin:6px 0 12px"><div id="bar" style="height:100%;width:0;background:#ff6a3d"></div></div>
  <div id="ph" style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#b9b2d2">Ready</div>
  <div id="line" style="font-size:18px;font-weight:700;min-height:48px;margin:8px 0 12px"></div>
  <button id="go" style="padding:10px 18px;border-radius:12px;border:2px solid #f4f1ff;background:#ff6a3d;color:#1b1730;font-weight:800;cursor:pointer">Start</button>
  <button id="skip" style="padding:10px 18px;border-radius:12px;border:2px solid #443b69;background:transparent;color:#f4f1ff;font-weight:700;cursor:pointer;margin-left:8px">Skip round</button>
</div>
<script>
const TEACH=__TEACH__, LEARN=__LEARN__, ME=__ME__, PARTNER=__PARTNER__;
const B=[420,840,900];
let e=0, run=false, iv=null;
const ph=()=> e<420?0:e<840?1:2;
const fmt=s=>String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0');
const $=id=>document.getElementById(id);
function draw(){
  $('t').textContent=fmt(900-e);
  $('bar').style.width=(e/9)+'%';
  const p=ph();
  $('ph').textContent = (e===0&&!run) ? 'Ready' : (e>=900 ? 'Done' : ['Round 1 of 2','Round 2 of 2','Wrap-up'][p]);
  $('line').textContent = e>=900 ? 'Nice swap. Head back and collect your card.' :
     [ME+' teaches '+TEACH+'.', PARTNER+' teaches '+LEARN+'.', 'Swap one tip each and say thanks.'][p];
  $('go').textContent = run ? 'Pause' : (e===0 ? 'Start' : (e>=900 ? 'Restart' : 'Resume'));
}
$('go').onclick=()=>{
  if(e>=900){e=0;}
  run=!run; clearInterval(iv);
  if(run){iv=setInterval(()=>{e++; if(e>=900){clearInterval(iv);run=false;} draw();},1000);}
  draw();
};
$('skip').onclick=()=>{ e=B[ph()]; if(e>=900){clearInterval(iv);run=false;} draw(); };
draw();
</script>
"""


def timer_component(me_name, partner, teach, learn):
    def js(v):
        return json.dumps(v).replace("</", "<\\/")
    code = (TIMER_HTML.replace("__TEACH__", js(teach)).replace("__LEARN__", js(learn))
            .replace("__ME__", js(me_name)).replace("__PARTNER__", js(partner)))
    components.html(code, height=330)


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500..800&family=DM+Mono:wght@400;500&family=Figtree:wght@400..800&display=swap');
.stApp{background-color:#100d1c;background-image:radial-gradient(#231e3a 1.3px,transparent 1.4px);background-size:22px 22px;color:#f4f1ff;font-family:'Figtree',system-ui,sans-serif}
[data-testid="stSidebar"]{background:#171325;border-right:2px solid #352e58}
h1,h2,h3,h4{font-family:'Bricolage Grotesque','Arial Black',sans-serif!important;letter-spacing:-.025em!important;font-weight:800!important}
.mark{font-family:'Bricolage Grotesque','Arial Black',sans-serif;font-weight:800;font-size:30px;letter-spacing:-.04em;display:flex;align-items:center;gap:8px;line-height:1;margin-bottom:6px}
.mark b{background:#ffd84d;color:#1b1730;padding:.06em .3em .1em;border-radius:10px;border:2px solid #f4f1ff;transform:rotate(-3deg);box-shadow:3px 3px 0 #f4f1ff}
.muted{color:#b3acce;font-size:13px}
.lbl{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#b9b2d2}
.stButton>button{border-radius:14px;border:2px solid #f4f1ff;background:#ff6a3d;color:#1b1730;font-weight:800;box-shadow:3px 3px 0 #f4f1ff;transition:transform .1s,box-shadow .1s}
.stButton>button:hover{transform:translate(-1px,-1px);box-shadow:4px 4px 0 #f4f1ff;color:#1b1730;border-color:#f4f1ff}
.stButton>button:active{transform:translate(2px,2px);box-shadow:1px 1px 0 #f4f1ff}
.stTabs [data-baseweb="tab"]{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:16px}
/* trading card */
.card{--f1:#ff8fc3;--f2:#ffa467;position:relative;border-radius:22px;padding:6px;overflow:hidden;background:linear-gradient(145deg,var(--f1),var(--f2));box-shadow:0 12px 26px -12px rgba(10,5,30,.7);transition:transform .25s ease,box-shadow .25s ease;margin-bottom:8px}
.card:hover{transform:translateY(-5px) rotate(-.7deg) scale(1.015);box-shadow:0 24px 40px -14px rgba(10,5,30,.8)}
.card::after{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;mix-blend-mode:color-dodge;opacity:0;
  background:repeating-linear-gradient(115deg,rgba(255,60,172,0) 0%,rgba(255,60,172,.6) 8%,rgba(60,210,255,.6) 16%,rgba(255,232,60,.6) 24%,rgba(150,100,255,.6) 32%,rgba(255,60,172,0) 40%);
  background-size:300% 300%;background-position:0% 0%;transition:opacity .3s ease,background-position .9s ease}
.card:hover::after{opacity:.65;background-position:100% 100%}
.card:has(.rar-holo)::after{opacity:.25}
.card:has(.rar-holo):hover::after{opacity:.85}
.card-in{background:#171325;border-radius:17px;padding:12px;display:flex;flex-direction:column;gap:11px;color:#f6f3ff;min-height:430px}
.topline{display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap}
.rar{font-family:'DM Mono',monospace;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;padding:.35em .6em;border-radius:6px;border:1.5px solid #443b69;color:#b9b2d2}
.rar-rare{background:#6fd3ff;color:#1b1730;border-color:#6fd3ff}
.rar-holo{background:linear-gradient(90deg,#ff8fc3,#ffd84d,#b9f05a,#6fd3ff,#b49cff);color:#1b1730;border-color:transparent}
.tag{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:11.5px;padding:.35em .6em;border-radius:8px;color:#1b1730}
.art{aspect-ratio:5/3;border-radius:12px;overflow:hidden;border:2px solid #443b69}
.art svg{display:block;width:100%;height:100%}
.nm{font-family:'Bricolage Grotesque','Arial Black',sans-serif;font-weight:800;font-size:23px;letter-spacing:-.025em;line-height:1.05}
.tg{font-size:13px;color:#b9b2d2;margin-top:3px}
.grp{display:flex;flex-direction:column;gap:7px}
.stks{display:flex;flex-wrap:wrap;gap:8px 6px}
.stk{display:inline-block;font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:12.5px;line-height:1;padding:.55em .8em;border-radius:10px;background:var(--cat);color:#1b1730;border:2px solid #fff;box-shadow:0 2px 0 rgba(0,0,0,.3),0 6px 10px -5px rgba(0,0,0,.55);transform:rotate(-2deg)}
.stks .stk:nth-child(even){transform:rotate(1.6deg)}
.stk.want{background:transparent;color:#f6f3ff;border:2px dashed #443b69;box-shadow:none}
.stats{margin-top:auto;border-top:1px dashed #443b69;padding-top:10px;display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.stats b{display:block;font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:16px}
.stats span{font-family:'DM Mono',monospace;font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:#b9b2d2}
/* session rows, badges */
.srow{display:flex;gap:14px;align-items:center}
.mav{width:56px;height:56px;border-radius:14px;overflow:hidden;border:2px solid #f4f1ff;flex:none}
.mav svg{display:block;width:100%;height:100%}
.rline{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;margin-top:8px}
.kudo{font-size:12.5px;font-weight:600;border:2px solid #352e58;border-radius:99px;padding:.2em .7em}
.badges{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px;margin-top:10px}
.badge{display:grid;grid-template-columns:72px 1fr;gap:14px;align-items:center;background:#1a1630;border:2px solid #352e58;border-radius:18px;padding:14px}
.badge.on{border-color:#f4f1ff}
.badge h4{margin:0;font-size:17px}
.badge p{margin:2px 0 0;font-size:13px;color:#b3acce}
.pbar{height:9px;border-radius:99px;border:1.5px solid #f4f1ff;background:#272142;overflow:hidden;margin-top:9px}
.pbar i{display:block;height:100%;background:#ff6a3d}
.medal{width:72px;height:72px;display:block;transition:transform .2s}
.badge.on:hover .medal{transform:rotate(-6deg) scale(1.06)}
.medal.off{filter:grayscale(1);opacity:.5}
.slot{min-height:140px;border:2px dashed #352e58;border-radius:22px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#b3acce;padding:16px;margin-bottom:8px}
.slot b{font-family:'Bricolage Grotesque',sans-serif;font-size:40px;color:#f4f1ff;line-height:1}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""


# --------------------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------------------
init_state()
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

if ss.get("flash"):
    st.toast(ss.pop("flash"))
if ss.pop("balloons", False):
    st.balloons()

# ---- Sidebar (runs first so the rest of the page always sees the latest profile) ----
with st.sidebar:
    st.markdown('<div class="mark">skill <b>swap</b></div>', unsafe_allow_html=True)
    st.caption("Teach 7 minutes. Learn 7 minutes. Wrap up in 1.")

    st.subheader("Groq AI")
    ss.api_key = st.text_input("Groq API key", type="password", value=ss.api_key,
                               help="Or set the GROQ_API_KEY environment variable, or add it to .streamlit/secrets.toml.")
    ss.model = st.selectbox("Model", MODELS)
    st.caption("AI is on." if resolve_api_key() else "Add a key to turn on the AI features.")

    st.divider()
    st.subheader("Your card")
    P = ss.profile
    P["name"] = st.text_input("Display name", value=P["name"], max_chars=14, key="in_name",
                              help="Use a first name and an initial. Keep your last name private.")
    P["tagline"] = st.text_input("Tagline", value=P["tagline"], max_chars=34, key="in_tag")
    P["theme"] = st.radio("Card color", list(THEMES), index=list(THEMES).index(P["theme"]), horizontal=True, key="in_theme")
    P["teaches"] = st.multiselect("I can teach (up to 3)", list(SKILLS), default=P["teaches"], max_selections=3, key="in_teach")
    wants_in = st.multiselect("I want to learn (up to 3)", list(SKILLS), default=P["wants"], max_selections=3, key="in_want")
    overlap = [s for s in wants_in if s in P["teaches"]]
    if overlap:
        st.warning("You can't both teach and want: " + ", ".join(overlap) + ". Kept as teaching only.")
    P["wants"] = [s for s in wants_in if s not in P["teaches"]]

    st.divider()
    if st.button("Reset demo"):
        for k in list(ss.keys()):
            del ss[k]
        st.rerun()

# ---- Header ----
S = stats()
st.markdown("# Trade what you know for what you want.")
st.caption(f"Level {S['lvl']} {LEVELS[min(S['lvl'] - 1, 3)]}  |  {S['xp']} XP  |  {S['done']} swaps  |  "
           f"{len(S['collected'])}/{len(PEOPLE)} cards collected")

booked_count = sum(1 for s in ss.sessions if s["status"] == "booked")
tab_discover, tab_sessions, tab_card, tab_binder, tab_coach = st.tabs(
    ["Discover", f"Sessions ({booked_count})", "My card", "Binder", "Swap Coach"])

# ---- Discover ----
with tab_discover:
    st.markdown('<span class="lbl">You teach</span>', unsafe_allow_html=True)
    st.markdown('<div class="stks" style="margin:6px 0 12px">' + ("".join(sticker(s) for s in ss.profile["teaches"]) or '<span class="muted">Nothing yet</span>')
                + '</div><span class="lbl">You want</span><div class="stks" style="margin:6px 0 12px">'
                + ("".join(sticker(s, True) for s in ss.profile["wants"]) or '<span class="muted">Nothing yet</span>') + "</div>",
                unsafe_allow_html=True)

    filters = ["Best matches", "Everyone"] + [v[0] for v in CATS.values()]
    flt = st.radio("Filter", filters, horizontal=True, label_visibility="collapsed")
    rows = [(p, match_of(p)) for p in PEOPLE]
    if flt == "Best matches":
        shown = [r for r in rows if r[1]["kind"] != "none"]
        if not shown:
            st.info("No overlap with your card yet. Showing everyone. Add skills in the sidebar to find matches.")
            shown = rows
    elif flt == "Everyone":
        shown = rows
    else:
        key = next(k for k, v in CATS.items() if v[0] == flt)
        shown = [r for r in rows if any(SKILLS[s] == key for s in r[0]["teaches"])]
    shown = sorted(shown, key=lambda r: (MATCH_RANK[r[1]["kind"]], -r[0]["taught"]))

    cols = st.columns(3)
    for i, (p, m) in enumerate(shown):
        with cols[i % 3]:
            tag = (m["kind"], TAG_TEXT[m["kind"]]) if m["kind"] != "none" else None
            st.markdown(card_html(p, tag=tag), unsafe_allow_html=True)
            first = p["name"].split()[0]
            with st.expander(f"Swap with {first}"):
                st.caption(f"Replies in about {p['reply']}.")
                learn_idx = p["teaches"].index(m["get"][0]) if m["get"] else 0
                learn = st.selectbox("You learn", p["teaches"], index=learn_idx, key=f"learn_{p['id']}")
                if ss.profile["teaches"]:
                    teach_idx = ss.profile["teaches"].index(m["give"][0]) if m["give"] else 0
                    teach = st.selectbox("You teach", ss.profile["teaches"], index=teach_idx, key=f"teach_{p['id']}")
                else:
                    teach = None
                    st.warning("Add a skill you can teach in the sidebar first.")
                slot = st.selectbox("Time", p["slots"], key=f"slot_{p['id']}")
                if st.button("Write my first message", key=f"msg_{p['id']}", disabled=not teach):
                    with st.spinner("Writing"):
                        text, err = ask(
                            f"Write a short, friendly first message (max 40 words) from {ss.profile['name']} to {first} "
                            f"proposing a skill swap: I teach {teach}, you teach {learn}, {slot}. "
                            "Casual teen tone, no personal info.", temperature=0.9, max_tokens=150)
                    if err:
                        st.error(err)
                    else:
                        st.text_area("Copy this", text.strip(), key=f"draft_{p['id']}_{abs(hash(text)) % 10000}", height=110)
                if st.button("Send swap request", key=f"send_{p['id']}", disabled=not teach):
                    ss.sessions.append(dict(id=f"s{len(ss.sessions)}{abs(hash(slot + learn)) % 1000}", personId=p["id"],
                                            learn=learn, teach=teach, slot=slot, status="booked", kudos=[]))
                    ss.flash = f"Request sent to {first}. Find it in Sessions."
                    st.rerun()

# ---- Sessions ----
with tab_sessions:
    st.subheader("Coming up")
    booked = [s for s in ss.sessions if s["status"] == "booked"]
    if not booked:
        st.info("Nothing booked yet. Open a card in Discover and send a swap request.")
    for s in booked:
        p = BY_ID[s["personId"]]
        first = p["name"].split()[0]
        with st.container(border=True):
            st.markdown(session_row_html(s), unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("Generate AI lesson plan", key=f"plan_{s['id']}"):
                with st.spinner("Planning your 15 minutes"):
                    text, err = ask(
                        f"Plan a 15-minute skill swap between two teens.\n"
                        f"- {ss.profile['name']} teaches: {s['teach']}\n- {p['name']} teaches: {s['learn']}\n"
                        "Use Markdown with exactly these sections:\n"
                        "**Icebreaker (10 seconds)**: one friendly line.\n"
                        f"**Round 1 (7 min): {ss.profile['name']} teaches {s['teach']}**: 3 numbered steps with minutes, one thing to show, one quick check question.\n"
                        f"**Round 2 (7 min): {p['name']} teaches {s['learn']}**: what {ss.profile['name']} should have ready, 3 good questions to ask, one mini challenge.\n"
                        "**Wrap-up (1 min)**: one tip each to practice and a kudos suggestion.\n"
                        "Beginner friendly, concrete, under 250 words.", max_tokens=700)
                if err:
                    st.error(err)
                else:
                    ss.plans[s["id"]] = text
            show_timer = c2.toggle("Show 15-minute timer", key=f"timer_{s['id']}")
            if s["id"] in ss.plans:
                st.markdown(ss.plans[s["id"]])
            if show_timer:
                timer_component(ss.profile["name"].split()[0] or "You", first, s["teach"], s["learn"])
            kudos = st.multiselect(f"Kudos for {first} (up to 2, +10 XP each)", KUDOS, max_selections=2, key=f"kudos_{s['id']}")
            f1, f2 = st.columns(2)
            if f1.button("Finish and collect card", key=f"fin_{s['id']}"):
                before = unlocked_names()
                s["status"], s["kudos"] = "done", list(kudos)
                new = sorted(unlocked_names() - before)
                gained = 50 + 10 * len(kudos)
                ss.flash = f"{p['name']}'s card collected. +{gained} XP." + (f" New badge: {', '.join(new)}." if new else "")
                ss.balloons = bool(new)
                st.rerun()
            if f2.button("Cancel session", key=f"can_{s['id']}"):
                ss.sessions = [x for x in ss.sessions if x["id"] != s["id"]]
                ss.flash = "Session cancelled."
                st.rerun()

    st.subheader("Finished")
    done = [s for s in ss.sessions if s["status"] == "done"][::-1]
    if not done:
        st.caption("Finished swaps show up here.")
    for s in done:
        with st.container(border=True):
            st.markdown(session_row_html(s), unsafe_allow_html=True)
            st.caption(f"+{50 + 10 * len(s['kudos'])} XP")

# ---- My card ----
with tab_card:
    left, right = st.columns([1, 1.4])
    with left:
        st.markdown(my_card_html(), unsafe_allow_html=True)
        st.caption("Edit your card in the sidebar. Hover it to see the shine.")
    with right:
        st.subheader("Not sure what to teach?")
        interests = st.text_input("What are you into?", placeholder="gaming, drawing, football, cooking", key="interests")
        if st.button("Suggest skills I could teach in 15 minutes", disabled=not interests.strip()):
            with st.spinner("Thinking"):
                text, err = ask(
                    f"A teenager is into: {interests}. Suggest 5 skills they could teach a beginner in a 7-minute mini lesson. "
                    "For each give the skill name, a one-line lesson idea, and what the learner will be able to do afterwards. "
                    "Keep it short.", max_tokens=500)
            st.error(err) if err else st.markdown(text)

# ---- Binder ----
with tab_binder:
    S = stats()
    st.subheader(f"Level {S['lvl']}: {LEVELS[min(S['lvl'] - 1, 3)]}")
    st.progress(S["into"] / 150, text=f"{S['into']} / 150 XP to level {S['lvl'] + 1}")

    st.subheader("Badges")
    cards = []
    for b in BADGES:
        val = min(b["val"](S), b["goal"])
        on = b["val"](S) >= b["goal"]
        cards.append(
            f'<div class="badge{" on" if on else ""}">{medal_html(b, on)}<div><h4>{esc(b["name"])}</h4><p>{esc(b["desc"])}</p>'
            f'<div class="pbar"><i style="width:{val / b["goal"] * 100:.0f}%"></i></div>'
            f'<p style="font-family:DM Mono,monospace;font-size:11px;margin-top:5px">{val} / {b["goal"]}{" unlocked" if on else ""}</p></div></div>')
    st.markdown(f'<div class="badges">{"".join(cards)}</div>', unsafe_allow_html=True)

    st.subheader("Card collection")
    cols = st.columns(4)
    for i, p in enumerate(PEOPLE):
        with cols[i % 4]:
            if p["id"] in S["collected"]:
                st.markdown(card_html(p, mini=True), unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="slot"><b>?</b><span>Swap with {esc(p["name"].split()[0])} to collect this card</span></div>',
                            unsafe_allow_html=True)

# ---- Swap Coach ----
with tab_coach:
    st.subheader("Swap Coach")
    st.caption("Ask for help picking a skill, planning a lesson, or breaking the ice.")
    for m in ss.coach:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    q = st.chat_input("Ask Swap Coach anything about your swaps")
    if q:
        ss.coach.append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(q)
        context = (f"The user's card: name {ss.profile['name']}, teaches {ss.profile['teaches']}, "
                   f"wants to learn {ss.profile['wants']}. Swaps finished: {stats()['done']}.")
        msgs = [{"role": "system", "content": SYSTEM_PROMPT + " " + context}] + ss.coach[-8:]
        with st.chat_message("assistant"):
            with st.spinner("Thinking"):
                text, err = llm(msgs, max_tokens=600)
            if err:
                st.error(err)
                ss.coach.pop()
            else:
                st.markdown(text)
                ss.coach.append({"role": "assistant", "content": text})

st.caption("Prototype. The people and progress shown here are sample data. Swaps should happen in a moderated group room, and personal details stay private.")
