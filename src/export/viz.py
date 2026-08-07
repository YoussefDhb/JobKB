"""Self-contained interactive HTML views of the KB graph (no server, no internet, no external library).
`write_html` renders the navigable backbone (~300 nodes) with an inline canvas force layout; `write_full_html`
renders every node + edge with a Python-precomputed static layout so the browser runs no physics.
"""

from __future__ import annotations

import json

_KEEP = {"skill_type", "skill_domain", "skill_category", "isco_group", "occupation"}
_COLOR = {"skill_type": "#8250df", "skill_domain": "#0969da", "skill_category": "#1a7f76",
          "isco_group": "#bc4c00", "occupation": "#1a7f37"}


def _backbone(nodes, edges):
    by_id = {n["id"]: n for n in nodes}
    # skills per category (broader edge skill -> category)
    skill_per_cat = {}
    for e in edges:
        if e["type"] == "broader":
            tgt = by_id.get(e["target"])
            src = by_id.get(e["source"])
            if tgt and tgt["kind"] == "skill_category" and src and src["kind"] == "skill":
                skill_per_cat[e["target"]] = skill_per_cat.get(e["target"], 0) + 1

    keep_ids = {n["id"] for n in nodes if n["kind"] in _KEEP}
    vnodes = []
    for n in nodes:
        if n["kind"] not in _KEEP:
            continue
        if n["kind"] == "skill_category":
            size = 8 + min(30, (skill_per_cat.get(n["id"], 0)) ** 0.5 * 2.2)
        elif n["kind"] == "skill_domain":
            size = 16
        elif n["kind"] == "skill_type":
            size = 22
        elif n["kind"] == "isco_group":
            size = 9
        else:
            size = 5
        vnodes.append({"id": n["id"], "label": n.get("label_en") or n.get("label_fr") or n["id"],
                       "kind": n["kind"], "size": round(size, 1), "color": _COLOR[n["kind"]],
                       "count": skill_per_cat.get(n["id"], 0)})
    vedges = [{"s": e["source"], "t": e["target"]} for e in edges
              if e["type"] in ("broader", "in_domain")
              and e["source"] in keep_ids and e["target"] in keep_ids]
    return vnodes, vedges


_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JobKB — knowledge-graph overview</title>
<style>
  :root{color-scheme:light dark}
  html,body{margin:0;height:100%;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
  #wrap{position:fixed;inset:0}
  canvas{display:block;width:100%;height:100%;cursor:grab}
  #legend{position:fixed;top:12px;left:12px;background:rgba(255,255,255,.92);color:#111;
    border-radius:10px;padding:12px 14px;font-size:13px;box-shadow:0 2px 12px rgba(0,0,0,.18);max-width:280px}
  @media (prefers-color-scheme:dark){#legend{background:rgba(28,30,34,.92);color:#eee}}
  #legend h1{font-size:14px;margin:0 0 6px}
  #legend .row{display:flex;align-items:center;gap:8px;margin:3px 0}
  #legend .dot{width:12px;height:12px;border-radius:50%;flex:0 0 auto}
  #legend .muted{opacity:.7;font-size:12px;margin-top:8px;line-height:1.35}
  #tip{position:fixed;pointer-events:none;background:#111;color:#fff;padding:5px 8px;border-radius:6px;
    font-size:12px;opacity:0;transition:opacity .1s;max-width:320px;z-index:9}
</style></head>
<body><div id="wrap"><canvas id="c"></canvas></div>
<div id="legend"><h1>JobKB — graph overview</h1>
  <div class="row"><span class="dot" style="background:#8250df"></span>Skill type (hard/soft)</div>
  <div class="row"><span class="dot" style="background:#0969da"></span>Functional domain (10)</div>
  <div class="row"><span class="dot" style="background:#1a7f76"></span>Skill category (sized by #skills)</div>
  <div class="row"><span class="dot" style="background:#bc4c00"></span>ISCO occupation group</div>
  <div class="row"><span class="dot" style="background:#1a7f37"></span>Occupation</div>
  <div class="muted">Navigable backbone (%COUNT% nodes). Drag nodes, drag background to pan,
    scroll to zoom, hover for detail. The full %FULL% graph is in the GraphML / JSON / RDF exports.</div>
</div><div id="tip"></div>
<script>
const DATA=%DATA%;
const cv=document.getElementById('c'),ctx=cv.getContext('2d'),tip=document.getElementById('tip');
let W,H,DPR;function resize(){DPR=devicePixelRatio||1;W=cv.clientWidth;H=cv.clientHeight;
  cv.width=W*DPR;cv.height=H*DPR;ctx.setTransform(DPR,0,0,DPR,0,0);}addEventListener('resize',resize);
const N=DATA.nodes, idx=new Map(N.map((n,i)=>[n.id,i]));
N.forEach(n=>{n.x=W? W/2:innerWidth/2 + (Math.random()-.5)*400; n.y=(H||innerHeight)/2+(Math.random()-.5)*400; n.vx=0; n.vy=0;});
const E=DATA.edges.map(e=>({s:idx.get(e.s),t:idx.get(e.t)})).filter(e=>e.s!=null&&e.t!=null);
let view={x:0,y:0,k:1};
// ---- force simulation (O(n^2) repulsion is fine at this scale) ----
function step(){
  for(let i=0;i<N.length;i++){const a=N[i];
    for(let j=i+1;j<N.length;j++){const b=N[j];let dx=a.x-b.x,dy=a.y-b.y;let d2=dx*dx+dy*dy||1;
      let f=1400/d2;let d=Math.sqrt(d2);dx/=d;dy/=d;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;}}
  for(const e of E){const a=N[e.s],b=N[e.t];let dx=b.x-a.x,dy=b.y-a.y;let d=Math.sqrt(dx*dx+dy*dy)||1;
    let f=(d-70)*0.012;dx/=d;dy/=d;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f;}
  const cx=W/2,cy=H/2;
  for(const n of N){n.vx+=(cx-n.x)*0.0016;n.vy+=(cy-n.y)*0.0016;
    if(n!==drag){n.x+=n.vx*=.86;n.y+=n.vy*=.86;}}
}
function draw(){
  ctx.clearRect(0,0,W,H);ctx.save();ctx.translate(view.x,view.y);ctx.scale(view.k,view.k);
  ctx.strokeStyle='rgba(130,130,130,.28)';ctx.lineWidth=1/view.k;
  for(const e of E){const a=N[e.s],b=N[e.t];ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();}
  for(const n of N){ctx.beginPath();ctx.arc(n.x,n.y,n.size,0,7);ctx.fillStyle=n.color;ctx.fill();
    if(n.kind!=='occupation'&&n.kind!=='isco_group'){ctx.fillStyle=getComputedStyle(document.body).color;
      ctx.font=(n.kind==='skill_type'?13:11)+'px system-ui';ctx.textAlign='center';
      ctx.fillText(n.label,n.x,n.y-n.size-3);}}
  ctx.restore();
}
let drag=null;
function loop(){step();draw();requestAnimationFrame(loop);}
function toWorld(mx,my){return{x:(mx-view.x)/view.k,y:(my-view.y)/view.k};}
function pick(mx,my){const w=toWorld(mx,my);let best=null,bd=1e9;
  for(const n of N){const dx=n.x-w.x,dy=n.y-w.y,d=dx*dx+dy*dy;if(d<Math.max(n.size*n.size,64)&&d<bd){bd=d;best=n;}}return best;}
let pan=null;
cv.addEventListener('mousedown',e=>{const n=pick(e.clientX,e.clientY);if(n){drag=n;}else{pan={x:e.clientX-view.x,y:e.clientY-view.y};cv.style.cursor='grabbing';}});
addEventListener('mousemove',e=>{
  if(drag){const w=toWorld(e.clientX,e.clientY);drag.x=w.x;drag.y=w.y;drag.vx=drag.vy=0;}
  else if(pan){view.x=e.clientX-pan.x;view.y=e.clientY-pan.y;}
  const n=(!drag&&!pan)?pick(e.clientX,e.clientY):null;
  if(n){tip.style.opacity=1;tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';
    tip.textContent=n.label+' · '+n.kind.replace('_',' ')+(n.count?(' · '+n.count+' skills'):'');}
  else tip.style.opacity=0;
});
addEventListener('mouseup',()=>{drag=null;pan=null;cv.style.cursor='grab';});
cv.addEventListener('wheel',e=>{e.preventDefault();const s=e.deltaY<0?1.1:1/1.1;
  const wx=(e.clientX-view.x)/view.k,wy=(e.clientY-view.y)/view.k;view.k*=s;
  view.x=e.clientX-wx*view.k;view.y=e.clientY-wy*view.k;},{passive:false});
resize();loop();
</script></body></html>"""


def write_html(nodes, edges, path):
    vnodes, vedges = _backbone(nodes, edges)
    data = json.dumps({"nodes": vnodes, "edges": vedges}, ensure_ascii=False).replace("<", "\\u003c")
    html = (_HTML.replace("%DATA%", data)
                 .replace("%COUNT%", str(len(vnodes)))
                 .replace("%FULL%", f"{len(nodes):,}-node"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return {"viz_nodes": len(vnodes), "viz_edges": len(vedges)}


# FULL-graph HTML — every node + edge. The layout is precomputed in Python (a deterministic
# clustered layout: domains fan out around the centre, each category is a sub-hub, its skills form a
# phyllotaxis cloud, occupations sit on an outer ring by domain), so the browser runs NO physics — it
# only pans/zooms/redraws a static scene, which keeps 11k nodes + 44k edges smooth everywhere.
_KIND_IDX = {"skill_type": 0, "skill_domain": 1, "skill_category": 2, "isco_group": 3,
             "occupation": 4, "skill": 5}


def _full_layout(nodes, edges):
    """Deterministic, clarity-first layout: every domain owns a separate angular WEDGE sized by its
    content (skills + occupations), so domains read as distinct islands. Inside a wedge: the domain hub
    sits inner, its categories fan across the wedge, each category's skills form a compact phyllotaxis
    cluster, and the domain's occupations spread across an outer arc band (no thin radial spokes)."""
    import math
    from collections import defaultdict
    byid = {n["id"]: n for n in nodes}
    skill_cat, cat_dom, occ_dom = {}, {}, {}
    for e in edges:
        s, t = e["source"], e["target"]
        if e["type"] == "broader":
            sk, tk = byid[s]["kind"], byid[t]["kind"]
            if sk == "skill" and tk == "skill_category":
                skill_cat[s] = t
            elif sk == "skill_category" and tk == "skill_domain":
                cat_dom[s] = t
        elif e["type"] == "in_domain":
            occ_dom[e["source"]] = e["target"]

    domains = [n["id"] for n in nodes if n["kind"] == "skill_domain"]
    dom_idx = {d: i for i, d in enumerate(domains)}
    cats_by_dom = defaultdict(list)
    for c in [n["id"] for n in nodes if n["kind"] == "skill_category"]:
        cats_by_dom[cat_dom.get(c)].append(c)
    skills_by_cat = defaultdict(list)
    for s in [n["id"] for n in nodes if n["kind"] == "skill"]:
        skills_by_cat[skill_cat.get(s)].append(s)
    occ_by_dom = defaultdict(list)
    for o in [n["id"] for n in nodes if n["kind"] == "occupation"]:
        occ_by_dom[occ_dom.get(o)].append(o)

    # angular span per domain, proportional to its content (so big domains never crowd small ones)
    weight = {}
    for d in domains:
        nsk = sum(len(skills_by_cat.get(c, [])) for c in cats_by_dom.get(d, []))
        weight[d] = nsk + 1.5 * len(occ_by_dom.get(d, [])) + 45
    total = sum(weight.values()) or 1.0
    GAPF = 0.05                                   # fraction of each wedge kept empty on each side
    dom_span, ang = {}, -math.pi / 2
    for d in domains:
        span = 2 * math.pi * weight[d] / total
        dom_span[d] = (ang, ang + span, span)
        ang += span

    R_DOM, R_CAT, R_OCC = 1150.0, 2050.0, 2950.0
    GOLD = 2.399963229728653
    pos, dom_of = {}, {}

    for i, t in enumerate([n["id"] for n in nodes if n["kind"] == "skill_type"]):
        pos[t] = ((-1) ** i * 150.0, 0.0)
    for j, ic in enumerate([n["id"] for n in nodes if n["kind"] == "isco_group"]):
        a = 2 * math.pi * j / max(1, len([n for n in nodes if n["kind"] == "isco_group"]))
        pos[ic] = (400 * math.cos(a), 400 * math.sin(a))
    for d in domains:
        a0, a1, span = dom_span[d]
        mid = (a0 + a1) / 2
        pos[d] = (R_DOM * math.cos(mid), R_DOM * math.sin(mid)); dom_of[d] = d
    for d in domains:
        a0, a1, span = dom_span[d]; pad = span * GAPF
        clist = cats_by_dom.get(d, [])
        for j, c in enumerate(clist):
            a = (a0 + a1) / 2 if len(clist) == 1 else a0 + pad + (a1 - a0 - 2 * pad) * (j + 0.5) / len(clist)
            pos[c] = (R_CAT * math.cos(a), R_CAT * math.sin(a)); dom_of[c] = d
    for d in domains:
        a0, a1, span = dom_span[d]; pad = span * GAPF
        clist = cats_by_dom.get(d, [])
        share = (span - 2 * pad) / max(1, len(clist))
        for c in clist:
            cx, cy = pos.get(c, (0.0, 0.0))
            slist = skills_by_cat.get(c, [])
            k = len(slist)
            rad = min(0.48 * share * R_CAT, 46 + 20 * math.sqrt(k))
            for j, s in enumerate(slist):
                rr = rad * math.sqrt((j + 0.5) / max(1, k))
                aa = j * GOLD
                pos[s] = (cx + rr * math.cos(aa), cy + rr * math.sin(aa)); dom_of[s] = d
    for d in domains:
        a0, a1, span = dom_span[d]; pad = span * GAPF
        olist = occ_by_dom.get(d, [])
        m = len(olist)
        per_row = max(1, int((span - 2 * pad) * R_OCC / 62))
        for j, o in enumerate(olist):
            row, col = divmod(j, per_row)
            ncol = min(per_row, m - row * per_row)
            a = (a0 + a1) / 2 if ncol == 1 else a0 + pad + (a1 - a0 - 2 * pad) * (col + 0.5) / per_row
            rr = R_OCC + row * 72
            pos[o] = (rr * math.cos(a), rr * math.sin(a)); dom_of[o] = d
    # anything unclustered (no domain path) -> far ring, so nothing is dropped
    leftover = [n["id"] for n in nodes if n["id"] not in pos]
    for j, m in enumerate(leftover):
        a = 2 * math.pi * j / max(1, len(leftover))
        pos[m] = (4300 * math.cos(a), 4300 * math.sin(a))
    return pos, {nid: dom_idx.get(dom_of.get(nid), -1) for nid in byid}


def _full_data(nodes, edges):
    import math
    from collections import defaultdict
    pos, dom_of = _full_layout(nodes, edges)
    idx = {n["id"]: i for i, n in enumerate(nodes)}
    kind_of = {n["id"]: n["kind"] for n in nodes}
    deg = defaultdict(int)
    for e in edges:
        if e["type"] == "requires":
            deg[e["source"]] += 1
            deg[e["target"]] += 1
    base_r = {0: 24.0, 1: 15.0, 2: 9.0, 3: 7.0, 4: 4.5, 5: 2.6}
    narr = []
    for n in nodes:
        x, y = pos[n["id"]]
        k = _KIND_IDX[n["kind"]]
        r = base_r[k]
        d = deg.get(n["id"], 0)
        if n["kind"] == "skill":
            r = 2.3 + min(4.6, 0.52 * math.sqrt(d))
        elif n["kind"] == "occupation":
            r = 4.0 + min(3.2, 0.30 * math.sqrt(d))
        desc = (n.get("description") or "").strip()
        if len(desc) > 260:
            desc = desc[:257] + "…"
        narr.append([round(x, 1), round(y, 1), round(r, 1), k, dom_of.get(n["id"], -1),
                     n.get("label_en") or n.get("label_fr") or n["id"], desc,
                     n.get("wikidata_qid") or "", n.get("hard_soft") or ""])
    # edge classes for level-of-detail rendering:
    #   0 = backbone (type↔domain↔category, occupation→domain, ISCO tree) — always shown
    #   1 = occupation → skill (requires) — shown when zoomed in (+ toggle)
    #   2 = skill → category (taxonomy leaf) — shown when zoomed in
    earr = []
    for e in edges:
        s, t = e["source"], e["target"]
        if e["type"] == "requires":
            cls = 1
        elif kind_of[s] == "skill" or kind_of[t] == "skill":
            cls = 2
        else:
            cls = 0
        earr.append([idx[s], idx[t], cls])
    dom_names = [n.get("label_en") or n.get("label_fr") or n["id"]
                 for n in nodes if n["kind"] == "skill_domain"]
    return narr, earr, dom_names


# FULL-graph HTML — every node + edge, Python-precomputed static layout (browser runs no physics).
# Node payload: [x, y, r, kindIdx, domIdx, label, description, wikidata_qid, hard_soft].
# Edge payload: [srcIdx, tgtIdx, classIdx]  (0 backbone · 1 occupation→skill · 2 skill→category).
_FULL_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JobKB — full knowledge graph</title>
<style>
  :root{color-scheme:light dark}
  html,body{margin:0;height:100%;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;overflow:hidden}
  body{background:#f6f8fa}
  @media (prefers-color-scheme:dark){body{background:#0d1117}}
  canvas{display:block;width:100vw;height:100vh;cursor:grab}
  .card{position:fixed;background:rgba(255,255,255,.96);color:#111;border-radius:11px;
    box-shadow:0 3px 16px rgba(0,0,0,.24);border:1px solid rgba(0,0,0,.06)}
  @media (prefers-color-scheme:dark){.card{background:rgba(22,27,34,.96);color:#e6edf3;border-color:rgba(255,255,255,.08)}}
  #panel{top:14px;left:14px;padding:13px 15px;font-size:13px;max-width:306px}
  #panel h1{font-size:15px;margin:0 0 2px}
  #panel .sub{font-size:11.5px;opacity:.72;margin-bottom:8px}
  #panel label{display:block;margin:4px 0;cursor:pointer}
  #panel .k{display:flex;align-items:center;gap:7px;margin:2px 0;font-size:12px}
  #panel .dot{width:11px;height:11px;border-radius:50%;flex:0 0 auto}
  #panel .muted{opacity:.72;font-size:11.5px;margin-top:9px;line-height:1.45}
  #panel button{margin-top:9px;font:inherit;padding:4px 11px;border-radius:7px;border:1px solid #8887;
    background:transparent;color:inherit;cursor:pointer}
  #panel button:hover{background:rgba(128,128,128,.12)}
  #q{width:100%;box-sizing:border-box;margin-top:2px;padding:6px 9px;border-radius:7px;
    border:1px solid #8887;background:transparent;color:inherit;font:inherit}
  #qinfo{font-size:11px;opacity:.7;min-height:13px;margin:2px 0}
  hr{border:0;border-top:1px solid rgba(128,128,128,.22);margin:9px 0}
  #doms{margin-top:6px;max-height:150px;overflow:auto}
  #detail{left:14px;bottom:14px;padding:12px 14px;font-size:12.5px;max-width:344px;display:none}
  #detail b{font-size:14px}
  #detail .kind{opacity:.7}
  #detail .meta{opacity:.82;font-size:11.5px;margin-top:3px}
  #detail .desc{margin-top:8px;line-height:1.5}
  #detail .x{float:right;cursor:pointer;opacity:.55;margin-left:10px;font-size:14px}
  #hint{left:50%;bottom:16px;transform:translateX(-50%);padding:7px 13px;font-size:12px;
    border-radius:20px;opacity:.94;pointer-events:none}
  #tip{position:fixed;pointer-events:none;background:#111;color:#fff;padding:6px 10px;border-radius:7px;
    font-size:12px;opacity:0;transition:opacity .08s;max-width:360px;z-index:9;line-height:1.4}
</style></head>
<body><canvas id="c"></canvas>
<div id="panel" class="card"><h1>JobKB — full knowledge graph</h1>
  <div class="sub">Interactive map · %NNODES% concepts · %NEDGES% relations</div>
  <input id="q" type="search" placeholder="🔍  search an occupation or skill…" autocomplete="off">
  <div id="qinfo"></div>
  <label><input type="checkbox" id="tax" checked> taxonomy structure &amp; skill links</label>
  <label><input type="checkbox" id="occ"> occupation → skill links</label>
  <label><input type="checkbox" id="lab" checked> labels</label>
  <button id="fit">reset view</button>
  <hr>
  <div class="k"><span class="dot" style="background:#8250df"></span>skill type (hard / soft)</div>
  <div class="k"><span class="dot" style="background:#bc4c00"></span>ISCO occupation group</div>
  <div class="k"><span class="dot" style="border:1.5px solid #111;background:#59a14f"></span>occupation (outlined)</div>
  <div style="font-size:11.5px;opacity:.82;margin-top:7px">functional domains — each domain's categories &amp; skills share its hue:</div>
  <div id="doms"></div>
  <div class="muted">Drag = pan · scroll = zoom · <b>click a node for its definition</b>.
    Zoom in to reveal individual skills and their links.</div>
</div>
<div id="detail" class="card"></div>
<div id="hint" class="card"></div>
<div id="tip"></div>
<script>
const NODES=%NODES%, EDGES=%EDGES%, DOMAINS=%DOMAINS%;
const PAL=['#4e79a7','#f28e2b','#59a14f','#e15759','#b07aa1','#9c755f','#ff9da7','#76b7b2','#edc948','#bab0ac'];
const DARK=matchMedia('(prefers-color-scheme: dark)').matches;
function color(n){const k=n[3];if(k===0)return'#8250df';if(k===3)return'#bc4c00';return n[4]>=0?PAL[n[4]%10]:'#8a8a8a';}
function esc(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
const cv=document.getElementById('c'),ctx=cv.getContext('2d'),tip=document.getElementById('tip'),hint=document.getElementById('hint');
let W,H,DPR;function resize(){DPR=devicePixelRatio||1;W=innerWidth;H=innerHeight;cv.width=W*DPR;cv.height=H*DPR;
  ctx.setTransform(DPR,0,0,DPR,0,0);req();}addEventListener('resize',resize);
(function(){const box=document.getElementById('doms');DOMAINS.forEach((nm,i)=>{const d=document.createElement('div');
  d.className='k';d.innerHTML='<span class="dot" style="background:'+PAL[i%10]+'"></span>'+esc(nm);box.appendChild(d);});})();
const adj=NODES.map(()=>[]);for(let i=0;i<EDGES.length;i++){const e=EDGES[i];adj[e[0]].push(i);adj[e[1]].push(i);}
let view={x:0,y:0,k:1};
function fit(){let a=1e9,b=1e9,c=-1e9,d=-1e9;for(const n of NODES){a=Math.min(a,n[0]);b=Math.min(b,n[1]);c=Math.max(c,n[0]);d=Math.max(d,n[1]);}
  const k=0.9*Math.min(W/(c-a||1),H/(d-b||1));view.k=k;view.x=W/2-(a+c)/2*k;view.y=H/2-(b+d)/2*k;req();}
const S=n=>[n[0]*view.k+view.x,n[1]*view.k+view.y];
let hov=-1,sel=-1,rafid=0;function req(){if(!rafid)rafid=requestAnimationFrame(draw);}
const showTax=()=>document.getElementById('tax').checked,showOcc=()=>document.getElementById('occ').checked,
      showLab=()=>document.getElementById('lab').checked;
function focusNode(){return sel>=0?sel:hov;}
let fset=new Set();function computeFocus(){fset=new Set();const f=focusNode();if(f>=0){fset.add(f);
  for(const ei of adj[f]){const e=EDGES[ei];fset.add(e[0]);fset.add(e[1]);}}}
let matches=new Set(),matchList=[];
function draw(){rafid=0;ctx.clearRect(0,0,W,H);const f=focusNode();const hasM=matches.size>0;
  const zin=view.k>0.22;
  hint.style.display=(zin||hasM||f>=0)?'none':'block';
  ctx.lineWidth=Math.min(1.2,1/view.k*0.9);
  for(let i=0;i<EDGES.length;i++){const e=EDGES[i];const c=e[2];
    if(c===0){if(!showTax())continue;}
    else if(c===2){if(!showTax()||!zin)continue;}
    else{if(!showOcc()||!zin)continue;}
    if(f>=0&&(e[0]===f||e[1]===f))continue;
    const A=NODES[e[0]],B=NODES[e[1]];const ax=A[0]*view.k+view.x,ay=A[1]*view.k+view.y,bx=B[0]*view.k+view.x,by=B[1]*view.k+view.y;
    if((ax<0&&bx<0)||(ax>W&&bx>W)||(ay<0&&by<0)||(ay>H&&by>H))continue;
    ctx.strokeStyle=c===1?'rgba(180,150,90,.16)':(c===2?'rgba(120,120,130,.20)':'rgba(90,110,150,.42)');
    ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(bx,by);ctx.stroke();}
  for(let i=0;i<NODES.length;i++){const n=NODES[i];const sx=n[0]*view.k+view.x,sy=n[1]*view.k+view.y;
    if(sx<-20||sx>W+20||sy<-20||sy>H+20)continue;
    let r=Math.max(1.1,n[2]*Math.min(1.6,Math.sqrt(view.k)));
    let dim=1;
    if(hasM)dim=matches.has(i)?1:0.09;
    else if(f>=0&&i!==f&&!fset.has(i))dim=0.20;
    else if(!zin&&n[3]===5)dim=0.72;
    ctx.globalAlpha=dim;ctx.beginPath();ctx.arc(sx,sy,r,0,7);ctx.fillStyle=color(n);ctx.fill();
    if(n[3]===4){ctx.lineWidth=Math.min(1.2,0.85*Math.sqrt(view.k));ctx.strokeStyle=DARK?'rgba(230,230,230,.6)':'rgba(20,20,20,.6)';ctx.stroke();}
    ctx.globalAlpha=1;
    if(hasM&&matches.has(i)){ctx.beginPath();ctx.arc(sx,sy,r+3,0,7);ctx.lineWidth=1.8;ctx.strokeStyle='#e15759';ctx.stroke();}}
  if(f>=0){const n0=NODES[f];ctx.lineWidth=1.6;
    for(const ei of adj[f]){const e=EDGES[ei];const A=NODES[e[0]],B=NODES[e[1]];
      ctx.strokeStyle=e[2]===1?'rgba(200,120,20,.9)':'rgba(30,120,60,.9)';
      ctx.beginPath();ctx.moveTo(...S(A));ctx.lineTo(...S(B));ctx.stroke();}
    const p0=S(n0);ctx.beginPath();ctx.arc(p0[0],p0[1],Math.max(5,n0[2]*1.7),0,7);ctx.lineWidth=2.4;
    ctx.strokeStyle=DARK?'#e6edf3':'#111';ctx.stroke();}
  if(showLab()){const txt=DARK?'#e6edf3':'#161b22',halo=DARK?'rgba(0,0,0,.74)':'rgba(255,255,255,.86)';
    ctx.textAlign='center';ctx.lineJoin='round';
    function lblAt(wx,wy,s,fs,dy){const sx=wx*view.k+view.x,sy=wy*view.k+view.y+(dy||0);
      ctx.font=fs+'px system-ui';ctx.lineWidth=3.4;ctx.strokeStyle=halo;ctx.strokeText(s,sx,sy);
      ctx.fillStyle=txt;ctx.fillText(s,sx,sy);}
    function lbl(n,fs){lblAt(n[0],n[1],n[5],fs,-n[2]*1.4-2);}
    for(const n of NODES){
      if(n[3]===1)lblAt(n[0]*1.72,n[1]*1.72,n[5],13.5,0);   // domain label pushed onto its cluster
      else if(n[3]===2&&view.k>0.19)lbl(n,10.5);
      else if((n[3]===5||n[3]===4)&&view.k>0.55&&n[2]>=4.6)lbl(n,10);}}
}
function pick(mx,my){let best=-1,bd=1e9;for(let i=0;i<NODES.length;i++){const n=NODES[i];const sx=n[0]*view.k+view.x,sy=n[1]*view.k+view.y;
  const dx=sx-mx,dy=sy-my,d=dx*dx+dy*dy;const rr=Math.max(5,n[2]*Math.sqrt(view.k)+3);if(d<rr*rr&&d<bd){bd=d;best=i;}}return best;}
let pan=null,down=null,moved=false;
cv.addEventListener('mousedown',e=>{down={x:e.clientX,y:e.clientY};moved=false;pan={x:e.clientX-view.x,y:e.clientY-view.y};cv.style.cursor='grabbing';});
addEventListener('mouseup',e=>{cv.style.cursor='grab';
  if(down&&!moved){const p=pick(e.clientX,e.clientY);sel=(p>=0&&sel!==p)?p:-1;computeFocus();updateDetail();req();}
  pan=null;down=null;});
addEventListener('mousemove',e=>{
  if(pan){if(down&&(Math.abs(e.clientX-down.x)+Math.abs(e.clientY-down.y)>4))moved=true;
    view.x=e.clientX-pan.x;view.y=e.clientY-pan.y;req();tip.style.opacity=0;return;}
  const p=pick(e.clientX,e.clientY);
  if(p!==hov){hov=p;if(sel<0)computeFocus();req();}
  if(p>=0){const n=NODES[p];tip.style.opacity=1;tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY+14)+'px';
    const K=['skill type','domain','category','ISCO group','occupation','skill'];
    tip.textContent=n[5]+' · '+K[n[3]]+(n[6]?(' — '+(n[6].length>96?n[6].slice(0,94)+'…':n[6])):'');}
  else tip.style.opacity=0;
});
cv.addEventListener('wheel',e=>{e.preventDefault();const s=e.deltaY<0?1.12:1/1.12;
  const wx=(e.clientX-view.x)/view.k,wy=(e.clientY-view.y)/view.k;view.k*=s;
  view.x=e.clientX-wx*view.k;view.y=e.clientY-wy*view.k;req();},{passive:false});
addEventListener('keydown',e=>{if(e.key==='Escape'){document.getElementById('q').value='';matches=new Set();matchList=[];
  document.getElementById('qinfo').textContent='';sel=-1;computeFocus();updateDetail();req();}});
function updateDetail(){const el=document.getElementById('detail');if(sel<0){el.style.display='none';return;}
  const n=NODES[sel];const K=['skill type','functional domain','skill category','ISCO group','occupation','skill'];
  let h='<span class="x" id="dx">✕</span><b>'+esc(n[5])+'</b> <span class="kind">· '+K[n[3]]+'</span>';
  if(n[4]>=0&&DOMAINS[n[4]])h+='<div class="meta">domain — '+esc(DOMAINS[n[4]])+'</div>';
  if(n[8])h+='<div class="meta">'+(n[8]==='hard'?'hard skill':'soft skill')+'</div>';
  if(n[7])h+='<div class="meta">Wikidata — '+esc(n[7])+'</div>';
  if(n[6])h+='<div class="desc">'+esc(n[6])+'</div>';
  else h+='<div class="desc" style="opacity:.6">(no definition)</div>';
  el.innerHTML=h;el.style.display='block';
  document.getElementById('dx').addEventListener('click',()=>{sel=-1;computeFocus();updateDetail();req();});}
function runSearch(){const v=document.getElementById('q').value.trim().toLowerCase();
  matches=new Set();matchList=[];
  if(v.length>=2){for(let i=0;i<NODES.length;i++){if((NODES[i][5]||'').toLowerCase().includes(v)){matches.add(i);matchList.push(i);}}}
  document.getElementById('qinfo').textContent=v.length>=2?(matchList.length+' match'+(matchList.length!==1?'es':'')):'';
  if(matchList.length){let best=matchList[0];for(const i of matchList){if((NODES[i][5]||'').length<(NODES[best][5]||'').length)best=i;}
    const n=NODES[best];view.k=Math.max(view.k,0.55);view.x=W/2-n[0]*view.k;view.y=H/2-n[1]*view.k;
    sel=best;computeFocus();updateDetail();}
  req();}
document.getElementById('q').addEventListener('input',runSearch);
['tax','occ','lab'].forEach(id=>document.getElementById(id).addEventListener('change',req));
document.getElementById('fit').addEventListener('click',()=>{const q=document.getElementById('q');q.value='';
  matches=new Set();matchList=[];document.getElementById('qinfo').textContent='';sel=-1;updateDetail();computeFocus();fit();});
hint.textContent='Zoom in to reveal individual skills and their links';
resize();fit();
</script></body></html>"""


def write_full_html(nodes, edges, path):
    narr, earr, dom_names = _full_data(nodes, edges)
    nodes_js = json.dumps(narr, ensure_ascii=False).replace("<", "\\u003c")
    doms_js = json.dumps(dom_names, ensure_ascii=False).replace("<", "\\u003c")
    html = (_FULL_HTML
            .replace("%NODES%", nodes_js)
            .replace("%EDGES%", json.dumps(earr, separators=(",", ":")))
            .replace("%DOMAINS%", doms_js)
            .replace("%NNODES%", f"{len(narr):,}")
            .replace("%NEDGES%", f"{len(earr):,}"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return {"full_nodes": len(narr), "full_edges": len(earr)}
