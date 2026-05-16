// ── Library Management System — Live Update JS ──
const LMS = {
  POLL_MS: 15000,

  init() {
    this.setupFlashDismiss();
    this.setupSearchDebounce();
    this.startPolling();
    this.initCharts();
    this.initSidebar();
  },

  setupFlashDismiss() {
    document.querySelectorAll('.flash').forEach(el => {
      el.addEventListener('click', () => el.remove());
      setTimeout(() => { if (el.parentNode) el.remove(); }, 5000);
    });
  },

  setupSearchDebounce() {
    document.querySelectorAll('.live-search').forEach(input => {
      let timer;
      input.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          const form = input.closest('form');
          if (form) form.submit();
        }, 500);
      });
    });
  },

  startPolling() {
    if (!document.querySelector('[data-live-stats]')) return;
    const poll = async () => {
      try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();
        this.updateStatCards(data);
        this.updateActivityFeed();
      } catch(e) {}
    };
    setInterval(poll, this.POLL_MS);
  },

  updateStatCards(data) {
    const map = {
      'stat-total-books': data.total_books,
      'stat-available': data.available_books,
      'stat-members': data.total_members,
      'stat-active-issues': data.active_issues,
      'stat-overdue': data.overdue_count,
      'stat-fines': `₹${parseFloat(data.total_fines||0).toFixed(0)}`,
      'stat-today-issues': data.today_issues,
      'stat-today-returns': data.today_returns,
    };
    for (const [id, val] of Object.entries(map)) {
      const el = document.getElementById(id);
      if (el && el.textContent !== String(val)) {
        el.textContent = val;
        el.closest('.stat-card')?.classList.add('pulse');
        setTimeout(() => el.closest('.stat-card')?.classList.remove('pulse'), 800);
      }
    }
  },

  async updateActivityFeed() {
    const feed = document.getElementById('activity-feed');
    if (!feed) return;
    try {
      const res = await fetch('/api/activity?limit=10');
      const items = await res.json();
      feed.innerHTML = items.map(a => `
        <div class="activity-item">
          <div class="activity-dot"></div>
          <div style="flex:1">
            <div class="activity-text"><strong>${a.action}</strong> — ${a.description||''}</div>
            <div class="activity-time">${a.user_name||'System'} · ${this.timeAgo(a.created_at)}</div>
          </div>
        </div>`).join('');
    } catch(e) {}
  },

  timeAgo(iso) {
    if (!iso) return '';
    const diff = Date.now() - new Date(iso).getTime();
    const m = Math.floor(diff/60000);
    if (m < 1) return 'just now';
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m/60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h/24)}d ago`;
  },

  initCharts() {
    const chartEl = document.getElementById('trend-chart');
    if (!chartEl) return;
    try {
      const data = JSON.parse(chartEl.dataset.values || '[]');
      if (!data.length) return;
      const max = Math.max(...data.map(d => parseInt(d.cnt)||0), 1);
      const container = chartEl.querySelector('.chart-container');
      const labels = chartEl.querySelector('.chart-labels');
      if (!container) return;
      container.innerHTML = '';
      if (labels) labels.innerHTML = '';
      data.forEach(item => {
        const pct = Math.max(Math.round(((parseInt(item.cnt)||0)/max)*100), 3);
        const wrap = document.createElement('div');
        wrap.style.cssText = 'flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;height:100%';
        const bar = document.createElement('div');
        bar.className = 'chart-bar';
        bar.style.height = pct + '%';
        bar.title = `${item.month}: ${item.cnt}`;
        wrap.appendChild(bar);
        if (labels) {
          const lbl = document.createElement('div');
          lbl.className = 'chart-label';
          lbl.textContent = (item.month||'').split(' ')[0];
          wrap.appendChild(lbl);
        }
        container.appendChild(wrap);
      });
    } catch(e) {}
  },

  initSidebar() {
    const toggle = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (toggle && sidebar) {
      toggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    }
  },

  confirmDelete(msg) {
    return confirm(msg || 'Are you sure you want to delete this item? This cannot be undone.');
  }
};

document.addEventListener('DOMContentLoaded', () => LMS.init());
