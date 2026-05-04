/* ============================================================
   FinGuard AI – app.js  (all frontend logic)
   ============================================================ */

const API = '';   // same origin
let sessionId = localStorage.getItem('fg_session') || null;

// ── Tab switching ──────────────────────────────────────────
function showTab(name, btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
  const titles = { chat:'Ask FinGuard', market:'Live Market', tools:'Calculators', budget:'Budget Planner', kb:'Knowledge Base' };
  document.getElementById('topbarTitle').textContent = titles[name] || name;
  if (name === 'market') loadMarket();
  if (name === 'kb') loadKB();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ── Health check ───────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch(`${API}/api/health`);
    const d = await r.json();
    document.getElementById('healthDot').className = 'health-dot online';
    document.getElementById('healthLabel').textContent = 'Online';
    document.getElementById('kbBadge').textContent = `KB: ${d.kb_docs} chunks`;
  } catch {
    document.getElementById('healthDot').className = 'health-dot offline';
    document.getElementById('healthLabel').textContent = 'Offline';
  }
}

// ── Chat ───────────────────────────────────────────────────
function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
}

function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function sendQuick(text) {
  document.getElementById('chatInput').value = text;
  sendMessage();
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  appendMsg('user', text);
  input.value = '';
  input.style.height = 'auto';

  const btn = document.getElementById('sendBtn');
  btn.disabled = true;

  const typingId = appendTyping();

  try {
    const res = await fetch(`${API}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id: sessionId })
    });
    const data = await res.json();
    sessionId = data.session_id;
    localStorage.setItem('fg_session', sessionId);
    removeTyping(typingId);
    appendMsg('ai', data.answer, data.sources);
  } catch (err) {
    removeTyping(typingId);
    appendMsg('ai', 'Connection error. Please ensure the server is running.');
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

function appendMsg(role, text, sources) {
  const wrap = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = `msg ${role}`;

  const avatar = `<div class="avatar">${role === 'ai' ? 'FG' : 'You'}</div>`;
  const md = role === 'ai' ? markdownLite(text) : `<p>${escHtml(text)}</p>`;
  let srcHtml = '';
  if (sources && sources.length) {
    srcHtml = `<div class="sources">${sources.map(s => `<span class="source-tag">${s}</span>`).join('')}</div>`;
  }
  div.innerHTML = `${avatar}<div class="bubble">${md}${srcHtml}</div>`;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
}

function appendTyping() {
  const wrap = document.getElementById('chatMessages');
  const id = 'typing_' + Date.now();
  const div = document.createElement('div');
  div.className = 'msg ai';
  div.id = id;
  div.innerHTML = `<div class="avatar">FG</div><div class="bubble"><div class="typing"><span></span><span></span><span></span></div></div>`;
  wrap.appendChild(div);
  wrap.scrollTop = wrap.scrollHeight;
  return id;
}

function removeTyping(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function newChat() {
  if (sessionId) fetch(`${API}/api/chat/history/${sessionId}`, { method: 'DELETE' });
  sessionId = null;
  localStorage.removeItem('fg_session');
  const wrap = document.getElementById('chatMessages');
  wrap.innerHTML = '';
  appendMsg('ai', 'New session started. How can I help you today?');
}

// Simple markdown renderer
function markdownLite(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br/>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>');
}

function escHtml(t) {
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Market ─────────────────────────────────────────────────
async function loadMarket() {
  const grid = document.getElementById('indicesGrid');
  grid.innerHTML = '<div class="loading-pulse">Fetching live data…</div>';
  try {
    const res = await fetch(`${API}/api/market/summary/indices`);
    const data = await res.json();
    if (!Object.keys(data).length) { grid.innerHTML = '<p style="color:var(--text2)">No data available.</p>'; return; }
    grid.innerHTML = Object.entries(data).map(([name, d]) => {
      const cls = d.change_pct >= 0 ? 'pos' : 'neg';
      const arrow = d.change_pct >= 0 ? '▲' : '▼';
      return `<div class="index-card">
        <div class="index-name">${name}</div>
        <div class="index-price">${fmtNum(d.price)}</div>
        <div class="index-change ${cls}">${arrow} ${Math.abs(d.change_pct).toFixed(2)}%</div>
      </div>`;
    }).join('');
  } catch {
    grid.innerHTML = '<p style="color:var(--text2)">Could not load market data.</p>';
  }
}

async function lookupStock() {
  const sym = document.getElementById('stockSymbol').value.trim().toUpperCase();
  if (!sym) return;
  const box = document.getElementById('stockResult');
  box.innerHTML = '<div class="loading-pulse">Looking up…</div>';
  try {
    const res = await fetch(`${API}/api/market/${sym}`);
    if (!res.ok) { box.innerHTML = `<p style="color:var(--red)">Symbol not found.</p>`; return; }
    const d = await res.json();
    const cls = d.change >= 0 ? 'pos' : 'neg';
    const arrow = d.change >= 0 ? '▲' : '▼';
    box.innerHTML = `
      <div style="margin-bottom:12px">
        <div style="font-size:20px;font-weight:700">${d.name}</div>
        <div style="font-size:28px;font-weight:800;color:var(--accent2)">${fmtNum(d.price)} <span style="font-size:14px">${d.currency}</span></div>
        <div class="index-change ${cls}" style="font-size:14px;margin-top:4px">${arrow} ${d.change} (${Math.abs(d.change_pct).toFixed(2)}%)</div>
      </div>
      <div class="stock-card">
        ${stockStat('Sector', d.sector || '—')}
        ${stockStat('P/E Ratio', d.pe_ratio ? d.pe_ratio.toFixed(2) : '—')}
        ${stockStat('52W High', d['52w_high'] ? fmtNum(d['52w_high']) : '—')}
        ${stockStat('52W Low', d['52w_low'] ? fmtNum(d['52w_low']) : '—')}
        ${stockStat('Market Cap', d.market_cap ? fmtCap(d.market_cap) : '—')}
        ${stockStat('Volume', d.volume ? fmtNum(d.volume) : '—')}
      </div>`;
  } catch {
    box.innerHTML = '<p style="color:var(--red)">Error fetching stock data.</p>';
  }
}

function stockStat(label, val) {
  return `<div class="stock-stat"><div class="stat-label">${label}</div><div class="stat-value">${val}</div></div>`;
}

// ── Calculators ────────────────────────────────────────────
async function calcSIP() {
  const body = { monthly_investment: +document.getElementById('sipAmt').value, annual_rate: +document.getElementById('sipRate').value, years: +document.getElementById('sipYrs').value };
  const d = await postJSON('/api/tools/sip', body);
  document.getElementById('sipResult').innerHTML = `
    ${resRow('Invested', '₹' + fmtNum(d.total_invested))}
    ${resRow('Est. Returns', '₹' + fmtNum(d.estimated_returns))}
    ${resRow('Maturity Value', '₹' + fmtNum(d.maturity_value))}
    ${resRow('Wealth Gain', d.wealth_gained_pct + '%')}`;
}

async function calcEMI() {
  const body = { principal: +document.getElementById('emiPrin').value, annual_rate: +document.getElementById('emiRate').value, years: +document.getElementById('emiYrs').value };
  const d = await postJSON('/api/tools/emi', body);
  document.getElementById('emiResult').innerHTML = `
    ${resRow('Monthly EMI', '₹' + fmtNum(d.emi))}
    ${resRow('Total Payment', '₹' + fmtNum(d.total_payment))}
    ${resRow('Total Interest', '₹' + fmtNum(d.total_interest))}
    ${resRow('Interest %', d.interest_pct + '%')}`;
}

async function calcCI() {
  const body = { principal: +document.getElementById('ciPrin').value, annual_rate: +document.getElementById('ciRate').value, years: +document.getElementById('ciYrs').value, compounds_per_year: +document.getElementById('ciN').value };
  const d = await postJSON('/api/tools/compound', body);
  document.getElementById('ciResult').innerHTML = `
    ${resRow('Final Amount', '₹' + fmtNum(d.final_amount))}
    ${resRow('Interest Earned', '₹' + fmtNum(d.interest_earned))}
    ${resRow('Effective Rate', d.effective_annual_rate + '%')}`;
}



function resRow(key, val) {
  return `<div class="res-row"><span class="key">${key}</span><span class="val">${val}</span></div>`;
}

// ── Budget Planner ─────────────────────────────────────────
let expenses = [];

function addExpense() {
  const cat = document.getElementById('expCat').value.trim();
  const amt = parseFloat(document.getElementById('expAmt').value);
  if (!cat || !amt || amt <= 0) return;
  expenses.push({ category: cat, amount: amt });
  document.getElementById('expCat').value = '';
  document.getElementById('expAmt').value = '';
  renderExpenseList();
}

function removeExpense(idx) {
  expenses.splice(idx, 1);
  renderExpenseList();
}

function renderExpenseList() {
  const list = document.getElementById('expenseList');
  if (!expenses.length) { list.innerHTML = '<p style="font-size:13px;color:var(--text2)">No expenses added yet.</p>'; return; }
  const colors = ['c1','c2','c3','c4','c5'];
  list.innerHTML = expenses.map((e, i) => `
    <div class="expense-item">
      <div class="expense-cat">${e.category}</div>
      <div class="expense-amt">Rs ${fmtNum(e.amount)}</div>
      <button class="expense-del" onclick="removeExpense(${i})" title="Remove">x</button>
    </div>`).join('');
}

function resetBudget() {
  expenses = [];
  document.getElementById('budgetIncome').value = '50000';
  renderExpenseList();
  document.getElementById('budgetResult').innerHTML = `
    <div class="budget-placeholder">
      <div class="bp-icon">BP</div>
      <p>Add your income and expenses, then click Analyze Budget to see your financial health.</p>
    </div>`;
}

async function analyzeBudget() {
  const income = parseFloat(document.getElementById('budgetIncome').value);
  if (!income || income <= 0) { alert('Please enter a valid income.'); return; }
  if (!expenses.length) { alert('Please add at least one expense.'); return; }
  const body = { income, items: expenses };
  const d = await postJSON('/api/tools/budget', body);
  renderBudgetResult(d);
}

function renderBudgetResult(d) {
  const colors = ['c1','c2','c3','c4','c5'];
  const remClass = d.remaining >= 0 ? 'green' : 'red';
  const savClass = d.savings_pct >= 20 ? 'green' : d.savings_pct >= 10 ? 'accent' : 'red';

  const bars = d.items.map((item, i) => `
    <div class="bar-row">
      <div class="bar-label-row">
        <span>${item.category}</span>
        <span>Rs ${fmtNum(item.amount)} (${item.pct}%)</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill ${colors[i % colors.length]}" style="width:${Math.min(item.pct, 100)}%"></div>
      </div>
    </div>`).join('');

  const r = d.rule_5030;
  const needsBadge = r.needs_pct <= 50 ? 'ok' : 'bad';
  const wantsBadge = r.wants_pct <= 30 ? 'ok' : 'bad';
  const savBadge   = r.savings_pct >= 20 ? 'ok' : r.savings_pct >= 10 ? 'warn' : 'bad';

  document.getElementById('budgetResult').innerHTML = `
    <div class="budget-summary">
      <div class="b-stat">
        <div class="b-stat-label">Total Spent</div>
        <div class="b-stat-value red">Rs ${fmtNum(d.total_spent)}</div>
      </div>
      <div class="b-stat">
        <div class="b-stat-label">Remaining</div>
        <div class="b-stat-value ${remClass}">Rs ${fmtNum(Math.abs(d.remaining))}${d.remaining < 0 ? ' deficit' : ''}</div>
      </div>
      <div class="b-stat">
        <div class="b-stat-label">Savings Rate</div>
        <div class="b-stat-value ${savClass}">${d.savings_pct}%</div>
      </div>
    </div>
    <div class="budget-bars">
      <h3>Expense Breakdown</h3>
      ${bars}
    </div>
    <div class="rule-card">
      <h3>50-30-20 Rule Analysis</h3>
      <div class="rule-row">
        <span class="rule-name">Needs (target: max 50%) — ${r.needs_pct}%</span>
        <span class="rule-badge ${needsBadge}">${r.needs_pct <= 50 ? 'Good' : 'Over limit'}</span>
      </div>
      <div class="rule-row">
        <span class="rule-name">Wants (target: max 30%) — ${r.wants_pct}%</span>
        <span class="rule-badge ${wantsBadge}">${r.wants_pct <= 30 ? 'Good' : 'Over limit'}</span>
      </div>
      <div class="rule-row">
        <span class="rule-name">Savings (target: min 20%) — ${r.savings_pct}%</span>
        <span class="rule-badge ${savBadge}">${r.savings_pct >= 20 ? 'Excellent' : r.savings_pct >= 10 ? 'Needs work' : 'Too low'}</span>
      </div>
    </div>`;
}

// ── Knowledge Base ─────────────────────────────────────────
async function loadKB() {
  const box = document.getElementById('kbStats');
  box.innerHTML = '<div class="loading-pulse">Loading…</div>';
  try {
    const res = await fetch(`${API}/api/kb/stats`);
    const d = await res.json();
    box.innerHTML = `
      ${kbCard('Total Chunks', d.total_chunks)}
      ${kbCard('Collection', d.collection)}
      ${kbCard('DB Path', d.db_path.split('/').slice(-2).join('/'))}`;
  } catch {
    box.innerHTML = '<p style="color:var(--red)">Could not load KB stats.</p>';
  }
}

function kbCard(label, value) {
  return `<div class="kb-stat-card"><div class="kb-stat-label">${label}</div><div class="kb-stat-value" style="font-size:${String(value).length > 10 ? '14px' : '28px'}">${value}</div></div>`;
}

async function clearKB() {
  if (!confirm('Clear all knowledge base data? Built-in knowledge will be restored.')) return;
  await fetch(`${API}/api/kb/clear`, { method: 'DELETE' });
  loadKB(); checkHealth();
}

// ── Helpers ────────────────────────────────────────────────
async function postJSON(url, body) {
  const res = await fetch(API + url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  return res.json();
}

function fmtNum(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function fmtCap(n) {
  if (n >= 1e12) return (n / 1e12).toFixed(2) + 'T';
  if (n >= 1e9)  return (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e7)  return (n / 1e7).toFixed(2) + 'Cr';
  return fmtNum(n);
}

// ── Init ───────────────────────────────────────────────────
checkHealth();
renderExpenseList();
setInterval(checkHealth, 30000);
