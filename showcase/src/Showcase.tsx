import React from 'react';
import {
  AbsoluteFill,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  Img,
} from 'remotion';

const THEME = {
  bgDark: '#0b1015',
  bgCard: '#151d24',
  bgCardAlt: '#1c2630',
  accentGreen: '#4caf50',
  accentCyan: '#26c6da',
  accentGold: '#f5c542',
  accentOrange: '#ff9800',
  accentRed: '#e53935',
  textLight: '#f3f7fa',
  textMuted: '#94a3b8',
};

// --- ANIMATED BACKGROUND ---
const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const shift = (frame * 0.5) % 80;

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at 50% 25%, #1a2733 0%, #0b0f14 75%, #070a0d 100%)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `linear-gradient(to right, rgba(255,255,255,0.028) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(255,255,255,0.028) 1px, transparent 1px)`,
          backgroundSize: '80px 80px',
          backgroundPosition: `${shift}px ${shift}px`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 720,
          height: 720,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(38,198,218,0.08) 0%, transparent 70%)',
          top: -180,
          right: -120,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 680,
          height: 680,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(76,175,80,0.09) 0%, transparent 70%)',
          bottom: -200,
          left: -120,
        }}
      />
    </AbsoluteFill>
  );
};

// --- SCENE 1: HERO INTRO ---
const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12, mass: 0.75 } });
  const titleOpacity = interpolate(frame, [10, 28], [0, 1], { extrapolateRight: 'clamp' });
  const titleY = interpolate(frame, [10, 28], [26, 0], { extrapolateRight: 'clamp' });
  const pillsOpacity = interpolate(frame, [24, 44], [0, 1], { extrapolateRight: 'clamp' });

  const pills = [
    { label: '⚡ Stockfish 19 Engine', color: THEME.accentGreen, bg: 'rgba(76,175,80,0.14)' },
    { label: '💎 Brilliant (!!) Library Tracker', color: THEME.accentCyan, bg: 'rgba(38,198,218,0.14)' },
    { label: '🖥️ Windows .EXE  •  📱 Android .APK  •  🍎 iOS .IPA', color: THEME.accentGold, bg: 'rgba(245,197,66,0.13)' },
  ];

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          transform: `scale(${logoScale})`,
          boxShadow: '0 24px 70px rgba(76, 175, 80, 0.38)',
          borderRadius: 42,
          overflow: 'hidden',
          marginBottom: 32,
          border: '2px solid rgba(255,255,255,0.18)',
        }}
      >
        <Img src={staticFile('icon.png')} style={{ width: 176, height: 176, display: 'block' }} />
      </div>

      <div
        style={{
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          textAlign: 'center',
        }}
      >
        <h1
          style={{
            fontFamily: 'Segoe UI, system-ui, sans-serif',
            fontSize: 82,
            fontWeight: 900,
            letterSpacing: '2px',
            color: THEME.textLight,
            margin: 0,
            textShadow: '0 6px 28px rgba(0,0,0,0.65)',
          }}
        >
          CHESS ANALYZER
        </h1>
        <p
          style={{
            fontFamily: 'Segoe UI, system-ui, sans-serif',
            fontSize: 26,
            color: THEME.textMuted,
            margin: '10px 0 0 0',
          }}
        >
          Pro-Grade Move Classification, Lichess Win% Curves &amp; In-App Game Library
        </p>
      </div>

      <div
        style={{
          opacity: pillsOpacity,
          display: 'flex',
          gap: 18,
          marginTop: 32,
        }}
      >
        {pills.map((p) => (
          <div
            key={p.label}
            style={{
              fontFamily: 'Segoe UI, system-ui, sans-serif',
              fontSize: 21,
              fontWeight: 700,
              color: p.color,
              background: p.bg,
              border: `1px solid ${p.color}55`,
              padding: '10px 24px',
              borderRadius: 999,
            }}
          >
            {p.label}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 2: LIVE INTERACTIVE BOARD & ANNOTATIONS ---
const LiveBoardScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const boardSpring = spring({ frame, fps, config: { damping: 14 } });
  const moveStep = frame < 45 ? 0 : 1; // 0 = before sacrifice, 1 = after Nd5!! sacrifice
  const badgePop = spring({ frame: Math.max(0, frame - 45), fps, config: { damping: 10, mass: 0.6 } });
  const evalWhitePct = interpolate(frame, [0, 45, 75], [56, 84, 88], { extrapolateRight: 'clamp' });
  const evalText = frame < 45 ? '+0.4' : '+3.6';

  // Simplified 8x8 position pieces
  const basePieces: Record<string, string> = {
    '0,0': '♜', '0,2': '♝', '0,3': '♛', '0,4': '♚', '0,5': '♝', '0,7': '♜',
    '1,0': '♟', '1,1': '♟', '1,2': '♟', '1,4': '♞', '1,5': '♟', '1,6': '♟', '1,7': '♟',
    '2,2': '♞', '2,5': '♟',
    '3,4': '♟',
    '4,2': '♗', '4,4': '♙',
    '5,5': '♘',
    '6,0': '♙', '6,1': '♙', '6,2': '♙', '6,3': '♙', '6,5': '♙', '6,6': '♙', '6,7': '♙',
    '7,0': '♖', '7,3': '♕', '7,4': '♔', '7,7': '♖',
  };
  if (moveStep === 0) {
    basePieces['5,2'] = '♘'; // c3
  } else {
    basePieces['3,3'] = '♘'; // Nd5!! sacrifice square
  }

  const moveRows = [
    { num: '1.', w: 'e4', wIcon: 'book.png', b: 'c5', bIcon: 'book.png', eval: '+0.2' },
    { num: '2.', w: 'Nf3', wIcon: 'book.png', b: 'd6', bIcon: 'book.png', eval: '+0.3' },
    { num: '3.', w: 'Bc4', wIcon: 'best.png', b: 'Nf6?!', bIcon: 'inaccuracy.png', eval: '+0.8' },
    { num: '4.', w: 'Nc3', wIcon: 'good.png', b: 'g6?', bIcon: 'mistake.png', eval: '+1.7' },
    { num: '5.', w: 'Nd5!!', wIcon: 'brilliant.png', b: 'Nxd5✗', bIcon: 'incorrect.png', eval: '+3.6', active: moveStep === 1 },
    { num: '6.', w: 'Bxd5!', wIcon: 'great_find.png', b: 'Bg7??', bIcon: 'blunder.png', eval: '+6.4' },
  ];

  const sqSize = 72;

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'row',
        padding: '60px 90px',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 48,
      }}
    >
      {/* Left: Eval Bar + 8x8 Board */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 18,
          transform: `scale(${boardSpring})`,
        }}
      >
        {/* Eval Bar */}
        <div
          style={{
            width: 38,
            height: sqSize * 8,
            background: '#262421',
            borderRadius: 12,
            overflow: 'hidden',
            position: 'relative',
            border: '2px solid rgba(255,255,255,0.15)',
            boxShadow: '0 16px 40px rgba(0,0,0,0.5)',
          }}
        >
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: `${evalWhitePct}%`,
              background: 'linear-gradient(180deg, #ffffff 0%, #e2e8f0 100%)',
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: 10,
              width: '100%',
              textAlign: 'center',
              fontSize: 13,
              fontWeight: 800,
              color: '#111',
              fontFamily: 'Segoe UI, sans-serif',
            }}
          >
            {evalText}
          </div>
        </div>

        {/* 8x8 Chessboard */}
        <div
          style={{
            width: sqSize * 8,
            height: sqSize * 8,
            borderRadius: 16,
            overflow: 'hidden',
            position: 'relative',
            boxShadow: '0 24px 60px rgba(0,0,0,0.65)',
            border: '3px solid rgba(255,255,255,0.15)',
          }}
        >
          {Array.from({ length: 64 }).map((_, idx) => {
            const r = Math.floor(idx / 8);
            const c = idx % 8;
            const light = (r + c) % 2 === 0;
            const isFrom = moveStep === 1 && r === 5 && c === 2;
            const isTo = moveStep === 1 && r === 3 && c === 3;
            let bg = light ? '#f0d9b5' : '#b58863';
            if (isFrom || isTo) {
              bg = light ? '#cdd26a' : '#aaa23a';
            }
            const piece = basePieces[`${r},${c}`];
            const isWhitePiece = piece && '♔♕♖♗♘♙'.includes(piece);

            return (
              <div
                key={idx}
                style={{
                  position: 'absolute',
                  left: c * sqSize,
                  top: r * sqSize,
                  width: sqSize,
                  height: sqSize,
                  background: bg,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 52,
                  fontFamily: 'Segoe UI Symbol, sans-serif',
                  color: isWhitePiece ? '#fff' : '#1b1b1b',
                  textShadow: isWhitePiece
                    ? '0 2px 4px rgba(0,0,0,0.65), 0 0 2px #000'
                    : '0 2px 4px rgba(255,255,255,0.25)',
                }}
              >
                {piece}
              </div>
            );
          })}

          {/* Best Move Arrow overlay */}
          <svg
            width={sqSize * 8}
            height={sqSize * 8}
            style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
          >
            <defs>
              <marker id="arrowHead" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="#26c6da" />
              </marker>
            </defs>
            {moveStep === 1 && (
              <line
                x1={2 * sqSize + sqSize / 2}
                y1={5 * sqSize + sqSize / 2}
                x2={3 * sqSize + sqSize / 2}
                y2={3 * sqSize + sqSize / 2}
                stroke="#26c6da"
                strokeWidth="9"
                strokeLinecap="round"
                opacity={0.82}
                markerEnd="url(#arrowHead)"
              />
            )}
          </svg>

          {/* Brilliant (!!) Badge on d5 */}
          {moveStep === 1 && (
            <div
              style={{
                position: 'absolute',
                left: 3 * sqSize + sqSize - 24,
                top: 3 * sqSize - 10,
                transform: `scale(${badgePop})`,
              }}
            >
              <Img
                src={staticFile('icons/brilliant.png')}
                style={{
                  width: 36,
                  height: 36,
                  filter: 'drop-shadow(0 4px 10px rgba(0,0,0,0.65))',
                }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Right: Move Table & Annotation Legend */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20 }}>
        <div>
          <span
            style={{
              color: THEME.accentCyan,
              fontSize: 19,
              fontWeight: 800,
              letterSpacing: '1.5px',
              textTransform: 'uppercase',
            }}
          >
            Stockfish 19 Multi-PV Analysis
          </span>
          <h2
            style={{
              fontFamily: 'Segoe UI, sans-serif',
              fontSize: 44,
              fontWeight: 800,
              color: THEME.textLight,
              margin: '6px 0 0 0',
            }}
          >
            Live Board Badges &amp; Best-Line Arrows
          </h2>
        </div>

        {/* Move Table */}
        <div
          style={{
            background: THEME.bgCard,
            borderRadius: 20,
            padding: 20,
            border: '1px solid rgba(255,255,255,0.1)',
            boxShadow: '0 16px 40px rgba(0,0,0,0.45)',
          }}
        >
          {moveRows.map((row) => (
            <div
              key={row.num}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 16px',
                borderRadius: 12,
                background: row.active ? 'rgba(38,198,218,0.16)' : 'transparent',
                border: row.active ? '1px solid rgba(38,198,218,0.45)' : '1px solid transparent',
                fontFamily: 'Segoe UI, sans-serif',
                fontSize: 21,
              }}
            >
              <span style={{ color: THEME.textMuted, width: 45, fontWeight: 700 }}>{row.num}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, width: 170 }}>
                <Img src={staticFile(`icons/${row.wIcon}`)} style={{ width: 26, height: 26 }} />
                <span style={{ color: THEME.textLight, fontWeight: 700 }}>{row.w}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, width: 170 }}>
                <Img src={staticFile(`icons/${row.bIcon}`)} style={{ width: 26, height: 26 }} />
                <span style={{ color: THEME.textLight, fontWeight: 600 }}>{row.b}</span>
              </div>
              <span
                style={{
                  color: THEME.accentGreen,
                  fontWeight: 800,
                  background: 'rgba(76,175,80,0.14)',
                  padding: '4px 12px',
                  borderRadius: 8,
                  fontSize: 18,
                }}
              >
                {row.eval}
              </span>
            </div>
          ))}
        </div>

        {/* Updated Mistake (?) & Miss (✗) highlight row */}
        <div style={{ display: 'flex', gap: 16 }}>
          {[
            { icon: 'brilliant.png', label: 'Brilliant (!!)', sub: 'Sound Sacrifice', col: '#26c6da' },
            { icon: 'mistake.png', label: 'Mistake (?)', sub: '10–20% Win Drop', col: '#ff9800' },
            { icon: 'incorrect.png', label: 'Miss (✗)', sub: 'Missed Winning Tactic', col: '#e53935' },
            { icon: 'blunder.png', label: 'Blunder (??)', sub: '>20% Win Drop', col: '#ca3431' },
          ].map((b) => (
            <div
              key={b.label}
              style={{
                flex: 1,
                background: THEME.bgCardAlt,
                borderRadius: 14,
                padding: '12px 14px',
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                border: `1px solid ${b.col}44`,
              }}
            >
              <Img src={staticFile(`icons/${b.icon}`)} style={{ width: 34, height: 34 }} />
              <div>
                <div style={{ color: b.col, fontSize: 16, fontWeight: 800, fontFamily: 'Segoe UI, sans-serif' }}>
                  {b.label}
                </div>
                <div style={{ color: THEME.textMuted, fontSize: 13, fontFamily: 'Segoe UI, sans-serif' }}>
                  {b.sub}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 3: IN-APP SAVED GAMES LIBRARY & BRILLIANT TRACKER ---
const LibraryScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const cardSpring = spring({ frame, fps, config: { damping: 14 } });

  const games = [
    {
      name: '🔥 Immortal Queen Sacrifice',
      players: 'You vs GM_Hikaru',
      res: '1-0',
      totalBril: '3 (2W / 1B)',
      yourBril: '2 (White)',
      opening: 'B90 Sicilian Najdorf',
      acc: '94.8% / 88.2%',
      elo: '2480',
      highlight: true,
    },
    {
      name: '⚔️ Club Championship Finals Rd 4',
      players: 'Magnus_Fan vs You',
      res: '0-1',
      totalBril: '2 (0W / 2B)',
      yourBril: '2 (Black)',
      opening: 'C65 Ruy Lopez: Berlin',
      acc: '86.4% / 93.1%',
      elo: '2390',
      highlight: false,
    },
    {
      name: '⚡ King’s Gambit Romantic Attack',
      players: 'You vs Naroditsky_Sub',
      res: '1-0',
      totalBril: '4 (3W / 1B)',
      yourBril: '3 (White)',
      opening: 'C33 King’s Gambit Accepted',
      acc: '96.1% / 84.7%',
      elo: '2540',
      highlight: false,
    },
    {
      name: '🛡️ Endgame Fortress Defense',
      players: 'TacticalWizard vs You',
      res: '1/2-1/2',
      totalBril: '1 (0W / 1B)',
      yourBril: '1 (Black)',
      opening: 'D37 Queen’s Gambit Declined',
      acc: '91.5% / 92.0%',
      elo: '2310',
      highlight: false,
    },
  ];

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        padding: '60px 100px',
        justifyContent: 'center',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginBottom: 24 }}>
        <div>
          <span
            style={{
              color: THEME.accentCyan,
              fontSize: 20,
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: '1.5px',
            }}
          >
            Built-In SQLite Game Database
          </span>
          <h2
            style={{
              fontFamily: 'Segoe UI, sans-serif',
              fontSize: 48,
              fontWeight: 800,
              color: THEME.textLight,
              margin: '6px 0 0 0',
            }}
          >
            Saved Games Library, Custom Renaming &amp; Brilliant Counter
          </h2>
        </div>

        <div style={{ display: 'flex', gap: 14 }}>
          <div
            style={{
              background: 'rgba(245,197,66,0.15)',
              border: '1px solid rgba(245,197,66,0.45)',
              color: THEME.accentGold,
              padding: '10px 20px',
              borderRadius: 12,
              fontSize: 18,
              fontWeight: 700,
              fontFamily: 'Segoe UI, sans-serif',
            }}
          >
            ✏️ Rename Any Game (F2)
          </div>
          <div
            style={{
              background: 'rgba(76,175,80,0.15)',
              border: '1px solid rgba(76,175,80,0.45)',
              color: THEME.accentGreen,
              padding: '10px 20px',
              borderRadius: 12,
              fontSize: 18,
              fontWeight: 700,
              fontFamily: 'Segoe UI, sans-serif',
            }}
          >
            ⚡ Instant 0ms Reload (No Re-Analysis)
          </div>
        </div>
      </div>

      {/* Library Window Mock */}
      <div
        style={{
          transform: `scale(${cardSpring})`,
          background: THEME.bgCard,
          borderRadius: 24,
          padding: 28,
          border: '1px solid rgba(255,255,255,0.12)',
          boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
        }}
      >
        {/* Brilliant Summary Banner */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(38,198,218,0.12)',
            border: '1px solid rgba(38,198,218,0.38)',
            borderRadius: 16,
            padding: '14px 24px',
            marginBottom: 22,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Img src={staticFile('icons/brilliant.png')} style={{ width: 38, height: 38 }} />
            <span style={{ fontFamily: 'Segoe UI, sans-serif', fontSize: 23, color: THEME.textLight }}>
              <b style={{ color: THEME.accentCyan }}>Brilliant Moves (!!) Across Library:</b> 10 played in total
              &nbsp;&nbsp;•&nbsp;&nbsp;
              <b style={{ color: THEME.accentGold }}>Played by You: 8 (80%)</b>
            </span>
          </div>
          <span
            style={{
              fontFamily: 'Segoe UI, sans-serif',
              fontSize: 16,
              color: THEME.accentCyan,
              background: 'rgba(0,0,0,0.3)',
              padding: '6px 14px',
              borderRadius: 8,
            }}
          >
            Switch My Side (White / Black)
          </span>
        </div>

        {/* Table Header */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '2.2fr 1.5fr 0.7fr 1.3fr 1.2fr 1.8fr 1.2fr 0.8fr',
            padding: '12px 18px',
            background: '#222d38',
            borderRadius: 12,
            color: THEME.textMuted,
            fontSize: 16,
            fontWeight: 700,
            fontFamily: 'Segoe UI, sans-serif',
            marginBottom: 10,
          }}
        >
          <div>Game Name (Renamed)</div>
          <div>Players</div>
          <div>Result</div>
          <div>Brilliant (!!)</div>
          <div>Your !!</div>
          <div>Opening (ECO)</div>
          <div>Accuracy</div>
          <div>Est. Elo</div>
        </div>

        {/* Table Rows */}
        {games.map((g, idx) => {
          const rowDelay = idx * 5;
          const rowOpacity = interpolate(frame - rowDelay, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
          return (
            <div
              key={g.name}
              style={{
                opacity: rowOpacity,
                display: 'grid',
                gridTemplateColumns: '2.2fr 1.5fr 0.7fr 1.3fr 1.2fr 1.8fr 1.2fr 0.8fr',
                padding: '16px 18px',
                borderRadius: 14,
                alignItems: 'center',
                background: g.highlight ? 'rgba(38,198,218,0.1)' : 'rgba(255,255,255,0.02)',
                border: g.highlight ? '1px solid rgba(38,198,218,0.35)' : '1px solid rgba(255,255,255,0.04)',
                marginBottom: 8,
                fontFamily: 'Segoe UI, sans-serif',
                fontSize: 18,
              }}
            >
              <div style={{ color: THEME.textLight, fontWeight: 700 }}>{g.name}</div>
              <div style={{ color: THEME.textMuted }}>{g.players}</div>
              <div style={{ color: THEME.textLight, fontWeight: 700 }}>{g.res}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: THEME.textLight, fontWeight: 700 }}>
                <Img src={staticFile('icons/brilliant.png')} style={{ width: 22, height: 22 }} />
                {g.totalBril}
              </div>
              <div style={{ color: THEME.accentCyan, fontWeight: 800 }}>{g.yourBril}</div>
              <div style={{ color: THEME.textMuted }}>{g.opening}</div>
              <div style={{ color: THEME.accentGreen, fontWeight: 700 }}>{g.acc}</div>
              <div style={{ color: THEME.accentGold, fontWeight: 800 }}>{g.elo}</div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 4: WIN% PROBABILITY CURVE & ACCURACY ---
const EvaluationScene: React.FC = () => {
  const frame = useCurrentFrame();
  const graphProgress = interpolate(frame, [0, 45], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'row',
        padding: '70px 100px',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 50,
      }}
    >
      {/* Left: Eval Graph & Win% Formula */}
      <div
        style={{
          flex: 1.15,
          background: THEME.bgCard,
          borderRadius: 28,
          padding: 36,
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.55)',
        }}
      >
        <span style={{ color: THEME.accentGreen, fontSize: 18, fontWeight: 800, textTransform: 'uppercase' }}>
          Non-Linear Lichess Win Probability
        </span>
        <h3 style={{ fontSize: 34, fontWeight: 800, color: THEME.textLight, margin: '6px 0 12px 0', fontFamily: 'Segoe UI, sans-serif' }}>
          Win% Curve &amp; Interactive Eval Graph
        </h3>
        <div
          style={{
            background: '#0e1419',
            padding: '10px 18px',
            borderRadius: 12,
            color: THEME.accentCyan,
            fontFamily: 'Consolas, monospace',
            fontSize: 18,
            marginBottom: 20,
            border: '1px solid rgba(38,198,218,0.25)',
          }}
        >
          win% = 50 + 50 · (2 / (1 + e^(-0.00368208 · cp)) - 1)
        </div>

        <div
          style={{
            height: 210,
            background: '#10161c',
            borderRadius: 16,
            position: 'relative',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <svg width="100%" height="100%" viewBox="0 0 800 210">
            <line x1="0" y1="105" x2="800" y2="105" stroke="rgba(255,255,255,0.12)" strokeDasharray="6 6" />
            <path
              d="M 0 110 Q 120 95 220 65 T 420 130 T 600 40 T 800 22"
              fill="none"
              stroke={THEME.accentGreen}
              strokeWidth="5"
              strokeDasharray="1000"
              strokeDashoffset={`${(1 - graphProgress) * 1000}`}
              style={{ filter: 'drop-shadow(0 0 12px rgba(76,175,80,0.75))' }}
            />
          </svg>
        </div>
      </div>

      {/* Right: Phase Accuracy Cards */}
      <div style={{ flex: 0.85, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <span style={{ color: THEME.accentGold, fontSize: 19, fontWeight: 800, textTransform: 'uppercase' }}>
          Harmonic + Weighted Mean
        </span>
        <h2 style={{ fontSize: 44, fontWeight: 800, color: THEME.textLight, margin: '0 0 12px 0', fontFamily: 'Segoe UI, sans-serif' }}>
          Phase Accuracy &amp; Elo Rating
        </h2>
        {[
          { phase: 'Opening Theory (ECO A–E)', acc: '96.4%', color: '#6fa84d' },
          { phase: 'Middlegame Tactics', acc: '91.8%', color: '#4caf50' },
          { phase: 'Endgame Conversion', acc: '94.2%', color: '#26c6da' },
          { phase: 'Estimated Performance', acc: '2450 Elo', color: THEME.accentGold },
        ].map((item) => (
          <div
            key={item.phase}
            style={{
              background: THEME.bgCard,
              borderRadius: 16,
              padding: '18px 24px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderLeft: `6px solid ${item.color}`,
              fontFamily: 'Segoe UI, sans-serif',
            }}
          >
            <span style={{ color: THEME.textLight, fontSize: 20, fontWeight: 600 }}>{item.phase}</span>
            <span style={{ color: item.color, fontSize: 26, fontWeight: 800 }}>{item.acc}</span>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 5: MULTI-PLATFORM OUTRO ---
const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 14 } });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <Img
          src={staticFile('icon.png')}
          style={{
            width: 148,
            height: 148,
            marginBottom: 26,
            boxShadow: '0 18px 50px rgba(76,175,80,0.42)',
            borderRadius: 34,
            border: '2px solid rgba(255,255,255,0.18)',
          }}
        />
        <h1
          style={{
            fontFamily: 'Segoe UI, sans-serif',
            fontSize: 66,
            fontWeight: 900,
            color: THEME.textLight,
            margin: 0,
          }}
        >
          Chess Game Analyzer v1.2
        </h1>

        <div style={{ display: 'flex', gap: 18, marginTop: 26 }}>
          {[
            { label: '🖥️ Windows (.exe)', col: THEME.accentGreen },
            { label: '🤖 Android (.apk)', col: THEME.accentCyan },
            { label: '🍎 iOS (.ipa)', col: THEME.accentGold },
          ].map((p) => (
            <span
              key={p.label}
              style={{
                background: 'rgba(255,255,255,0.07)',
                padding: '12px 26px',
                borderRadius: 999,
                fontSize: 23,
                fontWeight: 700,
                color: p.col,
                border: `1px solid ${p.col}55`,
                fontFamily: 'Segoe UI, sans-serif',
              }}
            >
              {p.label}
            </span>
          ))}
        </div>

        <p
          style={{
            fontSize: 22,
            color: THEME.textMuted,
            marginTop: 22,
            fontFamily: 'Segoe UI, sans-serif',
          }}
        >
          Powered by Stockfish 19 • Built-In Game Library &amp; Brilliant Move Tracker
        </p>
      </div>
    </AbsoluteFill>
  );
};

export const ShowcaseVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      <Background />
      <Sequence from={0} durationInFrames={80}>
        <IntroScene />
      </Sequence>
      <Sequence from={80} durationInFrames={115}>
        <LiveBoardScene />
      </Sequence>
      <Sequence from={195} durationInFrames={115}>
        <LibraryScene />
      </Sequence>
      <Sequence from={310} durationInFrames={100}>
        <EvaluationScene />
      </Sequence>
      <Sequence from={410} durationInFrames={70}>
        <OutroScene />
      </Sequence>
    </AbsoluteFill>
  );
};
