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

// --- PIECE GRAPHICS (SVG) ---
const PIECES: Record<string, React.ReactNode> = {
  // White Pieces
  wK: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="none" fillRule="evenodd" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22.5 11.63V6M20 8h5" stroke="#f8fafc" strokeWidth="2.5" />
        <path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" fill="#f8fafc" stroke="#f8fafc" />
        <path d="M11.5 37c5.5 3.5 16.5 3.5 22 0l-1.5-6.5c-4 2-15 2-19 0l-1.5 6.5z" fill="#f8fafc" stroke="#f8fafc" />
        <path d="M12 30c6 2.5 15 2.5 21 0l1-5c-3 1.5-19 1.5-22 0l-0 5z" fill="#f8fafc" stroke="#f8fafc" />
      </g>
    </svg>
  ),
  wQ: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#f8fafc" stroke="#f8fafc" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
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
      <g fill="#f8fafc" stroke="#f8fafc" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 39h27v-3H9v3zm3-3v-4h21v4H12zm2-4l1.5-13.5h14L31 32H14zm-3-15h23v-5h-3v2h-4v-2h-4v2h-4v-2h-4v2h-4v-2z" />
      </g>
    </svg>
  ),
  wB: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#f8fafc" stroke="#f8fafc" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 36c3.5-1 18.5-1 22 0-1-2.5-3-2.5-4-4-2-1.5-10-1.5-12 0-1 1.5-5 1.5-6 4z" />
        <path d="M15 32c2.5 2.5 12.5 2.5 15 0 .5-1.5 0-2 0-2 0-2.5-2.5-4-2.5-4 5.5-1.5 6-11.5-5-15.5-11 4-10.5 14-5 15.5 0 0-2.5 1.5-2.5 4 0 0-.5.5 0 2z" />
        <circle cx="25" cy="8" r="1.8" />
        <path d="M17.5 26h10M15 30h15m-7.5-14.5v5m-3-2.5h6" stroke="#0e1724" strokeWidth="2" />
      </g>
    </svg>
  ),
  wN: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#f8fafc" stroke="#f8fafc" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 10c10.5 1 16.5 8 16 29H15c0-9 10-6.5 8-21" />
        <path d="M24 18c.38 2.91-5.55 7.37-8 9-3 2-2.82 4.34-5 4-1.042-.94 1.41-3.04 0-3-1 0 .19 1.23-1 2-1 0-4.003 1-4-4 0-2 6-12 6-12s1.89-1.9 2-3.5c-.73-.994-.5-2-.5-3 1-1 3 2.5 3 2.5h2s.78-1.992 2.5-3c1 0 1 3 1 3" />
        <circle cx="9.5" cy="25.5" r="1.5" fill="#0e1724" stroke="none" />
      </g>
    </svg>
  ),
  wP: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <path d="M22 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38-1.95 1.12-3.28 3.21-3.28 5.62 0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#f8fafc" stroke="#f8fafc" strokeWidth="2" />
    </svg>
  ),

  // Black Pieces
  bK: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#18202c" stroke="#ef5350" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22.5 11.63V6M20 8h5" />
        <path d="M22.5 25s4.5-7.5 3-10.5c0 0-1-2.5-3-2.5s-3 2.5-3 2.5c-1.5 3 3 10.5 3 10.5" />
        <path d="M11.5 37c5.5 3.5 16.5 3.5 22 0l-1.5-6.5c-4 2-15 2-19 0l-1.5 6.5z" />
        <path d="M12 30c6 2.5 15 2.5 21 0l1-5c-3 1.5-19 1.5-22 0l-0 5z" />
      </g>
    </svg>
  ),
  bQ: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#18202c" stroke="#ef5350" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="6" cy="12" r="2.5" />
        <circle cx="14" cy="9" r="2.5" />
        <circle cx="22.5" cy="8" r="2.5" />
        <circle cx="31" cy="9" r="2.5" />
        <circle cx="39" cy="12" r="2.5" />
        <path d="M9 26c8.5-1.5 18.5-1.5 27 0l2.5-12.5L31 21l-8.5-10L14 21 6.5 13.5 9 26z" />
        <path d="M11 38.5c7 2.5 16 2.5 23 0l-1.5-5.5c-6.5 1.5-13.5 1.5-20 0l-1.5 5.5z" />
      </g>
    </svg>
  ),
  bR: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <g fill="#18202c" stroke="#ef5350" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 39h27v-3H9v3zm3-3v-4h21v4H12zm2-4l1.5-13.5h14L31 32H14zm-3-15h23v-5h-3v2h-4v-2h-4v2h-4v-2h-4v2h-4v-2z" />
      </g>
    </svg>
  ),
  bP: (
    <svg viewBox="0 0 45 45" width="100%" height="100%">
      <path d="M22 9c-2.21 0-4 1.79-4 4 0 .89.29 1.71.78 2.38-1.95 1.12-3.28 3.21-3.28 5.62 0 2.03.94 3.84 2.41 5.03-3 1.06-7.41 5.55-7.41 13.47h23c0-7.92-4.41-12.41-7.41-13.47 1.47-1.19 2.41-3 2.41-5.03 0-2.41-1.33-4.5-3.28-5.62.49-.67.78-1.49.78-2.38 0-2.21-1.79-4-4-4z" fill="#18202c" stroke="#ef5350" strokeWidth="2.2" />
    </svg>
  ),
};

// --- CHESSBOARD COMPONENT ---
interface BoardProps {
  frame: number;
}

const ChessEditBoard: React.FC<BoardProps> = ({ frame }) => {
  // Key Animation Milestones:
  // frame 24 (0.8s): Black Queen takes bait on f7
  // frame 357 (11.9s): BEAT DROP! White Knight sacrifices Nf6+!!
  // frame 465 (15.5s): Black Pawn forced gxf6
  // frame 495 (16.5s): White Bishop checks Bh6+!
  // frame 525 (17.5s): Black King retreats Kg8
  // frame 555 (18.5s): White Rook delivers Re8# CHECKMATE!!

  // Piece Positions: row 0 = rank 8, row 7 = rank 1; col 0 = file a, col 7 = file h
  // Standard tactical board coordinates:
  // e8 = [0, 4], f8 = [0, 5], g8 = [0, 6], h8 = [0, 7]
  // f7 = [1, 5], g7 = [1, 6], h7 = [1, 7]
  // f6 = [2, 5], h6 = [2, 7]
  // e1 = [7, 4], e8 = [0, 4]

  // Animated Piece Movements
  // 1. Black Queen takes f7 (frame 15 to 26)
  const bQPos = frame < 24 ? { r: 1, c: 3 } : { r: 1, c: 5 };

  // 2. White Knight from d5 to f6 (frame 348 to 357)
  const knightProgress = interpolate(frame, [346, 357], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.back(1.5)),
  });
  const wN_r = interpolate(knightProgress, [0, 1], [3, 2]); // row 3 to 2
  const wN_c = interpolate(knightProgress, [0, 1], [3, 5]); // col 3 to 5 (f6)

  // 3. Black Pawn gxf6 (frame 455 to 465)
  const bP_gxf6 = frame >= 465;

  // 4. White Bishop to h6 (frame 485 to 495)
  const bishopProgress = interpolate(frame, [485, 495], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.quad),
  });
  const wB_r = interpolate(bishopProgress, [0, 1], [5, 2]); // c1 to h6
  const wB_c = interpolate(bishopProgress, [0, 1], [2, 7]);

  // 5. Black King from e8 to g8 / h8 (frame 515 to 525)
  const bK_r = 0;
  const bK_c = frame < 525 ? 4 : 7; // e8 -> h8

  // 6. White Rook from e1 to e8# (frame 545 to 555)
  const rookProgress = interpolate(frame, [545, 555], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });
  const wR_r = interpolate(rookProgress, [0, 1], [7, 0]); // e1 -> e8
  const wR_c = 4;

  const squares = [
    // Rank 8
    [{ r: 0, c: 4 }, 'bK', bK_r === 0 && bK_c === 4],
    [{ r: 0, c: 7 }, 'bK', bK_c === 7],
    [{ r: 0, c: 0 }, 'bR', true],
    [{ r: 0, c: 5 }, 'bR', frame < 400],
    // Rank 7
    [{ r: 1, c: 5 }, 'bQ', frame >= 24 && frame < 357],
    [{ r: 1, c: 6 }, 'bP', !bP_gxf6],
    [{ r: 1, c: 7 }, 'bP', true],
    // Rank 6 (f6 target)
    [{ r: 2, c: 5 }, bP_gxf6 ? 'bP' : 'wN', frame >= 357],
    [{ r: wB_r, c: wB_c }, 'wB', true],
    // Rank 1
    [{ r: wR_r, c: wR_c }, 'wR', true],
    [{ r: 7, c: 6 }, 'wK', true],
  ];

  return (
    <div
      style={{
        width: 820,
        height: 820,
        borderRadius: 32,
        background: '#0d131a',
        border: '6px solid rgba(255, 255, 255, 0.15)',
        boxShadow: frame >= 357
          ? '0 0 60px rgba(38, 198, 218, 0.6), 0 30px 90px rgba(0,0,0,0.95)'
          : '0 25px 80px rgba(0,0,0,0.85)',
        display: 'grid',
        gridTemplateColumns: 'repeat(8, 1fr)',
        gridTemplateRows: 'repeat(8, 1fr)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* 64 Board Squares */}
      {Array.from({ length: 64 }).map((_, idx) => {
        const row = Math.floor(idx / 8);
        const col = idx % 8;
        const isDark = (row + col) % 2 === 1;

        // Highlight square of interest
        const isF6 = row === 2 && col === 5;
        const isCheckmated = frame >= 555 && row === 0 && col === 7;

        return (
          <div
            key={idx}
            style={{
              background: isCheckmated
                ? '#e53935'
                : isF6 && frame >= 357 && frame < 450
                ? '#26c6da'
                : isDark
                ? '#1e293b'
                : '#334155',
              boxShadow: isF6 && frame >= 357 ? 'inset 0 0 25px rgba(255,255,255,0.8)' : 'none',
              transition: 'background 0.1s ease',
            }}
          />
        );
      })}

      {/* Render Dynamic Moving Pieces */}
      {/* 1. Black Queen */}
      {frame >= 24 && frame < 357 && (
        <div
          style={{
            position: 'absolute',
            width: 102.5,
            height: 102.5,
            top: bQPos.r * 102.5,
            left: bQPos.c * 102.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 10,
          }}
        >
          {PIECES.bQ}
        </div>
      )}

      {/* 2. White Knight (Sacrifice to f6) */}
      {frame < 465 && (
        <div
          style={{
            position: 'absolute',
            width: 102.5,
            height: 102.5,
            top: wN_r * 102.5,
            left: wN_c * 102.5,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 8,
            filter: frame >= 357 ? 'drop-shadow(0 0 20px #26c6da)' : 'none',
            zIndex: 10,
          }}
        >
          {PIECES.wN}
        </div>
      )}

      {/* 3. Black King */}
      <div
        style={{
          position: 'absolute',
          width: 102.5,
          height: 102.5,
          top: bK_r * 102.5,
          left: bK_c * 102.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 8,
          transform: frame >= 555 ? 'rotate(90deg) translateY(20px)' : 'none',
          transition: 'transform 0.2s ease',
        }}
      >
        {PIECES.bK}
      </div>

      {/* 4. White Bishop */}
      <div
        style={{
          position: 'absolute',
          width: 102.5,
          height: 102.5,
          top: wB_r * 102.5,
          left: wB_c * 102.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 8,
          filter: frame >= 495 ? 'drop-shadow(0 0 16px #ffd54f)' : 'none',
        }}
      >
        {PIECES.wB}
      </div>

      {/* 5. White Rook (Delivering Checkmate) */}
      <div
        style={{
          position: 'absolute',
          width: 102.5,
          height: 102.5,
          top: wR_r * 102.5,
          left: wR_c * 102.5,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 8,
          filter: frame >= 555 ? 'drop-shadow(0 0 25px #4caf50)' : 'none',
          zIndex: 15,
        }}
      >
        {PIECES.wR}
      </div>

      {/* 6. Static / Defending pawns */}
      <div style={{ position: 'absolute', top: 102.5, left: 7 * 102.5, width: 102.5, height: 102.5, padding: 12 }}>
        {PIECES.bP}
      </div>
      {!bP_gxf6 && (
        <div style={{ position: 'absolute', top: 102.5, left: 6 * 102.5, width: 102.5, height: 102.5, padding: 12 }}>
          {PIECES.bP}
        </div>
      )}
      {bP_gxf6 && (
        <div style={{ position: 'absolute', top: 2 * 102.5, left: 5 * 102.5, width: 102.5, height: 102.5, padding: 12 }}>
          {PIECES.bP}
        </div>
      )}
    </div>
  );
};

// --- DYNAMIC EVALUATION BAR COMPONENT ---
const EvalBar: React.FC<{ frame: number }> = ({ frame }) => {
  // Before drop (frame < 357): Eval bar is deeply negative (-9.5) / 95% black
  // Exactly at frame 357: Explosively reverses to +M1 / 100% white!
  const reversalSpring = spring({
    frame: Math.max(0, frame - 357),
    fps: 30,
    config: { damping: 9, mass: 0.45, stiffness: 210 },
  });

  const evalPercent = frame < 357
    ? interpolate(frame, [0, 60], [50, 6], { extrapolateRight: 'clamp' })
    : interpolate(reversalSpring, [0, 1], [6, 100]);

  const evalText = frame < 357
    ? (frame < 30 ? '0.0' : '-9.5')
    : '+M1';

  const isBrilliant = frame >= 357;

  return (
    <div
      style={{
        width: 860,
        height: 64,
        background: 'rgba(10, 16, 24, 0.95)',
        border: isBrilliant ? '3px solid #26c6da' : '2px solid rgba(255,255,255,0.2)',
        borderRadius: 20,
        boxShadow: isBrilliant
          ? '0 0 35px rgba(38, 198, 218, 0.8), inset 0 0 20px rgba(38, 198, 218, 0.3)'
          : '0 8px 30px rgba(0,0,0,0.8)',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        padding: 4,
      }}
    >
      {/* Sinking Red Fill vs Rising White/Cyan Fill */}
      <div
        style={{
          width: `${evalPercent}%`,
          height: '100%',
          background: isBrilliant
            ? 'linear-gradient(90deg, #26c6da 0%, #ffffff 100%)'
            : 'linear-gradient(90deg, #1e293b 0%, #ffffff 100%)',
          borderRadius: 14,
          transition: 'width 0.05s ease',
          boxShadow: isBrilliant ? '0 0 25px #26c6da' : 'none',
        }}
      />

      {/* Floating Eval Text Tag */}
      <div
        style={{
          position: 'absolute',
          left: 24,
          fontFamily: 'Montserrat, sans-serif',
          fontSize: 26,
          fontWeight: 900,
          color: isBrilliant ? '#071018' : '#ffffff',
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
          fontSize: 22,
          fontWeight: 800,
          color: '#ef5350',
          letterSpacing: '1px',
          zIndex: 5,
        }}
      >
        {isBrilliant ? 'CHECKMATE FORCED' : 'BLUNDER DETECTED'}
      </div>
    </div>
  );
};

// --- MAIN CHESS PHONK EDIT COMPOSITION (9:16 / 1080x1920) ---
export const ChessPhonkEditVideo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 1. Bass Hit Camera Shake Engine
  // Beat transients:
  // frame 357 (11.90s) - THE DROP
  // frame 465 (15.50s) - BEAT 1
  // frame 495 (16.50s) - BEAT 2
  // frame 525 (17.50s) - BEAT 3
  // frame 555 (18.50s) - BEAT 4 (MATE)
  let shakeIntensity = 0;
  const drops = [357, 465, 495, 525, 555];
  drops.forEach((d, idx) => {
    if (frame >= d && frame < d + 18) {
      const decay = (d + 18 - frame) / 18;
      shakeIntensity = Math.max(shakeIntensity, (idx === 0 ? 32 : 18) * decay);
    }
  });

  const shakeX = Math.sin(frame * 1.8) * shakeIntensity;
  const shakeY = Math.cos(frame * 1.9) * shakeIntensity;

  // 2. White Flash at the drop (frame 357)
  const flashOpacity = frame >= 357 && frame < 375
    ? interpolate(frame, [357, 375], [1, 0], { extrapolateRight: 'clamp' })
    : 0;

  // 3. Shockwave ring at frame 357
  const shockwave = frame >= 357 && frame < 390
    ? spring({ frame: frame - 357, fps, config: { damping: 10, mass: 0.5 } })
    : 0;

  // 4. Brilliant (!!) Badge Scale & Slam
  const brilliantSlam = frame >= 357 && frame < 450
    ? spring({ frame: frame - 357, fps, config: { damping: 11, mass: 0.5, stiffness: 240 } })
    : 0;

  // 5. 3D Camera tilt angle
  const boardRotateX = interpolate(frame, [0, 357, 555], [38, 42, 28], { extrapolateRight: 'clamp' });
  const boardRotateZ = interpolate(frame, [0, 357, 555], [-8, 6, -4], { extrapolateRight: 'clamp' });
  const boardZoom = interpolate(frame, [315, 356], [1, 1.25], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // 6. Dynamic On-Screen Sigma Phonk Text Overlays
  let mainText = 'HE THOUGHT THE QUEEN WAS FREE';
  let subText = 'BLACK ADVANTAGE: -9.5';
  let textColor = '#ef5350';

  if (frame >= 165 && frame < 315) {
    mainText = "HE DIDN'T CALCULATE AHEAD";
    subText = 'STOCKFISH 19 DEPTH 36';
    textColor = '#ffd54f';
  } else if (frame >= 315 && frame < 357) {
    mainText = 'WAIT FOR THE SACRIFICE...';
    subText = 'CALCULATING 100% FORCED MATE';
    textColor = '#ffffff';
  } else if (frame >= 357 && frame < 450) {
    mainText = 'BRILLIANT MOVE !!';
    subText = 'QUEEN SACRIFICE ACCELERATION';
    textColor = '#26c6da';
  } else if (frame >= 450 && frame < 555) {
    mainText = 'FORCED CHECKMATE SEQUENCE';
    subText = 'EVERY MOVE IS FORCED';
    textColor = '#4caf50';
  } else if (frame >= 555) {
    mainText = 'CHESS ANALYZER';
    subText = 'NEVER MISS A BRILLIANT SACRIFICE';
    textColor = '#26c6da';
  }

  return (
    <AbsoluteFill
      style={{
        background: '#04070b',
        overflow: 'hidden',
        transform: `translate(${shakeX}px, ${shakeY}px)`,
      }}
    >
      <Audio src={staticFile('phonk_track.mp3')} />

      {/* Animated Phonk Neon Cyber Grid */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(circle at 50% 45%, #101c2a 0%, #060a0f 70%, #020406 100%)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `linear-gradient(to right, rgba(38,198,218,0.05) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(38,198,218,0.05) 1px, transparent 1px)`,
          backgroundSize: '80px 80px',
          backgroundPosition: `0px ${(frame * 2.5) % 80}px`,
          pointerEvents: 'none',
        }}
      />

      {/* Red Pulse / Heartbeat Vignette for the Bait phase */}
      {frame < 357 && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(circle, transparent 40%, rgba(229,57,53,0.38) 100%)',
            opacity: Math.sin(frame * 0.35) * 0.4 + 0.6,
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Top Header: Stockfish 19 & Dynamic Eval Bar */}
      <div
        style={{
          position: 'absolute',
          top: 80,
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
            background: 'rgba(15, 23, 42, 0.85)',
            border: '2px solid rgba(255,255,255,0.2)',
            borderRadius: 30,
            padding: '8px 26px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
          }}
        >
          <div
            style={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: frame >= 357 ? '#26c6da' : '#ef5350',
              boxShadow: `0 0 14px ${frame >= 357 ? '#26c6da' : '#ef5350'}`,
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
            STOCKFISH 19 • DEPTH {Math.min(38, Math.floor(12 + frame * 0.08))}
          </span>
        </div>

        <EvalBar frame={frame} />
      </div>

      {/* Center 3D Perspective Chessboard */}
      <div
        style={{
          position: 'absolute',
          top: '48%',
          left: '50%',
          transform: `translate(-50%, -50%) perspective(1000px) rotateX(${boardRotateX}deg) rotateZ(${boardRotateZ}deg) scale(${boardZoom})`,
          zIndex: 20,
        }}
      >
        <ChessEditBoard frame={frame} />
      </div>

      {/* Shockwave Blast Ring on Bass Drop */}
      {frame >= 357 && frame < 390 && (
        <div
          style={{
            position: 'absolute',
            top: '48%',
            left: '50%',
            transform: `translate(-50%, -50%) scale(${shockwave * 4})`,
            width: 320,
            height: 320,
            borderRadius: '50%',
            border: '8px solid rgba(38,198,218,0.9)',
            boxShadow: '0 0 60px rgba(38,198,218,0.95), inset 0 0 40px rgba(38,198,218,0.5)',
            opacity: 1 - shockwave,
            pointerEvents: 'none',
            zIndex: 45,
          }}
        />
      )}

      {/* Giant Brilliant (!!) Badge Slam at Frame 357 */}
      {frame >= 357 && frame < 450 && (
        <div
          style={{
            position: 'absolute',
            top: '48%',
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
              fontSize: 62,
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

      {/* Checkmate Victory Stamp at Frame 555+ */}
      {frame >= 555 && frame < 595 && (
        <div
          style={{
            position: 'absolute',
            top: '48%',
            left: '50%',
            transform: `translate(-50%, -50%) scale(${spring({ frame: frame - 555, fps, config: { damping: 9, mass: 0.5 } })})`,
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
              fontSize: 68,
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
      {frame < 575 && (
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
              background: 'rgba(6, 12, 19, 0.92)',
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
                fontSize: 56,
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
                fontSize: 28,
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

      {/* Outro Screen (frames 575 - 630 / 19.1s - 21.0s) */}
      {frame >= 575 && (
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
            transform: `scale(${spring({ frame: frame - 575, fps, config: { damping: 11, mass: 0.55 } })})`,
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
              padding: '14px 34px',
              boxShadow: '0 10px 30px rgba(0,0,0,0.7)',
            }}
          >
            <span style={{ fontFamily: 'Montserrat, sans-serif', fontSize: 24, fontWeight: 800, color: '#f8fafc' }}>
              💻 Windows .EXE &nbsp;•&nbsp; 📱 Android .APK &nbsp;•&nbsp; 🍏 iOS .IPA
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

