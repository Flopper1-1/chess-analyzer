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

// Color palette
const THEME = {
  bgDark: '#0f1418',
  bgCard: '#1a2228',
  accentGreen: '#4caf50',
  accentTeal: '#1baca6',
  accentGold: '#e6c619',
  accentRed: '#ca3431',
  textLight: '#f0f4f8',
  textMuted: '#9aa0a6',
};

// --- BACKGROUND COMPONENT ---
const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const shift = (frame * 0.4) % 120;

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 50% 30%, #1c2630 0%, #0d1216 100%)`,
        overflow: 'hidden',
      }}
    >
      {/* Subtle animated grid lines */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px),
                            linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)`,
          backgroundSize: '80px 80px',
          backgroundPosition: `${shift}px ${shift}px`,
        }}
      />
    </AbsoluteFill>
  );
};

// --- SCENE 1: INTRO ---
const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const logoScale = spring({ frame, fps, config: { damping: 12, mass: 0.8 } });
  const titleOpacity = interpolate(frame, [15, 35], [0, 1], { extrapolateRight: 'clamp' });
  const titleY = interpolate(frame, [15, 35], [30, 0], { extrapolateRight: 'clamp' });
  const subtitleOpacity = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: 'clamp' });

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
          boxShadow: '0 20px 60px rgba(76, 175, 80, 0.35)',
          borderRadius: '40px',
          overflow: 'hidden',
          marginBottom: '35px',
          border: '2px solid rgba(255,255,255,0.15)',
        }}
      >
        <Img
          src={staticFile('icon.png')}
          style={{ width: 170, height: 170, display: 'block' }}
        />
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
            fontSize: 78,
            fontWeight: 800,
            letterSpacing: '2px',
            color: THEME.textLight,
            margin: 0,
            textShadow: '0 4px 20px rgba(0,0,0,0.6)',
          }}
        >
          CHESS ANALYZER
        </h1>
      </div>

      <div
        style={{
          opacity: subtitleOpacity,
          marginTop: '15px',
        }}
      >
        <p
          style={{
            fontFamily: 'Segoe UI, system-ui, sans-serif',
            fontSize: 28,
            fontWeight: 400,
            color: THEME.accentGreen,
            letterSpacing: '1px',
            margin: 0,
            padding: '8px 24px',
            background: 'rgba(76, 175, 80, 0.12)',
            borderRadius: '20px',
            border: '1px solid rgba(76, 175, 80, 0.25)',
          }}
        >
          Powered by Stockfish 17.1 • Standalone Windows App
        </p>
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 2: ANNOTATIONS & MOVE ANALYSIS ---
const AnnotationsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sceneProgress = spring({ frame, fps, config: { damping: 14 } });
  const badges = [
    { name: 'Brilliant', key: 'brilliant.png', desc: 'Game-turning Sacrifice', color: '#1baca6' },
    { name: 'Great Find', key: 'great_find.png', desc: 'Crucial Tactical Move', color: '#5c8bb0' },
    { name: 'Best Move', key: 'best.png', desc: 'Top Stockfish 17 Engine Line', color: '#4caf50' },
    { name: 'Excellent', key: 'excellent.png', desc: 'Maintains Advantage', color: '#6fa84d' },
    { name: 'Book Move', key: 'book.png', desc: 'Lichess Opening Encyclopedia', color: '#a58d6d' },
    { name: 'Blunder', key: 'blunder.png', desc: 'Critical Game Loss', color: '#ca3431' },
  ];

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'row',
        padding: '80px 100px',
        alignItems: 'center',
        justifyContent: 'space-between',
        opacity: sceneProgress,
      }}
    >
      {/* Left side: Feature Title & Board Mock */}
      <div style={{ flex: 1, paddingRight: '60px' }}>
        <span
          style={{
            color: THEME.accentGreen,
            fontSize: 22,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '2px',
          }}
        >
          Intelligent Classification
        </span>
        <h2
          style={{
            fontFamily: 'Segoe UI, sans-serif',
            fontSize: 54,
            fontWeight: 800,
            color: THEME.textLight,
            margin: '12px 0 24px 0',
            lineHeight: 1.15,
          }}
        >
          Every Move Evaluated with Precision
        </h2>
        <p
          style={{
            fontFamily: 'Segoe UI, sans-serif',
            fontSize: 24,
            color: THEME.textMuted,
            lineHeight: 1.5,
            margin: 0,
          }}
        >
          Real-time win probability analysis instantly flags brilliant sacrifices, best moves, mistakes, and book theory with visual badge highlights.
        </p>

        {/* Live arrow preview pill */}
        <div
          style={{
            marginTop: '36px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '16px',
            background: 'rgba(27, 172, 166, 0.15)',
            border: '1px solid rgba(27, 172, 166, 0.4)',
            padding: '12px 24px',
            borderRadius: '16px',
          }}
        >
          <Img src={staticFile('icons/alternative.png')} style={{ width: 40, height: 40 }} />
          <span style={{ color: '#8ee6e1', fontSize: 20, fontWeight: 600 }}>
            Visual arrow pointers show best alternatives on errors!
          </span>
        </div>
      </div>

      {/* Right side: Badges Grid */}
      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '20px',
        }}
      >
        {badges.map((b, idx) => {
          const delay = idx * 6;
          const badgeScale = spring({
            frame: frame - delay,
            fps,
            config: { damping: 12, mass: 0.6 },
          });

          return (
            <div
              key={b.name}
              style={{
                transform: `scale(${Math.max(0, badgeScale)})`,
                background: THEME.bgCard,
                borderRadius: '20px',
                padding: '20px 24px',
                display: 'flex',
                alignItems: 'center',
                gap: '20px',
                boxShadow: '0 12px 30px rgba(0,0,0,0.4)',
                border: `1px solid ${b.color}44`,
              }}
            >
              <Img
                src={staticFile(`icons/${b.key}`)}
                style={{
                  width: 58,
                  height: 58,
                  filter: 'drop-shadow(0 4px 10px rgba(0,0,0,0.5))',
                }}
              />
              <div>
                <div style={{ color: b.color, fontSize: 22, fontWeight: 700 }}>{b.name}</div>
                <div style={{ color: THEME.textMuted, fontSize: 16, marginTop: '4px' }}>
                  {b.desc}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 3: EVALUATION & ACCURACY ---
const EvaluationScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const graphProgress = interpolate(frame, [0, 45], [0, 1], { extrapolateRight: 'clamp' });
  const evalValue = interpolate(frame, [0, 40, 80], [0.4, 3.2, 1.8]);

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'row',
        padding: '80px 100px',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      {/* Left side: Eval & Graph representation */}
      <div
        style={{
          flex: 1.1,
          background: THEME.bgCard,
          borderRadius: '28px',
          padding: '36px',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ color: THEME.accentGreen, fontSize: 18, fontWeight: 700, textTransform: 'uppercase' }}>
              Real-Time Engine Stream
            </span>
            <h3 style={{ fontSize: 32, fontWeight: 800, color: THEME.textLight, margin: '6px 0 0 0' }}>
              Dynamic Eval Curve & Bar
            </h3>
          </div>
          <div
            style={{
              background: '#23303a',
              padding: '10px 22px',
              borderRadius: '14px',
              color: THEME.accentGreen,
              fontSize: 26,
              fontWeight: 800,
            }}
          >
            +{evalValue.toFixed(1)}
          </div>
        </div>

        {/* Mock animated wave graph */}
        <div
          style={{
            marginTop: '30px',
            height: '180px',
            background: '#12171c',
            borderRadius: '16px',
            position: 'relative',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
            <path
              d="M 0 100 Q 150 40 300 120 T 600 70 T 900 60"
              fill="none"
              stroke={THEME.accentGreen}
              strokeWidth="5"
              strokeDasharray="1000"
              strokeDashoffset={`${(1 - graphProgress) * 1000}`}
              style={{ filter: 'drop-shadow(0 0 10px rgba(76,175,80,0.8))' }}
            />
          </svg>
          <div
            style={{
              position: 'absolute',
              bottom: '12px',
              left: '20px',
              color: THEME.textMuted,
              fontSize: 14,
            }}
          >
            Interactive Hover: Move 24 • Queen Sac → Checkmate in 3
          </div>
        </div>
      </div>

      {/* Right side: Accuracy & Rating Cards */}
      <div style={{ flex: 0.9, paddingLeft: '60px' }}>
        <span style={{ color: THEME.accentGold, fontSize: 20, fontWeight: 700, textTransform: 'uppercase' }}>
          Performance Metrics
        </span>
        <h2 style={{ fontSize: 48, fontWeight: 800, color: THEME.textLight, margin: '10px 0 24px 0' }}>
          Phase-by-Phase Accuracy
        </h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {[
            { phase: 'Opening (ECO A-E)', acc: '95.4%', color: '#6fa84d' },
            { phase: 'Middlegame Tactics', acc: '89.1%', color: '#4caf50' },
            { phase: 'Endgame Precision', acc: '92.8%', color: '#1baca6' },
            { phase: 'Overall Performance', acc: '92.4%', color: THEME.accentGold, rating: 'Est. 2350 Elo' },
          ].map((item, i) => (
            <div
              key={item.phase}
              style={{
                background: THEME.bgCard,
                borderRadius: '16px',
                padding: '16px 24px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderLeft: `6px solid ${item.color}`,
              }}
            >
              <div>
                <div style={{ color: THEME.textLight, fontSize: 20, fontWeight: 600 }}>{item.phase}</div>
                {item.rating && (
                  <div style={{ color: THEME.accentGold, fontSize: 15, fontWeight: 700, marginTop: '2px' }}>
                    {item.rating}
                  </div>
                )}
              </div>
              <div style={{ color: item.color, fontSize: 26, fontWeight: 800 }}>{item.acc}</div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 4: ADVANCED FEATURES (Background & MS Paint Customization) ---
const FeaturesScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const features = [
    {
      icon: '🎨',
      title: 'One-Click Paint Editing',
      desc: 'Customize any annotation badge in MS Paint with instant hot-reloading.',
    },
    {
      icon: '⚡',
      title: 'Zero-Throttle Backgrounding',
      desc: 'Analyzes games at full CPU speed even when tabbed out or minimized.',
    },
    {
      icon: '🧠',
      title: 'Dynamic Resource Tuning',
      desc: 'Automatic thread & hash memory scaling tuned to your CPU depth slider.',
    },
    {
      icon: '🔄',
      title: 'Smart Perspective Auto-Flip',
      desc: 'Automatically aligns the board to your player username from PGN headers.',
    },
  ];

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '60px 120px',
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: '45px' }}>
        <span style={{ color: THEME.accentTeal, fontSize: 20, fontWeight: 700, textTransform: 'uppercase' }}>
          Designed for Chess Players & Creators
        </span>
        <h2 style={{ fontSize: 52, fontWeight: 800, color: THEME.textLight, margin: '8px 0 0 0' }}>
          Cutting-Edge Features Under the Hood
        </h2>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '28px',
          width: '100%',
        }}
      >
        {features.map((f, idx) => {
          const cardSpring = spring({
            frame: frame - idx * 7,
            fps,
            config: { damping: 14 },
          });

          return (
            <div
              key={f.title}
              style={{
                transform: `scale(${Math.max(0, cardSpring)})`,
                background: THEME.bgCard,
                borderRadius: '24px',
                padding: '28px 32px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '24px',
                border: '1px solid rgba(255,255,255,0.08)',
                boxShadow: '0 16px 40px rgba(0,0,0,0.3)',
              }}
            >
              <div
                style={{
                  fontSize: 44,
                  background: 'rgba(255,255,255,0.05)',
                  padding: '12px 16px',
                  borderRadius: '16px',
                }}
              >
                {f.icon}
              </div>
              <div>
                <h3 style={{ color: THEME.textLight, fontSize: 26, fontWeight: 700, margin: '0 0 8px 0' }}>
                  {f.title}
                </h3>
                <p style={{ color: THEME.textMuted, fontSize: 18, lineHeight: 1.5, margin: 0 }}>
                  {f.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// --- SCENE 5: OUTRO ---
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
            width: 140,
            height: 140,
            marginBottom: '28px',
            boxShadow: '0 15px 45px rgba(76,175,80,0.4)',
            borderRadius: '32px',
            border: '2px solid rgba(255,255,255,0.15)',
          }}
        />

        <h1
          style={{
            fontFamily: 'Segoe UI, sans-serif',
            fontSize: 64,
            fontWeight: 800,
            color: THEME.textLight,
            margin: 0,
            letterSpacing: '1px',
          }}
        >
          Chess Game Analyzer
        </h1>

        <div
          style={{
            display: 'flex',
            gap: '16px',
            marginTop: '24px',
            justifyContent: 'center',
          }}
        >
          <span
            style={{
              background: 'rgba(255,255,255,0.08)',
              padding: '10px 24px',
              borderRadius: '24px',
              fontSize: 22,
              fontWeight: 600,
              color: THEME.textLight,
              border: '1px solid rgba(255,255,255,0.12)',
            }}
          >
            Standalone Windows Executable
          </span>
          <span
            style={{
              background: 'rgba(76, 175, 80, 0.15)',
              padding: '10px 24px',
              borderRadius: '24px',
              fontSize: 22,
              fontWeight: 600,
              color: THEME.accentGreen,
              border: '1px solid rgba(76, 175, 80, 0.3)',
            }}
          >
            Stockfish 17.1 Built-in
          </span>
        </div>

        <p
          style={{
            fontSize: 22,
            color: THEME.textMuted,
            marginTop: '20px',
            marginBottom: 0,
            letterSpacing: '0.5px',
          }}
        >
          No external dependencies required
        </p>
      </div>
    </AbsoluteFill>
  );
};

// --- ROOT COMPOSITION ---
export const ShowcaseVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      <Background />

      {/* 0s - 3s: Intro */}
      <Sequence from={0} durationInFrames={90}>
        <IntroScene />
      </Sequence>

      {/* 3s - 7s: Annotations */}
      <Sequence from={90} durationInFrames={120}>
        <AnnotationsScene />
      </Sequence>

      {/* 7s - 11s: Evaluation & Accuracy */}
      <Sequence from={210} durationInFrames={120}>
        <EvaluationScene />
      </Sequence>

      {/* 11s - 14s: Advanced Features */}
      <Sequence from={330} durationInFrames={90}>
        <FeaturesScene />
      </Sequence>

      {/* 14s - 16s: Outro */}
      <Sequence from={420} durationInFrames={60}>
        <OutroScene />
      </Sequence>
    </AbsoluteFill>
  );
};

