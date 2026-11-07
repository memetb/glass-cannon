#!/usr/bin/env python3
"""Generate content/images/tree-cycle.svg — a looping, CSS-only animated SVG.

Each cycle: a random search tree grows (bouncy pop-in, level by level), one
leaf is selected (path lights up), the leaf is rejected (red ✕, shake), the
tree collapses, and a different tree grows in its place.

CSS-only so it animates inside <img>. Usage: python3 tools/tree-anim.py [seed]
"""
import random, sys

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 11
TREES = 4            # distinct trees per loop
WIN = None           # seconds per tree (derived from the timeline below)
W, H = 1200, 900
DEPTH = 4            # levels below root
TOP, BOTTOM, LEFT, RIGHT = 140, 760, 110, 1090

# timeline (seconds, local to a tree's window)
GROW0, GROW_STEP = 0.1, 0.2
SELECT0, SELECT_STEP = GROW0 + DEPTH * GROW_STEP + 0.5, 0.14
LEAF_ON = SELECT0 + SELECT_STEP * DEPTH + 0.05
REJECT = LEAF_ON + 0.75
COLLAPSE0, COLLAPSE_STEP = REJECT + 0.75, 0.09
GONE = COLLAPSE0 + COLLAPSE_STEP * DEPTH + 0.35
WIN = GONE + 0.25
T = TREES * WIN      # loop length

BOUNCE = "cubic-bezier(.34,1.56,.64,1)"


def pct(k, t):
    return f"{max(0.0, min(100.0, (k * WIN + t) / T * 100)):.3f}%"


def build_tree(rng):
    while True:
        levels = [[{"parent": None}]]
        for d in range(1, DEPTH + 1):
            row = []
            for pi, _ in enumerate(levels[-1]):
                for _ in range(rng.choices([1, 2, 3], weights=[2, 5, 3])[0]):
                    row.append({"parent": pi})
            levels.append(row)
        if 14 <= len(levels[-1]) <= 26:
            break
    # leaves evenly spaced, parents centred over children
    n = len(levels[-1])
    for i, node in enumerate(levels[-1]):
        node["x"] = LEFT + i * (RIGHT - LEFT) / (n - 1)
    for d in range(DEPTH - 1, -1, -1):
        for pi, node in enumerate(levels[d]):
            xs = [c["x"] for c in levels[d + 1] if c["parent"] == pi]
            node["x"] = sum(xs) / len(xs)
    for d, row in enumerate(levels):
        for node in row:
            node["y"] = TOP + d * (BOTTOM - TOP) / DEPTH + rng.uniform(-10, 10)
            node["x"] += rng.uniform(-6, 6) if d else 0
    target = rng.randrange(n)
    path, i = [], target
    for d in range(DEPTH, -1, -1):
        path.append(i)
        i = levels[d][i]["parent"] if d else 0
    path = path[::-1]  # index per level, root..leaf
    return levels, path


css, body = [], []
rng = random.Random(SEED)

for k in range(TREES):
    levels, path = build_tree(rng)
    g = []

    for d in range(DEPTH + 1):
        t0 = GROW0 + d * GROW_STEP
        c0 = COLLAPSE0 + (DEPTH - d) * COLLAPSE_STEP
        # node pop-in / collapse
        css.append(
            f"@keyframes n{k}{d}{{0%,{pct(k,t0)}{{transform:scale(0)}}"
            f"{pct(k,t0+.12)}{{transform:scale(1.4)}}{pct(k,t0+.22)}{{transform:scale(.82)}}"
            f"{pct(k,t0+.31)}{{transform:scale(1.1)}}{pct(k,t0+.4)},{pct(k,c0)}{{transform:scale(1)}}"
            f"{pct(k,c0+.1)}{{transform:scale(1.25)}}{pct(k,c0+.32)},100%{{transform:scale(0)}}}}"
            f".n{k}{d}{{animation:n{k}{d} {T}s linear infinite}}"
        )
        if d:
            e0 = t0 - 0.2
            css.append(
                f"@keyframes e{k}{d}{{0%,{pct(k,e0)}{{stroke-dashoffset:1;opacity:1}}"
                f"{pct(k,e0+.24)}{{stroke-dashoffset:0}}"
                f"{pct(k,c0-.05)}{{stroke-dashoffset:0;opacity:1}}{pct(k,c0+.25)},100%{{stroke-dashoffset:1;opacity:0}}}}"
                f".e{k}{d}{{animation:e{k}{d} {T}s linear infinite}}"
            )

    # dim everything off the selected path while the leaf is examined
    css.append(
        f"@keyframes dim{k}{{0%,{pct(k,SELECT0)}{{opacity:1}}{pct(k,SELECT0+.4)},{pct(k,COLLAPSE0)}{{opacity:.28}}"
        f"{pct(k,COLLAPSE0+.2)},100%{{opacity:1}}}}.dim{k}{{animation:dim{k} {T}s linear infinite}}"
    )

    on_path_edges, off_edges, on_nodes, off_nodes = [], [], [], []
    for d, row in enumerate(levels):
        for i, nd in enumerate(row):
            r = 10 - d * 1.2
            circ = (f'<circle class="node n{k}{d}" cx="{nd["x"]:.1f}" cy="{nd["y"]:.1f}" r="{r:.1f}"/>')
            (on_nodes if path[d] == i else off_nodes).append(circ)
            if d:
                p = levels[d - 1][nd["parent"]]
                line = (f'<line class="edge e{k}{d}" pathLength="1" x1="{p["x"]:.1f}" y1="{p["y"]:.1f}" '
                        f'x2="{nd["x"]:.1f}" y2="{nd["y"]:.1f}"/>')
                (on_path_edges if path[d] == i else off_edges).append(line)

    g.append(f'<g class="dim{k}">' + "".join(off_edges) + "".join(off_nodes) + "</g>")
    g.append("".join(on_path_edges) + "".join(on_nodes))

    # selected path glow, drawn root → leaf
    pts = [levels[d][path[d]] for d in range(DEPTH + 1)]
    dpath = " ".join(f"{'M' if j == 0 else 'L'}{p['x']:.1f},{p['y']:.1f}" for j, p in enumerate(pts))
    css.append(
        f"@keyframes s{k}{{0%,{pct(k,SELECT0)}{{stroke-dashoffset:1;opacity:1}}"
        f"{pct(k,SELECT0+SELECT_STEP*DEPTH+.1)}{{stroke-dashoffset:0}}"
        f"{pct(k,REJECT)}{{stroke:#ffb347;stroke-dashoffset:0;opacity:1}}{pct(k,REJECT+.15)}{{stroke:#ff3b6b}}"
        f"{pct(k,COLLAPSE0)}{{stroke:#ff3b6b;stroke-dashoffset:0;opacity:1}}{pct(k,COLLAPSE0+.3)},100%{{stroke:#ff3b6b;stroke-dashoffset:1;opacity:0}}}}"
        f".s{k}{{animation:s{k} {T}s linear infinite}}"
    )
    g.append(f'<path class="sel s{k}" pathLength="1" d="{dpath}"/>')

    # leaf marker: pop in, wobble, turn red on reject, shake, vanish
    lx, ly = pts[-1]["x"], pts[-1]["y"]
    a, c = LEAF_ON, REJECT
    css.append(
        f"@keyframes l{k}{{0%,{pct(k,a)}{{transform:scale(0);fill:#fff}}"
        f"{pct(k,a+.18)}{{transform:scale(1.6);fill:#fff}}{pct(k,a+.32)}{{transform:scale(.85)}}"
        f"{pct(k,a+.46)}{{transform:scale(1.15)}}{pct(k,a+.58)},{pct(k,c)}{{transform:scale(1);fill:#fff}}"
        f"{pct(k,c+.08)}{{transform:translateX(-9px) scale(1.2);fill:#ff3b6b}}{pct(k,c+.16)}{{transform:translateX(9px) scale(1.2)}}"
        f"{pct(k,c+.24)}{{transform:translateX(-6px) scale(1.1)}}{pct(k,c+.32)}{{transform:translateX(5px)}}"
        f"{pct(k,c+.4)},{pct(k,COLLAPSE0)}{{transform:translateX(0) scale(1);fill:#ff3b6b}}"
        f"{pct(k,COLLAPSE0+.2)},100%{{transform:scale(0);fill:#ff3b6b}}}}"
        f".l{k}{{animation:l{k} {T}s linear infinite}}"
        f"@keyframes h{k}{{0%,{pct(k,a)}{{opacity:0;transform:scale(.3)}}{pct(k,a+.3)}{{opacity:1;transform:scale(1.15)}}"
        f"{pct(k,a+.5)},{pct(k,c)}{{opacity:.9;transform:scale(1);fill:url(#glowA)}}{pct(k,c+.01)}{{fill:url(#glowR)}}"
        f"{pct(k,c+.2)}{{opacity:1;transform:scale(1.5);fill:url(#glowR)}}{pct(k,COLLAPSE0)}{{opacity:.8;transform:scale(1);fill:url(#glowR)}}"
        f"{pct(k,COLLAPSE0+.25)},100%{{opacity:0;transform:scale(.2);fill:url(#glowR)}}}}"
        f".h{k}{{animation:h{k} {T}s linear infinite}}"
        # ✕ strike + labels (VERIFY → REJECT)
        f"@keyframes x{k}{{0%,{pct(k,c)}{{transform:scale(0) rotate(-90deg)}}{pct(k,c+.2)}{{transform:scale(1.5) rotate(10deg)}}"
        f"{pct(k,c+.34)}{{transform:scale(.85) rotate(-4deg)}}{pct(k,c+.46)},{pct(k,COLLAPSE0)}{{transform:scale(1) rotate(0)}}"
        f"{pct(k,COLLAPSE0+.25)},100%{{transform:scale(0) rotate(45deg)}}}}.x{k}{{animation:x{k} {T}s linear infinite}}"
        f"@keyframes v{k}{{0%,{pct(k,a+.1)}{{opacity:0;transform:translateY(12px)}}{pct(k,a+.35)}{{opacity:1;transform:translateY(-4px)}}"
        f"{pct(k,a+.5)},{pct(k,c-.05)}{{opacity:1;transform:translateY(0)}}{pct(k,c+.1)},100%{{opacity:0;transform:translateY(0)}}}}"
        f".v{k}{{animation:v{k} {T}s linear infinite}}"
        f"@keyframes c{k}{{0%,{pct(k,c+.05)}{{opacity:0;transform:scale(.4)}}{pct(k,c+.25)}{{opacity:1;transform:scale(1.25)}}"
        f"{pct(k,c+.4)},{pct(k,COLLAPSE0)}{{opacity:1;transform:scale(1)}}{pct(k,COLLAPSE0+.2)},100%{{opacity:0;transform:scale(.6)}}}}"
        f".c{k}{{animation:c{k} {T}s linear infinite}}"
    )
    lab_y = ly + 52
    g.append(
        f'<circle class="halo h{k}" cx="{lx:.1f}" cy="{ly:.1f}" r="70" fill="url(#glowA)"/>'
        f'<circle class="leaf l{k}" cx="{lx:.1f}" cy="{ly:.1f}" r="12"/>'
        f'<g class="x x{k}" transform-origin="{lx:.1f} {ly:.1f}"><path d="M{lx-22:.1f},{ly-22:.1f} L{lx+22:.1f},{ly+22:.1f} M{lx+22:.1f},{ly-22:.1f} L{lx-22:.1f},{ly+22:.1f}"/></g>'
        f'<text class="lab v{k}" x="{lx:.1f}" y="{lab_y:.1f}">VERIFY(x)</text>'
        f'<text class="lab reject c{k}" x="{lx:.1f}" y="{lab_y:.1f}">REJECT</text>'
    )
    body.append(f'<g class="tree t{k}">' + "".join(g) + "</g>")

# tree counter in the header: 1..TREES cycling
for k in range(TREES):
    css.append(
        f"@keyframes k{k}{{0%,{pct(k,0)}{{opacity:0}}{pct(k,.05)},{pct(k,WIN-.05)}{{opacity:1}}{pct(k,WIN)},100%{{opacity:0}}}}"
        f".k{k}{{opacity:0;animation:k{k} {T}s linear infinite}}"
    )
counter = "".join(f'<tspan class="k{k}" x="1140" text-anchor="end">TREE #{k+1:02d}</tspan>' for k in range(TREES))

style = f"""
.node{{fill:#c026d3;fill-opacity:.9;stroke:#fff;stroke-opacity:.3;stroke-width:1.5;transform-box:fill-box;transform-origin:center;transform:scale(0)}}
.edge{{stroke:url(#edge);stroke-width:1.8;stroke-opacity:.7;stroke-dasharray:1;stroke-dashoffset:1}}
.sel{{fill:none;stroke:#ffb347;stroke-width:5;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;filter:url(#soft)}}
.leaf{{fill:#fff;transform-box:fill-box;transform-origin:center;transform:scale(0)}}
.halo{{transform-box:fill-box;transform-origin:center;opacity:0}}
.x path{{stroke:#ff3b6b;stroke-width:7;stroke-linecap:round;fill:none;filter:url(#soft)}}
.x{{transform:scale(0)}}
.lab{{font:600 22px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:4px;text-anchor:middle;fill:#fff;opacity:0;transform-box:fill-box;transform-origin:center}}
.reject{{fill:#ff3b6b}}
.hdr{{font:20px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:6px}}
{''.join(css)}
@media (prefers-reduced-motion: reduce){{
  *{{animation:none!important}}
  .t1,.t2,.t3{{display:none}}
  .t0 .node,.t0 .leaf,.t0 .x{{transform:none}} .t0 .edge,.t0 .sel{{stroke-dashoffset:0}}
  .t0 .halo,.t0 .reject,.k0{{opacity:1}}
}}
"""

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<title>A search tree grows, one leaf is selected and rejected, and a new tree grows</title>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1a0b2e"/><stop offset="1" stop-color="#0b0614"/></linearGradient>
<linearGradient id="edge" x1="0" y1="0" x2="0" y2="{H}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#ffb347"/><stop offset="1" stop-color="#8b2cf5"/></linearGradient>
<radialGradient id="glowA"><stop offset="0" stop-color="#ff7a18" stop-opacity=".9"/><stop offset="1" stop-color="#ff7a18" stop-opacity="0"/></radialGradient>
<radialGradient id="glowR"><stop offset="0" stop-color="#ff3b6b" stop-opacity=".95"/><stop offset="1" stop-color="#ff3b6b" stop-opacity="0"/></radialGradient>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<style>{style}</style>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
<text class="hdr" x="60" y="70" fill="#ffb347" opacity=".85">GENERATE: SEARCH Σⁿ</text>
<text class="hdr" y="70" fill="#fff" opacity=".5">{counter}</text>
{''.join(body)}
<text class="hdr" x="{W-60}" y="{H-40}" fill="#fff" opacity=".45" text-anchor="end" style="font-size:18px;letter-spacing:5px">O(bᵈ) vs O(|x|)</text>
</svg>
"""
out = "content/images/tree-cycle.svg"
open(out, "w", encoding="utf-8").write(svg)
print(f"wrote {out} ({len(svg)//1024} KB, {TREES} trees, {T:.0f}s loop)")
