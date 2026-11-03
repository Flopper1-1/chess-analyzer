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

import captionChunks from './caption_chunks.json';

// --- ZACK D. STYLE SYNCHRONIZED WORD-LEVEL BOUNCING CAPTIONS ---
const ZackDCaptions: React.FC = () => {
  const frame = useCurrentFrame();
  const currentTime = frame / 30;

  const activeChunk = captionChunks.find(
    (c) => currentTime >= c.start && currentTime <= c.end
  );
  if (!activeChunk) return null;

  const chunkLocalFrame = (currentTime - activeChunk.start) * 30;
  const bounce = spring({
    frame: chunkLocalFrame,
    fps: 30,
    config: { damping: 12, mass: 0.4, stiffness: 240 },
  });

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 220,
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '0 40px',
        zIndex: 100,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          transform: `scale(${Math.max(0.75, bounce)})`,
          background: 'rgba(5, 10, 16, 0.92)',
          border: '3px solid rgba(255, 255, 255, 0.25)',
          boxShadow: '0 16px 45px rgba(0,0,0,0.85), 0 0 30px rgba(38,198,218,0.3)',
          borderRadius: 24,
          padding: '16px 36px',
          textAlign: 'center',
          maxWidth: 980,
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          alignItems: 'center',
          gap: '14px',
        }}
      >
        {activeChunk.words.map((w, idx) => {
          const isCurrent = currentTime >= w.start && currentTime <= w.end;
          const isPast = currentTime > w.end;
          const cleanText = w.text.toUpperCase();

          // Highlight color based on keywords
          let hlColor = '#ffd54f'; // Default energetic yellow
          if (
            cleanText.includes('BLUNDER') ||
            cleanText.includes('RESIGN') ||
            cleanText.includes('OVER') ||
            cleanText.includes('HEART')
          ) {
            hlColor = '#ef5350';
          } else if (
            cleanText.includes('BRILLIANT') ||
            cleanText.includes('ANALYZER') ||
            cleanText.includes('STOCKFISH') ||
            cleanText.includes('ANALYZE')
          ) {
            hlColor = '#26c6da';
          } else if (
            cleanText.includes('GRANDMASTER') ||
            cleanText.includes('COUNTER-TACTIC') ||
            cleanText.includes('ACCURACY')
          ) {
            hlColor = '#4caf50';
          }

          return (
            <span
              key={idx}
              style={{
                fontFamily: 'Montserrat, Impact, Segoe UI, sans-serif',
                fontSize: isCurrent ? 56 : 50,
                fontWeight: 900,
                letterSpacing: '1px',
                color: isCurrent ? hlColor : isPast ? '#ffffff' : 'rgba(255,255,255,0.45)',
                textShadow: isCurrent
                  ? `0 0 24px ${hlColor}, 0 4px 10px rgba(0,0,0,0.9)`
                  : '0 4px 12px rgba(0,0,0,0.9)',
                transform: isCurrent ? 'scale(1.12)' : 'scale(1.0)',
                transition: 'transform 0.05s ease-out',
                display: 'inline-block',
                margin: '0 8px',
              }}
            >
              {cleanText}
            </span>
          );
        })}
      </div>
    </div>
  );
};

// --- SCENE 1: THE BLUNDER HOOK (0.00s - 5.20s / frames 0 - 156) ---
const SceneBlunderHook: React.FC = () => {
  const frame = useCurrentFrame();

  const camZoom = interpolate(frame, [0, 150], [1, 1.45], { easing: Easing.out(Easing.quad) });
  const queenTilt = interpolate(frame, [40, 95], [0, 78], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.bounce });
  const queenFallY = interpolate(frame, [40, 95], [0, 60], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const redPulse = frame > 45 ? Math.sin((frame - 45) * 0.3) * 0.4 + 0.6 : 0;

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at 50% 35%, #182230 0%, #080d14 70%, #030508 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden',
      }}
    >
      {/* Red Stress Vignette */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'radial-gradient(circle, transparent 40%, rgba(229,57,53,0.35) 100%)',
          opacity: redPulse,
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          transform: `scale(${camZoom})`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Floating Blunder Badge */}
        {frame > 50 && (
          <div
            style={{
              position: 'absolute',
              top: -120,
              transform: `scale(${interpolate(frame, [50, 65], [0, 1], { extrapolateRight: 'clamp' })})`,
              filter: 'drop-shadow(0 0 35px #e53935)',
              zIndex: 10,
            }}
          >
            <Img src={staticFile('icons/blunder.png')} style={{ width: 140, height: 140 }} />
          </div>
        )}

        {/* 3D Tilted Chessboard with Toppling Queen */}
        <div
          style={{
            width: 720,
            height: 720,
            borderRadius: 32,
            border: '4px solid rgba(255,255,255,0.2)',
            boxShadow: '0 30px 80px rgba(0,0,0,0.85)',
            transform: 'perspective(1000px) rotateX(42deg) rotateZ(-12deg)',
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gridTemplateRows: 'repeat(4, 1fr)',
            overflow: 'hidden',
          }}
        >
          {Array.from({ length: 16 }).map((_, i) => {
            const r = Math.floor(i / 4);
            const c = i % 4;
            const isLight = (r + c) % 2 === 0;
            const isCenter = r === 2 && c === 2;
            return (
              <div
                key={i}
                style={{
                  background: isCenter && frame > 45
                    ? '#c62828'
                    : isLight ? '#edd7b4' : '#b28562',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 88,
                  position: 'relative',
                }}
              >
                {isCenter && (
                  <div
                    style={{
                      transform: `rotate(${queenTilt}deg) translateY(${queenFallY}px)`,
                      transformOrigin: 'bottom right',
                      color: '#111827',
                      textShadow: '0 4px 14px rgba(0,0,0,0.6)',
                    }}
                  >
                    ♛
                  </div>
                )}
                {r === 1 && c === 1 && <span style={{ color: '#fff', textShadow: '0 2px 4px #000' }}>♙</span>}
                {r === 3 && c === 1 && <span style={{ color: '#fff', textShadow: '0 2px 4px #000' }}>♖</span>}
                {r === 0 && c === 3 && <span style={{ color: '#111' }}>♜</span>}
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 2: ANATOMICAL PANIC REACTION (5.20s - 13.60s / frames 156 - 408) ---
const SceneAnatomicalPanic: React.FC = () => {
  const frame = useCurrentFrame();
  const localFrame = frame;

  const heartRate = Math.round(interpolate(localFrame, [0, 240], [78, 168]));
  const brainPulse = Math.sin(localFrame * 0.4) * 0.35 + 0.65;
  const ekgOffset = (localFrame * 12) % 360;

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at 50% 40%, #1a121d 0%, #0d0912 70%, #050307 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Zack D. Style 3D Hologram Silhouette & Brain Cross-Section */}
      <div
        style={{
          width: 780,
          height: 1050,
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Hologram Head Outline */}
        <svg width="600" height="700" viewBox="0 0 600 700" style={{ overflow: 'visible' }}>
          <defs>
            <radialGradient id="brainGlow" cx="50%" cy="40%" r="50%">
              <stop offset="0%" stopColor="#ff3d00" stopOpacity={brainPulse * 0.95} />
              <stop offset="60%" stopColor="#d50000" stopOpacity={brainPulse * 0.6} />
              <stop offset="100%" stopColor="transparent" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Head & Neck Profile Outline */}
          <path
            d="M 180 620 C 180 540 220 500 230 450 C 210 430 170 380 170 300 C 170 170 260 100 370 100 C 480 100 550 180 550 310 C 550 420 480 480 440 510 C 440 560 460 620 460 620"
            fill="rgba(255, 61, 0, 0.08)"
            stroke="#ff5722"
            strokeWidth="5"
            strokeDasharray="12 6"
            style={{ filter: 'drop-shadow(0 0 25px rgba(255,87,34,0.5))' }}
          />

          {/* Glowing Amygdala / Stress Neural Hub */}
          <circle cx="360" cy="300" r="140" fill="url(#brainGlow)" />

          {/* Neural firing pulses */}
          {Array.from({ length: 8 }).map((_, i) => {
            const angle = (i / 8) * Math.PI * 2 + localFrame * 0.05;
            const r = 90 + Math.sin(localFrame * 0.3 + i) * 35;
            const x = 360 + Math.cos(angle) * r;
            const y = 300 + Math.sin(angle) * r;
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r="8"
                fill="#ffd54f"
                style={{ filter: 'drop-shadow(0 0 10px #ffd54f)' }}
              />
            );
          })}
        </svg>

        {/* EKG Heart Rate Monitor Box */}
        <div
          style={{
            position: 'absolute',
            bottom: 40,
            width: 720,
            background: 'rgba(18, 10, 15, 0.92)',
            border: '3px solid #ff1744',
            borderRadius: 24,
            padding: '20px 32px',
            boxShadow: '0 0 40px rgba(255, 23, 68, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ fontSize: 24, fontWeight: 800, color: '#ff8a80', fontFamily: 'Montserrat, sans-serif' }}>
              PULSE RATE (BPM)
            </div>
            <div style={{ fontSize: 68, fontWeight: 900, color: '#ff1744', fontFamily: 'Impact, sans-serif' }}>
              {heartRate} <span style={{ fontSize: 32 }}>BPM</span>
            </div>
          </div>

          {/* Animated EKG Wave */}
          <div style={{ width: 340, height: 70, overflow: 'hidden', position: 'relative' }}>
            <svg width="700" height="70" viewBox="0 0 700 70" style={{ transform: `translateX(-${ekgOffset}px)` }}>
              <path
                d="M 0 35 L 60 35 L 80 10 L 100 60 L 120 20 L 140 45 L 160 35 L 240 35 L 260 10 L 280 60 L 300 20 L 320 45 L 340 35 L 420 35 L 440 10 L 460 60 L 480 20 L 500 45 L 520 35 L 600 35 L 620 10 L 640 60 L 660 20 L 680 45 L 700 35"
                fill="none"
                stroke="#ff1744"
                strokeWidth="4"
              />
            </svg>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 3: THE GRANDMASTER COUNTER-TACTIC (13.60s - 19.69s / frames 408 - 591) ---
const SceneGrandmasterTactic: React.FC = () => {
  const frame = useCurrentFrame();
  const localFrame = frame;

  const vectorGlow = Math.sin(localFrame * 0.25) * 0.3 + 0.7;

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at 50% 45%, #0e2738 0%, #07131c 70%, #03080d 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          width: 820,
          height: 820,
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Floating Queen Piece Radiating Tactical Rays */}
        <div
          style={{
            fontSize: 160,
            color: '#26c6da',
            textShadow: '0 0 50px rgba(38,198,218,0.9), 0 0 100px rgba(38,198,218,0.5)',
            zIndex: 5,
          }}
        >
          ♛
        </div>

        {/* Tactical Trajectory Circles & Vectors */}
        <svg width="800" height="800" viewBox="0 0 800 800" style={{ position: 'absolute', inset: 0 }}>
          <defs>
            <marker id="tacticArrow" markerWidth="6" markerHeight="6" refX="4" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#ffd54f" />
            </marker>
          </defs>

          <circle cx="400" cy="400" r="160" fill="none" stroke="#26c6da" strokeWidth="3" strokeDasharray="10 6" opacity={vectorGlow} />
          <circle cx="400" cy="400" r="280" fill="none" stroke="#26c6da" strokeWidth="2" strokeDasharray="16 8" opacity={vectorGlow * 0.7} />

          {/* Dynamic Laser Attack Lines to Key Checkmate Squares */}
          <line x1="400" y1="400" x2="680" y2="180" stroke="#ffd54f" strokeWidth="6" strokeDasharray="12 6" markerEnd="url(#tacticArrow)" />
          <line x1="400" y1="400" x2="160" y2="240" stroke="#ffd54f" strokeWidth="6" strokeDasharray="12 6" markerEnd="url(#tacticArrow)" />
          <line x1="400" y1="400" x2="520" y2="680" stroke="#ffd54f" strokeWidth="6" strokeDasharray="12 6" markerEnd="url(#tacticArrow)" />

          {/* Target Kings */}
          <circle cx="680" cy="180" r="38" fill="rgba(255,213,79,0.2)" stroke="#ffd54f" strokeWidth="4" />
          <text x="680" y="195" textAnchor="middle" fill="#ffd54f" fontSize="42" fontFamily="Segoe UI Symbol">♚</text>
        </svg>
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 4: STOCKFISH 19 & BRILLIANT (!!) (19.69s - 29.89s / frames 591 - 897) ---
const SceneBrilliantPayoff: React.FC = () => {
  const frame = useCurrentFrame();
  const localFrame = frame;

  const evalRise = interpolate(localFrame, [0, 180], [8, 98], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic)
  });
  const brilSlam = spring({
    frame: localFrame - 210,
    fps: 30,
    config: { damping: 9, mass: 0.65, stiffness: 200 },
  });

  const shockwave = localFrame > 210
    ? interpolate(localFrame - 210, [0, 45], [0.6, 2.8], { extrapolateRight: 'clamp' })
    : 0;
  const shockwaveAlpha = localFrame > 210
    ? interpolate(localFrame - 210, [0, 45], [0.9, 0], { extrapolateRight: 'clamp' })
    : 0;

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at 50% 40%, #0d273a 0%, #07131e 70%, #03080d 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Shockwave Ring */}
      {localFrame > 210 && (
        <div
          style={{
            position: 'absolute',
            width: 450,
            height: 450,
            borderRadius: '50%',
            border: '8px solid #26c6da',
            transform: `scale(${shockwave})`,
            opacity: shockwaveAlpha,
            boxShadow: '0 0 60px #26c6da',
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Win% Spiking Eval Bar */}
      <div
        style={{
          width: 720,
          background: 'rgba(15, 23, 34, 0.95)',
          borderRadius: 28,
          border: '3px solid rgba(255,255,255,0.2)',
          padding: '24px 32px',
          boxShadow: '0 20px 60px rgba(0,0,0,0.8)',
          marginBottom: 40,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 26, fontWeight: 900, color: '#4caf50', fontFamily: 'Montserrat, sans-serif' }}>
            ENGINE WIN CHANCE
          </span>
          <span style={{ fontSize: 52, fontWeight: 900, color: '#26c6da', fontFamily: 'Impact, sans-serif' }}>
            {evalRise.toFixed(1)}%
          </span>
        </div>
        <div style={{ width: '100%', height: 34, background: '#1e293b', borderRadius: 17, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${evalRise}%`,
              background: 'linear-gradient(90deg, #ef5350 0%, #ffd54f 40%, #4caf50 75%, #26c6da 100%)',
              boxShadow: '0 0 24px #26c6da',
            }}
          />
        </div>
      </div>

      {/* Giant Brilliant (!!) Badge Slam */}
      {localFrame > 210 && (
        <div
          style={{
            transform: `scale(${brilSlam})`,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Img
            src={staticFile('icons/brilliant.png')}
            style={{
              width: 300,
              height: 300,
              filter: 'drop-shadow(0 0 50px rgba(38,198,218,0.95))',
            }}
          />
        </div>
      )}
    </AbsoluteFill>
  );
};

// --- SCENE 5: CHESS ANALYZER APP SHOWCASE (29.89s - 40.10s / frames 897 - 1203) ---
const SceneAppShowcase: React.FC = () => {
  const frame = useCurrentFrame();
  const localFrame = frame;

  const cardScale = spring({ frame: localFrame, fps: 30, config: { damping: 12, mass: 0.6 } });

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at 50% 35%, #132b3d 0%, #08121a 75%, #03070b 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 60px',
      }}
    >
      <div
        style={{
          transform: `scale(${cardScale})`,
          width: 860,
          background: 'rgba(17, 24, 34, 0.95)',
          borderRadius: 36,
          border: '3px solid #26c6da',
          padding: '36px 40px',
          boxShadow: '0 25px 70px rgba(0,0,0,0.85), 0 0 45px rgba(38,198,218,0.4)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 28 }}>
          <Img src={staticFile('icon.png')} style={{ width: 100, height: 100, borderRadius: 24 }} />
          <div>
            <div style={{ fontSize: 44, fontWeight: 900, color: '#f8fafc', fontFamily: 'Montserrat, sans-serif' }}>
              CHESS ANALYZER
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#4caf50', marginTop: 4 }}>
              STOCKFISH 19 • IN-APP LIBRARY
            </div>
          </div>
        </div>

        {/* Feature Highlights Grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {[
            { icon: 'brilliant.png', title: 'Brilliant Sacrifice Detector', desc: 'Identifies game-winning sound piece drops' },
            { icon: 'best.png', title: 'Stockfish 19 Engine Analysis', desc: 'Calculates win% curves in milliseconds' },
            { icon: 'book.png', title: 'Full Opening Classification', desc: 'Instant ECO A–E theory database lookup' },
          ].map((item, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 20,
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.1)',
                padding: '16px 20px',
                borderRadius: 20,
              }}
            >
              <Img src={staticFile(`icons/${item.icon}`)} style={{ width: 56, height: 56 }} />
              <div>
                <div style={{ fontSize: 24, fontWeight: 800, color: '#f8fafc' }}>{item.title}</div>
                <div style={{ fontSize: 18, color: '#94a3b8', marginTop: 2 }}>{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 6: FINAL PUNCHLINE & CALL TO ACTION (40.10s - 44.72s / frames 1203 - 1342) ---
const SceneFinalPunchline: React.FC = () => {
  const frame = useCurrentFrame();
  const localFrame = frame;

  const slam = spring({ frame: localFrame, fps: 30, config: { damping: 10, mass: 0.65, stiffness: 220 } });
  const arrowBounce = Math.sin(localFrame * 0.35) * 12;

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(circle at 50% 45%, #183348 0%, #091520 70%, #03080d 100%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          transform: `scale(${slam})`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        <Img
          src={staticFile('icon.png')}
          style={{
            width: 220,
            height: 220,
            borderRadius: 52,
            border: '4px solid rgba(255,255,255,0.3)',
            boxShadow: '0 25px 80px rgba(76,175,80,0.5), 0 0 50px rgba(38,198,218,0.6)',
            marginBottom: 36,
          }}
        />

        <h1
          style={{
            fontFamily: 'Montserrat, sans-serif',
            fontSize: 74,
            fontWeight: 900,
            color: '#f8fafc',
            margin: '0 0 16px 0',
            letterSpacing: '2px',
          }}
        >
          CHESS ANALYZER
        </h1>

        <div
          style={{
            fontFamily: 'Montserrat, sans-serif',
            fontSize: 44,
            fontWeight: 900,
            color: '#ffd54f',
            marginBottom: 44,
          }}
        >
          DON'T RESIGN. ANALYZE IT.
        </div>

        {/* Bouncing Down Arrow */}
        <div
          style={{
            transform: `translateY(${arrowBounce}px)`,
            width: 90,
            height: 90,
            borderRadius: '50%',
            background: 'linear-gradient(180deg, #26c6da 0%, #4caf50 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 40px rgba(38,198,218,0.9)',
            border: '4px solid #ffffff',
          }}
        >
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 4V20M12 20L5 13M12 20L19 13"
              stroke="#071018"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// --- ROOT ZACK D. SHORT COMPOSITION ---
export const ZackDShortVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: '#05080c' }}>
      <Audio src={staticFile('zack_voice.mp3')} />

      {/* Scene 1: The Blunder Hook (0 - 4.64s / frames 0 - 139) */}
      <Sequence from={0} durationInFrames={139}>
        <SceneBlunderHook />
      </Sequence>

      {/* Scene 2: Anatomical Panic (4.64 - 12.28s / frames 139 - 369) */}
      <Sequence from={139} durationInFrames={230}>
        <SceneAnatomicalPanic />
      </Sequence>

      {/* Scene 3: Grandmaster Counter-Tactic (12.28 - 18.71s / frames 369 - 561) */}
      <Sequence from={369} durationInFrames={192}>
        <SceneGrandmasterTactic />
      </Sequence>

      {/* Scene 4: Brilliant Move Payoff (18.71 - 27.25s / frames 561 - 817) */}
      <Sequence from={561} durationInFrames={256}>
        <SceneBrilliantPayoff />
      </Sequence>

      {/* Scene 5: App Showcase (27.25 - 38.85s / frames 817 - 1165) */}
      <Sequence from={817} durationInFrames={348}>
        <SceneAppShowcase />
      </Sequence>

      {/* Scene 6: Outro (38.85 - 44.00s / frames 1165 - 1320) */}
      <Sequence from={1165} durationInFrames={155}>
        <SceneFinalPunchline />
      </Sequence>

      {/* Viral Zack D. Bouncing Captions Layer */}
      <ZackDCaptions />
    </AbsoluteFill>
  );
};

