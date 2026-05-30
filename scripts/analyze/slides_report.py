#!/usr/bin/env python3
"""把 report payload 渲染成"叙事版滑动年报"——单文件、零依赖、零联网的 HTML。

UI 来源：docs/demo/slides.html（frontend-slides 风格：整屏 scroll-snap、入场动画、
进度条、导航点）。这里把那份手写 demo 的 CSS/JS 逐字搬入，9 个 slide 的硬编码数据
全部换成 payload 字段。和 share_card.py 一样是纯 Python 模板渲染，没有 npm / React
构建，产物是自包含单文件 HTML。

只负责展示层；整条分析链路（export / features / daily / customer / emotion /
mbti / speech / social / report_data）一行都不动。
"""

import html


EMOTION_ROWS = [
    ("positive", "积极", "linear-gradient(90deg,var(--teal),#0c9488)"),
    ("neutral", "平稳", "linear-gradient(90deg,var(--sun),var(--tangerine))"),
    ("negative", "消极", "var(--berry)"),
    ("anxious", "焦虑", "linear-gradient(90deg,var(--sun),var(--coral))"),
    ("angry", "愤怒", "linear-gradient(90deg,var(--coral),var(--berry))"),
]

# 每个 MBTI 字母对应的一句通俗描述，用于维度条右侧标签。
LETTER_DESC = {
    "E": "外向", "I": "内向",
    "S": "务实", "N": "直觉",
    "T": "理性", "F": "重情",
    "J": "计划", "P": "随性",
}

# 待跟进标签 -> pill 样式类
FOLLOWUP_TAG_CLASS = {
    "商业": "sand",
    "报价": "sand",
    "负面": "neg",
}


def esc(value):
    return html.escape(str(value if value is not None else ""))


def _safe_pct(value, total, floor=2.0):
    """value 占 total 的百分比，最小给 floor 保证条形可见。"""
    if not total:
        return floor
    pct = value / total * 100
    return max(pct, floor) if value else floor


def _num(value):
    """尽量用整数显示，避免 11.0 这种尾巴。"""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


# ---------------------------------------------------------------------------
# CSS / JS：逐字来自 docs/demo/slides.html，是这次选定的 UI，不要改动。
# ---------------------------------------------------------------------------
SLIDES_CSS = """
:root {
  --paper: #fdf5ea;
  --paper-2: #fbeede;
  --ink: #2b231d;
  --ink-soft: #6f6157;
  --ink-faint: #ab9c8d;
  --coral: #ff5c39;
  --tangerine: #f99421;
  --berry: #e8478c;
  --teal: #11b3a3;
  --sun: #ffc23d;
  --line: #ecdcc8;
  --card: #fffaf2;

  --font-serif: "Noto Serif SC", "Fraunces", serif;
  --font-sans: "Noto Sans SC", system-ui, sans-serif;
  --font-num: "Fraunces", "Noto Serif SC", serif;

  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-normal: 0.7s;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}

html, body { height: 100%; overflow-x: hidden; }
html { scroll-snap-type: y mandatory; scroll-behavior: smooth; }
.slide {
  width: 100vw; height: 100vh; height: 100dvh; overflow: hidden;
  scroll-snap-align: start; display: flex; flex-direction: column; position: relative;
}
.slide:nth-child(even) { background: var(--paper-2); }
.slide-content {
  flex: 1; display: flex; flex-direction: column; justify-content: center;
  max-height: 100%; overflow: hidden; padding: var(--slide-padding);
}
:root {
  --title-size: clamp(1.5rem, 5vw, 4rem);
  --h2-size: clamp(1.25rem, 3.5vw, 2.5rem);
  --h3-size: clamp(1rem, 2.5vw, 1.75rem);
  --body-size: clamp(0.75rem, 1.5vw, 1.125rem);
  --small-size: clamp(0.65rem, 1vw, 0.875rem);
  --slide-padding: clamp(1.25rem, 5vw, 5rem);
  --content-gap: clamp(0.5rem, 2vw, 2rem);
  --element-gap: clamp(0.25rem, 1vw, 1rem);
}
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 250px), 1fr)); gap: clamp(0.5rem, 1.5vw, 1rem); }
@media (max-height: 700px) { :root { --slide-padding: clamp(0.75rem, 3vw, 2rem); --title-size: clamp(1.25rem, 4.5vw, 2.5rem); --h2-size: clamp(1rem, 3vw, 1.75rem); } }
@media (max-height: 600px) { :root { --slide-padding: clamp(0.5rem, 2.5vw, 1.5rem); --title-size: clamp(1.1rem, 4vw, 2rem); --body-size: clamp(0.7rem, 1.2vw, 0.95rem); } .nav-dots, .keyboard-hint, .decorative { display: none; } }
@media (max-height: 500px) { :root { --slide-padding: clamp(0.4rem, 2vw, 1rem); --title-size: clamp(1rem, 3.5vw, 1.5rem); } }
@media (max-width: 600px) { :root { --title-size: clamp(1.4rem, 8vw, 2.5rem); } .grid { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.2s !important; } html { scroll-behavior: auto; } }

.glow { position: absolute; border-radius: 50%; filter: blur(70px); opacity: 0.38; pointer-events: none; z-index: 0; }
.glow.coral { background: radial-gradient(circle, var(--coral), transparent 70%); }
.glow.teal  { background: radial-gradient(circle, var(--teal), transparent 70%); }
.glow.berry { background: radial-gradient(circle, var(--berry), transparent 70%); }
.glow.sun   { background: radial-gradient(circle, var(--sun), transparent 70%); }
.slide-content > * { position: relative; z-index: 1; }

.accent-rule { width: clamp(40px, 6vw, 80px); height: 4px; background: var(--coral); border-radius: 4px; transform: rotate(-1.5deg); }

.reveal { opacity: 0; transform: translateY(26px); transition: opacity var(--duration-normal) var(--ease-out-expo), transform var(--duration-normal) var(--ease-out-expo); }
.slide.visible .reveal { opacity: 1; transform: translateY(0); }
.slide.visible .reveal:nth-child(1) { transition-delay: .05s; }
.slide.visible .reveal:nth-child(2) { transition-delay: .15s; }
.slide.visible .reveal:nth-child(3) { transition-delay: .25s; }
.slide.visible .reveal:nth-child(4) { transition-delay: .35s; }
.slide.visible .reveal:nth-child(5) { transition-delay: .45s; }
.slide.visible .reveal:nth-child(6) { transition-delay: .55s; }

.progress-bar { position: fixed; top: 0; left: 0; height: 4px; width: 0; background: linear-gradient(90deg, var(--coral), var(--berry), var(--sun)); z-index: 100; transition: width .2s ease; }

.nav-dots { position: fixed; right: clamp(12px, 2vw, 28px); top: 50%; transform: translateY(-50%); display: flex; flex-direction: column; gap: 12px; z-index: 100; }
.nav-dots button { width: 10px; height: 10px; border-radius: 50%; border: 1.5px solid var(--ink-faint); background: transparent; cursor: pointer; padding: 0; transition: all .3s ease; }
.nav-dots button.active { background: var(--coral); border-color: var(--coral); transform: scale(1.4); }

.keyboard-hint { position: fixed; bottom: clamp(10px, 2vh, 22px); left: 50%; transform: translateX(-50%); font-size: var(--small-size); color: var(--ink-faint); z-index: 100; letter-spacing: .12em; }

.kicker { display: inline-flex; align-items: center; gap: .5rem; font-size: var(--small-size); letter-spacing: .28em; text-transform: uppercase; color: var(--coral); font-weight: 700; margin-bottom: clamp(.6rem, 1.5vh, 1.2rem); }
h1, h2 { font-family: var(--font-serif); font-weight: 900; line-height: 1.08; letter-spacing: .01em; color: var(--ink); }
h1 { font-size: clamp(2.2rem, 7vw, 5.2rem); }
h2 { font-size: var(--h2-size); margin-bottom: clamp(.8rem, 2vh, 1.6rem); }
.lead { font-size: var(--body-size); color: var(--ink-soft); line-height: 1.7; max-width: 40ch; }
.disclaimer { font-size: var(--small-size); color: var(--ink-faint); margin-top: clamp(.8rem,2vh,1.6rem); }

.num { font-family: var(--font-num); font-weight: 900; line-height: .9; color: var(--ink); }

.stats-row { display: flex; flex-wrap: wrap; gap: clamp(1rem, 4vw, 3.5rem); margin-top: clamp(1rem,3vh,2rem); }
.stat .num { font-size: clamp(2.6rem, 8vw, 6rem); }
.stat .num .unit { font-family: var(--font-sans); font-size: .26em; color: var(--ink-soft); margin-left: .25em; font-weight: 500; }
.stat .cap { font-size: var(--small-size); color: var(--ink-soft); letter-spacing: .08em; margin-top: .3rem; }
.stat .num.coral { color: var(--coral); }
.stat .num.teal { color: var(--teal); }
.stat .num.berry { color: var(--berry); }

.stack-bar { display: flex; height: clamp(48px, 9vh, 84px); border-radius: 16px; overflow: hidden; box-shadow: 0 6px 24px rgba(255,92,57,.12); margin: clamp(1rem,3vh,2rem) 0; }
.stack-bar .seg { display: flex; flex-direction: column; justify-content: center; padding: 0 clamp(.8rem,2vw,1.6rem); color: #fff; width: 0; transition: width 1.1s var(--ease-out-expo); }
.slide.visible .stack-bar .seg { width: var(--w); }
.seg.private { background: linear-gradient(135deg, var(--coral), var(--tangerine)); }
.seg.group { background: linear-gradient(135deg, var(--teal), #0c9488); }
.seg b { font-family: var(--font-num); font-size: clamp(1.3rem,3vw,2rem); line-height: 1; }
.seg span { font-size: var(--small-size); font-weight: 500; }
.mini-stats { display: flex; gap: clamp(1.5rem,5vw,4rem); }
.mini-stats .num { font-size: clamp(1.8rem,4vw,3rem); }

.mbti-type { font-family: var(--font-num); font-weight: 900; font-size: clamp(4rem, 16vw, 11rem); letter-spacing: .04em; line-height: .9; background: linear-gradient(120deg, var(--coral), var(--berry) 60%, var(--tangerine)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.dims { display: flex; flex-direction: column; gap: clamp(.5rem,1.6vh,1.1rem); max-width: 560px; width: 100%; }
.dim { display: grid; grid-template-columns: clamp(34px,5vw,52px) 1fr auto; align-items: center; gap: clamp(.6rem,2vw,1.2rem); }
.dim .letter { font-family: var(--font-num); font-weight: 900; font-size: clamp(1.6rem,4vw,2.6rem); color: var(--coral); }
.dim .track { height: 8px; background: var(--line); border-radius: 6px; overflow: hidden; }
.dim .fill { height: 100%; width: 0; background: linear-gradient(90deg, var(--tangerine), var(--coral)); border-radius: 6px; transition: width 1.1s var(--ease-out-expo); }
.slide.visible .dim .fill { width: var(--w); }
.dim .label { font-size: var(--small-size); color: var(--ink-soft); white-space: nowrap; }

.emo-list { display: flex; flex-direction: column; gap: clamp(.6rem,1.8vh,1.2rem); max-width: 560px; width: 100%; }
.emo { display: grid; grid-template-columns: clamp(56px,8vw,84px) 1fr clamp(34px,5vw,48px); align-items: center; gap: clamp(.6rem,2vw,1.2rem); font-size: var(--body-size); }
.emo .track { height: 12px; background: var(--line); border-radius: 6px; overflow: hidden; }
.emo .fill { height: 100%; width: 0; border-radius: 6px; transition: width 1.2s var(--ease-out-expo); }
.slide.visible .emo .fill { width: var(--w); }
.emo .v { font-family: var(--font-num); font-weight: 900; text-align: right; color: var(--ink-soft); }

.terms { display: flex; flex-wrap: wrap; gap: clamp(.5rem,1.5vw,1rem); max-width: 760px; align-items: center; }
.term { border: 2px solid var(--ink); border-radius: 999px; padding: clamp(.4rem,1.2vh,.8rem) clamp(.9rem,2.2vw,1.5rem); background: var(--card); color: var(--ink); display: flex; align-items: baseline; gap: .5rem; box-shadow: 3px 3px 0 var(--coral); }
.term .c { font-family: var(--font-num); font-weight: 900; color: var(--coral); font-size: 1.1em; }
.term.lg { font-size: clamp(1.1rem,2.6vw,1.7rem); }
.term.lg:nth-child(2) { box-shadow: 3px 3px 0 var(--berry); } .term.lg:nth-child(2) .c { color: var(--berry); }
.term.md { font-size: clamp(.95rem,2vw,1.3rem); box-shadow: 3px 3px 0 var(--teal); } .term.md .c { color: var(--teal); }
.term.sm { font-size: clamp(.8rem,1.6vw,1rem); box-shadow: 2px 2px 0 var(--sun); border-color: var(--ink-soft); } .term.sm .c { color: var(--tangerine); }

.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: clamp(1.5rem,5vw,4rem); max-width: 900px; }
@media (max-width: 720px) { .two-col { grid-template-columns: 1fr; } }
.rank { display: flex; flex-direction: column; gap: clamp(.45rem,1.4vh,.9rem); }
.rank .row { display: grid; grid-template-columns: 1fr auto; gap: .5rem; align-items: center; }
.rank .nm { font-size: var(--body-size); }
.rank .track { grid-column: 1 / -1; height: 7px; background: var(--line); border-radius: 6px; overflow: hidden; }
.rank .fill { height: 100%; width: 0; background: var(--coral); border-radius: 6px; transition: width 1s var(--ease-out-expo); }
.slide.visible .rank .fill { width: var(--w); }
.rank .v { font-family: var(--font-num); font-weight: 900; color: var(--ink-soft); }
.col-h { font-size: var(--small-size); letter-spacing: .18em; text-transform: uppercase; font-weight: 700; color: var(--teal); margin-bottom: clamp(.6rem,1.6vh,1.1rem); }

.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: clamp(.7rem,2vw,1.4rem); max-width: 1000px; }
@media (max-width: 820px) { .cards { grid-template-columns: 1fr; } .card-follow:nth-child(n+3){ display:none; } }
.card-follow { border-radius: 18px; padding: clamp(1rem,2.5vw,1.6rem); background: var(--card); border: 1px solid var(--line); box-shadow: 0 8px 28px rgba(43,35,29,.06); display: flex; flex-direction: column; gap: .7rem; border-top: 5px solid var(--coral); }
.card-follow:nth-child(2) { border-top-color: var(--tangerine); }
.card-follow:nth-child(3) { border-top-color: var(--berry); }
.card-follow .who { font-family: var(--font-serif); font-weight: 900; font-size: clamp(1.05rem,2.4vw,1.5rem); }
.card-follow .quote { font-size: var(--body-size); color: var(--ink-soft); line-height: 1.6; flex: 1; }
.tags { display: flex; flex-wrap: wrap; gap: .4rem; }
.tag { font-size: var(--small-size); padding: .2rem .6rem; border-radius: 6px; background: rgba(255,92,57,.12); color: var(--coral); font-weight: 500; }
.tag.neg { background: rgba(232,71,140,.14); color: var(--berry); }
.tag.sand { background: rgba(249,148,33,.16); color: var(--tangerine); }
.score { font-family: var(--font-num); font-weight: 900; color: var(--coral); font-size: clamp(1.2rem,2.6vw,1.7rem); }

.btn-row { display: flex; gap: clamp(.6rem,2vw,1rem); flex-wrap: wrap; margin-top: clamp(1rem,3vh,2rem); }
.btn { text-decoration: none; padding: clamp(.6rem,1.4vh,.9rem) clamp(1rem,2.4vw,1.6rem); border-radius: 12px; font-weight: 700; font-size: var(--body-size); }
.btn.solid { background: var(--coral); color: #fff; box-shadow: 0 8px 20px rgba(255,92,57,.3); }
.btn.ghost { border: 2px solid var(--ink); color: var(--ink); }
.brand-foot { font-family: var(--font-num); font-weight: 900; font-size: clamp(1.1rem,2.4vw,1.6rem); color: var(--ink); }
.brand-foot span { color: var(--coral); }
"""

SLIDES_JS = """
class SlideDeck {
  constructor() {
    this.slides = Array.from(document.querySelectorAll('.slide'));
    this.current = 0;
    this.locked = false;
    this.observe();
    this.buildDots();
    this.keys();
    this.wheel();
    this.touch();
    this.progress();
  }

  observe() {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting && e.intersectionRatio > 0.55) {
          e.target.classList.add('visible');
          this.current = this.slides.indexOf(e.target);
          this.syncDots();
          this.countUp(e.target);
        }
      });
    }, { threshold: [0.55] });
    this.slides.forEach((s) => io.observe(s));
  }

  countUp(slide) {
    slide.querySelectorAll('.count').forEach((el) => {
      if (el.dataset.done) return;
      el.dataset.done = '1';
      const target = +el.dataset.target;
      const dur = 1000; const t0 = performance.now();
      const tick = (t) => {
        const p = Math.min((t - t0) / dur, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(target * eased).toLocaleString();
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }

  buildDots() {
    this.dotsWrap = document.getElementById('navDots');
    this.dotsWrap.innerHTML = '';
    this.slides.forEach((s, i) => {
      const b = document.createElement('button');
      b.setAttribute('aria-label', s.dataset.label || ('第' + (i + 1) + '屏'));
      b.addEventListener('click', () => this.go(i));
      this.dotsWrap.appendChild(b);
    });
    this.dots = Array.from(this.dotsWrap.children);
    this.syncDots();
  }
  syncDots() { if (this.dots) this.dots.forEach((d, i) => d.classList.toggle('active', i === this.current)); }

  go(i) {
    i = Math.max(0, Math.min(this.slides.length - 1, i));
    this.slides[i].scrollIntoView({ behavior: 'smooth' });
  }

  keys() {
    document.addEventListener('keydown', (e) => {
      if (['ArrowDown', 'PageDown', ' '].includes(e.key)) { e.preventDefault(); this.go(this.current + 1); }
      if (['ArrowUp', 'PageUp'].includes(e.key)) { e.preventDefault(); this.go(this.current - 1); }
      if (e.key === 'Home') this.go(0);
      if (e.key === 'End') this.go(this.slides.length - 1);
    });
  }

  wheel() {
    window.addEventListener('wheel', (e) => {
      if (this.locked || Math.abs(e.deltaY) < 18) return;
      this.locked = true;
      this.go(this.current + (e.deltaY > 0 ? 1 : -1));
      setTimeout(() => (this.locked = false), 720);
    }, { passive: true });
  }

  touch() {
    let y0 = null;
    window.addEventListener('touchstart', (e) => (y0 = e.touches[0].clientY), { passive: true });
    window.addEventListener('touchend', (e) => {
      if (y0 === null) return;
      const dy = y0 - e.changedTouches[0].clientY;
      if (Math.abs(dy) > 50) this.go(this.current + (dy > 0 ? 1 : -1));
      y0 = null;
    }, { passive: true });
  }

  progress() {
    const bar = document.getElementById('progressBar');
    const update = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      bar.style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + '%';
    };
    window.addEventListener('scroll', update, { passive: true });
    update();
  }
}

new SlideDeck();
"""


# ---------------------------------------------------------------------------
# 各屏 body：数据驱动
# ---------------------------------------------------------------------------
def _slide_cover(overview):
    span = _num(overview.get("date_span_days", 0)) or 0
    return f"""
<section class="slide" data-label="封面">
  <div class="glow coral" style="width:46vw;height:46vw;top:-12vw;right:-8vw;"></div>
  <div class="glow sun" style="width:34vw;height:34vw;bottom:-10vw;left:-6vw;"></div>
  <div class="slide-content">
    <div class="kicker reveal">WeChat Insight · 关系年报</div>
    <h1 class="reveal">我的微信<br/>关系画像</h1>
    <div class="reveal" style="margin:clamp(1rem,3vh,1.8rem) 0;"><div class="accent-rule"></div></div>
    <p class="lead reveal">把近 {esc(span)} 天的聊天记录，读成一份关于关系、商机、情绪与表达习惯的画像。全程在本机完成，聊天内容不出本机。</p>
    <p class="disclaimer reveal">MBTI / 情绪 / 口头禅均为启发式分析，仅供参考</p>
  </div>
</section>"""


def _slide_overview(overview):
    total = _num(overview.get("total_messages", 0)) or 0
    chats = _num(overview.get("active_chat_count", 0)) or 0
    latency = overview.get("median_response_latency_minutes")
    business = _num(overview.get("business_contact_count", 0)) or 0
    stats = [
        f'<div class="stat reveal"><div class="num coral"><span class="count" data-target="{esc(total)}">0</span></div><div class="cap">条消息</div></div>',
        f'<div class="stat reveal"><div class="num teal"><span class="count" data-target="{esc(chats)}">0</span></div><div class="cap">个活跃会话</div></div>',
    ]
    if latency is not None:
        stats.append(
            f'<div class="stat reveal"><div class="num berry"><span class="count" data-target="{esc(_num(latency))}">0</span><span class="unit">分钟</span></div><div class="cap">中位回复时延</div></div>'
        )
    stats.append(
        f'<div class="stat reveal"><div class="num"><span class="count" data-target="{esc(business)}">0</span></div><div class="cap">个商机联系人</div></div>'
    )
    return f"""
<section class="slide" data-label="概览">
  <div class="glow teal" style="width:40vw;height:40vw;top:30%;left:-14vw;"></div>
  <div class="slide-content">
    <div class="kicker reveal">这段时间，发生了什么</div>
    <h2 class="reveal">一眼看完整体节奏</h2>
    <div class="stats-row">
      {''.join(stats)}
    </div>
  </div>
</section>"""


def _slide_structure(overview):
    private = overview.get("private_message_count", 0) or 0
    group = overview.get("group_message_count", 0) or 0
    total = overview.get("total_messages", 0) or 0
    text = overview.get("text_messages", 0) or 0
    avg_len = overview.get("avg_message_length", 0) or 0
    pm_total = private + group
    private_w = _safe_pct(private, pm_total, floor=0.0)
    group_w = _safe_pct(group, pm_total, floor=0.0)
    text_pct = (text / total * 100) if total else 0
    return f"""
<section class="slide" data-label="结构">
  <div class="glow coral" style="width:36vw;height:36vw;top:-10vw;right:-8vw;"></div>
  <div class="slide-content">
    <div class="kicker reveal">消息结构</div>
    <h2 class="reveal">私聊为主，群聊为辅</h2>
    <div class="stack-bar reveal">
      <div class="seg private" style="--w:{private_w:.1f}%"><b>{esc(private)}</b><span>私聊消息</span></div>
      <div class="seg group" style="--w:{group_w:.1f}%"><b>{esc(group)}</b><span>群聊消息</span></div>
    </div>
    <div class="mini-stats reveal">
      <div><div class="num coral">{text_pct:.1f}<span class="unit" style="font-size:.4em;color:var(--ink-soft)">%</span></div><div class="cap">是纯文本消息</div></div>
      <div><div class="num teal">{_num(round(avg_len, 1))}<span class="unit" style="font-size:.4em;color:var(--ink-soft)">字</span></div><div class="cap">平均每条长度</div></div>
    </div>
  </div>
</section>"""


def _slide_mbti(overview, mbti):
    mbti_type = overview.get("mbti_type") or mbti.get("mbti_type") or "----"
    dims = mbti.get("dimensions", {}) or {}
    rows = ""
    for key in ("EI", "SN", "TF", "JP"):
        dim = dims.get(key)
        if not dim:
            continue
        letter = dim.get("letter", "-")
        label = dim.get("label", "")
        desc = LETTER_DESC.get(letter, "")
        width = round((dim.get("confidence", 0) or 0) * 100)
        suffix = f"{esc(label)} · {esc(desc)}" if desc else esc(label)
        rows += (
            f'<div class="dim"><span class="letter">{esc(letter)}</span>'
            f'<div class="track"><div class="fill" style="--w:{width}%"></div></div>'
            f'<span class="label">{suffix}</span></div>'
        )
    if not rows:
        rows = '<div class="label">数据不足</div>'
    return f"""
<section class="slide" data-label="人格">
  <div class="glow berry" style="width:42vw;height:42vw;bottom:-14vw;right:-10vw;"></div>
  <div class="slide-content">
    <div class="kicker reveal">人格推测 · 启发式</div>
    <div style="display:flex;flex-wrap:wrap;align-items:center;gap:clamp(1.5rem,5vw,4rem);">
      <div class="reveal" style="flex:0 0 auto;">
        <div class="mbti-type">{esc(mbti_type)}</div>
        <div class="cap" style="color:var(--ink-soft);margin-top:.4rem;">基于你发出的消息反推</div>
      </div>
      <div class="dims reveal" style="flex:1 1 320px;">
        {rows}
      </div>
    </div>
    <p class="disclaimer reveal">条形长度表示该维度的判断置信度。启发式推测，仅供娱乐参考。</p>
  </div>
</section>"""


def _slide_emotion(emotion):
    dist = emotion.get("emotion_distribution", {}) or {}
    total = sum(v or 0 for v in dist.values())
    sample = emotion.get("total_text_messages", total) or total
    if total == 0:
        body = '<p class="lead reveal">这段时间的文本太少，还看不出情绪结构。</p>'
        footer = ""
    else:
        rows = ""
        for key, label, color in EMOTION_ROWS:
            value = dist.get(key, 0) or 0
            if value == 0 and key in ("anxious", "angry"):
                continue
            width = _safe_pct(value, total)
            rows += (
                f'<div class="emo reveal"><span>{esc(label)}</span>'
                f'<div class="track"><div class="fill" style="--w:{width:.1f}%;background:{color}"></div></div>'
                f'<span class="v">{esc(value)}</span></div>'
            )
        body = f'<div class="emo-list">{rows}</div>'
        footer = f'<p class="disclaimer reveal">基于聊天文本的统计规则推测，不是心理测评。共分析 {esc(sample)} 条文本。</p>'
    return f"""
<section class="slide" data-label="情绪">
  <div class="glow teal" style="width:38vw;height:38vw;top:-12vw;left:-10vw;"></div>
  <div class="slide-content">
    <div class="kicker reveal">情绪底色</div>
    <h2 class="reveal">表达里的情绪结构</h2>
    {body}
    {footer}
  </div>
</section>"""


def _slide_phrases(speech):
    terms = (speech.get("top_terms") or [])[:6]
    size_classes = ["lg", "lg", "md", "md", "sm", "sm"]
    pills = ""
    for idx, term in enumerate(terms):
        text = term.get("text", "")
        count = term.get("count", 0)
        if not text:
            continue
        cls = size_classes[idx] if idx < len(size_classes) else "sm"
        pills += f'<span class="term {cls}">{esc(text)} <span class="c">×{esc(count)}</span></span>'
    if not pills:
        pills = '<span class="term lg">暂无明显高频表达</span>'
    return f"""
<section class="slide" data-label="口头禅">
  <div class="glow sun" style="width:40vw;height:40vw;bottom:-12vw;right:-8vw;"></div>
  <div class="slide-content">
    <div class="kicker reveal">语言风格</div>
    <h2 class="reveal">你最爱说的几句话</h2>
    <div class="terms reveal">
      {pills}
    </div>
    <p class="disclaimer reveal">从你发出的高频短句里提取，越大代表用得越多。</p>
  </div>
</section>"""


def _rank_rows(items, fill_style=""):
    """items: [(name, value), ...]，按 value 归一化条宽。"""
    if not items:
        return '<div class="row"><span class="nm">暂无数据</span></div>'
    top = max((v or 0) for _, v in items) or 1
    out = ""
    for name, value in items:
        width = round((value or 0) / top * 100)
        out += (
            f'<div class="row"><span class="nm">{esc(name)}</span>'
            f'<span class="v">{esc(value)}</span>'
            f'<div class="track"><div class="fill" style="--w:{width}%{fill_style}"></div></div></div>'
        )
    return out


def _slide_relationship(daily):
    contacts = [(n, c) for n, c in (daily.get("top_contacts") or [])][:5]
    hours = [(f"{int(h):02d}:00", c) for h, c in (daily.get("top_hours") or [])][:5]
    return f"""
<section class="slide" data-label="关系">
  <div class="glow coral" style="width:38vw;height:38vw;top:20%;right:-12vw;"></div>
  <div class="slide-content">
    <div class="kicker reveal">关系与节奏</div>
    <h2 class="reveal">和谁聊得多，几点最活跃</h2>
    <div class="two-col">
      <div class="reveal">
        <div class="col-h">最常聊的人</div>
        <div class="rank">
          {_rank_rows(contacts)}
        </div>
      </div>
      <div class="reveal">
        <div class="col-h">最活跃时段</div>
        <div class="rank">
          {_rank_rows(hours, fill_style=";background:var(--teal)")}
        </div>
      </div>
    </div>
  </div>
</section>"""


def _slide_followups(customer):
    all_pending = customer.get("pending_followups") or []
    pending = all_pending[:3]
    total = len(all_pending)
    cards = ""
    for item in pending:
        who = item.get("contact_name", "")
        score = item.get("opportunity_score", 0)
        follow = item.get("pending_followup", {}) or {}
        quote = follow.get("content", "")
        labels = follow.get("labels", []) or []
        tags = "".join(
            f'<span class="tag {FOLLOWUP_TAG_CLASS.get(lbl, "")}">{esc(lbl)}</span>'
            for lbl in labels
        )
        cards += (
            '<div class="card-follow reveal">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span class="who">{esc(who)}</span><span class="score">{esc(score)}</span></div>'
            f'<p class="quote">"{esc(quote)}"</p>'
            f'<div class="tags">{tags}</div>'
            "</div>"
        )
    if not cards:
        title = "暂时没有待跟进的人"
        cards = '<div class="card-follow reveal"><p class="quote">这段时间没有检测到明显的待跟进信号。</p></div>'
    elif total > len(pending):
        title = f"{total} 个人正等你回话，先看这 {len(pending)} 个"
    else:
        title = f"{total} 个人，正等你回话"
    return f"""
<section class="slide" data-label="待跟进">
  <div class="glow berry" style="width:44vw;height:44vw;top:-14vw;left:-10vw;"></div>
  <div class="slide-content">
    <div class="kicker reveal">待跟进客户 · 别让机会凉掉</div>
    <h2 class="reveal">{esc(title)}</h2>
    <div class="cards">
      {cards}
    </div>
    <p class="disclaimer reveal">分数 = 机会强度，由聊天里的报价/商机/待办等信号加权得出。</p>
  </div>
</section>"""


def _slide_cta():
    return """
<section class="slide" data-label="开始">
  <div class="glow coral" style="width:48vw;height:48vw;top:-10vw;right:-12vw;"></div>
  <div class="glow sun" style="width:32vw;height:32vw;bottom:-8vw;left:-6vw;"></div>
  <div class="slide-content">
    <div class="kicker reveal">轮到你了</div>
    <h1 class="reveal" style="font-size:clamp(1.9rem,6vw,4.2rem);">生成你自己的<br/>微信关系画像</h1>
    <p class="lead reveal" style="margin-top:clamp(.8rem,2vh,1.4rem);">一行命令，全程本地、零联网。你的聊天内容永远只待在自己的电脑里。</p>
    <div class="btn-row reveal">
      <a class="btn ghost" href="https://github.com/caigee-cmd/wechat-insight">GitHub 仓库</a>
    </div>
    <div class="reveal" style="margin-top:clamp(1.4rem,4vh,2.6rem);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;">
      <div class="brand-foot">WeChat <span>Insight</span></div>
      <div class="disclaimer" style="margin:0;">MBTI / 情绪 / 口头禅均为启发式分析，仅供参考</div>
    </div>
  </div>
</section>"""


def build_slides_html(payload):
    overview = payload.get("overview", {}) or {}
    sections = payload.get("sections", {}) or {}
    mbti = sections.get("mbti", {}) or {}
    emotion = sections.get("emotion", {}) or {}
    speech = sections.get("speech", {}) or {}
    daily = sections.get("daily", {}) or {}
    customer = sections.get("customer", {}) or {}

    slides = "".join([
        _slide_cover(overview),
        _slide_overview(overview),
        _slide_structure(overview),
        _slide_mbti(overview, mbti),
        _slide_emotion(emotion),
        _slide_phrases(speech),
        _slide_relationship(daily),
        _slide_followups(customer),
        _slide_cta(),
    ])

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>我的微信关系画像 · WeChat Insight</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,700;0,9..144,900;1,9..144,600&family=Noto+Sans+SC:wght@300;400;500;700&family=Noto+Serif+SC:wght@500;700;900&display=swap" rel="stylesheet" />
<style>{SLIDES_CSS}</style>
</head>
<body>

<div class="progress-bar" id="progressBar"></div>
<nav class="nav-dots" id="navDots" aria-label="幻灯片导航"></nav>
<div class="keyboard-hint">滚动 / 方向键 翻页</div>
{slides}

<script>{SLIDES_JS}</script>
</body>
</html>
"""
