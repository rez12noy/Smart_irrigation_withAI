
   
    const API_BASE = 'http://192.168.0.28:5000';
    const UPDATE_INTERVAL = 5000;
    const FRESH_DATA_TIMEOUT = 60000;

    const crops = {
      0: "Apple", 1: "Banana", 2: "Blackgram", 3: "Chickpea", 4: "Coconut",
      5: "Coffee", 6: "Cotton", 7: "Grapes", 8: "Jute", 9: "Kidneybeans",
      10: "Lentil", 11: "Maize", 12: "Mango", 13: "Mothbeans", 14: "Mungbean",
      15: "Muskmelon", 16: "Orange", 17: "Papaya", 18: "Pigeonpeas",
      19: "Pomegranate", 20: "Rice", 21: "Watermelon"
    };

    const elements = {
      currentCrop: document.getElementById('currentCrop'),
      currentMonth: document.getElementById('currentMonth'),
      pumpStatus: document.getElementById('pumpStatus'),
      moistureLevel: document.getElementById('moistureLevel'),
      waterNeed: document.getElementById('waterNeed'),
      temperature: document.getElementById('temperature'),
      humidity: document.getElementById('humidity'),
      rainfall: document.getElementById('rainfall'),
      statusMessage: document.getElementById('statusMessage'),
      cropSelect: document.getElementById('cropSelect'),
      updateCropBtn: document.getElementById('updateCropBtn'),
      historyBody: document.getElementById('historyBody'),
      errorMessage: document.getElementById('error-message'),
      cropUpdateStatus: document.getElementById('cropUpdateStatus')
    };

    let currentSystemCrop = 0;
    let updateInProgress = false;

    function showError(message) {
      const errorText = document.getElementById('error-text');
      errorText.textContent = message;
      elements.errorMessage.style.display = 'flex';
      setTimeout(() => {
        elements.errorMessage.style.display = 'none';
      }, 5000);
    }

    function showLoading(show) {
      elements.updateCropBtn.innerHTML = show
        ? '<span class="loading"></span> Updating...'
        : '<i class="fas fa-save"></i> Update Crop';
      elements.updateCropBtn.disabled = show;
    }

    function getMonthName(monthNumber) {
      const months = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"];
      return months[(monthNumber || 1) - 1] || "Unknown";
    }

    function isDataFresh(timestamp) {
      if (!timestamp) return false;
      const now = new Date().getTime();
      return (now - timestamp) <= FRESH_DATA_TIMEOUT;
    }

    function resetSensorData() {
      elements.moistureLevel.textContent = "Waiting...";
      elements.moistureLevel.className = "data-value waiting";
      elements.waterNeed.textContent = "Waiting...";
      elements.waterNeed.className = "data-value waiting";
      elements.pumpStatus.textContent = "Waiting...";
      elements.pumpStatus.className = "data-value waiting";
      elements.statusMessage.textContent = "Waiting for ESP32 data...";
      elements.statusMessage.className = "status-message checking";
    }

    async function fetchData(endpoint, options = {}) {
      try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
      } catch (error) {
        showError(`Failed to fetch data: ${error.message}`);
        console.error('API Error:', error);
        return null;
      }
    }

    async function loadCurrentData() {
      const data = await fetchData('/current');
      if (!data) return;

      elements.currentCrop.textContent = crops[data.current_crop] || "Unknown";
      elements.currentMonth.textContent = getMonthName(data.month);
      elements.temperature.textContent = `${data.weather?.temperature?.toFixed(1) || '0.0'}°C`;
      elements.humidity.textContent = `${data.weather?.humidity || '0'}%`;
      elements.rainfall.textContent = `${data.weather?.rainfall?.toFixed(2) || '0.00'}mm`;

      const hasFreshData = data.timestamp && isDataFresh(new Date(data.timestamp).getTime());

      if (!hasFreshData) {
        resetSensorData();
      } else {
        const voltage = data.voltage;
        const moisturePercent = Math.min(100, Math.max(0, ((3.3 - voltage) / (3.3 - 1.1)) * 100));
        elements.moistureLevel.textContent = `${moisturePercent.toFixed(0)}% (${voltage.toFixed(2)}V)`;
        elements.moistureLevel.className = "data-value";
        elements.waterNeed.textContent = `${data.water_need?.toFixed(2)}mm`;
        elements.waterNeed.className = "data-value";

        if (data.pump_active) {
          elements.pumpStatus.textContent = `ACTIVE\n(Watered for ${data.watering_time?.toFixed(1) || 0}s)`;
          elements.pumpStatus.className = "data-value pump-active";
          elements.statusMessage.textContent = "Pumping water...";
          elements.statusMessage.className = "status-message watering";
        } else {
          elements.pumpStatus.textContent = "INACTIVE";
          elements.pumpStatus.className = "data-value pump-inactive";
          const targetVoltage = 1.62 - ((data.water_need || 0) / 300.0);
          if (voltage <= targetVoltage + 0.05) {
            elements.statusMessage.textContent = "Adequate moisture - no need to water";
            elements.statusMessage.className = "status-message adequate";
          } else if ((data.weather?.rainfall || 0) >= (data.water_need || 0)) {
            elements.statusMessage.textContent = "Rainfall sufficient - no need to water";
            elements.statusMessage.className = "status-message adequate";
          } else {
            elements.statusMessage.textContent = "Checking moisture...";
            elements.statusMessage.className = "status-message checking";
          }
        }
      }

      currentSystemCrop = data.current_crop || 0;
      elements.cropSelect.value = currentSystemCrop;
    }

    async function loadHistory() {
      const history = await fetchData('/history');
      if (!history) return;
      elements.historyBody.innerHTML = history.map(item => `
        <tr>
          <td>${new Date(item.timestamp).toLocaleString()}</td>
          <td>${item.crop_type}</td>
          <td>${getMonthName(item.month)}</td>
          <td>${item.voltage?.toFixed(2) || '0.00'}V</td>
          <td>${item.water_need?.toFixed(2) || '0.00'}mm</td>
          <td class="${item.pump_active ? 'pump-active' : 'pump-inactive'}">
            ${item.pump_active ? `${item.watering_time?.toFixed(1) || 0}s` : '—'}
          </td>
        </tr>
      `).join('');
    }

    async function loadCropOptions() {
      const settings = await fetchData('/settings');
      if (!settings) return;
      elements.cropSelect.innerHTML = Object.entries(crops)
        .map(([id, name]) => `<option value="${id}">${name}</option>`)
        .join('');
      if (settings.current_crop !== undefined) {
        elements.cropSelect.value = settings.current_crop;
        currentSystemCrop = settings.current_crop;
      }
    }

    async function updateCrop() {
      if (updateInProgress) return;
      updateInProgress = true;
      showLoading(true);

      const cropId = elements.cropSelect.value;
      try {
        const response = await fetchData('/settings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ crop: cropId })
        });

        if (response?.status === "success") {
          elements.cropUpdateStatus.textContent = `Crop updated to ${crops[cropId]}`;
          elements.cropUpdateStatus.style.color = "green";
          elements.cropUpdateStatus.style.display = "block";
          currentSystemCrop = parseInt(cropId);
          await loadCurrentData();
        } else {
          showError(response?.message || "Failed to update crop");
          elements.cropSelect.value = currentSystemCrop;
        }
      } catch (error) {
        showError("Error updating crop");
        elements.cropSelect.value = currentSystemCrop;
      } finally {
        showLoading(false);
        updateInProgress = false;
        setTimeout(() => {
          elements.cropUpdateStatus.style.display = 'none';
        }, 3000);
      }
    }

    async function initDashboard() {
      await loadCropOptions();
      await loadCurrentData();
      await loadHistory();
      setInterval(loadCurrentData, UPDATE_INTERVAL);
      setInterval(loadHistory, UPDATE_INTERVAL * 2);
    }

    elements.updateCropBtn.addEventListener('click', updateCrop);
    document.addEventListener('DOMContentLoaded', initDashboard);

    const profileIcon = document.getElementById("profileIcon");
    const profileMenu = document.getElementById("profileMenu");
    const profileEmail = document.getElementById("profileEmail");

    profileIcon.addEventListener("click", () => {
      profileMenu.style.display = profileMenu.style.display === "block" ? "none" : "block";
    });

    window.addEventListener("click", function(e) {
      if (!profileIcon.contains(e.target) && !profileMenu.contains(e.target)) {
        profileMenu.style.display = "none";
      }
    });

    async function loadUserEmail() {
      const res = await fetch("/check-auth", { credentials: "include" });
      const data = await res.json();
      if (data.authenticated) {
        const initials = (data.user[0] || 'U').toUpperCase();
        profileIcon.textContent = initials;
        profileEmail.textContent = data.user;
      }
    }

    document.addEventListener('DOMContentLoaded', loadUserEmail);

    // Add at the top with your other variables
let cropSelectLock = false;

// Replace your loadCropOptions function with this
async function loadCropOptions() {
  if (cropSelectLock) return;
  
  const settings = await fetchData('/settings');
  if (!settings) return;
  
  cropSelectLock = true;
  elements.cropSelect.innerHTML = Object.entries(crops)
    .map(([id, name]) => `<option value="${id}">${name}</option>`)
    .join('');
  
  if (settings.current_crop !== undefined) {
    elements.cropSelect.value = settings.current_crop;
    currentSystemCrop = settings.current_crop;
  }
  cropSelectLock = false;
}

// Add this at the end of your loadCurrentData function
if (!cropSelectLock && data.current_crop !== undefined) {
  currentSystemCrop = data.current_crop;
  elements.cropSelect.value = currentSystemCrop;
}