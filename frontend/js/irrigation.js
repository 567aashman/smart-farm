/**
 * SmartFarm AI - Irrigation JS
 */

if (!requireAuth()) {}

const farmId = State.farmId;
document.getElementById('sb-farm-name').textContent = State.farmName;

document.addEventListener('DOMContentLoaded', () => {
  loadAll();
});

async function loadAll() {
  await Promise.allSettled([
    loadRecommendation(),
    loadWeather(),
    loadHistory(),
    loadMonsoon(),
  ]);
}

// ── Recommendation ──
async function loadRecommendation() {
  try {
    const rec = await API.getIrrigationRec(farmId);
    const needed = rec.irrigation_required;
    document.getElementById('irr-rec-section').innerHTML = `
      <div class="irrigation-card" style="height:100%;display:flex;flex-direction:column;justify-content:center">
        <div class="text-xs text-muted mb-2">IRRIGATION STATUS</div>
        <div style="font-size:3rem;margin-bottom:8px">${needed ? '💧' : '✅'}</div>
        <div class="font-bold" style="font-size:1.3rem;color:${needed ? 'var(--color-primary)' : 'var(--color-text-dim)'}">
          ${needed ? 'Irrigation Required' : 'No Irrigation Needed'}
        </div>
        ${needed ? `
          <div class="irrigation-amount" style="font-size:3.5rem">${rec.estimated_requirement_mm?.toFixed(0) || '—'}<sup>mm</sup></div>
          <div class="text-sm mt-2">Recommended time: <span class="text-primary">${rec.recommended_time}</span></div>
          ${rec.duration_hours ? `<div class="text-sm">Duration: ~${rec.duration_hours} hours</div>` : ''}
        ` : `
          <div class="text-sm mt-4 text-dim">${rec.skip_reason || 'Soil moisture is adequate.'}</div>
        `}
        <div class="alert ${needed ? 'alert-info' : 'alert-success'} mt-4" style="text-align:left">
          <span class="alert-icon">${needed ? '📌' : '✅'}</span>
          <div style="font-size:0.85rem">${rec.reason}</div>
        </div>
      </div>
    `;
  } catch (e) {
    document.getElementById('irr-rec-section').innerHTML = `
      <div class="card" style="height:100%">
        <div class="empty-state">
          <div class="empty-icon">💧</div>
          <h3>Data Unavailable</h3>
          <p>${e.message}</p>
        </div>
      </div>`;
  }
}

// ── Weather Context ──
async function loadWeather() {
  try {
    const w = await API.getWeather(farmId);
    const icon = getWeatherIcon(w.description);
    document.getElementById('irr-weather-section').innerHTML = `
      <div class="card" style="height:100%">
        <div class="card-header">
          <div class="card-title"><span class="card-icon">🌤️</span> Current Conditions</div>
        </div>
        <div class="flex items-center gap-4 mb-4">
          <div style="font-size:3.5rem">${icon}</div>
          <div>
            <div style="font-size:2rem;font-weight:700;line-height:1">${w.temperature_c}°C</div>
            <div class="text-muted text-sm mt-1">${w.description}</div>
          </div>
        </div>
        <div class="grid-2 gap-3 mt-4">
          <div style="background:var(--color-surface-2);padding:12px;border-radius:8px">
            <div class="text-xs text-muted mb-1">Humidity</div>
            <div class="font-bold text-blue">${w.humidity_percent}%</div>
          </div>
          <div style="background:var(--color-surface-2);padding:12px;border-radius:8px">
            <div class="text-xs text-muted mb-1">Rainfall</div>
            <div class="font-bold text-sky">${w.rainfall_mm} mm</div>
          </div>
          <div style="background:var(--color-surface-2);padding:12px;border-radius:8px">
            <div class="text-xs text-muted mb-1">Wind</div>
            <div class="font-bold">${w.wind_speed_kmh} km/h</div>
          </div>
          <div style="background:var(--color-surface-2);padding:12px;border-radius:8px">
            <div class="text-xs text-muted mb-1">Cloud Cover</div>
            <div class="font-bold">${w.cloud_cover_percent}%</div>
          </div>
        </div>
      </div>
    `;
  } catch (e) {
    document.getElementById('irr-weather-section').innerHTML = `
      <div class="card" style="height:100%"><p class="text-muted">${e.message}</p></div>
    `;
  }
}

// ── History ──
async function loadHistory() {
  try {
    const history = await API.getIrrigationHistory(farmId);
    if (history.length === 0) {
      document.getElementById('irr-history').innerHTML = `
        <div class="text-center p-4 text-muted">No irrigation records found.</div>
      `;
      return;
    }
    document.getElementById('irr-history').innerHTML = `
      <div style="overflow-x:auto">
        <table style="width:100%;text-align:left;border-collapse:collapse;font-size:0.875rem">
          <thead>
            <tr style="border-bottom:1px solid var(--color-border);color:var(--color-text-muted)">
              <th style="padding:10px">Date</th>
              <th style="padding:10px">Amount</th>
              <th style="padding:10px">Status</th>
            </tr>
          </thead>
          <tbody>
            ${history.map(r => `
              <tr style="border-bottom:1px solid var(--color-surface-2)">
                <td style="padding:10px">${formatDate(r.actual_date || r.scheduled_date)}</td>
                <td style="padding:10px;font-weight:600;color:var(--color-primary)">${r.amount_mm || '—'} mm</td>
                <td style="padding:10px">
                  ${r.completed ? '<span class="badge badge-green">Completed</span>' : 
                    r.skipped ? '<span class="badge badge-gray">Skipped</span>' : 
                    '<span class="badge badge-amber">Pending</span>'}
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch (e) {
    document.getElementById('irr-history').innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
}

// ── Monsoon Tracker ──
async function loadMonsoon() {
  try {
    const forecast = await API.getForecast(farmId, 5);
    const rainyDays = forecast.days.filter(d => d.rain_probability > 40 || d.rainfall_mm > 5);
    
    if (rainyDays.length > 0) {
      document.getElementById('monsoon-section').innerHTML = `
        <div class="alert alert-info mb-4">
          <span class="alert-icon">🌧️</span>
          <div class="alert-content">
            <div class="alert-title">Rain Expected</div>
            Rain is expected in the next 5 days. Adjust irrigation accordingly.
          </div>
        </div>
        <div class="forecast-strip">
          ${rainyDays.map(d => `
            <div class="forecast-day" style="border-color:var(--color-blue)">
              <div class="fd-day">${d.day_of_week}</div>
              <div class="fd-icon">🌧️</div>
              <div class="fd-rain">${d.rainfall_mm}mm</div>
              <div style="font-size:0.7rem;color:var(--color-blue)">${d.rain_probability}% chance</div>
            </div>
          `).join('')}
        </div>
      `;
    } else {
      document.getElementById('monsoon-section').innerHTML = `
        <div class="alert alert-warning mb-4">
          <span class="alert-icon">☀️</span>
          <div class="alert-content">
            <div class="alert-title">Dry Spell Expected</div>
            No significant rain expected in the next 5 days. Ensure adequate irrigation.
          </div>
        </div>
        <div class="forecast-strip">
          ${forecast.days.map(d => `
            <div class="forecast-day">
              <div class="fd-day">${d.day_of_week.slice(0,3)}</div>
              <div class="fd-icon">${getWeatherIcon(d.description)}</div>
              <div class="fd-rain text-muted">0mm</div>
            </div>
          `).join('')}
        </div>
      `;
    }
  } catch (e) {
    document.getElementById('monsoon-section').innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
}

// ── Actions ──
async function logManualIrrigation() {
  const amount = prompt("Enter approximate amount of water in mm (e.g., 20):", "20");
  if (amount !== null && !isNaN(parseFloat(amount))) {
    try {
      await API.logIrrigation(farmId, parseFloat(amount));
      showToast(`Logged ${amount}mm irrigation!`, 'success');
      loadAll();
    } catch (e) {
      showToast(`Failed to log: ${e.message}`, 'error');
    }
  }
}
