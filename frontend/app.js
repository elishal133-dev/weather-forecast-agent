/**
 * Israel Outdoor Forecast - Unified PWA
 * Modes: Helicopter, Kite, Stars
 */

// ============ Security ============
// Escape HTML to prevent XSS
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

// Escape for use in HTML attributes (like onclick)
function escapeAttr(str) {
    if (str === null || str === undefined) return '';
    return String(str).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

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
    const spotId = escapeAttr(item.spot_id);

    return `
        <article class="card kite-card" onclick="openKiteDetail('${spotId}')">
            <div class="card-header">
                <div class="card-info">
                    <span class="rank">#${rank}</span>
                    <h3>${escapeHtml(item.spot_name_he)}</h3>
                    <span class="subtitle">${escapeHtml(item.spot_name)}</span>
                    <span class="region">${escapeHtml(translations.regions[item.region] || item.region)}</span>
                </div>
                <div class="score-badge ${escapeAttr(rating)}">
                    <span class="score">${Math.round(item.overall_score)}</span>
                    <span class="label">${escapeHtml(translations.ratings[rating] || rating)}</span>
                </div>
            </div>
            <div class="card-stats kite-stats">
                <div class="stat"><span class="value">${item.wind_speed_knots.toFixed(0)}</span><span class="unit">קשר</span></div>
                <div class="stat"><span class="value">${item.wind_gusts_knots.toFixed(0)}</span><span class="unit">משבים</span></div>
                <div class="stat"><span class="value">${item.wind_direction_deg || item.wind_direction}°</span><span class="unit">כיוון</span></div>
                <div class="stat ${waveDanger}"><span class="value">${wave}</span><span class="unit">גלים</span></div>
            </div>
            <div class="card-footer">${escapeHtml(item.recommendation)}</div>
        </article>
    `;
}

function renderHelicopterCard(item, rank) {
    const flyable = item.is_flyable;
    const sunrise = item.sunrise ? item.sunrise.split('T')[1]?.substring(0,5) : '';
    const sunset = item.sunset ? item.sunset.split('T')[1]?.substring(0,5) : '';
    const civilTwilight = item.civil_twilight_end ? item.civil_twilight_end.split('T')[1]?.substring(0,5) : '';
    const moonrise = item.moonrise || '--:--';
    const moonset = item.moonset || '--:--';
    const moonStatusHe = item.moon_status_he || '';
    const locationId = escapeAttr(item.location.id);

    // Wind direction to Hebrew compass
    const windDir = item.wind_direction_deg;
    const compass = windDir >= 337.5 || windDir < 22.5 ? 'צפון' :
                    windDir < 67.5 ? 'צפון-מזרח' :
                    windDir < 112.5 ? 'מזרח' :
                    windDir < 157.5 ? 'דרום-מזרח' :
                    windDir < 202.5 ? 'דרום' :
                    windDir < 247.5 ? 'דרום-מערב' :
                    windDir < 292.5 ? 'מערב' : 'צפון-מערב';

    return `
        <article class="card heli-card" onclick="openHeliDetail('${locationId}')">
            <div class="card-header">
                <div class="card-info">
                    <h3>${escapeHtml(item.location.name_he)}</h3>
                    <span class="subtitle">${escapeHtml(item.location.name)}</span>
                    <span class="flyable-status ${flyable ? 'good' : 'poor'}">${flyable ? '✓ טיסה' : '✗ לא טיסה'}</span>
                </div>
            </div>
            <div class="card-stats heli-stats heli-main-stats">
                <div class="stat cloud-stat">
                    <span class="icon">☁️</span>
                    <span class="value">${escapeHtml(item.cloud_oktas)}</span>
                    <span class="detail">${(item.cloud_base_ft/1000).toFixed(1)}k ft</span>
                </div>
                <div class="stat wind-stat">
                    <span class="icon">💨</span>
                    <span class="value">${item.wind_speed_knots.toFixed(0)} kts</span>
                    <span class="detail">${compass}</span>
                </div>
                <div class="stat temp-stat">
                    <span class="icon">🌡️</span>
                    <span class="value">${item.temperature_c.toFixed(0)}°C</span>
                </div>
                <div class="stat vis-stat">
                    <span class="icon">👁️</span>
                    <span class="value">${item.visibility_km.toFixed(0)} ק"מ</span>
                </div>
            </div>
            <div class="card-stats heli-stats heli-time-stats">
                <div class="stat sun-stat">
                    <span class="label">שמש</span>
                    <span class="times">🌅 ${escapeHtml(sunrise)} → 🌇 ${escapeHtml(sunset)}</span>
                    ${civilTwilight ? `<span class="twilight">דמדומים עד ${escapeHtml(civilTwilight)}</span>` : ''}
                </div>
                <div class="stat moon-stat">
                    <span class="label">ירח ${item.moon_illumination}%</span>
                    <span class="times">↑ ${escapeHtml(moonrise)} ↓ ${escapeHtml(moonset)}</span>
                    <span class="status">${escapeHtml(moonStatusHe)}</span>
                </div>
            </div>
            ${item.warnings.length ? `<div class="card-footer warning">${escapeHtml(item.warnings.join(', '))}</div>` : ''}
        </article>
    `;
}

function renderStarsCard(item, rank) {
    const rating = item.rating;
    const scoreClass = item.score >= 70 ? 'good' : item.score >= 50 ? 'fair' : 'poor';
    const moonrise = item.moonrise || '--:--';
    const moonset = item.moonset || '--:--';
    const moonStatusIcon = item.moon_status_icon || '🌙';
    const moonStatusHe = item.moon_status_he || '';
    const locationId = escapeAttr(item.location.id);

    return `
        <article class="card stars-card" onclick="openStarsDetail('${locationId}')">
            <div class="card-header">
                <div class="card-info">
                    <span class="rank">#${rank}</span>
                    <h3>${escapeHtml(item.location.name_he)}</h3>
                    <span class="subtitle">${escapeHtml(item.location.name)}</span>
                </div>
                <div class="score-badge ${scoreClass}">
                    <span class="score">${Math.round(item.score)}</span>
                    <span class="label">${escapeHtml(translations.ratings[rating] || rating)}</span>
                </div>
            </div>
            <div class="card-stats stars-stats">
                <div class="stat"><span class="value">${item.moon_illumination.toFixed(0)}%</span><span class="unit">ירח</span></div>
                <div class="stat"><span class="value">${item.cloud_cover.toFixed(0)}%</span><span class="unit">עננות</span></div>
                <div class="stat moon-stat"><span class="value">↑${escapeHtml(moonrise)}</span><span class="unit">זריחה</span></div>
                <div class="stat moon-stat"><span class="value">↓${escapeHtml(moonset)}</span><span class="unit">שקיעה</span></div>
            </div>
            <div class="card-footer">
                <span class="moon-phase">${escapeHtml(item.moon_phase)}</span>
                <span class="moon-status">${escapeHtml(moonStatusIcon)} ${escapeHtml(moonStatusHe)}</span>
            </div>
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

        // Show last updated
        const updateEl = $('last-update');
        const fetchedAt = result?.fetched_at || result?.last_update;
        if (fetchedAt) {
            const t = new Date(fetchedAt).toLocaleTimeString('he-IL', {hour:'2-digit', minute:'2-digit'});
            updateEl.textContent = `עודכן: ${t}`;
            show(updateEl);
        }

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
        const res = await fetch(`/api/kite/forecast/${spotId}?hours=24`, {signal: AbortSignal.timeout(60000)});
        const forecast = await res.json();

        const hoursHtml = forecast.hourly.map(h => {
            const time = new Date(h.time).toLocaleTimeString('he-IL', {hour: '2-digit', minute: '2-digit'});
            const wave = h.wave_height_m != null ? `${h.wave_height_m.toFixed(1)}m` : '-';
            const waveDanger = h.wave_height_m != null && h.wave_height_m > 1.5 ? ' danger' : '';
            return `<div class="forecast-hour">
                <div class="time">${time}</div>
                <div class="wind">${Math.round(h.wind_speed_knots)}kts</div>
                <div class="dir">${h.wind_direction_deg || h.wind_direction}°</div>
                <div class="wave${waveDanger}">${wave}</div>
            </div>`;
        }).join('');

        body.innerHTML = `
            <h2>${forecast.spot_name_he}</h2>
            <p class="subtitle">${forecast.spot_name}</p>
            <h3>תחזית 24 שעות</h3>
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

        // Daily summary cards (no ranking)
        const dailyHtml = (forecast.daily || []).map(d => {
            const dayName = new Date(d.date).toLocaleDateString('he-IL', {weekday: 'short', day: 'numeric', month: 'numeric'});
            const sunrise = d.sunrise ? d.sunrise.split('T')[1]?.substring(0,5) : '';
            const sunset = d.sunset ? d.sunset.split('T')[1]?.substring(0,5) : '';
            const civilTwilight = d.civil_twilight_end ? d.civil_twilight_end.split('T')[1]?.substring(0,5) : '';
            const moonrise = d.moonrise || '--:--';
            const moonset = d.moonset || '--:--';
            const moonStatusIcon = d.moon_status_icon || '🌙';
            const moonStatusHe = d.moon_status_he || '';
            return `<div class="daily-card heli-daily">
                <div class="daily-date">${dayName}</div>
                <div class="daily-flyable">${d.flyable_hours}/${d.total_hours} שעות טיסה</div>
                <div class="daily-weather">
                    <div class="daily-row">☁️ ${d.cloud_oktas} @ ${(d.cloud_base_avg_ft/1000).toFixed(1)}k ft</div>
                    <div class="daily-row">💨 ${d.wind_max_knots?.toFixed(0)} kts</div>
                    <div class="daily-row">🌡️ ${d.temp_min?.toFixed(0)}°-${d.temp_max?.toFixed(0)}°</div>
                </div>
                <div class="daily-times">
                    <div class="sun-times">🌅 ${sunrise} → 🌇 ${sunset}</div>
                    ${civilTwilight ? `<div class="twilight">דמדומים ${civilTwilight}</div>` : ''}
                </div>
                <div class="daily-moon">
                    <div class="moon-times">🌙 ↑${moonrise} ↓${moonset}</div>
                    <div class="moon-info">${d.moon_illumination}% ${moonStatusHe}</div>
                </div>
            </div>`;
        }).join('');

        // 3-hour forecast (filter every 3rd hour)
        const threeHourData = forecast.forecast.filter((_, i) => i % 3 === 0).slice(0, 24);
        const hoursHtml = threeHourData.map(h => {
            const time = new Date(h.time).toLocaleTimeString('he-IL', {hour: '2-digit', minute: '2-digit'});
            return `<div class="forecast-hour heli-forecast ${h.is_flyable ? 'good' : 'poor'}">
                <div class="time">${time}</div>
                <div class="cloud">☁️ ${h.cloud_oktas}</div>
                <div class="wind">💨 ${Math.round(h.wind_speed_knots)}kts</div>
                <div class="temp">🌡️ ${h.temperature_c.toFixed(0)}°</div>
                <div class="vis">👁️ ${h.visibility_km.toFixed(0)}km</div>
            </div>`;
        }).join('');

        body.innerHTML = `
            <h2>${forecast.location.name_he}</h2>
            <p class="subtitle">${forecast.location.name}</p>
            <h3>תחזית יומית</h3>
            <div class="daily-cards">${dailyHtml}</div>
            <h3>תחזית 3 שעות</h3>
            <div class="forecast-hours heli-hours">${hoursHtml}</div>
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
            const dateStr = new Date(d.date).toLocaleDateString('he-IL', {weekday: 'long', day: 'numeric', month: 'numeric'});
            const moonrise = d.moonrise || '--:--';
            const moonset = d.moonset || '--:--';
            const moonStatusIcon = d.moon_status_icon || '🌙';
            const moonStatusHe = d.moon_status_he || '';
            const sunset = d.sunset ? d.sunset.split('T')[1]?.substring(0,5) : '--:--';

            return `<div class="forecast-day stars-forecast ${d.is_good_night ? 'good' : ''}">
                <div class="date">${dateStr}</div>
                <div class="score">${Math.round(d.score)}</div>
                <div class="moon-info">
                    <div class="moon-illum">${d.moon_illumination.toFixed(0)}% 🌙</div>
                    <div class="moon-phase-small">${d.moon_phase}</div>
                </div>
                <div class="moon-times">
                    <span class="moon-rise">↑${moonrise}</span>
                    <span class="moon-set">↓${moonset}</span>
                </div>
                <div class="moon-status-row">${moonStatusIcon} ${moonStatusHe}</div>
                <div class="clouds">${d.cloud_cover_night.toFixed(0)}% ☁️</div>
                <div class="sunset-info">🌇 ${sunset}</div>
            </div>`;
        }).join('');

        body.innerHTML = `
            <h2>${forecast.location.name_he}</h2>
            <p class="subtitle">${forecast.location.name}</p>
            <h3>תחזית 7 ימים</h3>
            <div class="forecast-days stars-days">${daysHtml}</div>
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
