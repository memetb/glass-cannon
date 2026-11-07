#!/usr/bin/env python3
"""Generate content/images/tree-regrow.svg — a looping, CSS-only animated SVG.

Each scenario: a search tree grows; a leaf is verified and REJECTED; the
rejection propagates up the path to an ancestor (never the root); the
ancestor's subtree is pruned and a new subtree regenerates beneath it; a leaf
in the new subtree is re-verified and COMMITTED (green ball); the tree clears and the next
scenario starts.

CSS-only so it animates inside <img>. Usage: python3 tools/tree-regrow.py [seed]
"""
import random, sys

SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 5
SCENARIOS = 3
W, H = 1200, 900
DEPTH = 4
TOP, BOTTOM, LEFT, RIGHT = 140, 760, 110, 1090
LEVEL_Y = [TOP + d * (BOTTOM - TOP) / DEPTH for d in range(DEPTH + 1)]

RED, GREEN, ORANGE = "#ff3b6b", "#34d399", "#ffb347"

# timeline (seconds, local to a scenario)
GROW0, STEP = 0.1, 0.2            # level stagger while growing
SEL_STEP = 0.12                    # path draw stagger per edge
PROP_STEP = 0.16                   # rejection propagation per level
COLL_STEP = 0.07                   # collapse stagger per level


def timeline(a):
    t = {}
    t["grown"] = GROW0 + DEPTH * STEP + 0.4
    t["s1"] = t["grown"] + 0.15
    t["l1"] = t["s1"] + SEL_STEP * DEPTH + 0.05
    t["r1"] = t["l1"] + 0.7
    t["anc"] = t["r1"] + PROP_STEP * (DEPTH - a) + 0.1      # rejection reaches ancestor
    t["prune"] = t["anc"] + 0.6
    t["regrow"] = t["prune"] + COLL_STEP * (DEPTH - a) + 0.35
    t["regrown"] = t["regrow"] + (DEPTH - a - 1) * STEP + 0.4
    t["s2"] = t["regrown"] + 0.15
    t["l2"] = t["s2"] + SEL_STEP * DEPTH + 0.05
    t["v2"] = t["l2"] + 0.7
    t["end"] = t["v2"] + 1.3
    t["win"] = t["end"] + COLL_STEP * DEPTH + 0.3 + 0.25
    return t


# ---------------------------------------------------------------- trees
def grow(rng, parent_idx_count, from_level):
    """levels from_level+1..DEPTH; returns list of rows (each node has 'parent')."""
    rows, prev = [], parent_idx_count
    for _ in range(from_level + 1, DEPTH + 1):
        row = []
        for pi in range(prev):
            for _ in range(rng.choices([1, 2, 3], weights=[2, 5, 3])[0]):
                row.append({"parent": pi})
        rows.append(row)
        prev = len(row)
    return rows


def layout(rows, top_nodes, x0, x1, jitter, rng):
    """Leaves evenly in [x0,x1]; parents centred over children. rows[0] parents are top_nodes."""
    leaves = rows[-1]
    n = len(leaves)
    for i, nd in enumerate(leaves):
        nd["x"] = (x0 + x1) / 2 if n == 1 else x0 + i * (x1 - x0) / (n - 1)
    for r in range(len(rows) - 2, -1, -1):
        for pi, nd in enumerate(rows[r]):
            xs = [c["x"] for c in rows[r + 1] if c["parent"] == pi]
            nd["x"] = sum(xs) / len(xs)
    for r, row in enumerate(rows):
        for nd in row:
            nd["x"] += rng.uniform(-jitter, jitter)


def subtree_leaves(levels, a, ai):
    """indices of leaves under node (a, ai)."""
    idx = {ai}
    for d in range(a + 1, DEPTH + 1):
        idx = {i for i, nd in enumerate(levels[d]) if nd["parent"] in idx}
    return sorted(idx)


def scenario(rng):
    while True:
        levels = [[{"parent": None, "x": (LEFT + RIGHT) / 2}]] + grow(rng, 1, 0)
        if not 14 <= len(levels[-1]) <= 24:
            continue
        rows = levels[1:]
        layout(rows, levels[0], LEFT, RIGHT, 6, rng)
        a = rng.choice([1, 2])
        cands = [i for i in range(len(levels[a])) if len(subtree_leaves(levels, a, i)) >= 3]
        if cands:
            break
    ai = rng.choice(cands)
    old_leaves = subtree_leaves(levels, a, ai)
    leaf1 = rng.choice(old_leaves)

    # membership of the old subtree, per level
    sub = {a: {ai}}
    for d in range(a + 1, DEPTH + 1):
        sub[d] = {i for i, nd in enumerate(levels[d]) if nd["parent"] in sub[d - 1]}

    # path root..leaf1 (index per level)
    path1, i = [0] * (DEPTH + 1), leaf1
    for d in range(DEPTH, 0, -1):
        path1[d] = i
        i = levels[d][i]["parent"]

    # new subtree under the ancestor, inside the old subtree's horizontal span
    gap = (RIGHT - LEFT) / (len(levels[-1]) - 1)
    xs = [levels[DEPTH][j]["x"] for j in old_leaves]
    x0, x1 = min(xs) - gap * 0.35, max(xs) + gap * 0.35
    while True:
        new_rows = grow(rng, 1, a)
        m = len(new_rows[-1])
        if 2 <= m <= len(old_leaves) + 1 and [len(r) for r in new_rows] != [len(sub[d]) for d in range(a + 1, DEPTH + 1)]:
            break
    layout(new_rows, None, x0, x1, 4, rng)
    leaf2 = rng.randrange(m)
    path2_new, i = {}, leaf2   # level -> index in new_rows[level-a-1]
    for d in range(DEPTH, a, -1):
        path2_new[d] = i
        i = new_rows[d - a - 1][i]["parent"]

    anc = levels[a][ai]
    return levels, a, ai, sub, path1, new_rows, path2_new, anc


# ---------------------------------------------------------------- css helpers
css, body = [], []
_uid = [0]
_seen = {}
_offsets = []   # scenario start times
TOTAL = [0.0]


def P(k, t):
    return (_offsets[k] + t) / TOTAL[0] * 100


def kf(k, stops, prop_default=None):
    """stops: [(t, 'decl')] in scenario-local seconds. Returns a class name."""
    stops = sorted(stops, key=lambda s: s[0])
    key = (k, tuple(stops))
    if key in _seen:
        return _seen[key]
    _uid[0] += 1
    name = f"a{_uid[0]}"
    _seen[key] = name
    parts = [f"0%{{{stops[0][1]}}}"]
    for t, decl in stops:
        parts.append(f"{max(0, min(100, P(k, t))):.3f}%{{{decl}}}")
    parts.append(f"100%{{{stops[-1][1]}}}")
    css.append(f"@keyframes {name}{{{''.join(parts)}}}.{name}{{animation:{name} {TOTAL[0]:.2f}s linear infinite}}")
    return name


def pop(t0):
    return [(t0, "transform:scale(0)"), (t0 + .12, "transform:scale(1.4)"), (t0 + .22, "transform:scale(.82)"),
            (t0 + .31, "transform:scale(1.1)"), (t0 + .4, "transform:scale(1)")]


def collapse(c0):
    return [(c0, "transform:scale(1)"), (c0 + .08, "transform:scale(1.25)"), (c0 + .26, "transform:scale(0)")]


def draw(t0, dur=.24):
    return [(t0, "stroke-dashoffset:1;opacity:1"), (t0 + dur, "stroke-dashoffset:0;opacity:1")]


def undraw(c0):
    return [(c0, "stroke-dashoffset:0;opacity:1"), (c0 + .26, "stroke-dashoffset:1;opacity:0")]


# ---------------------------------------------------------------- build
rng = random.Random(SEED)
scens = [scenario(rng) for _ in range(SCENARIOS)]
tls = [timeline(s[1]) for s in scens]
acc = 0.0
for tl in tls:
    _offsets.append(acc)
    acc += tl["win"]
TOTAL[0] = acc


def node(cls, x, y, d):
    return f'<circle class="node {cls}" cx="{x:.1f}" cy="{y:.1f}" r="{10 - d * 1.2:.1f}"/>'


def edge(cls, p, c):
    return (f'<line class="edge {cls}" pathLength="1" x1="{p[0]:.1f}" y1="{p[1]:.1f}" '
            f'x2="{c[0]:.1f}" y2="{c[1]:.1f}"/>')


def seg(cls, p, c):
    return (f'<line class="sel {cls}" pathLength="1" x1="{p[0]:.1f}" y1="{p[1]:.1f}" '
            f'x2="{c[0]:.1f}" y2="{c[1]:.1f}"/>')


for k, ((levels, a, ai, sub, path1, new_rows, path2_new, anc), t) in enumerate(zip(scens, tls)):
    rnd = random.Random(SEED * 100 + k)
    Y = {d: [LEVEL_Y[d] + rnd.uniform(-10, 10) for _ in levels[d]] for d in range(DEPTH + 1)}
    YN = {d: [LEVEL_Y[d] + rnd.uniform(-10, 10) for _ in new_rows[d - a - 1]] for d in range(a + 1, DEPTH + 1)}
    pos = lambda d, i: (levels[d][i]["x"], Y[d][i])
    posn = lambda d, i: (new_rows[d - a - 1][i]["x"], YN[d][i])

    def dim(windows):
        stops = [(0, "opacity:1")]
        for s, e in windows:
            stops += [(s, "opacity:1"), (s + .35, "opacity:.28"), (e, "opacity:.28"), (e + .2, "opacity:1")]
        return kf(k, stops)

    end_coll = lambda d: t["end"] + (DEPTH - d) * COLL_STEP
    groups = {"A_on": [], "A_off": [], "B_on": [], "B_off": [], "C_on": [], "C_off": []}

    # old tree: A = outside ancestor's subtree (incl. ancestor), B = below ancestor
    for d in range(DEPTH + 1):
        for i, nd in enumerate(levels[d]):
            in_b = d > a and i in sub[d]
            on = path1[d] == i
            grow_t = GROW0 + d * STEP
            gone = (t["prune"] + (DEPTH - d) * COLL_STEP) if in_b else end_coll(d)
            ncls = kf(k, pop(grow_t) + collapse(gone))
            g = ("B" if in_b else "A") + ("_on" if on and (in_b or d <= a) else "_off")
            if in_b: ncls += " b"
            groups[g].append(node(ncls, *pos(d, i), d))
            if d:
                ecls = kf(k, [(0, "stroke-dashoffset:1;opacity:1")] + draw(grow_t - .2) + undraw(gone - .05))
                if in_b: ecls += " b"
                groups[g].insert(0, edge(ecls, pos(d - 1, nd["parent"]), pos(d, i)))

    # new subtree C under the ancestor
    for d in range(a + 1, DEPTH + 1):
        for i, nd in enumerate(new_rows[d - a - 1]):
            on = path2_new.get(d) == i
            grow_t = t["regrow"] + (d - a - 1) * STEP
            ncls = kf(k, [(0, "transform:scale(0)")] + pop(grow_t) + collapse(end_coll(d)))
            g = "C_on" if on else "C_off"
            groups[g].append(node(ncls, *posn(d, i), d))
            parent = pos(a, ai) if d == a + 1 else posn(d - 1, nd["parent"])
            ecls = kf(k, [(0, "stroke-dashoffset:1;opacity:1")] + draw(grow_t - .2) + undraw(end_coll(d) - .05))
            groups[g].insert(0, edge(ecls, parent, posn(d, i)))

    w1, w2 = (t["s1"], t["prune"]), (t["s2"], t["end"])
    body_k = [
        f'<g class="{dim([w1, w2])}">' + "".join(groups["A_off"]) + "</g>",
        f'<g class="{dim([w1])}">' + "".join(groups["B_off"]) + "</g>",
        f'<g class="{dim([w2])}">' + "".join(groups["C_off"]) + "</g>",
        "".join(groups["A_on"] + groups["B_on"] + groups["C_on"]),
    ]

    # selection path segments
    sel = []
    for d in range(1, DEPTH + 1):
        p, c = pos(d - 1, path1[d - 1]), pos(d, path1[d])
        d0 = t["s1"] + (d - 1) * SEL_STEP
        if d > a:   # below ancestor: rejected, pruned with the subtree
            red = t["r1"] + (DEPTH - d) * PROP_STEP
            st = [(0, f"stroke-dashoffset:1;opacity:1;stroke:{ORANGE}")] + draw(d0) + [
                (red, f"stroke:{ORANGE}"), (red + .1, f"stroke:{RED}"),
                (t["prune"] - .1, f"stroke:{RED};stroke-dashoffset:0;opacity:1"),
                (t["prune"] + .2, f"stroke:{RED};stroke-dashoffset:0;opacity:0")]
        else:       # root..ancestor: stays, re-used by the second attempt
            st = [(0, f"stroke-dashoffset:1;opacity:1;stroke:{ORANGE}")] + draw(d0) + [
                (t["prune"], f"stroke:{ORANGE};stroke-dashoffset:0;opacity:1"),
                (t["prune"] + .3, f"stroke:{ORANGE};stroke-dashoffset:0;opacity:.35"),
                (t["s2"] + (d - 1) * SEL_STEP, f"stroke:{ORANGE};stroke-dashoffset:0;opacity:.35"),
                (t["s2"] + (d - 1) * SEL_STEP + .24, f"stroke:{ORANGE};stroke-dashoffset:0;opacity:1"),
                (t["v2"] + (d - 1) * .05, f"stroke:{ORANGE};stroke-dashoffset:0;opacity:1"),
                (t["v2"] + (d - 1) * .05 + .15, f"stroke:{GREEN};stroke-dashoffset:0;opacity:1"),
            ] + [(s, f"stroke:{GREEN};" + v) for s, v in undraw(end_coll(d) - .1)]
        sel.append(seg(kf(k, st), p, c))
    for d in range(a + 1, DEPTH + 1):
        p = pos(a, ai) if d == a + 1 else posn(d - 1, path2_new[d - 1])
        c = posn(d, path2_new[d])
        d0 = t["s2"] + (d - 1) * SEL_STEP
        st = [(0, f"stroke-dashoffset:1;opacity:1;stroke:{ORANGE}")] + draw(d0) + [
            (t["v2"] + (d - 1) * .05, f"stroke:{ORANGE}"), (t["v2"] + (d - 1) * .05 + .15, f"stroke:{GREEN};stroke-dashoffset:0;opacity:1")
        ] + [(s, f"stroke:{GREEN};" + v) for s, v in undraw(end_coll(d) - .1)]
        sel.append(seg(kf(k, st), p, c))
    body_k.insert(3, "".join(sel))

    # leaf 1: VERIFY → REJECT
    lx, ly = pos(DEPTH, path1[DEPTH])
    l1, r1 = t["l1"], t["r1"]
    leaf1 = kf(k, [(0, "transform:scale(0);fill:#fff")] + [(s, v + ";fill:#fff") for s, v in pop(l1)] + [
        (r1, "transform:scale(1);fill:#fff"), (r1 + .08, f"transform:translateX(-9px) scale(1.2);fill:{RED}"),
        (r1 + .16, f"transform:translateX(9px) scale(1.2);fill:{RED}"), (r1 + .24, f"transform:translateX(-5px);fill:{RED}"),
        (r1 + .32, f"transform:translateX(0) scale(1);fill:{RED}"),
        (t["prune"], f"transform:scale(1);fill:{RED}"), (t["prune"] + .2, f"transform:scale(0);fill:{RED}")])
    halo1 = kf(k, [(0, "opacity:0;transform:scale(.3)"), (l1, "opacity:0;transform:scale(.3)"),
                   (l1 + .3, "opacity:.9;transform:scale(1.1)"), (l1 + .45, "opacity:.8;transform:scale(1)"),
                   (r1, "opacity:.8;transform:scale(1)"), (r1 + .2, "opacity:1;transform:scale(1.4)"),
                   (t["prune"], "opacity:.7;transform:scale(1)"), (t["prune"] + .2, "opacity:0;transform:scale(.2)")])
    halo1r = kf(k, [(0, "opacity:0"), (r1, "opacity:0"), (r1 + .05, "opacity:1"), (t["prune"], "opacity:1"), (t["prune"] + .2, "opacity:0")])
    x1 = kf(k, [(0, "transform:scale(0) rotate(-90deg)"), (r1, "transform:scale(0) rotate(-90deg)"),
                (r1 + .2, "transform:scale(1.5) rotate(10deg)"), (r1 + .34, "transform:scale(.85) rotate(-4deg)"),
                (r1 + .46, "transform:scale(1) rotate(0)"), (t["prune"], "transform:scale(1) rotate(0)"),
                (t["prune"] + .2, "transform:scale(0) rotate(45deg)")])
    v1 = kf(k, [(0, "opacity:0;transform:translateY(12px)"), (l1 + .1, "opacity:0;transform:translateY(12px)"),
                (l1 + .35, "opacity:1;transform:translateY(-4px)"), (l1 + .5, "opacity:1;transform:translateY(0)"),
                (r1 - .05, "opacity:1;transform:translateY(0)"), (r1 + .1, "opacity:0;transform:translateY(0)")])
    rj1 = kf(k, [(0, "opacity:0;transform:scale(.4)"), (r1 + .05, "opacity:0;transform:scale(.4)"),
                 (r1 + .25, "opacity:1;transform:scale(1.25)"), (r1 + .4, "opacity:1;transform:scale(1)"),
                 (t["prune"], "opacity:1;transform:scale(1)"), (t["prune"] + .2, "opacity:0;transform:scale(.6)")])

    # ancestor: red ring when rejection arrives, then orange "REGENERATE" pulse
    axx, axy = pos(a, ai)
    an = t["anc"]
    ring = kf(k, [(0, f"transform:scale(0);stroke:{RED}"), (an, f"transform:scale(0);stroke:{RED}"),
                  (an + .14, f"transform:scale(1.5);stroke:{RED}"), (an + .26, f"transform:scale(.85);stroke:{RED}"),
                  (an + .38, f"transform:scale(1.1);stroke:{RED}"), (an + .48, f"transform:scale(1);stroke:{RED}"),
                  (t["regrow"] - .15, f"transform:scale(1);stroke:{RED}"), (t["regrow"], f"transform:scale(1.2);stroke:{ORANGE}"),
                  (t["regrow"] + .25, f"transform:scale(.95);stroke:{ORANGE}"), (t["regrown"], f"transform:scale(1.15);stroke:{ORANGE}"),
                  (t["s2"] + .1, f"transform:scale(0);stroke:{ORANGE}")])
    lab_anc_r = kf(k, [(0, "opacity:0"), (an + .1, "opacity:0"), (an + .3, "opacity:1"), (t["regrow"] - .1, "opacity:1"), (t["regrow"] + .05, "opacity:0")])
    lab_anc_g = kf(k, [(0, "opacity:0"), (t["regrow"], "opacity:0"), (t["regrow"] + .15, "opacity:1"), (t["s2"], "opacity:1"), (t["s2"] + .2, "opacity:0")])

    # leaf 2: VERIFY → COMMIT (leaf swells into a green ball)
    mx, my = posn(DEPTH, path2_new[DEPTH])
    l2, v2 = t["l2"], t["v2"]
    leaf2 = kf(k, [(0, "transform:scale(0);fill:#fff")] + [(s, v + ";fill:#fff") for s, v in pop(l2)] + [
        (v2, "transform:scale(1);fill:#fff"), (v2 + .14, f"transform:scale(2.6);fill:{GREEN}"),
        (v2 + .28, f"transform:scale(1.6);fill:{GREEN}"), (v2 + .4, f"transform:scale(2.05);fill:{GREEN}"),
        (v2 + .5, f"transform:scale(1.9);fill:{GREEN}")] +
        [(t["end"], f"transform:scale(1.9);fill:{GREEN}"), (t["end"] + .08, f"transform:scale(2.3);fill:{GREEN}"),
         (t["end"] + .26, f"transform:scale(0);fill:{GREEN}")])
    halo2a = kf(k, [(0, "opacity:0;transform:scale(.3)"), (l2, "opacity:0;transform:scale(.3)"),
                   (l2 + .3, "opacity:.9;transform:scale(1.1)"), (l2 + .45, "opacity:.8;transform:scale(1)"),
                   (v2, "opacity:.8;transform:scale(1)"), (v2 + .1, "opacity:0;transform:scale(1.2)")])
    halo2 = kf(k, [(0, "opacity:0;transform:scale(1)"), (v2, "opacity:0;transform:scale(1)"), (v2 + .2, "opacity:1;transform:scale(1.6)"),
                   (v2 + .5, "opacity:.85;transform:scale(1.2)"), (t["end"], "opacity:.85;transform:scale(1.2)"),
                   (t["end"] + .25, "opacity:0;transform:scale(.2)")])
    v2l = kf(k, [(0, "opacity:0;transform:translateY(12px)"), (l2 + .1, "opacity:0;transform:translateY(12px)"),
                 (l2 + .35, "opacity:1;transform:translateY(-4px)"), (l2 + .5, "opacity:1;transform:translateY(0)"),
                 (v2 - .05, "opacity:1;transform:translateY(0)"), (v2 + .1, "opacity:0;transform:translateY(0)")])
    commit_l = kf(k, [(0, "opacity:0;transform:scale(.4)"), (v2 + .05, "opacity:0;transform:scale(.4)"),
                   (v2 + .25, "opacity:1;transform:scale(1.25)"), (v2 + .4, "opacity:1;transform:scale(1)"),
                   (t["end"], "opacity:1;transform:scale(1)"), (t["end"] + .2, "opacity:0;transform:scale(.6)")])

    # attempt counter
    att1 = kf(k, [(0, "opacity:0"), (t["s1"] - .1, "opacity:0"), (t["s1"], "opacity:1"), (t["prune"], "opacity:1"), (t["prune"] + .15, "opacity:0")])
    att2 = kf(k, [(0, "opacity:0"), (t["s2"] - .1, "opacity:0"), (t["s2"], "opacity:1"), (t["end"] + .3, "opacity:1"), (t["end"] + .45, "opacity:0")])

    side = 1 if axx < W - 300 else -1
    lab_x, lab_anchor = axx + side * 38, ("start" if side > 0 else "end")
    body_k.append(
        f'<circle class="halo {halo1}" cx="{lx:.1f}" cy="{ly:.1f}" r="70" fill="url(#glowA)"/>'
        f'<circle class="halo {halo1r}" cx="{lx:.1f}" cy="{ly:.1f}" r="70" fill="url(#glowR)"/>'
        f'<circle class="leaf {leaf1}" cx="{lx:.1f}" cy="{ly:.1f}" r="12"/>'
        f'<g class="x {x1}" transform-origin="{lx:.1f} {ly:.1f}"><path d="M{lx-22:.1f},{ly-22:.1f} L{lx+22:.1f},{ly+22:.1f} M{lx+22:.1f},{ly-22:.1f} L{lx-22:.1f},{ly+22:.1f}"/></g>'
        f'<text class="lab {v1}" x="{lx:.1f}" y="{ly + 52:.1f}">VERIFY(x)</text>'
        f'<text class="lab reject {rj1}" x="{lx:.1f}" y="{ly + 52:.1f}">REJECT</text>'
        f'<circle class="ring {ring}" cx="{axx:.1f}" cy="{axy:.1f}" r="24"/>'
        f'<text class="lab small reject {lab_anc_r}" x="{lab_x:.1f}" y="{axy + 6:.1f}" style="text-anchor:{lab_anchor}">REJECT ↑</text>'
        f'<text class="lab small regen {lab_anc_g}" x="{lab_x:.1f}" y="{axy + 6:.1f}" style="text-anchor:{lab_anchor}">REGENERATE</text>'
        f'<circle class="halo {halo2a}" cx="{mx:.1f}" cy="{my:.1f}" r="70" fill="url(#glowA)"/>'
        f'<circle class="halo {halo2}" cx="{mx:.1f}" cy="{my:.1f}" r="70" fill="url(#glowG)"/>'
        f'<circle class="leaf {leaf2}" cx="{mx:.1f}" cy="{my:.1f}" r="12"/>'
        f'<text class="lab {v2l}" x="{mx:.1f}" y="{my + 52:.1f}">VERIFY(x′)</text>'
        f'<text class="lab commit {commit_l}" x="{mx:.1f}" y="{my + 52:.1f}">COMMIT</text>'
        f'<text class="hdr {att1}" x="1140" y="70" text-anchor="end" fill="#fff">ATTEMPT 1</text>'
        f'<text class="hdr {att2}" x="1140" y="70" text-anchor="end" fill="#fff">ATTEMPT 2</text>'
    )
    body.append(f'<g class="scn s{k}">' + "".join(body_k) + "</g>")

style = f"""
.node{{fill:#c026d3;fill-opacity:.9;stroke:#fff;stroke-opacity:.3;stroke-width:1.5;transform-box:fill-box;transform-origin:center;transform:scale(0)}}
.edge{{stroke:url(#edge);stroke-width:1.8;stroke-opacity:.7;stroke-dasharray:1;stroke-dashoffset:1}}
.sel{{fill:none;stroke:{ORANGE};stroke-width:5;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:1;filter:url(#soft)}}
.leaf{{fill:#fff;transform-box:fill-box;transform-origin:center;transform:scale(0)}}
.halo{{transform-box:fill-box;transform-origin:center;opacity:0}}
.ring{{fill:none;stroke:{RED};stroke-width:4;transform-box:fill-box;transform-origin:center;transform:scale(0);filter:url(#soft)}}
.x path{{stroke:{RED};stroke-width:7;stroke-linecap:round;fill:none;filter:url(#soft)}}
.x{{transform:scale(0)}}
.lab{{font:600 22px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:4px;text-anchor:middle;fill:#fff;opacity:0;transform-box:fill-box;transform-origin:center}}
.small{{font-size:18px;letter-spacing:3px}}
.reject{{fill:{RED}}} .regen{{fill:{ORANGE}}} .commit{{fill:{GREEN}}}
.hdr{{font:20px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:6px;opacity:0}}
{''.join(css)}
@media (prefers-reduced-motion: reduce){{
  *{{animation:none!important}}
  .scn:not(.s0){{display:none}}
  .s0 .node{{transform:none}} .s0 .edge{{stroke-dashoffset:0}} .s0 .b{{display:none}}
}}
"""

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<title>A leaf is rejected, the rejection propagates to an ancestor, the subtree is regenerated and a new leaf is verified</title>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1a0b2e"/><stop offset="1" stop-color="#0b0614"/></linearGradient>
<linearGradient id="edge" x1="0" y1="0" x2="0" y2="{H}" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#ffb347"/><stop offset="1" stop-color="#8b2cf5"/></linearGradient>
<radialGradient id="glowA"><stop offset="0" stop-color="#ff7a18" stop-opacity=".9"/><stop offset="1" stop-color="#ff7a18" stop-opacity="0"/></radialGradient>
<radialGradient id="glowR"><stop offset="0" stop-color="{RED}" stop-opacity=".95"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient>
<radialGradient id="glowG"><stop offset="0" stop-color="{GREEN}" stop-opacity=".9"/><stop offset="1" stop-color="{GREEN}" stop-opacity="0"/></radialGradient>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<style>{style}</style>
<rect width="{W}" height="{H}" fill="url(#bg)"/>
<text x="60" y="70" fill="{ORANGE}" opacity=".85" style="font:20px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:6px">GENERATE · VERIFY · PRUNE</text>
{''.join(body)}
<text x="{W-60}" y="{H-40}" fill="#fff" opacity=".45" text-anchor="end" style="font:18px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:5px">O(bᵈ) vs O(|x|)</text>
</svg>
"""
out = "content/images/tree-regrow.svg"
open(out, "w", encoding="utf-8").write(svg)
print(f"wrote {out} ({len(svg)//1024} KB, {SCENARIOS} scenarios, {TOTAL[0]:.1f}s loop)")
