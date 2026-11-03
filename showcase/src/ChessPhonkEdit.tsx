import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

// --- CLEAN VECTOR CHESS PIECES (2D FLAT STREAM/APP STYLE) ---
const PIECES: Record<string, React.ReactNode> = {
  // White Pieces (Pure White with Crisp Dark Contours)
  wK: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="none" fillRule="evenodd" stroke="#0f172a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22.5 11.63V6M20 8h5" stroke="#f8fafc" strokeWidth="3" />
        <path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#f8fafc" stroke="#0f172a" />
        <path d="M11.5 37c5.5 3.5 16.5 3.5 22 0l-1.5-6.5c-4 2-15 2-19 0l-1.5 6.5z" fill="#f8fafc" stroke="#0f172a" />
        <path d="M12 30c6 2.5 15 2.5 21 0l1-5c-3 1.5-19 1.5-22 0l-0 5z" fill="#f8fafc" stroke="#0f172a" />
      </g>
    </svg>
  ),
  wQ: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#f8fafc" stroke="#0f172a" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="6" cy="12" r="2.5" />
        <circle cx="14" cy="9" r="2.5" />
        <circle cx="22.5" cy="8" r="2.5" />
        <circle cx="31" cy="9" r="2.5" />
        <circle cx="39" cy="12" r="2.5" />
        <path d="M9 26c8.5-1.5 18.5-1.5 27 0l2.5-12.5L31 21l-8.5-10L14 21 6.5 13.5 9 26z" />
        <path d="M9 26c0 2 1.5 2 2.5 4 2.5 1 18.5 1 21 0 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-26 0z" />
        <path d="M11 38.5c7 2.5 16 2.5 23 0l-1.5-5.5c-6.5 1.5-13.5 1.5-20 0l-1.5 5.5z" />
      </g>
    </svg>
  ),
  wR: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#f8fafc" stroke="#0f172a" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 39h27v-3H9v3zm3-3v-4h21v4H12zm2-4l1.5-13.5h14L31 32H14zm-3-15h23v-5h-3v2h-4v-2h-4v2h-4v-2h-4v2h-4v-2z" />
      </g>
    </svg>
  ),
  wB: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#f8fafc" stroke="#0f172a" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 36c3.5-1 18.5-1 22 0-1-2.5-3-2.5-4-4-2-1.5-10-1.5-12 0-1 1.5-5 1.5-6 4z" />
        <path d="M15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2z" />
        <circle cx="25" cy="8" r="1.8" />
        <path d="M17.5 26h10M15 30h15m-7.5-14.5v5m-3-2.5h6" stroke="#0f172a" strokeWidth="2" />
      </g>
    </svg>
  ),
  wN: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#f8fafc" stroke="#0f172a" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 10c10.5 1 16.5 8 16 29H15c0-9 10-6.5 8-21" />
        <path d="M24 18c.38 2.91-5.55 7.37-8 9-3 2-2.82 4.34-5 4-1.042-.94 1.41-3.04 0-3-1 0 .19 1.23-1 2-1 0-4.003 1-4-4 0-2 6-12 6-12s1.89-1.9 2-3.5c-.73-.994-.5-2-.5-3 1-1 3 2.5 3 2.5h2s.78-1.992 2.5-3c1 0 1 3 1 3" />
        <circle cx="9.5" cy="25.5" r="1.8" fill="#0f172a" stroke="none" />
      </g>
    </svg>
  ),
  wP: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <path d="M22 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38-1.95 1.12-3.28 3.21-3.28 5.62 0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#f8fafc" stroke="#0f172a" strokeWidth="2.2" />
    </svg>
  ),

  // Black Pieces (Dark Charcoal with Crimson Edge Glow)
  bK: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#111827" stroke="#ef5350" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22.5 11.63V6M20 8h5" />
        <path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" />
        <path d="M11.5 37c5.5 3.5 16.5 3.5 22 0l-1.5-6.5c-4 2-15 2-19 0l-1.5 6.5z" />
        <path d="M12 30c6 2.5 15 2.5 21 0l1-5c-3 1.5-19 1.5-22 0l-0 5z" />
      </g>
    </svg>
  ),
  bQ: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#111827" stroke="#ef5350" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="6" cy="12" r="2.5" />
        <circle cx="14" cy="9" r="2.5" />
        <circle cx="22.5" cy="8" r="2.5" />
        <circle cx="31" cy="9" r="2.5" />
        <circle cx="39" cy="12" r="2.5" />
        <path d="M9 26c8.5-1.5 18.5-1.5 27 0l2.5-12.5L31 21l-8.5-10L14 21 6.5 13.5 9 26z" />
        <path d="M9 26c0 2 1.5 2 2.5 4 2.5 1 18.5 1 21 0 1-2 2.5-2 2.5-4-8.5-1.5-18.5-1.5-26 0z" />
        <path d="M11 38.5c7 2.5 16 2.5 23 0l-1.5-5.5c-6.5 1.5-13.5 1.5-20 0l-1.5 5.5z" />
      </g>
    </svg>
  ),
  bR: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#111827" stroke="#ef5350" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 39h27v-3H9v3zm3-3v-4h21v4H12zm2-4l1.5-13.5h14L31 32H14zm-3-15h23v-5h-3v2h-4v-2h-4v2h-4v-2h-4v2h-4v-2z" />
      </g>
    </svg>
  ),
  bB: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#111827" stroke="#ef5350" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 36c3.5-1 18.5-1 22 0-1-2.5-3-2.5-4-4-2-1.5-10-1.5-12 0-1 1.5-5 1.5-6 4z" />
        <path d="M15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2z" />
        <circle cx="25" cy="8" r="1.8" />
        <path d="M17.5 26h10M15 30h15m-7.5-14.5v5m-3-2.5h6" stroke="#ef5350" strokeWidth="2" />
      </g>
    </svg>
  ),
  bN: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#111827" stroke="#ef5350" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 10c10.5 1 16.5 8 16 29H15c0-9 10-6.5 8-21" />
        <path d="M24 18c.38 2.91-5.55 7.37-8 9-3 2-2.82 4.34-5 4-1.042-.94 1.41-3.04 0-3-1 0 .19 1.23-1 2-1 0-4.003 1-4-4 0-2 6-12 6-12s1.89-1.9 2-3.5c-.73-.994-.5-2-.5-3 1-1 3 2.5 3 2.5h2s.78-1.992 2.5-3c1 0 1 3 1 3" />
        <circle cx="9.5" cy="25.5" r="1.8" fill="#ef5350" stroke="none" />
      </g>
    </svg>
  ),
  bP: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <path d="M22 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38-1.95 1.12-3.28 3.21-3.28 5.62 0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#111827" stroke="#ef5350" strokeWidth="2.4" />
    </svg>
  ),
};

// --- CHESSBOARD TILES & SQUARES DEFINITION ---
// files: 0=a, 1=b, 2=c, 3=d, 4=e, 5=f, 6=g, 7=h
// ranks: 0=8, 1=7, 2=6, 3=5, 4=4, 5=3, 6=2, 7=1
const FILES = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
const RANKS = ['8', '7', '6', '5', '4', '3', '2', '1'];

interface LightSquare {
  row: number;
  col: number;
  color: string;
  intensity: number;
}

// 2D CHESSBOARD WITH GLOWING LIGHT-UP TILES
const Chess2DBoard: React.FC<{ frame: number }> = ({ frame }) => {
  // Move 1: 15. Bxd7+ (Bishop b5 -> d7) - snappy whip frames 175 to 179 (Beat 1)
  // Move 2: 15... Nxd7 (Knight f6 -> d7) - snappy whip frames 255 to 259 (Beat 2)
  // Pre-drop build: pulses at 319, 339, 359
  // Move 3: 16. Qb8+!! (Queen b3 -> b8) - snappy whip frames 375 to 379 (THE MAIN 808 BASS DROP)
  // Move 4: 16... Nxb8 (Knight d7 -> b8) - snappy whip frames 435 to 439 (Beat 4)
  // Move 5: 17. Rd8# (Rook d1 -> d8) - snappy whip frames 495 to 499 (CHECKMATE DROP)

  // Snappy Piece Transitions (3-4 frame whip snaps landing exactly on the drum transients):
  // White Bishop b5 -> d7 (starts [3,1], goes to [1,3])
  const progB = interpolate(frame, [175, 179], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
  const wB_row = interpolate(progB, [0, 1], [3, 1]);
  const wB_col = interpolate(progB, [0, 1], [1, 3]);

  // Black Knight f6 -> d7 (starts [2,5], goes to [1,3])
  const progN1 = interpolate(frame, [255, 259], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
  // Black Knight d7 -> b8 (from [1,3] to [0,1])
  const progN2 = interpolate(frame, [435, 439], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
  const bN_row = frame < 259
    ? interpolate(progN1, [0, 1], [2, 1])
    : interpolate(progN2, [0, 1], [1, 0]);
  const bN_col = frame < 259
    ? interpolate(progN1, [0, 1], [5, 3])
    : interpolate(progN2, [0, 1], [3, 1]);

  // White Queen b3 -> b8 (starts [5,1], goes to [0,1])
  const progQ = interpolate(frame, [375, 379], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad) });
  const wQ_row = interpolate(progQ, [0, 1], [5, 0]);
  const wQ_col = 1;

  // White Rook d1 -> d8 (starts [7,3], goes to [0,3])
  const progR = interpolate(frame, [495, 499], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) });
  const wR_row = interpolate(progR, [0, 1], [7, 0]);
  const wR_col = 3;

  // Active Light-Up Tiles depending on the move and beat:
  const litSquares: LightSquare[] = [];

  if (frame < 179) {
    // Initial tension: Black Queen on e6 [2,4] & White Queen on b3 [5,1]
    litSquares.push({ row: 2, col: 4, color: '#ef5350', intensity: Math.sin(frame * 0.25) * 0.3 + 0.7 });
    litSquares.push({ row: 5, col: 1, color: '#ffd54f', intensity: 0.8 });
  } else if (frame >= 179 && frame < 259) {
    // Move 1: 15. Bxd7+ Check! Origin b5 [3,1], destination d7 [1,3], Black King e8 [0,4]
    litSquares.push({ row: 3, col: 1, color: '#ffd54f', intensity: 0.6 });
    litSquares.push({ row: 1, col: 3, color: '#ffd54f', intensity: 1.0 });
    litSquares.push({ row: 0, col: 4, color: '#ef5350', intensity: 0.8 }); // King in check!
  } else if (frame >= 259 && frame < 379) {
    // Move 2: 15... Nxd7 Knight takes on d7 [1,3].
    // Target b8 [0,1] pulses as the sacrifice square!
    litSquares.push({ row: 1, col: 3, color: '#ef5350', intensity: 0.7 });
    // b8 starts pulsing neon cyan in anticipation of the drop!
    const targetGlow = frame >= 319 ? Math.sin((frame - 319) * 0.45) * 0.5 + 0.5 : 0.2;
    litSquares.push({ row: 0, col: 1, color: '#26c6da', intensity: targetGlow });
  } else if (frame >= 379 && frame < 439) {
    // Move 3: 16. Qb8+!! THE BRILLIANT QUEEN SACRIFICE
    // b3 [5,1] and b8 [0,1] explode with radiant cyan light!
    litSquares.push({ row: 5, col: 1, color: '#26c6da', intensity: 0.85 });
    litSquares.push({ row: 0, col: 1, color: '#26c6da', intensity: 1.0 });
    litSquares.push({ row: 0, col: 4, color: '#ef5350', intensity: 0.9 }); // King in check!
  } else if (frame >= 439 && frame < 499) {
    // Move 4: 16... Nxb8 forced
    litSquares.push({ row: 1, col: 3, color: '#ef5350', intensity: 0.6 });
    litSquares.push({ row: 0, col: 1, color: '#ef5350', intensity: 0.9 });
  } else if (frame >= 499) {
    // Move 5: 17. Rd8# CHECKMATE!!
    litSquares.push({ row: 7, col: 3, color: '#4caf50', intensity: 0.7 });
    litSquares.push({ row: 0, col: 3, color: '#4caf50', intensity: 1.0 }); // Rd8#
    litSquares.push({ row: 0, col: 4, color: '#ef5350', intensity: 1.0 }); // King checkmated!
  }

  const squareSize = 108; // 108 * 8 = 864px

  return (
    <div
      style={{
        width: 900,
        height: 900,
        background: '#090d14',
        borderRadius: 24,
        border: frame >= 378 ? '4px solid #26c6da' : '4px solid rgba(255, 255, 255, 0.2)',
        boxShadow: frame >= 378
          ? '0 0 60px rgba(38,198,218,0.7), 0 20px 60px rgba(0,0,0,0.9)'
          : '0 25px 70px rgba(0,0,0,0.9)',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* 8x8 Board Container */}
      <div
        style={{
          width: 864,
          height: 864,
          display: 'grid',
          gridTemplateColumns: 'repeat(8, 108px)',
          gridTemplateRows: 'repeat(8, 108px)',
          position: 'relative',
          borderRadius: 16,
          overflow: 'hidden',
        }}
      >
        {/* Render 64 Squares with Lighting Engine */}
        {Array.from({ length: 64 }).map((_, idx) => {
          const row = Math.floor(idx / 8);
          const col = idx % 8;
          const isDark = (row + col) % 2 === 1;

          const lit = litSquares.find((s) => s.row === row && s.col === col);
          const baseColor = isDark ? '#141d27' : '#233040';

          let bg = baseColor;
          let shadow = 'none';
          let border = 'none';

          if (lit) {
            bg = `radial-gradient(circle at 50% 50%, ${lit.color}${Math.floor(lit.intensity * 90).toString(16).padStart(2, '0')}, ${baseColor})`;
            shadow = `inset 0 0 24px ${lit.color}, 0 0 20px ${lit.color}88`;
            border = `2px solid ${lit.color}`;
          }

          return (
            <div
              key={idx}
              style={{
                width: 108,
                height: 108,
                background: bg,
                boxShadow: shadow,
                border: border,
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxSizing: 'border-box',
                transition: 'background 0.08s ease',
              }}
            >
              {/* File / Rank coordinates on borders */}
              {col === 0 && (
                <span
                  style={{
                    position: 'absolute',
                    top: 4,
                    left: 6,
                    fontSize: 14,
                    fontWeight: 900,
                    color: isDark ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.25)',
                    fontFamily: 'Montserrat, sans-serif',
                    pointerEvents: 'none',
                  }}
                >
                  {RANKS[row]}
                </span>
              )}
              {row === 7 && (
                <span
                  style={{
                    position: 'absolute',
                    bottom: 4,
                    right: 6,
                    fontSize: 14,
                    fontWeight: 900,
                    color: isDark ? 'rgba(255,255,255,0.35)' : 'rgba(255,255,255,0.25)',
                    fontFamily: 'Montserrat, sans-serif',
                    pointerEvents: 'none',
                  }}
                >
                  {FILES[col]}
                </span>
              )}
            </div>
          );
        })}

        {/* --- ALL 100% LEGAL CHESS PIECES (POSITIONED IN 2D) --- */}

        {/* 1. White King: c1 [7, 2] */}
        <PieceSlot row={7} col={2} piece="wK" />

        {/* 2. White Pawns */}
        <PieceSlot row={6} col={0} piece="wP" />
        <PieceSlot row={6} col={1} piece="wP" />
        <PieceSlot row={6} col={2} piece="wP" />
        <PieceSlot row={4} col={4} piece="wP" />
        <PieceSlot row={6} col={5} piece="wP" />
        <PieceSlot row={6} col={6} piece="wP" />
        <PieceSlot row={6} col={7} piece="wP" />

        {/* 3. White Bishop g5: [3, 6] (Pins the knight!) */}
        <PieceSlot row={3} col={6} piece="wB" />

        {/* 4. White Bishop b5 (Moves to d7 at frame 179, captured at frame 259) */}
        {frame < 259 && (
          <PieceSlot
            row={wB_row}
            col={wB_col}
            piece="wB"
            highlight={frame >= 179 ? '#ffd54f' : undefined}
            scale={frame >= 179 && frame < 186 ? interpolate(frame, [179, 186], [1.3, 1.0]) : 1}
          />
        )}

        {/* 5. White Queen (Moves to b8 at frame 379, captured at frame 439) */}
        {frame < 439 && (
          <PieceSlot
            row={wQ_row}
            col={wQ_col}
            piece="wQ"
            highlight={frame >= 379 ? '#26c6da' : undefined}
            scale={frame >= 379 && frame < 388 ? interpolate(frame, [379, 388], [1.4, 1.0]) : 1}
          />
        )}

        {/* 6. White Rook d1 (Moves to d8# at frame 499) */}
        <PieceSlot
          row={wR_row}
          col={wR_col}
          piece="wR"
          highlight={frame >= 499 ? '#4caf50' : undefined}
          scale={frame >= 499 && frame < 508 ? interpolate(frame, [499, 508], [1.4, 1.0]) : 1}
        />

        {/* --- BLACK PIECES --- */}

        {/* 7. Black King e8: [0, 4] */}
        <PieceSlot
          row={0}
          col={4}
          piece="bK"
          highlight={frame >= 499 ? '#ef5350' : undefined}
          rotation={frame >= 499 ? 90 : 0}
        />

        {/* 8. Black Pawns */}
        <PieceSlot row={1} col={0} piece="bP" />
        <PieceSlot row={3} col={4} piece="bP" />
        <PieceSlot row={1} col={5} piece="bP" />
        <PieceSlot row={1} col={6} piece="bP" />
        <PieceSlot row={1} col={7} piece="bP" />

        {/* 9. Black Bishop f8: [0, 5] */}
        <PieceSlot row={0} col={5} piece="bB" />

        {/* 10. Black Rook h8: [0, 7] */}
        <PieceSlot row={0} col={7} piece="bR" />

        {/* 11. Black Queen e6: [2, 4] */}
        <PieceSlot row={2} col={4} piece="bQ" />

        {/* 12. Black Rook d7: [1, 3] (Captured at frame 179) */}
        {frame < 179 && <PieceSlot row={1} col={3} piece="bR" />}

        {/* 13. Black Knight (f6 -> d7 at frame 259, d7 -> b8 at frame 439) */}
        <PieceSlot
          row={bN_row}
          col={bN_col}
          piece="bN"
          highlight={frame >= 439 ? '#26c6da' : undefined}
          scale={(frame >= 259 && frame < 267) || (frame >= 439 && frame < 447) ? 1.3 : 1}
        />
      </div>
    </div>
  );
};

// Helper component to cleanly position pieces by (row, col)
const PieceSlot: React.FC<{
  row: number;
  col: number;
  piece: string;
  highlight?: string;
  scale?: number;
  rotation?: number;
}> = ({ row, col, piece, highlight, scale = 1, rotation = 0 }) => {
  return (
    <div
      style={{
        position: 'absolute',
        width: 108,
        height: 108,
        top: row * 108,
        left: col * 108,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 10,
        transform: `scale(${scale}) rotate(${rotation}deg)`,
        filter: highlight ? `drop-shadow(0 0 16px ${highlight})` : 'none',
        zIndex: scale > 1 ? 25 : 10,
        boxSizing: 'border-box',
        pointerEvents: 'none',
      }}
    >
      {PIECES[piece]}
    </div>
  );
};

// --- DYNAMIC EVALUATION BAR COMPONENT ---
const EvalBar: React.FC<{ frame: number }> = ({ frame }) => {
  // Reversal happens ON THE EXACT BEAT DROP at frame 379
  const reversalSpring = spring({
    frame: Math.max(0, frame - 379),
    fps: 30,
    config: { damping: 9, mass: 0.45, stiffness: 220 },
  });

  const isLanded = frame >= 379;

  // Before drop: 12% white / 88% black (-9.5)
  // After drop: rockets to 100% white (+M1 forced checkmate)
  const evalPercent = !isLanded
    ? interpolate(frame, [0, 40], [50, 10], { extrapolateRight: 'clamp' })
    : interpolate(reversalSpring, [0, 1], [10, 100]);

  const evalText = !isLanded ? '-9.5' : (frame >= 499 ? '# 1-0' : '+M1');

  return (
    <div
      style={{
        width: 900,
        height: 60,
        background: 'rgba(10, 16, 24, 0.95)',
        border: isLanded ? '3px solid #26c6da' : '2px solid rgba(255,255,255,0.2)',
        borderRadius: 20,
        boxShadow: isLanded
          ? '0 0 40px rgba(38, 198, 218, 0.85), inset 0 0 20px rgba(38, 198, 218, 0.3)'
          : '0 8px 30px rgba(0,0,0,0.8)',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        padding: 4,
        boxSizing: 'border-box',
      }}
    >
      {/* Sinking Red Fill vs Rising White/Cyan Fill */}
      <div
        style={{
          width: `${evalPercent}%`,
          height: '100%',
          background: isLanded
            ? (frame >= 499 ? 'linear-gradient(90deg, #4caf50 0%, #26c6da 50%, #ffffff 100%)' : 'linear-gradient(90deg, #26c6da 0%, #ffffff 100%)')
            : 'linear-gradient(90deg, #1e293b 0%, #ffffff 100%)',
          borderRadius: 14,
          boxShadow: isLanded ? (frame >= 499 ? '0 0 25px #4caf50' : '0 0 25px #26c6da') : 'none',
        }}
      />

      {/* Floating Eval Text Tag */}
      <div
        style={{
          position: 'absolute',
          left: 24,
          fontFamily: 'Montserrat, sans-serif',
          fontSize: 24,
          fontWeight: 900,
          color: isLanded ? '#071018' : '#ffffff',
          letterSpacing: '1px',
          zIndex: 5,
        }}
      >
        WHITE: {evalText}
      </div>

      <div
        style={{
          position: 'absolute',
          right: 24,
          fontFamily: 'Montserrat, sans-serif',
          fontSize: 20,
          fontWeight: 800,
          color: frame >= 499 ? '#4caf50' : (isLanded ? '#26c6da' : '#ef5350'),
          letterSpacing: '1px',
          zIndex: 5,
        }}
      >
        {isLanded ? (frame >= 499 ? 'WHITE WINS BY CHECKMATE' : 'CHECKMATE IN 2 (FORCED)') : 'BLACK WIN ADVANTAGE'}
      </div>
    </div>
  );
};

// --- MAIN 9:16 CHESS PHONK EDIT COMPOSITION (1080x1920) ---
export const ChessPhonkEditVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Exact 20-frame phonk beat grid in LAST CHANCE FUNK (Slowed, ~90 BPM):
  // 179: Bishop Check (15. Bxd7+)
  // 259: Knight Recapture (15... Nxd7)
  // 319, 339: Build-up snares
  // 359: Pre-drop snare slam
  // 379: THE MAIN BASS DROP (16. Qb8+!! Queen Sacrifice)
  // 399, 419: Post-drop driving bass
  // 439: Knight Recapture (16... Nxb8)
  // 459, 479: Driving bass
  // 499: Rook Checkmate (17. Rd8#)
  // 519, 539: Victory bass
  // 559: Outro Slam
  const allBeats = [179, 259, 319, 339, 359, 379, 399, 419, 439, 459, 479, 499, 519, 539, 559];

  // Beat Zoom Punch (signature phonk beat pump)
  let beatZoom = 1.0;
  for (const b of allBeats) {
    if (frame >= b && frame < b + 6) {
      const p = (frame - b) / 6;
      const intensity = b === 379 ? 0.08 : (b === 359 || b === 439 || b === 499 ? 0.045 : 0.025);
      beatZoom += (1 - p) * intensity;
    }
  }

  // Camera Shake on heavy hits
  const heavyDrops = [359, 379, 439, 499, 559];
  let shakeIntensity = 0;
  heavyDrops.forEach((d) => {
    if (frame >= d && frame < d + 14) {
      const decay = (d + 14 - frame) / 14;
      shakeIntensity = Math.max(shakeIntensity, (d === 379 ? 34 : (d === 359 ? 18 : 16)) * decay);
    }
  });

  const shakeX = Math.sin(frame * 2.2) * shakeIntensity;
  const shakeY = Math.cos(frame * 2.4) * shakeIntensity;

  // White Flash on the drop at frame 379 and snare at 359
  const flashOpacity =
    frame >= 379 && frame < 396
      ? interpolate(frame, [379, 396], [0.95, 0], { extrapolateRight: 'clamp' })
      : (frame >= 359 && frame < 365
          ? interpolate(frame, [359, 365], [0.35, 0], { extrapolateRight: 'clamp' })
          : 0);

  // Shockwave ring on the drop
  const shockwave =
    frame >= 379 && frame < 415
      ? spring({ frame: frame - 379, fps, config: { damping: 10, mass: 0.5 } })
      : 0;

  // Brilliant (!!) Badge Scale & Slam
  const brilliantSlam =
    frame >= 379 && frame < 439
      ? spring({ frame: frame - 379, fps, config: { damping: 11, mass: 0.5, stiffness: 240 } })
      : 0;

  // Dynamic Typography & Narrative
  let mainText = 'HE THOUGHT THE QUEEN WAS TRAPPED';
  let subText = 'EVALUATION: -9.5';
  let textColor = '#ef5350';

  if (frame >= 179 && frame < 259) {
    mainText = '15. Bxd7+ !!';
    subText = 'SACRIFICING THE BISHOP';
    textColor = '#ffd54f';
  } else if (frame >= 259 && frame < 359) {
    mainText = 'HE THOUGHT HE WAS SAFE...';
    subText = 'STOCKFISH 19 CALCULATING MATE';
    textColor = '#ffffff';
  } else if (frame >= 359 && frame < 379) {
    mainText = 'WAIT FOR IT...';
    subText = 'STOCKFISH CALCULATING 100%';
    textColor = '#26c6da';
  } else if (frame >= 379 && frame < 439) {
    mainText = '16. Qb8+ !! — BRILLIANT';
    subText = 'THE IMMORTAL QUEEN SACRIFICE';
    textColor = '#26c6da';
  } else if (frame >= 439 && frame < 499) {
    mainText = '16... Nxb8 (FORCED)';
    subText = 'ONLY ONE LEGAL MOVE';
    textColor = '#ffd54f';
  } else if (frame >= 499 && frame < 559) {
    mainText = '17. Rd8 # — CHECKMATE';
    subText = 'MORPHY OPERA IMMORTAL MATE';
    textColor = '#4caf50';
  } else if (frame >= 559) {
    mainText = 'CHESS ANALYZER';
    subText = 'NEVER MISS A BRILLIANT SACRIFICE';
    textColor = '#26c6da';
  }

  return (
    <AbsoluteFill
      style={{
        background: '#04070b',
        overflow: 'hidden',
        transform: `translate(${shakeX}px, ${shakeY}px) scale(${beatZoom})`,
      }}
    >
      <Audio src={staticFile('phonk_track.mp3')} />

      {/* Cyber Grid Background */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(circle at 50% 50%, #0d1622 0%, #06090e 70%, #020305 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `linear-gradient(to right, rgba(38,198,218,0.04) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(38,198,218,0.04) 1px, transparent 1px)`,
          backgroundSize: '70px 70px',
          backgroundPosition: `0px ${(frame * 2) % 70}px`,
          pointerEvents: 'none',
        }}
      />

      {/* Red Warning Vignette prior to the drop */}
      {frame < 379 && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(circle, transparent 40%, rgba(229,57,53,0.3) 100%)',
            opacity: Math.sin(frame * 0.3) * 0.4 + 0.6,
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Top Header: Stockfish 19 & Dynamic Eval Bar */}
      <div
        style={{
          position: 'absolute',
          top: 70,
          left: 0,
          right: 0,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 16,
          zIndex: 40,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            background: 'rgba(15, 23, 42, 0.9)',
            border: '2px solid rgba(255,255,255,0.2)',
            borderRadius: 30,
            padding: '8px 28px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
          }}
        >
          <div
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: frame >= 378 ? '#26c6da' : '#ef5350',
              boxShadow: `0 0 14px ${frame >= 378 ? '#26c6da' : '#ef5350'}`,
            }}
          />
          <span
            style={{
              fontFamily: 'Montserrat, sans-serif',
              fontSize: 22,
              fontWeight: 900,
              color: '#f8fafc',
              letterSpacing: '2px',
            }}
          >
            STOCKFISH 19 • DEPTH {Math.min(36, Math.floor(14 + frame * 0.07))}
          </span>
        </div>

        <EvalBar frame={frame} />
      </div>

      {/* Center Flat 2D Chessboard with Glowing Tiles */}
      <div
        style={{
          position: 'absolute',
          top: '49%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          zIndex: 20,
        }}
      >
        <Chess2DBoard frame={frame} />
      </div>

      {/* Shockwave Blast Ring on Bass Drop */}
      {frame >= 379 && frame < 415 && (
        <div
          style={{
            position: 'absolute',
            top: '49%',
            left: '50%',
            transform: `translate(-50%, -50%) scale(${shockwave * 4.5})`,
            width: 300,
            height: 300,
            borderRadius: '50%',
            border: '8px solid rgba(38,198,218,0.95)',
            boxShadow: '0 0 60px rgba(38,198,218,0.95), inset 0 0 40px rgba(38,198,218,0.5)',
            opacity: 1 - shockwave,
            pointerEvents: 'none',
            zIndex: 45,
          }}
        />
      )}

      {/* Giant Brilliant (!!) Badge Slam at Frame 379 */}
      {frame >= 379 && frame < 439 && (
        <div
          style={{
            position: 'absolute',
            top: '49%',
            left: '50%',
            transform: `translate(-50%, -50%) scale(${Math.max(0.6, brilliantSlam)})`,
            zIndex: 60,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            filter: 'drop-shadow(0 0 50px #26c6da)',
          }}
        >
          <Img src={staticFile('icons/brilliant.png')} style={{ width: 260, height: 260 }} />
          <div
            style={{
              fontFamily: 'Montserrat, Impact, sans-serif',
              fontSize: 64,
              fontWeight: 900,
              color: '#ffffff',
              letterSpacing: '3px',
              textShadow: '0 0 35px #26c6da, 0 6px 16px rgba(0,0,0,0.9)',
              marginTop: 18,
            }}
          >
            BRILLIANT !!
          </div>
        </div>
      )}

      {/* Checkmate Victory Stamp at Frame 499+ */}
      {frame >= 499 && frame < 559 && (
        <div
          style={{
            position: 'absolute',
            top: '49%',
            left: '50%',
            transform: `translate(-50%, -50%) scale(${spring({ frame: frame - 499, fps, config: { damping: 9, mass: 0.5 } })})`,
            zIndex: 60,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            filter: 'drop-shadow(0 0 60px #4caf50)',
          }}
        >
          <Img src={staticFile('icons/checkmate_white.png')} style={{ width: 260, height: 260 }} />
          <div
            style={{
              fontFamily: 'Montserrat, Impact, sans-serif',
              fontSize: 70,
              fontWeight: 900,
              color: '#4caf50',
              letterSpacing: '4px',
              textShadow: '0 0 40px #4caf50, 0 6px 20px rgba(0,0,0,0.9)',
              marginTop: 18,
            }}
          >
            CHECKMATE #
          </div>
        </div>
      )}

      {/* Bottom Bold Phonk Typography HUD */}
      {frame < 559 && (
        <div
          style={{
            position: 'absolute',
            bottom: 120,
            left: 0,
            right: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            padding: '0 40px',
            zIndex: 50,
          }}
        >
          <div
            style={{
              background: 'rgba(6, 12, 19, 0.94)',
              border: `3px solid ${textColor}44`,
              boxShadow: `0 20px 60px rgba(0,0,0,0.9), 0 0 30px ${textColor}33`,
              borderRadius: 24,
              padding: '20px 48px',
              maxWidth: 960,
            }}
          >
            <div
              style={{
                fontFamily: 'Montserrat, Impact, sans-serif',
                fontSize: 54,
                fontWeight: 900,
                color: textColor,
                letterSpacing: '2px',
                lineHeight: 1.2,
                textShadow: `0 0 25px ${textColor}`,
                marginBottom: 10,
              }}
            >
              {mainText}
            </div>
            <div
              style={{
                fontFamily: 'Montserrat, sans-serif',
                fontSize: 26,
                fontWeight: 800,
                color: '#f8fafc',
                letterSpacing: '3px',
                opacity: 0.9,
              }}
            >
              {subText}
            </div>
          </div>
        </div>
      )}

      {/* Outro Screen (frames 559 - 630 / 18.63s - 21.0s) */}
      {frame >= 559 && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(4, 7, 11, 0.96)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 70,
            transform: `scale(${spring({ frame: frame - 559, fps, config: { damping: 11, mass: 0.55 } })})`,
          }}
        >
          <Img
            src={staticFile('icon.png')}
            style={{
              width: 220,
              height: 220,
              borderRadius: 50,
              border: '4px solid #26c6da',
              boxShadow: '0 0 60px rgba(38,198,218,0.8), 0 20px 50px rgba(0,0,0,0.8)',
              marginBottom: 32,
            }}
          />

          <h1
            style={{
              fontFamily: 'Montserrat, sans-serif',
              fontSize: 72,
              fontWeight: 900,
              color: '#f8fafc',
              margin: '0 0 16px 0',
              letterSpacing: '3px',
              textShadow: '0 0 35px rgba(38,198,218,0.6)',
            }}
          >
            CHESS ANALYZER
          </h1>

          <div
            style={{
              fontFamily: 'Montserrat, sans-serif',
              fontSize: 34,
              fontWeight: 800,
              color: '#ffd54f',
              letterSpacing: '2px',
              marginBottom: 44,
              textAlign: 'center',
            }}
          >
            NEVER MISS A BRILLIANT SACRIFICE
          </div>

          <div
            style={{
              display: 'flex',
              gap: 16,
              background: 'rgba(255,255,255,0.08)',
              border: '2px solid rgba(255,255,255,0.2)',
              borderRadius: 30,
              padding: '14px 42px',
              boxShadow: '0 10px 30px rgba(0,0,0,0.7)',
            }}
          >
            <span style={{ fontFamily: 'Montserrat, sans-serif', fontSize: 26, fontWeight: 800, color: '#f8fafc', letterSpacing: '1.5px' }}>
              💻 STANDALONE WINDOWS .EXE
            </span>
          </div>
        </div>
      )}

      {/* White Beat Flash Effect */}
      {flashOpacity > 0 && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: '#ffffff',
            opacity: flashOpacity,
            pointerEvents: 'none',
            zIndex: 100,
          }}
        />
      )}
    </AbsoluteFill>
  );
};
