/**
 * Israel Outdoor Forecast - Unified PWA
 * Modes: Helicopter, Kite, Stars
 */

// ============ State ============
let currentMode = 'kite';
let currentRegion = 'all';
let data = {};

// ============ Translations ============
const translations = {
    regions: {
        'north': 'צפון', 'central': 'מרכז', 'south': 'דרום',
        'eilat': 'אילת', 'kinneret': 'כנרת'
    },
    ratings: {
        'epic': 'מושלם', 'good': 'טוב', 'fair': 'סביר',
        'marginal': 'גבולי', 'poor': 'חלש',
        'Excellent': 'מעולה', 'Good': 'טוב', 'Fair': 'סביר', 'Poor': 'חלש'
    },
    modes: {
        'helicopter': 'טיסות',
        'kite': 'קייט',
        'stars': 'צפייה בכוכבים'
    }
};

// ============ DOM ============
const $ = id => document.getElementById(id);
const show = el => el.classList.remove('hidden');
const hide = el => el.classList.add('hidden');

// ============ Mode Switching ============
function switchMode(mode) {
    currentMode = mode;

    // Update tabs
    document.querySelectorAll('.mode-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.mode === mode);
    });

    // Update header
    $('header-title').textContent = translations.modes[mode] || 'Israel Outdoor';

    // Show/hide region filter (only for kite)
    const subFilter = $('sub-filter');
    if (mode === 'kite') {
        show(subFilter);
    } else {
        hide(subFilter);
    }

    // Load data
    loadData();
}

// ============ API Calls ============
async function fetchKiteRankings() {
    const params = new URLSearchParams({ limit: 50 });
    if (currentRegion !== 'all') params.set('region', currentRegion);
    const res = await fetch(`/api/kite/rankings?${params}`, {signal: AbortSignal.timeout(60000)});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function fetchHelicopterRankings() {
    const res = await fetch('/api/helicopter/rankings', {signal: AbortSignal.timeout(60000)});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function fetchStarsRankings() {
    const res = await fetch('/api/stars/rankings', {signal: AbortSignal.timeout(60000)});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

// ============ Rendering ============
function renderKiteCard(item, rank) {
    const rating = item.overall_rating || 'fair';
    const wave = item.wave_height_m !== null ? `${item.wave_height_m.toFixed(1)}m` : 'שטוח';
    const waveDanger = item.wave_danger ? 'danger' : '';

    return `
        <article class="card kite-card" onclick="openKiteDetail('${item.spot_id}')">
            <div class="card-header">
                <div class="card-info">
                    <span class="rank">#${rank}</span>
                    <h3>${item.spot_name_he}</h3>
                    <span class="subtitle">${item.spot_name}</span>
                    <span class="region">${translations.regions[item.region] || item.region}</span>
                </div>
                <div class="score-badge ${rating}">
                    <span class="score">${Math.round(item.overall_score)}</span>
                    <span class="label">${translations.ratings[rating] || rating}</span>
                </div>
            </div>
            <div class="card-stats">
                <div class="stat"><span class="value">${item.wind_speed_knots.toFixed(0)}</span><span class="unit">קשר</span></div>
                <div class="stat"><span class="value">${item.wind_direction_deg || item.wind_direction}°</span><span class="unit">כיוון</span></div>
                <div class="stat ${waveDanger}"><span class="value">${wave}</span><span class="unit">גלים</span></div>
            </div>
            <div class="card-footer">${item.recommendation}</div>
        </article>
    `;
}

function renderHelicopterCard(item, rank) {
    const flyable = item.is_flyable;
    const scoreClass = item.score >= 70 ? 'good' : item.score >= 50 ? 'fair' : 'poor';
    const sunrise = item.sunrise ? item.sunrise.split('T')[1]?.substring(0,5) : '';
    const sunset = item.sunset ? item.sunset.split('T')[1]?.substring(0,5) : '';

    return `
        <article class="card heli-card" onclick="openHeliDetail('${item.location.id}')">
            <div class="card-header">
                <div class="card-info">
                    <span class="rank">#${rank}</span>
                    <h3>${item.location.name_he}</h3>
                    <span class="subtitle">${item.location.name}</span>
                </div>
                <div class="score-badge ${scoreClass}">
                    <span class="score">${Math.round(item.score)}</span>
                    <span class="label">${flyable ? 'טיסה' : 'לא טיסה'}</span>
                </div>
            </div>
            <div class="card-stats">
                <div class="stat"><span class="value">${item.wind_speed_knots.toFixed(0)}</span><span class="unit">קשר</span></div>
                <div class="stat"><span class="value">${item.wind_direction_deg}°</span><span class="unit">כיוון</span></div>
                <div class="stat"><span class="value">${item.temperature_c.toFixed(0)}°</span><span class="unit">טמפ׳</span></div>
                <div class="stat"><span class="value">${item.cloud_symbol}</span><span class="unit">${item.cloud_cover_percent}%</span></div>
            </div>
            <div class="card-stats">
                <div class="stat"><span class="value">${item.visibility_km.toFixed(0)}</span><span class="unit">ק"מ ראות</span></div>
                <div class="stat"><span class="value">${item.cloud_base_ft}</span><span class="unit">ft בסיס</span></div>
                <div class="stat"><span class="value">🌅${sunrise}</span><span class="unit">🌇${sunset}</span></div>
                <div class="stat"><span class="value">${item.moon_illumination}%</span><span class="unit">ירח</span></div>
            </div>
            ${item.warnings.length ? `<div class="card-footer warning">${item.warnings.join(', ')}</div>` : ''}
        </article>
    `;
}

function renderStarsCard(item, rank) {
    const rating = item.rating;
    const scoreClass = item.score >= 70 ? 'good' : item.score >= 50 ? 'fair' : 'poor';

    return `
        <article class="card stars-card" onclick="openStarsDetail('${item.location.id}')">
            <div class="card-header">
                <div class="card-info">
                    <span class="rank">#${rank}</span>
                    <h3>${item.location.name_he}</h3>
                    <span class="subtitle">${item.location.name}</span>
                </div>
                <div class="score-badge ${scoreClass}">
                    <span class="score">${Math.round(item.score)}</span>
                    <span class="label">${translations.ratings[rating] || rating}</span>
                </div>
            </div>
            <div class="card-stats">
                <div class="stat"><span class="value">${item.moon_illumination.toFixed(0)}%</span><span class="unit">ירח</span></div>
                <div class="stat"><span class="value">${item.cloud_cover.toFixed(0)}%</span><span class="unit">עננות</span></div>
                <div class="stat"><span class="value">${item.is_good_night ? '⭐' : '☁️'}</span><span class="unit">לילה</span></div>
            </div>
            <div class="card-footer">${item.moon_phase}</div>
        </article>
    `;
}

// ============ Load Data ============
async function loadData() {
    const loading = $('loading');
    const error = $('error');
    const content = $('content');

    show(loading);
    hide(error);
    hide(content);
    loading.querySelector('p').textContent = `טוען ${translations.modes[currentMode]}...`;

    try {
        let result;

        if (currentMode === 'kite') {
            result = await fetchKiteRankings();
            data.kite = result;
            if (!result.rankings || result.rankings.length === 0) {
                content.innerHTML = '<p style="text-align:center;color:var(--text-secondary);padding:2rem">אין נתונים זמינים כרגע. נסה שוב בעוד דקה.</p>';
            } else {
                content.innerHTML = result.rankings.map((item, i) => renderKiteCard(item, i + 1)).join('');
            }
        } else if (currentMode === 'helicopter') {
            result = await fetchHelicopterRankings();
            data.helicopter = result;
            if (!result.rankings || result.rankings.length === 0) {
                content.innerHTML = '<p style="text-align:center;color:var(--text-secondary);padding:2rem">אין נתונים זמינים כרגע. נסה שוב בעוד דקה.</p>';
            } else {
                content.innerHTML = result.rankings.map((item, i) => renderHelicopterCard(item, i + 1)).join('');
            }
        } else if (currentMode === 'stars') {
            result = await fetchStarsRankings();
            data.stars = result;
            if (!result.rankings || result.rankings.length === 0) {
                content.innerHTML = '<p style="text-align:center;color:var(--text-secondary);padding:2rem">אין נתונים זמינים כרגע. נסה שוב בעוד דקה.</p>';
            } else {
                content.innerHTML = result.rankings.map((item, i) => renderStarsCard(item, i + 1)).join('');
            }
        }

        hide(loading);
        show(content);

    } catch (err) {
        console.error('Error loading data:', err);
        hide(loading);
        $('error').querySelector('p').textContent = `שגיאה בטעינת ${translations.modes[currentMode]}`;
        show(error);
    }
}

// ============ Detail Modals ============
async function openKiteDetail(spotId) {
    const modal = $('modal');
    const body = $('modal-body');

    show(modal);
    body.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';

    try {
        const res = await fetch(`/api/kite/forecast/${spotId}?hours=12`);
        const forecast = await res.json();

        const hoursHtml = forecast.hourly.map(h => {
            const time = new Date(h.time).toLocaleTimeString('he-IL', {hour: '2-digit', minute: '2-digit'});
            return `<div class="forecast-hour">
                <div class="time">${time}</div>
                <div class="wind">${Math.round(h.wind_speed_knots)}</div>
                <div class="dir">${h.wind_direction || h.wind_direction_cardinal}°</div>
            </div>`;
        }).join('');

        body.innerHTML = `
            <h2>${forecast.spot_name_he}</h2>
            <p class="subtitle">${forecast.spot_name}</p>
            <h3>תחזית 12 שעות (רוח בקשר)</h3>
            <div class="forecast-hours">${hoursHtml}</div>
        `;
    } catch (err) {
        body.innerHTML = '<p>שגיאה בטעינה</p>';
    }
}

async function openHeliDetail(locationId) {
    const modal = $('modal');
    const body = $('modal-body');

    show(modal);
    body.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';

    try {
        const res = await fetch(`/api/helicopter/forecast/${locationId}?days=3`, {signal: AbortSignal.timeout(60000)});
        const forecast = await res.json();

        // Daily summary cards
        const dailyHtml = (forecast.daily || []).map(d => {
            const dayName = new Date(d.date).toLocaleDateString('he-IL', {weekday: 'short', day: 'numeric', month: 'numeric'});
            const sunrise = d.sunrise ? d.sunrise.split('T')[1]?.substring(0,5) : '';
            const sunset = d.sunset ? d.sunset.split('T')[1]?.substring(0,5) : '';
            return `<div class="daily-card">
                <div class="daily-date">${dayName}</div>
                <div class="daily-cloud">${d.cloud_symbol}</div>
                <div class="daily-temp">${d.temp_min?.toFixed(0)}°-${d.temp_max?.toFixed(0)}°</div>
                <div class="daily-wind">💨 ${d.wind_max_knots?.toFixed(0)}kts ${d.wind_direction_dominant}°</div>
                <div class="daily-cloud-base">☁️ בסיס: ${d.cloud_base_avg_ft}ft</div>
                <div class="daily-sun">🌅${sunrise} 🌇${sunset}</div>
                <div class="daily-moon">${d.moon_phase} ${d.moon_illumination}%</div>
                <div class="daily-flyable">${d.flyable_hours}/${d.total_hours} שעות טיסה</div>
            </div>`;
        }).join('');

        // Hourly forecast
        const hoursHtml = forecast.forecast.slice(0, 24).map(h => {
            const time = new Date(h.time).toLocaleTimeString('he-IL', {hour: '2-digit'});
            return `<div class="forecast-hour ${h.is_flyable ? 'good' : 'poor'}">
                <div class="time">${time}</div>
                <div class="wind">${Math.round(h.wind_speed_knots)}kts</div>
                <div class="dir">${h.wind_direction_deg}°</div>
                <div class="cloud">${h.cloud_symbol}</div>
                <div class="temp">${h.temperature_c}°</div>
            </div>`;
        }).join('');

        body.innerHTML = `
            <h2>${forecast.location.name_he}</h2>
            <p class="subtitle">${forecast.location.name}</p>
            <h3>תחזית יומית</h3>
            <div class="daily-cards">${dailyHtml}</div>
            <h3>תחזית שעתית (24 שעות)</h3>
            <div class="forecast-hours">${hoursHtml}</div>
        `;
    } catch (err) {
        body.innerHTML = '<p>שגיאה בטעינה</p>';
    }
}

async function openStarsDetail(locationId) {
    const modal = $('modal');
    const body = $('modal-body');

    show(modal);
    body.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';

    try {
        const res = await fetch(`/api/stars/forecast/${locationId}?days=7`);
        const forecast = await res.json();

        const daysHtml = forecast.forecast.map(d => {
            const dateStr = new Date(d.date).toLocaleDateString('he-IL', {weekday: 'short', day: 'numeric'});
            return `<div class="forecast-day ${d.is_good_night ? 'good' : ''}">
                <div class="date">${dateStr}</div>
                <div class="score">${Math.round(d.score)}</div>
                <div class="moon">${d.moon_illumination.toFixed(0)}% 🌙</div>
                <div class="clouds">${d.cloud_cover_night.toFixed(0)}% ☁️</div>
            </div>`;
        }).join('');

        body.innerHTML = `
            <h2>${forecast.location.name_he}</h2>
            <p class="subtitle">${forecast.location.name}</p>
            <h3>תחזית 7 ימים</h3>
            <div class="forecast-days">${daysHtml}</div>
        `;
    } catch (err) {
        body.innerHTML = '<p>שגיאה בטעינה</p>';
    }
}

function closeModal() {
    hide($('modal'));
}

// Close modal on backdrop click
$('modal').addEventListener('click', e => {
    if (e.target.id === 'modal') closeModal();
});

// ============ Refresh ============
async function refreshData() {
    const btn = $('refresh-btn');
    btn.classList.add('loading');

    try {
        await fetch('/api/refresh', { method: 'POST' });
        await new Promise(r => setTimeout(r, 2000));
        await loadData();
    } finally {
        btn.classList.remove('loading');
    }
}

// ============ Region Filter (Kite) ============
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentRegion = btn.dataset.region;
        loadData();
    });
});

// ============ Init ============
document.addEventListener('DOMContentLoaded', () => {
    switchMode('kite');
});

// Global functions for onclick
window.switchMode = switchMode;
window.refreshData = refreshData;
window.closeModal = closeModal;
window.openKiteDetail = openKiteDetail;
window.openHeliDetail = openHeliDetail;
window.openStarsDetail = openStarsDetail;
