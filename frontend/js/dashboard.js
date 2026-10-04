/**
 * SmartFarm - Dashboard JS
 * Loads all dashboard sections from the API.
 */

// Auth guard
if (!requireAuth()) { throw new Error("Redirecting to onboarding"); }

const farmId = State.farmId;
const userId = State.userId;

// Conversation history for quick AI
let quickAIHistory = [];

// ── Init ──
document.addEventListener('DOMContentLoaded', async () => {
  // Set user info in sidebar
  document.getElementById('sb-farm-name').textContent = State.farmName || 'My Farm';
  document.getElementById('sb-user-name').textContent = State.userName || 'Farmer';

  // Header date
  const now = new Date();
  document.getElementById('header-date').textContent =
    now.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

  await refreshAll();
});

async function refreshAll() {
  // Run all sections in parallel (failures don't block others)
  await Promise.allSettled([
    loadStats(),
    loadWeather(),
    loadIrrigation(),
    loadForecast(),
    loadActionPlan(),
    loadRisks(),
    loadCrops(),
    loadTasks(),
    loadAnalytics(),
    loadMarketPreview(),
    loadRecommendations(),
  ]);
}

// ── Stats ──
async function loadStats() {
  try {
    const analytics = await API.getFarmAnalytics(farmId);
    document.getElementById('stats-row').innerHTML = `
      <div class="stat-card" style="--card-accent:var(--color-primary)">
        <span class="stat-icon">🌱</span>
        <div class="stat-value">${analytics.active_crops}</div>
        <div class="stat-label">Active Crops</div>
      </div>
      <div class="stat-card" style="--card-accent:var(--color-blue)">
        <span class="stat-icon">💧</span>
        <div class="stat-value">${analytics.irrigation_events_last_30_days}</div>
        <div class="stat-label">Irrigations (30d)</div>
      </div>
      <div class="stat-card" style="--card-accent:var(--color-amber)">
        <span class="stat-icon">📋</span>
        <div class="stat-value">${analytics.pending_tasks}</div>
        <div class="stat-label">Pending Tasks</div>
        ${analytics.overdue_tasks > 0 ? `<div class="stat-change down">⚠️ ${analytics.overdue_tasks} overdue</div>` : ''}
      </div>
      <div class="stat-card" style="--card-accent:var(--color-sky)">
        <span class="stat-icon">🌧️</span>
        <div class="stat-value">${analytics.total_rainfall_mm.toFixed(0)}<span style="font-size:0.9rem;font-weight:400">mm</span></div>
        <div class="stat-label">Rainfall (30d)</div>
      </div>
    `;
  } catch (e) {
    document.getElementById('stats-row').innerHTML = `<div class="alert alert-warning" style="grid-column:1/-1"><span class="alert-icon">⚠️</span><div>Analytics unavailable: ${e.message}</div></div>`;
  }
}

// ── Weather ──
async function loadWeather() {
  try {
    const w = await API.getWeather(farmId);
    const icon = getWeatherIcon(w.description);
    document.getElementById('weather-section').innerHTML = `
      <div class="weather-widget">
        <div class="flex justify-between items-center mb-2">
          <div>
            <div class="text-xs text-muted">${w.location}</div>
            <div style="font-size:0.7rem;color:var(--color-text-muted)">${new Date(w.recorded_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</div>
          </div>
          <div style="font-size:2.5rem">${icon}</div>
        </div>
        <div class="flex items-end gap-3">
          <div class="weather-temp">${w.temperature_c}<sup>°C</sup></div>
          <div>
            <div class="weather-desc">${w.description}</div>
            <div style="font-size:0.72rem;color:var(--color-text-muted)">Feels like ${w.feels_like_c}°C</div>
          </div>
        </div>
        <div class="weather-stats">
          <div class="weather-stat">
            <div class="ws-value">💧 ${w.humidity_percent}%</div>
            <div class="ws-label">Humidity</div>
          </div>
          <div class="weather-stat">
            <div class="ws-value">🌧️ ${w.rainfall_mm}mm</div>
            <div class="ws-label">Rainfall</div>
          </div>
          <div class="weather-stat">
            <div class="ws-value">💨 ${w.wind_speed_kmh}km/h</div>
            <div class="ws-label">Wind ${w.wind_direction}</div>
          </div>
          <div class="weather-stat">
            <div class="ws-value">🌅 ${w.sunrise}</div>
            <div class="ws-label">Sunrise</div>
          </div>
          <div class="weather-stat">
            <div class="ws-value">🌇 ${w.sunset}</div>
            <div class="ws-label">Sunset</div>
          </div>
          <div class="weather-stat">
            <div class="ws-value">☁️ ${w.cloud_cover_percent}%</div>
            <div class="ws-label">Cloud Cover</div>
          </div>
        </div>
      </div>
    `;
  } catch (e) {
    document.getElementById('weather-section').innerHTML = `
      <div class="card" style="height:100%">
        <div class="empty-state">
          <div class="empty-icon">🌤️</div>
          <h3>Weather Unavailable</h3>
          <p>${e.message}</p>
          <p class="mt-2 text-xs">Check WEATHER_API_KEY in .env</p>
        </div>
      </div>`;
  }
}

// ── Irrigation ──
async function loadIrrigation() {
  try {
    const rec = await API.getIrrigationRec(farmId);
    const needed = rec.irrigation_required;
    document.getElementById('irrigation-section').innerHTML = `
      <div class="irrigation-card">
        <div class="text-xs text-muted mb-2">IRRIGATION RECOMMENDATION</div>
        <div style="font-size:2.5rem;margin-bottom:4px">${needed ? '💧' : '✅'}</div>
        <div class="font-bold" style="font-size:1.1rem;color:${needed ? 'var(--color-primary)' : 'var(--color-text-dim)'}">
          ${needed ? 'Irrigation Required' : 'No Irrigation Needed'}
        </div>
        ${needed ? `
          <div class="irrigation-amount">${rec.estimated_requirement_mm?.toFixed(0) || '—'}<sup>mm</sup></div>
          <div class="text-xs text-muted">Recommended time: ${rec.recommended_time}</div>
          ${rec.duration_hours ? `<div class="text-xs text-muted">Duration: ~${rec.duration_hours}h</div>` : ''}
        ` : `
          <div class="text-sm text-dim mt-2">${rec.skip_reason || 'Soil moisture is adequate.'}</div>
        `}
        <div class="alert ${needed ? 'alert-info' : 'alert-success'} mt-3" style="text-align:left">
          <span class="alert-icon">${needed ? '📌' : '✅'}</span>
          <div style="font-size:0.78rem">${rec.reason}</div>
        </div>
        <div class="mt-3 flex gap-2 justify-center">
          <span class="badge ${rec.confidence === 'high' ? 'badge-green' : rec.confidence === 'medium' ? 'badge-amber' : 'badge-blue'}">
            ${rec.confidence?.toUpperCase() || 'MEDIUM'} confidence
          </span>
        </div>
        ${needed ? `
          <button class="btn btn-primary mt-3" style="width:100%" onclick="logIrrigation(${rec.estimated_requirement_mm?.toFixed(0) || 0})">
            💧 Log Irrigation
          </button>
        ` : ''}
      </div>
    `;
  } catch (e) {
    document.getElementById('irrigation-section').innerHTML = `
      <div class="card" style="height:100%">
        <div class="empty-state">
          <div class="empty-icon">💧</div>
          <h3>Irrigation Data Unavailable</h3>
          <p>${e.message}</p>
        </div>
      </div>`;
  }
}

// ── Forecast ──
async function loadForecast() {
  try {
    const forecast = await API.getForecast(farmId, 5);
    document.getElementById('forecast-location').textContent = forecast.location;
    const strip = forecast.days.map(d => `
      <div class="forecast-day">
        <div class="fd-day">${d.day_of_week.slice(0, 3)}</div>
        <div style="font-size:0.75rem;color:var(--color-text-muted)">${d.date.slice(5)}</div>
        <div class="fd-icon">${getWeatherIcon(d.description)}</div>
        <div class="fd-temp">${d.temp_max_c}° / ${d.temp_min_c}°</div>
        <div class="fd-rain">💧 ${d.rainfall_mm}mm</div>
        <div style="font-size:0.65rem;color:var(--color-text-muted)">${d.rain_probability}% rain</div>
      </div>
    `).join('');
    document.getElementById('forecast-strip').innerHTML = strip;
  } catch (e) {
    document.getElementById('forecast-strip').innerHTML = `<p class="text-muted text-sm">${e.message}</p>`;
  }
}

// ── Action Plan ──
async function loadActionPlan() {
  try {
    const plan = await API.getActionPlan(farmId);
    const today = plan.days[0];
    if (!today) {
      document.getElementById('action-plan-section').innerHTML = '<p class="text-muted">No plan available</p>';
      return;
    }

    const actionsHtml = today.actions.slice(0, 6).map(a => `
      <div class="action-item">
        <span class="action-icon">${a.icon}</span>
        <div class="action-content">
          <div class="action-title">${a.title}</div>
          ${a.description ? `<div class="action-desc">${a.description}</div>` : ''}
        </div>
        <div class="action-priority">
          ${a.priority === 1 ? '<span class="badge badge-red">HIGH</span>' :
            a.priority === 2 ? '<span class="badge badge-amber">MED</span>' :
            '<span class="badge badge-green">LOW</span>'}
        </div>
      </div>
    `).join('');

    document.getElementById('action-plan-section').innerHTML = `
      <div class="action-plan-day">
        <div class="action-day-header">
          <span class="action-day-label today">🌅 TODAY</span>
          <span class="action-day-weather">${today.weather_summary}</span>
        </div>
        ${actionsHtml || '<div class="action-item"><span class="action-icon">✅</span><div class="action-content"><div class="action-title">No urgent actions for today</div></div></div>'}
      </div>
      <div class="mt-2">
        <a href="dashboard.html#full-plan" class="text-sm text-primary">View full 7-day plan →</a>
      </div>
    `;
  } catch (e) {
    document.getElementById('action-plan-section').innerHTML = `<p class="text-muted text-sm">${e.message}</p>`;
  }
}

// ── Risks ──
async function loadRisks() {
  try {
    const risks = await API.getRisks(farmId);
    const indicator = document.getElementById('risk-indicator');
    indicator.className = `badge risk-${risks.overall_risk_level}`;
    indicator.textContent = `Risk: ${risks.overall_risk_level.toUpperCase()}`;

    if (risks.risks.length === 0) {
      document.getElementById('risks-section').innerHTML = `
        <div class="alert alert-success">
          <span class="alert-icon">✅</span>
          <div class="alert-content">
            <div class="alert-title">No active risks detected</div>
            Weather and crop conditions look stable.
          </div>
        </div>`;
      return;
    }

    const html = risks.risks.map(r => `
      <div class="risk-card risk-${r.level}">
        <div class="risk-icon">${r.level === 'critical' ? '🔴' : r.level === 'high' ? '🟠' : r.level === 'medium' ? '🟡' : '🔵'}</div>
        <div class="risk-content">
          <div class="risk-title">${r.title}</div>
          <div class="risk-desc">${r.description}</div>
          <div class="risk-action">💡 ${r.recommended_action}</div>
        </div>
      </div>
    `).join('');
    document.getElementById('risks-section').innerHTML = html;
  } catch (e) {
    document.getElementById('risks-section').innerHTML = `<p class="text-muted text-sm">${e.message}</p>`;
  }
}

// ── Crops ──
async function loadCrops() {
  try {
    const crops = await API.getFarmCrops(farmId);
    const active = crops.filter(c => c.status === 'active');

    if (active.length === 0) {
      document.getElementById('crops-section').innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🌱</div>
          <h3>No active crops</h3>
          <p><a href="crops.html" class="text-primary">Add a crop →</a></p>
        </div>`;
      return;
    }

    const COLORS = ['var(--color-primary)', 'var(--color-blue)', 'var(--color-amber)', 'var(--color-purple)'];
    document.getElementById('crops-section').innerHTML = active.slice(0, 4).map((c, i) => `
      <div class="crop-card mb-2" style="--crop-color:${COLORS[i % COLORS.length]}">
        <div class="flex justify-between items-start">
          <div>
            <div class="crop-name">${c.crop_name}</div>
            ${c.variety ? `<div class="crop-variety">${c.variety}</div>` : ''}
          </div>
          <span class="badge badge-green">${getStageName(c.current_stage)}</span>
        </div>
        <div class="crop-meta">
          <div class="crop-meta-item">📐 ${c.area_acres} ac</div>
          ${c.sowing_date ? `<div class="crop-meta-item">🗓️ Sown: ${formatDateShort(c.sowing_date)}</div>` : ''}
          ${c.expected_harvest_date ? `<div class="crop-meta-item">🚜 Harvest: ${formatDateShort(c.expected_harvest_date)}</div>` : ''}
          <div class="crop-meta-item">📍 ${c.field_name}</div>
        </div>
      </div>
    `).join('');
  } catch (e) {
    document.getElementById('crops-section').innerHTML = `<p class="text-muted text-sm">${e.message}</p>`;
  }
}

// ── Tasks ──
async function loadTasks() {
  try {
    const tasks = await API.getFarmTasks(farmId, 'pending');
    document.getElementById('task-count').textContent = `${tasks.length} pending`;
    if (tasks.length === 0) {
      document.getElementById('tasks-section').innerHTML = `<div class="empty-state" style="padding:24px"><div class="empty-icon">✅</div><p>All tasks done!</p></div>`;
      return;
    }
    document.getElementById('tasks-section').innerHTML = `
      <div class="card" style="padding:0;overflow:hidden">
        ${tasks.slice(0, 5).map(t => `
          <div class="action-item" style="padding:10px 16px">
            <span class="action-icon">${getTaskIcon(t.task_type)}</span>
            <div class="action-content">
              <div class="action-title" style="font-size:0.82rem">${t.title}</div>
              ${t.due_date ? `<div class="action-desc">Due: ${formatDateShort(t.due_date)}</div>` : ''}
            </div>
            <button class="btn btn-ghost btn-sm" onclick="doneTask(${t.id}, this)" title="Mark complete">✓</button>
          </div>
        `).join('')}
      </div>`;
  } catch (e) {
    document.getElementById('tasks-section').innerHTML = `<p class="text-muted text-sm">${e.message}</p>`;
  }
}

// ── Analytics ──
async function loadAnalytics() {
  try {
    const a = await API.getFarmAnalytics(farmId);
    const waterUtil = a.estimated_water_used_mm > 0
      ? Math.min(100, (a.estimated_water_used_mm / (a.total_rainfall_mm + a.estimated_water_used_mm)) * 100)
      : 0;

    document.getElementById('analytics-section').innerHTML = `
      <div class="card">
        <div class="card-header">
          <div class="card-title"><span class="card-icon">📊</span> Farm Analytics (30 days)</div>
        </div>
        <div class="flex flex-col gap-3">
          <div>
            <div class="flex justify-between text-xs text-muted mb-1">
              <span>💧 Irrigation Water Used</span>
              <span>${a.estimated_water_used_mm.toFixed(0)}mm (estimated)</span>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width:${Math.min(100, waterUtil)}%"></div></div>
          </div>
          <div>
            <div class="flex justify-between text-xs text-muted mb-1">
              <span>🌧️ Rainfall Received</span>
              <span>${a.total_rainfall_mm.toFixed(0)}mm</span>
            </div>
            <div class="progress-bar"><div class="progress-fill" style="width:${Math.min(100, a.total_rainfall_mm / 3)}%;background:linear-gradient(90deg,#60a5fa,#38bdf8)"></div></div>
          </div>
          <div class="grid-2 mt-2">
            <div class="stat-card" style="padding:12px;--card-accent:var(--color-amber)">
              <div class="stat-value" style="font-size:1.4rem">${a.irrigation_events_last_30_days}</div>
              <div class="stat-label">Irrigation Events</div>
            </div>
            <div class="stat-card" style="padding:12px;--card-accent:var(--color-red)">
              <div class="stat-value" style="font-size:1.4rem">${a.overdue_tasks}</div>
              <div class="stat-label">Overdue Tasks</div>
            </div>
          </div>
        </div>
      </div>`;
  } catch (e) {
    document.getElementById('analytics-section').innerHTML = `<p class="text-muted text-sm">${e.message}</p>`;
  }
}

// ── Market Preview ──
async function loadMarketPreview() {
  try {
    const data = await API.getMandiPrices(farmId);
    if (!data.prices || data.prices.length === 0) {
      document.getElementById('market-section').innerHTML = `
        <div class="card">
          <div class="card-header"><div class="card-title"><span class="card-icon">💰</span> Mandi Prices</div></div>
          <p class="text-muted text-sm">No active crops to check prices for.</p>
        </div>`;
      return;
    }
    const rows = data.prices.slice(0, 4).map(p => `
      <div class="flex justify-between items-center" style="padding:8px 0;border-bottom:1px solid var(--color-border)">
        <span class="font-semibold" style="font-size:0.85rem">${p.crop_name}</span>
        <div class="text-right">
          ${p.available && p.price_per_quintal
            ? `<div class="font-bold text-primary">₹${p.price_per_quintal.toLocaleString()}</div><div class="text-xs text-muted">per ${p.unit}</div>`
            : `<div class="text-xs text-muted">Check agmarknet.gov.in</div>`}
        </div>
      </div>
    `).join('');
    document.getElementById('market-section').innerHTML = `
      <div class="card">
        <div class="card-header">
          <div class="card-title"><span class="card-icon">💰</span> Mandi Prices (MSP)</div>
          <span class="text-xs text-muted">Govt. reference</span>
        </div>
        ${rows}
        <p class="text-xs text-muted mt-2">MSP reference only. Check <a href="https://agmarknet.gov.in" target="_blank" class="text-primary">agmarknet.gov.in</a> for live prices.</p>
      </div>`;
  } catch (e) {
    document.getElementById('market-section').innerHTML = `<div class="card"><p class="text-muted text-sm">${e.message}</p></div>`;
  }
}

// ── Recommendations ──
async function loadRecommendations() {
  try {
    const data = await API.getCropRecommendations(farmId);
    const top = data.recommendations.filter(r => r.suitability !== 'not_suitable').slice(0, 4);
    document.getElementById('recommendations-section').innerHTML = `
      <div class="grid-auto">
        ${top.map(r => {
          const scoreClass = r.suitability_score >= 75 ? 'green' : r.suitability_score >= 55 ? 'blue' : 'amber';
          return `
            <div class="rec-card ${r.suitability}">
              <div class="flex gap-3 items-start">
                <div class="rec-score ${scoreClass}">${Math.round(r.suitability_score)}</div>
                <div>
                  <div class="font-bold">${r.crop_name}</div>
                  ${r.local_name ? `<div class="text-xs text-muted">${r.local_name}</div>` : ''}
                  ${getSuitabilityBadge(r.suitability)}
                </div>
              </div>
              <div class="rec-flags mt-2">
                <span class="rec-flag ${r.soil_match ? 'match' : 'no-match'}">
                  ${r.soil_match ? '✅' : '❌'} Soil
                </span>
                <span class="rec-flag ${r.temp_match ? 'match' : 'no-match'}">
                  ${r.temp_match ? '✅' : '❌'} Temp
                </span>
                <span class="rec-flag ${r.rainfall_match ? 'match' : 'no-match'}">
                  ${r.rainfall_match ? '✅' : '❌'} Rainfall
                </span>
              </div>
              ${r.sowing_window ? `<div class="text-xs text-muted mt-1">🗓️ Sow: ${r.sowing_window}</div>` : ''}
            </div>`;
        }).join('')}
      </div>
      <p class="text-xs text-muted mt-2">Season: ${data.season} | Month: ${data.current_month}</p>`;
  } catch (e) {
    document.getElementById('recommendations-section').innerHTML = `<p class="text-muted text-sm">${e.message}</p>`;
  }
}

// ── Quick AI ──
async function quickAsk() {
  const input = document.getElementById('quick-ai-input');
  const msg = input.value.trim();
  if (!msg) return;

  const btn = document.getElementById('quick-ai-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Asking...';

  const answerDiv = document.getElementById('quick-ai-answer');
  const textDiv = document.getElementById('quick-ai-text');
  answerDiv.classList.remove('hidden');
  textDiv.innerHTML = '<span class="loading-spinner"></span> Ask Shyam is thinking...';

  try {
    const result = await API.chatWithAI(userId, farmId, msg, quickAIHistory);
    textDiv.innerHTML = result.reply.replace(/\n/g, '<br>');

    // Update history
    quickAIHistory.push({ role: 'user', content: msg });
    quickAIHistory.push({ role: 'assistant', content: result.reply });
    if (quickAIHistory.length > 10) quickAIHistory = quickAIHistory.slice(-10);

    input.value = '';
  } catch (e) {
    textDiv.innerHTML = `⚠️ Ask Shyam unavailable: ${e.message}. Check GROQ_API_KEY.`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Ask 🤖';
  }
}

document.getElementById('quick-ai-input').addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); quickAsk(); }
});

// ── Market Modal ──
async function showMarketModal() {
  document.getElementById('market-modal').classList.remove('hidden');
  try {
    const data = await API.getMandiPrices(farmId);
    if (!data.prices || data.prices.length === 0) {
      document.getElementById('market-modal-body').innerHTML = '<p class="text-muted">No active crops on this farm.</p>';
      return;
    }
    document.getElementById('market-modal-body').innerHTML = `
      ${data.prices.map(p => `
        <div style="padding:14px 0;border-bottom:1px solid var(--color-border)">
          <div class="flex justify-between">
            <div class="font-bold">${p.crop_name}</div>
            ${p.available && p.price_per_quintal
              ? `<div class="font-bold text-primary" style="font-size:1.1rem">₹${p.price_per_quintal.toLocaleString()} / ${p.unit}</div>`
              : `<div class="text-muted text-sm">Data unavailable</div>`}
          </div>
          ${p.note ? `<div class="text-xs text-muted mt-1">${p.note}</div>` : ''}
        </div>
      `).join('')}
      <p class="text-xs text-muted mt-3">${data.disclaimer || ''}</p>
      <a href="https://agmarknet.gov.in" target="_blank" class="btn btn-secondary btn-sm mt-3">🔗 Check Live Prices on AgMarknet</a>
    `;
  } catch (e) {
    document.getElementById('market-modal-body').innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
}

// ── Telegram Modal ──
async function showTelegramModal() {
  document.getElementById('telegram-modal').classList.remove('hidden');
  try {
    const data = await API.linkTelegram(userId);
    document.getElementById('telegram-modal-body').innerHTML = `
      <div class="text-center mb-4">
        <div style="font-size:3rem;margin-bottom:8px">💬</div>
        <h3 class="font-bold mb-2">Connect Telegram for Reminders</h3>
      </div>
      <div class="alert alert-info">
        <span class="alert-icon">📋</span>
        <div class="alert-content">
          <div class="alert-title">Your Link Code</div>
          <div style="font-size:1.5rem;font-weight:800;color:var(--color-primary);letter-spacing:0.1em">${data.code}</div>
        </div>
      </div>
      
      <div class="mt-4 text-center">
        <a href="${data.deep_link}" target="_blank" class="btn btn-primary" style="display:inline-block; width:100%;">
          🚀 Open Telegram & Link
        </a>
      </div>

      <div class="mt-4" style="font-size:0.875rem;color:var(--color-text-dim)">
        <pre style="background:var(--color-surface-2);padding:12px;border-radius:8px;border:1px solid var(--color-border);white-space:pre-wrap">${data.instructions}</pre>
      </div>
      <div class="mt-3 text-xs text-muted">Code expires in ${data.expires_in_minutes} minutes. After linking, you'll receive reminders and can ask Ask Shyam from Telegram!</div>
    `;
  } catch (e) {
    document.getElementById('telegram-modal-body').innerHTML = `
      <div class="alert alert-warning">
        <span class="alert-icon">⚠️</span>
        <div>${e.message}</div>
      </div>
      <p class="text-xs text-muted mt-2">Add TELEGRAM_BOT_TOKEN to your .env file to enable Telegram.</p>`;
  }
}

function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// ── Actions ──
async function logIrrigation(amountMm) {
  const actualAmount = prompt(`How much water did you add? (Recommended: ${amountMm}mm)\n\nNote: 1mm ≈ 4,000 Liters per acre.`, amountMm);
  if (actualAmount === null) return; // User cancelled
  
  const parsedAmount = parseFloat(actualAmount);
  if (isNaN(parsedAmount) || parsedAmount < 0) {
      showToast("Please enter a valid positive number for water amount.", "error");
      return;
  }
  
  try {
    await API.logIrrigation(farmId, parsedAmount);
    showToast(`Irrigation of ${parsedAmount}mm logged successfully!`, 'success');
    await loadIrrigation();
    await loadStats();
  } catch (e) {
    showToast(`Failed to log irrigation: ${e.message}`, 'error');
  }
}

async function doneTask(taskId, btn) {
  try {
    await API.completeTask(taskId);
    btn.closest('.action-item').style.opacity = '0.4';
    btn.textContent = '✓ Done';
    btn.disabled = true;
    showToast('Task marked complete!', 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function getTaskIcon(type) {
  const icons = {
    irrigation: '💧', fertilization: '🧪', pest_control: '🐛',
    inspection: '🔍', harvesting: '🚜', land_prep: '🌱',
    sowing: '🌾', general: '📋'
  };
  return icons[type] || '📋';
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

function logout() {
  State.clear();
  window.location.href = 'index.html';
}

// Close modal on overlay click
document.querySelectorAll('.modal-overlay').forEach(el => {
  el.addEventListener('click', e => {
    if (e.target === el) el.classList.add('hidden');
  });
});
