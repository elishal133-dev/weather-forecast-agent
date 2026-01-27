/**
 * Kite Forecast Israel - PWA Frontend
 * Main application JavaScript
 */

// ============ Configuration ============
const API_BASE = '';  // Same origin
const REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

// ============ State ============
let currentRegion = 'all';
let rankings = [];
let spots = {};
let refreshTimer = null;

// ============ Region translations ============
const regionNames = {
    'north': 'צפון',
    'central': 'מרכז',
    'south': 'דרום',
    'eilat': 'אילת',
    'kinneret': 'כנרת'
};

const ratingLabels = {
    'epic': 'מושלם',
    'good': 'טוב',
    'fair': 'סביר',
    'marginal': 'גבולי',
    'poor': 'חלש'
};

// ============ DOM Elements ============
const elements = {
    loading: document.getElementById('loading'),
    error: document.getElementById('error'),
    spotsList: document.getElementById('spots-list'),
    lastUpdate: document.getElementById('last-update'),
    refreshBtn: document.getElementById('refresh-btn'),
    modal: document.getElementById('spot-modal'),
    modalBody: document.getElementById('modal-body'),
    notificationBanner: document.getElementById('notification-banner'),
    enableNotifications: document.getElementById('enable-notifications')
};

// ============ API Functions ============
async function fetchRankings(region = null) {
    const params = new URLSearchParams();
    if (region && region !== 'all') {
        params.set('region', region);
    }
    params.set('limit', '50');

    const response = await fetch(`${API_BASE}/api/rankings?${params}`);
    if (!response.ok) throw new Error('Failed to fetch rankings');
    return response.json();
}

async function fetchSpotForecast(spotId) {
    const response = await fetch(`${API_BASE}/api/forecast/${spotId}?hours=24`);
    if (!response.ok) throw new Error('Failed to fetch forecast');
    return response.json();
}

async function forceRefresh() {
    const response = await fetch(`${API_BASE}/api/admin/refresh`, { method: 'POST' });
    return response.json();
}

// ============ UI Functions ============
function showLoading() {
    elements.loading.classList.remove('hidden');
    elements.error.classList.add('hidden');
    elements.spotsList.classList.add('hidden');
}

function showError() {
    elements.loading.classList.add('hidden');
    elements.error.classList.remove('hidden');
    elements.spotsList.classList.add('hidden');
}

function showSpots() {
    elements.loading.classList.add('hidden');
    elements.error.classList.add('hidden');
    elements.spotsList.classList.remove('hidden');
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(isoString) {
    const date = new Date(isoString);
    return date.toLocaleDateString('he-IL', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getScoreClass(rating) {
    return rating.toLowerCase();
}

function createSpotCard(spot, rank) {
    const waveDisplay = spot.wave_height_m !== null
        ? `${spot.wave_height_m.toFixed(1)}m`
        : 'שטוח';

    const beginnerTag = spot.is_suitable_for_beginners
        ? '<span class="beginner-tag">מתאים למתחילים</span>'
        : '';

    return `
        <article class="spot-card" data-spot-id="${spot.spot_id}" onclick="openSpotModal('${spot.spot_id}')">
            <div class="spot-card-header">
                <div class="spot-info">
                    <div class="spot-rank">#${rank}</div>
                    <h2 class="spot-name">${spot.spot_name_he}</h2>
                    <div class="spot-name-en">${spot.spot_name}</div>
                    <div class="spot-region">${regionNames[spot.region] || spot.region}</div>
                    ${beginnerTag}
                </div>
                <div class="score-badge ${getScoreClass(spot.overall_rating)}">
                    <span class="score">${Math.round(spot.overall_score)}</span>
                    <span class="label">${ratingLabels[spot.overall_rating] || spot.overall_rating}</span>
                </div>
            </div>

            <div class="spot-conditions">
                <div class="condition-item">
                    <div class="condition-value">${spot.wind_speed_knots.toFixed(0)}</div>
                    <div class="condition-label">קשר</div>
                </div>
                <div class="condition-item">
                    <div class="condition-value">${spot.wind_direction}</div>
                    <div class="condition-label">כיוון</div>
                </div>
                <div class="condition-item">
                    <div class="condition-value">${waveDisplay}</div>
                    <div class="condition-label">גלים</div>
                </div>
            </div>

            <div class="spot-recommendation">
                ${spot.recommendation}
            </div>
        </article>
    `;
}

function renderSpots(data) {
    if (!data.rankings || data.rankings.length === 0) {
        elements.spotsList.innerHTML = `
            <div class="no-results">
                <p>אין ספוטים זמינים באזור זה</p>
            </div>
        `;
        return;
    }

    rankings = data.rankings;

    const html = data.rankings.map((spot, index) =>
        createSpotCard(spot, index + 1)
    ).join('');

    elements.spotsList.innerHTML = html;

    // Update last update time
    if (data.last_update) {
        elements.lastUpdate.textContent = `עודכן: ${formatDate(data.last_update)}`;
    }
}

// ============ Modal Functions ============
async function openSpotModal(spotId) {
    const spot = rankings.find(s => s.spot_id === spotId);
    if (!spot) return;

    elements.modal.classList.remove('hidden');
    elements.modalBody.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';

    try {
        const forecast = await fetchSpotForecast(spotId);
        renderModalContent(spot, forecast);
    } catch (error) {
        elements.modalBody.innerHTML = '<p>שגיאה בטעינת התחזית</p>';
    }
}

function renderModalContent(spot, forecast) {
    const waveDisplay = spot.wave_height_m !== null
        ? `${spot.wave_height_m.toFixed(1)}m`
        : 'שטוח';

    // Get next 12 hours
    const nextHours = forecast.hourly.slice(0, 12);

    const hoursHtml = nextHours.map(hour => {
        const time = new Date(hour.time);
        const timeStr = time.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });

        return `
            <div class="forecast-hour">
                <div class="time">${timeStr}</div>
                <div class="wind">${Math.round(hour.wind_speed_knots)}</div>
                <div class="direction">${hour.wind_direction_cardinal}</div>
            </div>
        `;
    }).join('');

    elements.modalBody.innerHTML = `
        <div class="modal-spot-header">
            <h2>${spot.spot_name_he}</h2>
            <div class="subtitle">${spot.spot_name} | ${regionNames[spot.region] || spot.region}</div>
        </div>

        <div class="score-badge ${getScoreClass(spot.overall_rating)}" style="margin: 0 auto var(--spacing-lg);">
            <span class="score">${Math.round(spot.overall_score)}</span>
            <span class="label">${ratingLabels[spot.overall_rating] || spot.overall_rating}</span>
        </div>

        <div class="spot-conditions" style="margin-bottom: var(--spacing-lg);">
            <div class="condition-item">
                <div class="condition-value">${spot.wind_speed_knots.toFixed(0)}</div>
                <div class="condition-label">קשר</div>
            </div>
            <div class="condition-item">
                <div class="condition-value">${spot.wind_gusts_knots.toFixed(0)}</div>
                <div class="condition-label">משבים</div>
            </div>
            <div class="condition-item">
                <div class="condition-value">${waveDisplay}</div>
                <div class="condition-label">גלים</div>
            </div>
        </div>

        <div style="background: var(--primary-light); padding: var(--spacing-md); border-radius: var(--border-radius-sm); margin-bottom: var(--spacing-lg);">
            <strong>המלצה:</strong> ${spot.recommendation}
        </div>

        <div class="forecast-section">
            <h3>תחזית ל-12 שעות הקרובות (רוח בקשר)</h3>
            <div class="forecast-hours">
                ${hoursHtml}
            </div>
        </div>

        <div style="margin-top: var(--spacing-lg); font-size: var(--font-size-sm); color: var(--text-secondary);">
            <p><strong>רוח:</strong> ${spot.wind_description}</p>
            <p><strong>גלים:</strong> ${spot.wave_description}</p>
            <p><strong>רמת קושי:</strong> ${spot.difficulty}</p>
        </div>
    `;
}

function closeModal() {
    elements.modal.classList.add('hidden');
}

// Close modal on backdrop click
elements.modal.addEventListener('click', (e) => {
    if (e.target === elements.modal) {
        closeModal();
    }
});

// Close modal on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal();
    }
});

// ============ Region Filter ============
document.querySelectorAll('.region-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        // Update active state
        document.querySelectorAll('.region-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        currentRegion = btn.dataset.region;
        await loadRankings();
    });
});

// ============ Refresh Button ============
elements.refreshBtn.addEventListener('click', async () => {
    elements.refreshBtn.classList.add('loading');

    try {
        await forceRefresh();
        // Wait a moment for the refresh to complete
        await new Promise(resolve => setTimeout(resolve, 2000));
        await loadRankings();
    } catch (error) {
        console.error('Refresh failed:', error);
    } finally {
        elements.refreshBtn.classList.remove('loading');
    }
});

// ============ Notifications ============
async function checkNotificationSupport() {
    if (!('Notification' in window) || !('serviceWorker' in navigator)) {
        return false;
    }

    if (Notification.permission === 'granted') {
        return true;
    }

    if (Notification.permission === 'denied') {
        return false;
    }

    // Show notification banner for first-time users
    const dismissed = localStorage.getItem('notification-banner-dismissed');
    if (!dismissed) {
        elements.notificationBanner.classList.remove('hidden');
    }

    return false;
}

async function enableNotifications() {
    try {
        const permission = await Notification.requestPermission();

        if (permission === 'granted') {
            const registration = await navigator.serviceWorker.ready;

            // Get VAPID public key
            const keyResponse = await fetch(`${API_BASE}/api/notifications/vapid-public-key`);

            if (keyResponse.ok) {
                const { publicKey } = await keyResponse.json();

                // Subscribe to push
                const subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(publicKey)
                });

                // Send subscription to server
                await fetch(`${API_BASE}/api/notifications/subscribe`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(subscription.toJSON())
                });

                console.log('Push notifications enabled');
            }
        }

        elements.notificationBanner.classList.add('hidden');
    } catch (error) {
        console.error('Failed to enable notifications:', error);
    }
}

function dismissNotificationBanner() {
    elements.notificationBanner.classList.add('hidden');
    localStorage.setItem('notification-banner-dismissed', 'true');
}

// Helper function for VAPID key conversion
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

elements.enableNotifications.addEventListener('click', enableNotifications);

// ============ Main Load Function ============
async function loadRankings() {
    showLoading();

    try {
        const data = await fetchRankings(currentRegion);
        renderSpots(data);
        showSpots();
    } catch (error) {
        console.error('Failed to load rankings:', error);
        showError();
    }
}

// ============ Auto Refresh ============
function startAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }

    refreshTimer = setInterval(loadRankings, REFRESH_INTERVAL);
}

// Pause refresh when page is not visible
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
    } else {
        loadRankings();
        startAutoRefresh();
    }
});

// ============ Bottom Navigation ============
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const view = btn.dataset.view;

        // Update active state
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Handle view change (for now, only rankings is implemented)
        if (view === 'rankings') {
            loadRankings();
        } else if (view === 'map') {
            elements.spotsList.innerHTML = `
                <div style="text-align: center; padding: var(--spacing-xl);">
                    <p>תצוגת מפה תהיה זמינה בקרוב</p>
                </div>
            `;
            showSpots();
        } else if (view === 'settings') {
            elements.spotsList.innerHTML = `
                <div style="padding: var(--spacing-lg);">
                    <h2 style="margin-bottom: var(--spacing-lg);">הגדרות</h2>

                    <div style="background: var(--surface); padding: var(--spacing-md); border-radius: var(--border-radius); margin-bottom: var(--spacing-md);">
                        <h3 style="margin-bottom: var(--spacing-sm);">התראות</h3>
                        <p style="color: var(--text-secondary); font-size: var(--font-size-sm);">
                            קבל התראות כשיש תנאים טובים לגלישה
                        </p>
                        <button onclick="enableNotifications()" style="margin-top: var(--spacing-sm); padding: var(--spacing-sm) var(--spacing-md); background: var(--primary); color: white; border: none; border-radius: var(--border-radius-sm); cursor: pointer;">
                            הפעל התראות
                        </button>
                    </div>

                    <div style="background: var(--surface); padding: var(--spacing-md); border-radius: var(--border-radius);">
                        <h3 style="margin-bottom: var(--spacing-sm);">אודות</h3>
                        <p style="color: var(--text-secondary); font-size: var(--font-size-sm);">
                            Kite Forecast Israel v1.0.0<br>
                            תחזית קייטסרפינג לכל הספוטים בישראל
                        </p>
                    </div>
                </div>
            `;
            showSpots();
        }
    });
});

// ============ Initialize ============
document.addEventListener('DOMContentLoaded', async () => {
    await loadRankings();
    startAutoRefresh();
    checkNotificationSupport();
});

// Make functions available globally for onclick handlers
window.openSpotModal = openSpotModal;
window.closeModal = closeModal;
window.loadRankings = loadRankings;
window.dismissNotificationBanner = dismissNotificationBanner;
window.enableNotifications = enableNotifications;
