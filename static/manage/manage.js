'use strict';
// 视图与接口分开：图谱、列表和搜索共享同一空间，不使用演示数据冒充数据库。
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icons = {
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
  palette:'<path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 1-3.7c-1-.7-.6-2.3.7-2.3H17a4 4 0 0 0 4-4 9 9 0 0 0-9-8Z"/><circle cx="7" cy="11" r=".7"/><circle cx="9" cy="7" r=".7"/><circle cx="14" cy="6.5" r=".7"/><circle cx="17" cy="10" r=".7"/>',
  grid:'<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  edit:'<path d="m15 4 5 5-11 11-6 1 1-6Z"/><path d="m13 6 5 5"/>',
  globe:'<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
  pause:'<path d="M8 5v14M16 5v14" stroke-width="3"/>',
  play:'<path d="m8 4 12 8-12 8Z"/>',
  reset:'<path d="M4 10a8 8 0 1 1 1 7M4 4v6h6"/>',
  list:'<path d="M9 6h12M9 12h12M9 18h12M3 6h1M3 12h1M3 18h1"/>',
  shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
  file:'<path d="M14 3H5v18h14V8Z"/><path d="M14 3v5h5M8 12h8M8 16h8"/>'
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.file}</svg>`;
function hydrateIcons(root=document) { root.querySelectorAll('[data-icon]').forEach(e => { e.innerHTML=icon(e.dataset.icon); }); }
const defaults = () => ({exposure:1,theme:'blue',custom_color:'#102A48',paused:false,reduced_motion:false});
const state = {user:null,space:'personal',category:null,nodes:[],publicCategories:[],personalCategories:[],selected:null,
  appearance:defaults(),savedAppearance:defaults(),page:1,items:[],search:null,question:'',mode:'semantic',view:'graph',
  phase:0,zoom:1,hover:false,modal:false,nav:0,adminTab:'planets',editing:null,detail:null,register:false};
let actionSubmit=null, toastTimer, previewBefore=null;

async function api(path, options={}) {
  const epoch=state.epoch||0;
  const response = await fetch(path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});
  let data; try { data=await response.json(); } catch { data={detail:'服务器暂时不可用'}; }
  if(epoch!==(state.epoch||0))throw new Error('登录状态已改变，请重新操作');
  if(!response.ok){
    if(response.status===401 && state.user) { signedOut(); toast('登录已过期，请重新登录'); }
    const error=new Error(typeof data.detail==='string'?data.detail:('输入不符合要求，请检查表单。'));
    error.status=response.status; throw error;
  }
  return data;
}
const send = (path,body,method='POST') => api(path,{method,body:JSON.stringify(body)});
function toast(message){$('toast').textContent=message;$('toast').classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.add('hidden'),4500);}
function report(error){toast(error.message||'操作失败，请重试');}
const date = value => value?new Date(value).toLocaleDateString('zh-CN'):'';
function show(id,on=true){$(id).classList.toggle('hidden',!on);}
function safeUrl(url){try{const u=new URL(url);return /^https?:$/.test(u.protocol)&&!u.username&&!u.password?u.href:null;}catch{return null;}}
function dialog(id){const d=$(id);if(!d.open)d.showModal();state.modal=true;}
function closeDialog(id){$(id).close();state.modal=!!document.querySelector('dialog[open]');}
function buttonBusy(button,busy){if(button)button.disabled=busy;}

function applyAppearance(value){
  state.appearance={...defaults(),...value};
  const colors={blue:'#163b70',purple:'#563268',teal:'#1c655d',black:'#353943'};
  const accents={blue:[52,136,255],purple:[155,108,232],teal:[30,181,160],black:[116,143,177]};
  const hex=state.appearance.theme==='custom'?state.appearance.custom_color:(colors[state.appearance.theme]||colors.blue);
  const rgb=[1,3,5].map(n=>parseInt(hex.slice(n,n+2),16));
  const tint=state.appearance.theme==='custom'?rgb.map(c=>Math.max(65,c)):accents[state.appearance.theme]||accents.blue;
  const root=document.documentElement;
  root.style.setProperty('--tint',tint.join(','));
  root.style.setProperty('--accent',`rgb(${tint.map(c=>Math.min(245,Math.round(c*.55+110))).join(',')})`);
  root.style.setProperty('--bg',`rgb(${rgb.map(c=>Math.round(c*.1+3)).join(',')})`);
  root.style.setProperty('--panel',`rgb(${rgb.map(c=>Math.round(c*.16+9)).join(',')})`);
  root.style.setProperty('--exposure',state.appearance.exposure);
  document.body.classList.toggle('reduce-motion',state.appearance.reduced_motion);
  updatePause();
}
function updatePause(){
  const reduced=motionReduced(),paused=state.appearance.paused||reduced;
  $('pause-orbit').disabled=reduced;
  $('pause-orbit').title=reduced?'减少动态效果已开启，可在外观设置中调整':'';
  $('pause-orbit').innerHTML=icon(paused?'play':'pause')+`<span>${reduced?'静态图谱':paused?'恢复环绕':'暂停环绕'}</span>`;
}

function signedOut(){
  state.nav++;state.epoch=(state.epoch||0)+1;state.user=null;state.items=[];state.nodes=[];state.edges=[];state.search=null;state.chat=null;state.detail=null;state.pendingQuestion=null;state.question='';state.lastSelected={};state.personalCategories=[];previewBefore=null;
  for(const id of ['inspector-content','knowledge-results','category-list','orbit-nodes','detail-content','admin-content'])$(id).innerHTML='';
  $('category-question').value='';$('top-question').value='';$('auth-form').elements.password.value='';
  document.querySelectorAll('dialog[open]').forEach(d=>d.close());state.modal=false;
  applyAppearance(defaults());show('app',false);show('boot',false);show('auth');
  $('profile-menu').classList.add('hidden');
}
async function signedIn(user){
  state.epoch=(state.epoch||0)+1;state.user=user;
  const [appearance]=await Promise.all([api('/api/appearance'),refreshCategories()]);
  state.savedAppearance={...appearance};applyAppearance(appearance);
  $('profile-name').textContent=user.username;$('username-label').textContent=user.username+' 的空间';
  $('profile-button').textContent=user.username.slice(0,1).toUpperCase();show('admin-nav',user.role==='admin');
  show('boot',false);show('auth',false);show('app');window.scrollTo({top:0,left:0});
  if(!location.hash)location.hash='#/personal';else await route();
  api('/ai/status').then(info=>{$('model-status').textContent=info.embedding.configured?'本地语义模型已连接':'关键词搜索可用 · 语义模型待连接';}).catch(()=>{});
}
async function refreshCategories(){
  const [personal,pub]=await Promise.all([api('/api/personal/categories'),api('/api/admin/categories')]);
  state.personalCategories=personal.items;state.publicCategories=pub.items;
}
async function loadUniverse(){
  const result=await api('/api/universe?space='+state.space);state.nodes=result.nodes;state.edges=result.edges||[];
  $('total-count').innerHTML=`${result.total.toLocaleString()} <small>条知识</small>`;
  renderSidebar();renderOrbits();return result;
}
function renderSidebar(){
  const personal=state.space==='personal';
  $('category-heading').textContent=personal?'我的门类':'公共门类';
  $('space-description').textContent=personal?'你的个人知识空间':'所有人共同分享的知识';
  show('new-category',personal);show('manage-category',personal&&state.category!==null);
  const cats=personal?state.personalCategories:state.publicCategories;
  $('category-list').innerHTML=cats.map(c=>{
    const node=state.nodes.find(n=>n.id===c.id),count=personal?(node?.count??0):c.count;
    return `<button class="category-item ${state.category===c.id?'active':''}" data-category="${c.id}" title="${esc(c.name)}"><span class="category-dot" style="color:${esc(personal?c.color:'#74dcff')}"></span><span>${esc(c.name)}</span><b>${count}</b></button>`;
  }).join('')||'<p class="tiny muted" style="padding:12px">尚无门类，点击＋创建</p>';
  $('category-list').querySelectorAll('[data-category]').forEach(b=>b.onclick=()=>navigateCategory(Number(b.dataset.category)));
}
function currentCategory(){return (state.space==='personal'?state.personalCategories:state.publicCategories).find(c=>c.id===state.category);}

async function route(){
  if(!state.user)return;
  window.scrollTo({top:0,left:0});
  const ticket=++state.nav,parts=location.hash.replace(/^#\//,'').split('/');
  state.view=parts[0]==='admin'?'admin':parts[1]==='category'||parts[1]==='list'?'list':'graph';
  state.space=parts[0]==='public'||parts[0]==='admin'?'public':'personal';show('profile-menu',false);
  state.category=parts[1]==='category'?Number(parts[2]):null;
  state.page=1;state.search=null;state.chat=null;state.question='';$('category-question').value='';$('top-question').value='';$('app').classList.remove('chat-open');
  $('app').classList.toggle('admin-mode',state.view==='admin');
  show('graph-view',state.view==='graph');show('knowledge-view',state.view==='list');show('admin-view',state.view==='admin');
  document.querySelectorAll('[data-space]').forEach(e=>e.classList.toggle('active',e.dataset.space===state.space&&state.view!=='admin'));
  try{
    await refreshCategories();if(ticket!==state.nav)return;
    await loadUniverse();if(ticket!==state.nav)return;
    if(state.view==='admin'){
      if(state.user.role!=='admin'){location.hash='#/public';toast('需要管理员权限');return;}
      await renderAdmin();return;
    }
    if(state.view==='list'){
      const cat=currentCategory();
      if(state.category!==null&&!cat){toast('门类不存在或无权访问');location.hash='#/'+state.space;return;}
      $('category-title').textContent=cat?.name||(state.space==='personal'?'我的全部知识':'公有知识星海');
      $('category-caption').textContent=state.space==='personal'?'你的笔记与有效收藏 · 私有内容仅自己可见':'所有用户主动分享的知识 · 点击查看原文与来源';
      $('search-scope').textContent='范围：'+(cat?.name||(state.space==='personal'?'我的知识':'公有知识'));
      $('banner-planet').className='planet '+(cat?.style||(state.space==='personal'?'earth':'sun'));
      $('knowledge-view').classList.remove('enter-category');void $('knowledge-view').offsetWidth;$('knowledge-view').classList.add('enter-category');
      if(state.pendingQuestion){const question=state.pendingQuestion;state.pendingQuestion=null;await runSearch(question);}else await loadItems();
    } else {
      const personal=state.space==='personal';
      $('space-kicker').textContent=personal?'PERSONAL UNIVERSE':'SHARED KNOWLEDGE COSMOS';
      $('graph-title').textContent=personal?'我的知识图谱':'全体知识图谱';
      $('graph-description').textContent=personal?'把知识连接成自己的世界':'探索共同分享的知识';
      $('central-planet').className='planet '+(personal?'earth':'sun');
      $('central-planet').parentElement.classList.toggle('public-center',!personal);
      $('center-label').textContent=personal?'我的星球':'共同的知识星海';
      $('size-legend').innerHTML='<i></i>'+(personal?'光点':'行星')+'大小表示知识条数';
      show('empty-graph',!state.nodes.length);
      if(!state.nodes.length){$('empty-graph').querySelector('h3').textContent=personal?'你的知识星海，从这里开始':'这片星海，等待第一份分享';$('empty-graph').querySelector('p').textContent=personal?'新建一个门类，放入第一份知识。':'分享你的知识，让新的行星亮起来。';$('empty-create').textContent=personal?'＋ 新建门类':'＋ 新建知识';}
      state.selected=state.nodes.find(n=>n.id===state.lastSelected?.[state.space])||state.nodes[0]||null;await renderInspector();
    }
  }catch(error){if(ticket===state.nav){report(error);$('inspector-content').innerHTML=`<div class="error-state">${esc(error.message)}<button id="retry-route">重新加载</button></div>`;$('retry-route').onclick=route;}}
}
function navigateCategory(id){
  state.lastSelected={...state.lastSelected,[state.space]:id};
  state.selected=state.nodes.find(n=>n.id===id)||null;
  document.querySelectorAll('.orbit-node').forEach(e=>e.classList.toggle('selected',Number(e.dataset.id)===id));
  if(state.view==='graph'&&!motionReduced()){
    $('graph-view').classList.add('leaving');const current=state.nav;
    setTimeout(()=>{$('graph-view').classList.remove('leaving');if(current===state.nav)location.hash=`#/${state.space}/category/${id}`;},370);
  }else location.hash=`#/${state.space}/category/${id}`;
}
function renderOrbits(){
  const personal=state.space==='personal';
  const allCounts=(personal?state.nodes:state.publicCategories).map(n=>n.count);
  const max=Math.max(1,...allCounts);
  $('orbit-nodes').innerHTML=state.nodes.map(n=>{
    const ratio=Math.sqrt(n.count/max),diameter=personal?5+ratio*10:33+ratio*40;
    return `<button class="orbit-node" data-id="${n.id}" style="--diameter:${diameter}px;--point-color:${esc(n.color)}" aria-label="${esc(n.name)}，${n.count}条知识，进入门类"><span class="${personal?'point':'planet '+n.style}"></span><span class="node-label">${esc(n.name)}<small>${n.count} 条知识</small></span></button>`;
  }).join('');
  $('orbit-nodes').querySelectorAll('button').forEach(b=>{
    b.onclick=()=>navigateCategory(Number(b.dataset.id));
    b.onpointerenter=()=>selectNode(b);b.onpointerleave=()=>{state.hover=false;};
    b.onfocus=()=>selectNode(b);b.onblur=()=>{state.hover=false;};
  });
  if(!$('graph-links')){$('orbit-content').insertAdjacentHTML('afterbegin','<svg id="graph-links" aria-hidden="true"></svg>');}
  positionNodes();
}
function selectNode(button){state.hover=true;state.selected=state.nodes.find(n=>n.id===Number(button.dataset.id));document.querySelectorAll('.orbit-node').forEach(e=>e.classList.toggle('selected',e===button));renderInspector().catch(report);}
function motionReduced(){return state.appearance.reduced_motion||matchMedia('(prefers-reduced-motion: reduce)').matches;}
function positionNodes(){
  if(state.view!=='graph')return;
  const stage=$('orbit-stage'),w=stage.clientWidth,h=stage.clientHeight;
  const count=state.nodes.length,rings=Math.max(2,Math.ceil(count/5));
  const rmax=Math.max(120,w*.39),rymax=Math.max(135,h*.34);
  const radii=Array.from({length:rings},(_,i)=>({x:rmax*(.75+.25*(i/(rings-1))),y:rymax*(.82+.18*i/(rings-1))}));
  const ringHTML=radii.map(r=>`<i class="orbit-ring" style="width:${r.x*2}px;height:${r.y*2}px"></i>`).join('');
  if($('orbit-rings').dataset.size!==`${w}-${h}-${rings}`){$('orbit-rings').innerHTML=ringHTML;$('orbit-rings').dataset.size=`${w}-${h}-${rings}`;}
  const positions={};
  document.querySelectorAll('.orbit-node').forEach((node,i)=>{
    const ring=i%rings,r=radii[ring],angle=i/count*Math.PI*2-.65+state.phase*(.65+.18*ring);
    const x=r.x*Math.cos(angle),y=r.y*Math.sin(angle);
    const tilt=-.16,xx=x*Math.cos(tilt)-y*Math.sin(tilt),yy=x*Math.sin(tilt)+y*Math.cos(tilt);
    node.style.transform=`translate(calc(-50% + ${xx}px),calc(-50% + ${yy}px))`;
    positions[node.dataset.id]={x:w/2+xx,y:h/2+yy};
  });
  if($('graph-links')){
    $('graph-links').setAttribute('viewBox',`0 0 ${w} ${h}`);
    $('graph-links').innerHTML=(state.edges||[]).filter(e=>e.source===state.selected?.id||e.target===state.selected?.id).map(e=>{const a=positions[e.source],b=positions[e.target];if(!a||!b)return '';return `<path d="M${a.x},${a.y} Q${w/2},${h/2-70} ${b.x},${b.y}"/><text x="${(a.x+b.x)/2}" y="${(a.y+b.y)/2-12}">${esc(e.relation)}</text>`;}).join('');
  }
  $('orbit-content').style.transform=`scale(${state.zoom})`;
}
let lastFrame=0;
function frame(time){
  const delta=lastFrame?Math.min((time-lastFrame)/1000,.05):0;lastFrame=time;
  if(!document.hidden){
    if(state.user&&state.view==='graph'&&!state.hover&&!state.modal&&!state.appearance.paused&&!motionReduced())state.phase+=delta*.028;
    positionNodes();drawStars(time);
  }
  requestAnimationFrame(frame);
}
const starContext=$('stars').getContext('2d');let stars=[];
function resizeStars(){const canvas=$('stars'),dpr=Math.min(devicePixelRatio||1,2);canvas.width=innerWidth*dpr;canvas.height=innerHeight*dpr;starContext.setTransform(dpr,0,0,dpr,0,0);stars=Array.from({length:innerWidth<680?34:90},(_,i)=>({x:(Math.sin(i*127.1)*.5+.5)*innerWidth,y:(Math.cos(i*311.7)*.5+.5)*innerHeight,r:i%9===0?1:.45,phase:i*2.1}));positionNodes();}
function drawStars(t){starContext.clearRect(0,0,innerWidth,innerHeight);for(const s of stars){const glow=motionReduced()?.55:.32+.25*Math.sin(t*.00045+s.phase);starContext.fillStyle=`rgba(153,205,255,${glow})`;starContext.beginPath();starContext.arc(s.x,s.y,s.r,0,Math.PI*2);starContext.fill();}}

async function renderInspector(){
  if(state.view==='list'&&!state.search){
    state.search={search_id:null,question:'',sources:[],needsRetrieval:true,directEntry:true,
      payload:{space:state.space,category_id:state.category}};
  }
  if(state.search)return renderAI();
  $('app').classList.remove('chat-open');
  const node=state.view==='list'?currentCategory():state.selected;
  if(!node){$('inspector-content').innerHTML=`<div class="inspector-card"><div class="inspector-planet planet ${state.space==='personal'?'earth':'sun'}"></div><span class="eyebrow">EXPLORE YOUR UNIVERSE</span><h2>每份知识，皆可成星</h2><p>点击光点或行星进入门类，也可以从左侧列表直接开始。</p><div class="inspector-section"><h3>两种搜索方式</h3><p>关键词适合精确查找，语义搜索帮助理解自然语言问题。</p></div></div>`;return;}
  const nodeId=node.id,scope=state.space;
  const count=node.count??state.nodes.find(n=>n.id===node.id)?.count??0;
  $('inspector-content').innerHTML=`<div class="inspector-card"><div class="inspector-planet planet ${node.style||(state.space==='personal'?'earth':'jupiter')}"></div><span class="eyebrow">KNOWLEDGE COLLECTION</span><h2>${esc(node.name)}</h2><div class="inspector-count">${count}<small>条${state.space==='public'?'公有':''}知识</small></div><p>${state.space==='personal'?'你的记录、整理与收藏，都在这条轨道上。':'来自用户共同分享的知识，查看资料时请留意来源与适用时间。'}</p><button class="primary" id="inspect-enter">进入门类 <span>→</span></button><div class="inspector-section"><h3>最近更新</h3><div id="recent-items"><p>正在读取…</p></div></div></div>`;
  $('inspect-enter').onclick=()=>navigateCategory(nodeId);
  const result=await api(`/api/knowledge?space=${scope}&category_id=${nodeId}&page_size=3`);
  if((state.view==='list'?currentCategory()?.id:state.selected?.id)!==nodeId||scope!==state.space||!$('recent-items'))return;
  $('recent-items').innerHTML=result.items.map(k=>`<button class="inspector-preview" data-open="${k.kid}">${icon('file')}<span>${esc(k.title)}</span>›</button>`).join('')||'<p>这里还没有知识，添加第一条吧。</p>';
  bindOpen($('recent-items'));
}
function bindOpen(root){root.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.open)).catch(report));}
function renderCards(items,total){
  $('result-count').textContent=`${state.search?'找到':'共'} ${total} 条知识`;
  $('result-title').textContent=state.search?'相关知识':state.question?'关键词搜索结果':'门类知识';
  $('knowledge-results').innerHTML=items.map(k=>`<article class="knowledge-card" tabindex="0" role="button" data-open="${k.kid}"><div class="card-top"><h3>${esc(k.title)}</h3><span class="pill ${k.visibility==='private'?'private':''}">${k.hidden?'已下架':k.visibility==='private'?'仅自己可见':'公有知识'}</span></div><p>${esc(k.summary||k.excerpt||'')}</p><div class="card-meta"><span>${esc(k.author||'知识星海')}</span><span>${date(k.updated_at)}</span>${k.bookmarked?'<span class="pill">已收藏</span>':''}<span class="card-link">查看知识 ↗</span></div></article>`).join('')||`<div class="empty-state"><h3>${state.question?'暂未找到相关知识':'这里还没有知识'}</h3><p>${state.question?'换一种描述，或切换关键词搜索试试。':'添加一份知识，让这个门类亮起来。'}</p></div>`;
  bindOpen($('knowledge-results'));$('knowledge-results').querySelectorAll('[data-open]').forEach(e=>e.onkeydown=ev=>{if(ev.key==='Enter'||ev.key===' '){ev.preventDefault();e.click();}});
}
async function loadItems(preserveChat=false){
  const ticket=state.nav,searchTicket=state.searchTicket=(state.searchTicket||0)+1;if(!preserveChat)state.search=null;$('knowledge-results').innerHTML='<div class="loading-state">正在寻找知识…</div>';
  const params=new URLSearchParams({space:state.space,page:state.page,page_size:20,q:state.question});if(state.category!==null)params.set('category_id',state.category);
  const data=await api('/api/knowledge?'+params);if(ticket!==state.nav||searchTicket!==state.searchTicket)return;
  state.items=data.items;renderCards(data.items,data.count);
  const pages=Math.max(1,Math.ceil(data.count/20));$('pagination').innerHTML=pages>1?`<button id="page-prev" ${state.page<=1?'disabled':''}>上一页</button><span>${state.page} / ${pages}</span><button id="page-next" ${state.page>=pages?'disabled':''}>下一页</button>`:'';
  if($('page-prev'))$('page-prev').onclick=()=>{state.page--;loadItems(true).catch(report);};
  if($('page-next'))$('page-next').onclick=()=>{state.page++;loadItems(true).catch(report);};
  if(state.space==='personal'&&!state.question){const lost=await api('/api/unavailable-bookmarks');if(ticket!==state.nav)return;const relevant=lost.items.filter(e=>state.category===null||e.personal_category_id===state.category);if(relevant.length){$('knowledge-results').insertAdjacentHTML('beforeend',relevant.map(k=>`<div class="notice">原文已不可用 · 不参与搜索与计数 <button class="text-button" data-forget="${k.kid}">移除收藏</button></div>`).join(''));$('knowledge-results').querySelectorAll('[data-forget]').forEach(b=>b.onclick=()=>api(`/api/knowledge/${b.dataset.forget}/bookmark`,{method:'DELETE'}).then(loadItems).catch(report));}}
  if(!preserveChat&&state.question&&document.querySelector('input[name=mode]:checked').value==='keyword'){
    const payload={question:state.question,space:state.space,mode:'keyword'};if(state.category!==null)payload.category_id=state.category;
    const result=await send('/ai/search',payload);
    if(ticket!==state.nav||searchTicket!==state.searchTicket)return;
    state.search={...result,question:payload.question,payload};
  }
  renderInspector().catch(report);
}
async function runSearch(question){
  if(!question.trim())return loadItems();
  state.question=question.trim();state.page=1;
  if(state.view!=='list'){
    state.pendingQuestion=question.trim();
    location.hash=`#/${state.space}/list`;
    return;
  }
  $('category-question').value=state.question;$('top-question').value=state.question;
  state.mode=document.querySelector('input[name=mode]:checked').value;
  if(state.mode==='keyword')return loadItems();
  const ticket=state.nav,searchTicket=state.searchTicket=(state.searchTicket||0)+1;
  state.search=null;state.chat=null;
  $('inspector-content').innerHTML='<div class="loading-state">正在更新对话参考资料…</div>';
  $('knowledge-results').innerHTML='<div class="loading-state">本地模型正在理解你的问题…</div>';$('pagination').innerHTML='';
  const payload={question:state.question,space:state.space};if(state.category!==null)payload.category_id=state.category;
  try{
    const result=await send('/ai/search',payload);if(ticket!==state.nav||searchTicket!==state.searchTicket)return;
    const items=await Promise.all(result.sources.map(s=>api('/api/knowledge/'+s.knowledge_id).then(k=>({...k,excerpt:s.excerpt,summary:s.excerpt}))));
    if(ticket!==state.nav||searchTicket!==state.searchTicket)return;
    state.search={...result,question:payload.question,payload};state.items=items;renderCards(items,items.length);renderAI();
  }catch(error){if(ticket!==state.nav||searchTicket!==state.searchTicket)return;$('knowledge-results').innerHTML=`<div class="error-state">${esc(error.message)}<button id="keyword-fallback">切换关键词搜索</button></div>`;$('keyword-fallback').onclick=()=>{document.querySelector('input[value=keyword]').checked=true;loadItems().catch(report);};}
}
function renderAI(){
  const search=state.search;if(!search)return;
  $('app').classList.add('chat-open');
  if(!state.chat||state.chat.searchId!==search.search_id)state.chat={searchId:search.search_id,id:null,turns:0,messages:[],draft:search.question,busy:false,error:'',stale:false};
  const chat=state.chat;
  const scopeName=currentCategory()?.name||(state.space==='personal'?'我的知识':'公有知识');
  const renderMessage=(message)=>{
    const cited=message.sources||[],extra=(message.availableSources||[]).filter(s=>!cited.some(c=>c.knowledge_id===s.knowledge_id));
    const link=s=>`<button data-open="${s.knowledge_id}">[${s.knowledge_id}] ${esc(s.title)} ↗</button>`;
    return `<div class="chat-message ${message.role}"><span class="chat-role">${message.role==='user'?'你':'✧ DeepSeek'}</span>${message.status==='partial'?'<span class="evidence-label">部分资料支持 · 尚需核实</span>':message.status==='insufficient_evidence'?'<span class="evidence-label">暂无直接依据 · 提供核实建议</span>':''}<div class="chat-bubble">${esc(message.content)}</div>${cited.length?`<div class="chat-source-links">${cited.map(link).join('')}</div>`:''}${extra.length?`<details class="chat-available"><summary>其他现有资料（${extra.length}）</summary><div class="chat-source-links">${extra.map(link).join('')}</div></details>`:''}</div>`;
  };
  $('inspector-content').innerHTML=`<div class="inspector-card chat-panel"><div class="chat-heading"><h2>✧ AI 对话</h2><span class="model-pill">DeepSeek</span></div><p class="chat-scope">${search.needsRetrieval?'提问范围：'+esc(scopeName)+' · 可直接提问':search.sources.length?'基于 '+search.sources.length+' 条参考资料 · 支持连续追问':'暂无直接匹配资料 · 可继续提问'}</p><div id="chat-messages" class="chat-messages" role="log" aria-live="polite">${chat.messages.length?chat.messages.map(renderMessage).join(''):`<div class="chat-welcome"><span>✧</span><strong>${search.needsRetrieval?'在这个门类，直接问我':'继续问，知识就在这里'}</strong><p>${search.needsRetrieval?'输入问题，我会在当前范围查找资料并回答。无需先点击搜索。':'可以追问细节、比较差异，或让我换一种方式说明。回答将附上资料来源。'}</p></div>`}${chat.busy?renderMessage({role:'user',content:chat.pending})+'<div class="chat-thinking">'+(chat.stage==='retrieval'?'正在查找当前范围的资料…':'DeepSeek 正在思考…')+'</div>':''}${chat.error?`<div class="chat-error" role="alert">${esc(chat.error)}</div>`:''}</div><form id="chat-form" class="chat-composer"><label class="chat-input-label" for="chat-input">你的问题或追问</label><textarea id="chat-input" rows="3" maxlength="${search.needsRetrieval?500:2000}" placeholder="输入问题，继续追问…" ${chat.busy||chat.stale?'disabled':''}>${esc(chat.draft)}</textarea><div class="chat-composer-actions"><span>Enter 发送 · Shift+Enter 换行</span><button class="primary" type="submit" ${chat.busy||chat.stale?'disabled':''}>${chat.busy?'思考中…':chat.error&&!chat.stale?'重试':'发送 ↑'}</button></div></form>${chat.stale?'<button id="chat-restart" class="outline full">重新搜索，开启新对话</button>':''}<p class="ai-note">${state.space==='personal'?'发送后将相关资料与最近对话交给外部 DeepSeek 服务。':'仅根据当前范围的知识回答；换话题可重新搜索。'}</p></div>`;
  bindOpen($('chat-messages'));
  $('chat-input').oninput=e=>{chat.draft=e.target.value;};
  $('chat-input').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();$('chat-form').requestSubmit();}};
  $('chat-form').onsubmit=async e=>{
    e.preventDefault();
    if(chat.busy||state.search!==search||chat.stale)return;
    const message=$('chat-input').value.trim();if(!message)return;
    if(search.directEntry&&!chat.turns&&search.retrievedQuestion!==message)search.needsRetrieval=true;
    chat.draft=message;chat.pending=message;chat.busy=true;chat.error='';chat.stage=search.needsRetrieval?'retrieval':'generation';renderAI();
    try{
      if(search.needsRetrieval){
        const payload={question:message,space:search.payload.space,
          mode:document.querySelector('input[name=mode]:checked').value};
        if(search.payload.category_id!==null&&search.payload.category_id!==undefined)payload.category_id=search.payload.category_id;
        const found=await send('/ai/search',payload);
        if(state.search!==search||state.chat!==chat)return;
        search.search_id=found.search_id;search.sources=found.sources;search.question=message;search.retrievedQuestion=message;chat.searchId=found.search_id;
        search.needsRetrieval=false;chat.stage='generation';renderAI();
      }
      const result=await send('/ai/chat',{search_id:search.search_id,message,conversation_id:chat.id,expected_turns:chat.turns});
      if(state.search!==search||state.chat!==chat)return;
      chat.messages.push({role:'user',content:message},{role:'assistant',content:result.answer,sources:result.sources,status:result.status,availableSources:result.available_sources});
      chat.id=result.conversation_id;chat.turns=result.turns;chat.draft='';
    }catch(error){
      if(state.search!==search||state.chat!==chat)return;
      chat.error=error.message;chat.stale=error.status===409||error.status===404;
    }finally{
      chat.busy=false;chat.pending=null;
      if(state.search===search&&state.chat===chat){renderAI();if(!chat.stale)$('chat-input').focus({preventScroll:true});}
    }
  };
  if($('chat-restart'))$('chat-restart').onclick=()=>runSearch(search.question).catch(report);
  $('chat-messages').scrollTop=$('chat-messages').scrollHeight;
}

function action(title,html,handler){$('action-title').textContent=title;$('action-fields').innerHTML=html;$('action-error').textContent='';actionSubmit=handler;dialog('action-dialog');}
function newCategory(){action('新建个人门类','<label>门类名称<input name="name" required maxlength="100" placeholder="如：毕业准备"></label><label>光点颜色<input name="color" type="color" value="#74dcff"></label>',async form=>{await send('/api/personal/categories',Object.fromEntries(new FormData(form)));await refreshCategories();await loadUniverse();toast('新的知识轨道已创建');});}
function personalOptions(selected){return state.personalCategories.map(c=>`<option value="${c.id}" ${c.id===selected?'selected':''}>${esc(c.name)}</option>`).join('');}
function publicOptions(selected){return state.publicCategories.map(c=>`<option value="${c.id}" ${c.id===selected?'selected':''}>${esc(c.name)}</option>`).join('');}
async function openEditor(item=null){
  await refreshCategories();
  if(!state.personalCategories.length){toast('先创建一个个人门类，再添加知识');newCategory();return;}
  if(!state.publicCategories.length){toast('请管理员先创建一个公共主门类');return;}
  state.editing=item;$('knowledge-form').reset();$('editor-error').textContent='';
  const form=$('knowledge-form'),fields=form.elements;
  fields.personal_category_id.innerHTML=personalOptions(item?.personal_category_id||(state.space==='personal'?state.category:null));
  fields.category_id.innerHTML=publicOptions(item?.category_id||(state.space==='public'?state.category:null));
  if(item){for(const key of ['title','content','summary','keyword'])fields[key].value=item[key]||'';const source=item.sources?.find(s=>s.source_type==='star_user')||item.sources?.[0];fields.source_name.value=source?.source_name||'';fields.source_url.value=source?.source_url||'';}
  $('editor-title').textContent=item?'编辑知识':'点亮一份新知识';
  $('sharing-hint').textContent=item?.visibility==='public'?'这份知识已公开，保存公有修改将同步给其他用户':'默认仅自己可见';
  $('save-public').textContent=item?.visibility==='public'?'保存公有修改':'保存并分享';
  if($('detail-dialog').open)closeDialog('detail-dialog');dialog('editor-dialog');
}
async function openDetail(kid){
  const [item,links]=await Promise.all([api('/api/knowledge/'+kid),api('/api/links')]);state.detail=item;
  const sourceHTML=(item.sources||[]).map(s=>{const url=safeUrl(s.source_url);return `<div>${esc(s.source_name||'未标注来源')}${url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)} ↗</a>`:''}</div>`;}).join('');
  const relations=links.items.filter(l=>l.source_id===kid||l.target_id===kid);
  $('detail-content').innerHTML=`<div class="dialog-heading"><span class="eyebrow">KNOWLEDGE / ${kid}</span><button type="button" class="icon-button" id="detail-close" aria-label="关闭详情">×</button></div><h1 class="detail-title">${esc(item.title)}</h1><div class="detail-meta"><span>${esc(item.author)}</span><span>更新于 ${date(item.updated_at)}</span><span class="pill ${item.visibility==='private'?'private':''}">${item.visibility==='private'?'仅自己可见':'公有知识'}</span>${item.hidden?'<span class="pill danger">已被下架</span>':''}</div>${item.moderation_reason?`<div class="notice">下架原因：${esc(item.moderation_reason)}</div>`:''}<div class="detail-body">${esc(item.content)}</div><div class="detail-sources"><strong>资料来源</strong>${sourceHTML||'<p>作者尚未提供来源链接</p>'}</div><div class="detail-actions">${item.owned?`<button class="outline" id="detail-edit">${icon('edit')}编辑</button><button class="outline" id="detail-visibility">${item.visibility==='public'?'撤回为私有':'分享到公有库'}</button><button class="outline" id="detail-reindex">更新语义索引</button><button class="outline danger-button" id="detail-delete">删除知识</button>`:`<button class="primary" id="detail-bookmark">${item.bookmarked?'移动收藏门类':'收藏到我的图谱'}</button>${item.bookmarked?'<button class="outline" id="detail-unbookmark">取消收藏</button>':''}`}<button class="outline" id="detail-relate">＋ 关联知识</button></div><div class="detail-relations"><h3>我的知识关联 <small class="muted">仅自己可见</small></h3>${relations.map(l=>`<div class="relation-row"><span class="pill">${esc(l.relation)}</span><button data-related="${l.source_id===kid?l.target_id:l.source_id}">${esc(l.source_id===kid?l.target_title:l.source_title)}</button><button data-delete-link="${l.id}">移除</button></div>`).join('')||'<p class="tiny muted">还没有关联。连接相关知识，让自己的图谱更完整。</p>'}</div>`;
  $('detail-close').onclick=()=>closeDialog('detail-dialog');hydrateIcons($('detail-content'));dialog('detail-dialog');
  const refresh=async()=>{await refreshCategories();await loadUniverse();if(state.view==='list')await loadItems();};
  if(item.owned){
    $('detail-edit').onclick=()=>openEditor(item).catch(report);
    $('detail-visibility').onclick=()=>{
      if(item.visibility==='public'){if(!confirm('撤回后，其他用户将不能继续阅读、检索或使用 AI 解释这份知识。确定撤回？'))return;send(`/api/knowledge/${kid}/visibility`,{visibility:'private'},'PATCH').then(async()=>{closeDialog('detail-dialog');await refresh();toast('已撤回为私有');}).catch(report);}
      else action('分享到公有库',`<p class="muted tiny">分享后无需审核，其他用户可立即阅读与检索。</p><label>公共主门类<select name="category_id">${publicOptions(item.category_id)}</select></label>`,async form=>{await send(`/api/knowledge/${kid}/visibility`,{visibility:'public',category_id:Number(form.elements.category_id.value)},'PATCH');closeDialog('detail-dialog');await refresh();toast('已分享至公有星海');});
    };
    $('detail-delete').onclick=()=>{if(confirm('确定删除这份知识？其他用户的收藏将显示原文不可用。'))api('/api/knowledge/'+kid,{method:'DELETE'}).then(async()=>{closeDialog('detail-dialog');await refresh();toast('知识已删除');}).catch(report);};
    $('detail-reindex').onclick=async()=>{const b=$('detail-reindex');buttonBusy(b,true);try{const r=await send(`/api/knowledge/${kid}/reindex`,{});toast(r.index_status==='ready'?'语义索引已更新':'索引尚未就绪，请检查本地模型服务');}catch(e){report(e);}finally{buttonBusy(b,false);}};
  }else{
    $('detail-bookmark').onclick=async()=>{await refreshCategories();if(!state.personalCategories.length){toast('先创建一个个人门类');newCategory();return;}action('收藏到我的图谱',`<label>个人门类<select name="category_id">${personalOptions(item.personal_category_id)}</select></label>`,async form=>{await send(`/api/knowledge/${kid}/organize`,{personal_category_id:Number(form.elements.category_id.value)},'PUT');closeDialog('detail-dialog');await refresh();toast('已收藏，前往我的图谱查看');});};
    if($('detail-unbookmark'))$('detail-unbookmark').onclick=()=>api(`/api/knowledge/${kid}/bookmark`,{method:'DELETE'}).then(async()=>{closeDialog('detail-dialog');await refresh();toast('已取消收藏');}).catch(report);
  }
  $('detail-relate').onclick=()=>openRelation(kid).catch(report);
  $('detail-content').querySelectorAll('[data-related]').forEach(b=>b.onclick=()=>openDetail(Number(b.dataset.related)).catch(report));
  $('detail-content').querySelectorAll('[data-delete-link]').forEach(b=>b.onclick=()=>api('/api/links/'+b.dataset.deleteLink,{method:'DELETE'}).then(()=>openDetail(kid)).catch(report));
}
async function openRelation(kid){
  const result=await api('/api/knowledge?space=personal&page_size=100');
  const options=items=>items.filter(k=>k.kid!==kid).map(k=>`<option value="${k.kid}">${esc(k.title)}</option>`).join('');
  action('关联另一份知识',`<label>筛选目标<input name="filter" placeholder="输入关键词筛选你的知识"></label><button type="button" id="relation-search" class="text-button">查找目标</button><label>目标知识<select name="target_id" required>${options(result.items)}</select></label><label>关系<select name="relation"><option>相关</option><option>前置知识</option><option>补充说明</option></select></label><p class="tiny muted">该关系仅在你的个人空间展示。</p>`,async form=>{const target=Number(form.elements.target_id.value);if(!target)throw Error('请先选择目标知识');await send('/api/links',{source_id:kid,target_id:target,relation:form.elements.relation.value});await openDetail(kid);toast('关联已建立');});
  $('relation-search').onclick=()=>{const form=$('action-form');api('/api/knowledge?space=personal&page_size=100&q='+encodeURIComponent(form.elements.filter.value)).then(r=>{form.elements.target_id.innerHTML=options(r.items);}).catch(report);};
}

async function manageCategory(){
  const cat=currentCategory();if(!cat||state.space!=='personal')return;
  action('整理个人门类',`<label>名称<input name="name" maxlength="100" required value="${esc(cat.name)}"></label><label>光点颜色<input name="color" type="color" value="${esc(cat.color)}"></label><p class="tiny muted">保存后将更新名称与颜色。</p><hr style="border:0;border-top:1px solid var(--line);margin:22px 0"><label>删除时将知识移到<select name="move_to"><option value="">空门类可直接删除</option>${personalOptions().replace(new RegExp('<option value="'+cat.id+'"[^>]*>[^<]*</option>'),'')}</select></label><button type="button" class="text-button danger-button" id="delete-personal-category">删除这个门类</button>`,async form=>{await send('/api/personal/categories/'+cat.id,{name:form.elements.name.value,color:form.elements.color.value},'PUT');await refreshCategories();await loadUniverse();$('category-title').textContent=form.elements.name.value;toast('门类已更新');});
  $('delete-personal-category').onclick=async()=>{if(!confirm('删除门类会保留知识正文。确定继续？'))return;try{const target=$('action-form').elements.move_to.value;await api('/api/personal/categories/'+cat.id+(target?'?move_to='+Number(target):''),{method:'DELETE'});closeDialog('action-dialog');location.hash='#/personal';toast('门类已删除');}catch(e){$('action-error').textContent=e.message;}};
}

async function renderAdmin(){
  $('admin-content').innerHTML='<div class="loading-state">读取公有空间…</div>';
  document.querySelectorAll('[data-admin-tab]').forEach(b=>b.classList.toggle('active',b.dataset.adminTab===state.adminTab));
  if(state.adminTab==='events'){
    const result=await api('/api/admin/events');
    $('admin-content').innerHTML='<p class="manage-note">最近100次行星展示与公有内容管理操作</p><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>时间</th><th>操作者</th><th>操作</th><th>详情</th></tr></thead><tbody>'+result.items.map(e=>`<tr><td>${esc(new Date(e.created_at).toLocaleString('zh-CN'))}</td><td>${esc(e.actor)}</td><td>${esc(e.action)}</td><td>${esc(e.detail)}</td></tr>`).join('')+'</tbody></table></div>';return;
  }
  if(state.adminTab==='planets'){
    const result=await api('/api/admin/categories');
    $('admin-content').innerHTML=`<div class="admin-toolbar"><p class="manage-note">隐藏仅影响首页行星，公有知识仍可搜索。</p><button class="primary" id="create-public-category">＋ 新建门类</button></div><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>知识门类</th><th>公有知识</th><th>行星样式</th><th>首页展示</th><th>操作</th></tr></thead><tbody>${result.items.map(c=>`<tr><td>${esc(c.name)}</td><td>${c.count}</td><td>${esc({earth:'地球',sun:'太阳',jupiter:'木星',saturn:'土星',neptune:'蓝色行星',violet:'紫色行星'}[c.style])}</td><td class="${c.visible?'':'off'}">${c.visible?'显示':'已隐藏'}</td><td><button data-planet="${c.id}">设置</button><button data-cat-edit="${c.id}">编辑</button><button data-cat-delete="${c.id}" class="danger-button">删除</button></td></tr>`).join('')}</tbody></table></div>`;
    $('create-public-category').onclick=()=>action('新建公共门类','<label>门类名称<input name="name" required maxlength="100"></label><label>简介<textarea name="description" maxlength="1000"></textarea></label>',async form=>{await send('/categories',Object.fromEntries(new FormData(form)));await refreshCategories();await renderAdmin();toast('公共门类已创建，默认允许展示');});
    $('create-public-category').insertAdjacentHTML('beforebegin','<button class="outline" id="planets-show-all">全部显示</button><button class="outline" id="planets-hide-all">全部隐藏</button>');
    for(const visible of [true,false])$(visible?'planets-show-all':'planets-hide-all').onclick=async()=>{if(!visible&&!confirm('隐藏全部首页行星？知识仍可通过搜索和门类列表访问。'))return;try{await send('/api/admin/planets',{visible},'PUT');await refreshCategories();await renderAdmin();toast(visible?'全部行星已允许展示':'首页行星已隐藏，公有搜索仍可使用');}catch(e){report(e);}};
    $('admin-content').querySelectorAll('[data-planet]').forEach(b=>b.onclick=()=>{const c=result.items.find(c=>c.id===Number(b.dataset.planet));action('行星展示 · '+c.name,`<label>样式<select name="style">${['jupiter','saturn','neptune','violet','earth'].map(s=>`<option value="${s}" ${c.style===s?'selected':''}>${{jupiter:'木星',saturn:'土星',neptune:'蓝色行星',violet:'紫色行星',earth:'地球'}[s]}</option>`).join('')}</select></label><label>显示顺序<input name="position" type="number" min="0" max="10000" value="${c.position}"></label><label><input name="visible" type="checkbox" ${c.visible?'checked':''}>在全体图谱首页展示</label><p class="tiny muted">隐藏行星不会删除门类或阻止搜索。</p>`,async form=>{await send('/api/admin/categories/'+c.id+'/planet',{style:form.elements.style.value,visible:form.elements.visible.checked,position:Number(form.elements.position.value)},'PUT');await refreshCategories();await renderAdmin();});});
    $('admin-content').querySelectorAll('[data-cat-edit]').forEach(b=>b.onclick=()=>{const c=result.items.find(c=>c.id===Number(b.dataset.catEdit));action('编辑公共门类',`<label>名称<input name="name" required maxlength="100" value="${esc(c.name)}"></label><label>简介<textarea name="description" maxlength="1000">${esc(c.description)}</textarea></label>`,async form=>{await send('/categories/'+c.id,Object.fromEntries(new FormData(form)),'PUT');await refreshCategories();await renderAdmin();});});
    $('admin-content').querySelectorAll('[data-cat-delete]').forEach(b=>b.onclick=()=>{if(confirm('门类中有知识时不能删除，请先迁移知识。确定删除？'))api('/categories/'+b.dataset.catDelete,{method:'DELETE'}).then(()=>{refreshCategories();renderAdmin();}).catch(report);});
  }else{
    $('admin-content').innerHTML='<div class="admin-toolbar"><input id="admin-query" placeholder="搜索公有知识标题"><select id="admin-state"><option value="all">全部状态</option><option value="active">正常展示</option><option value="hidden">已下架</option></select><button id="admin-search" class="primary">筛选</button></div><div id="admin-rows"></div>';
    const rows=async()=>{const result=await api('/api/admin/knowledge?state='+$('admin-state').value+'&q='+encodeURIComponent($('admin-query').value));$('admin-rows').innerHTML=`<p class="manage-note">${result.items.length} 条公有知识 · 不包含用户私有内容</p><div class="admin-table-wrap"><table class="admin-table"><thead><tr><th>标题</th><th>作者</th><th>状态</th><th>操作</th></tr></thead><tbody>${result.items.map(k=>`<tr><td>${esc(k.title)}</td><td>${esc(k.author)}</td><td><span class="pill ${k.hidden?'danger':''}">${k.hidden?'已下架':'正常'}</span></td><td>${k.hidden?'':`<button data-open="${k.kid}">查看</button>`}<button data-moderate="${k.kid}">${k.hidden?'恢复':'下架'}</button></td></tr>`).join('')}</tbody></table></div>`;bindOpen($('admin-rows'));$('admin-rows').querySelectorAll('[data-moderate]').forEach(b=>b.onclick=()=>{const k=result.items.find(k=>k.kid===Number(b.dataset.moderate));action(k.hidden?'恢复公有内容':'下架公有内容',`<p class="muted tiny">${esc(k.title)}</p><label>操作原因<textarea name="reason" maxlength="500" ${k.hidden?'':'required'}></textarea></label>`,async form=>{await send('/api/admin/knowledge/'+k.kid+'/moderation',{hidden:!k.hidden,reason:form.elements.reason.value});await rows();toast(k.hidden?'已恢复':'已下架');});});};
    $('admin-search').onclick=()=>rows().catch(report);await rows();
  }
}

function openAppearance(){previewBefore={...state.appearance};$('appearance-error').textContent='';syncAppearanceForm();dialog('appearance-dialog');$('appearance-dialog').scrollTop=0;}
function syncAppearanceForm(){const a=state.appearance;$('exposure').value=Math.round(a.exposure*100);$('exposure-value').textContent=Math.round(a.exposure*100)+'%';$('custom-color').value=a.custom_color;$('custom-hex').value=a.custom_color.toUpperCase();$('setting-paused').checked=a.paused;$('setting-reduced').checked=a.reduced_motion;document.querySelectorAll('[data-theme]').forEach(b=>{b.classList.toggle('active',b.dataset.theme===a.theme);b.setAttribute('aria-pressed',String(b.dataset.theme===a.theme));});}
function previewAppearance(values){applyAppearance({...state.appearance,...values});syncAppearanceForm();}
function cancelAppearance(){if(previewBefore)applyAppearance(previewBefore);previewBefore=null;closeDialog('appearance-dialog');}

hydrateIcons();
$('auth-form').onsubmit=async e=>{e.preventDefault();const b=$('auth-submit');buttonBusy(b,true);$('auth-error').textContent='';const form=e.currentTarget,username=form.elements.username.value.trim(),password=form.elements.password.value;try{if(state.register)await send('/register',{username,password,email:form.elements.email.value});const result=await send('/login',{username,password});await signedIn(result.user);}catch(error){$('auth-error').textContent=error.message;}finally{buttonBusy(b,false);}};
$('auth-switch').onclick=()=>{state.register=!state.register;show('email-label',state.register);$('auth-form').elements.email.required=state.register;$('auth-form').elements.password.minLength=state.register?8:1;$('auth-form').elements.password.maxLength=state.register?15:128;$('auth-form').elements.password.autocomplete=state.register?'new-password':'current-password';$('auth-title').textContent=state.register?'创建你的星球':'欢迎回来';$('auth-subtitle').textContent=state.register?'注册账号，开启个人知识空间。':'登录，继续探索你的知识星海。';$('auth-submit').textContent=state.register?'注册并进入星海':'登录星海';$('auth-switch').textContent=state.register?'已有账号？返回登录':'还没有账号？创建个人星球';$('auth-error').textContent='';};
$('profile-button').onclick=()=>$('profile-menu').classList.toggle('hidden');
document.addEventListener('click',e=>{if(!e.target.closest('#profile-button,#profile-menu'))show('profile-menu',false);});
$('logout').onclick=async()=>{try{await send('/logout',{});signedOut();}catch(e){report(e);}};
$('new-knowledge').onclick=()=>openEditor().catch(report);$('new-category').onclick=newCategory;
$('empty-create').onclick=()=>state.space==='personal'?newCategory():openEditor().catch(report);
$('manage-category').onclick=()=>manageCategory().catch(report);
$('all-categories').onclick=()=>{location.hash=`#/${state.space}/list`;};
$('list-view').onclick=()=>{location.hash=`#/${state.space}/list`;};$('back-graph').onclick=()=>{location.hash='#/'+state.space;};
$('pause-orbit').onclick=async()=>{previewAppearance({paused:!state.appearance.paused,reduced_motion:state.appearance.reduced_motion});try{state.savedAppearance=await send('/api/appearance',state.appearance,'PUT');}catch(e){report(e);}};
$('reset-orbit').onclick=()=>{state.zoom=1;state.phase=0;positionNodes();};$('zoom-in').onclick=()=>{state.zoom=Math.min(1.8,state.zoom+.15);};$('zoom-out').onclick=()=>{state.zoom=Math.max(.65,state.zoom-.15);};
$('top-search').onsubmit=e=>{e.preventDefault();runSearch($('top-question').value).catch(report);};$('category-search').onsubmit=e=>{e.preventDefault();runSearch($('category-question').value).catch(report);};
$('knowledge-form').onsubmit=async e=>{e.preventDefault();const form=e.currentTarget,raw=Object.fromEntries(new FormData(form));const visibility=e.submitter?.name==='save-public'?'public':'private';raw.personal_category_id=Number(raw.personal_category_id);raw.category_id=Number(raw.category_id);raw.visibility=visibility;raw.source_url=raw.source_url||null;const button=e.submitter;buttonBusy(button,true);$('editor-error').textContent='';try{const result=await send('/api/knowledge'+(state.editing?'/'+state.editing.kid:''),raw,state.editing?'PUT':'POST');closeDialog('editor-dialog');await refreshCategories();await loadUniverse();if(state.view==='list')await loadItems();toast((visibility==='public'?'已分享至公有星海':'已保存到个人空间')+(result.index_status==='ready'?'':' · 语义索引待更新'));}catch(error){$('editor-error').textContent=error.message;}finally{buttonBusy(button,false);}};
$('action-form').onsubmit=async e=>{e.preventDefault();const button=e.currentTarget.querySelector('button[type=submit]');buttonBusy(button,true);$('action-error').textContent='';try{await actionSubmit(e.currentTarget);closeDialog('action-dialog');}catch(error){$('action-error').textContent=error.message;}finally{buttonBusy(button,false);}};
document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>closeDialog(b.closest('dialog').id));
document.querySelectorAll('dialog').forEach(d=>{d.addEventListener('close',()=>{state.modal=!!document.querySelector('dialog[open]');});});
$('appearance-open').onclick=openAppearance;$('appearance-close').onclick=cancelAppearance;
$('appearance-dialog').addEventListener('cancel',e=>{e.preventDefault();cancelAppearance();});
$('exposure').oninput=e=>previewAppearance({exposure:Number(e.target.value)/100});
document.querySelectorAll('[data-theme]').forEach(b=>b.onclick=()=>previewAppearance({theme:b.dataset.theme}));
$('custom-color').oninput=e=>previewAppearance({theme:'custom',custom_color:e.target.value});
$('custom-hex').oninput=e=>{if(/^#[0-9a-f]{6}$/i.test(e.target.value))previewAppearance({theme:'custom',custom_color:e.target.value});};
$('setting-paused').onchange=e=>previewAppearance({paused:e.target.checked});$('setting-reduced').onchange=e=>previewAppearance({reduced_motion:e.target.checked});
$('appearance-reset').onclick=()=>previewAppearance(defaults());
$('appearance-save').onclick=async()=>{buttonBusy($('appearance-save'),true);try{state.savedAppearance=await send('/api/appearance',state.appearance,'PUT');previewBefore=null;closeDialog('appearance-dialog');toast('星海外观已保存');}catch(e){$('appearance-error').textContent='未保存：'+e.message;}finally{buttonBusy($('appearance-save'),false);}};
document.querySelectorAll('[data-admin-tab]').forEach(b=>b.onclick=()=>{state.adminTab=b.dataset.adminTab;renderAdmin().catch(report);});
window.addEventListener('hashchange',()=>{state.hover=false;route().catch(report);});window.addEventListener('resize',resizeStars);
resizeStars();requestAnimationFrame(frame);
api('/auth/me').then(signedIn).catch(error=>{signedOut();if(error.status!==401)$('auth-error').textContent='连接后端失败，请稍后重试。';});
