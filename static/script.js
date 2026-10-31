/* API 边界：现有接口已接入；语义搜索使用本地 BGE，解释通过后端调用 DeepSeek。
 * POST /ai/search {question} -> {sources:[{knowledge_id,title,excerpt}], search_id?}
 * POST /ai/explain {question,knowledge_ids,search_id?} -> {answer}
 * GET /ai/status -> {embedding:{configured:boolean},deepseek:{configured:boolean}}
 * 解释接口必须在后端重新校验知识及权限，并在缺少密钥时返回 503。
 * 本前端不保存 API Key，不直接请求模型供应商。
 */
'use strict';
const $ = (id) => document.getElementById(id);
const escapeHTML = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const API = {search:'/ai/search', explain:'/ai/explain', status:'/ai/status'};
const state = {categories:[], categoryEditId:null, reviewId:null, ownSubmissions:[], submissionEditId:null, demo:false, user:null, register:false, view:'search', sessions:[], active:null, knowledge:[], editId:null, serviceStatus:null};
const demoKnowledge = [
  {kid:1,title:'栈与后进先出原则',content:'栈是一种只允许在一端进行插入和删除的线性表。允许操作的一端称为栈顶，另一端称为栈底。\n\n栈遵循后进先出（LIFO）原则：最后进入栈的元素最先被取出。可以想象一叠盘子：每次从顶部放入或取出盘子。\n\n入栈（push）和出栈（pop）是栈的两种基本操作。栈常用于函数调用、表达式求值和括号匹配。',summary:'从一叠盘子理解后进先出：栈的定义、入栈和出栈，以及常见应用。',keyword:'栈、后进先出、LIFO',category_id:1,status:'published'},
  {kid:2,title:'队列与先进先出原则',content:'队列是一种插入操作在队尾、删除操作在队首进行的线性表。\n\n队列遵循先进先出（FIFO）原则，类似于排队等待服务：先到的人先得到服务。\n\n队列常用于任务调度、消息处理和广度优先遍历。',summary:'先到先服务。认识队列的队首、队尾及其在任务调度中的应用。',keyword:'队列、先进先出、FIFO',category_id:1,status:'published'},
  {kid:3,title:'二叉树的三种遍历方式',content:'二叉树中每个节点最多有两个子节点，分别称为左子节点和右子节点。\n\n前序遍历：根节点 → 左子树 → 右子树。\n中序遍历：左子树 → 根节点 → 右子树。\n后序遍历：左子树 → 右子树 → 根节点。\n\n遍历时需要对每棵子树递归应用相同的顺序。',summary:'用清晰的访问顺序，理解前序、中序与后序遍历。',keyword:'二叉树、遍历、前序、中序',category_id:2,status:'published'},
  {kid:4,title:'二分查找的适用条件',content:'二分查找在有序的顺序表上进行。每次比较中间位置的元素，将搜索范围缩小为原来的一半。\n\n最坏情况下时间复杂度为 O(log n)。高效定位中间元素依赖随机访问，链表不能直接以相同的访问代价实现这一过程。',summary:'为什么要求有序和随机访问？理解二分查找的前提与效率。',keyword:'二分查找、有序、复杂度',category_id:3,status:'published'},
  {kid:5,title:'顺序表与链表的比较',content:'顺序表使用连续存储空间，支持按下标随机访问。链表通过指针关联节点，不要求节点连续存储。\n\n讨论插入与删除的复杂度时，需要区分是否已经定位操作位置。',summary:'从存储方式、访问方式和操作条件比较两种线性结构。',keyword:'顺序表、链表、线性表',category_id:1,status:'draft'}
];
let toastTimer;
function toast(message){$('toast').textContent=message;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4200);}
class ApiError extends Error {constructor(message,status){super(message);this.status=status;}}
async function request(path, options={}){
  const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),45000);
  try {
    const response=await fetch(path,{credentials:'same-origin',...options,headers:{'Content-Type':'application/json',...options.headers},signal:controller.signal});
    const data=await response.json().catch(()=>({}));
    if(!response.ok){const detail=Array.isArray(data.detail)?data.detail.map(e=>e.msg).join('；'):data.detail;throw new ApiError(typeof detail==='string'?detail:`请求失败（${response.status}）`,response.status);}
    return data;
  }catch(error){if(error.name==='AbortError')throw new ApiError('请求超时，请稍后重试。',504);if(error instanceof ApiError)throw error;throw new ApiError('无法连接服务，请确认后端已启动。',0);}finally{clearTimeout(timer);}
}
const jsonOptions=(method,data)=>({method,body:JSON.stringify(data)});
function toggleAuth(){state.register=!state.register;$('auth-title').textContent=state.register?'开启新的探索':'欢迎回来';$('auth-subtitle').textContent=state.register?'建立你的知识空间，从一个问题开始。':'坐下来，继续你的知识探索。';$('email-field').hidden=!state.register;$('email').required=state.register;$('password').minLength=state.register?8:1;$('password').maxLength=state.register?15:128;$('password').autocomplete=state.register?'new-password':'current-password';$('auth-submit').textContent=state.register?'创建账号 ↗':'登 录 ↗';$('auth-switch-label').textContent=state.register?'已经有账号？':'还没有账号？';$('auth-switch').textContent=state.register?'返回登录':'创建账号';$('auth-error').textContent='';}
$('auth-switch').onclick=toggleAuth;
$('toggle-password').onclick=()=>{const show=$('password').type==='password';$('password').type=show?'text':'password';$('toggle-password').textContent=show?'隐藏':'显示';$('toggle-password').setAttribute('aria-label',show?'隐藏密码':'显示密码');};
$('auth-form').onsubmit=async(event)=>{event.preventDefault();$('auth-submit').disabled=true;$('auth-error').textContent='';try{const username=$('username').value.trim();const password=$('password').value;if(state.register){await request('/register',jsonOptions('POST',{username,password,email:$('email').value.trim()}));toggleAuth();toast('账号创建成功，请登录。');}else{const data=await request('/login',jsonOptions('POST',{username,password}));const user=data.user||await request('/users/'+encodeURIComponent(username));enter({uid:user.uid,username:user.username,role:user.role||'user'},false);}$('password').value='';}catch(error){$('auth-error').textContent=error.message;}finally{$('auth-submit').disabled=false;}};
function enter(user,demo){state.user=user;state.demo=demo;state.categories=demo?[{cid:1,name:'线性结构',description:''},{cid:2,name:'树与二叉树',description:''},{cid:3,name:'查找算法',description:''}]:[];state.sessions=[];state.ownSubmissions=[];state.submissionEditId=null;state.knowledge=demo?structuredClone(demoKnowledge):[];state.serviceStatus=null;$('auth-screen').hidden=true;$('workspace').hidden=false;$('demo-badge').hidden=!demo;$('mode-label').textContent=demo?'示例体验 · 数据仅本次有效':'已连接项目后端';$('account-name').textContent=user.username;$('account-role').textContent=user.role==='admin'?'知识管理员':'知识探索者';$('avatar').textContent=user.username.slice(0,1);$('nav-admin').hidden=user.role!=='admin';newSearch();if(user.role==='admin')showView('admin');}
$('demo-user').onclick=()=>enter({uid:1,username:'林间探索者',role:'user'},true);
$('demo-admin').onclick=()=>{enter({uid:1,username:'木知管理员',role:'admin'},true);showView('admin');};
$('account-button').onclick=async()=>{if(!state.demo){try{await request('/logout',{method:'POST'});}catch(error){toast('退出失败：'+error.message);return;}}state.user=null;state.sessions=[];state.active=null;state.knowledge=[];state.ownSubmissions=[];state.submissionEditId=null;document.querySelectorAll('dialog').forEach(dialog=>dialog.close());$('workspace').hidden=true;$('auth-screen').hidden=false;$('password').value='';closeSidebar();};
function closeSidebar(){$('sidebar').classList.remove('open');$('sidebar-overlay').hidden=true;}
$('open-sidebar').onclick=()=>{$('sidebar').classList.add('open');$('sidebar-overlay').hidden=false;};$('close-sidebar').onclick=closeSidebar;$('sidebar-overlay').onclick=closeSidebar;
function showView(view){state.view=view;$('search-view').hidden=view!=='search';$('admin-view').hidden=view!=='admin';$('submissions-view').hidden=view!=='submissions';$('nav-search').classList.toggle('active',view==='search');$('nav-admin').classList.toggle('active',view==='admin');$('nav-submissions').classList.toggle('active',view==='submissions');$('breadcrumb').innerHTML=view==='search'?'探索 / <strong>知识搜索</strong>':view==='submissions'?'我的空间 / <strong>知识投稿</strong>':'工作台 / <strong>知识管理</strong>';closeSidebar();if(view==='admin')loadKnowledge();else if(view==='submissions')loadSubmissions();else{renderHistory();renderConversation();}}
function newSearch(){const session={id:crypto.randomUUID(),title:'新的探索',turns:[]};state.sessions.unshift(session);state.active=session.id;$('question').value='';showView('search');renderHistory();renderConversation();$('question').focus();}
function activeSession(){return state.sessions.find(s=>s.id===state.active);}
$('new-search').onclick=newSearch;$('nav-search').onclick=()=>showView('search');$('nav-admin').onclick=()=>{if(state.user?.role==='admin')showView('admin');};
$('nav-submissions').onclick=()=>showView('submissions');
$('nav-submit').onclick=()=>{showView('submissions');return openSubmission(null);};
function renderHistory(){$('history-list').innerHTML=state.sessions.filter(s=>s.turns.length).map(s=>`<button class="history-item ${s.id===state.active?'active':''}" data-session="${s.id}" title="${escapeHTML(s.title)}">${escapeHTML(s.title)}</button>`).join('')||'<p class="history-empty">你的好奇心，将在这里留下足迹。</p>';}
$('history-list').onclick=(event)=>{const btn=event.target.closest('[data-session]');if(!btn)return;state.active=btn.dataset.session;showView('search');renderHistory();renderConversation();};
const welcome=()=>`<div class="welcome"><div class="welcome-symbol"><span>木</span></div><span class="eyebrow">A LITTLE CURIOSITY, A WORLD OF KNOWLEDGE</span><h1>你好，今天想探索什么？</h1><p>不必记住准确的术语，用你的方式提问。<br>在这里，让每一次搜索都有所发现。</p><div class="suggestions"><button class="suggestion" data-prompt="栈和队列有什么区别？"><span class="suggest-icon">▤</span><strong>理解一个概念 ↗</strong><small>栈和队列有什么区别？</small></button><button class="suggestion" data-prompt="二叉树有哪些遍历方式？"><span class="suggest-icon">♧</span><strong>梳理一条思路 ↗</strong><small>二叉树如何遍历？</small></button><button class="suggestion" data-prompt="二分查找为什么要求有序？"><span class="suggest-icon">⌕</span><strong>找到问题的依据 ↗</strong><small>二分查找的适用条件</small></button></div><div class="welcome-line">KNOWLEDGE TAKES ROOT HERE</div></div>`;
function renderConversation(){const session=activeSession();if(!session)return;const container=$('conversation');container.innerHTML=session.turns.length?session.turns.map(turn=>`<div class="message user-message"><div class="user-bubble">${escapeHTML(turn.question)}</div></div><div class="message" data-turn="${turn.id}"><div class="assistant-heading"><span class="brand-mark">木</span>木知 <span>· ${state.demo?'示例搜索':turn.mode==='semantic'?'语义搜索':'关键词搜索'}</span></div>${renderTurn(turn)}</div>`).join(''):welcome();const busy=session.turns.some(t=>t.loading);$('send').disabled=busy;container.scrollTop=container.scrollHeight;}
function renderTurn(turn){if(turn.loading)return '<div class="loading">正在为你寻找相关知识</div>';if(turn.error)return `<div class="inline-error">${escapeHTML(turn.error)}<button class="retry" data-retry="${turn.id}">重新尝试</button></div>`;if(!turn.sources.length)return '<div class="empty-result">暂时没有找到相关知识。<br>试试补充概念名称，或换一种描述。没有检索依据时，不提供 AI 解释。</div>';return `<p class="result-intro">${state.demo?'以下是交互演示用的示例知识，共':'为你找到'} ${turn.sources.length} 条相关知识${state.demo?'，未调用 Embedding API。':'。'}</p>${turn.sources.map(s=>`<article class="result-card"><button data-source="${s.knowledge_id}" data-turn-id="${turn.id}"><div class="result-top"><span class="result-number">${String(turn.sources.indexOf(s)+1).padStart(2,'0')}</span><span class="result-title">${escapeHTML(s.title)}</span><span class="result-arrow">↗</span></div><p>${escapeHTML(s.excerpt)}</p><div class="result-meta"><span>知识 #${escapeHTML(s.knowledge_id)}</span><span>查看原文 →</span></div></button></article>`).join('')}${turn.answer?`<div class="answer-box">✧ DeepSeek 解释\n\n${escapeHTML(turn.answer)}</div>`:turn.skipped?'<p class="fine-print">已跳过 AI 解释，你可以继续搜索。</p>':`<div class="explain-actions"><button class="explain-btn" data-explain="${turn.id}" ${turn.explaining?'disabled':''}>${turn.explaining?'正在根据资料解释……':'✧ 使用 DeepSeek 解释'}</button><button class="skip-btn" data-skip="${turn.id}" ${turn.explaining?'disabled':''}>不需要，继续搜索 →</button></div>`}${turn.explainError?`<p class="inline-error">${escapeHTML(turn.explainError)}</p>`:''}`;}
function normalizeSources(data){const list=data.sources||data.items;if(!Array.isArray(list))throw new ApiError('搜索接口返回格式不符合约定。',502);const seen=new Set();return list.filter(s=>{const id=s.knowledge_id??s.kid;if(!Number.isInteger(id)||seen.has(id))return false;seen.add(id);return true;}).map(s=>({knowledge_id:s.knowledge_id??s.kid,title:s.title||'未命名知识',excerpt:s.excerpt??s.summary??s.content??'',content:s.content}));}
async function executeSearch(turn){const user=state.user;const session=activeSession();turn.loading=true;turn.error=null;renderConversation();try{if(state.demo){await new Promise(r=>setTimeout(r,550));const q=turn.question;const terms=q.match(/栈|队列|后进先出|先进先出|二叉树|遍历|查找|有序|链表|顺序表/g)||[];turn.sources=state.knowledge.filter(k=>k.status==='published'&&(turn.mode==='keyword'?`${k.title}${k.content}${k.keyword}`.includes(q):terms.some(t=>`${k.title}${k.content}${k.keyword}`.includes(t)))).slice(0,3).map(k=>({knowledge_id:k.kid,title:k.title,excerpt:k.summary,content:k.content}));}else{let data;try{data=turn.mode==='semantic'?await request(API.search,jsonOptions('POST',{question:turn.question})):await request('/search/knowledge?status=published&keyword='+encodeURIComponent(turn.question));}catch(error){if(error.status===404&&turn.mode==='semantic')throw new ApiError('语义搜索接口尚未接入。请确认后端已更新，或切换「关键词搜索」使用现有接口。',404);throw error;}turn.sources=normalizeSources(data);turn.searchId=data.search_id;}}catch(error){turn.error=error.message;}finally{turn.loading=false;if(state.user===user&&state.active===session.id&&state.view==='search')renderConversation();}}
$('search-form').onsubmit=(event)=>{event.preventDefault();const question=$('question').value.trim();if(!question||activeSession().turns.some(t=>t.loading))return;const session=activeSession();const turn={id:crypto.randomUUID(),question,mode:$('search-mode').value,sources:[],loading:true};session.turns.push(turn);session.title=session.turns[0].question;$('question').value='';$('question').style.height='auto';renderHistory();executeSearch(turn);};
$('question').onkeydown=(event)=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();$('search-form').requestSubmit();}};$('question').oninput=()=>{$('question').style.height='auto';$('question').style.height=Math.min($('question').scrollHeight,120)+'px';};
$('conversation').onclick=async(event)=>{const prompt=event.target.closest('[data-prompt]');if(prompt){$('question').value=prompt.dataset.prompt;$('search-form').requestSubmit();return;}const source=event.target.closest('[data-source]');if(source){const turn=activeSession().turns.find(t=>t.id===source.dataset.turnId);const item=turn?.sources.find(s=>s.knowledge_id===Number(source.dataset.source));if(item)openDetail(item);return;}const btn=event.target.closest('[data-explain],[data-skip],[data-retry]');if(!btn)return;const session=activeSession();const turn=session.turns.find(t=>t.id===(btn.dataset.explain||btn.dataset.skip||btn.dataset.retry));if(!turn)return;if(btn.dataset.retry){executeSearch(turn);return;}if(btn.dataset.skip){turn.skipped=true;turn.explainError=null;renderConversation();$('question').focus();return;}if(turn.explaining)return;turn.explaining=true;turn.explainError=null;renderConversation();const user=state.user;try{if(state.demo)throw new ApiError('演示模式未配置 DeepSeek API Key，无法生成真实解释。搜索结果可以继续阅读。',503);const data=await request(API.explain,jsonOptions('POST',{question:turn.question,knowledge_ids:turn.sources.map(s=>s.knowledge_id),...(turn.searchId?{search_id:turn.searchId}:{})}));if(typeof data.answer!=='string'||!data.answer.trim())throw new ApiError('解释接口没有返回有效答案。',502);turn.answer=data.answer;}catch(error){turn.explainError=error.status===404?'DeepSeek 解释接口尚未接入。接入后由后端检查 API Key，并根据本次检索资料生成解释。':error.message;}finally{turn.explaining=false;if(state.user===user&&state.active===session.id&&state.view==='search')renderConversation();}};
const knowledgeStatusLabel=status=>({published:'已发布',draft:'未发布 / 待审核',rejected:'已驳回',deleted:'已删除'}[status]||status);
function renderKnowledgeDetail(item,excerpt=''){
  const sources=(item.sources||[]).map(source=>`<p class="detail-source">来源：${escapeHTML(source.source_name||'未填写名称')}${/^https?:\/\//i.test(source.source_url||'')?` · <a href="${escapeHTML(source.source_url)}" target="_blank" rel="noopener noreferrer">打开来源链接 ↗</a>`:''}</p>`).join('');
  return `<h2 class="detail-title">${escapeHTML(item.title)}</h2><span class="detail-label">知识 #${escapeHTML(item.kid)} · ${escapeHTML(knowledgeStatusLabel(item.status))}${item.created_by_name?' · 投稿人：'+escapeHTML(item.created_by_name):''}</span>${sources}${item.status==='rejected'&&item.review_note?`<p class="review-reason">驳回理由：${escapeHTML(item.review_note)}</p>`:''}<div class="detail-body">${escapeHTML(item.content||excerpt||'暂无正文')}</div>`;
}
async function openDetail(source){$('detail-content').innerHTML='<p class="loading">正在打开知识</p>';$('detail-dialog').showModal();try{const item=state.demo?state.knowledge.find(k=>k.kid===(source.knowledge_id??source.kid)):await request('/knowledge/'+(source.knowledge_id??source.kid));if(!$('detail-dialog').open)return;$('detail-content').innerHTML=renderKnowledgeDetail(item,source.excerpt);}catch(error){$('detail-content').innerHTML=`<p class="inline-error">${escapeHTML(error.message)}</p>`;}}
async function loadKnowledge(){const user=state.user;$('admin-note').textContent=state.demo?'当前为管理演示：发布、驳回和删除仅影响本次页面，不修改数据库。':'发布后才进入公开搜索，并自动生成向量。驳回需填写理由；撤回后立即停止公开展示。';try{if(!state.demo){const data=await request('/knowledge');if(state.user!==user)return;state.knowledge=data.items||[];await loadCategories();if(state.user!==user)return;}renderKnowledge();}catch(error){$('knowledge-rows').innerHTML=`<tr><td colspan="4">${escapeHTML(error.message)}</td></tr>`;}}
function renderKnowledge(){
  const list=state.knowledge;const q=$('admin-search').value.trim().toLowerCase();const status=$('admin-status').value||'all';const category=$('admin-category').value||'all';
  const selected=category==='all'||state.categories.some(c=>String(c.cid)===category)?category:'all';
  $('admin-category').innerHTML='<option value="all">全部分类</option>'+state.categories.map(c=>`<option value="${c.cid}">${escapeHTML(c.name)}</option>`).join('');$('admin-category').value=selected;
  const counts={all:list.length,draft:list.filter(k=>k.status==='draft').length,published:list.filter(k=>k.status==='published').length,rejected:list.filter(k=>k.status==='rejected').length};
  $('admin-stats').innerHTML=[['知识总数',counts.all],['未发布 / 待审核',counts.draft],['已发布',counts.published],['已驳回',counts.rejected]].map(([label,n])=>`<div class="stat"><span>${label}</span><strong>${String(n).padStart(2,'0')}</strong></div>`).join('');
  $('knowledge-status-filters').innerHTML=[['all','全部'],['draft','未发布 / 待审核'],['published','已发布'],['rejected','已驳回']].map(([value,label])=>`<button class="status-filter ${status===value?'active':''}" data-status="${value}" aria-pressed="${status===value}">${label}<span>${counts[value]}</span></button>`).join('');
  const origin=$('admin-origin').value||'all';
  const rows=list.filter(k=>(status==='all'||k.status===status)&&(selected==='all'||String(k.category_id)===selected)&&(origin==='all'||(origin==='student'?k.is_submission:!k.is_submission))&&`${k.title} ${k.keyword||''}`.toLowerCase().includes(q));
  $('knowledge-rows').innerHTML=rows.map(k=>`<tr><td class="knowledge-title-cell">${escapeHTML(k.title)}<small>#${k.kid} · ${escapeHTML(state.categories.find(c=>c.cid===k.category_id)?.name||k.category_id)}${k.is_submission?' · 用户投稿：'+escapeHTML(k.created_by_name||'#'+k.created_by):''}</small></td><td class="knowledge-keywords">${escapeHTML(k.keyword||'—')}</td><td class="knowledge-status-cell"><span class="state ${k.status==='published'?'':k.status==='rejected'?'rejected':'draft'}">${escapeHTML(knowledgeStatusLabel(k.status))}</span>${k.status==='rejected'&&k.review_note?`<small class="review-reason">理由：${escapeHTML(k.review_note)}</small>`:''}</td><td class="knowledge-actions"><div class="knowledge-action-buttons"><button class="table-link" data-preview="${k.kid}">查看</button><button class="table-link" data-edit="${k.kid}">编辑</button>${k.status==='draft'?`<button class="table-link publish-link" data-publish="${k.kid}">发布</button><button class="table-link danger-link" data-reject="${k.kid}">驳回</button>`:''}${k.status==='published'?`<button class="table-link" data-withdraw="${k.kid}">撤回</button>`:''}${k.status==='rejected'?`<button class="table-link" data-restore="${k.kid}">恢复审核</button>`:''}<button class="table-link danger-link" data-delete="${k.kid}">删除</button></div></td></tr>`).join('')||'<tr><td colspan="4">没有符合筛选条件的知识。</td></tr>';
  $('table-caption').textContent=`当前显示 ${rows.length} 条 / 共 ${list.length} 条 · 仅已发布内容可被公开搜索。`;
}
$('knowledge-status-filters').onclick=event=>{const button=event.target.closest('[data-status]');if(!button)return;$('admin-status').value=button.dataset.status;renderKnowledge();};
$('admin-search').oninput=renderKnowledge;$('admin-status').onchange=renderKnowledge;$('admin-category').onchange=renderKnowledge;$('admin-origin').onchange=renderKnowledge;$('refresh-knowledge').onclick=loadKnowledge;
async function editKnowledge(id){try{await loadCategories();}catch(error){toast(error.message);return;}if(!state.categories.length){toast('请先在分类管理中创建分类。');return;}fillCategorySelect();state.editId=id;$('edit-form').reset();$('edit-error').textContent='';$('edit-title').textContent=id?'编辑知识':'新增知识';if(id){try{const k=state.demo?state.knowledge.find(k=>k.kid===id):await request('/knowledge/'+id);for(const name of ['title','content','summary','category_id','keyword'])$('edit-form').elements[name].value=k[name]??'';}catch(error){toast(error.message);return;}}$('edit-dialog').showModal();}
$('add-knowledge').onclick=()=>editKnowledge(null);
$('knowledge-rows').onclick=async(event)=>{
  const btn=event.target.closest('[data-edit],[data-publish],[data-preview],[data-delete],[data-reject],[data-withdraw],[data-restore]');if(!btn||btn.disabled)return;
  const action=['edit','publish','preview','delete','reject','withdraw','restore'].find(key=>btn.dataset[key]);const id=Number(btn.dataset[action]);const item=state.knowledge.find(k=>k.kid===id);if(!item)return;
  if(action==='edit'){await editKnowledge(id);return;}if(action==='preview'){await openDetail({knowledge_id:id});return;}
  if(action==='reject'){state.reviewId=id;$('review-knowledge-title').textContent=item.title;$('review-reason').value='';$('review-error').textContent='';$('review-dialog').showModal();return;}
  if(action==='delete'&&!confirm(`确认永久删除「${item.title}」？关联问答、资料和向量也将删除，操作无法撤销。`))return;
  if(action==='withdraw'&&!confirm(`确认撤回「${item.title}」？撤回后普通用户将无法搜索或查看。`))return;
  btn.disabled=true;
  try{
    let result={};
    if(state.demo){if(action==='delete')state.knowledge=state.knowledge.filter(k=>k.kid!==id);else{item.status=action==='publish'?'published':'draft';item.review_note='';}}
    else if(action==='delete')result=await request(`/knowledge/${id}`,{method:'DELETE'});
    else if(action==='publish')result=await request(`/knowledge/${id}/publish`,{method:'PATCH'});
    else result=await request(`/knowledge/${id}/review`,jsonOptions('PATCH',{action}));
    toast(action==='publish'?(state.demo?'示例知识已发布':result.index_status==='ready'?'已发布，语义索引已更新':'已发布，索引暂未就绪，请检查本地模型服务。'):action==='delete'?'知识已删除':action==='withdraw'?'已撤回，内容重新进入待审核':'已恢复为待审核');
    await loadKnowledge();
  }catch(error){toast(error.message);btn.disabled=false;}
};
$('review-form').onsubmit=async(event)=>{
  event.preventDefault();const reason=$('review-reason').value.trim();const button=event.submitter;
  if(!reason){$('review-error').textContent='请填写驳回理由';return;}
  button.disabled=true;$('review-error').textContent='';
  try{
    const id=state.reviewId;
    if(state.demo){const item=state.knowledge.find(k=>k.kid===id);if(!item||item.status!=='draft')throw new Error('状态已改变，请刷新列表');item.status='rejected';item.review_note=reason;}
    else await request(`/knowledge/${id}/review`,jsonOptions('PATCH',{action:'reject',reason}));
    $('review-dialog').close();state.reviewId=null;toast('已驳回，内容和理由已保留');await loadKnowledge();
  }catch(error){$('review-error').textContent=error.message;}finally{button.disabled=false;}
};
$('edit-form').onsubmit=async(event)=>{event.preventDefault();const button=event.submitter;button.disabled=true;const payload=Object.fromEntries(new FormData(event.target));payload.category_id=Number(payload.category_id);payload.created_by=state.user.uid;const id=state.editId;let indexStatus;try{if(state.demo){if(id)Object.assign(state.knowledge.find(k=>k.kid===id),payload);else state.knowledge.push({...payload,kid:Math.max(0,...state.knowledge.map(k=>k.kid))+1,status:'draft'});}else {const result=await request(id?'/knowledge/'+id:'/knowledge',jsonOptions(id?'PUT':'POST',payload));indexStatus=result.index_status;}$('edit-dialog').close();toast(indexStatus==='pending'?'正文已保存，但语义索引未更新，请检查本地模型服务。':id?'知识已保存':'知识已创建为草稿');loadKnowledge();}catch(error){$('edit-error').textContent=error.message;}finally{button.disabled=false;}};
async function renderServices(){const container=$('services-panel');container.innerHTML='<p class="loading">正在检查服务状态</p>';let status=null;let error='';if(state.demo)error='演示模式不检测真实配置。';else try{status=await request(API.status);}catch(e){error=e.status===404?'服务状态接口尚未接入，当前无法判断是否配置。':e.message;}container.innerHTML=[['本地 BGE Embedding','将知识和问题转换成向量，为语义搜索提供基础。',status?.embedding],['DeepSeek','在你选择后，根据搜索结果提供解释。',status?.deepseek]].map(([name,desc,value])=>`<article class="service-card"><span class="eyebrow">MODEL SERVICE</span><h3>${name}</h3><span class="state ${value?.configured?'':'draft'}">${value?.configured===true?'已配置':value?.configured===false?'未配置 API Key':'待接入'}</span><p>${desc}</p><p>${escapeHTML(error||'密钥由后端环境变量管理，前端不读取密钥。')}</p></article>`).join('');}
document.querySelectorAll('.admin-tab').forEach(btn=>btn.onclick=()=>{document.querySelectorAll('.admin-tab').forEach(b=>b.classList.toggle('active',b===btn));$('knowledge-panel').hidden=btn.dataset.panel!=='knowledge';$('services-panel').hidden=btn.dataset.panel!=='services';$('categories-panel').hidden=btn.dataset.panel!=='categories';if(btn.dataset.panel==='categories')loadCategories().then(renderCategories).catch(e=>toast(e.message));if(btn.dataset.panel==='services')renderServices();});
document.querySelectorAll('[data-close]').forEach(btn=>btn.onclick=()=>btn.closest('dialog').close());document.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();}}));
$('help-button').onclick=()=>{$('detail-content').innerHTML='<h2 class="detail-title">从一个问题开始</h2><div class="detail-body">输入自然语言，先查看搜索到的知识，再决定是否让 DeepSeek 解释。\n\n语义搜索由本地 BGE 模型提供，结合关键词匹配排序；结果相关度不是正确概率。\n\n演示模式使用示例数据，不会调用模型。搜索历史只在本次页面会话中保留。\n\n搜索和 AI 解释独立：解释失败不会清除搜索结果。</div>';$('detail-dialog').showModal();};

// 页面刷新后通过服务端会话恢复身份；演示模式仅保存在当前页面。
request('/auth/me').then(user=>{if(!state.user)enter(user,false);}).catch(()=>{});

// 分类管理：编号由后端维护，知识编辑使用名称下拉框。
async function loadCategories(){
  if(!state.demo){const user=state.user;const data=await request('/categories');if(state.user!==user)return;state.categories=data.items||[];}
  renderCategories();
}
function fillCategorySelect(){
  $('knowledge-category').innerHTML='<option value="">请选择分类</option>'+state.categories.map(c=>`<option value="${c.cid}">${escapeHTML(c.name)}</option>`).join('');
}
function renderCategories(){
  $('category-rows').innerHTML=state.categories.map(c=>{const n=state.demo?state.knowledge.filter(k=>k.category_id===c.cid).length:c.knowledge_count;return `<tr><td>${escapeHTML(c.name)}<small>#${c.cid}</small></td><td>${escapeHTML(c.description||'暂无说明')}</td><td>${n??0}</td><td><button class="table-link" data-category-edit="${c.cid}">编辑</button><button class="table-link danger-link" data-category-delete="${c.cid}" ${n?'disabled title="请先转移分类下的知识"':''}>删除</button></td></tr>`;}).join('')||'<tr><td colspan="4">还没有分类，点击「新增分类」开始整理知识。</td></tr>';
}
function editCategory(id){
  state.categoryEditId=id;const form=$('category-form');form.reset();$('category-error').textContent='';$('category-title').textContent=id?'编辑分类':'新增分类';
  if(id){const c=state.categories.find(c=>c.cid===id);form.elements.name.value=c.name;form.elements.description.value=c.description||'';}
  $('category-dialog').showModal();
}
$('add-category').onclick=()=>editCategory(null);
$('category-rows').onclick=async(event)=>{
  const btn=event.target.closest('[data-category-edit],[data-category-delete]');if(!btn)return;
  const id=Number(btn.dataset.categoryEdit||btn.dataset.categoryDelete);if(btn.dataset.categoryEdit){editCategory(id);return;}
  const category=state.categories.find(c=>c.cid===id);if(!confirm(`确认删除分类「${category.name}」？分类下有知识时无法删除。`))return;
  btn.disabled=true;try{if(state.demo){if(state.knowledge.some(k=>k.category_id===id))throw new Error('分类下还有知识，请先转移后再删除。');state.categories=state.categories.filter(c=>c.cid!==id);}else await request('/categories/'+id,{method:'DELETE'});await loadCategories();toast('分类已删除');}catch(error){toast(error.message);btn.disabled=false;}
};
$('category-form').onsubmit=async(event)=>{
  event.preventDefault();const btn=event.submitter;btn.disabled=true;$('category-error').textContent='';
  const form=event.target;const payload={name:form.elements.name.value.trim(),description:form.elements.description.value.trim()};
  try{if(!payload.name)throw new Error('分类名称不能为空');const id=state.categoryEditId;
    if(state.demo){if(state.categories.some(c=>c.name===payload.name&&c.cid!==id))throw new Error('分类名称已存在');if(id)Object.assign(state.categories.find(c=>c.cid===id),payload);else state.categories.push({...payload,cid:Math.max(0,...state.categories.map(c=>c.cid))+1});}
    else await request(id?'/categories/'+id:'/categories',jsonOptions(id?'PUT':'POST',payload));
    $('category-dialog').close();await loadCategories();renderKnowledge();toast('分类已保存');
  }catch(error){$('category-error').textContent=error.message;}finally{btn.disabled=false;}
};

// 普通用户投稿：私有列表与公开搜索分开，作者和审核状态由后端维护。
async function loadSubmissions(){
  const user=state.user;
  try{
    if(!state.demo){const [data]=await Promise.all([request('/submissions'),loadCategories()]);if(state.user!==user)return;state.ownSubmissions=data.items||[];}
    renderSubmissions();
  }catch(error){$('submission-rows').innerHTML=`<tr><td colspan="3">${escapeHTML(error.message)}</td></tr>`;}
}
function renderSubmissions(){
  const status=$('submission-status').value||'all';const items=state.ownSubmissions.filter(item=>status==='all'||item.status===status);
  $('submission-rows').innerHTML=items.map(item=>`<tr><td>${escapeHTML(item.title)}<small>#${item.kid} · ${escapeHTML(state.categories.find(c=>c.cid===item.category_id)?.name||'未分类')}</small><small>来源：${escapeHTML(item.source_name||'未填写')}${item.source_url?' · 已附链接':''}</small></td><td><span class="state ${item.status==='published'?'':item.status==='rejected'?'rejected':'draft'}">${item.status==='draft'?'待审核':escapeHTML(knowledgeStatusLabel(item.status))}</span>${item.status==='rejected'?`<p class="review-reason">${escapeHTML(item.review_note||'请联系管理员了解修改建议')}</p>`:''}</td><td><button class="table-link" data-submission-view="${item.kid}">查看</button>${['draft','rejected'].includes(item.status)?`<button class="table-link" data-submission-edit="${item.kid}">${item.status==='rejected'?'修改后重投':'修改投稿'}</button>`:'<small>已发布，由管理员维护</small>'}</td></tr>`).join('')||'<tr><td colspan="3">暂无符合条件的投稿。点击「提交知识」，分享你的第一条校园知识。</td></tr>';
  $('submission-caption').textContent=`当前显示 ${items.length} 条 / 共 ${state.ownSubmissions.length} 条投稿${state.demo?' · 体验模式仅保存在本次页面':''}`;
}
async function openSubmission(id){
  const user=state.user;
  try{
    await loadCategories();if(state.user!==user)return;
    if(!state.categories.length){toast('暂时没有可选分类，请联系管理员创建分类。');return;}
    let item=null;if(id)item=state.demo?state.ownSubmissions.find(item=>item.kid===id):await request('/submissions/'+id);
    if(state.user!==user)return;
    state.submissionEditId=id;const form=$('submission-form');form.reset();$('submission-error').textContent='';
    $('submission-title').textContent=id?'修改投稿':'提交知识';$('submission-submit').textContent=id?'保存并重新提交审核':'提交审核';
    $('submission-category').innerHTML='<option value="">请选择分类</option>'+state.categories.map(c=>`<option value="${c.cid}">${escapeHTML(c.name)}</option>`).join('');
    if(item)for(const name of ['title','content','summary','category_id','keyword','source_name','source_url'])form.elements[name].value=item[name]??'';
    $('submission-dialog').showModal();
  }catch(error){toast(error.message);}
}
$('add-submission').onclick=()=>openSubmission(null);
$('submission-status').onchange=renderSubmissions;$('refresh-submissions').onclick=loadSubmissions;
$('submission-rows').onclick=async(event)=>{
  const button=event.target.closest('[data-submission-view],[data-submission-edit]');if(!button)return;
  const id=Number(button.dataset.submissionView||button.dataset.submissionEdit);
  if(button.dataset.submissionEdit){await openSubmission(id);return;}
  $('detail-content').innerHTML='<p class="loading">正在打开投稿</p>';$('detail-dialog').showModal();
  try{const item=state.demo?state.ownSubmissions.find(item=>item.kid===id):await request('/submissions/'+id);if($('detail-dialog').open)$('detail-content').innerHTML=renderKnowledgeDetail(item);}
  catch(error){$('detail-content').innerHTML=`<p class="inline-error">${escapeHTML(error.message)}</p>`;}
};
$('submission-form').onsubmit=async(event)=>{
  event.preventDefault();const button=event.submitter;const user=state.user;button.disabled=true;$('submission-error').textContent='';
  try{
    const payload={};for(const name of ['title','content','summary','category_id','keyword','source_name','source_url'])payload[name]=String(event.target.elements[name].value??'').trim();
    payload.category_id=Number(payload.category_id);payload.source_url=payload.source_url||null;
    if(payload.title.length<5||payload.content.length<10||!payload.category_id)throw new Error('请填写至少5个字的标题、10个字的正文，并选择分类。');
    const id=state.submissionEditId;
    if(state.demo){
      const item=id?state.ownSubmissions.find(item=>item.kid===id):null;
      if(id&&(!item||!['draft','rejected'].includes(item.status)))throw new Error('已发布内容由管理员维护');
      const values={...payload,status:'draft',review_note:'',created_by:user.uid,created_by_name:user.username,is_submission:true,sources:[{source_type:'student_submission',source_name:payload.source_name||'用户投稿',source_url:payload.source_url}]};
      if(item)Object.assign(item,values);else{const created={...values,kid:Math.max(0,...state.knowledge.map(k=>k.kid))+1};state.ownSubmissions.unshift(created);state.knowledge.push(created);}
    }else await request(id?'/submissions/'+id:'/submissions',jsonOptions(id?'PUT':'POST',payload));
    if(state.user!==user)return;
    $('submission-dialog').close();state.submissionEditId=null;toast('投稿已提交，等待管理员审核');showView('submissions');
  }catch(error){$('submission-error').textContent=error.message;}finally{button.disabled=false;}
};
