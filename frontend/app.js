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
let currentWorkoutView = 'today';
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
        'stars': 'צפייה בכוכבים',
        'workout': 'אימון'
    },
    workoutTypes: {
        'strength': 'כוח', 'cardio': 'אירובי', 'hiit': 'HIIT',
        'flexibility': 'גמישות', 'mixed': 'משולב'
    },
    muscleGroups: {
        'chest': 'חזה', 'back': 'גב', 'shoulders': 'כתפיים',
        'biceps': 'ביספס', 'triceps': 'טרייספס', 'legs': 'רגליים',
        'core': 'ליבה', 'glutes': 'ישבן', 'full_body': 'גוף מלא'
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
    const workoutFilter = $('workout-filter');
    if (mode === 'kite') {
        show(subFilter);
        hide(workoutFilter);
    } else if (mode === 'workout') {
        hide(subFilter);
        show(workoutFilter);
    } else {
        hide(subFilter);
        hide(workoutFilter);
    }

    // Load data
    loadData();
}

// ============ Workout View Switching ============
function switchWorkoutView(view) {
    currentWorkoutView = view;
    document.querySelectorAll('.wfilter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.wview === view);
    });
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

// ============ Workout API ============
async function fetchWorkoutToday() {
    const [todayRes, sessionsRes] = await Promise.all([
        fetch('/api/workout/today', {signal: AbortSignal.timeout(60000)}),
        fetch('/api/workout/sessions?limit=5', {signal: AbortSignal.timeout(60000)})
    ]);
    if (!todayRes.ok || !sessionsRes.ok) throw new Error('Failed to fetch');
    const today = await todayRes.json();
    const sessions = await sessionsRes.json();
    return { today, sessions };
}

async function fetchWorkoutProgress() {
    const res = await fetch('/api/workout/progress?days=30', {signal: AbortSignal.timeout(60000)});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function fetchWorkoutSchedule() {
    const res = await fetch('/api/workout/schedule', {signal: AbortSignal.timeout(60000)});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function fetchWeeklySummary() {
    const res = await fetch('/api/workout/summary?week_offset=0', {signal: AbortSignal.timeout(60000)});
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function generateWorkout(type, muscles, duration) {
    const body = { duration_minutes: duration || 30 };
    if (type) body.workout_type = type;
    if (muscles && muscles.length) body.target_muscles = muscles;

    const res = await fetch('/api/workout/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(60000)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function completeSession(sessionId, rating) {
    const body = { rating: rating || null };
    const res = await fetch(`/api/workout/sessions/${sessionId}/complete`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(60000)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function addToSchedule(day, time, type, duration, label) {
    const body = {
        day, time_of_day: time, workout_type: type,
        duration_minutes: duration || 30, label: label || ''
    };
    const res = await fetch('/api/workout/schedule', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(60000)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

async function removeFromSchedule(scheduleId) {
    const res = await fetch(`/api/workout/schedule/${scheduleId}`, {
        method: 'DELETE',
        signal: AbortSignal.timeout(60000)
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return true;
}

// ============ Workout Rendering ============
function renderWorkoutToday(data) {
    const { today, sessions } = data;
    let html = '';

    // Today's scheduled
    if (today.workouts && today.workouts.length > 0) {
        html += '<h3 style="color:var(--text-secondary);margin-bottom:12px">אימונים מתוכננים להיום</h3>';
        today.workouts.forEach(w => {
            const typeHe = translations.workoutTypes[w.workout_type] || w.workout_type;
            html += `
                <div class="schedule-entry" style="margin-bottom:8px">
                    <div class="schedule-info">
                        <div class="schedule-day">${escapeHtml(w.label || typeHe)}</div>
                        <div class="schedule-time">${escapeHtml(w.time_of_day)} - ${w.duration_minutes} דקות</div>
                        <div class="schedule-type">${escapeHtml(typeHe)}</div>
                    </div>
                    <button class="workout-btn small" onclick="quickGenerate('${escapeAttr(w.workout_type)}', ${w.duration_minutes})">התחל</button>
                </div>`;
        });
    } else {
        html += `
            <div style="text-align:center;padding:24px;color:var(--text-secondary)">
                <div style="font-size:2rem;margin-bottom:8px">📅</div>
                <p>אין אימונים מתוכננים להיום</p>
                <button class="workout-btn small" style="margin-top:12px" onclick="switchWorkoutView('generate')">צור אימון חדש</button>
            </div>`;
    }

    // Recent sessions
    if (sessions.sessions && sessions.sessions.length > 0) {
        html += '<h3 style="color:var(--text-secondary);margin:16px 0 12px">אימונים אחרונים</h3>';
        html += '<div class="session-list">';
        sessions.sessions.forEach(s => {
            const typeHe = translations.workoutTypes[s.workout_type] || s.workout_type;
            const dateStr = new Date(s.date).toLocaleDateString('he-IL', {day: 'numeric', month: 'numeric'});
            const statusClass = s.completed ? 'complete' : 'pending';
            const statusText = s.completed ? 'הושלם' : 'ממתין';
            const exerciseCount = (s.exercises || []).length;
            const sessionId = escapeAttr(s.id);

            html += `
                <div class="session-item" onclick="openWorkoutDetail('${sessionId}')">
                    <div class="session-info">
                        <h4>${escapeHtml(typeHe)} - ${dateStr}</h4>
                        <div class="session-meta">${exerciseCount} תרגילים | ${s.duration_minutes} דקות | ~${s.estimated_calories || 0} קלוריות</div>
                    </div>
                    <span class="session-status ${statusClass}">${statusText}</span>
                </div>`;
        });
        html += '</div>';
    }

    return html;
}

function renderWorkoutGenerate() {
    return `
        <div class="workout-form">
            <h3 style="text-align:center;margin-bottom:8px">צור אימון חדש</h3>
            <div class="form-group">
                <label>סוג אימון</label>
                <select id="gen-type">
                    <option value="">אוטומטי</option>
                    <option value="strength">כוח</option>
                    <option value="cardio">אירובי</option>
                    <option value="hiit">HIIT</option>
                    <option value="flexibility">גמישות</option>
                    <option value="mixed">משולב</option>
                </select>
            </div>
            <div class="form-group">
                <label>קבוצת שרירים (אופציונלי)</label>
                <select id="gen-muscles">
                    <option value="">הכל</option>
                    <option value="chest">חזה</option>
                    <option value="back">גב</option>
                    <option value="shoulders">כתפיים</option>
                    <option value="legs">רגליים</option>
                    <option value="core">ליבה</option>
                    <option value="glutes">ישבן</option>
                    <option value="full_body">גוף מלא</option>
                </select>
            </div>
            <div class="form-group">
                <label>משך (דקות)</label>
                <input type="number" id="gen-duration" value="30" min="10" max="90" step="5">
            </div>
            <button class="workout-btn" onclick="doGenerateWorkout()">צור אימון</button>
        </div>
        <div id="generated-workout"></div>`;
}

function renderGeneratedWorkout(workout) {
    const typeHe = translations.workoutTypes[workout.workout_type] || workout.workout_type;
    let html = `
        <div class="workout-card" style="margin-top:16px">
            <div class="card-header">
                <div class="card-info">
                    <h3>${escapeHtml(typeHe)}</h3>
                    <span class="subtitle">${workout.exercises.length} תרגילים</span>
                </div>
                <span class="workout-type-badge ${escapeAttr(workout.workout_type)}">${escapeHtml(typeHe)}</span>
            </div>
            <div class="workout-stats">
                <div class="workout-stat">
                    <span class="stat-value">${workout.duration_minutes}</span>
                    <span class="stat-label">דקות</span>
                </div>
                <div class="workout-stat">
                    <span class="stat-value">${workout.estimated_calories}</span>
                    <span class="stat-label">קלוריות</span>
                </div>
                <div class="workout-stat">
                    <span class="stat-value">${workout.exercises.length}</span>
                    <span class="stat-label">תרגילים</span>
                </div>
            </div>
            <div class="exercise-list">`;

    workout.exercises.forEach(ex => {
        const muscles = (ex.muscle_groups || []).map(m => translations.muscleGroups[m] || m);
        const detail = ex.is_timed ? `${ex.sets}x${ex.reps}s` : `${ex.sets}x${ex.reps}`;
        html += `
            <div class="exercise-item">
                <span class="exercise-name">${escapeHtml(ex.exercise_name_he || ex.exercise_name)}</span>
                <span class="exercise-detail">${detail}</span>
            </div>`;
    });

    html += `</div>
            <div style="padding:12px;display:flex;gap:8px">
                <button class="workout-btn success small" style="flex:1" onclick="doCompleteSession('${escapeAttr(workout.id)}')">סיים אימון</button>
                <button class="workout-btn secondary small" onclick="doGenerateWorkout()">אימון אחר</button>
            </div>
        </div>`;

    return html;
}

function renderWorkoutSchedule(data) {
    const schedule = data.schedule || [];
    let html = '';

    if (schedule.length === 0) {
        html += '<div style="text-align:center;padding:24px;color:var(--text-secondary)"><p>אין אימונים מתוזמנים</p></div>';
    } else {
        schedule.forEach(s => {
            const typeHe = translations.workoutTypes[s.workout_type] || s.workout_type;
            const activeClass = s.active ? '' : ' inactive';
            const schedId = escapeAttr(s.id);
            html += `
                <div class="schedule-entry${activeClass}" style="margin-bottom:8px">
                    <div class="schedule-info">
                        <div class="schedule-day">${escapeHtml(s.day_he || s.day)}</div>
                        <div class="schedule-time">${escapeHtml(s.time_of_day)} - ${s.duration_minutes} דקות</div>
                        <div class="schedule-type">${escapeHtml(s.label || typeHe)}</div>
                    </div>
                    <div class="schedule-actions">
                        <button onclick="doRemoveSchedule('${schedId}')">מחק</button>
                    </div>
                </div>`;
        });
    }

    // Add new schedule form
    html += `
        <div class="workout-form" style="margin-top:16px">
            <h3 style="text-align:center;margin-bottom:8px">הוסף אימון קבוע</h3>
            <div class="form-group">
                <label>יום</label>
                <select id="sched-day">
                    <option value="sunday">ראשון</option>
                    <option value="monday">שני</option>
                    <option value="tuesday">שלישי</option>
                    <option value="wednesday">רביעי</option>
                    <option value="thursday">חמישי</option>
                    <option value="friday">שישי</option>
                    <option value="saturday">שבת</option>
                </select>
            </div>
            <div class="form-group">
                <label>שעה</label>
                <input type="time" id="sched-time" value="07:00">
            </div>
            <div class="form-group">
                <label>סוג אימון</label>
                <select id="sched-type">
                    <option value="strength">כוח</option>
                    <option value="cardio">אירובי</option>
                    <option value="hiit">HIIT</option>
                    <option value="flexibility">גמישות</option>
                    <option value="mixed">משולב</option>
                </select>
            </div>
            <div class="form-group">
                <label>משך (דקות)</label>
                <input type="number" id="sched-duration" value="30" min="10" max="90" step="5">
            </div>
            <div class="form-group">
                <label>תווית (אופציונלי)</label>
                <input type="text" id="sched-label" placeholder="למשל: אימון בוקר">
            </div>
            <button class="workout-btn" onclick="doAddSchedule()">הוסף ללוח זמנים</button>
        </div>`;

    return html;
}

function renderWorkoutProgress(progress) {
    let html = '';

    // Streak
    html += `
        <div class="streak-badge" style="margin-bottom:16px">
            <span class="streak-number">${progress.current_streak}</span>
            <span>ימים ברצף</span>
        </div>`;

    // Stats grid
    html += `
        <div class="progress-section" style="margin-bottom:16px">
            <h3>30 ימים אחרונים</h3>
            <div class="progress-grid">
                <div class="progress-item">
                    <span class="big-number">${progress.total_workouts}</span>
                    <span class="progress-label">אימונים</span>
                </div>
                <div class="progress-item">
                    <span class="big-number">${progress.total_duration_minutes}</span>
                    <span class="progress-label">דקות</span>
                </div>
                <div class="progress-item">
                    <span class="big-number">${progress.total_calories}</span>
                    <span class="progress-label">קלוריות</span>
                </div>
                <div class="progress-item">
                    <span class="big-number">${progress.workouts_per_week_avg}</span>
                    <span class="progress-label">לשבוע</span>
                </div>
            </div>
        </div>`;

    // By type
    if (progress.workouts_by_type && Object.keys(progress.workouts_by_type).length > 0) {
        html += '<div class="progress-section" style="margin-bottom:16px"><h3>לפי סוג</h3>';
        for (const [type, count] of Object.entries(progress.workouts_by_type)) {
            const typeHe = translations.workoutTypes[type] || type;
            html += `
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)">
                    <span>${escapeHtml(typeHe)}</span>
                    <span style="font-weight:600;color:#6c5ce7">${count}</span>
                </div>`;
        }
        html += '</div>';
    }

    // Muscle groups
    if (progress.muscle_groups_frequency && Object.keys(progress.muscle_groups_frequency).length > 0) {
        html += '<div class="progress-section"><h3>קבוצות שרירים</h3>';
        const sorted = Object.entries(progress.muscle_groups_frequency).sort((a, b) => b[1] - a[1]);
        for (const [muscle, count] of sorted) {
            const muscleHe = translations.muscleGroups[muscle] || muscle;
            html += `
                <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border)">
                    <span>${escapeHtml(muscleHe)}</span>
                    <span style="font-weight:600;color:#6c5ce7">${count}</span>
                </div>`;
        }
        html += '</div>';
    }

    return html;
}

function renderWeeklySummary(summary) {
    const s = summary.summary;
    const goalClass = s.goal_met ? 'met' : 'not-met';
    const goalText = s.goal_met ? 'יעד שבועי הושג!' : `${s.goal_progress} אימונים`;

    return `
        <div class="summary-card">
            <div class="summary-header">
                <h3>סיכום שבועי</h3>
                <div class="date-range">${s.week_start} - ${s.week_end}</div>
            </div>
            <div class="summary-body">
                <div class="summary-stats">
                    <div class="summary-stat">
                        <span class="num">${s.total_workouts}</span>
                        <span class="lbl">אימונים</span>
                    </div>
                    <div class="summary-stat">
                        <span class="num">${s.total_duration_minutes}</span>
                        <span class="lbl">דקות</span>
                    </div>
                    <div class="summary-stat">
                        <span class="num">${s.total_calories}</span>
                        <span class="lbl">קלוריות</span>
                    </div>
                </div>
                <div class="summary-goal ${goalClass}">
                    ${escapeHtml(goalText)}
                </div>
                ${s.streak_days > 0 ? `<div class="streak-badge" style="margin-top:12px"><span class="streak-number">${s.streak_days}</span><span>ימים ברצף</span></div>` : ''}
                ${s.workout_days && s.workout_days.length > 0 ?
                    `<div style="text-align:center;margin-top:12px;color:var(--text-secondary);font-size:0.85rem">ימי אימון: ${escapeHtml(s.workout_days.join(', '))}</div>` : ''}
            </div>
        </div>`;
}

// ============ Workout Actions ============
async function doGenerateWorkout() {
    const type = document.getElementById('gen-type')?.value || '';
    const muscles = document.getElementById('gen-muscles')?.value;
    const duration = parseInt(document.getElementById('gen-duration')?.value || '30');

    const target = $('generated-workout') || $('content');
    target.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>יוצר אימון...</p></div>';

    try {
        const workout = await generateWorkout(type || null, muscles ? [muscles] : null, duration);
        target.innerHTML = renderGeneratedWorkout(workout);
    } catch (err) {
        target.innerHTML = '<p style="text-align:center;color:var(--poor)">שגיאה ביצירת אימון</p>';
    }
}

async function quickGenerate(type, duration) {
    const content = $('content');
    content.innerHTML = '<div class="loading-container"><div class="spinner"></div><p>יוצר אימון...</p></div>';
    show(content);

    try {
        const workout = await generateWorkout(type, null, duration);
        content.innerHTML = renderGeneratedWorkout(workout);
    } catch (err) {
        content.innerHTML = '<p style="text-align:center;color:var(--poor)">שגיאה ביצירת אימון</p>';
    }
}

async function doCompleteSession(sessionId) {
    try {
        await completeSession(sessionId, 4);
        loadData();
    } catch (err) {
        console.error('Error completing session:', err);
    }
}

async function doAddSchedule() {
    const day = document.getElementById('sched-day').value;
    const time = document.getElementById('sched-time').value;
    const type = document.getElementById('sched-type').value;
    const duration = parseInt(document.getElementById('sched-duration').value || '30');
    const label = document.getElementById('sched-label').value;

    try {
        await addToSchedule(day, time, type, duration, label);
        loadData();
    } catch (err) {
        console.error('Error adding to schedule:', err);
    }
}

async function doRemoveSchedule(scheduleId) {
    try {
        await removeFromSchedule(scheduleId);
        loadData();
    } catch (err) {
        console.error('Error removing from schedule:', err);
    }
}

function openWorkoutDetail(sessionId) {
    const modal = $('modal');
    const body = $('modal-body');

    show(modal);
    body.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';

    fetch(`/api/workout/sessions/${sessionId}`, {signal: AbortSignal.timeout(60000)})
        .then(res => res.json())
        .then(session => {
            const typeHe = translations.workoutTypes[session.workout_type] || session.workout_type;
            const dateStr = new Date(session.date).toLocaleDateString('he-IL', {weekday: 'long', day: 'numeric', month: 'long'});

            let exHtml = '';
            (session.exercises || []).forEach(ex => {
                const detail = ex.is_timed ? `${ex.sets}x${ex.reps}s` : `${ex.sets}x${ex.reps}`;
                const muscles = (ex.muscle_groups || []).map(m =>
                    `<span class="muscle-tag">${escapeHtml(translations.muscleGroups[m] || m)}</span>`
                ).join('');
                const completedClass = ex.completed ? ' completed' : '';
                exHtml += `
                    <div class="exercise-item${completedClass}">
                        <div style="flex:1">
                            <div>${escapeHtml(ex.exercise_name_he || ex.exercise_name)}</div>
                            <div class="exercise-muscles">${muscles}</div>
                        </div>
                        <span class="exercise-detail">${detail}</span>
                    </div>`;
            });

            const ratingHtml = session.rating ? `<div style="margin-top:8px">דירוג: ${'★'.repeat(session.rating)}${'☆'.repeat(5 - session.rating)}</div>` : '';

            body.innerHTML = `
                <h2>${escapeHtml(typeHe)}</h2>
                <p class="subtitle">${dateStr}</p>
                <div class="workout-stats">
                    <div class="workout-stat">
                        <span class="stat-value">${session.duration_minutes}</span>
                        <span class="stat-label">דקות</span>
                    </div>
                    <div class="workout-stat">
                        <span class="stat-value">${session.estimated_calories || 0}</span>
                        <span class="stat-label">קלוריות</span>
                    </div>
                    <div class="workout-stat">
                        <span class="stat-value">${session.exercises.length}</span>
                        <span class="stat-label">תרגילים</span>
                    </div>
                </div>
                ${ratingHtml}
                <h3 style="margin-top:16px">תרגילים</h3>
                <div class="exercise-list">${exHtml}</div>
                ${!session.completed ? `<button class="workout-btn success" style="width:100%;margin-top:16px" onclick="doCompleteSession('${escapeAttr(session.id)}');closeModal()">סיים אימון</button>` : ''}
            `;
        })
        .catch(() => {
            body.innerHTML = '<p>שגיאה בטעינה</p>';
        });
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
        } else if (currentMode === 'workout') {
            if (currentWorkoutView === 'today') {
                result = await fetchWorkoutToday();
                content.innerHTML = renderWorkoutToday(result);
            } else if (currentWorkoutView === 'generate') {
                content.innerHTML = renderWorkoutGenerate();
                result = { fetched_at: new Date().toISOString() };
            } else if (currentWorkoutView === 'schedule') {
                result = await fetchWorkoutSchedule();
                content.innerHTML = renderWorkoutSchedule(result);
            } else if (currentWorkoutView === 'progress') {
                result = await fetchWorkoutProgress();
                content.innerHTML = renderWorkoutProgress(result);
            } else if (currentWorkoutView === 'summary') {
                result = await fetchWeeklySummary();
                content.innerHTML = renderWeeklySummary(result);
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
window.switchWorkoutView = switchWorkoutView;
window.doGenerateWorkout = doGenerateWorkout;
window.quickGenerate = quickGenerate;
window.doCompleteSession = doCompleteSession;
window.doAddSchedule = doAddSchedule;
window.doRemoveSchedule = doRemoveSchedule;
window.openWorkoutDetail = openWorkoutDetail;
