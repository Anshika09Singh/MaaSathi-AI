const API = 'http://127.0.0.1:5000';
let currentUser = null;
const SOUND_PREFS_KEY = 'maasathi-sound-prefs';
let audioContext = null;

function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `show ${type}`;
  clearTimeout(t._tid);
  t._tid = setTimeout(() => t.classList.remove('show'), 3500);
}

async function apiFetch(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    ...opts,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
  });
  if (res.status === 401) {
    window.location.href = '/login.html';
    throw new Error('Unauthenticated');
  }
  return res.json();
}

function badge(val, type) {
  return `<span class="badge badge-${type}">${val}</span>`;
}

function priorityBadge(p) {
  return badge(p, p === 'high' ? 'high' : p === 'medium' ? 'medium' : 'low');
}

function empty(icon, msg) {
  return `<div class="empty-state"><div class="empty-icon">${icon}</div>${msg}</div>`;
}

function getSoundPrefs() {
  try {
    return JSON.parse(localStorage.getItem(SOUND_PREFS_KEY)) || { alarm: 80, notification: 55 };
  } catch {
    return { alarm: 80, notification: 55 };
  }
}

function saveSoundPrefs(prefs) {
  localStorage.setItem(SOUND_PREFS_KEY, JSON.stringify(prefs));
}

async function checkAuth() {
  try {
    const data = await apiFetch('/api/auth/me');
    if (!data.authenticated) {
      window.location.href = '/login.html';
      return false;
    }
    currentUser = data.user;
    return true;
  } catch {
    window.location.href = '/login.html';
    return false;
  }
}

const pageTitles = {
  overview: ['Overview', 'Your family at a glance'],
  chat: ['AI Chat', 'Powered by Groq with Ollama backup · RAG memory'],
  tasks: ['Tasks', 'AI-balanced household task management'],
  reminders: ['Reminders', 'Smart priority auto-detection'],
  meals: ['Meal Planner', 'AI-powered nutrition planning'],
  safety: ['Safety', 'Emergency SOS and safety logs'],
};

function switchSection(name) {
  document.querySelectorAll('.content').forEach((el) => el.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach((el) => el.classList.remove('active'));

  const sec = document.getElementById(`section-${name}`);
  if (sec) sec.classList.add('active');

  const navItem = document.querySelector(`[data-section="${name}"]`);
  if (navItem) navItem.classList.add('active');

  const [title, sub] = pageTitles[name] || [name, ''];
  document.getElementById('pageTitle').textContent = title;
  document.getElementById('pageSub').textContent = sub;

  if (name === 'overview') loadOverview();
  if (name === 'tasks') loadTasks();
  if (name === 'reminders') loadReminders();
  if (name === 'meals') loadMeals();
  if (name === 'safety') loadSafety();

  closeSidebar();
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').style.display = 'none';
}

function formatSectionBody(body) {
  const trimmed = String(body || '').trim();
  if (!trimmed) return '';

  const lines = trimmed.split('\n').map((line) => line.trim()).filter(Boolean);
  let html = '';
  let listItems = [];

  const renderInlineMarkdown = (value) => {
    let safe = escHtml(value);
    safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    return safe;
  };

  const flushList = () => {
    if (!listItems.length) return;
    html += `<ul>${listItems.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join('')}</ul>`;
    listItems = [];
  };

  lines.forEach((line) => {
    const bulletMatch = line.match(/^([-*]|\d+[.)])\s+(.+)$/);
    if (bulletMatch) {
      listItems.push(bulletMatch[2].trim());
      return;
    }
    flushList();
    html += `<p>${renderInlineMarkdown(line)}</p>`;
  });

  flushList();
  return html;
}

function formatSystematicOutput(text) {
  const normalized = String(text || '')
    .replace(/\r/g, '')
    .replace(/\*\*([^*]+)\*\*\s*:/g, '$1:')
    .trim();
  if (!normalized) return '';

  const lines = normalized.split('\n');
  const sections = [];
  let currentTitle = '';
  let currentLines = [];

  const pushSection = () => {
    if (!currentTitle && !currentLines.length) return;
    sections.push({
      title: currentTitle || 'Response',
      body: currentLines.join('\n').trim(),
    });
    currentTitle = '';
    currentLines = [];
  };

  lines.forEach((rawLine) => {
    const line = rawLine.trim();
    const markdownHeading = line.match(/^\*\*([^*]+)\*\*\s*$/);
    const colonHeading = line.match(/^([A-Z][A-Za-z ]{2,30}):\s*(.*)$/);

    if (markdownHeading) {
      pushSection();
      currentTitle = markdownHeading[1].trim();
      return;
    }

    if (colonHeading) {
      pushSection();
      currentTitle = colonHeading[1].trim();
      if (colonHeading[2]) currentLines.push(colonHeading[2].trim());
      return;
    }

    currentLines.push(rawLine);
  });

  pushSection();

  if (!sections.length) {
    return `<div class="systematic-body">${formatSectionBody(normalized)}</div>`;
  }

  const sectionHtml = sections.map((section) => {
    return `
      <div class="systematic-section">
        <div class="systematic-title">${escHtml(section.title)}</div>
        <div class="systematic-body">${formatSectionBody(section.body)}</div>
      </div>
    `;
  });

  return `<div class="systematic">${sectionHtml.join('')}</div>`;
}

function renderSystematicAdvice(elementId, text) {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.innerHTML = formatSystematicOutput(text);
}

function toSystematicText(title, value) {
  const trimmed = String(value || '').trim();
  if (!trimmed) return `${title}: No information available.`;
  const alreadyStructured =
    /^\*\*[^*]+\*\*/.test(trimmed) ||
    /^[A-Z][A-Za-z ]{2,30}:\s*/.test(trimmed);
  if (alreadyStructured) return trimmed;
  return `${title}: ${trimmed}`;
}

async function loadOverview() {
  try {
    const data = await apiFetch('/api/overview');
    document.getElementById('ovTaskCount').textContent = data.taskCount ?? '-';
    document.getElementById('ovRemCount').textContent = data.reminderCount ?? '-';
    document.getElementById('ovMealCount').textContent = data.mealCount ?? '-';
    document.getElementById('ovOpenTasks').textContent = `${data.openTasks ?? 0} open`;
    document.getElementById('ovUrgentRem').textContent = `${data.urgentReminders ?? 0} urgent`;
    renderSystematicAdvice('ovNextAction', toSystematicText('Next Action', data.nextAction || '-'));
    renderSystematicAdvice('ovSafetyTip', toSystematicText('Safety Note', data.safetyTip || '-'));
    document.getElementById('ovSafetyCount').textContent = '-';

    const safety = await apiFetch('/api/safety');
    document.getElementById('ovSafetyCount').textContent = safety.length ?? '-';
  } catch (e) {
    console.error('Overview error', e);
  }
}

function appendMsg(windowId, role, text) {
  const win = document.getElementById(windowId);
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  const isUser = role === 'user';
  const rendered = isUser ? escHtml(text).replace(/\n/g, '<br/>') : formatSystematicOutput(text);
  div.innerHTML = `
    <div class="msg-avatar">${isUser ? (currentUser?.avatar || 'U') : 'AI'}</div>
    <div class="msg-bubble">${rendered}</div>
  `;
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
  return div;
}

function appendTyping(windowId) {
  const win = document.getElementById(windowId);
  const div = document.createElement('div');
  div.className = 'msg ai';
  div.id = `typing-${windowId}`;
  div.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-bubble">
      <div class="typing-indicator"><span></span><span></span><span></span></div>
    </div>
  `;
  win.appendChild(div);
  win.scrollTop = win.scrollHeight;
}

function removeTyping(windowId) {
  const el = document.getElementById(`typing-${windowId}`);
  if (el) el.remove();
}

async function sendChat(windowId, message, sendBtnId) {
  const sendBtn = document.getElementById(sendBtnId);
  if (sendBtn) sendBtn.disabled = true;

  appendMsg(windowId, 'user', message);
  appendTyping(windowId);

  try {
    const data = await apiFetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
    removeTyping(windowId);
    appendMsg(windowId, 'ai', data.answer || data.error || 'No response.');
  } catch {
    removeTyping(windowId);
    appendMsg(windowId, 'ai', 'Could not reach MaaSathi. Check your Groq API key or local Ollama backup.');
  }

  if (sendBtn) sendBtn.disabled = false;
}

function setupChatForm(formId, inputId, windowId, sendBtnId) {
  const form = document.getElementById(formId);
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const input = document.getElementById(inputId);
    const msg = input.value.trim();
    if (!msg) return;
    input.value = '';
    await sendChat(windowId, msg, sendBtnId);
  });
}

async function loadTasks() {
  const list = document.getElementById('taskList');
  list.innerHTML = '<div class="empty-state"><div class="load-spinner" style="width:22px;height:22px;border-width:2px;margin:0 auto .5rem;"></div></div>';
  try {
    const tasks = await apiFetch('/api/tasks');
    renderTasks(tasks);
  } catch {
    list.innerHTML = empty('!', 'Could not load tasks.');
  }
}

function renderTasks(tasks) {
  const list = document.getElementById('taskList');
  if (!tasks.length) {
    list.innerHTML = empty('OK', 'No tasks yet. Add one above.');
    return;
  }
  list.innerHTML = tasks.map((t) => `
    <div class="list-item" id="task-${t.id}">
      <div class="item-content">
        <div class="item-title" style="${t.status === 'done' ? 'text-decoration:line-through;opacity:.5;' : ''}">${escHtml(t.title)}</div>
        <div class="item-meta">
          ${priorityBadge(t.priority)}
          <span class="badge badge-${t.status === 'done' ? 'done' : 'open'}">${t.status}</span>
          <span>${escHtml(t.assigned_to)}</span>
        </div>
      </div>
      ${t.status !== 'done' ? `<button class="complete-btn" onclick="completeTask(${t.id})">Done</button>` : ''}
      <button class="delete-btn" onclick="deleteTask(${t.id})">Delete</button>
    </div>
  `).join('');
}

async function deleteTask(id) {
  try {
    await apiFetch(`/api/tasks/${id}`, { method: 'DELETE' });
    showToast('Task deleted.', 'info');
    loadTasks();
  } catch {
    showToast('Could not delete task.', 'error');
  }
}

async function completeTask(id) {
  try {
    await apiFetch(`/api/tasks/${id}`, { method: 'PATCH', body: JSON.stringify({ status: 'done' }) });
    showToast('Task marked done.', 'success');
    loadTasks();
  } catch {
    showToast('Could not update task.', 'error');
  }
}

async function loadReminders() {
  const list = document.getElementById('reminderList');
  list.innerHTML = '<div class="empty-state"><div class="load-spinner" style="width:22px;height:22px;border-width:2px;margin:0 auto .5rem;"></div></div>';
  try {
    const reminders = await apiFetch('/api/reminders');
    renderReminders(reminders);
  } catch {
    list.innerHTML = empty('!', 'Could not load reminders.');
  }
}

function renderReminders(reminders) {
  const list = document.getElementById('reminderList');
  if (!reminders.length) {
    list.innerHTML = empty('Bell', 'No reminders yet. Add one above.');
    return;
  }
  list.innerHTML = reminders.map((r) => `
    <div class="list-item" id="rem-${r.id}">
      <div class="item-content">
        <div class="item-title">${escHtml(r.note)}</div>
        <div class="item-meta">
          ${priorityBadge(r.priority)}
          <span>Due: ${escHtml(r.due)}</span>
        </div>
      </div>
      <button class="delete-btn" onclick="deleteReminder(${r.id})">Delete</button>
    </div>
  `).join('');
}

async function deleteReminder(id) {
  try {
    await apiFetch(`/api/reminders/${id}`, { method: 'DELETE' });
    showToast('Reminder removed.', 'info');
    loadReminders();
  } catch {
    showToast('Could not delete reminder.', 'error');
  }
}

function getAudioContext() {
  if (!audioContext) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return null;
    audioContext = new AudioCtx();
  }
  return audioContext;
}

function playToneSequence(type, volumePercent) {
  const ctx = getAudioContext();
  const status = document.getElementById('soundStatus');
  if (!ctx) {
    if (status) status.textContent = 'Interactive audio is not supported in this browser.';
    return;
  }

  const volume = Math.max(0.01, Math.min(1, volumePercent / 100));
  const start = ctx.currentTime;
  const tones = type === 'alarm' ? [880, 740, 880] : [660, 880];
  const gap = type === 'alarm' ? 0.35 : 0.22;

  tones.forEach((frequency, index) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type === 'alarm' ? 'square' : 'sine';
    osc.frequency.setValueAtTime(frequency, start + (index * gap));
    gain.gain.setValueAtTime(0.0001, start + (index * gap));
    gain.gain.exponentialRampToValueAtTime(volume * (type === 'alarm' ? 0.22 : 0.12), start + (index * gap) + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + (index * gap) + (type === 'alarm' ? 0.25 : 0.16));
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(start + (index * gap));
    osc.stop(start + (index * gap) + (type === 'alarm' ? 0.28 : 0.18));
  });

  if (status) {
    status.textContent = `${type === 'alarm' ? 'Alarm' : 'Notification'} preview played at ${volumePercent}%.`;
  }
}

function setupSoundControls() {
  const alarmSlider = document.getElementById('alarmVolume');
  const notificationSlider = document.getElementById('notificationVolume');
  const alarmValue = document.getElementById('alarmVolumeValue');
  const notificationValue = document.getElementById('notificationVolumeValue');
  const testAlarmBtn = document.getElementById('testAlarmBtn');
  const testNotificationBtn = document.getElementById('testNotificationBtn');
  if (!alarmSlider || !notificationSlider) return;

  const prefs = getSoundPrefs();
  const sync = () => {
    alarmSlider.value = prefs.alarm;
    notificationSlider.value = prefs.notification;
    alarmValue.textContent = `${prefs.alarm}%`;
    notificationValue.textContent = `${prefs.notification}%`;
  };

  alarmSlider.addEventListener('input', () => {
    prefs.alarm = Number(alarmSlider.value);
    alarmValue.textContent = `${prefs.alarm}%`;
    saveSoundPrefs(prefs);
  });

  notificationSlider.addEventListener('input', () => {
    prefs.notification = Number(notificationSlider.value);
    notificationValue.textContent = `${prefs.notification}%`;
    saveSoundPrefs(prefs);
  });

  testAlarmBtn.addEventListener('click', async () => {
    const ctx = getAudioContext();
    if (ctx && ctx.state === 'suspended') await ctx.resume();
    playToneSequence('alarm', prefs.alarm);
  });

  testNotificationBtn.addEventListener('click', async () => {
    const ctx = getAudioContext();
    if (ctx && ctx.state === 'suspended') await ctx.resume();
    playToneSequence('notification', prefs.notification);
  });

  sync();
}

async function loadMeals() {
  const list = document.getElementById('mealList');
  list.innerHTML = '<div class="empty-state"><div class="load-spinner" style="width:22px;height:22px;border-width:2px;margin:0 auto .5rem;"></div></div>';
  try {
    const meals = await apiFetch('/api/meals');
    renderMeals(meals);
  } catch {
    list.innerHTML = empty('!', 'Could not load meals.');
  }
}

function renderMeals(meals) {
  const list = document.getElementById('mealList');
  if (!meals.length) {
    list.innerHTML = empty('Meal', 'No saved meals yet.');
    return;
  }
  list.innerHTML = meals.map((m) => `
    <div class="list-item">
      <div class="item-content">
        <div class="item-title">${escHtml(m.description)}</div>
        <div class="item-meta">${(m.tags || []).map((tag) => `<span class="badge badge-low">${escHtml(tag)}</span>`).join('')}</div>
      </div>
    </div>
  `).join('');
}

async function loadSafety() {
  const log = document.getElementById('safetyLog');
  log.innerHTML = '<div class="empty-state"><div class="load-spinner" style="width:22px;height:22px;border-width:2px;margin:0 auto .5rem;"></div></div>';
  try {
    const logs = await apiFetch('/api/safety');
    if (!logs.length) {
      log.innerHTML = empty('Shield', 'No safety logs yet.');
      return;
    }
    log.innerHTML = logs.map((l) => `
      <div class="safety-item">
        <div>${escHtml(l.note)}</div>
        <div class="safety-time">Checked: ${escHtml(l.last_checked)}</div>
      </div>
    `).join('');
  } catch {
    log.innerHTML = empty('!', 'Could not load safety logs.');
  }
}

async function triggerSOS(message = 'SOS - need immediate safety help') {
  const sosBtn = document.getElementById('sosBtn');
  const safetyBtn = document.getElementById('safetySOSBtn');
  if (sosBtn) sosBtn.disabled = true;
  if (safetyBtn) safetyBtn.disabled = true;

  showToast('SOS sent. Generating AI guidance...', 'error');

  try {
    const data = await apiFetch('/api/safety/alert', {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
    const txt = data.alert || 'Stay safe. Emergency services: 112/100.';
    const resBox = document.getElementById('sosResult');
    const resTxt = document.getElementById('sosResultText');
    if (resBox && resTxt) {
      resBox.style.display = 'block';
      resTxt.innerHTML = formatSystematicOutput(txt);
    }
    showToast('AI safety guidance ready.', 'success');
    loadSafety();
  } catch {
    showToast('Could not reach AI. Call emergency services: 112.', 'error');
  }

  if (sosBtn) sosBtn.disabled = false;
  if (safetyBtn) safetyBtn.disabled = false;
}

async function checkAIStatus() {
  try {
    const data = await apiFetch('/api/ai/status');
    const dot = document.getElementById('statusDot');
    const txt = document.getElementById('statusText');

    if (data.provider === 'groq' && data.primary?.ready) {
      dot.className = 'status-dot online';
      txt.textContent = `Groq · ${data.primary.active_model || 'Ready'}`;
    } else if (data.provider === 'ollama' && data.backup?.ready) {
      dot.className = 'status-dot online';
      txt.textContent = `Ollama backup · ${data.backup.active_model || 'Ready'}`;
    } else if (data.primary?.configured) {
      dot.className = 'status-dot offline';
      txt.textContent = 'Groq configured · waiting';
    } else {
      dot.className = 'status-dot offline';
      txt.textContent = 'AI unavailable';
    }
  } catch {
    document.getElementById('statusDot').className = 'status-dot offline';
    document.getElementById('statusText').textContent = 'AI offline';
  }
}

async function createDayPlan() {
  const btn = document.getElementById('dayPlanBtn');
  const box = document.getElementById('dayPlanResult');
  const txt = document.getElementById('dayPlanText');
  const energy_level = document.getElementById('energyLevel').value;
  const available_minutes = document.getElementById('availableMinutes').value || '90';
  const focus_area = document.getElementById('focusArea').value.trim() || 'home rhythm';

  btn.disabled = true;
  btn.textContent = 'Creating...';
  box.style.display = 'block';
  txt.innerHTML = 'Building a realistic plan for today...';
  txt.classList.add('loading-pulse');

  try {
    const data = await apiFetch('/api/assist/day_plan', {
      method: 'POST',
      body: JSON.stringify({ energy_level, available_minutes, focus_area }),
    });
    renderSystematicAdvice('dayPlanText', data.plan || 'No plan generated.');
  } catch {
    txt.textContent = 'Could not create plan. Check your Groq API key or Ollama backup.';
  }

  txt.classList.remove('loading-pulse');
  btn.disabled = false;
  btn.textContent = 'Create Plan';
}

function escHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

window.addEventListener('DOMContentLoaded', async () => {
  const ok = await checkAuth();
  if (!ok) return;

  document.getElementById('loadingScreen').style.display = 'none';
  document.getElementById('sidebarName').textContent = currentUser.name;
  document.getElementById('sidebarEmail').textContent = currentUser.email;
  document.getElementById('sidebarAvatar').textContent = currentUser.avatar || currentUser.name[0].toUpperCase();

  checkAIStatus();
  setInterval(checkAIStatus, 30000);

  document.querySelectorAll('.nav-item').forEach((item) => {
    item.addEventListener('click', () => switchSection(item.dataset.section));
  });

  document.getElementById('hamburgerDash').addEventListener('click', () => {
    document.getElementById('sidebar').classList.add('open');
    document.getElementById('sidebarOverlay').style.display = 'block';
  });

  document.getElementById('logoutBtn').addEventListener('click', async () => {
    await apiFetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/';
  });

  document.getElementById('sosBtn').addEventListener('click', () => triggerSOS());
  document.getElementById('safetySOSBtn').addEventListener('click', () => triggerSOS());

  setupChatForm('ovChatForm', 'ovChatInput', 'ovChatWindow', 'ovChatSend');
  setupChatForm('mainChatForm', 'mainChatInput', 'mainChatWindow', 'mainChatSend');
  setupSoundControls();

  appendMsg('ovChatWindow', 'ai', `Hello ${currentUser.name.split(' ')[0]}! Summary: I can help with routines, tasks, reminders, and family planning. Next Step: Ask for a day plan, meal plan, or workload balance.`);
  appendMsg('mainChatWindow', 'ai', `Hello ${currentUser.name.split(' ')[0]}! Summary: I am running on Groq first with Ollama backup and full RAG memory. Next Step: Ask me for a structured plan and I will answer systematically.`);

  document.getElementById('taskForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('taskTitle').value.trim();
    const priority = document.getElementById('taskPriority').value;
    const assigned = document.getElementById('taskAssigned').value;
    if (!title) return;
    document.getElementById('taskTitle').value = '';
    try {
      await apiFetch('/api/tasks', { method: 'POST', body: JSON.stringify({ title, priority, assigned_to: assigned }) });
      showToast('Task added.', 'success');
      loadTasks();
    } catch {
      showToast('Could not add task.', 'error');
    }
  });

  document.getElementById('balanceBtn').addEventListener('click', async () => {
    const btn = document.getElementById('balanceBtn');
    btn.disabled = true;
    btn.textContent = 'Thinking...';
    const box = document.getElementById('balanceAdvice');
    const res = document.getElementById('balanceResult');
    box.style.display = 'block';
    res.textContent = 'Generating AI workload plan...';
    res.classList.add('loading-pulse');
    try {
      const data = await apiFetch('/api/assist/task_balance', { method: 'POST' });
      renderSystematicAdvice('balanceResult', data.advice || 'No advice available.');
    } catch {
      res.textContent = 'Could not reach AI. Check your Groq API key or Ollama backup.';
    }
    res.classList.remove('loading-pulse');
    btn.disabled = false;
    btn.textContent = 'AI Balance';
  });

  document.getElementById('reminderForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const note = document.getElementById('reminderNote').value.trim();
    const due = document.getElementById('reminderDue').value.trim() || 'today';
    if (!note) return;
    document.getElementById('reminderNote').value = '';
    document.getElementById('reminderDue').value = '';
    try {
      await apiFetch('/api/reminders', { method: 'POST', body: JSON.stringify({ note, due }) });
      showToast('Reminder added.', 'success');
      loadReminders();
    } catch {
      showToast('Could not add reminder.', 'error');
    }
  });

  document.getElementById('mealPlanForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const ingredients = document.getElementById('ingredientsInput').value.trim();
    if (!ingredients) return;
    const btn = document.getElementById('planBtn');
    btn.disabled = true;
    btn.textContent = 'Planning...';
    const box = document.getElementById('mealPlanResult');
    const txt = document.getElementById('mealPlanText');
    box.style.display = 'block';
    txt.textContent = 'Generating meal plan...';
    txt.classList.add('loading-pulse');
    try {
      const data = await apiFetch('/api/assist/meal_planner', {
        method: 'POST',
        body: JSON.stringify({ ingredients }),
      });
      renderSystematicAdvice('mealPlanText', data.plan || data.error || 'No plan generated.');
    } catch {
      txt.textContent = 'Could not reach AI. Check your Groq API key or Ollama backup.';
    }
    txt.classList.remove('loading-pulse');
    btn.disabled = false;
    btn.textContent = 'Generate Plan';
  });

  document.getElementById('dayPlanForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    await createDayPlan();
  });

  document.getElementById('mealAddForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const description = document.getElementById('mealDescription').value.trim();
    if (!description) return;
    document.getElementById('mealDescription').value = '';
    try {
      await apiFetch('/api/meals', { method: 'POST', body: JSON.stringify({ description }) });
      showToast('Meal saved.', 'success');
      loadMeals();
    } catch {
      showToast('Could not save meal.', 'error');
    }
  });

  loadOverview();
});
