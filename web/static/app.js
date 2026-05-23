// ─── Estado global ────────────────────────────────────────────────
const state = {
  games: [], liveGames: [], liveScores: {},
  standings: {}, bracket: null, tournaments: [],
  valueBets: [], accuracy: null,
  activeTournament: null, activeTab: "jogos",
  livePollingInterval: null,
  notificationsEnabled: false,
};

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
      showToast("⚽ GOL!", `${game.home_team} ${h} – ${a} ${game.away_team}`, "toast-goal");
      if (state.notificationsEnabled)
        new Notification(`⚽ GOL!`, { body: `${game.home_team} ${h} – ${a} ${game.away_team}` });
    }
    state.liveScores[game.id] = { home: h, away: a };
  }
}

// ─── TABS ─────────────────────────────────────────────────────────
function switchTab(tab) {
  state.activeTab = tab;
  ["jogos", "grupos", "chaveamento", "valor", "simulador"].forEach(t => {
    document.getElementById(`view-${t}`).style.display = t === tab ? "" : "none";
    document.getElementById(`tab-${t}`)?.classList.toggle("active", t === tab);
  });
  document.getElementById("filters").style.display = tab === "jogos" ? "" : "none";
  if (tab === "grupos") renderGroups();
  if (tab === "chaveamento") renderBracket();
  if (tab === "valor") renderValueBets();
  if (tab === "simulador") renderSimulator();
}

// ─── BARRA AO VIVO ────────────────────────────────────────────────
function renderLiveBar() {
  const bar = document.getElementById("live-bar");
  const list = document.getElementById("live-games-list");
  if (!state.liveGames.length) { bar.classList.remove("visible"); return; }
  bar.classList.add("visible");
  list.innerHTML = state.liveGames.map(g => `
    <div class="live-game-item">
      <span class="live-game-teams">${g.home_team} vs ${g.away_team}</span>
      <span>
        <span class="live-game-score">${g.home_score ?? 0} – ${g.away_score ?? 0}</span>
        ${g.minute ? `<span class="live-game-min">${g.minute}'</span>` : ""}
      </span>
    </div>`).join("");
}

// ─── JOGOS ────────────────────────────────────────────────────────
function renderValueBetSection(valueBets) {
  if (!valueBets?.length) return "";
  return `
    <div class="value-bet-section">
      <div class="value-bet-title">💰 Apostas de Valor</div>
      ${valueBets.map(vb => `
        <div class="value-bet-item">
          <div class="value-bet-info">
            <div class="value-bet-label">${vb.label}</div>
            <div class="value-bet-probs">
              Modelo: ${vb.model_prob}% · Mercado: ${vb.implied_prob}% · Casa: ${vb.bookmaker}
            </div>
          </div>
          <div class="value-bet-right">
            <span class="edge-badge">+${vb.edge}% edge</span>
            <span class="odd-badge">${vb.best_odd}</span>
            <a class="bet-cta" href="${vb.affiliate_link}" target="_blank" rel="noopener">Apostar →</a>
          </div>
        </div>`).join("")}
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
          <th style="text-align:center">${game.home_team}</th>
          <th style="text-align:center">Empate</th>
          <th style="text-align:center">${game.away_team}</th>
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
  return `
    <div class="prob-bar-wrapper">
      <div class="prob-labels"><span>${game.home_team}</span><span>Empate</span><span>${game.away_team}</span></div>
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
    </div>`;
}

function renderGame(game) {
  const proj = game.projection;
  const isLive = game.status === "live";
  const hasValue = game.value_bets?.length > 0;
  const groupLabel = game.group_name ? `<span class="game-group">${game.group_name}</span>` : "";
  const valueBadge = hasValue ? `<span class="value-card-badge">💰 VALOR</span>` : "";

  return `
    <div class="game-card" style="${isLive ? "border-color:rgba(248,81,73,.5);" : hasValue ? "border-color:rgba(63,185,80,.4);" : ""}">
      <div class="game-header">
        <div class="game-header-left">
          <span class="game-tournament">${game.tournament} ${groupLabel}${valueBadge}</span>
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
          <div class="team-name">${game.home_team}</div>
          <div class="team-goals">${proj ? `${proj.home_goals_proj.toFixed(1)} gols esperados` : ""}</div>
        </div>
        <div class="vs">VS</div>
        <div class="team away">
          <div class="team-name">${game.away_team}</div>
          <div class="team-goals">${proj ? `${proj.away_goals_proj.toFixed(1)} gols esperados` : ""}</div>
        </div>
      </div>
      ${isLive ? "" : renderProjection(game)}
      ${renderValueBetSection(game.value_bets)}
      ${renderOddsTable(game)}
    </div>`;
}

// ─── ABA VALOR ────────────────────────────────────────────────────
function renderValueBets() {
  const container = document.getElementById("value-bets-list");
  const games = state.valueBets;
  if (!games.length) {
    container.innerHTML = `<div class="empty"><h3>Nenhuma aposta de valor encontrada agora</h3><p>O modelo compara as probabilidades com as odds do mercado. Volte quando houver mais jogos disponíveis.</p></div>`;
    return;
  }
  container.innerHTML = games.map(game => renderGame(game)).join("");
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

function renderSimulator() {
  const container = document.getElementById("simulator-content");
  const data = simLoad();
  const pending = data.bets.filter(b => b.status === "pending");
  const history = data.bets.filter(b => b.status !== "pending").reverse().slice(0, 20);

  const betRow = b => `
    <div class="sim-bet-item">
      <div class="sim-bet-info">
        <div class="sim-bet-game">${b.homeTeam} vs ${b.awayTeam}</div>
        <div class="sim-bet-detail">${b.label} @ ${b.odd} · R$ ${b.amount.toFixed(2)} → R$ ${b.potential.toFixed(2)} possível</div>
      </div>
      <span class="sim-bet-status ${b.status}">${b.status === "pending" ? "Aguardando" : b.status === "won" ? "✅ Ganhou" : "❌ Perdeu"}</span>
    </div>`;

  container.innerHTML = `
    <div class="simulator-panel">
      <div class="simulator-header">
        <div>
          <div class="simulator-title">💰 Simulador de Apostas</div>
          <div style="font-size:12px;color:var(--text-muted);margin-top:3px;">Clique em qualquer odd na aba Jogos para apostar virtualmente</div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
          <div>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:2px;">Saldo Virtual</div>
            <div class="balance-display">R$ ${data.balance.toFixed(2)}</div>
          </div>
          <button onclick="simReset()" class="filter-btn" style="height:fit-content">Resetar</button>
        </div>
      </div>

      ${pending.length ? `
        <div style="margin-bottom:16px;">
          <div class="odds-title" style="margin-bottom:10px;">Apostas Abertas (${pending.length})</div>
          <div class="sim-bets-list">${pending.map(betRow).join("")}</div>
        </div>` : ""}

      ${history.length ? `
        <div>
          <div class="odds-title" style="margin-bottom:10px;">Histórico</div>
          <div class="sim-bets-list">${history.map(betRow).join("")}</div>
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
          <td><div class="team-cell">${t.live ? `<span class="team-live-dot"></span>` : ""}${t.team}</div></td>
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
      return `
        <div class="bracket-game">
          <div class="bracket-game-inner">
            <div class="bracket-team">
              <span class="bracket-team-name ${isTbd ? "tbd" : ""}">${game.home_team}</span>
              <span class="bracket-score ${hWin ? "winner" : ""}">${game.home_score ?? ""}</span>
            </div>
            <div class="bracket-team">
              <span class="bracket-team-name ${isTbd ? "tbd" : ""}">${game.away_team}</span>
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
    document.getElementById("last-update").textContent = "Atualizado: " + new Date().toLocaleTimeString("pt-BR");
    // Notifica value bets novos
    if (valueBets.length > 0) {
      const topEdge = valueBets[0].value_bets[0];
      showToast("💰 Aposta de valor!", `${valueBets[0].home_team} vs ${valueBets[0].away_team} — ${topEdge.label} @ ${topEdge.best_odd} (+${topEdge.edge}% edge)`, "");
    }
  } catch (e) {
    document.getElementById("games").innerHTML = `<div class="empty"><h3>Erro</h3><p>${e.message}</p></div>`;
    return;
  }
  renderLiveBar(); renderFilters(); renderGames();
  if (state.activeTab === "grupos") renderGroups();
  if (state.activeTab === "chaveamento") renderBracket();
  if (state.activeTab === "valor") renderValueBets();
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
      renderLiveBar(); renderGames();
      if (state.activeTab === "grupos") renderGroups();
      if (state.activeTab === "chaveamento") renderBracket();
      if (state.activeTab === "valor") renderValueBets();
    } catch {}
  }, 30_000);
}

// ─── INIT ─────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  await requestNotifications();
  await loadAll();
  startLivePolling();
});
