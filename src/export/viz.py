"""Self-contained interactive HTML overview of the KB graph.

A full 11k-node render is unreadable, so this materializes the **navigable backbone** —
skill types ↔ domains ↔ categories, the ISCO occupation tree, and occupations linked to their functional
domain (~300 nodes) — with category nodes sized by how many skills they carry. Rendering is a small inline
vanilla-JS canvas force layout (drag / pan / zoom / hover); the page embeds its own data and script, so it
opens in any browser with **no server, no internet, no external library**. The heavy full graph lives in
the GraphML/JSON/RDF exports for analytical tools.
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
    data = json.dumps({"nodes": vnodes, "edges": vedges}, ensure_ascii=False)
    html = (_HTML.replace("%DATA%", data)
                 .replace("%COUNT%", str(len(vnodes)))
                 .replace("%FULL%", f"{len(nodes):,}-node"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return {"viz_nodes": len(vnodes), "viz_edges": len(vedges)}
