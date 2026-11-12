"""Build the website in docs/ from the templates here and the saved results.

    docs/index.html      from demo/site.html
    docs/explorer.html   from demo/template.html, with demo/kernel.js inlined
    docs/audit.html      from results/audit.json
    icons and the social card
"""
import html
import json
import os
import re
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DOCS = os.path.join(ROOT, "docs")
INK, PAPER, RED = "#171A2B", "#F6F1E7", "#C0271D"


def read(*p):
    with open(os.path.join(*p), encoding="utf-8") as fh:
        return fh.read()


def pages(pdf):
    out = subprocess.run(["pdfinfo", os.path.join(DOCS, pdf)], capture_output=True, text=True).stdout
    m = re.search(r"Pages:\s+(\d+)", out)
    return m.group(1) if m else "?"


def fill(template, values):
    def sub(m):
        if m.group(1) not in values:
            raise KeyError(f"no value for {{{{{m.group(1)}}}}}")
        return str(values[m.group(1)])
    return re.sub(r"\{\{(\w+)\}\}", sub, template)


AUDIT_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rakshasutra Audit</title>
<meta name="description" content="Every checkable number in the first draft of the Rakshasutra white paper, recomputed by open code, with a verdict for each.">
<meta name="theme-color" content="#F6F1E7"><link rel="icon" href="rs-icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400..700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{{CSS}}
header{padding:54px 0 30px}header h1{font-size:clamp(36px,5.6vw,60px)}header p{margin-top:16px;color:#33384F;font-size:18px}
.tally{display:flex;flex-wrap:wrap;gap:8px 28px;margin:26px 0 0;font:500 14px var(--mono)}.tally b{font:560 28px var(--serif);margin-right:6px}
.filters{display:flex;flex-wrap:wrap;gap:8px;margin:34px 0 18px}
.filters button{font:500 13px var(--mono);padding:8px 13px;border:1.5px solid var(--ink);background:transparent;color:var(--ink);cursor:pointer;border-radius:2px;min-height:38px}
.filters button[aria-pressed=true]{background:var(--ink);color:var(--paper)}
.claim{display:grid;grid-template-columns:46px minmax(0,1.5fr) minmax(0,1fr) minmax(0,1fr) 112px;gap:6px 20px;padding:16px 0;border-top:1px solid var(--rule);font-size:15.5px;align-items:baseline}
.claim .id{font:500 13px var(--mono);color:var(--muted)}.claim .sec{font:12px var(--mono);color:var(--muted);display:block;margin-top:2px}
.claim .v{font:14px var(--mono)}.claim .v::before{display:block;font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);margin-bottom:2px}
.claim .was::before{content:"First draft"}.claim .now::before{content:"This model"}
.claim .note{grid-column:2/-1;font-size:14.5px;color:#3A3F55;max-width:78ch}
.verdict{font:500 12px var(--mono);padding:3px 8px;border:1.5px solid;border-radius:3px;justify-self:start;white-space:nowrap}
.verdict.reproduced{color:#0B6B62;border-color:#0B6B62}.verdict.differs{color:#7A5800;border-color:#B8860B}
.verdict.fix{color:var(--red);border-color:var(--red)}.verdict.open{color:var(--muted);border-color:var(--muted)}
@media (max-width:760px){.claim{grid-template-columns:40px 1fr 1fr}.claim .what{grid-column:2/-1}.claim .was{grid-column:2}.claim .verdict{grid-column:2}}
main{padding-bottom:80px}
</style></head><body>
<nav><div class="wrap"><a class="brand" href="./"><span class="knot"></span>Rakshasutra</a>
<div class="links"><a href="./">Home</a><a href="explorer.html">Explorer</a><a href="audit.html" aria-current="page">Audit</a>
<a href="A-Thread-Through-the-Crowd-Rakshasutra.pdf">Book</a><a href="https://github.com/0xr4j/rakshasutra">GitHub</a></div></div></nav>
<header><div class="wrap"><span class="eyebrow">Reproduction audit</span>
<h1>{{AuditTotal}} claims, recomputed.</h1>
<p>The first draft of White Paper WP-01 described its results as empirical. Nothing had been measured. Each checkable number was recomputed by the code in the repository from the paper's own equations and parameters, and the revised paper and the book use the model's values. All values are calculated or simulated.</p>
<div class="tally"><span><b>{{AuditRep}}</b>reproduced</span><span><b>{{AuditDiff}}</b>differ</span><span><b>{{AuditFix}}</b>need a design fix</span><span><b>{{AuditOpen}}</b>open</span></div>
</div></header>
<main class="wrap">
<div class="filters" role="group" aria-label="Filter by verdict"><button data-f="all" aria-pressed="true">All</button><button data-f="reproduced" aria-pressed="false">Reproduced</button><button data-f="differs" aria-pressed="false">Differs</button><button data-f="fix" aria-pressed="false">Design fix</button><button data-f="open" aria-pressed="false">Open</button></div>
{{ROWS}}
</main>
<footer><div class="wrap"><p>Written by <code>demo/build_web.py</code> from <code>results/audit.json</code>. The same list is <a href="https://github.com/0xr4j/rakshasutra/blob/main/AUDIT.md">AUDIT.md</a>, and <code>rakshasutra audit</code> prints it.</p></div></footer>
<script>
document.querySelectorAll('.filters button').forEach(function(b){b.addEventListener('click',function(){
  document.querySelectorAll('.filters button').forEach(function(o){o.setAttribute('aria-pressed',o===b)});
  document.querySelectorAll('.claim').forEach(function(c){c.hidden=b.dataset.f!=='all'&&c.dataset.v!==b.dataset.f})})});
</script></body></html>
"""


def audit_rows(items):
    out = []
    for e in items:
        cls = "fix" if e["verdict"] == "design fix" else e["verdict"]
        note = f'<p class="note">{html.escape(e["note"])}</p>' if e["note"] else ""
        out.append(f'<div class="claim" data-v="{cls}"><span class="id">{e["id"]}</span>'
                   f'<span class="what">{html.escape(e["claim"])}<span class="sec">WP-01 section {html.escape(e["section"])}</span></span>'
                   f'<span class="v was">{html.escape(str(e["paper"]))}</span>'
                   f'<span class="v now">{html.escape(str(e["model"]))} {html.escape(e["unit"])}</span>'
                   f'<span class="verdict {cls}">{e["verdict"]}</span>{note}</div>')
    return "\n".join(out)


def font(size, bold=False):
    for name in (("Inter-Bold.otf" if bold else "Inter-Regular.otf"), "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        for base in ("/usr/share/fonts/opentype/inter/", "/usr/share/fonts/truetype/dejavu/"):
            if os.path.exists(base + name):
                return ImageFont.truetype(base + name, size)
    return ImageFont.load_default()


def icons():
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#171A2B"/>'
           '<path d="M6 50C22 44 26 22 58 14" fill="none" stroke="#C0271D" stroke-width="5" stroke-linecap="round"/>'
           '<circle cx="31" cy="33" r="8" fill="#171A2B" stroke="#F6F1E7" stroke-width="4.5"/></svg>\n')
    with open(os.path.join(DOCS, "rs-icon.svg"), "w") as fh:
        fh.write(svg)
    for size, name in ((32, "rs-icon-32.png"), (180, "rs-touch-icon.png")):
        s = size * 4
        im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.19), fill=INK)
        pts = [(s * (6 + 52 * t) / 64, s * (50 - 36 * (t ** 0.8) - 6 * (1 - abs(2 * t - 1))) / 64) for t in
               [i / 60 for i in range(61)]]
        d.line(pts, fill=RED, width=int(s * 5 / 64), joint="curve")
        cx, cy, r = s * 31 / 64, s * 33 / 64, s * 8 / 64
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=INK, outline=PAPER, width=int(s * 4.5 / 64))
        im.resize((size, size), Image.LANCZOS).save(os.path.join(DOCS, name))
    im = Image.open(os.path.join(DOCS, "rs-icon-32.png"))
    im.save(os.path.join(DOCS, "favicon.ico"), sizes=[(32, 32)])


def card(path, size=(1200, 630), title=("A thread", "through", "the crowd."), sub=None):
    w, h = size
    k = h / 630
    im = Image.new("RGB", (w * 2, h * 2), INK)
    d = ImageDraw.Draw(im)

    def bez(p0, p1, p2, p3, n=80):
        return [tuple(2 * ((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * e)
                      for a, b, c, e in zip(p0, p1, p2, p3)) for t in [i / n for i in range(n + 1)]]
    sx, sy = w / 1200, h / 630
    S = lambda x, y: (x * sx, y * sy)   # noqa: E731
    tracks = [bez(S(560, 560), S(690, 470), S(790, 430), S(900, 410)), bez(S(560, 560), S(720, 580), S(820, 520), S(900, 410)),
              [tuple(2 * v for v in S(900, 410)), tuple(2 * v for v in S(940, 400))],
              bez(S(940, 400), S(990, 320), S(1050, 330), S(1100, 350)), bez(S(940, 400), S(1000, 420), S(1060, 410), S(1100, 350)),
              bez(S(1100, 350), S(1130, 330), S(1160, 250), S(1180, 180))]
    for t in tracks:
        d.line(t, fill=RED, width=int(6 * k), joint="curve")
        for i in range(0, len(t), max(1, len(t) // 5)):
            x, y = t[i]
            r = 9 * k
            d.ellipse([x - r, y - r, x + r, y + r], fill=INK, outline=PAPER, width=int(4 * k))
    d.text((2 * 64 * sx, 2 * 60 * sy), "RAKSHASUTRA", font=font(int(44 * k), True), fill=PAPER)
    y = 2 * 150 * sy
    for line in title:
        d.text((2 * 64 * sx, y), line, font=font(int(150 * k), True), fill=PAPER)
        y += 160 * k
    d.text((2 * 64 * sx, 2 * h - 2 * 76 * sy),
           sub or "Finding separated pilgrims without phones or cellular.",
           font=font(int(38 * k)), fill="#A9ADC4")
    im.resize((w, h), Image.LANCZOS).save(path)


def main():
    os.makedirs(os.path.join(DOCS, "img"), exist_ok=True)
    values = json.loads(read(ROOT, "generated", "numbers.json"))
    params = {r[0]: r[1] for r in __import__("csv").reader(open(os.path.join(ROOT, "data", "params.csv")))}
    values.update(CSS=read(HERE, "base.css"), KERNEL=read(HERE, "kernel.js"), GiBle=params["gi_loss_ble_db"],
                  GiLora=params["gi_loss_lora_db"], BookPages=pages("A-Thread-Through-the-Crowd-Rakshasutra.pdf"),
                  WpPages=pages("Rakshasutra-White-Paper-WP01.pdf"))
    items = json.loads(read(ROOT, "results", "audit.json"))
    for name, template in (("index.html", read(HERE, "site.html")), ("explorer.html", read(HERE, "template.html")),
                           ("audit.html", AUDIT_PAGE)):
        with open(os.path.join(DOCS, name), "w", encoding="utf-8") as fh:
            fh.write(fill(template, dict(values, ROWS=audit_rows(items))))
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    icons()
    card(os.path.join(DOCS, "img", "og-card.png"))
    card(os.path.join(DOCS, "banner.png"), size=(1280, 420), title=("A thread through", "the crowd."),
         sub="Finding separated pilgrims without phones or cellular.")
    print("wrote docs/index.html, explorer.html, audit.html, icons and cards")


if __name__ == "__main__":
    main()
