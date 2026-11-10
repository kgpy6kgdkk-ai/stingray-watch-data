/* Stingray Watch glossary overlay (embed 07) script, inlined by build_watch_glossary.py. __RAW__ is the raw.githubusercontent base for main. */
(function(){
var g=document.getElementById("glossary");if(!g)return;
var RAW="__RAW__",loaded=false;
function q(sel,root){return Array.prototype.slice.call((root||g).querySelectorAll(sel));}
function setTop(){var t=g.querySelector(".fs-g-top");if(t)g.style.setProperty("--g-top",t.offsetHeight+"px");}
window.fsCloseGlossary=function(){g.style.display="none";document.body.style.overflow="";tvStop();};
window.fsOpenGlossary=function(){if(window.gtag){gtag("event","glossary_open",{});}
g.style.display="block";document.body.style.overflow="hidden";g.scrollTop=0;setTop();refresh();tvStart();};
window.addEventListener("resize",function(){if(g.style.display!=="none")setTop();});
document.addEventListener("keydown",function(e){if(e.key==="Escape"&&g.style.display!=="none"){window.fsCloseGlossary();}});

var ICO='<svg class="fs-copy-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg><svg class="fs-copy-check" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg><span class="fs-copy-tip">copied</span>';
function txt(r){var d=r.querySelector(".fs-g-def").cloneNode(true),m=d.querySelector("a");if(m)d.removeChild(m);
var c=r.querySelector(".fs-g-chip");r._t=(r.querySelector(".fs-g-name").textContent+" "+d.textContent+" "+(c?c.textContent:"")).toLowerCase();}
q("[data-find]").forEach(function(r){var nm=r.querySelector(".fs-g-name").textContent,b=document.createElement("button");
b.type="button";b.className="fs-copy-btn";b.setAttribute("data-copy",r.id);b.setAttribute("aria-label","Copy link to "+nm);b.innerHTML=ICO;r.appendChild(b);
var a=r.querySelector(".fs-gloss-more");if(a)a.setAttribute("aria-label","full page: "+nm);txt(r);});
/* search: name + full definition (hidden tail included) + category, not just the visible line */
var input=document.getElementById("fs-glossary-search"),none=document.getElementById("fs-glossary-noresults");
if(input)input.addEventListener("input",function(){
var f=input.value.trim().toLowerCase(),any=0;
q("[data-find]").forEach(function(r){var hit=!f||r._t.indexOf(f)>-1;r.classList.toggle("fs-g-hide",!hit);if(hit)any++;});
q(".fs-g-letter").forEach(function(l){l.classList.toggle("fs-g-hide",!l.querySelector("[data-find]:not(.fs-g-hide)"));});
q(".fs-g-sec").forEach(function(s){if(s.querySelector("[data-find]"))s.classList.toggle("fs-g-hide",!s.querySelector("[data-find]:not(.fs-g-hide)"));});
if(none)none.hidden=!!any;
});

/* letters scroll inside the overlay; no hash change, so Carrd's section router never fires */
g.addEventListener("click",function(e){
var b=e.target.closest&&e.target.closest("[data-jump]");
if(b){var el=document.getElementById(b.getAttribute("data-jump"));
if(el){var rm=window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches;el.scrollIntoView({behavior:rm?"auto":"smooth",block:"start"});}return;}
var c=e.target.closest&&e.target.closest("[data-copy]");
if(c){if(window.fsCopyLink)window.fsCopyLink(c.getAttribute("data-copy"),"","",c);return;}
var a=e.target.closest&&e.target.closest("a.fs-gloss-more,a.fs-gloss-all");
if(a&&window.gtag){gtag("event","glossary_page_click",{term_slug:a.getAttribute("data-term")||"all",link_url:a.href,link_domain:"feed.stingrayfraud.com"});}
});

/* glossary_term_view {term_slug, view_trigger}: which terms visitors actually read.
   Nothing visible changes. At most one event per term per tab session (sessionStorage,
   in-memory if that's blocked). Triggers:
   - deep_link: the overlay opens on a #glossary-<slug> link (Watch's deep-link code opens it).
   - dwell: one term at a time, the one under the reading line (45% down the overlay), stays
     there for 3s while the overlay is open and the tab is visible. Counted only after the
     visitor has scrolled, clicked, typed or searched in the overlay, so opening it, the
     deep-link scroll, and scrolling past send nothing.
   - search: the search narrows to exactly one term and the box settles for 1.2s.
   The search text is never sent. */
var TV_KEY="fsGlossSeen",TV_DWELL=3000,TV_SETTLE=1200,seen={},armed=0,cand=null,since=0,tick=null,settle=null;
try{(JSON.parse(sessionStorage.getItem(TV_KEY))||[]).forEach(function(s){seen[s]=1;});}catch(e){}
function termView(r,how){if(!r||!r.id||r.id.indexOf("glossary-")!==0||!g.contains(r))return;
var s=r.id.slice(9);if(seen[s])return;seen[s]=1;
try{sessionStorage.setItem(TV_KEY,JSON.stringify(Object.keys(seen)));}catch(e){}
if(window.gtag){gtag("event","glossary_term_view",{term_slug:s,view_trigger:how});}}
function arm(){if(!armed)armed=1;}
function sample(){if(!armed||document.hidden||g.style.display==="none"){cand=null;return;}
var b=g.querySelector(".fs-g-body").getBoundingClientRect(),gr=g.getBoundingClientRect();
var el=document.elementFromPoint(b.left+b.width/2,gr.top+gr.height*0.45),r=el&&el.closest&&el.closest("[data-find]");
if(!r||!g.contains(r))return; /* a gap between rows: keep the current candidate */
var now=Date.now();if(r!==cand){cand=r;since=now;return;}
if(now-since>=TV_DWELL){termView(r,"dwell");}}
function tvStart(){armed=0;cand=null;
var h=(location.hash||"").slice(1);if(h.indexOf("glossary-")===0)termView(document.getElementById(h),"deep_link");
if(!tick)tick=setInterval(sample,500);}
function tvStop(){clearInterval(tick);tick=null;clearTimeout(settle);cand=null;}
/* armed by the visitor's own input only */
["wheel","touchstart","pointerdown","keydown"].forEach(function(t){g.addEventListener(t,arm,{passive:true});});
document.addEventListener("visibilitychange",function(){cand=null;});
if(input)input.addEventListener("input",function(){arm();clearTimeout(settle);settle=setTimeout(function(){
var v=q("[data-find]:not(.fs-g-hide)");if(input.value.trim()&&v.length===1)termView(v[0],"search");},TV_SETTLE);});

/* live refresh on first open: counts + sparklines from archive.json, wording from glossary.json.
   The static markup is the fallback; if either fetch fails nothing changes. */
function slug(s){return String(s||"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,80);}
/* 55 = LEAD_MIN in build_watch_glossary.py */
function split(d){var i=d.indexOf(" — ");return i>=55?[d.slice(0,i),d.slice(i)]:[d,""];}
function refresh(){if(loaded)return;loaded=true;
fetch(RAW+"archive.json").then(function(r){return r.json();}).then(function(data){
var board=document.getElementById("fs-glossary-core"),items=data.items||[];if(!board||!items.length)return;
var first=items.reduce(function(m,i){return i.published<m?i.published:m;},"9999").slice(0,7),now=new Date(),months=[];
var y=+first.slice(0,4),mo=+first.slice(5,7);
while(y<now.getUTCFullYear()||(y===now.getUTCFullYear()&&mo<=now.getUTCMonth()+1)){months.push(y+"-"+(mo<10?"0":"")+mo);if(++mo>12){mo=1;y++;}}
var mc={};items.forEach(function(i){var k=i.vector+"|"+i.published.slice(0,7);mc[k]=(mc[k]||0)+1;});
var rows=q(".fs-g-vrow",board),peak=1,speak=1,data2=rows.map(function(r){var v=r.getAttribute("data-vector");
var c=months.map(function(m){return mc[v+"|"+m]||0;}),t=c.reduce(function(a,b){return a+b;},0);
peak=Math.max(peak,t);speak=Math.max(speak,Math.max.apply(null,c));return {r:r,c:c,t:t,n:r.querySelector(".fs-g-name").textContent};});
data2.sort(function(a,b){return b.t-a.t||a.n.localeCompare(b.n);});
var ML=["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"];
data2.forEach(function(d){var n=d.c.length,xs=[],ys=[];
d.c.forEach(function(v,i){xs.push(3+(n>1?i*78/(n-1):39));ys.push(23-20*v/speak);});
var pts=xs.map(function(x,i){return x.toFixed(1)+","+ys[i].toFixed(1);});
var tip="by month: "+d.c.map(function(v,i){return ML[+months[i].slice(5)-1]+" "+v;}).join(", ");
var s=d.r.querySelector(".fs-g-spark");
s.setAttribute("aria-label",tip);s.querySelector("title").textContent=tip;
s.querySelector("polyline").setAttribute("points",pts.join(" "));
s.querySelector(".area").setAttribute("d","M"+xs[0].toFixed(1)+",23 L"+pts.join(" L")+" L"+xs[n-1].toFixed(1)+",23 Z");
var dot=s.querySelector("circle");dot.setAttribute("cx",xs[n-1].toFixed(1));dot.setAttribute("cy",ys[n-1].toFixed(1));
d.r.querySelector(".fs-g-num").textContent=d.t;d.r.querySelector(".fs-g-fill").style.width=(100*d.t/peak).toFixed(1)+"%";
board.appendChild(d.r);});
}).catch(function(){});
fetch(RAW+"glossary.json").then(function(r){return r.json();}).then(function(data){
if(!data.terms||data.updated===g.getAttribute("data-updated"))return;
data.terms.forEach(function(t){var r=document.getElementById("glossary-"+slug(t.name));if(!r)return;
var p=split(t.definition||"");r.querySelector(".fs-g-lead").textContent=p[0];r.querySelector(".fs-g-tail").textContent=p[1];txt(r);
});
}).catch(function(){});
}
})();
