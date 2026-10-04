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
    showToast(err.message || 'Something went wrong. Please try again.', 'error');
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


function initLocationAutocomplete() {
    const input = document.getElementById('farm-location');
    if (input && typeof google !== 'undefined' && google.maps && google.maps.places) {
        const autocomplete = new google.maps.places.Autocomplete(input, {
            types: ['(regions)'],
            componentRestrictions: { country: 'in' }
        });
        
        autocomplete.addListener('place_changed', function() {
            const place = autocomplete.getPlace();
            if (place.address_components) {
                let stateStr = '';
                for (let component of place.address_components) {
                    if (component.types.includes('administrative_area_level_1')) {
                        stateStr = component.long_name;
                        break;
                    }
                }
                if (stateStr) {
                    const stateSelect = document.getElementById('farm-state');
                    if (stateSelect) {
                        for (let i = 0; i < stateSelect.options.length; i++) {
                            if (stateSelect.options[i].text === stateStr || stateSelect.options[i].value === stateStr) {
                                stateSelect.selectedIndex = i;
                                break;
                            }
                        }
                    }
                }
            }
        });
    }
}

window.addEventListener('load', () => {
    setTimeout(initLocationAutocomplete, 500);
});
