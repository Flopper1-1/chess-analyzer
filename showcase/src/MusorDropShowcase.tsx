import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

const THEME = {
  bgDark: '#070a0f',
  bgCard: '#111822',
  accentGreen: '#4caf50',
  accentCyan: '#26c6da',
  accentGold: '#ffd54f',
  accentOrange: '#ff9800',
  accentRed: '#ef5350',
  textLight: '#f8fafc',
};

// --- ANIMATED BACKGROUND ---
const Background: React.FC<{ intense?: boolean }> = ({ intense }) => {
  const frame = useCurrentFrame();
  const shift = (frame * 1.2) % 80;
  const pulse = Math.sin(frame * 0.25) * 0.5 + 0.5;

  return (
    <AbsoluteFill
      style={{
        background: intense
          ? 'radial-gradient(circle at 50% 45%, #162c3d 0%, #091017 65%, #04070a 100%)'
          : 'radial-gradient(circle at 50% 30%, #152230 0%, #090d13 75%, #05070a 100%)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `linear-gradient(to right, rgba(38,198,218,0.04) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(38,198,218,0.04) 1px, transparent 1px)`,
          backgroundSize: '80px 80px',
          backgroundPosition: `${shift}px ${shift}px`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: 850,
          height: 850,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(38,198,218,${0.08 + pulse * 0.06}) 0%, transparent 70%)`,
          top: -240,
          left: '50%',
          transform: 'translateX(-50%)',
        }}
      />
    </AbsoluteFill>
  );
};

// --- MUSOR DROP STYLE CASE-OPENING BANNER (0s - 5.42s) ---
const REEL_ITEMS = [
  { icon: 'blunder.png', color: '#e53935' },
  { icon: 'mistake.png', color: '#ff9800' },
  { icon: 'inaccuracy.png', color: '#fdd835' },
  { icon: 'incorrect.png', color: '#ef5350' },
  { icon: 'book.png', color: '#a1887f' },
  { icon: 'good.png', color: '#81c784' },
  { icon: 'excellent.png', color: '#66bb6a' },
  { icon: 'best.png', color: '#4caf50' },
  { icon: 'great_find.png', color: '#42a5f5' },
  { icon: 'brilliant.png', color: '#26c6da' },
];

const MusorDropBanner: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Build a deterministic 45-slot roulette strip where index 34 is the winning 'brilliant.png'
  const WIN_INDEX = 34;
  const CARD_W = 136;
  const CARD_GAP = 16;
  const STEP = CARD_W + CARD_GAP;

  const strip = Array.from({ length: 45 }).map((_, idx) => {
    if (idx === WIN_INDEX) {
      return { icon: 'brilliant.png', color: '#26c6da', jackpot: true };
    }
    const item = REEL_ITEMS[(idx * 7 + 3) % (REEL_ITEMS.length - 1)];
    return { ...item, jackpot: false };
  });

  // Spin from slot 2 to slot WIN_INDEX (34), landing smoothly at frame 136
  const spinProgress = interpolate(frame, [0, 136], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const startX = 2 * STEP;
  const endX = WIN_INDEX * STEP;
  const currentOffset = interpolate(spinProgress, [0, 1], [startX, endX]);

  const landed = frame >= 136;
  const winPulse = landed
    ? spring({ frame: frame - 136, fps, config: { damping: 8, mass: 0.5 } })
    : 0;

  const bannerGlow = landed ? '0 0 50px rgba(38,198,218,0.75)' : '0 16px 45px rgba(0,0,0,0.75)';

  return (
    <div
      style={{
        width: 1680,
        height: 210,
        background: 'linear-gradient(180deg, #16222f 0%, #0d141c 100%)',
        borderRadius: 28,
        border: landed ? '3px solid #26c6da' : '3px solid #ffd54f',
        boxShadow: bannerGlow,
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
      }}
    >
      {/* Diagonal caution/neon stripes on edges (Musor Drop banner style, zero words) */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'repeating-linear-gradient(45deg, rgba(255,213,79,0.035) 0px, rgba(255,213,79,0.035) 20px, transparent 20px, transparent 40px)',
          pointerEvents: 'none',
        }}
      />

      {/* Scrolling Case-Opening Cards */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: CARD_GAP,
          position: 'absolute',
          left: 1680 / 2 - CARD_W / 2 - currentOffset,
        }}
      >
        {strip.map((card, idx) => {
          const isWinner = idx === WIN_INDEX && landed;
          const scale = isWinner ? 1 + winPulse * 0.22 : 1;

          return (
            <div
              key={idx}
              style={{
                width: CARD_W,
                height: 154,
                borderRadius: 20,
                background: isWinner
                  ? 'radial-gradient(circle at 50% 40%, rgba(38,198,218,0.42), #122530 80%)'
                  : '#141d26',
                border: isWinner ? '3px solid #26c6da' : `2px solid ${card.color}66`,
                borderBottom: `8px solid ${card.color}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transform: `scale(${scale})`,
                boxShadow: isWinner ? '0 0 36px rgba(38,198,218,0.9)' : '0 8px 20px rgba(0,0,0,0.45)',
              }}
            >
              <Img
                src={staticFile(`icons/${card.icon}`)}
                style={{
                  width: isWinner ? 92 : 78,
                  height: isWinner ? 92 : 78,
                  filter: `drop-shadow(0 6px 14px ${card.color}88)`,
                }}
              />
            </div>
          );
        })}
      </div>

      {/* Left & Right vignette fade */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(90deg, #0b1118 0%, transparent 18%, transparent 82%, #0b1118 100%)',
          pointerEvents: 'none',
        }}
      />

      {/* Center Golden Selector Line & Triangles */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: 0,
          bottom: 0,
          width: 4,
          transform: 'translateX(-50%)',
          background: landed ? '#26c6da' : '#ffd54f',
          boxShadow: landed ? '0 0 20px #26c6da' : '0 0 16px #ffd54f',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: 0,
          transform: 'translateX(-50%)',
          width: 0,
          height: 0,
          borderLeft: '16px solid transparent',
          borderRight: '16px solid transparent',
          borderTop: `22px solid ${landed ? '#26c6da' : '#ffd54f'}`,
        }}
      />
      <div
        style={{
          position: 'absolute',
          left: '50%',
          bottom: 0,
          transform: 'translateX(-50%)',
          width: 0,
          height: 0,
          borderLeft: '16px solid transparent',
          borderRight: '16px solid transparent',
          borderBottom: `22px solid ${landed ? '#26c6da' : '#ffd54f'}`,
        }}
      />
    </div>
  );
};

// --- PART 1 SCENE (0.00s - 5.42s / frames 0 - 162): VISUAL SHOWCASE + MUSOR DROP BANNER ---
const PreDropShowcaseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Step through 5 rapid tactical positions across 162 frames
  const step = Math.min(4, Math.floor(frame / 30));
  const stepLocalFrame = frame - step * 30;
  const badgePop = spring({ frame: stepLocalFrame, fps, config: { damping: 10, mass: 0.55 } });

  const evalFillPct = interpolate(
    frame,
    [0, 30, 60, 90, 120, 155],
    [52, 62, 38, 74, 92, 95],
    { extrapolateRight: 'clamp' }
  );

  // Dynamic tactical moves on the board (zero text, pure piece glyphs & badge icons)
  const moves = [
    { from: [6, 4], to: [4, 4], piece: '♙', icon: 'book.png', arrow: [[7, 6], [5, 5]] },
    { from: [7, 5], to: [4, 2], piece: '♗', icon: 'best.png', arrow: [[5, 5], [3, 6]] },
    { from: [0, 6], to: [2, 5], piece: '♞', icon: 'mistake.png', arrow: [[0, 1], [2, 2]] },
    { from: [5, 5], to: [3, 6], piece: '♘', icon: 'great_find.png', arrow: [[3, 6], [1, 5]] },
    { from: [3, 6], to: [1, 5], piece: '♘', icon: 'brilliant.png', arrow: [[7, 3], [5, 5]] },
  ];

  const activeMove = moves[step];

  const pieces: Record<string, string> = {
    '0,0': '♜', '0,2': '♝', '0,3': '♛', '0,4': '♚', '0,5': '♝', '0,7': '♜',
    '1,0': '♟', '1,1': '♟', '1,2': '♟', '1,6': '♟', '1,7': '♟',
    '2,2': '♞',
    '3,3': '♟',
    '6,0': '♙', '6,1': '♙', '6,2': '♙', '6,3': '♙', '6,5': '♙', '6,6': '♙', '6,7': '♙',
    '7,0': '♖', '7,1': '♘', '7,2': '♗', '7,3': '♕', '7,4': '♔', '7,7': '♖',
  };

  if (step >= 0) pieces['4,4'] = '♙';
  if (step >= 1) pieces['4,2'] = '♗';
  if (step >= 2) pieces['2,5'] = '♞';
  if (step === 3) pieces['3,6'] = '♘';
  if (step >= 4) pieces['1,5'] = '♘';
  else pieces['1,5'] = '♟';

  const sqSize = 76;
  const graphDraw = interpolate(frame, [0, 145], [0, 1], { extrapolateRight: 'clamp' });

  // Pre-cut camera zoom build-up on frames 142-162
  const preDropZoom = interpolate(frame, [142, 162], [1, 1.14], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.in(Easing.quad),
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '44px 120px 52px 120px',
        transform: `scale(${preDropZoom})`,
      }}
    >
      {/* Top: Musor Drop Style Icon Roulette Banner */}
      <MusorDropBanner />

      {/* Bottom: Visual Board + Eval Bar + Visual Wave & Icon Matrix */}
      <div
        style={{
          display: 'flex',
          width: 1680,
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 48,
        }}
      >
        {/* Left: Eval Bar + 8x8 Board */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          {/* Pure Visual Eval Bar (no numbers/text) */}
          <div
            style={{
              width: 38,
              height: sqSize * 8,
              background: '#1e2229',
              borderRadius: 14,
              overflow: 'hidden',
              position: 'relative',
              border: '2px solid rgba(255,255,255,0.18)',
              boxShadow: '0 16px 40px rgba(0,0,0,0.6)',
            }}
          >
            <div
              style={{
                position: 'absolute',
                bottom: 0,
                left: 0,
                right: 0,
                height: `${evalFillPct}%`,
                background: 'linear-gradient(180deg, #26c6da 0%, #f8fafc 30%, #e2e8f0 100%)',
              }}
            />
          </div>

          {/* 8x8 Chessboard */}
          <div
            style={{
              width: sqSize * 8,
              height: sqSize * 8,
              borderRadius: 20,
              overflow: 'hidden',
              position: 'relative',
              boxShadow: '0 24px 64px rgba(0,0,0,0.7)',
              border: '3px solid rgba(255,255,255,0.18)',
            }}
          >
            {Array.from({ length: 64 }).map((_, idx) => {
              const r = Math.floor(idx / 8);
              const c = idx % 8;
              const light = (r + c) % 2 === 0;
              const isFrom = activeMove.from[0] === r && activeMove.from[1] === c;
              const isTo = activeMove.to[0] === r && activeMove.to[1] === c;
              let bg = light ? '#f0d9b5' : '#b58863';
              if (isFrom || isTo) {
                bg = light ? '#cdd26a' : '#aaa23a';
              }
              const p = pieces[`${r},${c}`];
              const isW = p && '♔♕♖♗♘♙'.includes(p);

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
                    fontSize: 54,
                    fontFamily: 'Segoe UI Symbol, sans-serif',
                    color: isW ? '#ffffff' : '#181818',
                    textShadow: isW
                      ? '0 2px 5px rgba(0,0,0,0.7), 0 0 2px #000'
                      : '0 2px 4px rgba(255,255,255,0.25)',
                  }}
                >
                  {p}
                </div>
              );
            })}

            {/* Glowing Best-Move Arrow */}
            <svg
              width={sqSize * 8}
              height={sqSize * 8}
              style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
            >
              <defs>
                <marker id="cyanArrow" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto">
                  <path d="M0,0 L6,3 L0,6 Z" fill="#26c6da" />
                </marker>
              </defs>
              <line
                x1={activeMove.arrow[0][1] * sqSize + sqSize / 2}
                y1={activeMove.arrow[0][0] * sqSize + sqSize / 2}
                x2={activeMove.arrow[1][1] * sqSize + sqSize / 2}
                y2={activeMove.arrow[1][0] * sqSize + sqSize / 2}
                stroke="#26c6da"
                strokeWidth="10"
                strokeLinecap="round"
                opacity={0.85}
                markerEnd="url(#cyanArrow)"
              />
            </svg>

            {/* On-square Annotation Icon Badge */}
            <div
              style={{
                position: 'absolute',
                left: activeMove.to[1] * sqSize + sqSize - 26,
                top: activeMove.to[0] * sqSize - 10,
                transform: `scale(${badgePop})`,
              }}
            >
              <Img
                src={staticFile(`icons/${activeMove.icon}`)}
                style={{
                  width: 42,
                  height: 42,
                  filter: 'drop-shadow(0 5px 12px rgba(0,0,0,0.75))',
                }}
              />
            </div>
          </div>
        </div>

        {/* Right: Pure Visual Eval Graph + Animated Badge Showcase Grid (Zero Words) */}
        <div
          style={{
            flex: 1,
            height: sqSize * 8,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: 24,
          }}
        >
          {/* Animated Evaluation Curve Card */}
          <div
            style={{
              flex: 1,
              background: THEME.bgCard,
              borderRadius: 24,
              padding: 28,
              border: '2px solid rgba(38,198,218,0.22)',
              boxShadow: '0 20px 50px rgba(0,0,0,0.55)',
              position: 'relative',
              overflow: 'hidden',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <svg width="100%" height="100%" viewBox="0 0 880 260">
              <defs>
                <linearGradient id="evalFillGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#26c6da" stopOpacity="0.45" />
                  <stop offset="100%" stopColor="#26c6da" stopOpacity="0.0" />
                </linearGradient>
              </defs>
              <line x1="0" y1="130" x2="880" y2="130" stroke="rgba(255,255,255,0.12)" strokeDasharray="8 8" strokeWidth="2" />
              <path
                d="M 0 135 Q 110 110 220 95 T 440 165 T 640 55 T 880 24"
                fill="none"
                stroke="#26c6da"
                strokeWidth="7"
                strokeDasharray="1100"
                strokeDashoffset={`${(1 - graphDraw) * 1100}`}
                style={{ filter: 'drop-shadow(0 0 14px rgba(38,198,218,0.85))' }}
              />
              <circle
                cx={interpolate(graphDraw, [0, 1], [0, 880])}
                cy={interpolate(graphDraw, [0, 0.25, 0.5, 0.75, 1], [135, 95, 165, 55, 24])}
                r="11"
                fill="#ffd54f"
                style={{ filter: 'drop-shadow(0 0 12px #ffd54f)' }}
              />
            </svg>
          </div>

          {/* 5x2 Icon Matrix Highlighting Move Classifications (Zero Text) */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(5, 1fr)',
              gap: 18,
            }}
          >
            {[
              { icon: 'brilliant.png', col: '#26c6da', active: step === 4 },
              { icon: 'great_find.png', col: '#42a5f5', active: step === 3 },
              { icon: 'best.png', col: '#4caf50', active: step === 1 },
              { icon: 'excellent.png', col: '#66bb6a', active: false },
              { icon: 'good.png', col: '#81c784', active: false },
              { icon: 'book.png', col: '#a1887f', active: step === 0 },
              { icon: 'inaccuracy.png', col: '#fdd835', active: false },
              { icon: 'mistake.png', col: '#ff9800', active: step === 2 },
              { icon: 'incorrect.png', col: '#ef5350', active: false },
              { icon: 'blunder.png', col: '#e53935', active: false },
            ].map((item, idx) => {
              const pop = spring({
                frame: frame - idx * 3,
                fps,
                config: { damping: 12, mass: 0.5 },
              });
              return (
                <div
                  key={item.icon}
                  style={{
                    height: 118,
                    background: item.active
                      ? `radial-gradient(circle, ${item.col}44 0%, #151f2b 85%)`
                      : THEME.bgCard,
                    borderRadius: 22,
                    border: item.active ? `3px solid ${item.col}` : `2px solid ${item.col}44`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transform: `scale(${Math.max(0, pop) * (item.active ? 1.08 : 1)})`,
                    boxShadow: item.active ? `0 0 28px ${item.col}88` : '0 10px 25px rgba(0,0,0,0.45)',
                  }}
                >
                  <Img src={staticFile(`icons/${item.icon}`)} style={{ width: 68, height: 68 }} />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// --- PART 2 SCENE (5.42s - 9.46s / frames 162 - 284): "CHESS ANALYZER" DROP & TITLE REVEAL ---
const TitleDropScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Impact white/cyan flash on the hard cut at frame 0 of this sequence (global frame 162)
  const flashOpacity = interpolate(frame, [0, 12], [0.95, 0], { extrapolateRight: 'clamp' });

  // Slam-in spring for the logo & title
  const slamScale = spring({
    frame,
    fps,
    config: { damping: 11, mass: 0.65, stiffness: 160 },
  });

  const ringScale = interpolate(frame, [0, 45], [0.5, 2.4], { extrapolateRight: 'clamp' });
  const ringOpacity = interpolate(frame, [0, 45], [0.85, 0], { extrapolateRight: 'clamp' });

  // Orbiting annotation icons around the main emblem
  const orbitIcons = [
    'brilliant.png',
    'great_find.png',
    'best.png',
    'book.png',
    'mistake.png',
    'incorrect.png',
    'blunder.png',
    'excellent.png',
  ];

  // Visual-only bouncing down-arrow cue when announcer says "Ссылка в описании профиля" (global frame 213 -> local frame 51)
  const arrowPop = frame >= 48
    ? spring({ frame: frame - 48, fps, config: { damping: 10, mass: 0.6 } })
    : 0;
  const arrowBounce = Math.sin(frame * 0.35) * 10;

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Expanding Impact Shockwave Ring */}
      <div
        style={{
          position: 'absolute',
          width: 420,
          height: 420,
          borderRadius: '50%',
          border: '6px solid #26c6da',
          transform: `scale(${ringScale})`,
          opacity: ringOpacity,
          boxShadow: '0 0 60px #26c6da',
          pointerEvents: 'none',
        }}
      />

      {/* Orbiting Annotation Badges */}
      {orbitIcons.map((ic, idx) => {
        const angle = (idx / orbitIcons.length) * Math.PI * 2 + frame * 0.018;
        const radiusX = 750;
        const radiusY = 400;
        const x = Math.cos(angle) * radiusX;
        const y = Math.sin(angle) * radiusY - 10;
        const badgeScale = spring({
          frame: frame - idx * 2,
          fps,
          config: { damping: 12, mass: 0.5 },
        });

        return (
          <div
            key={ic}
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              transform: `translate(${x - 42}px, ${y - 42}px) scale(${Math.max(0, badgeScale)})`,
              background: 'rgba(17, 24, 34, 0.85)',
              padding: 14,
              borderRadius: 24,
              border: '2px solid rgba(38,198,218,0.4)',
              boxShadow: '0 14px 35px rgba(0,0,0,0.6)',
            }}
          >
            <Img src={staticFile(`icons/${ic}`)} style={{ width: 56, height: 56, display: 'block' }} />
          </div>
        );
      })}

      {/* Center Logo + THE ONLY WORDS IN THE SHOWCASE: "CHESS ANALYZER" */}
      <div
        style={{
          transform: `scale(${slamScale})`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          zIndex: 5,
        }}
      >
        <div
          style={{
            borderRadius: 48,
            overflow: 'hidden',
            boxShadow: '0 25px 80px rgba(76, 175, 80, 0.55), 0 0 40px rgba(38, 198, 218, 0.45)',
            border: '4px solid rgba(255,255,255,0.28)',
            marginBottom: 38,
          }}
        >
          <Img src={staticFile('icon.png')} style={{ width: 220, height: 220, display: 'block' }} />
        </div>

        <h1
          style={{
            fontFamily: 'Segoe UI, system-ui, sans-serif',
            fontSize: 108,
            fontWeight: 900,
            letterSpacing: '4px',
            color: THEME.textLight,
            margin: 0,
            textShadow: '0 8px 36px rgba(0,0,0,0.85), 0 0 30px rgba(38,198,218,0.45)',
          }}
        >
          CHESS ANALYZER
        </h1>

        {/* Wordless Visual Down-Arrow Cue synced to "Ссылка в описании профиля" */}
        <div
          style={{
            marginTop: 34,
            transform: `scale(${arrowPop}) translateY(${arrowBounce}px)`,
            width: 78,
            height: 78,
            borderRadius: '50%',
            background: 'linear-gradient(180deg, #26c6da 0%, #4caf50 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 35px rgba(38,198,218,0.8)',
            border: '3px solid #ffffff',
          }}
        >
          <svg width="42" height="42" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 4V20M12 20L5 13M12 20L19 13"
              stroke="#071018"
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>

      {/* Hard-Cut Impact Flash Overlay */}
      <AbsoluteFill
        style={{
          background: 'radial-gradient(circle, #ffffff 0%, #26c6da 60%, transparent 100%)',
          opacity: flashOpacity,
          pointerEvents: 'none',
          zIndex: 10,
        }}
      />
    </AbsoluteFill>
  );
};

// --- ROOT COMPOSITION ---
export const MusorDropVideo: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill>
      <Audio src={staticFile('musor_audio.mp3')} />
      <Background intense={frame >= 162} />

      {/* 0.00s - 5.42s (frames 0 - 162): Musor Drop Banner + Visual Chess Showcase */}
      <Sequence from={0} durationInFrames={162}>
        <PreDropShowcaseScene />
      </Sequence>

      {/* 5.42s - 9.46s (frames 162 - 284): Hard Cut on "Chess Analyzer" to Title Reveal */}
      <Sequence from={162} durationInFrames={122}>
        <TitleDropScene />
      </Sequence>
    </AbsoluteFill>
  );
};
