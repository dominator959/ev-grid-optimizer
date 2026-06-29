document.addEventListener('DOMContentLoaded', () => {
    // Cache Elements
    const stationsList = document.getElementById('stationsList');
    const chargersList = document.getElementById('chargersList');
    const selectUser = document.getElementById('selectUser');
    const selectCharger = document.getElementById('selectCharger');
    const userWalletInfo = document.getElementById('userWalletInfo');
    const bookingForm = document.getElementById('bookingForm');
    const btnSubmitBooking = document.getElementById('btnSubmitBooking');
    const inputStartTime = document.getElementById('inputStartTime');
    const inputEndTime = document.getElementById('inputEndTime');
    
    // Modal Elements
    const notificationModal = document.getElementById('notificationModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const modalIconContainer = document.getElementById('modalIconContainer');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const btnOkModal = document.getElementById('btnOkModal');

    // Global lists
    let usersData = [];

    // Pre-populate input dates (Start: Now, End: Now + 1 hour)
    const now = new Date();
    const future = new Date(now.getTime() + 60 * 60 * 1000); // +1 hour
    
    const formatDate = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    };

    inputStartTime.value = formatDate(now);
    inputEndTime.value = formatDate(future);

    // Initial Fetch Sequence
    updateDynamicTariffUI();
    fetchStations();
    fetchChargers();
    fetchUsers();

    // 1. Fetch & Render Stations
    async function fetchStations() {
        try {
            const response = await fetch('/api/stations');
            const stations = await response.json();
            
            if (response.ok) {
                stationsList.innerHTML = '';
                stations.forEach(station => {
                    const loadPercentage = Math.min(100, Math.round((station.current_load_kw / station.max_grid_capacity_kw) * 100));
                    
                    let loadClass = '';
                    if (loadPercentage > 85) loadClass = 'danger';
                    else if (loadPercentage > 60) loadClass = 'warning';

                    const stationHtml = `
                        <div class="station-load-card">
                            <div class="station-info">
                                <span class="station-title">${station.location_area} (${station.city})</span>
                                <span class="station-meta">Max Cap: ${station.max_grid_capacity_kw} kW</span>
                            </div>
                            <div class="load-bar-container">
                                <div class="load-bar ${loadClass}" style="width: ${loadPercentage}%"></div>
                            </div>
                            <div class="load-text">
                                <span>Current Load: ${station.current_load_kw} kW</span>
                                <span>${loadPercentage}% Load</span>
                            </div>
                        </div>
                    `;
                    stationsList.insertAdjacentHTML('beforeend', stationHtml);
                });
            } else {
                stationsList.innerHTML = `<p class="error-text">Failed to load stations: ${stations.error}</p>`;
            }
        } catch (err) {
            stationsList.innerHTML = `<p class="error-text">Unable to connect to service</p>`;
        }
    }

    // 2. Fetch & Render Chargers
    async function fetchChargers() {
        try {
            const response = await fetch('/api/chargers');
            const chargers = await response.json();

            if (response.ok) {
                // Render Status Board list
                chargersList.innerHTML = '';
                // Render Selection Dropdown
                selectCharger.innerHTML = '<option value="" disabled selected>Select Charger...</option>';

                chargers.forEach(charger => {
                    const statusClass = charger.status.toLowerCase();
                    const statusBadge = `<span class="badge ${statusClass}">${charger.status}</span>`;
                    
                    // Render to Status Board list
                    const chargerHtml = `
                        <div class="charger-item">
                            <div class="charger-detail">
                                <i class="fa-solid fa-plug charger-icon"></i>
                                <div>
                                    <div class="charger-name">Charger #${charger.charger_id} (${charger.connector_type})</div>
                                    <div class="charger-sub">${charger.location_area}, ${charger.city} | ${charger.power_output_kw} kW</div>
                                </div>
                            </div>
                            <div>
                                ${statusBadge}
                            </div>
                        </div>
                    `;
                    chargersList.insertAdjacentHTML('beforeend', chargerHtml);

                    // Add to dropdown list (disable if occupied, maintenance, or load shedding)
                    const isAvailable = charger.status === 'Available';
                    const optionHtml = `
                        <option value="${charger.charger_id}" ${!isAvailable ? 'disabled' : ''}>
                            Charger #${charger.charger_id} [${charger.connector_type}] (${charger.location_area}) - ${charger.status}
                        </option>
                    `;
                    selectCharger.insertAdjacentHTML('beforeend', optionHtml);
                });
            } else {
                chargersList.innerHTML = '<p class="error-text">Failed to load chargers.</p>';
            }
        } catch (err) {
            chargersList.innerHTML = '<p class="error-text">Unable to connect to service</p>';
        }
    }

    // 3. Fetch Users list for booking selection
    async function fetchUsers() {
        try {
            const response = await fetch('/api/users');
            const users = await response.json();
            if (response.ok) {
                usersData = users;
                selectUser.innerHTML = '<option value="" disabled selected>Select EV Owner...</option>';
                users.forEach(user => {
                    const opt = document.createElement('option');
                    opt.value = user.user_id;
                    opt.textContent = `${user.owner_name} (${user.car_model})`;
                    selectUser.appendChild(opt);
                });
            }
        } catch (err) {
            console.error("Failed to load users:", err);
        }
    }

    // Update wallet text info when user changes selection
    selectUser.addEventListener('change', () => {
        const selectedId = parseInt(selectUser.value);
        const user = usersData.find(u => u.user_id === selectedId);
        if (user) {
            userWalletInfo.textContent = `EV: ${user.car_model} (Cap: ${user.battery_capacity_kwh} kWh) | Balance: PKR ${parseFloat(user.wallet_balance_pkr).toFixed(2)}`;
            userWalletInfo.classList.remove('hidden');
        } else {
            userWalletInfo.classList.add('hidden');
        }
    });

    // 4. Update Tariff GUI Clock & Mode
    function updateDynamicTariffUI() {
        const currentHour = new Date().getHours();
        const currentRateBubble = document.getElementById('currentRateBubble');
        const tariffModeDisplay = document.getElementById('tariffModeDisplay');
        const periods = document.querySelectorAll('.schedule-period');

        if (currentHour >= 17 && currentHour < 23) {
            // Peak Hours (5 PM to 11 PM)
            currentRateBubble.innerHTML = `
                <span class="price-val">PKR 75.00</span>
                <span class="price-lbl">per kWh (PEAK)</span>
            `;
            tariffModeDisplay.innerHTML = `<span class="badge load_shedding"><i class="fa-solid fa-triangle-exclamation"></i> Peak Tariff active</span>`;
            periods[0].classList.remove('active');
            periods[1].classList.add('active');
        } else {
            // Off-Peak Hours
            currentRateBubble.innerHTML = `
                <span class="price-val">PKR 50.00</span>
                <span class="price-lbl">per kWh (OFF-PEAK)</span>
            `;
            tariffModeDisplay.innerHTML = `<span class="badge available"><i class="fa-solid fa-circle-check"></i> Off-Peak rate</span>`;
            periods[0].classList.add('active');
            periods[1].classList.remove('active');
        }
    }

    // 5. Submit Booking
    bookingForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const payload = {
            user_id: selectUser.value,
            charger_id: selectCharger.value,
            start_time: inputStartTime.value,
            end_time: inputEndTime.value
        };

        // Loading state
        btnSubmitBooking.disabled = true;
        btnSubmitBooking.querySelector('.btn-text').textContent = 'Processing...';
        btnSubmitBooking.querySelector('.btn-spinner').classList.remove('hidden');

        try {
            const response = await fetch('/api/book', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();

            if (response.ok && result.success) {
                showModal(
                    "Booking Confirmed!", 
                    `🎉 Success! Your EV charging reservation has been successfully booked using the secure BookChargingSlot transaction sequence.`,
                    true
                );
                // Refresh data states
                fetchStations();
                fetchChargers();
                bookingForm.reset();
                userWalletInfo.classList.add('hidden');
            } else {
                showModal(
                    "Booking Failed", 
                    `❌ Error: ${result.error || 'The charger may already be reserved for this time block or is currently unavailable.'}`,
                    false
                );
            }
        } catch (err) {
            showModal(
                "Connection Offline",
                "❌ Unable to send transaction to grid controller. Verify the web server is running.",
                false
            );
        } finally {
            btnSubmitBooking.disabled = false;
            btnSubmitBooking.querySelector('.btn-text').textContent = 'Confirm Reservation';
            btnSubmitBooking.querySelector('.btn-spinner').classList.add('hidden');
        }
    });

    // Modal helpers
    function showModal(title, msg, isSuccess) {
        modalTitle.textContent = title;
        modalMessage.textContent = msg;
        
        if (isSuccess) {
            modalIconContainer.innerHTML = `<i class="fa-solid fa-circle-check icon-success"></i>`;
        } else {
            modalIconContainer.innerHTML = `<i class="fa-solid fa-circle-xmark icon-error"></i>`;
        }
        
        notificationModal.classList.remove('hidden');
    }

    function closeModal() {
        notificationModal.classList.add('hidden');
    }

    btnCloseModal.addEventListener('click', closeModal);
    btnOkModal.addEventListener('click', closeModal);
    window.addEventListener('click', (e) => {
        if (e.target === notificationModal) closeModal();
    });
});
