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
    dom_ang = {d: 2 * math.pi * i / max(1, len(domains)) for i, d in enumerate(domains)}
    dom_idx = {d: i for i, d in enumerate(domains)}
    pos, dom_of = {}, {}

    for i, t in enumerate([n["id"] for n in nodes if n["kind"] == "skill_type"]):
        pos[t] = ((-1) ** i * 140.0, 0.0)
    for d, a in dom_ang.items():
        pos[d] = (900 * math.cos(a), 900 * math.sin(a))
        dom_of[d] = d
    cats_by_dom = defaultdict(list)
    for c in [n["id"] for n in nodes if n["kind"] == "skill_category"]:
        cats_by_dom[cat_dom.get(c)].append(c)
    for d, clist in cats_by_dom.items():
        base = dom_ang.get(d, 0.0)
        for j, c in enumerate(clist):
            a = base + (j - (len(clist) - 1) / 2) * (0.55 / max(1, len(clist)))
            pos[c] = (1650 * math.cos(a), 1650 * math.sin(a))
            dom_of[c] = d
    skills_by_cat = defaultdict(list)
    for s in [n["id"] for n in nodes if n["kind"] == "skill"]:
        skills_by_cat[skill_cat.get(s)].append(s)
    GOLD = 2.399963229728653
    for c, slist in skills_by_cat.items():
        cx, cy = pos.get(c, (0.0, 0.0))
        k = len(slist)
        rad = 70 + 26 * math.sqrt(k)
        for j, s in enumerate(slist):
            r = rad * math.sqrt((j + 0.5) / k)
            a = j * GOLD
            pos[s] = (cx + r * math.cos(a), cy + r * math.sin(a))
            dom_of[s] = cat_dom.get(c)
    occ_by_dom = defaultdict(list)
    for o in [n["id"] for n in nodes if n["kind"] == "occupation"]:
        occ_by_dom[occ_dom.get(o)].append(o)
    for d, olist in occ_by_dom.items():
        base = dom_ang.get(d, 0.0)
        for j, o in enumerate(olist):
            a = base + (j - (len(olist) - 1) / 2) * 0.02
            rr = 2750 + (j % 8) * 55
            pos[o] = (rr * math.cos(a), rr * math.sin(a))
            dom_of[o] = d
    for j, ic in enumerate([n["id"] for n in nodes if n["kind"] == "isco_group"]):
        a = 2 * math.pi * j / max(1, len([n for n in nodes if n["kind"] == "isco_group"]))
        pos[ic] = (330 * math.cos(a), 330 * math.sin(a))
    # any leftover (unclustered) node -> far ring, so nothing is dropped
    leftover = [n["id"] for n in nodes if n["id"] not in pos]
    for j, m in enumerate(leftover):
        a = 2 * math.pi * j / max(1, len(leftover))
        pos[m] = (4200 * math.cos(a), 4200 * math.sin(a))
    return pos, {nid: dom_idx.get(dom_of.get(nid), -1) for nid in byid}


def _full_data(nodes, edges):
    pos, dom_of = _full_layout(nodes, edges)
    idx = {n["id"]: i for i, n in enumerate(nodes)}
    _r = {0: 24.0, 1: 15.0, 2: 9.0, 3: 7.0, 4: 4.5, 5: 2.6}
    narr = []
    for n in nodes:
        x, y = pos[n["id"]]
        k = _KIND_IDX[n["kind"]]
        narr.append([round(x, 1), round(y, 1), _r[k], k, dom_of.get(n["id"], -1),
                     n.get("label_en") or n.get("label_fr") or n["id"]])
    earr = [[idx[e["source"]], idx[e["target"]], 0 if e["type"] in ("broader", "in_domain") else 1]
            for e in edges]
    return narr, earr


_FULL_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JobKB — full knowledge graph</title>
<style>
  :root{color-scheme:light dark}
  html,body{margin:0;height:100%;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;overflow:hidden}
  canvas{display:block;width:100vw;height:100vh;cursor:grab}
  #panel{position:fixed;top:12px;left:12px;background:rgba(255,255,255,.94);color:#111;border-radius:10px;
    padding:12px 14px;font-size:13px;box-shadow:0 2px 14px rgba(0,0,0,.2);max-width:290px}
  @media (prefers-color-scheme:dark){#panel{background:rgba(26,28,32,.94);color:#eee}}
  #panel h1{font-size:14px;margin:0 0 6px}
  #panel label{display:block;margin:4px 0;cursor:pointer}
  #panel .k{display:flex;align-items:center;gap:7px;margin:2px 0;font-size:12px}
  #panel .dot{width:11px;height:11px;border-radius:50%;flex:0 0 auto}
  #panel .muted{opacity:.72;font-size:11.5px;margin-top:8px;line-height:1.4}
  #panel button{margin-top:8px;font:inherit;padding:3px 9px;border-radius:6px;border:1px solid #8887;
    background:transparent;color:inherit;cursor:pointer}
  #tip{position:fixed;pointer-events:none;background:#111;color:#fff;padding:5px 9px;border-radius:6px;
    font-size:12px;opacity:0;transition:opacity .08s;max-width:340px;z-index:9}
</style></head>
<body><canvas id="c"></canvas>
<div id="panel"><h1>JobKB — full graph</h1>
  <div style="font-size:12px;opacity:.85">%NNODES% nodes · %NEDGES% edges</div>
  <label><input type="checkbox" id="tax" checked> taxonomy / domain edges</label>
  <label><input type="checkbox" id="occ"> occupation→skill edges</label>
  <label><input type="checkbox" id="lab" checked> hub labels</label>
  <button id="fit">reset view</button>
  <div class="k" style="margin-top:9px"><span class="dot" style="background:#8250df"></span>skill type</div>
  <div class="k"><span class="dot" style="background:#4e79a7"></span>domain / category / skill (by domain hue)</div>
  <div class="k"><span class="dot" style="background:#bc4c00"></span>ISCO group</div>
  <div class="muted">Each cluster is a category; its cloud is that category's skills. Occupations ring the
    outside by domain. Drag = pan · scroll = zoom · hover a node to highlight its links.</div>
</div><div id="tip"></div>
<script>
const NODES=%NODES%, EDGES=%EDGES%;
const PAL=['#4e79a7','#f28e2b','#59a14f','#e15759','#b07aa1','#9c755f','#ff9da7','#76b7b2','#edc948','#bab0ac'];
function color(n){const k=n[3];if(k===0)return'#8250df';if(k===3)return'#bc4c00';return n[4]>=0?PAL[n[4]%10]:'#8a8a8a';}
const cv=document.getElementById('c'),ctx=cv.getContext('2d'),tip=document.getElementById('tip');
let W,H,DPR;function resize(){DPR=devicePixelRatio||1;W=innerWidth;H=innerHeight;cv.width=W*DPR;cv.height=H*DPR;
  ctx.setTransform(DPR,0,0,DPR,0,0);req();}addEventListener('resize',resize);
// adjacency for hover highlight
const adj=NODES.map(()=>[]);for(let i=0;i<EDGES.length;i++){const e=EDGES[i];adj[e[0]].push(i);adj[e[1]].push(i);}
let view={x:0,y:0,k:1};
function fit(){let a=1e9,b=1e9,c=-1e9,d=-1e9;for(const n of NODES){a=Math.min(a,n[0]);b=Math.min(b,n[1]);c=Math.max(c,n[0]);d=Math.max(d,n[1]);}
  const k=0.92*Math.min(W/(c-a||1),H/(d-b||1));view.k=k;view.x=W/2-(a+c)/2*k;view.y=H/2-(b+d)/2*k;req();}
const S=n=>[n[0]*view.k+view.x,n[1]*view.k+view.y];
let hov=-1,dirty=true,rafid=0;function req(){if(!rafid)rafid=requestAnimationFrame(draw);}
const showTax=()=>document.getElementById('tax').checked,showOcc=()=>document.getElementById('occ').checked,
      showLab=()=>document.getElementById('lab').checked;
function draw(){rafid=0;ctx.clearRect(0,0,W,H);
  // edges (culled to viewport for speed)
  const hi=new Set(hov>=0?adj[hov]:[]);
  ctx.lineWidth=Math.min(1.2,1/view.k*0.9);
  for(let i=0;i<EDGES.length;i++){const e=EDGES[i];if(hi.has(i))continue;
    if(e[2]===0){if(!showTax())continue;}else{if(!showOcc())continue;}
    const A=NODES[e[0]],B=NODES[e[1]];const ax=A[0]*view.k+view.x,ay=A[1]*view.k+view.y,bx=B[0]*view.k+view.x,by=B[1]*view.k+view.y;
    if((ax<0&&bx<0)||(ax>W&&bx>W)||(ay<0&&by<0)||(ay>H&&by>H))continue;
    ctx.strokeStyle=e[2]===0?'rgba(120,120,130,.30)':'rgba(180,150,90,.16)';
    ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(bx,by);ctx.stroke();}
  // nodes
  for(let i=0;i<NODES.length;i++){const n=NODES[i];const sx=n[0]*view.k+view.x,sy=n[1]*view.k+view.y;
    if(sx<-20||sx>W+20||sy<-20||sy>H+20)continue;
    let r=Math.max(1.1,n[2]*Math.min(1.6,Math.sqrt(view.k)));ctx.beginPath();ctx.arc(sx,sy,r,0,7);
    ctx.fillStyle=color(n);ctx.globalAlpha=(hov>=0&&i!==hov&&!hi_has_node(i))?0.25:1;ctx.fill();ctx.globalAlpha=1;}
  // highlighted incident edges + neighbor ring on hover
  if(hov>=0){const n0=NODES[hov];ctx.lineWidth=1.4;
    for(const ei of adj[hov]){const e=EDGES[ei];const A=NODES[e[0]],B=NODES[e[1]];
      ctx.strokeStyle=e[2]===0?'rgba(30,120,60,.9)':'rgba(200,120,20,.85)';
      ctx.beginPath();ctx.moveTo(...S(A));ctx.lineTo(...S(B));ctx.stroke();}
    const [hx,hy]=S(n0);ctx.beginPath();ctx.arc(hx,hy,Math.max(4,n0[2]*1.6),0,7);ctx.lineWidth=2;ctx.strokeStyle='#111';ctx.stroke();}
  // hub labels
  if(showLab()){ctx.fillStyle=getComputedStyle(document.body).color;ctx.textAlign='center';
    for(const n of NODES){if(n[3]<=2&&(n[3]<=1||view.k>0.12)){const[sx,sy]=S(n);
      ctx.font=(n[3]===0?14:n[3]===1?12:10)+'px system-ui';ctx.fillText(n[5],sx,sy-n[2]*1.4-2);}}}
}
let hoverset=new Set();function hi_has_node(i){return hoverset.has(i);}
function computeHoverSet(){hoverset=new Set();if(hov>=0){hoverset.add(hov);for(const ei of adj[hov]){const e=EDGES[ei];hoverset.add(e[0]);hoverset.add(e[1]);}}}
function pick(mx,my){let best=-1,bd=1e9;for(let i=0;i<NODES.length;i++){const n=NODES[i];const sx=n[0]*view.k+view.x,sy=n[1]*view.k+view.y;
  const dx=sx-mx,dy=sy-my,d=dx*dx+dy*dy;const rr=Math.max(5,n[2]*Math.sqrt(view.k)+3);if(d<rr*rr&&d<bd){bd=d;best=i;}}return best;}
let pan=null;
cv.addEventListener('mousedown',e=>{pan={x:e.clientX-view.x,y:e.clientY-view.y};cv.style.cursor='grabbing';});
addEventListener('mouseup',()=>{pan=null;cv.style.cursor='grab';});
addEventListener('mousemove',e=>{
  if(pan){view.x=e.clientX-pan.x;view.y=e.clientY-pan.y;req();tip.style.opacity=0;return;}
  const p=pick(e.clientX,e.clientY);
  if(p!==hov){hov=p;computeHoverSet();req();}
  if(p>=0){const n=NODES[p];tip.style.opacity=1;tip.style.left=(e.clientX+13)+'px';tip.style.top=(e.clientY+13)+'px';
    const K=['skill type','domain','category','ISCO group','occupation','skill'];tip.textContent=n[5]+' · '+K[n[3]];}
  else tip.style.opacity=0;
});
cv.addEventListener('wheel',e=>{e.preventDefault();const s=e.deltaY<0?1.12:1/1.12;
  const wx=(e.clientX-view.x)/view.k,wy=(e.clientY-view.y)/view.k;view.k*=s;
  view.x=e.clientX-wx*view.k;view.y=e.clientY-wy*view.k;req();},{passive:false});
['tax','occ','lab'].forEach(id=>document.getElementById(id).addEventListener('change',req));
document.getElementById('fit').addEventListener('click',fit);
resize();fit();
</script></body></html>"""


def write_full_html(nodes, edges, path):
    narr, earr = _full_data(nodes, edges)
    # escape '<' so a label containing "</script>" can't break out of the inline <script> block
    nodes_js = json.dumps(narr, ensure_ascii=False).replace("<", "\\u003c")
    html = (_FULL_HTML
            .replace("%NODES%", nodes_js)
            .replace("%EDGES%", json.dumps(earr, separators=(",", ":")))
            .replace("%NNODES%", f"{len(narr):,}")
            .replace("%NEDGES%", f"{len(earr):,}"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return {"full_nodes": len(narr), "full_edges": len(earr)}
