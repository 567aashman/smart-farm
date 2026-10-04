/**
 * SmartFarm - API Client
 * Central fetch wrapper for all backend calls.
 */

const API_BASE = '/api';

// ── Session state (stored in localStorage) ──
const State = {
  get userId() { return parseInt(localStorage.getItem('sf_user_id') || '0'); },
  get farmId() { return parseInt(localStorage.getItem('sf_farm_id') || '0'); },
  get userName() { return localStorage.getItem('sf_user_name') || ''; },
  get farmName() { return localStorage.getItem('sf_farm_name') || ''; },

  set(userId, farmId, userName, farmName) {
    localStorage.setItem('sf_user_id', userId);
    localStorage.setItem('sf_farm_id', farmId);
    localStorage.setItem('sf_user_name', userName);
    localStorage.setItem('sf_farm_name', farmName);
  },

  clear() {
    localStorage.removeItem('sf_user_id');
    localStorage.removeItem('sf_farm_id');
    localStorage.removeItem('sf_user_name');
    localStorage.removeItem('sf_farm_name');
  },

  isLoggedIn() { return this.userId > 0 && this.farmId > 0; }
};

// ── Core fetch wrapper ──
async function apiFetch(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const defaults = {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  };
  if (options.body && typeof options.body === 'object') {
    defaults.body = JSON.stringify(options.body);
  }

  try {
    const response = await fetch(url, defaults);
    const text = await response.text();
    let data;
    try { data = JSON.parse(text); } catch { data = { message: text }; }

    if (!response.ok) {
      // Handle deleted/stale session cleanly without infinite reload loops
      if (response.status === 404 && (path.includes('/users/') || path.includes('/farms/'))) {
        console.warn("User or Farm not found in DB. Clearing stale session...");
        State.clear();
        const currentPath = window.location.pathname;
        if (!currentPath.includes('onboarding.html') && !currentPath.includes('index.html') && currentPath !== '/') {
          window.location.href = 'onboarding.html';
        }
        throw new APIError('Farm profile not found. Please set up your farm.', 404, data);
      }
      const msg = data?.detail || data?.message || `HTTP ${response.status}`;
      throw new APIError(msg, response.status, data);
    }
    return data;
  } catch (err) {
    if (err instanceof APIError) throw err;
    throw new APIError(`Connection failed: ${err.message}`, 0);
  }
}

class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

// ── API Methods ──
const API = {
  // Health
  health: () => fetch('/health').then(r => r.json()),

  // Users
  createUser: (data) => apiFetch('/users/', { method: 'POST', body: data }),
  getUser: (id) => apiFetch(`/users/${id}`),
  updateUser: (id, data) => apiFetch(`/users/${id}`, { method: 'PUT', body: data }),
  getNotifications: (userId) => apiFetch(`/users/${userId}/notifications`),

  // Farms
  createFarm: (userId, data) => apiFetch(`/farms/?user_id=${userId}`, { method: 'POST', body: data }),
  getUserFarms: (userId) => apiFetch(`/farms/user/${userId}`),
  getFarm: (farmId) => apiFetch(`/farms/${farmId}`),
  updateFarm: (farmId, data) => apiFetch(`/farms/${farmId}`, { method: 'PUT', body: data }),
  getSoil: (farmId) => apiFetch(`/farms/${farmId}/soil`),
  createSoil: (farmId, data) => apiFetch(`/farms/${farmId}/soil`, { method: 'POST', body: data }),
  getFields: (farmId) => apiFetch(`/farms/${farmId}/fields`),
  createField: (farmId, data) => apiFetch(`/farms/${farmId}/fields`, { method: 'POST', body: data }),
  getFarmAnalytics: (farmId) => apiFetch(`/farms/${farmId}/analytics`),

  // Crops
  getCropCatalog: () => apiFetch('/crops/catalog'),
  getFarmCrops: (farmId) => apiFetch(`/crops/farm/${farmId}`),
  createCrop: (data) => apiFetch('/crops/', { method: 'POST', body: data }),
  updateCrop: (cropId, data) => apiFetch(`/crops/${cropId}`, { method: 'PUT', body: data }),
  deleteCrop: (cropId) => apiFetch(`/crops/${cropId}`, { method: 'DELETE' }),
  getCropCalendar: (cropId) => apiFetch(`/crops/${cropId}/calendar`),
  getCropRecommendations: (farmId, month) => apiFetch(`/crops/recommendations/farm/${farmId}${month ? `?month=${month}` : ''}`),

  // Weather
  getWeather: (farmId) => apiFetch(`/weather/current/farm/${farmId}`),
  getForecast: (farmId, days = 5) => apiFetch(`/weather/forecast/farm/${farmId}?days=${days}`),

  // Irrigation
  getIrrigationRec: (farmId) => apiFetch(`/irrigation/recommend/farm/${farmId}`),
  logIrrigation: (farmId, amountMm) => apiFetch(`/irrigation/records?farm_id=${farmId}&amount_mm=${amountMm}`, { method: 'POST' }),
  getIrrigationHistory: (farmId) => apiFetch(`/irrigation/history/farm/${farmId}`),

  // Risks
  getRisks: (farmId) => apiFetch(`/risks/farm/${farmId}`),

  // Action Plan
  getActionPlan: (farmId) => apiFetch(`/plan/farm/${farmId}`),

  // Ask Shyam
  chatWithAI: (userId, farmId, message, history = [], image_base64 = null, voice_base64 = null, lang = "hi") => apiFetch('/ai/chat', {
    method: 'POST',
    body: { 
      user_id: userId, 
      farm_id: farmId, 
      message, 
      conversation_history: history, 
      image_base64: image_base64,
      voice_base64: voice_base64,
      generate_audio: !!voice_base64, // only generate audio if voice was sent
      language: lang
    }
  }),

  // Market
  getMandiPrices: (farmId) => apiFetch(`/market/prices/farm/${farmId}`),

  // Telegram
  linkTelegram: (userId) => apiFetch(`/telegram/link-code?user_id=${userId}`, { method: 'POST' }),

  // Tasks
  getFarmTasks: (farmId, status) => apiFetch(`/tasks/farm/${farmId}${status ? `?status=${status}` : ''}`),
  completeTask: (taskId) => apiFetch(`/tasks/${taskId}/complete`, { method: 'PUT' }),
  skipTask: (taskId) => apiFetch(`/tasks/${taskId}/skip`, { method: 'PUT' }),
};

// ── Toast notifications ──
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transform = 'translateX(20px)'; toast.style.transition = 'all 0.3s'; setTimeout(() => toast.remove(), 300); }, duration);
}

// ── Format helpers ──
function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatDateShort(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function timeAgo(dateStr) {
  const d = new Date(dateStr);
  const diff = Math.floor((Date.now() - d) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function getSuitabilityBadge(s) {
  const map = {
    highly_suitable: ['badge-green', '🌟 Highly Suitable'],
    suitable:        ['badge-blue', '✅ Suitable'],
    moderate:        ['badge-amber', '⚡ Moderate'],
    not_suitable:    ['badge-red', '❌ Not Suitable'],
  };
  const [cls, label] = map[s] || ['badge-gray', s];
  return `<span class="badge ${cls}">${label}</span>`;
}

function getRiskBadge(level) {
  const map = {
    critical: ['risk-critical', '🔴 CRITICAL'],
    high:     ['risk-high', '🟠 HIGH'],
    medium:   ['risk-medium', '🟡 MEDIUM'],
    low:      ['risk-low', '🔵 LOW'],
    none:     ['risk-none', '🟢 NONE'],
  };
  const [cls, label] = map[level] || ['badge-gray', level];
  return `<span class="badge ${cls}">${label}</span>`;
}

function getWeatherIcon(desc) {
  if (!desc) return '🌤️';
  const d = desc.toLowerCase();
  if (d.includes('thunder') || d.includes('storm')) return '⛈️';
  if (d.includes('heavy rain') || d.includes('shower')) return '🌧️';
  if (d.includes('rain') || d.includes('drizzle')) return '🌦️';
  if (d.includes('snow')) return '❄️';
  if (d.includes('fog') || d.includes('mist') || d.includes('haze')) return '🌫️';
  if (d.includes('cloud') || d.includes('overcast')) return '☁️';
  if (d.includes('partly cloudy') || d.includes('broken cloud')) return '⛅';
  if (d.includes('clear') || d.includes('sunny')) return '☀️';
  return '🌤️';
}

function getStageIcon(stage) {
  const icons = {
    land_preparation: '🌱', sowing: '🌾', germination: '🌿',
    vegetative: '🍃', flowering: '🌸', maturity: '🌻', harvest: '🚜'
  };
  return icons[stage] || '📅';
}

function getStageName(stage) {
  return stage ? stage.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'Unknown';
}

// ── Auth guard ──
function requireAuth(redirectTo = 'onboarding.html') {
  if (!State.isLoggedIn()) {
    window.location.href = redirectTo;
    return false;
  }
  return true;
}


// ─── GLOBAL WEBSITE TRANSLATOR CORE ───
(function initGoogleTranslate() {
    const gtDiv = document.createElement('div');
    gtDiv.id = 'google_translate_element';
    gtDiv.style.display = 'none';
    document.body.appendChild(gtDiv);

    window.googleTranslateElementInit = function() {
        new google.translate.TranslateElement({
            pageLanguage: 'en', 
            includedLanguages: 'en,hi', 
            autoDisplay: false
        }, 'google_translate_element');
    };
    const gtScript = document.createElement('script');
    gtScript.src = "https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
    document.body.appendChild(gtScript);

    const style = document.createElement('style');
    style.innerHTML = `html { height: 100%; margin: 0 !important; padding: 0 !important; }
body { position: static !important; top: 0px !important; min-height: 100% !important; }
iframe.goog-te-banner-frame { display: none !important; visibility: hidden !important; }
.goog-te-banner-frame.skiptranslate { display: none !important; }
.goog-te-banner-frame { display: none !important; }
#goog-gt-tt, .goog-te-balloon-frame { display: none !important; visibility: hidden !important; }
.goog-tooltip { display: none !important; }
.goog-tooltip:hover { display: none !important; }
.goog-text-highlight { background-color: transparent !important; box-shadow: none !important; }
.skiptranslate > iframe.goog-te-banner-frame { display: none !important; }
div#goog-gt- { display: none !important; }
.goog-logo-link { display: none !important; }
.goog-te-gadget { color: transparent !important; }
.goog-te-gadget .goog-te-combo { margin: 0 !important; }
#google_translate_element { opacity: 0; position: absolute; top: -100px; z-index: -999; width: 0; height: 0; overflow: hidden; display: block !important; }`;
    document.head.appendChild(style);
})();

window.changeWebsiteLanguage = function(langCode) {
    const selectField = document.querySelector("#google_translate_element select");
    
    if (langCode === 'en') {
        document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; domain=' + window.location.hostname + '; path=/;';
        
        // Try to revert by setting select value to empty string which is the default for 'Original'
        if(selectField) {
            selectField.value = "";
            selectField.dispatchEvent(new Event('change'));
        }
        
        // As a fallback, try to click the clear button in the iframe if it exists
        const restoreFrame = document.querySelector('iframe.goog-te-banner-frame');
        if (restoreFrame) {
            try {
                const restoreBtn = restoreFrame.contentWindow.document.querySelector('.goog-te-button button');
                if (restoreBtn) restoreBtn.click();
            } catch (e) {}
        }
        
        // Only reload if the text is STILL translated after 500ms
        setTimeout(() => {
            const isTranslated = document.querySelector('html').classList.contains('translated-ltr');
            if (isTranslated) {
                window.location.reload();
            }
        }, 500);
        
    } else {
        if(selectField) {
            selectField.value = langCode;
            selectField.dispatchEvent(new Event('change'));
        } else {
            if (!window._gtRetries) window._gtRetries = 0;
            if (window._gtRetries < 10) {
                window._gtRetries++;
                setTimeout(() => window.changeWebsiteLanguage(langCode), 500);
            }
        }
    }
    
    const shyamToggle = document.getElementById("shyamLangToggle");
    if (shyamToggle) shyamToggle.value = langCode;
    
    const checkboxes = document.querySelectorAll('.globalLangToggleCheckbox');
    checkboxes.forEach(c => c.checked = (langCode === 'hi'));
};

window.toggleWebsiteLanguage = function() {
    // Check if html has 'translated-ltr' class added by Google Translate
    const isTranslated = document.querySelector('html').classList.contains('translated-ltr');
    const newLang = isTranslated ? 'en' : 'hi';
    window.changeWebsiteLanguage(newLang);
};
// ──────────────────────────────────────

