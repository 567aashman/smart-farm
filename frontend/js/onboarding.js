/**
 * SmartFarm - Onboarding JS
 * Handles multi-step farm setup flow.
 */

let currentStep = 1;
const TOTAL_STEPS = 3;

// Created entity IDs
let createdUserId = null;
let createdFarmId = null;
let createdFieldId = null;
let detectedFarmCoords = null;

let isEditMode = false;

function updateStepUI() {
  // Show/hide steps
  for (let i = 1; i <= TOTAL_STEPS; i++) {
    document.getElementById(`step-${i}`).classList.toggle('active', i === currentStep);
  }

  // Update dots
  for (let i = 1; i <= TOTAL_STEPS; i++) {
    const dot = document.getElementById(`dot-${i}`);
    dot.classList.remove('active', 'done');
    if (i === currentStep) dot.classList.add('active');
    else if (i < currentStep) dot.classList.add('done');
  }

  // Update lines
  for (let i = 1; i < TOTAL_STEPS; i++) {
    document.getElementById(`line-${i}`).classList.toggle('done', i < currentStep);
  }

  // Back button
  const backBtn = document.getElementById('btn-back');
  backBtn.style.visibility = currentStep > 1 ? 'visible' : 'hidden';

  // Counter and next button
  document.getElementById('step-counter').textContent = `Step ${currentStep} of ${TOTAL_STEPS}`;

  const nextBtn = document.getElementById('btn-next');
  if (currentStep === TOTAL_STEPS) {
    nextBtn.textContent = '✅ Finish Setup';
  } else {
    nextBtn.textContent = 'Next →';
  }
}

function prevStep() {
  if (currentStep > 1) {
    currentStep--;
    updateStepUI();
  }
}

async function nextStep() {
  const btn = document.getElementById('btn-next');
  btn.disabled = true;
  btn.textContent = '⏳ Saving...';

  try {
    if (currentStep === 1) await submitStep1();
    else if (currentStep === 2) await submitStep2();
    else if (currentStep === 3) await submitStep3();

    if (currentStep < TOTAL_STEPS) {
      currentStep++;
      updateStepUI();
    } else {
      showSuccessScreen();
    }
  } catch (err) {
    const msg = err.message || 'Something went wrong. Please try again.';
    showToast(msg, 'error');
    alert('Error: ' + msg); // fallback for when toast is not visible
  } finally {
    btn.disabled = false;
    updateStepUI();
  }
}

async function submitStep1() {
  const name = document.getElementById('farmer-name').value.trim();
  if (!name) throw new Error('Please enter your name');

  const phone = document.getElementById('farmer-phone').value.trim();
  const email = document.getElementById('farmer-email').value.trim();

  if (isEditMode) {
    await API.updateUser(createdUserId, { name, phone: phone || null, email: email || null });
    showToast('Farmer profile updated!', 'success');
  } else {
    const user = await API.createUser({ name, phone: phone || null, email: email || null });
    createdUserId = user.id;
    showToast('Farmer profile created!', 'success');
  }
}

async function submitStep2() {
  if (!createdUserId) throw new Error('Farmer profile not found. Please go back to step 1.');

  const farmName = document.getElementById('farm-name').value.trim();
  const location = document.getElementById('farm-location').value.trim();
  const area = parseFloat(document.getElementById('farm-area').value);

  if (!farmName) throw new Error('Please enter your farm name');
  if (!location) throw new Error('Please enter your farm location (city/district)');
  if (!area || area <= 0) throw new Error('Please enter a valid farm area');

  const state = document.getElementById('farm-state').value;
  const irrigationMethod = document.getElementById('irrigation-method').value;
  const waterSource = document.getElementById('water-source').value;

  const farmData = {
    name: farmName,
    location,
    state: state || null,
    total_area_acres: area,
    irrigation_method: irrigationMethod,
    water_source: waterSource,
    country: 'India',
  };

  if (detectedFarmCoords && detectedFarmCoords.latitude && detectedFarmCoords.longitude) {
    farmData.latitude = detectedFarmCoords.latitude;
    farmData.longitude = detectedFarmCoords.longitude;
  }

  if (isEditMode) {
    await API.updateFarm(createdFarmId, farmData);
    
    // Attempt to update/create soil
    const soilType = document.getElementById('soil-type').value;
    const soilPH = parseFloat(document.getElementById('soil-ph').value);
    try {
      await API.createSoil(createdFarmId, {
        soil_type: soilType,
        ph_level: soilPH || null,
      });
    } catch (e) {
      console.log('Soil might already exist or update failed', e);
    }
    showToast('Farm profile updated!', 'success');
  } else {
    // Create farm
    const farm = await API.createFarm(createdUserId, farmData);
    createdFarmId = farm.id;

    // Create soil profile
    const soilType = document.getElementById('soil-type').value;
    const soilPH = parseFloat(document.getElementById('soil-ph').value);
    await API.createSoil(createdFarmId, {
      soil_type: soilType,
      ph_level: soilPH || null,
    });
    showToast('Farm profile saved!', 'success');
  }

  // Save to state
  State.set(createdUserId, createdFarmId, document.getElementById('farmer-name').value.trim(), farmName);
}

async function submitStep3() {
  if (!createdFarmId) throw new Error('Farm not created yet. Please go back.');

  const cropSelect = document.getElementById('crop-name').value;
  if (!cropSelect) {
    // Skipped — OK
    return;
  }

  const cropName = cropSelect === 'custom'
    ? document.getElementById('crop-custom').value.trim()
    : cropSelect;

  if (cropSelect === 'custom' && !cropName) throw new Error('Please enter the crop name');

  const fieldName = document.getElementById('field-name').value.trim() || 'Main Field';
  const cropArea = parseFloat(document.getElementById('crop-area').value) || 1.0;
  const variety = document.getElementById('crop-variety').value.trim();
  const sowingDate = document.getElementById('sowing-date').value;

  // Create field
  const field = await API.createField(createdFarmId, { name: fieldName, area_acres: cropArea });
  createdFieldId = field.id;

  // Create crop
  await API.createCrop({
    field_id: createdFieldId,
    crop_name: cropName,
    variety: variety || null,
    area_acres: cropArea,
    sowing_date: sowingDate || null,
  });

  showToast('Crop added successfully!', 'success');
}

function showSuccessScreen() {
  document.getElementById('step-3').classList.remove('active');
  document.getElementById('step-success').classList.add('active');
  document.getElementById('onboard-footer').style.display = 'none';

  // Update all dots to done
  for (let i = 1; i <= TOTAL_STEPS; i++) {
    const dot = document.getElementById(`dot-${i}`);
    dot.classList.remove('active');
    dot.classList.add('done');
  }
  for (let i = 1; i < TOTAL_STEPS; i++) {
    document.getElementById(`line-${i}`).classList.add('done');
  }
}

// Handle crop select change
document.getElementById('crop-name').addEventListener('change', function () {
  document.getElementById('custom-crop-row').classList.toggle('hidden', this.value !== 'custom');
});

// Initialize
async function initOnboarding() {
  if (State.isLoggedIn()) {
    isEditMode = true;
    createdUserId = State.userId;
    createdFarmId = State.farmId;
    
    // Update headers for edit mode
    document.querySelector('.onboard-header h1').textContent = '🌾 SmartFarm Settings';
    document.querySelector('.onboard-header p').textContent = 'Update your farm profile';
    
    try {
      // Load user data
      const user = await API.getUser(createdUserId);
      if (user) {
        document.getElementById('farmer-name').value = user.name || '';
        document.getElementById('farmer-phone').value = user.phone || '';
        document.getElementById('farmer-email').value = user.email || '';
      }
      
      // Load farm data
      const farms = await API.getUserFarms(createdUserId);
      if (farms && farms.length > 0) {
        const farm = farms[0];
        document.getElementById('farm-name').value = farm.name || '';
        document.getElementById('farm-location').value = farm.location || '';
        document.getElementById('farm-area').value = farm.total_area_acres || '';
        if (farm.state) document.getElementById('farm-state').value = farm.state;
        if (farm.irrigation_method) document.getElementById('irrigation-method').value = farm.irrigation_method;
        if (farm.water_source) document.getElementById('water-source').value = farm.water_source;
        
        // Soil
        if (farm.soil_profile) {
          if (farm.soil_profile.soil_type) document.getElementById('soil-type').value = farm.soil_profile.soil_type;
          if (farm.soil_profile.ph_level) document.getElementById('soil-ph').value = farm.soil_profile.ph_level;
        }
      }
    } catch (e) {
      console.error('Failed to load existing profile for edit mode:', e);
    }
  }
  updateStepUI();
}

initOnboarding();


/**
 * Match and select state dropdown option based on state name string
 */
function selectStateByName(stateStr) {
  if (!stateStr) return;
  const stateSelect = document.getElementById('farm-state');
  if (!stateSelect) return;

  const normalize = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const target = normalize(stateStr);

  for (let i = 0; i < stateSelect.options.length; i++) {
    const opt = stateSelect.options[i];
    const optVal = normalize(opt.value || opt.text);
    if (optVal && (optVal === target || target.includes(optVal) || optVal.includes(target))) {
      stateSelect.selectedIndex = i;
      return;
    }
  }
}

/**
 * Detect Current Live Location using Browser GPS + Google Geocoding (with fallbacks)
 */
async function detectLiveLocation() {
  const btn = document.getElementById('btn-live-location');
  const btnText = document.getElementById('loc-btn-text');
  const btnIcon = document.getElementById('loc-btn-icon');
  const hint = document.getElementById('farm-location-hint');
  const locationInput = document.getElementById('farm-location');

  if (!navigator.geolocation) {
    const msg = 'Geolocation is not supported by your browser.';
    if (typeof showToast === 'function') showToast(msg, 'error');
    else alert(msg);
    return;
  }

  // Update UI to loading state
  if (btn) {
    btn.disabled = true;
    btn.classList.add('loading');
  }
  if (btnText) btnText.textContent = 'Locating...';
  if (btnIcon) btnIcon.textContent = '⏳';
  if (hint) hint.innerHTML = '<span style="color:var(--color-primary);">📡 Fetching your GPS coordinates...</span>';

  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const lat = position.coords.latitude;
      const lng = position.coords.longitude;
      detectedFarmCoords = { latitude: lat, longitude: lng };

      if (hint) hint.innerHTML = '<span style="color:var(--color-primary);">🔍 Identifying city & state...</span>';

      try {
        let city = '';
        let district = '';
        let state = '';

        // 1. Try Google Maps Geocoder if loaded and available
        if (typeof google !== 'undefined' && google.maps && google.maps.Geocoder) {
          try {
            const geocoder = new google.maps.Geocoder();
            const gResults = await new Promise((resolve) => {
              geocoder.geocode({ location: { lat, lng } }, (results, status) => {
                if (status === 'OK' && results && results.length > 0) {
                  resolve(results);
                } else {
                  resolve(null);
                }
              });
            });

            if (gResults && gResults.length > 0) {
              for (const item of gResults) {
                for (const comp of item.address_components) {
                  if (!city && (comp.types.includes('locality') || comp.types.includes('postal_town'))) {
                    city = comp.long_name;
                  }
                  if (!district && comp.types.includes('administrative_area_level_2')) {
                    district = comp.long_name;
                  }
                  if (!state && comp.types.includes('administrative_area_level_1')) {
                    state = comp.long_name;
                  }
                }
                if (city && state) break;
              }
            }
          } catch (gErr) {
            console.warn('Google Geocoder lookup warning:', gErr);
          }
        }

        // 2. Fallback to BigDataCloud reverse geocoding API
        if (!city && !district) {
          try {
            const bdcRes = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lng}&localityLanguage=en`);
            if (bdcRes.ok) {
              const bdcData = await bdcRes.json();
              city = bdcData.city || bdcData.locality || '';
              state = bdcData.principalSubdivision || state;
              if (bdcData.localityInfo && bdcData.localityInfo.administrative) {
                for (const adm of bdcData.localityInfo.administrative) {
                  if (adm.adminLevel === 5 && !district) district = adm.name.replace(/\s+district/i, '');
                  if (adm.adminLevel === 4 && !state) state = adm.name;
                }
              }
            }
          } catch (bErr) {
            console.warn('BigDataCloud reverse geocode fallback warning:', bErr);
          }
        }

        // 3. Fallback to OpenStreetMap Nominatim reverse geocode
        if (!city && !district) {
          try {
            const osmRes = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=10&addressdetails=1`);
            if (osmRes.ok) {
              const osmData = await osmRes.json();
              const addr = osmData.address || {};
              city = addr.city || addr.town || addr.village || addr.county || '';
              district = addr.state_district || district;
              state = addr.state || state;
            }
          } catch (oErr) {
            console.warn('Nominatim reverse geocode fallback warning:', oErr);
          }
        }

        // Determine final location name
        const finalLocation = city || district || `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        if (locationInput) {
          locationInput.value = finalLocation;
        }

        // Select matching state
        if (state) {
          selectStateByName(state);
        }

        // Update hint with success badge
        if (hint) {
          hint.innerHTML = `<span style="color:var(--color-primary); font-weight: 500;">✓ Live location set: <b>${finalLocation}</b>${state ? ' (' + state + ')' : ''}</span>`;
        }

        if (typeof showToast === 'function') {
          showToast(`📍 Location detected: ${finalLocation}`, 'success');
        }
      } catch (err) {
        console.error('Error resolving location name:', err);
        if (locationInput && !locationInput.value) {
          locationInput.value = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
        }
        if (hint) {
          hint.innerHTML = `<span style="color:var(--color-primary);">✓ GPS Coordinates set: ${lat.toFixed(4)}, ${lng.toFixed(4)}</span>`;
        }
      } finally {
        if (btn) {
          btn.disabled = false;
          btn.classList.remove('loading');
        }
        if (btnText) btnText.textContent = 'Live Location';
        if (btnIcon) btnIcon.textContent = '📍';
      }
    },
    (err) => {
      console.error('Geolocation error:', err);
      let errMsg = 'Could not access live location.';
      if (err.code === 1) {
        errMsg = 'Location permission was denied. Please allow location access or type manually.';
      } else if (err.code === 2) {
        errMsg = 'GPS location unavailable. Please type manually.';
      } else if (err.code === 3) {
        errMsg = 'GPS request timed out. Please try again or type manually.';
      }

      if (hint) {
        hint.innerHTML = `<span style="color:var(--color-red);">${errMsg}</span>`;
      }
      if (typeof showToast === 'function') {
        showToast(errMsg, 'error');
      }

      if (btn) {
        btn.disabled = false;
        btn.classList.remove('loading');
      }
      if (btnText) btnText.textContent = 'Live Location';
      if (btnIcon) btnIcon.textContent = '📍';
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
  );
}

/**
 * Initialize Google Places Autocomplete for manual location typing
 */
function initLocationAutocomplete() {
  const input = document.getElementById('farm-location');
  if (!input) return;

  // Manual typing listener to keep manual control clean
  input.addEventListener('input', () => {
    // If user is actively typing, inform them manual editing is active
    const hint = document.getElementById('farm-location-hint');
    if (hint && !hint.textContent.includes('Manual typing')) {
      hint.innerHTML = 'Manual typing active. Tip: Click <b>Live Location</b> anytime for GPS.';
    }
  });

  if (typeof google !== 'undefined' && google.maps && google.maps.places) {
    try {
      const autocomplete = new google.maps.places.Autocomplete(input, {
        types: ['(regions)'],
        componentRestrictions: { country: 'in' }
      });

      autocomplete.addListener('place_changed', function() {
        const place = autocomplete.getPlace();
        if (place.geometry && place.geometry.location) {
          detectedFarmCoords = {
            latitude: place.geometry.location.lat(),
            longitude: place.geometry.location.lng()
          };
        }
        if (place.address_components) {
          let stateStr = '';
          for (let component of place.address_components) {
            if (component.types.includes('administrative_area_level_1')) {
              stateStr = component.long_name;
              break;
            }
          }
          if (stateStr) {
            selectStateByName(stateStr);
          }
        }
        const hint = document.getElementById('farm-location-hint');
        if (hint) {
          hint.innerHTML = '<span style="color:var(--color-primary);">✓ Location selected from Google Places</span>';
        }
      });
    } catch (e) {
      console.warn('Google Places Autocomplete init error:', e);
    }
  }
}

window.addEventListener('load', () => {
  setTimeout(initLocationAutocomplete, 500);
});
