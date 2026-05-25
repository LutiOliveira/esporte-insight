// ─── FLAGS ────────────────────────────────────────────────────────
const FLAGS = {
  "Mexico": "🇲🇽",
  "South Africa": "🇿🇦",
  "Jamaica": "🇯🇲",
  "Honduras": "🇭🇳",
  "USA": "🇺🇸",
  "Panama": "🇵🇦",
  "Ecuador": "🇪🇨",
  "New Zealand": "🇳🇿",
  "Canada": "🇨🇦",
  "Morocco": "🇲🇦",
  "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
  "Haiti": "🇭🇹",
  "Brazil": "🇧🇷",
  "Algeria": "🇩🇿",
  "Ivory Coast": "🇨🇮",
  "DR Congo": "🇨🇩",
  "Argentina": "🇦🇷",
  "Chile": "🇨🇱",
  "Japan": "🇯🇵",
  "Norway": "🇳🇴",
  "Spain": "🇪🇸",
  "Portugal": "🇵🇹",
  "Uruguay": "🇺🇾",
  "Turkey": "🇹🇷",
  "France": "🇫🇷",
  "Netherlands": "🇳🇱",
  "Colombia": "🇨🇴",
  "Australia": "🇦🇺",
  "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
  "Switzerland": "🇨🇭",
  "Paraguay": "🇵🇾",
  "Iran": "🇮🇷",
  "Germany": "🇩🇪",
  "Belgium": "🇧🇪",
  "South Korea": "🇰🇷",
  "Sweden": "🇸🇪",
  "Qatar": "🇶🇦",
  "Croatia": "🇭🇷",
  "Saudi Arabia": "🇸🇦",
  "Tunisia": "🇹🇳",
  "Ghana": "🇬🇭",
  "Senegal": "🇸🇳",
  "Egypt": "🇪🇬",
  "Cape Verde": "🇨🇻",
  "Austria": "🇦🇹",
  "Bosnia & Herzegovina": "🇧🇦",
  "Czech Republic": "🇨🇿",
  "Uzbekistan": "🇺🇿",
};

function flag(team) {
  return FLAGS[team] || "";
}

// ─── Estado global ────────────────────────────────────────────────
const state = {
  games: [], liveGames: [], liveScores: {},
  standings: {}, bracket: null, tournaments: [],
  valueBets: [], accuracy: null,
  activeTournament: null, activeTab: "jogos",
  livePollingInterval: null,
  notificationsEnabled: false,
  ranking: [],
  topEdgeGameId: null,
};

// Set de jogos já notificados (15min antes)
const notifiedGames = new Set();

// ─── API ──────────────────────────────────────────────────────────
async function apiFetch(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function formatDateTime(iso) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
    timeZone: "America/Manaus",
  });
}
function bestOdd(odds, field) { return Math.max(...odds.map(o => o[field])); }

// ─── TEMA ─────────────────────────────────────────────────────────
function toggleTheme() {
  const isLight = document.documentElement.classList.toggle("light");
  document.getElementById("btn-theme").textContent = isLight ? "☀️" : "🌙";
  localStorage.setItem("esporte_theme", isLight ? "light" : "dark");
}

function initTheme() {
  const saved = localStorage.getItem("esporte_theme");
  if (saved === "light") {
    document.documentElement.classList.add("light");
    const btn = document.getElementById("btn-theme");
    if (btn) btn.textContent = "☀️";
  }
}

// ─── NOTIFICAÇÕES ─────────────────────────────────────────────────
async function requestNotifications() {
  if (!("Notification" in window)) return;
  if (Notification.permission === "granted") { state.notificationsEnabled = true; return; }
  if (Notification.permission !== "denied") {
    state.notificationsEnabled = (await Notification.requestPermission()) === "granted";
  }
}

function showToast(title, body, cssClass = "") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${cssClass}`;
  el.innerHTML = `<div class="toast-title">${title}</div><div class="toast-body">${body}</div>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 6000);
}

function detectGoals(newLive) {
  for (const game of newLive) {
    const prev = state.liveScores[game.id];
    const h = game.home_score ?? 0, a = game.away_score ?? 0;
    if (prev && (h > prev.home || a > prev.away)) {
      showToast("⚽ GOL!", `${flag(game.home_team)}${game.home_team} ${h} – ${a} ${game.away_team}${flag(game.away_team)}`, "toast-goal");
      if (state.notificationsEnabled)
        new Notification(`⚽ GOL!`, { body: `${game.home_team} ${h} – ${a} ${game.away_team}` });
    }
    state.liveScores[game.id] = { home: h, away: a };
  }
}

// ─── NOTIFICAÇÃO 15 MIN ANTES ─────────────────────────────────────
function checkUpcomingGameNotifications(games) {
  const now = Date.now();
  const in16min = now + 16 * 60 * 1000;
  const in14min = now + 14 * 60 * 1000;

  for (const game of games) {
    if (game.status !== "upcoming") continue;
    const startMs = new Date(game.start_time).getTime();
    if (notifiedGames.has(game.id)) continue;
    if (startMs >= in14min && startMs <= in16min) {
      notifiedGames.add(game.id);
      const hf = flag(game.home_team);
      const af = flag(game.away_team);
      showToast("⏰ Vai começar!", `${hf}${game.home_team} vs ${game.away_team}${af} — em 15 min`, "");
      if (state.notificationsEnabled) {
        new Notification("⏰ Vai começar!", {
          body: `${game.home_team} vs ${game.away_team} — em 15 min`,
        });
      }
    }
  }
}

// ─── TABS ─────────────────────────────────────────────────────────
const ALL_TABS = ["jogos", "grupos", "chaveamento", "valor", "simulador", "ranking", "analytics"];

function switchTab(tab) {
  state.activeTab = tab;
  ALL_TABS.forEach(t => {
    document.getElementById(`view-${t}`).style.display = t === tab ? "" : "none";
    document.getElementById(`tab-${t}`)?.classList.toggle("active", t === tab);
  });
  document.getElementById("filters").style.display = tab === "jogos" ? "" : "none";
  if (tab === "grupos") renderGroups();
  if (tab === "chaveamento") renderBracket();
  if (tab === "valor") { initBankroll(); renderValueBets(); loadTipDay(); }
  if (tab === "simulador") renderSimulator();
  if (tab === "ranking") loadRanking();
  if (tab === "analytics") loadAnalytics();
}

// ─── BARRA AO VIVO ────────────────────────────────────────────────
function renderLiveBar() {
  const bar = document.getElementById("live-bar");
  const list = document.getElementById("live-games-list");
  if (!state.liveGames.length) { bar.classList.remove("visible"); return; }
  bar.classList.add("visible");
  list.innerHTML = state.liveGames.map(g => `
    <div class="live-game-item">
      <span class="live-game-teams">${flag(g.home_team)}${g.home_team} vs ${g.away_team}${flag(g.away_team)}</span>
      <span>
        <span class="live-game-score">${g.home_score ?? 0} – ${g.away_score ?? 0}</span>
        ${g.minute ? `<span class="live-game-min">${g.minute}'</span>` : ""}
      </span>
    </div>`).join("");
}

// ─── LIVE COUNT BADGE ─────────────────────────────────────────────
function updateLiveTabBadge() {
  const tab = document.getElementById("tab-jogos");
  const count = state.liveGames.length;
  // Remove old badge if any
  const old = tab.querySelector(".live-count-badge");
  if (old) old.remove();
  if (count > 0) {
    const badge = document.createElement("span");
    badge.className = "live-count-badge";
    badge.textContent = count;
    tab.appendChild(badge);
  }
}

// ─── COUNTDOWN ────────────────────────────────────────────────────
let _countdownInterval = null;

function renderCountdown() {
  const container = document.getElementById("countdown-container");
  if (!container) return;

  const all = [...state.liveGames, ...state.games];
  const upcoming = all.filter(g => g.status === "upcoming").sort((a, b) =>
    new Date(a.start_time) - new Date(b.start_time)
  );

  if (!upcoming.length) {
    container.innerHTML = "";
    if (_countdownInterval) { clearInterval(_countdownInterval); _countdownInterval = null; }
    return;
  }

  const next = upcoming[0];
  const hf = flag(next.home_team);
  const af = flag(next.away_team);

  function tick() {
    const now = Date.now();
    const diff = new Date(next.start_time).getTime() - now;
    if (diff <= 0) {
      container.innerHTML = "";
      if (_countdownInterval) { clearInterval(_countdownInterval); _countdownInterval = null; }
      return;
    }
    const totalSec = Math.floor(diff / 1000);
    const d = Math.floor(totalSec / 86400);
    const h = Math.floor((totalSec % 86400) / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    const parts = [];
    if (d > 0) parts.push(`${d}d`);
    if (h > 0 || d > 0) parts.push(`${h}h`);
    if (d === 0) parts.push(`${String(m).padStart(2,"0")}min`);
    if (d === 0 && h === 0) parts.push(`${String(s).padStart(2,"0")}s`);
    const timeStr = parts.join(" ");

    container.innerHTML = `
      <div class="countdown-banner">
        ⚽ Próximo: ${hf}${next.home_team} vs ${af}${next.away_team}
        — em <span class="countdown-time">${timeStr}</span>
      </div>`;
  }

  tick();
  if (_countdownInterval) clearInterval(_countdownInterval);
  _countdownInterval = setInterval(tick, 1000);
}

// ─── JOGOS ────────────────────────────────────────────────────────
function renderValueBetSection(valueBets) {
  if (!valueBets?.length) return "";
  const bankroll = getBankroll();
  return `
    <div class="value-bet-section">
      <div class="value-bet-title">💰 Apostas de Valor</div>
      ${valueBets.map(vb => {
        const qKellyR = bankroll * (vb.quarter_kelly_pct || 0) / 100;
        const fKellyR = bankroll * (vb.kelly_pct || 0) / 100;
        const edgeQualityBadge = vb.is_real_edge
          ? `<span class="real-edge-badge" title="Modelo Elo independente">✅ Edge real</span>`
          : `<span class="est-edge-badge" title="Modelo circular — use com cautela">⚠️ Estimado</span>`;
        const kellyBadge = (vb.quarter_kelly_pct != null && vb.quarter_kelly_pct > 0)
          ? `<span class="kelly-badge">🎯 ¼Kelly: ${vb.quarter_kelly_pct}% = <span class="kelly-amount" data-pct="${vb.quarter_kelly_pct}">R$ ${qKellyR.toFixed(2)}</span> <span style="opacity:.6">(Full: ${vb.kelly_pct}%)</span></span>`
          : "";
        return `
        <div class="value-bet-item">
          <div class="value-bet-info">
            <div class="value-bet-label">${vb.label}</div>
            <div class="value-bet-probs">
              Modelo: ${vb.model_prob}% · Mercado: ${vb.implied_prob}% · Casa: ${vb.bookmaker}
            </div>
          </div>
          <div class="value-bet-right">
            <span class="edge-badge">+${vb.edge}% edge</span>
            ${edgeQualityBadge}${kellyBadge}
            <span class="odd-badge">${vb.best_odd}</span>
            <a class="bet-cta" href="${vb.affiliate_link}" target="_blank" rel="noopener">Apostar →</a>
          </div>
        </div>`;
      }).join("")}
    </div>`;
}

function renderOUTable(game) {
  const ou = game.ou_projections;
  if (!ou) return "";
  const lines = ["0.5", "1.5", "2.5", "3.5"];
  return `
    <div class="ou-section">
      <div class="ou-title">📊 Total de Gols — Projeções O/U</div>
      <div class="ou-grid">
        ${lines.map(line => {
          const p = ou[line];
          if (!p) return "";
          const overPct = (p.over * 100).toFixed(0);
          const underPct = (p.under * 100).toFixed(0);
          return `
            <div class="ou-item">
              <div class="ou-line">O/U ${line}</div>
              <div class="ou-probs">
                <span class="ou-over ${p.over > 0.6 ? "ou-hot" : ""}">▲ Over: ${overPct}%</span>
                <span class="ou-under ${p.under > 0.6 ? "ou-hot" : ""}">▼ Under: ${underPct}%</span>
              </div>
            </div>`;
        }).join("")}
      </div>
    </div>`;
}

function renderOddsTable(game) {
  if (!game.odds?.length) return "";
  const bH = bestOdd(game.odds, "home_win");
  const bD = bestOdd(game.odds, "draw");
  const bA = bestOdd(game.odds, "away_win");
  return `
    <div class="odds-section">
      <div class="odds-title">Odds por casa de aposta</div>
      <table class="odds-table">
        <thead><tr>
          <th>Casa</th>
          <th style="text-align:center">${flag(game.home_team)}${game.home_team}</th>
          <th style="text-align:center">Empate</th>
          <th style="text-align:center">${flag(game.away_team)}${game.away_team}</th>
        </tr></thead>
        <tbody>${game.odds.map(o => `
          <tr>
            <td><a href="${o.affiliate_link || '#'}" target="_blank" rel="noopener">${o.bookmaker}</a></td>
            <td class="${o.home_win === bH ? "best-odd" : ""}"
                onclick="openSimBet('${game.id}','${game.home_team}','${game.away_team}','home','${game.home_team}',${o.home_win})" style="cursor:pointer" title="Simular aposta">
              ${o.home_win.toFixed(2)}</td>
            <td class="${o.draw === bD ? "best-odd" : ""}"
                onclick="openSimBet('${game.id}','${game.home_team}','${game.away_team}','draw','Empate',${o.draw})" style="cursor:pointer" title="Simular aposta">
              ${o.draw.toFixed(2)}</td>
            <td class="${o.away_win === bA ? "best-odd" : ""}"
                onclick="openSimBet('${game.id}','${game.home_team}','${game.away_team}','away','${game.away_team}',${o.away_win})" style="cursor:pointer" title="Simular aposta">
              ${o.away_win.toFixed(2)}</td>
          </tr>`).join("")}
        </tbody>
      </table>
      <div style="font-size:11px;color:var(--text-muted);padding:6px 0 0;">
        💡 Clique em qualquer odd para simular uma aposta virtual
      </div>
    </div>`;
}

function renderProjection(game) {
  const p = game.projection;
  if (!p) return "";
  const bttsHtml = (game.btts_yes != null) ? `
    <div class="btts-row">
      <span class="btts-label">⚽ Ambos Marcam</span>
      <span class="btts-yes ${game.btts_yes > 60 ? 'btts-hot' : ''}">Sim: ${game.btts_yes}%</span>
      <span class="btts-sep">·</span>
      <span class="btts-no ${game.btts_no > 60 ? 'btts-hot-no' : ''}">Não: ${game.btts_no}%</span>
    </div>` : "";
  return `
    <div class="prob-bar-wrapper">
      <div class="prob-labels"><span>${flag(game.home_team)}${game.home_team}</span><span>Empate</span><span>${flag(game.away_team)}${game.away_team}</span></div>
      <div class="prob-values">
        <span class="prob-home">${p.home_win_prob}%</span>
        <span class="prob-draw">${p.draw_prob}%</span>
        <span class="prob-away">${p.away_win_prob}%</span>
      </div>
      <div class="prob-bar">
        <div class="prob-bar-home" style="width:${p.home_win_prob}%"></div>
        <div class="prob-bar-draw" style="width:${p.draw_prob}%"></div>
        <div class="prob-bar-away" style="width:${p.away_win_prob}%"></div>
      </div>
    </div>
    <div class="scoreline-badge">
      Placar mais provável: <span class="score">${p.best_scoreline}</span>
      <span class="pct">(${p.scoreline_prob}% de chance)</span>
    </div>
    ${bttsHtml}`;
}

function renderGame(game) {
  const proj = game.projection;
  const isLive = game.status === "live";
  const hasValue = game.value_bets?.length > 0;
  const isTopEdge = game.id === state.topEdgeGameId;
  const groupLabel = game.group_name ? `<span class="game-group">${game.group_name}</span>` : "";
  const valueBadge = hasValue ? `<span class="value-card-badge">💰 VALOR</span>` : "";
  const topEdgeBadge = isTopEdge ? `<span class="top-edge-badge">🔥 TOP EDGE</span>` : "";
  const modelBadge = game.model_type === "elo"
    ? `<span class="model-badge model-elo" title="Modelo Elo independente — edge real">🎯 Elo</span>`
    : `<span class="model-badge model-odds" title="Modelo derivado das odds — edge estimado">📊 Est.</span>`;
  const conf = game.confidence;
  const confBadge = conf ? (() => {
    const s = conf.score;
    const cls = s >= 85 ? "conf-high" : s >= 70 ? "conf-med" : s >= 60 ? "conf-low" : "conf-vlow";
    return `<span class="conf-badge ${cls}" title="Confiança do modelo: ${conf.label} (${s}/100)">🔮 ${conf.label}</span>`;
  })() : "";
  const hf = flag(game.home_team);
  const af = flag(game.away_team);

  return `
    <div class="game-card" style="${isLive ? "border-color:rgba(248,81,73,.5);" : hasValue ? "border-color:rgba(63,185,80,.4);" : ""}">
      <div class="game-header">
        <div class="game-header-left">
          <span class="game-tournament">${game.tournament} ${groupLabel}${valueBadge}${topEdgeBadge}${modelBadge}${confBadge}</span>
        </div>
        <span class="game-time">${formatDateTime(game.start_time)}</span>
      </div>
      ${game.stadium ? `<div class="game-meta"><div class="game-meta-item">📍 <strong>${game.stadium}</strong> — ${game.city}</div></div>` : ""}
      ${game.broadcast ? `<div class="broadcast-tags">${game.broadcast.split("·").map(t => { t=t.trim(); return `<span class="broadcast-tag ${t.includes("Globo")||t.includes("CazéTV")?"highlight":""}">${t}</span>`; }).join("")}</div>` : ""}
      ${isLive ? `
        <div style="padding:8px 16px 0;display:flex;align-items:center;gap:12px;">
          <span class="live-badge"><span class="live-dot"></span> AO VIVO</span>
          <span class="live-score">
            <span class="score-num">${game.home_score ?? 0}</span>
            <span class="score-sep">–</span>
            <span class="score-num">${game.away_score ?? 0}</span>
          </span>
          ${game.minute ? `<span class="live-minute">${game.minute}'</span>` : ""}
        </div>` : ""}
      <div class="game-body">
        <div class="team home">
          <div class="team-name">${hf} ${game.home_team}</div>
          <div class="team-goals">${proj ? `${proj.home_goals_proj.toFixed(1)} gols esperados` : ""}</div>
        </div>
        <div class="vs">VS</div>
        <div class="team away">
          <div class="team-name">${game.away_team} ${af}</div>
          <div class="team-goals">${proj ? `${proj.away_goals_proj.toFixed(1)} gols esperados` : ""}</div>
        </div>
      </div>
      ${isLive ? "" : renderProjection(game)}
      ${isLive ? "" : renderOUTable(game)}
      ${renderValueBetSection(game.value_bets)}
      ${renderOddsTable(game)}
      <div style="padding:4px 16px 8px;display:flex;gap:12px;flex-wrap:wrap;">
        <a href="https://ge.globo.com/busca/?q=${encodeURIComponent(game.home_team)}" target="_blank" class="news-link">📰 Notícias sobre ${game.home_team} →</a>
        <a href="https://ge.globo.com/busca/?q=${encodeURIComponent(game.away_team)}" target="_blank" class="news-link">📰 Notícias sobre ${game.away_team} →</a>
      </div>
    </div>`;
}

// ─── ABA VALOR ────────────────────────────────────────────────────
function applyValorFilters() {
  const minEdge = parseFloat(document.getElementById("filter-min-edge")?.value || 5);
  const edgeDisplay = document.getElementById("filter-edge-display");
  if (edgeDisplay) edgeDisplay.textContent = minEdge + "%";
  const market = document.getElementById("filter-market")?.value || "all";
  const sort = document.getElementById("filter-sort")?.value || "edge";

  let games = [...state.valueBets];

  games = games.map(g => ({
    ...g,
    value_bets: (g.value_bets || []).filter(vb => {
      if (vb.edge < minEdge) return false;
      if (market === "1x2" && vb.market_type === "ou") return false;
      if (market === "ou" && vb.market_type !== "ou") return false;
      return true;
    })
  })).filter(g => g.value_bets.length > 0);

  if (sort === "edge") games.sort((a, b) => Math.max(...b.value_bets.map(v => v.edge)) - Math.max(...a.value_bets.map(v => v.edge)));
  else if (sort === "odd") games.sort((a, b) => Math.max(...b.value_bets.map(v => v.best_odd)) - Math.max(...a.value_bets.map(v => v.best_odd)));
  else if (sort === "kelly") games.sort((a, b) => Math.max(...b.value_bets.map(v => v.kelly_pct || 0)) - Math.max(...a.value_bets.map(v => v.kelly_pct || 0)));
  else if (sort === "time") games.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

  const container = document.getElementById("value-bets-list");
  if (!games.length) {
    container.innerHTML = `<div class="empty"><h3>Nenhuma aposta com edge ≥ ${minEdge}%</h3><p>Reduza o filtro de edge mínimo ou aguarde novos jogos.</p></div>`;
    return;
  }
  container.innerHTML = games.map(game => renderGame(game)).join("");
}

function renderValueBets() {
  applyValorFilters();
}

// ─── TIP DO DIA ───────────────────────────────────────────────────
async function loadTipDay() {
  const container = document.getElementById("tip-day-container");
  if (!container) return;
  try {
    const tip = await apiFetch("/api/tips");
    if (!tip || !tip.label) {
      container.innerHTML = "";
      return;
    }
    const hf = flag(tip.home_team);
    const af = flag(tip.away_team);
    container.innerHTML = `
      <div class="tip-day-section">
        <div>
          <div class="tip-day-label">💡 Tip do Dia</div>
          <div class="tip-day-game">${hf}${tip.home_team} vs ${af}${tip.away_team}</div>
          <div class="tip-day-meta">${tip.label} · Casa: ${tip.bookmaker} · Modelo: ${tip.model_prob}% · Mercado: ${tip.implied_prob}%</div>
        </div>
        <div class="tip-day-odds">
          <span class="tip-day-edge">+${tip.edge}% edge</span>
          <span class="tip-day-odd">${tip.best_odd}</span>
          <a class="bet-cta" href="${tip.affiliate_link}" target="_blank" rel="noopener">Apostar →</a>
        </div>
      </div>`;
  } catch {
    container.innerHTML = "";
  }
}

// ─── MONTE CARLO ─────────────────────────────────────────────────
let _simTab = "tracker"; // "tracker" | "montecarlo"

function switchSimTab(tab) {
  _simTab = tab;
  renderSimulator();
}

function runMonteCarlo() {
  const startBankroll = parseFloat(document.getElementById("mc-bankroll")?.value || "1000");
  const betPct = parseFloat(document.getElementById("mc-bet-pct")?.value || "3") / 100;
  const winRate = parseFloat(document.getElementById("mc-winrate")?.value || "52") / 100;
  const avgOdd = parseFloat(document.getElementById("mc-avg-odd")?.value || "2.10");
  const weeks = parseInt(document.getElementById("mc-weeks")?.value || "20", 10);
  const betsPerWeek = parseInt(document.getElementById("mc-bets-week")?.value || "3", 10);

  const N_SIM = 2000;
  const N_BETS = weeks * betsPerWeek;

  // Simula N_SIM trajetórias
  const allPaths = [];
  for (let s = 0; s < N_SIM; s++) {
    let bal = startBankroll;
    const path = [bal];
    for (let b = 0; b < N_BETS; b++) {
      const stake = bal * betPct;
      if (Math.random() < winRate) {
        bal += stake * (avgOdd - 1);
      } else {
        bal -= stake;
      }
      bal = Math.max(0, bal);
      path.push(bal);
    }
    allPaths.push(path);
  }

  // Calcula percentis para cada passo
  const finalVals = allPaths.map(p => p[N_BETS]);
  finalVals.sort((a, b) => a - b);

  const p5  = finalVals[Math.floor(N_SIM * 0.05)];
  const p25 = finalVals[Math.floor(N_SIM * 0.25)];
  const p50 = finalVals[Math.floor(N_SIM * 0.50)];
  const p75 = finalVals[Math.floor(N_SIM * 0.75)];
  const p95 = finalVals[Math.floor(N_SIM * 0.95)];

  const ruinCount = finalVals.filter(v => v < startBankroll * 0.1).length;
  const doubleCount = finalVals.filter(v => v >= startBankroll * 2).length;

  // Seleciona 5 trajetórias representativas: p5, p25, p50, p75, p95
  function findRepPath(target) {
    return allPaths.reduce((best, path) => {
      return Math.abs(path[N_BETS] - target) < Math.abs(best[N_BETS] - target) ? path : best;
    });
  }
  const paths = [
    { path: findRepPath(p5),  color: "#f85149", label: "P5 (pior 5%)" },
    { path: findRepPath(p25), color: "#e3b341", label: "P25" },
    { path: findRepPath(p50), color: "#58a6ff", label: "Mediana" },
    { path: findRepPath(p75), color: "#3fb950", label: "P75" },
    { path: findRepPath(p95), color: "#a5d6ff", label: "P95 (melhor 5%)" },
  ];

  // Renderiza SVG
  const W = 560, H = 200;
  const maxVal = Math.max(...paths.flatMap(p => p.path)) * 1.05;
  const minVal = 0;

  function toX(i) { return (i / N_BETS) * (W - 40) + 20; }
  function toY(v) { return H - 20 - ((v - minVal) / (maxVal - minVal)) * (H - 30); }

  const polylines = paths.map(({ path, color, label }) => {
    const pts = path.map((v, i) => `${toX(i).toFixed(1)},${toY(v).toFixed(1)}`).join(" ");
    return `<polyline fill="none" stroke="${color}" stroke-width="1.5" stroke-opacity="0.85" points="${pts}"/>`;
  }).join("");

  // Eixo horizontal (semanas)
  const xLabels = [];
  for (let w = 0; w <= weeks; w += Math.max(1, Math.floor(weeks / 5))) {
    const i = w * betsPerWeek;
    xLabels.push(`<text x="${toX(i).toFixed(1)}" y="${H - 4}" fill="var(--text-muted)" font-size="9" text-anchor="middle">${w}s</text>`);
  }

  // Linha de banca inicial
  const y0 = toY(startBankroll).toFixed(1);
  const baselineSvg = `<line x1="20" y1="${y0}" x2="${W - 20}" y2="${y0}" stroke="var(--border)" stroke-width="1" stroke-dasharray="4,3"/>`;

  const svg = `
    <svg viewBox="0 0 ${W} ${H}" style="width:100%;height:${H}px">
      ${baselineSvg}
      ${polylines}
      ${xLabels.join("")}
    </svg>`;

  // Legenda
  const legend = paths.map(p => `
    <div style="display:flex;align-items:center;gap:5px;font-size:11px;">
      <div style="width:16px;height:3px;background:${p.color};border-radius:2px;"></div>
      <span style="color:var(--text-muted)">${p.label}: <strong style="color:${p.color}">R$ ${findRepPath(p === paths[0] ? p5 : p === paths[1] ? p25 : p === paths[2] ? p50 : p === paths[3] ? p75 : p95)[N_BETS].toFixed(0)}</strong></span>
    </div>`).join("");

  const resultEl = document.getElementById("mc-result");
  if (resultEl) resultEl.innerHTML = `
    <div class="mc-chart-wrap">
      ${svg}
      <div class="mc-legend">${legend}</div>
    </div>
    <div class="mc-stats-grid">
      <div class="mc-stat">
        <div class="mc-stat-value" style="color:#3fb950">R$ ${p50.toFixed(0)}</div>
        <div class="mc-stat-label">Mediana (${weeks}sem)</div>
      </div>
      <div class="mc-stat">
        <div class="mc-stat-value" style="color:#f85149">${(ruinCount / N_SIM * 100).toFixed(1)}%</div>
        <div class="mc-stat-label">Risco de ruína (&lt;10%)</div>
      </div>
      <div class="mc-stat">
        <div class="mc-stat-value" style="color:#58a6ff">${(doubleCount / N_SIM * 100).toFixed(1)}%</div>
        <div class="mc-stat-label">Prob. dobrar banca</div>
      </div>
      <div class="mc-stat">
        <div class="mc-stat-value">R$ ${p5.toFixed(0)} – R$ ${p95.toFixed(0)}</div>
        <div class="mc-stat-label">Intervalo P5–P95</div>
      </div>
    </div>
    <div style="font-size:11px;color:var(--text-muted);margin-top:8px;text-align:center">
      ${N_SIM.toLocaleString()} simulações · ${N_BETS} apostas (${weeks} semanas × ${betsPerWeek}/sem)
    </div>`;
}

// ─── SIMULADOR ────────────────────────────────────────────────────
function simLoad() {
  return JSON.parse(localStorage.getItem("esporte_insight_sim") || '{"balance":1000,"bets":[]}');
}
function simSave(data) {
  localStorage.setItem("esporte_insight_sim", JSON.stringify(data));
}

function openSimBet(gameId, homeTeam, awayTeam, outcome, label, odd) {
  switchTab("simulador");
  const amount = prompt(`💰 Simular aposta\n${homeTeam} vs ${awayTeam}\n${label} @ ${odd}\n\nQuantia (R$):`);
  if (!amount || isNaN(parseFloat(amount))) return;
  const val = parseFloat(parseFloat(amount).toFixed(2));
  const data = simLoad();
  if (val > data.balance) { alert("Saldo insuficiente!"); return; }
  data.balance = parseFloat((data.balance - val).toFixed(2));
  data.bets.push({
    id: Date.now(), gameId, homeTeam, awayTeam,
    outcome, label, odd, amount: val,
    potential: parseFloat((val * odd).toFixed(2)),
    status: "pending",
    placedAt: new Date().toISOString(),
  });
  simSave(data);
  renderSimulator();
  showToast("✅ Aposta simulada!", `${label} @ ${odd} — R$ ${val.toFixed(2)}`, "");
}

function simReset() {
  if (!confirm("Resetar simulador? Volta para R$ 1.000")) return;
  simSave({ balance: 1000, bets: [] });
  renderSimulator();
}

function simSettle(betId, result) {
  const data = simLoad();
  const bet = data.bets.find(b => String(b.id) === String(betId));
  if (!bet) return;
  bet.status = result;
  if (result === "won") {
    data.balance = parseFloat((data.balance + bet.potential).toFixed(2));
  }
  simSave(data);
  renderSimulator();
  showToast(
    result === "won" ? "✅ Aposta ganha!" : "❌ Aposta perdida",
    `${bet.label} @ ${bet.odd}${result === "won" ? ` — +R$ ${(bet.potential - bet.amount).toFixed(2)}` : ""}`,
    result === "won" ? "toast-goal" : ""
  );
}

function renderSimulator() {
  const container = document.getElementById("simulator-content");
  const data = simLoad();
  const pending = data.bets.filter(b => b.status === "pending");
  const settled = data.bets.filter(b => b.status !== "pending");
  const won = settled.filter(b => b.status === "won");

  // Métricas
  const totalStaked = settled.reduce((s, b) => s + b.amount, 0);
  const totalReturn = won.reduce((s, b) => s + b.potential, 0);
  const profit = totalReturn - totalStaked;
  const roi = totalStaked > 0 ? (profit / totalStaked * 100) : 0;
  const winRate = settled.length > 0 ? (won.length / settled.length * 100) : 0;
  const avgOdd = settled.length > 0 ? settled.reduce((s, b) => s + b.odd, 0) / settled.length : 0;
  const startingBalance = 1000;
  const currentBalance = data.balance;

  // Curva de lucro (últimos 20 settled)
  const recentSettled = settled.slice(-20);
  let runningProfit = 0;
  const profitPoints = recentSettled.map(b => {
    runningProfit += (b.status === "won" ? b.potential - b.amount : -b.amount);
    return runningProfit;
  });
  const maxAbs = Math.max(...profitPoints.map(Math.abs), 1);
  const sparkline = profitPoints.length > 1 ? `
    <svg width="100%" height="48" viewBox="0 0 ${profitPoints.length * 12} 48" preserveAspectRatio="none" style="display:block">
      <polyline
        fill="none"
        stroke="${profit >= 0 ? "#3fb950" : "#f85149"}"
        stroke-width="2"
        points="${profitPoints.map((p, i) => `${i * 12 + 6},${24 - (p / maxAbs) * 20}`).join(" ")}"
      />
      <line x1="0" y1="24" x2="${profitPoints.length * 12}" y2="24" stroke="var(--border)" stroke-width="1" stroke-dasharray="3,3"/>
    </svg>` : "";

  // Streak atual
  let streak = 0;
  let streakType = "";
  for (let i = settled.length - 1; i >= 0; i--) {
    if (i === settled.length - 1) { streakType = settled[i].status; streak = 1; }
    else if (settled[i].status === streakType) streak++;
    else break;
  }
  const streakLabel = streakType === "won"
    ? `🔥 ${streak} vitória${streak > 1 ? "s" : ""} seguida${streak > 1 ? "s" : ""}`
    : streakType === "lost"
    ? `❄️ ${streak} derrota${streak > 1 ? "s" : ""} seguida${streak > 1 ? "s" : ""}`
    : "";

  const betRow = b => `
    <div class="sim-bet-item">
      <div class="sim-bet-info">
        <div class="sim-bet-game">${flag(b.homeTeam)}${b.homeTeam} vs ${b.awayTeam}${flag(b.awayTeam)}</div>
        <div class="sim-bet-detail">${b.label} @ ${b.odd} · R$ ${b.amount.toFixed(2)}
          ${b.status === "won" ? ` → <span style="color:#3fb950">+R$ ${(b.potential - b.amount).toFixed(2)}</span>` :
            b.status === "lost" ? ` → <span style="color:#f85149">-R$ ${b.amount.toFixed(2)}</span>` :
            ` → R$ ${b.potential.toFixed(2)} possível`}
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        ${b.status === "pending" ? `
          <button onclick="simSettle('${b.id}','won')" class="btn-settle won" title="Marcar como ganha">✅</button>
          <button onclick="simSettle('${b.id}','lost')" class="btn-settle lost" title="Marcar como perdida">❌</button>` : ""}
        <span class="sim-bet-status ${b.status}">${b.status === "pending" ? "Aberta" : b.status === "won" ? "✅ Ganhou" : "❌ Perdeu"}</span>
      </div>
    </div>`;

  const mcPanel = `
    <div class="simulator-panel">
      <div class="sim-subtabs">
        <button class="sim-subtab" onclick="switchSimTab('tracker')">📊 Tracker</button>
        <button class="sim-subtab active" onclick="switchSimTab('montecarlo')">🎲 Monte Carlo</button>
      </div>
      <div class="mc-panel">
        <div class="mc-title">🎲 Simulação Monte Carlo — Projeção de Banca</div>
        <div class="mc-subtitle">Simule 2.000 trajetórias com sua estratégia para ver o leque de resultados possíveis</div>
        <div class="mc-inputs">
          <div class="mc-input-group">
            <label>Banca inicial (R$)</label>
            <input type="number" id="mc-bankroll" value="1000" min="100" step="100">
          </div>
          <div class="mc-input-group">
            <label>% da banca por aposta</label>
            <input type="number" id="mc-bet-pct" value="3" min="0.5" max="25" step="0.5">
          </div>
          <div class="mc-input-group">
            <label>Taxa de acerto (%)</label>
            <input type="number" id="mc-winrate" value="52" min="30" max="80" step="1">
          </div>
          <div class="mc-input-group">
            <label>Odd média</label>
            <input type="number" id="mc-avg-odd" value="2.10" min="1.20" max="5" step="0.05">
          </div>
          <div class="mc-input-group">
            <label>Semanas simuladas</label>
            <input type="number" id="mc-weeks" value="20" min="4" max="52" step="4">
          </div>
          <div class="mc-input-group">
            <label>Apostas por semana</label>
            <input type="number" id="mc-bets-week" value="3" min="1" max="14" step="1">
          </div>
        </div>
        <button class="btn-run-mc" onclick="runMonteCarlo()">▶ Simular agora</button>
        <div id="mc-result"></div>
      </div>
    </div>`;

  if (_simTab === "montecarlo") {
    container.innerHTML = mcPanel;
    return;
  }

  container.innerHTML = `
    <div class="simulator-panel">
      <div class="sim-subtabs">
        <button class="sim-subtab active" onclick="switchSimTab('tracker')">📊 Tracker</button>
        <button class="sim-subtab" onclick="switchSimTab('montecarlo')">🎲 Monte Carlo</button>
      </div>
      <!-- Header -->
      <div class="simulator-header">
        <div>
          <div class="simulator-title">📊 Performance Tracker</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:2px;">Clique em qualquer odd nos Jogos para apostar virtualmente</div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
          <div>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:2px;">Saldo Virtual</div>
            <div class="balance-display" style="color:${currentBalance >= startingBalance ? "#3fb950" : "#f85149"}">R$ ${currentBalance.toFixed(2)}</div>
          </div>
          <button onclick="simReset()" class="filter-btn" style="height:fit-content">Resetar</button>
        </div>
      </div>

      <!-- Stats grid -->
      ${settled.length > 0 ? `
      <div class="roi-stats-grid">
        <div class="roi-stat ${profit >= 0 ? "positive" : "negative"}">
          <div class="roi-stat-value">${profit >= 0 ? "+" : ""}R$ ${profit.toFixed(2)}</div>
          <div class="roi-stat-label">Lucro Total</div>
        </div>
        <div class="roi-stat ${roi >= 0 ? "positive" : "negative"}">
          <div class="roi-stat-value">${roi >= 0 ? "+" : ""}${roi.toFixed(1)}%</div>
          <div class="roi-stat-label">ROI</div>
        </div>
        <div class="roi-stat">
          <div class="roi-stat-value">${winRate.toFixed(0)}%</div>
          <div class="roi-stat-label">Acerto ${won.length}/${settled.length}</div>
        </div>
        <div class="roi-stat">
          <div class="roi-stat-value">${avgOdd.toFixed(2)}</div>
          <div class="roi-stat-label">Odd Média</div>
        </div>
      </div>

      ${streakLabel ? `<div class="streak-badge">${streakLabel}</div>` : ""}

      ${profitPoints.length > 1 ? `
        <div class="profit-chart">
          <div class="profit-chart-label">Curva de Lucro (últimas ${profitPoints.length} apostas)</div>
          ${sparkline}
        </div>` : ""}
      ` : ""}

      <!-- Apostas abertas -->
      ${pending.length ? `
        <div style="margin-bottom:16px;">
          <div class="odds-title" style="margin-bottom:8px;">⏳ Apostas Abertas (${pending.length})</div>
          <div class="sim-bets-list">${pending.map(betRow).join("")}</div>
        </div>` : ""}

      <!-- Histórico -->
      ${settled.length ? `
        <div>
          <div class="odds-title" style="margin-bottom:8px;">📋 Histórico (${settled.length} apostas)</div>
          <div class="sim-bets-list">${settled.slice().reverse().slice(0, 15).map(betRow).join("")}</div>
        </div>` :
        (!pending.length ? `<div class="sim-empty">Nenhuma aposta ainda.<br>Vá para a aba <strong>Jogos</strong> e clique em qualquer odd!</div>` : "")}
    </div>`;
}

// ─── GRUPOS ───────────────────────────────────────────────────────
function renderGroups() {
  const container = document.getElementById("groups");
  const standings = state.standings;
  if (!Object.keys(standings).length) {
    container.innerHTML = `<div class="empty"><h3>Nenhum grupo disponível</h3></div>`;
    return;
  }
  container.innerHTML = Object.entries(standings).map(([group, teams]) => {
    const liveCount = teams.filter(t => t.live).length;
    const liveLabel = liveCount ? `<span class="group-live-count"><span class="live-dot" style="display:inline-block;margin-right:4px;"></span>${liveCount} ao vivo</span>` : "";
    const rows = teams.map((t, i) => {
      const isQ = i < 2 && t.P > 0;
      return `
        <tr class="${isQ ? "qualified" : ""}">
          <td class="pos">${i + 1}</td>
          <td><div class="team-cell">${t.live ? `<span class="team-live-dot"></span>` : ""}${flag(t.team)}${t.team}</div></td>
          <td>${t.P}</td><td>${t.W}</td><td>${t.D}</td><td>${t.L}</td>
          <td>${t.GF}</td><td>${t.GA}</td>
          <td>${t.GD > 0 ? "+" : ""}${t.GD}</td>
          <td class="pts-cell" ${t.live ? `style="color:var(--yellow)"` : ""} title="${t.live ? "Provisório" : ""}">${t.Pts}${t.live ? "*" : ""}</td>
        </tr>`;
    }).join("");
    return `
      <div class="group-card">
        <div class="group-header"><span class="group-title">${group}</span>${liveLabel}</div>
        <table class="standings-table">
          <thead><tr><th>#</th><th>Time</th><th>J</th><th>V</th><th>E</th><th>D</th><th>GP</th><th>GC</th><th>SG</th><th>Pts</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }).join("");
}

// ─── CHAVEAMENTO ──────────────────────────────────────────────────
function renderBracket() {
  const container = document.getElementById("bracket");
  if (!state.bracket) { container.innerHTML = `<div class="loading"><span class="spinner"></span> Carregando...</div>`; return; }
  const roundsHtml = state.bracket.rounds.map(round => {
    const gamesHtml = round.games.map(game => {
      const isTbd = game.home_team === "A definir";
      const hWin = game.home_score !== null && game.home_score > game.away_score;
      const aWin = game.away_score !== null && game.away_score > game.home_score;
      const hf = flag(game.home_team);
      const af = flag(game.away_team);
      return `
        <div class="bracket-game">
          <div class="bracket-game-inner">
            <div class="bracket-team">
              <span class="bracket-team-name ${isTbd ? "tbd" : ""}">${hf}${game.home_team}</span>
              <span class="bracket-score ${hWin ? "winner" : ""}">${game.home_score ?? ""}</span>
            </div>
            <div class="bracket-team">
              <span class="bracket-team-name ${isTbd ? "tbd" : ""}">${af}${game.away_team}</span>
              <span class="bracket-score ${aWin ? "winner" : ""}">${game.away_score ?? ""}</span>
            </div>
          </div>
        </div>`;
    }).join("");
    return `<div class="bracket-round"><div class="round-header">${round.name}</div><div class="round-games">${gamesHtml}</div></div>`;
  }).join("");
  container.innerHTML = `<div class="bracket-wrapper"><div class="bracket">${roundsHtml}</div></div>`;
}

// ─── FILTROS / JOGOS ──────────────────────────────────────────────
function renderFilters() {
  const c = document.getElementById("filters");
  c.innerHTML = `<button class="filter-btn ${!state.activeTournament ? "active" : ""}" onclick="setTournament(null)">Todos</button>` +
    state.tournaments.map(t => `<button class="filter-btn ${state.activeTournament === t ? "active" : ""}" onclick="setTournament('${t}')">${t}</button>`).join("");
}

function computeTopEdgeGameId(allGames) {
  let best = null;
  let bestEdge = -Infinity;
  for (const game of allGames) {
    if (game.value_bets?.length) {
      const maxEdge = Math.max(...game.value_bets.map(v => v.edge));
      if (maxEdge > bestEdge) { bestEdge = maxEdge; best = game.id; }
    }
  }
  return best;
}

function renderGames() {
  const container = document.getElementById("games");
  const all = [...state.liveGames, ...state.games];
  const filtered = state.activeTournament ? all.filter(g => g.tournament === state.activeTournament) : all;
  if (!filtered.length) {
    container.innerHTML = `<div class="empty"><h3>Nenhum jogo encontrado</h3></div>`;
    return;
  }
  container.innerHTML = filtered.map(renderGame).join("");
}

function setTournament(t) { state.activeTournament = t; renderFilters(); renderGames(); }

// ─── RANKING ──────────────────────────────────────────────────────
async function loadRanking() {
  const container = document.getElementById("ranking-content");
  container.innerHTML = `<div class="loading"><span class="spinner"></span> Carregando ranking...</div>`;
  try {
    state.ranking = await apiFetch("/api/ranking");
    renderRanking();
  } catch (e) {
    container.innerHTML = `<div class="empty"><h3>Erro ao carregar ranking</h3><p>${e.message}</p></div>`;
  }
}

function renderRanking() {
  const container = document.getElementById("ranking-content");
  const data = state.ranking;
  if (!data.length) {
    container.innerHTML = `<div class="empty"><h3>Nenhum dado de ranking disponível</h3><p>Atualize os dados para calcular.</p></div>`;
    return;
  }

  const maxForce = data.length > 0 ? data[0].force : 1;

  const rows = data.map((t, i) => {
    const pct = maxForce > 0 ? Math.max(0, Math.min(100, (t.force / maxForce) * 100)) : 0;
    const posClass = i < 3 ? "top3" : "";
    return `
      <tr>
        <td class="rank-pos ${posClass}">${i + 1}</td>
        <td><span class="team-flag">${t.flag}</span><span class="rank-team">${t.team}</span></td>
        <td><span class="rank-group">${t.group || "—"}</span></td>
        <td style="color:var(--green);font-weight:600">${t.avg_attack.toFixed(2)}</td>
        <td style="color:var(--red);font-weight:600">${t.avg_defense_conceded.toFixed(2)}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px;">
            <div class="rank-bar-wrap"><div class="rank-bar-fill" style="width:${pct.toFixed(1)}%"></div></div>
            <span style="font-weight:700;font-size:12px;color:var(--blue)">${t.force.toFixed(2)}</span>
          </div>
        </td>
      </tr>`;
  }).join("");

  const teamOptions = data.map(t => `<option value="${t.team}">${t.flag} ${t.team}</option>`).join("");

  container.innerHTML = `
    <div class="ranking-header">
      <h2>🏆 Ranking de Times</h2>
      <span style="font-size:12px;color:var(--text-muted)">${data.length} times analisados</span>
    </div>
    <div class="ranking-table-wrap">
      <table class="ranking-table">
        <thead><tr><th>#</th><th>Time</th><th>Grupo</th><th>Ataque</th><th>Defesa</th><th>Força</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
    <div class="compare-section">
      <div class="compare-title">⚔️ Comparador de Times</div>
      <div class="compare-controls">
        <select id="compare-home">
          <option value="">Selecione o time da casa</option>
          ${teamOptions}
        </select>
        <select id="compare-away">
          <option value="">Selecione o time visitante</option>
          ${teamOptions}
        </select>
        <button class="btn-compare" onclick="runCompare()">Simular confronto</button>
      </div>
      <div id="compare-result"></div>
    </div>`;
}

async function runCompare() {
  const home = document.getElementById("compare-home")?.value;
  const away = document.getElementById("compare-away")?.value;
  const result = document.getElementById("compare-result");
  if (!home || !away) { showToast("Atenção", "Selecione os dois times", ""); return; }
  if (home === away) { showToast("Atenção", "Selecione times diferentes", ""); return; }
  result.innerHTML = `<div class="loading"><span class="spinner"></span> Calculando...</div>`;
  try {
    const data = await apiFetch(`/api/compare?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}`);
    const hf = flag(home);
    const af = flag(away);
    result.innerHTML = `
      <div class="compare-result">
        <div class="compare-result-title">${hf}${home} vs ${af}${away}</div>
        <div class="compare-probs">
          <div class="compare-prob-row">
            <span class="compare-prob-label">Vitória ${home}</span>
            <div class="compare-prob-bar-wrap"><div class="compare-prob-bar home-bar" style="width:${data.home_win_prob}%"></div></div>
            <span class="compare-prob-pct" style="color:var(--green)">${data.home_win_prob}%</span>
          </div>
          <div class="compare-prob-row">
            <span class="compare-prob-label">Empate</span>
            <div class="compare-prob-bar-wrap"><div class="compare-prob-bar draw-bar" style="width:${data.draw_prob}%"></div></div>
            <span class="compare-prob-pct" style="color:var(--yellow)">${data.draw_prob}%</span>
          </div>
          <div class="compare-prob-row">
            <span class="compare-prob-label">Vitória ${away}</span>
            <div class="compare-prob-bar-wrap"><div class="compare-prob-bar away-bar" style="width:${data.away_win_prob}%"></div></div>
            <span class="compare-prob-pct" style="color:var(--red)">${data.away_win_prob}%</span>
          </div>
        </div>
        <div class="compare-scoreline">
          Placar mais provável: <strong>${data.best_scoreline}</strong>
          <span style="color:var(--text-muted)">(${data.scoreline_prob}% de chance)</span>
        </div>
      </div>`;
  } catch (e) {
    result.innerHTML = `<div class="empty"><p>Erro ao comparar: ${e.message}</p></div>`;
  }
}

// ─── ANALYTICS ────────────────────────────────────────────────────
async function loadAnalytics() {
  const container = document.getElementById("analytics-content");
  container.innerHTML = `<div class="loading"><span class="spinner"></span> Carregando analytics...</div>`;
  try {
    const [summary, byRange, calibration] = await Promise.all([
      apiFetch("/api/stats/summary"),
      apiFetch("/api/accuracy/by-range"),
      apiFetch("/api/accuracy/calibration"),
    ]);
    renderAnalytics(summary, byRange, calibration);
  } catch (e) {
    container.innerHTML = `<div class="empty"><h3>Erro ao carregar analytics</h3><p>${e.message}</p></div>`;
  }
}

function renderAnalytics(summary, byRange, calibration) {
  const container = document.getElementById("analytics-content");
  const acc = summary.accuracy;

  // ── Cartões de resumo ──
  const summaryCards = `
    <div class="analytics-summary-grid">
      <div class="analytics-card">
        <div class="analytics-card-value">${summary.upcoming_games}</div>
        <div class="analytics-card-label">Jogos Próximos</div>
      </div>
      <div class="analytics-card ${summary.live_games > 0 ? "card-live" : ""}">
        <div class="analytics-card-value">${summary.live_games}</div>
        <div class="analytics-card-label">Ao Vivo</div>
      </div>
      <div class="analytics-card">
        <div class="analytics-card-value">${summary.games_with_value_bets}</div>
        <div class="analytics-card-label">Value Bets</div>
      </div>
      <div class="analytics-card">
        <div class="analytics-card-value">${summary.elo_model_games}</div>
        <div class="analytics-card-label">Modelo Elo</div>
      </div>
      <div class="analytics-card ${acc.accuracy != null && acc.accuracy >= 60 ? "card-good" : ""}">
        <div class="analytics-card-value">${acc.accuracy != null ? acc.accuracy + "%" : "—"}</div>
        <div class="analytics-card-label">Assertividade</div>
      </div>
      <div class="analytics-card">
        <div class="analytics-card-value">${acc.correct}/${acc.total}</div>
        <div class="analytics-card-label">Acertos/Total</div>
      </div>
    </div>`;

  // ── Tabela por faixa de probabilidade ──
  const hasRangeData = byRange.some(r => r.total > 0);
  const rangeRows = byRange.map(r => {
    const bar = r.accuracy != null ? `<div class="analytics-bar-wrap"><div class="analytics-bar-fill" style="width:${r.accuracy}%;background:${r.accuracy >= 70 ? "var(--green)" : r.accuracy >= 55 ? "var(--yellow)" : "var(--red)"}"></div></div>` : "";
    return `<tr>
      <td>${r.range}</td>
      <td>${r.total}</td>
      <td>${r.correct}</td>
      <td>${r.accuracy != null ? r.accuracy + "%" : "—"}${bar}</td>
    </tr>`;
  }).join("");

  const rangeTable = hasRangeData ? `
    <div class="analytics-section">
      <div class="analytics-section-title">📊 Precisão por Faixa de Probabilidade</div>
      <div class="analytics-section-desc">Verifica se o modelo está calibrado: se o modelo diz 70%, deveria acertar ~70% das vezes.</div>
      <table class="analytics-table">
        <thead><tr><th>Faixa</th><th>Total</th><th>Acertos</th><th>Precisão</th></tr></thead>
        <tbody>${rangeRows}</tbody>
      </table>
    </div>` : `
    <div class="analytics-section">
      <div class="analytics-section-title">📊 Precisão por Faixa de Probabilidade</div>
      <div class="empty" style="padding:24px"><p>Sem predições resolvidas ainda. Aguarde jogos finalizados.</p></div>
    </div>`;

  // ── Curva de calibração SVG ──
  const calWithData = calibration.filter(c => c.total > 0);
  let calibrationSvg = "";
  if (calWithData.length >= 3) {
    const W = 320, H = 160;
    const pad = 30;
    function cx(prob) { return pad + (prob / 100) * (W - pad * 2); }
    function cy(freq) { return H - pad - (freq * (H - pad * 2)); }

    // Linha perfeita
    const perfectLine = `<line x1="${cx(0)}" y1="${cy(0)}" x2="${cx(100)}" y2="${cy(1)}" stroke="var(--border)" stroke-width="1" stroke-dasharray="4,3"/>`;

    // Pontos do modelo (só buckets com dados)
    const modelPoints = calWithData
      .filter(c => c.frequency != null)
      .map(c => `${cx(c.mid_prob).toFixed(1)},${cy(c.frequency).toFixed(1)}`)
      .join(" ");

    const polyline = modelPoints ? `<polyline fill="none" stroke="var(--blue)" stroke-width="2" points="${modelPoints}"/>` : "";
    const dots = calWithData
      .filter(c => c.frequency != null)
      .map(c => `<circle cx="${cx(c.mid_prob).toFixed(1)}" cy="${cy(c.frequency).toFixed(1)}" r="4" fill="var(--blue)" stroke="var(--bg-card)" stroke-width="1"/>`)
      .join("");

    // Eixos
    const xLabels = [0, 25, 50, 75, 100].map(v =>
      `<text x="${cx(v)}" y="${H - 10}" fill="var(--text-muted)" font-size="9" text-anchor="middle">${v}%</text>`
    ).join("");
    const yLabels = [0, 25, 50, 75, 100].map(v =>
      `<text x="6" y="${cy(v / 100).toFixed(1)}" fill="var(--text-muted)" font-size="9" dominant-baseline="middle">${v}</text>`
    ).join("");

    calibrationSvg = `
      <div class="analytics-section">
        <div class="analytics-section-title">🎯 Curva de Calibração</div>
        <div class="analytics-section-desc">Linha tracejada = modelo perfeito. Azul = nosso modelo.</div>
        <svg viewBox="0 0 ${W} ${H}" style="width:100%;max-width:${W}px;height:${H}px;display:block;margin:0 auto">
          ${perfectLine}${polyline}${dots}${xLabels}${yLabels}
        </svg>
      </div>`;
  }

  // ── Informativo sobre modelos ──
  const modelInfo = `
    <div class="analytics-section">
      <div class="analytics-section-title">🔍 Sobre os Modelos</div>
      <div class="analytics-model-info">
        <div class="model-info-item">
          <span class="model-badge model-elo">🎯 Elo</span>
          <div>
            <strong>Modelo Elo (independente)</strong> — usado para jogos da Copa do Mundo 2026.
            As probabilidades são calculadas a partir de ratings Elo das seleções, sem depender das odds do mercado.
            O edge detectado aqui é <em>real</em> — há vantagem matemática genuína sobre as casas.
          </div>
        </div>
        <div class="model-info-item" style="margin-top:12px">
          <span class="model-badge model-odds">📊 Est.</span>
          <div>
            <strong>Modelo Derivado (odds)</strong> — usado para ligas sem ratings Elo.
            As probabilidades são derivadas das próprias odds, criando circularidade.
            O edge calculado é um <em>artefato matemático</em> — use com cautela.
          </div>
        </div>
      </div>
    </div>`;

  container.innerHTML = summaryCards + rangeTable + (calibrationSvg || "") + modelInfo;
}

// ─── ACCURACY / QUOTA ─────────────────────────────────────────────
async function updateHeaderStats() {
  try {
    const [quota, accuracy] = await Promise.all([apiFetch("/api/quota"), apiFetch("/api/accuracy")]);
    state.accuracy = accuracy;
    const quotaEl = document.getElementById("quota-status");
    const accEl = document.getElementById("accuracy-status");
    if (quota.remaining !== null) {
      const cls = quota.remaining < 50 ? "critical" : quota.remaining < 150 ? "low" : "";
      quotaEl.innerHTML = `<span class="quota-badge ${cls}">API: ${quota.remaining} req</span>`;
    }
    if (accuracy.total > 0) {
      accEl.innerHTML = `<span class="accuracy-widget"><span class="accuracy-pct">${accuracy.accuracy}%</span><span class="accuracy-label">assertividade<br>${accuracy.correct}/${accuracy.total} acertos</span></span>`;
    }
  } catch {}
}

// ─── CARGA DE DADOS ───────────────────────────────────────────────
async function loadAll() {
  try {
    const [games, live, standings, tournaments, bracket, valueBets] = await Promise.all([
      apiFetch("/api/games"),
      apiFetch("/api/live"),
      apiFetch("/api/standings"),
      apiFetch("/api/tournaments"),
      apiFetch("/api/bracket"),
      apiFetch("/api/value-bets"),
    ]);
    detectGoals(live);
    state.games = games; state.liveGames = live;
    state.standings = standings; state.tournaments = tournaments;
    state.bracket = bracket; state.valueBets = valueBets;

    // Calcula top edge game id
    const allForEdge = [...live, ...games];
    state.topEdgeGameId = computeTopEdgeGameId(allForEdge);

    document.getElementById("last-update").textContent = "Atualizado: " + new Date().toLocaleTimeString("pt-BR");
    // Notifica value bets novos
    if (valueBets.length > 0) {
      const topEdge = valueBets[0].value_bets[0];
      showToast("💰 Aposta de valor!", `${valueBets[0].home_team} vs ${valueBets[0].away_team} — ${topEdge.label} @ ${topEdge.best_odd} (+${topEdge.edge}% edge)`, "");
    }

    checkUpcomingGameNotifications([...live, ...games]);
  } catch (e) {
    document.getElementById("games").innerHTML = `<div class="empty"><h3>Erro</h3><p>${e.message}</p></div>`;
    return;
  }
  renderLiveBar();
  updateLiveTabBadge();
  renderFilters();
  renderGames();
  renderCountdown();
  if (state.activeTab === "grupos") renderGroups();
  if (state.activeTab === "chaveamento") renderBracket();
  if (state.activeTab === "valor") { renderValueBets(); loadTipDay(); }
  updateHeaderStats();
}

async function refresh() {
  const btn = document.getElementById("btn-refresh");
  btn.disabled = true; btn.textContent = "Atualizando...";
  try { await fetch("/api/refresh", { method: "POST" }); await loadAll(); } catch {}
  btn.disabled = false; btn.textContent = "Atualizar dados";
}

// ─── POLLING (30s) ────────────────────────────────────────────────
function startLivePolling() {
  if (state.livePollingInterval) clearInterval(state.livePollingInterval);
  state.livePollingInterval = setInterval(async () => {
    try {
      const [live, standings, bracket, valueBets] = await Promise.all([
        apiFetch("/api/live"), apiFetch("/api/standings"),
        apiFetch("/api/bracket"), apiFetch("/api/value-bets"),
      ]);
      detectGoals(live);
      state.liveGames = live; state.standings = standings;
      state.bracket = bracket; state.valueBets = valueBets;

      // Recompute top edge
      state.topEdgeGameId = computeTopEdgeGameId([...live, ...state.games]);

      checkUpcomingGameNotifications([...live, ...state.games]);

      renderLiveBar();
      updateLiveTabBadge();
      renderGames();
      renderCountdown();
      if (state.activeTab === "grupos") renderGroups();
      if (state.activeTab === "chaveamento") renderBracket();
      if (state.activeTab === "valor") renderValueBets();
    } catch {}
  }, 30_000);
}

// ─── CALCULADORA BANKROLL ─────────────────────────────────────────
function getBankroll() {
  const input = document.getElementById("bankroll-input");
  const val = parseFloat(input?.value || "1000");
  return isNaN(val) || val <= 0 ? 1000 : val;
}

function updateKellyValues() {
  const bankroll = getBankroll();
  localStorage.setItem("esporte_bankroll", bankroll);
  document.querySelectorAll(".kelly-amount").forEach(el => {
    const pct = parseFloat(el.dataset.pct || "0");
    el.textContent = `R$ ${(bankroll * pct / 100).toFixed(2)}`;
  });
  const info = document.getElementById("bankroll-info");
  if (info) info.textContent = `Banca: R$ ${bankroll.toFixed(2)} — Kelly mostra quanto apostar em cada bet abaixo`;
}

function initBankroll() {
  const saved = localStorage.getItem("esporte_bankroll");
  if (saved) {
    const input = document.getElementById("bankroll-input");
    if (input) { input.value = saved; updateKellyValues(); }
  }
}

// ─── INIT ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  initBankroll();
  await requestNotifications();
  await loadAll();
  startLivePolling();
});
