'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const styles = {glass:'薄荷玻璃', oak:'原木开放', arch:'圆拱高柜', wide:'宽幅陈列'};
const state = {user:null, items:[], categories:[], events:[], status:'all', page:1, pageSize:12, refreshing:false};
let formAction = null, toastTimer;

async function api(path, method='GET', body) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(path, {method, credentials:'same-origin', signal:controller.signal,
      headers:{'Content-Type':'application/json'}, body:body === undefined ? undefined : JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) {
      const error = new Error(typeof data.detail === 'string' ? data.detail : '请求未能完成，请检查填写内容。');
      error.status = response.status;
      throw error;
    }
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('请求超时，请稍后重试。');
    throw error;
  } finally { clearTimeout(timer); }
}
function toast(text) {
  $('toast').textContent = text; $('toast').hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4000);
}
function report(error) { $('page-error').textContent = error.message; $('page-error').hidden = false; }
function date(value) { return value ? new Date(value).toLocaleString('zh-CN', {month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false}) : '—'; }
function categoryName(id) { return state.categories.find(c => c.id === id)?.name || '未分类'; }
function currentCategories() {
  const used = new Set(state.items.map(item => item.category_id));
  return state.categories.filter(c => c.count > 0 || c.has_shelf || used.has(c.id));
}

async function refreshData() {
  if (state.refreshing) return;
  state.refreshing = true; $('refresh').disabled = true; $('refresh').setAttribute('aria-busy', 'true');
  try {
    const [knowledge, categories, events] = await Promise.all([
      api('/api/admin/knowledge?state=all'), api('/api/admin/categories'), api('/api/admin/events')]);
    state.items = knowledge.items; state.categories = categories.items; state.events = events.items;
    $('page-error').hidden = true;
    const selected = $('knowledge-category').value;
    $('knowledge-category').innerHTML = '<option value="">全部分类</option>' + state.categories.filter(c => state.items.some(k => k.category_id === c.id)).map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('');
    $('knowledge-category').value = selected;
    $('stat-total').textContent = state.items.length;
    $('stat-categories').textContent = currentCategories().length;
    const hidden = state.items.filter(item => item.hidden).length;
    $('stat-hidden').textContent = hidden;
    $('nav-count').textContent = state.items.length;
    $('count-all').textContent = state.items.length;
    $('count-active').textContent = state.items.length - hidden;
    $('count-hidden').textContent = hidden;
    renderContent(); renderCategories(); renderEvents();
  } finally {
    state.refreshing = false; $('refresh').disabled = false; $('refresh').removeAttribute('aria-busy');
  }
}

function navigate() {
  const tab = ['content','categories','events'].includes(location.hash.slice(1)) ? location.hash.slice(1) : 'content';
  for (const name of ['content','categories','events']) {
    $(name+'-view').hidden = name !== tab;
    const link = document.querySelector(`[data-tab="${name}"]`);
    if (name === tab) link.setAttribute('aria-current','page'); else link.removeAttribute('aria-current');
  }
  $('breadcrumb').textContent = {content:'公共知识',categories:'分类与书架',events:'操作记录'}[tab];
}

function renderContent() {
  const query = $('knowledge-search').value.trim().toLowerCase(), category = $('knowledge-category').value;
  const filtered = state.items.filter(item =>
    (state.status === 'all' || (state.status === 'hidden' ? item.hidden : !item.hidden)) &&
    (!category || item.category_id === Number(category)) &&
    (!query || [item.title,item.summary,item.author].join(' ').toLowerCase().includes(query)));
  const pages = Math.max(1, Math.ceil(filtered.length / state.pageSize));
  state.page = Math.min(state.page, pages);
  const start = (state.page - 1) * state.pageSize;
  $('knowledge-rows').innerHTML = filtered.slice(start, start + state.pageSize).map(item => `<tr>
    <td class="title-cell" data-label="知识内容"><span class="book-mark" aria-hidden="true"></span><div><button class="title-button" data-action="preview" data-id="${item.kid}">${esc(item.title)}</button><p>${esc((item.summary || '').replace(/\s+/g,' '))}</p></div></td>
    <td data-label="所属分类"><span class="category-label">${esc(categoryName(item.category_id))}</span></td>
    <td data-label="分享者">${esc(item.author)}</td>
    <td data-label="状态"><span class="pill ${item.hidden ? 'muted-pill' : 'green-pill'}">${item.hidden ? '已下架' : '展示中'}</span></td>
    <td data-label="更新时间" class="date-cell">${esc(date(item.updated_at))}</td>
    <td data-label="操作"><div class="row-actions"><button data-action="preview" data-id="${item.kid}">查看</button><button class="${item.hidden ? 'restore' : 'warning'}" data-action="moderate" data-id="${item.kid}">${item.hidden ? '恢复' : '下架'}</button></div></td>
  </tr>`).join('');
  $('content-empty').hidden = filtered.length > 0;
  document.querySelector('.table-wrap').hidden = filtered.length === 0;
  $('content-count').textContent = filtered.length + ' 条知识';
  $('page-summary').textContent = filtered.length ? `第 ${start + 1}–${Math.min(start + state.pageSize, filtered.length)} 条，共 ${filtered.length} 条` : '暂无符合条件的知识';
  $('page-number').textContent = `${state.page} / ${pages}`;
  $('prev-page').disabled = state.page <= 1; $('next-page').disabled = state.page >= pages;
  document.querySelectorAll('[data-state]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.state === state.status)));
}

function renderCategories() {
  const query = $('category-search').value.trim().toLowerCase();
  const categories = ($('category-scope').value === 'all' ? state.categories : currentCategories()).filter(c => c.name.toLowerCase().includes(query));
  $('category-grid').innerHTML = categories.map(c => `<article class="category-card">
    <div class="category-card-top"><div class="shelf-mini shelf-${esc(c.shelf_style)}" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div><span class="pill ${c.visible ? 'green-pill' : 'muted-pill'}">${c.visible ? '书架已展示' : '书架已隐藏'}</span></div>
    <h3>${esc(c.name)}</h3><p class="category-description">${esc(c.description || '为相关知识留一处归所。')}</p>
    <div class="category-meta"><span><strong>${c.count}</strong> 条可见知识</span><span>${esc(styles[c.shelf_style] || styles.glass)}</span></div>
    <div class="category-actions"><button class="button outline" data-action="edit-category" data-id="${c.id}">编辑与设置</button><button class="quiet warning" data-action="delete-category" data-id="${c.id}">删除分类</button></div>
  </article>`).join('');
  $('category-empty').hidden = categories.length > 0;
}

function eventDescription(event) {
  try {
    const detail = JSON.parse(event.detail);
    const parts = [];
    if (detail.title || detail.name) parts.push(detail.title || detail.name);
    else if (detail.category_id) parts.push(categoryName(detail.category_id));
    if (typeof detail.visible === 'boolean') parts.push(detail.visible ? '允许展示书架' : '隐藏书架');
    if (detail.shelf_style) parts.push(styles[detail.shelf_style] || '更新书架样式');
    if (detail.reason) parts.push(detail.reason);
    return parts.join(' · ') || '已记录本次知识库维护操作。';
  } catch { return '已记录本次知识库维护操作。'; }
}
function renderEvents() {
  $('event-list').innerHTML = state.events.map(event => `<article class="event-row"><span class="event-dot" aria-hidden="true">${icon('check')}</span><div><h3>${esc(event.action.replace(/行星/g,'书架'))}<span>${esc(event.actor)}</span></h3><p>${esc(eventDescription(event))}</p></div><time>${esc(date(event.created_at))}</time></article>`).join('');
  $('events-empty').hidden = state.events.length > 0;
}

function openForm(title, fields, action, label='保存设置') {
  $('dialog-title').textContent = title; $('form-fields').innerHTML = fields; $('form-error').textContent = '';
  $('form-submit').textContent = label; formAction = action; $('form-dialog').showModal();
}
function styleOptions(selected='glass') { return Object.entries(styles).map(([value,label]) => `<option value="${value}" ${value === selected ? 'selected' : ''}>${label}</option>`).join(''); }
function newCategory() {
  openForm('新建公共书架', `<p class="form-hint">新的知识分类会拥有一座独立书架。</p><label>书架名称<input name="name" required maxlength="100" placeholder="例如：机器学习"></label><label>书架样式<select name="style">${styleOptions()}</select></label>`, async form => {
    await api('/api/library/shelves','POST',{name:form.elements.name.value.trim(),space:'public',style:form.elements.style.value});
  }, '创建书架');
}
function editCategory(category) {
  openForm('编辑分类与书架', `<label>分类名称<input name="name" required maxlength="100" value="${esc(category.name)}"></label><label>分类简介<textarea name="description" rows="3" maxlength="1000">${esc(category.description)}</textarea></label><label>书架样式<select name="shelf_style">${styleOptions(category.shelf_style)}</select></label><label class="check-label"><input name="visible" type="checkbox" ${category.visible ? 'checked' : ''}>在图书馆展示书架</label><p class="form-hint">隐藏书架只影响展示，不会删除知识或阻止搜索。</p>`, async form => {
    await api('/api/admin/categories/'+category.id,'PUT',{name:form.elements.name.value.trim(),description:form.elements.description.value.trim(),shelf_style:form.elements.shelf_style.value,visible:form.elements.visible.checked});
  });
}
function deleteCategory(category) {
  openForm('删除分类', `<p class="confirmation">确定删除「${esc(category.name)}」吗？</p><p class="form-hint">分类下存在任何知识时，系统会阻止删除。请先转移相关知识。</p>`, () => api('/categories/'+category.id,'DELETE'), '确认删除');
}
function moderate(item) {
  if ($('detail-dialog').open) $('detail-dialog').close();
  const hidden = !item.hidden;
  openForm(hidden ? '下架公有知识' : '恢复公有知识', `<p class="confirmation">${esc(item.title)}</p><p class="form-hint">${hidden ? '下架后，其他用户将无法阅读、搜索或通过 AI 使用这份知识。作者仍可管理原文。' : '恢复后，这份知识将重新出现在公共知识库中。'}</p><label>${hidden ? '下架原因（必填）' : '恢复说明（可选）'}<textarea name="reason" rows="3" maxlength="500" ${hidden ? 'required' : ''} placeholder="${hidden ? '请说明需要修正的内容…' : '填写本次恢复的说明…'}"></textarea></label>`, async form => {
    const reason = form.elements.reason.value.trim();
    if (hidden && !reason) throw new Error('请填写下架原因。');
    await api('/api/admin/knowledge/'+item.kid+'/moderation','POST',{hidden,reason});
  }, hidden ? '确认下架' : '确认恢复');
}
async function preview(id) {
  const item = await api('/api/admin/knowledge/'+id);
  const safeSources = (item.sources || []).map(source => {
    try { const url = new URL(source.source_url); if (!['http:','https:'].includes(url.protocol) || url.username || url.password) return ''; return `<a href="${esc(url.href)}" target="_blank" rel="noopener noreferrer">${esc(source.source_name || '原文来源')} ↗</a>`; } catch { return ''; }
  }).join('');
  $('detail-content').innerHTML = `<span class="pill ${item.hidden ? 'muted-pill' : 'green-pill'}">${item.hidden ? '已下架' : '展示中'}</span><h2>${esc(item.title)}</h2><p class="detail-meta">${esc(categoryName(item.category_id))} · ${esc(item.author)} · ${esc(date(item.updated_at))}</p>${item.moderation_reason ? `<div class="moderation-note">下架原因：${esc(item.moderation_reason)}</div>` : ''}<article id="detail-body"></article><div class="source-links">${safeSources}</div><button id="detail-moderate" class="button outline">${item.hidden ? '恢复公有展示' : '下架这份知识'}</button>`;
  $('detail-body').textContent = item.content;
  $('detail-moderate').onclick = () => moderate(item);
  $('detail-dialog').showModal();
}
function batchDisplay(visible) {
  openForm(visible ? '展示全部书架' : '隐藏全部书架', `<p class="confirmation">${visible ? '允许全部公共分类在图书馆中展示。' : '隐藏全部公共书架，公有知识仍然可以搜索。'}</p>`, () => api('/api/admin/categories/display','PATCH',{visible}), '确认设置');
}

$('action-form').onsubmit = async event => {
  event.preventDefault(); const form = event.currentTarget, action = formAction;
  const buttons = [...form.querySelectorAll('button')]; buttons.forEach(b => b.disabled = true);
  $('form-error').textContent = ''; $('form-submit').setAttribute('aria-busy','true');
  try {
    await action(form); $('form-dialog').close(); toast('操作已完成。');
    try { await refreshData(); } catch (error) { report(new Error('操作已保存，但刷新失败：'+error.message)); }
  } catch (error) { $('form-error').textContent = error.message; }
  finally { buttons.forEach(b => b.disabled = false); $('form-submit').removeAttribute('aria-busy'); }
};
document.querySelectorAll('[data-close]').forEach(button => button.onclick = () => $(button.dataset.close).close());
document.querySelectorAll('[data-state]').forEach(button => button.onclick = () => { state.status = button.dataset.state; state.page = 1; renderContent(); });
$('knowledge-search').oninput = $('knowledge-category').onchange = () => { state.page = 1; renderContent(); };
$('category-search').oninput = $('category-scope').onchange = renderCategories;
$('clear-filters').onclick = () => { state.status = 'all'; state.page = 1; $('knowledge-search').value = ''; $('knowledge-category').value = ''; renderContent(); };
$('prev-page').onclick = () => { state.page--; renderContent(); };
$('next-page').onclick = () => { state.page++; renderContent(); };
$('new-category').onclick = newCategory;
$('show-all').onclick = () => batchDisplay(true); $('hide-all').onclick = () => batchDisplay(false);
$('refresh').onclick = () => refreshData().catch(report);
$('dashboard').addEventListener('click', event => {
  const button = event.target.closest('button[data-action]'); if (!button) return;
  const id = Number(button.dataset.id), action = button.dataset.action;
  if (action === 'preview') preview(id).catch(report);
  else if (action === 'moderate') moderate(state.items.find(item => item.kid === id));
  else if (action === 'edit-category') editCategory(state.categories.find(category => category.id === id));
  else if (action === 'delete-category') deleteCategory(state.categories.find(category => category.id === id));
});
$('logout').onclick = async () => { try { await api('/logout','POST',{}); location.assign('/library'); } catch (error) { report(error); } };
window.addEventListener('hashchange', navigate);

(async function boot() {
  try {
    state.user = await api('/auth/me');
    if (state.user.role !== 'admin') { const error = new Error('当前账号没有管理员权限。请返回图书馆继续浏览。'); error.status = 403; throw error; }
    $('username').textContent = state.user.username; $('avatar').textContent = state.user.username.slice(0,1).toUpperCase();
    await refreshData(); navigate(); $('access-state').hidden = true; $('dashboard').hidden = false;
    api('/ai/status').then(info => $('service-status').textContent = `${info.embedding.configured ? '本地语义搜索已连接' : '本地语义搜索待连接'} · ${info.deepseek.configured ? 'DeepSeek 已配置' : 'DeepSeek 待配置'}`).catch(() => $('service-status').textContent = '模型连接状态暂不可用');
  } catch (error) {
    $('access-title').textContent = error.status === 401 ? '先登录，再整理知识。' : error.status === 403 ? '这是管理员的工作空间。' : '暂时无法打开管理中心';
    $('access-description').textContent = error.message;
    $('access-link').hidden = false;
  }
})();
