"""Draw the README's animated banner, diagrams and the family-walk GIF.

    docs/img/hero.svg       animated banner (SMIL), with docs/banner.png as the still fallback
    docs/img/pipeline.svg   the data path
    docs/img/roadmap.svg    the roadmap
    docs/img/walk.gif       the simulated family walk, as the control room sees it
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from rakshasutra import simulate  # noqa: E402

IMG = os.path.join(ROOT, "docs", "img")
INK, PAPER, RED, MUTED, RULE = "#171A2B", "#F6F1E7", "#C0271D", "#6A6F85", "#D9D2C2"
FONT = "font-family=\"'IBM Plex Sans','Segoe UI',Helvetica,Arial,sans-serif\""
MONO = "font-family=\"'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace\""
SERIF = "font-family=\"Georgia,'Times New Roman',serif\""


def hero():
    parent = "M70 300 C 220 220, 340 190, 520 178 L 580 168 C 680 188, 790 178, 880 124 L 950 114"
    child = "M70 300 C 220 220, 340 190, 520 178 L 580 168 C 660 90, 780 98, 880 124 L 950 114"
    tracks = ["M70 300 C 220 220, 340 190, 520 178", "M70 300 C 260 316, 400 268, 520 178", "M520 178 L 580 168",
              "M580 168 C 660 90, 780 98, 880 124", "M580 168 C 680 188, 790 178, 880 124",
              "M880 124 L 950 114 C 1010 90, 1080 60, 1150 40"]
    knots = [(70, 300), (160, 251), (255, 216), (350, 195), (440, 184), (520, 178), (175, 305), (290, 290), (395, 255),
             (470, 215), (550, 173), (580, 168), (640, 122), (715, 100), (800, 104), (880, 124), (660, 179), (745, 174),
             (820, 155), (950, 114), (1020, 87), (1085, 62), (1150, 40)]
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 360" role="img" aria-label="Rakshasutra: a thread '
           f'through the crowd. A parent and a child walk a branching mountain route and take different tracks at a junction.">',
           f'<rect width="1280" height="360" fill="{INK}"/>']
    svg.append('<g transform="translate(250,95) scale(0.8,0.78)">')
    svg += [f'<path d="{d}" fill="none" stroke="{RED}" stroke-width="3.6" stroke-linecap="round"/>' for d in tracks]
    for i, (x, y) in enumerate(knots):
        svg.append(f'<circle cx="{x}" cy="{y}" r="5.5" fill="{INK}" stroke="{PAPER}" stroke-width="2.2">'
                   f'<animate attributeName="r" values="5.5;8.5;5.5" dur="3.2s" begin="{(i * 0.37) % 3.2:.2f}s" '
                   f'repeatCount="indefinite"/></circle>')
    svg.append(f'<circle r="7" fill="{PAPER}"><animateMotion dur="22s" repeatCount="indefinite" path="{parent}"/></circle>')
    svg.append(f'<circle r="5.5" fill="{RED}" stroke="{PAPER}" stroke-width="2"><animateMotion dur="22s" begin="0.4s" '
               f'repeatCount="indefinite" path="{child}"/></circle>')
    svg.append('</g>')
    svg += [f'<text x="70" y="62" {FONT} font-size="20" font-weight="600" letter-spacing="3" fill="{PAPER}">RAKSHASUTRA</text>',
            f'<text x="70" y="128" {SERIF} font-size="58" font-weight="700" fill="{PAPER}">A thread through the crowd.</text>',
            f'<text x="70" y="166" {FONT} font-size="19" fill="#A9ADC4">Finding separated pilgrims on a mountain route, '
            f'without phones or cellular coverage.</text>',
            f'<text x="1210" y="336" text-anchor="end" {MONO} font-size="13" fill="#7C819C">design and calculation · '
            f'nothing measured yet</text>', '</svg>']
    with open(os.path.join(IMG, "hero.svg"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(svg) + "\n")


def pipeline(n):
    boxes = [("1 · Wristband", ["signed 15-byte frame", "new ID every 15 min", "SOS button, buzzer"]),
             ("2 · Pole", ["scans under the roof", "reports arrivals once", "64-byte Bloom heartbeat"]),
             ("3 · LoRaWAN", ["IN865, 8 channels, SF7", "whip above the roof", "fibre in the two hubs"]),
             ("4 · Server", ["resolves the pseudonym", "verifies every SOS", "distance on the route graph"]),
             ("5 · Alerts", ["band-to-band tether", "Class C wake token", "control-room alarm"])]
    w, h, bw, gap = 1200, 250, 208, 32
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="Data path: wristband, pole, '
           f'LoRaWAN, server, alerts."><rect width="{w}" height="{h}" fill="{PAPER}"/>']
    for i, (title, lines) in enumerate(boxes):
        x = 20 + i * (bw + gap)
        svg.append(f'<rect x="{x}" y="40" width="{bw}" height="150" fill="#fff" stroke="{INK}" stroke-width="1.5"/>')
        svg.append(f'<rect x="{x}" y="40" width="{bw}" height="38" fill="{INK}"/>')
        svg.append(f'<text x="{x + 14}" y="65" {FONT} font-size="16" font-weight="600" fill="{PAPER}">{title}</text>')
        for j, line in enumerate(lines):
            svg.append(f'<text x="{x + 14}" y="{108 + j * 26}" {FONT} font-size="14.5" fill="{INK}">{line}</text>')
        if i < len(boxes) - 1:
            ax = x + bw
            svg.append(f'<path d="M{ax + 4} 115 H{ax + gap - 9}" stroke="{RED}" stroke-width="2.5"/>'
                       f'<path d="M{ax + gap - 11} 109 l9 6 l-9 6 z" fill="{RED}"/>')
            svg.append(f'<circle r="4" fill="{RED}"><animateMotion dur="1.8s" begin="{i * 0.45}s" repeatCount="indefinite" '
                       f'path="M{ax + 4} 115 H{ax + gap - 10}"/></circle>')
    svg.append(f'<text x="20" y="226" {MONO} font-size="13" fill="{MUTED}">3,000 wristbands in one gateway cell: '
               f'{n["LossSingle"]}% of frames lost with one uplink per arrival, {n["LossRakNd"]}% with chunks and the Bloom '
               f'heartbeat (calculated)</text></svg>')
    with open(os.path.join(IMG, "pipeline.svg"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(svg) + "\n")


def roadmap():
    stops = [("Nov 2026", "Reference model", "package, book, audit", True),
             ("Next", "Protocol revision", "tether, signed sightings", False),
             ("Planned", "Bench radio", "roof loss and range, measured", False),
             ("Planned", "Prototype", "10 bands, 3 poles", False),
             ("After that", "Pilot and peer review", "one zone, with permission", False)]
    w, h = 1200, 190
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="Roadmap: reference model '
           f'done in November 2026; protocol revision next; then bench radio, a prototype, a pilot and peer review.">',
           f'<rect width="{w}" height="{h}" fill="{PAPER}"/>',
           f'<path d="M60 70 H1140" stroke="{RED}" stroke-width="2.5"/>']
    for i, (when, name, what, done) in enumerate(stops):
        x = 60 + i * 270
        svg.append(f'<circle cx="{x}" cy="70" r="9" fill="{RED if done else PAPER}" stroke="{RED}" stroke-width="3"/>')
        svg.append(f'<text x="{x}" y="42" text-anchor="{"start" if i == 0 else "middle" if i < 4 else "end"}" {MONO} '
                   f'font-size="13" fill="{MUTED}">{when.upper()}{"  ·  DONE" if done else ""}</text>')
        anchor = "start" if i == 0 else "middle" if i < 4 else "end"
        svg.append(f'<text x="{x}" y="108" text-anchor="{anchor}" {FONT} font-size="17" font-weight="600" fill="{INK}">{name}</text>')
        svg.append(f'<text x="{x}" y="132" text-anchor="{anchor}" {FONT} font-size="13.5" fill="{MUTED}">{what}</text>')
    svg.append('</svg>')
    with open(os.path.join(IMG, "roadmap.svg"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(svg) + "\n")


def _font(size, bold=False):
    for path in ("/usr/share/fonts/opentype/inter/Inter-%s.otf" % ("SemiBold" if bold else "Regular"),
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def walk_gif():
    w = simulate.family_walk()
    trek, room, routes, along = w["trek"], w["room"], w["routes"], w["along"]
    W, H = 900, 400
    shared = [p for p in routes["band-0421"] if p in routes["tag-0421"]]
    split_m = along["band-0421"][len(shared) - 1]
    total = along["band-0421"][-1]
    xs = lambda m: 50 + 800 * m / total                                   # noqa: E731

    def xy(uid, m):
        if m <= split_m:
            return xs(m), 215
        f = min(1.0, (m - split_m) / 260.0)
        return xs(m), 215 + (-88 if uid == "band-0421" else 88) * f
    pole_xy = {}
    for uid in routes:
        for pid, m in zip(routes[uid], along[uid]):
            pole_xy[pid] = xy(uid, m)
    f_s, f_b, f_t = _font(13), _font(14, True), _font(21, True)
    uplinks = [(r["time_s"], r["pole"], r["fport"]) for r in w["log"]]
    events = [(e.time, e.kind, e.detail) for e in room.events if e.kind in ("SEPARATION", "SOS")]
    frames, step = [], 7.0
    t = 0.0
    while t <= w["duration_s"]:
        im = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(im)
        d.text((50, 22), "One simulated family at the Adhkuwari junction", font=f_t, fill=INK)
        d.text((50, 52), "black: parent tag    red: child's band    rings: where the server places them    "
                         "flash: a pole sends an uplink", font=f_s, fill=MUTED)
        for uid in routes:
            pts = [pole_xy[p] for p in routes[uid]]
            d.line(pts, fill=RED, width=2)
        for pid, (x, y) in pole_xy.items():
            recent = [fp for (ut, up, fp) in uplinks if up == pid and 0 <= t - ut < 9]
            if recent:
                r = 13 if 10 in recent else 10
                d.ellipse([x - r, y - r, x + r, y + r], outline=RED, width=2)
            d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=PAPER, outline=RED if trek.pole(pid).fiber else INK, width=2)
        d.text((xs(split_m) - 190, 182), "Adhkuwari hub: poles 25 m apart", font=f_s, fill=MUTED)
        d.text((xs(total) - 96, 100), "Sanjichhat track", font=f_s, fill=MUTED)
        d.text((xs(total) - 86, 318), "Himkoti track", font=f_s, fill=MUTED)
        for uid, col in (("tag-0421", INK), ("band-0421", RED)):
            seen = [p for (tt, p) in room.track.get(uid, []) if tt <= t]
            if seen:
                x, y = pole_xy[seen[-1]]
                d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=col, width=3)
            x, y = xy(uid, min(1.25 * t, total))
            r = 6 if uid == "tag-0421" else 5
            d.ellipse([x - r, y - r, x + r, y + r], fill=col)
        d.text((50, 362), f"t = {t:4.0f} s", font=f_b, fill=INK)
        msg = [(et, k, det) for (et, k, det) in events if et <= t]
        if msg:
            et, k, det = msg[-1]
            text = (f"SEPARATION flagged at {et:.0f} s: {det.split(';')[0]}" if k == "SEPARATION"
                    else f"SOS at {et:.0f} s: alarm raised, MIC verified, placed at the strongest pole")
            d.rectangle([150, 354, 860, 384], fill=INK)
            d.text((162, 361), text, font=f_b, fill=PAPER)
        frames.append(im.quantize(colors=24, method=Image.MEDIANCUT, dither=Image.NONE))
        t += step
    frames[0].save(os.path.join(IMG, "walk.gif"), save_all=True, append_images=frames[1:], duration=90, loop=0,
                   optimize=True)
    return len(frames)


def main():
    os.makedirs(IMG, exist_ok=True)
    with open(os.path.join(ROOT, "generated", "numbers.json")) as fh:
        n = json.load(fh)
    hero(), pipeline(n), roadmap()
    print("wrote hero.svg, pipeline.svg, roadmap.svg and walk.gif (%d frames)" % walk_gif())


if __name__ == "__main__":
    main()
