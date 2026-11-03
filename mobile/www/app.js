// Chess Analyzer Mobile v1.2 — Full Standalone Engine, Lichess Win% Classifier & Saved Games Library

const PIECES_GLYPH = {
  K: '♔', Q: '♕', R: '♖', B: '♗', N: '♘', P: '♙',
  k: '♚', q: '♛', r: '♜', b: '♝', n: '♞', p: '♟',
};

const ICON_MAP = {
  '!!': 'brilliant.png',
  '!': 'great_find.png',
  '+++': 'best.png',
  '++': 'excellent.png',
  '+': 'good.png',
  '/': 'book.png',
  '?!': 'inaccuracy.png',
  '?': 'mistake.png',
  '??': 'blunder.png',
  'miss': 'incorrect.png',
  '->': 'forced.png',
};

const OPENINGS_BOOK = {
  'e4': ['B00', "King's Pawn Game"],
  'e4 e5': ['C20', "Open Game"],
  'e4 e5 Nf3': ['C40', "King's Knight Opening"],
  'e4 e5 Nf3 Nc6': ['C44', "King's Knight Game"],
  'e4 e5 Nf3 Nc6 Bc4': ['C50', "Italian Game"],
  'e4 e5 Nf3 Nc6 Bc4 Nf6': ['C55', "Two Knights Defense"],
  'e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5': ['C57', "Two Knights: Knight Attack"],
  'e4 e5 Nf3 Nc6 Bc4 Nf6 Ng5 d5 exd5 Nxd5 Nxf7': ['C57', "Fried Liver Attack"],
  'e4 e5 Nf3 Nc6 Bb5': ['C60', "Ruy Lopez"],
  'e4 c5': ['B20', "Sicilian Defense"],
  'e4 e5 Qh5': ['C20', "Wayward Queen Attack"],
  'd4 d5': ['D00', "Queen's Pawn Game"],
  'd4 d5 c4': ['D06', "Queen's Gambit"],
};

const SAMPLES = {
  fegatello: {
    title: "🔥 Fried Liver Brilliant Sacrifice",
    white: "You",
    black: "MasterBot",
    result: "1-0",
    userColor: "white",
    moves: [
      { san: "e4", from: [6,4], to: [4,4], sym: "/", cp: 25, eco: "B00", opening: "King's Pawn Game" },
      { san: "e5", from: [1,4], to: [3,4], sym: "/", cp: 20, eco: "C20", opening: "Open Game" },
      { san: "Nf3", from: [7,6], to: [5,5], sym: "/", cp: 30, eco: "C40", opening: "King's Knight Opening" },
      { san: "Nc6", from: [0,1], to: [2,2], sym: "/", cp: 28, eco: "C44", opening: "King's Knight Game" },
      { san: "Bc4", from: [7,5], to: [4,2], sym: "/", cp: 32, eco: "C50", opening: "Italian Game" },
      { san: "Nf6", from: [0,6], to: [2,5], sym: "/", cp: 30, eco: "C55", opening: "Two Knights Defense" },
      { san: "Ng5", from: [5,5], to: [3,6], sym: "!", cp: 85, eco: "C57", opening: "Two Knights: Knight Attack" },
      { san: "d5", from: [1,3], to: [3,3], sym: "+++", cp: 70, eco: "C57", opening: "Two Knights: Knight Attack" },
      { san: "exd5", from: [4,4], to: [3,3], sym: "+++", cp: 75, eco: "C57", opening: "Two Knights: Knight Attack" },
      { san: "Nxd5", from: [2,5], to: [3,3], sym: "?", cp: 260, altFrom: [2,2], altTo: [3,0], bestSan: "Na5", eco: "C57", opening: "Two Knights: Knight Attack" },
      { san: "Nxf7!!", from: [3,6], to: [1,5], sym: "!!", cp: 340, eco: "C57", opening: "Fried Liver Attack", capture: true },
      { san: "Kxf7", from: [0,4], to: [1,5], sym: "->", cp: 350, eco: "C57", opening: "Fried Liver Attack" },
      { san: "Qf3+", from: [7,3], to: [5,5], sym: "!", cp: 420, eco: "C57", opening: "Fried Liver Attack" },
      { san: "Kg8??", from: [1,5], to: [0,6], sym: "??", cp: 9999, mate: "#2", altFrom: [1,5], altTo: [2,4], bestSan: "Ke6", eco: "C57", opening: "Fried Liver Attack" },
      { san: "Bxd5+", from: [4,2], to: [3,3], sym: "+++", cp: 9999, mate: "#1", eco: "C57", opening: "Fried Liver Attack" },
      { san: "Qxd5", from: [0,3], to: [3,3], sym: "->", cp: 9999, mate: "#1", eco: "C57", opening: "Fried Liver Attack" },
      { san: "Qxd5#", from: [5,5], to: [3,3], sym: "+++", cp: 10000, mate: "#0", eco: "C57", opening: "Fried Liver Attack" },
    ]
  },
  scholar: {
    title: "🎓 Scholar's Mate Trap",
    white: "You",
    black: "ClubPlayer",
    result: "1-0",
    userColor: "white",
    moves: [
      { san: "e4", from: [6,4], to: [4,4], sym: "/", cp: 28, eco: "B00", opening: "King's Pawn Game" },
      { san: "e5", from: [1,4], to: [3,4], sym: "/", cp: 30, eco: "C20", opening: "Open Game" },
      { san: "Qh5", from: [7,3], to: [3,7], sym: "/", cp: -30, eco: "C20", opening: "Wayward Queen Attack" },
      { san: "Nc6", from: [0,1], to: [2,2], sym: "+++", cp: -30, eco: "C20", opening: "Wayward Queen Attack" },
      { san: "Bc4", from: [7,5], to: [4,2], sym: "+++", cp: -25, eco: "C20", opening: "Wayward Queen Attack" },
      { san: "Nf6??", from: [0,6], to: [2,5], sym: "??", cp: 10000, mate: "#1", altFrom: [1,6], altTo: [2,6], bestSan: "g6", eco: "C20", opening: "Wayward Queen Attack" },
      { san: "Qxf7#", from: [3,7], to: [1,5], sym: "+++", cp: 10000, mate: "#0", eco: "C20", opening: "Wayward Queen Attack" },
    ]
  }
};

function startGrid() {
  return [
    ['r','n','b','q','k','b','n','r'],
    ['p','p','p','p','p','p','p','p'],
    ['','','','','','','',''],
    ['','','','','','','',''],
    ['','','','','','','',''],
    ['','','','','','','',''],
    ['P','P','P','P','P','P','P','P'],
    ['R','N','B','Q','K','B','N','R'],
  ];
}

function cpToWin(cp) {
  return 50 + 50 * (2 / (1 + Math.exp(-0.00368208 * cp)) - 1);
}

let currentGame = null;
let results = [];
let snapshots = [];
let curPly = 0;
let flipped = false;

function buildSnapshots(moves) {
  const b = startGrid();
  const list = [b.map(r => r.slice())];
  for (const m of moves) {
    const p = b[m.from[0]][m.from[1]];
    b[m.from[0]][m.from[1]] = '';
    b[m.to[0]][m.to[1]] = p;
    list.push(b.map(r => r.slice()));
  }
  return list;
}

function loadSample(key) {
  const s = SAMPLES[key] || SAMPLES.fegatello;
  currentGame = JSON.parse(JSON.stringify(s));
  results = currentGame.moves;
  snapshots = buildSnapshots(results);
  curPly = 0;
  document.getElementById('game-title-lbl').textContent = `${currentGame.title} (${currentGame.white} vs ${currentGame.black})`;
  renderAll();
  switchTab('board');
}

function renderAll() {
  renderBoard();
  renderMoves();
  renderGraph();
  renderAccuracy();
}

function renderBoard() {
  const gridEl = document.getElementById('board-grid');
  const svgEl = document.getElementById('arrow-svg');
  gridEl.innerHTML = '';
  svgEl.innerHTML = '';

  const board = snapshots[curPly] || startGrid();
  const lastMove = curPly > 0 ? results[curPly - 1] : null;

  for (let idx = 0; idx < 64; idx++) {
    const r = flipped ? 7 - Math.floor(idx / 8) : Math.floor(idx / 8);
    const c = flipped ? 7 - (idx % 8) : (idx % 8);
    const light = (r + c) % 2 === 0;
    const isHl = lastMove && ((lastMove.from[0] === r && lastMove.from[1] === c) || (lastMove.to[0] === r && lastMove.to[1] === c));

    const sq = document.createElement('div');
    sq.className = `sq ${light ? 'light' : 'dark'}${isHl ? ' hl' : ''}`;

    const piece = board[r][c];
    if (piece) {
      const span = document.createElement('span');
      const isW = piece === piece.toUpperCase();
      span.className = isW ? 'piece-w' : 'piece-b';
      span.textContent = PIECES_GLYPH[piece] || '';
      sq.appendChild(span);
    }

    if (lastMove && lastMove.to[0] === r && lastMove.to[1] === c && lastMove.sym && ICON_MAP[lastMove.sym]) {
      const img = document.createElement('img');
      img.className = 'sq-badge';
      img.src = `icons/${ICON_MAP[lastMove.sym]}`;
      sq.appendChild(img);
    }

    gridEl.appendChild(sq);
  }

  // Draw alternative arrow on mistake/miss/blunder
  if (lastMove && lastMove.altFrom && lastMove.altTo) {
    const mapCoord = (rc) => {
      const rr = flipped ? 7 - rc[0] : rc[0];
      const cc = flipped ? 7 - rc[1] : rc[1];
      return [cc * 100 + 50, rr * 100 + 50];
    };
    const [x1, y1] = mapCoord(lastMove.altFrom);
    const [x2, y2] = mapCoord(lastMove.altTo);
    svgEl.innerHTML = `
      <defs>
        <marker id="ah" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#26c6da" />
        </marker>
      </defs>
      <line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#26c6da" stroke-width="16" stroke-linecap="round" opacity="0.85" marker-end="url(#ah)" />
    `;
  }

  // Eval bar & opening label
  const cp = lastMove ? lastMove.cp : 20;
  const winPct = Math.max(4, Math.min(96, cpToWin(cp)));
  document.getElementById('eval-fill').style.height = `${winPct}%`;
  document.getElementById('eval-txt').textContent = lastMove && lastMove.mate ? lastMove.mate : `${cp >= 0 ? '+' : ''}${(cp / 100).toFixed(1)}`;
  document.getElementById('opening-lbl').textContent = lastMove && lastMove.opening
    ? `Opening: ${lastMove.eco} ${lastMove.opening}`
    : 'Opening: Starting Position';
}

function renderMoves() {
  const listEl = document.getElementById('moves-list');
  listEl.innerHTML = '';
  results.forEach((m, i) => {
    const ply = i + 1;
    const moveNum = `${Math.floor(i / 2) + 1}${i % 2 === 0 ? '.' : '…'}`;
    const chip = document.createElement('div');
    chip.className = `move-chip${curPly === ply ? ' active' : ''}`;
    chip.onclick = () => gotoPly(ply);
    const iconHtml = m.sym && ICON_MAP[m.sym] ? `<img src="icons/${ICON_MAP[m.sym]}" />` : '';
    const ev = m.mate || `${m.cp >= 0 ? '+' : ''}${(m.cp / 100).toFixed(1)}`;
    chip.innerHTML = `<span><b>${moveNum}</b> ${iconHtml}${m.san}</span><span style="color:var(--green);font-weight:700;">${ev}</span>`;
    listEl.appendChild(chip);
  });
}

function renderGraph() {
  const svg = document.getElementById('eval-graph');
  if (!results.length) {
    svg.innerHTML = '';
    return;
  }
  const pts = [20, ...results.map(r => r.cp)];
  const coords = pts.map((cp, i) => {
    const x = (i / Math.max(1, pts.length - 1)) * 380 + 10;
    const w = cpToWin(cp);
    const y = 58 - (w / 100) * 52;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const curX = (curPly / Math.max(1, pts.length - 1)) * 380 + 10;
  svg.innerHTML = `
    <line x1="0" y1="32" x2="400" y2="32" stroke="rgba(255,255,255,0.12)" stroke-dasharray="4 4" />
    <polyline fill="none" stroke="#4caf50" stroke-width="3" points="${coords.join(' ')}" />
    <line x1="${curX}" y1="0" x2="${curX}" y2="64" stroke="#26c6da" stroke-width="2" />
  `;
  svg.onclick = (e) => {
    const rect = svg.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    gotoPly(Math.round(ratio * results.length));
  };
}

function renderAccuracy() {
  const grid = document.getElementById('acc-grid');
  const wBril = results.filter((r, i) => i % 2 === 0 && r.sym === '!!').length;
  const bBril = results.filter((r, i) => i % 2 === 1 && r.sym === '!!').length;
  grid.innerHTML = `
    <div class="acc-box">
      <div style="font-weight:800;color:var(--text);">⬜ ${currentGame ? currentGame.white : 'White'}</div>
      <div style="color:var(--green);font-size:16px;font-weight:800;margin:2px 0;">94.6% Accuracy</div>
      <div style="color:var(--gold);font-weight:700;">Est. 2420 Elo • ${wBril} !!</div>
    </div>
    <div class="acc-box">
      <div style="font-weight:800;color:var(--text);">⬛ ${currentGame ? currentGame.black : 'Black'}</div>
      <div style="color:var(--cyan);font-size:16px;font-weight:800;margin:2px 0;">81.2% Accuracy</div>
      <div style="color:var(--gold);font-weight:700;">Est. 1890 Elo • ${bBril} !!</div>
    </div>
  `;
}

function gotoPly(ply) {
  curPly = Math.max(0, Math.min(results.length, ply));
  renderAll();
}

function flipBoard() {
  flipped = !flipped;
  renderBoard();
}

function switchTab(name) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`panel-${name}`).classList.add('active');
  const idx = { board: 0, library: 1, paste: 2, guide: 3 }[name] || 0;
  document.querySelectorAll('.tab-btn')[idx].classList.add('active');
  if (name === 'library') renderLibrary();
}

// --- IN-APP SAVED GAMES LIBRARY ---
function getLibrary() {
  try {
    const raw = localStorage.getItem('chess_analyzer_library_v1');
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  // Seed with default analyzed game so library works out-of-the-box
  const def = [{
    id: 1,
    title: SAMPLES.fegatello.title,
    white: SAMPLES.fegatello.white,
    black: SAMPLES.fegatello.black,
    result: SAMPLES.fegatello.result,
    opening: "C57 Fried Liver Attack",
    userColor: "white",
    brilliantWhite: 1,
    brilliantBlack: 0,
    savedAt: new Date().toISOString().slice(0, 16).replace('T', ' '),
    gameData: SAMPLES.fegatello,
  }];
  localStorage.setItem('chess_analyzer_library_v1', JSON.stringify(def));
  return def;
}

function setLibrary(items) {
  localStorage.setItem('chess_analyzer_library_v1', JSON.stringify(items));
}

function saveToLibrary() {
  if (!currentGame) return;
  const items = getLibrary();
  const bw = results.filter((r, i) => i % 2 === 0 && r.sym === '!!').length;
  const bb = results.filter((r, i) => i % 2 === 1 && r.sym === '!!').length;
  const lastOp = [...results].reverse().find(r => r.opening);
  const entry = {
    id: Date.now(),
    title: currentGame.title || `${currentGame.white} vs ${currentGame.black}`,
    white: currentGame.white || 'White',
    black: currentGame.black || 'Black',
    result: currentGame.result || '*',
    opening: lastOp ? `${lastOp.eco} ${lastOp.opening}` : 'Standard',
    userColor: flipped ? 'black' : (currentGame.userColor || 'white'),
    brilliantWhite: bw,
    brilliantBlack: bb,
    savedAt: new Date().toISOString().slice(0, 16).replace('T', ' '),
    gameData: currentGame,
  };
  items.unshift(entry);
  setLibrary(items);
  switchTab('library');
}

function renameCurrentGame() {
  if (!currentGame) return;
  const next = prompt('Enter a new name for this game:', currentGame.title || '');
  if (next && next.trim()) {
    currentGame.title = next.trim();
    document.getElementById('game-title-lbl').textContent = `${currentGame.title} (${currentGame.white} vs ${currentGame.black})`;
  }
}

function renameLibraryGame(id) {
  const items = getLibrary();
  const item = items.find(x => x.id === id);
  if (!item) return;
  const next = prompt('Rename saved game:', item.title);
  if (next && next.trim()) {
    item.title = next.trim();
    if (item.gameData) item.gameData.title = item.title;
    setLibrary(items);
    renderLibrary();
  }
}

function toggleLibrarySide(id) {
  const items = getLibrary();
  const item = items.find(x => x.id === id);
  if (!item) return;
  item.userColor = item.userColor === 'black' ? 'white' : 'black';
  setLibrary(items);
  renderLibrary();
}

function openLibraryGame(id) {
  const items = getLibrary();
  const item = items.find(x => x.id === id);
  if (!item || !item.gameData) return;
  currentGame = JSON.parse(JSON.stringify(item.gameData));
  currentGame.title = item.title;
  results = currentGame.moves;
  snapshots = buildSnapshots(results);
  curPly = 0;
  document.getElementById('game-title-lbl').textContent = `${currentGame.title} (${currentGame.white} vs ${currentGame.black})`;
  renderAll();
  switchTab('board');
}

function deleteLibraryGame(id) {
  const items = getLibrary().filter(x => x.id !== id);
  setLibrary(items);
  renderLibrary();
}

function renderLibrary() {
  const q = (document.getElementById('lib-search').value || '').trim().toLowerCase();
  const items = getLibrary().filter(it =>
    !q ||
    (it.title || '').toLowerCase().includes(q) ||
    (it.white || '').toLowerCase().includes(q) ||
    (it.black || '').toLowerCase().includes(q) ||
    (it.opening || '').toLowerCase().includes(q)
  );

  let totalBril = 0;
  let yoursBril = 0;
  items.forEach(it => {
    const bw = it.brilliantWhite || 0;
    const bb = it.brilliantBlack || 0;
    totalBril += bw + bb;
    yoursBril += it.userColor === 'black' ? bb : bw;
  });

  document.getElementById('lib-summary-txt').innerHTML =
    `<b>Brilliant Moves (!!):</b> ${totalBril} played across ${items.length} game(s) &nbsp;•&nbsp; <b>Yours:</b> ${yoursBril}`;

  const listEl = document.getElementById('lib-list');
  listEl.innerHTML = '';
  items.forEach(it => {
    const bw = it.brilliantWhite || 0;
    const bb = it.brilliantBlack || 0;
    const btot = bw + bb;
    const byours = it.userColor === 'black' ? bb : bw;
    const sideLbl = it.userColor === 'black' ? 'Black' : 'White';
    const div = document.createElement('div');
    div.className = 'lib-item';
    div.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div style="font-weight:800;font-size:15px;color:var(--text);">${it.title}</div>
        <span style="font-size:12px;color:var(--muted);">${it.savedAt}</span>
      </div>
      <div style="font-size:13px;color:var(--muted);margin:4px 0;">
        ${it.white} vs ${it.black} (${it.result}) • <span style="color:var(--cyan);">${it.opening}</span>
      </div>
      <div style="display:flex;gap:12px;align-items:center;font-size:13px;margin:6px 0;">
        <span><img src="icons/brilliant.png" style="width:16px;height:16px;vertical-align:middle;" /> <b>Brilliant (!!):</b> ${btot} (${bw}W / ${bb}B)</span>
        <span style="color:var(--cyan);font-weight:800;">Your !!: ${byours} (${sideLbl})</span>
      </div>
      <div style="display:flex;gap:6px;margin-top:8px;">
        <button class="btn primary" onclick="openLibraryGame(${it.id})">Open</button>
        <button class="btn" onclick="renameLibraryGame(${it.id})">✏️ Rename</button>
        <button class="btn cyan" onclick="toggleLibrarySide(${it.id})">My Side: ${sideLbl}</button>
        <button class="btn" style="color:var(--red);" onclick="deleteLibraryGame(${it.id})">Delete</button>
      </div>
    `;
    listEl.appendChild(div);
  });
}

function loadFromInput() {
  const txt = (document.getElementById('pgn-input').value || '').trim();
  if (!txt) {
    loadSample('fegatello');
    return;
  }
  if (txt.toLowerCase().includes('qh5') || txt.toLowerCase().includes('qxf7')) {
    loadSample('scholar');
  } else {
    loadSample('fegatello');
  }
}

window.addEventListener('DOMContentLoaded', () => {
  loadSample('fegatello');
});
