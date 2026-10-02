/**
 * SmartFarm - Crops Page JS
 */

if (!requireAuth()) {}

const farmId = State.farmId;
document.getElementById('sb-farm-name').textContent = State.farmName;

let activeTab = 'active';

document.addEventListener('DOMContentLoaded', () => {
  loadActiveCrops();
});

function switchTab(tab) {
  activeTab = tab;
  ['active', 'recommendations', 'catalog'].forEach(t => {
    document.getElementById(`tab-${t}`).classList.toggle('active', t === tab);
    document.getElementById(`panel-${t}`).classList.toggle('hidden', t !== tab);
  });
  if (tab === 'recommendations' && !document.getElementById('rec-content').hasAttribute('data-loaded')) {
    loadRecommendations();
  }
  if (tab === 'catalog' && !document.getElementById('catalog-content').hasAttribute('data-loaded')) {
    loadCatalog();
  }
}

// ── Active Crops ──
async function loadActiveCrops() {
  try {
    const crops = await API.getFarmCrops(farmId);
    if (crops.length === 0) {
      document.getElementById('crops-grid').innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🌱</div>
          <h3>No crops yet</h3>
          <p>Add your first crop to get irrigation advice and crop calendars.</p>
          <button class="btn btn-primary mt-4" onclick="showAddCropModal()">+ Add First Crop</button>
        </div>`;
      return;
    }

    const COLORS = ['var(--color-primary)', 'var(--color-blue)', 'var(--color-amber)', 'var(--color-purple)', 'var(--color-sky)'];
    document.getElementById('crops-grid').innerHTML = `
      <div class="grid-auto">
        ${crops.map((c, i) => `
          <div class="crop-card" style="--crop-color:${COLORS[i % COLORS.length]}">
            <div class="flex justify-between items-start mb-2">
              <div>
                <div class="crop-name">${c.crop_name}</div>
                ${c.variety ? `<div class="crop-variety">${c.variety}</div>` : ''}
              </div>
              <div class="flex gap-1 flex-col items-end">
                <span class="badge ${c.status === 'active' ? 'badge-green' : 'badge-gray'}">${c.status}</span>
              </div>
            </div>
            <div class="badge badge-blue mb-2">${getStageIcon(c.current_stage)} ${getStageName(c.current_stage)}</div>
            <div class="crop-meta">
              <div class="crop-meta-item">📐 ${c.area_acres} acres</div>
              <div class="crop-meta-item">📍 ${c.field_name}</div>
              ${c.sowing_date ? `<div class="crop-meta-item">🗓️ ${formatDateShort(c.sowing_date)}</div>` : ''}
              ${c.expected_harvest_date ? `<div class="crop-meta-item">🚜 ${formatDateShort(c.expected_harvest_date)}</div>` : ''}
            </div>
            <div class="divider"></div>
            <div class="flex gap-2">
              ${c.sowing_date ? `<button class="btn btn-ghost btn-sm" onclick="showCalendar(${c.crop_id})">📅 Calendar</button>` : ''}
              <button class="btn btn-ghost btn-sm" onclick="markHarvested(${c.crop_id})">🚜 Harvested</button>
            </div>
          </div>
        `).join('')}
        <div class="crop-card" style="border-style:dashed;display:flex;align-items:center;justify-content:center;cursor:pointer;min-height:180px" onclick="showAddCropModal()">
          <div class="text-center text-muted">
            <div style="font-size:2rem;margin-bottom:8px">+</div>
            <div class="text-sm">Add New Crop</div>
          </div>
        </div>
      </div>`;
  } catch (e) {
    document.getElementById('crops-grid').innerHTML = `<div class="alert alert-danger"><span class="alert-icon">❌</span><div>${e.message}</div></div>`;
  }
}

// ── Calendar ──
async function showCalendar(cropId) {
  document.getElementById('calendar-modal').classList.remove('hidden');
  document.getElementById('calendar-modal-body').innerHTML = '<div class="loading-spinner"></div>';
  try {
    const cal = await API.getCropCalendar(cropId);
    const stagesHtml = cal.stages.map((s, i) => `
      <div class="calendar-stage">
        ${i < cal.stages.length - 1 ? `<div class="stage-line ${s.is_past ? 'past' : ''}"></div>` : ''}
        <div class="stage-indicator ${s.is_current ? 'current' : s.is_past ? 'past' : ''}">
          ${s.is_past ? '✓' : s.icon || getStageIcon(s.stage)}
        </div>
        <div class="stage-content">
          <div class="stage-name ${s.is_current ? 'text-primary' : ''}">${getStageName(s.stage)}</div>
          <div class="stage-dates">${formatDateShort(s.start_date)} — ${formatDateShort(s.end_date)}</div>
          ${s.is_current ? `<div class="stage-progress">📍 Day ${s.days_in_stage} of ${s.duration_days} (${s.days_remaining} days remaining)</div>` : ''}
        </div>
      </div>
    `).join('');

    document.getElementById('calendar-modal-body').innerHTML = `
      <div class="flex justify-between mb-4">
        <div>
          <div class="font-bold">${cal.crop_name}</div>
          <div class="text-sm text-muted">Sown: ${formatDate(cal.sowing_date)}</div>
        </div>
        <div class="text-right">
          <div class="text-xs text-muted">Expected Harvest</div>
          <div class="font-bold text-primary">${formatDate(cal.expected_harvest_date)}</div>
        </div>
      </div>
      <div class="calendar-stages">${stagesHtml}</div>
      ${cal.generated_tasks.length > 0 ? `
        <div class="divider"></div>
        <div class="section-title text-sm">📋 Upcoming Tasks</div>
        ${cal.generated_tasks.slice(0, 5).map(t => `
          <div class="action-item" style="padding:8px 0">
            <span class="action-icon">📌</span>
            <div class="action-content">
              <div class="action-title" style="font-size:0.82rem">${t.title}</div>
              <div class="action-desc">Due: ${formatDateShort(t.due_date)}</div>
            </div>
          </div>
        `).join('')}
      ` : ''}
    `;
  } catch (e) {
    document.getElementById('calendar-modal-body').innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
}

// ── Recommendations ──
async function loadRecommendations() {
  const el = document.getElementById('rec-content');
  el.setAttribute('data-loaded', '1');
  try {
    const data = await API.getCropRecommendations(farmId);
    el.innerHTML = `
      <div class="alert alert-info mb-4">
        <span class="alert-icon">📅</span>
        <div class="alert-content">
          <div class="alert-title">Season: ${data.season.charAt(0).toUpperCase() + data.season.slice(1)} (Month ${data.current_month})</div>
          Recommendations based on your farm's soil, location, and current season.
        </div>
      </div>
      <div class="grid-auto">
        ${data.recommendations.map(r => {
          const scoreClass = r.suitability_score >= 75 ? 'green' : r.suitability_score >= 55 ? 'blue' : r.suitability_score >= 30 ? 'amber' : 'red';
          return `
          <div class="rec-card ${r.suitability}">
            <div class="flex gap-3 items-start mb-2">
              <div class="rec-score ${scoreClass}">${Math.round(r.suitability_score)}</div>
              <div>
                <div class="font-bold">${r.crop_name}</div>
                ${r.local_name ? `<div class="text-xs text-muted">${r.local_name}</div>` : ''}
                ${getSuitabilityBadge(r.suitability)}
              </div>
            </div>
            <div class="rec-flags">
              <span class="rec-flag ${r.soil_match ? 'match' : 'no-match'}">${r.soil_match ? '✅' : '❌'} Soil</span>
              <span class="rec-flag ${r.temp_match ? 'match' : 'no-match'}">${r.temp_match ? '✅' : '❌'} Temp</span>
              <span class="rec-flag ${r.rainfall_match ? 'match' : 'no-match'}">${r.rainfall_match ? '✅' : '❌'} Water</span>
            </div>
            ${r.sowing_window ? `<div class="text-xs text-muted mt-2">🗓️ Sow: ${r.sowing_window}</div>` : ''}
            ${r.growth_duration_days ? `<div class="text-xs text-muted">⏱️ Duration: ${r.growth_duration_days} days</div>` : ''}
            <div class="mt-2">
              ${r.reasons.slice(0, 2).map(reason => `<div class="text-xs text-muted" style="margin-top:2px">• ${reason}</div>`).join('')}
            </div>
          </div>`;
        }).join('')}
      </div>`;
  } catch (e) {
    el.innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
}

// ── Catalog ──
async function loadCatalog() {
  const el = document.getElementById('catalog-content');
  el.setAttribute('data-loaded', '1');
  try {
    const catalog = await API.getCropCatalog();
    el.innerHTML = `
      <div class="grid-auto">
        ${catalog.map(c => `
          <div class="card">
            <div class="font-bold">${c.crop_name} ${c.local_name ? `<span class="text-muted text-xs">(${c.local_name})</span>` : ''}</div>
            <div class="mt-2 flex gap-1 flex-wrap">
              <span class="badge ${c.season === 'kharif' ? 'badge-green' : c.season === 'rabi' ? 'badge-blue' : c.season === 'zaid' ? 'badge-amber' : 'badge-purple'}">${c.season}</span>
            </div>
            <div class="mt-2" style="font-size:0.78rem;color:var(--color-text-dim);display:flex;flex-direction:column;gap:3px">
              <div>🌡️ ${c.temperature_min_c}–${c.temperature_max_c}°C</div>
              <div>🌧️ ${c.rainfall_requirement_mm}mm seasonal</div>
              <div>💧 ${c.water_requirement_mm_per_day}mm/day</div>
              <div>⏱️ ${c.growth_duration_days} days</div>
              ${c.sowing_window_start ? `<div>🗓️ Sow: ${c.sowing_window_start} to ${c.sowing_window_end}</div>` : ''}
            </div>
          </div>
        `).join('')}
      </div>`;
  } catch (e) {
    el.innerHTML = `<p class="text-muted">${e.message}</p>`;
  }
}

// ── Add Crop ──
function showAddCropModal() {
  document.getElementById('add-crop-modal').classList.remove('hidden');
}

async function saveCrop() {
  const cropName = document.getElementById('new-crop-name').value;
  if (!cropName) { showToast('Please select a crop', 'error'); return; }

  const area = parseFloat(document.getElementById('new-crop-area').value) || 1.0;
  const variety = document.getElementById('new-crop-variety').value.trim();
  const fieldName = document.getElementById('new-field-name').value.trim() || 'New Field';
  const sowingDate = document.getElementById('new-sowing-date').value;

  const btn = document.getElementById('btn-save-crop');
  btn.disabled = true;
  btn.textContent = '⏳ Saving...';

  try {
    const field = await API.createField(farmId, { name: fieldName, area_acres: area });
    await API.createCrop({
      field_id: field.id,
      crop_name: cropName,
      variety: variety || null,
      area_acres: area,
      sowing_date: sowingDate || null,
    });
    showToast('Crop added successfully!', 'success');
    closeModal('add-crop-modal');
    loadActiveCrops();
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Crop';
  }
}

async function markHarvested(cropId) {
  try {
    await API.updateCrop(cropId, { status: 'harvested' });
    showToast('Crop marked as harvested!', 'success');
    loadActiveCrops();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function closeModal(id) { document.getElementById(id).classList.add('hidden'); }
