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

// --- PART 1 (0.00s - 5.42s / frames 0 - 162): SLIDER BANNER ONLY ---
const SliderBannerScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // 55 slots, starting at slot 8 (so the left side is completely filled from frame 0!)
  // and landing on slot 42 ('brilliant.png') at frame 136
  const START_INDEX = 8;
  const WIN_INDEX = 42;
  const CARD_W = 148;
  const CARD_GAP = 16;
  const STEP = CARD_W + CARD_GAP;

  const strip = Array.from({ length: 55 }).map((_, idx) => {
    if (idx === WIN_INDEX) {
      return { icon: 'brilliant.png', color: '#26c6da', jackpot: true };
    }
    const item = REEL_ITEMS[(idx * 7 + 3) % (REEL_ITEMS.length - 1)];
    return { ...item, jackpot: false };
  });

  const spinProgress = interpolate(frame, [0, 136], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic),
  });

  const startX = START_INDEX * STEP;
  const endX = WIN_INDEX * STEP;
  const currentOffset = interpolate(spinProgress, [0, 1], [startX, endX]);

  const landed = frame >= 136;
  const winPulse = landed
    ? spring({ frame: frame - 136, fps, config: { damping: 8, mass: 0.5 } })
    : 0;

  return (
    <AbsoluteFill
      style={{
        background: '#06090d',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 8,
      }}
    >
      <div
        style={{
          width: width - 16,
          height: height - 16,
          background: 'linear-gradient(180deg, #16222f 0%, #0b1118 100%)',
          borderRadius: 28,
          border: landed ? '4px solid #26c6da' : '3px solid #ffd54f',
          boxShadow: landed
            ? '0 0 40px rgba(38,198,218,0.85), inset 0 0 30px rgba(38,198,218,0.25)'
            : '0 8px 30px rgba(0,0,0,0.8)',
          position: 'relative',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        {/* Subtle diagonal Musor Drop hazard pattern */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'repeating-linear-gradient(45deg, rgba(255,213,79,0.035) 0px, rgba(255,213,79,0.035) 20px, transparent 20px, transparent 40px)',
            pointerEvents: 'none',
          }}
        />

        {/* Scrolling Cards */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: CARD_GAP,
            position: 'absolute',
            left: (width - 16) / 2 - CARD_W / 2 - currentOffset,
          }}
        >
          {strip.map((card, idx) => {
            const isWinner = idx === WIN_INDEX && landed;
            const scale = isWinner ? 1 + winPulse * 0.18 : 1;

            return (
              <div
                key={idx}
                style={{
                  width: CARD_W,
                  height: 168,
                  borderRadius: 20,
                  background: isWinner
                    ? 'radial-gradient(circle at 50% 40%, rgba(38,198,218,0.45), #122530 80%)'
                    : '#131c25',
                  border: isWinner ? '3px solid #26c6da' : `2px solid ${card.color}66`,
                  borderBottom: `8px solid ${card.color}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transform: `scale(${scale})`,
                  boxShadow: isWinner ? '0 0 35px rgba(38,198,218,0.95)' : '0 8px 20px rgba(0,0,0,0.45)',
                }}
              >
                <Img
                  src={staticFile(`icons/${card.icon}`)}
                  style={{
                    width: isWinner ? 102 : 86,
                    height: isWinner ? 102 : 86,
                    filter: `drop-shadow(0 6px 14px ${card.color}88)`,
                  }}
                />
              </div>
            );
          })}
        </div>

        {/* Left & Right edge vignette */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'linear-gradient(90deg, #090e14 0%, transparent 14%, transparent 86%, #090e14 100%)',
            pointerEvents: 'none',
          }}
        />

        {/* Center Selector Line & Triangles */}
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: 0,
            bottom: 0,
            width: 4,
            transform: 'translateX(-50%)',
            background: landed ? '#26c6da' : '#ffd54f',
            boxShadow: landed ? '0 0 22px #26c6da' : '0 0 16px #ffd54f',
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
    </AbsoluteFill>
  );
};

// --- PART 2 (5.42s - 9.46s / frames 162 - 284): BANNER-SIZED TITLE DROP ---
const BannerTitleDropScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const flashOpacity = interpolate(frame, [0, 12], [0.95, 0], { extrapolateRight: 'clamp' });
  const slamScale = spring({
    frame,
    fps,
    config: { damping: 11, mass: 0.6, stiffness: 170 },
  });

  const leftBadges = [
    { icon: 'brilliant.png', col: '#26c6da' },
    { icon: 'great_find.png', col: '#42a5f5' },
    { icon: 'best.png', col: '#4caf50' },
  ];
  const rightBadges = [
    { icon: 'mistake.png', col: '#ff9800' },
    { icon: 'incorrect.png', col: '#ef5350' },
    { icon: 'blunder.png', col: '#e53935' },
  ];

  // Visual down-arrow pops in at local frame 48 (7.02s, when voice says "Ссылка в описании профиля")
  const arrowPop = frame >= 48
    ? spring({ frame: frame - 48, fps, config: { damping: 10, mass: 0.55 } })
    : 0;
  const arrowBounce = Math.sin(frame * 0.38) * 7;

  return (
    <AbsoluteFill
      style={{
        background: '#06090d',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 8,
      }}
    >
      <div
        style={{
          width: width - 16,
          height: height - 16,
          background: 'radial-gradient(circle at 50% 50%, #172e3f 0%, #0b131c 75%, #070b10 100%)',
          borderRadius: 28,
          border: '4px solid #26c6da',
          boxShadow: '0 0 45px rgba(38,198,218,0.65), inset 0 0 35px rgba(38,198,218,0.2)',
          position: 'relative',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 44px',
        }}
      >
        {/* Left Flanking Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, zIndex: 2 }}>
          {leftBadges.map((b, i) => {
            const pop = spring({ frame: frame - i * 3, fps, config: { damping: 11, mass: 0.5 } });
            const floatY = Math.sin((frame + i * 15) * 0.15) * 5;
            return (
              <div
                key={b.icon}
                style={{
                  transform: `scale(${Math.max(0, pop)}) translateY(${floatY}px)`,
                  background: '#121c27',
                  padding: 12,
                  borderRadius: 18,
                  border: `2px solid ${b.col}88`,
                  boxShadow: `0 8px 22px rgba(0,0,0,0.55), 0 0 16px ${b.col}44`,
                }}
              >
                <Img src={staticFile(`icons/${b.icon}`)} style={{ width: 54, height: 54, display: 'block' }} />
              </div>
            );
          })}
        </div>

        {/* Center Logo + THE ONLY WORDS: "CHESS ANALYZER" + Visual Down-Arrow */}
        <div
          style={{
            transform: `scale(${slamScale})`,
            display: 'flex',
            alignItems: 'center',
            gap: 28,
            zIndex: 5,
          }}
        >
          <div
            style={{
              borderRadius: 28,
              overflow: 'hidden',
              boxShadow: '0 12px 40px rgba(76, 175, 80, 0.6), 0 0 28px rgba(38, 198, 218, 0.5)',
              border: '3px solid rgba(255,255,255,0.3)',
            }}
          >
            <Img src={staticFile('icon.png')} style={{ width: 132, height: 132, display: 'block' }} />
          </div>

          <h1
            style={{
              fontFamily: 'Segoe UI, system-ui, sans-serif',
              fontSize: 74,
              fontWeight: 900,
              letterSpacing: '3px',
              color: '#f8fafc',
              margin: 0,
              whiteSpace: 'nowrap',
              textShadow: '0 6px 28px rgba(0,0,0,0.9), 0 0 24px rgba(38,198,218,0.55)',
            }}
          >
            CHESS ANALYZER
          </h1>

          {/* Wordless Bouncing Down-Arrow Cue synced to "Ссылка в описании профиля" */}
          {arrowPop > 0.01 && (
            <div
              style={{
                transform: `scale(${arrowPop}) translateY(${arrowBounce}px)`,
                width: 66,
                height: 66,
                borderRadius: '50%',
                background: 'linear-gradient(180deg, #26c6da 0%, #4caf50 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 28px rgba(38,198,218,0.9)',
                border: '3px solid #ffffff',
              }}
            >
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 4V20M12 20L5 13M12 20L19 13"
                  stroke="#071018"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          )}
        </div>

        {/* Right Flanking Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, zIndex: 2 }}>
          {rightBadges.map((b, i) => {
            const pop = spring({ frame: frame - i * 3, fps, config: { damping: 11, mass: 0.5 } });
            const floatY = Math.cos((frame + i * 15) * 0.15) * 5;
            return (
              <div
                key={b.icon}
                style={{
                  transform: `scale(${Math.max(0, pop)}) translateY(${floatY}px)`,
                  background: '#121c27',
                  padding: 12,
                  borderRadius: 18,
                  border: `2px solid ${b.col}88`,
                  boxShadow: `0 8px 22px rgba(0,0,0,0.55), 0 0 16px ${b.col}44`,
                }}
              >
                <Img src={staticFile(`icons/${b.icon}`)} style={{ width: 54, height: 54, display: 'block' }} />
              </div>
            );
          })}
        </div>

        {/* Hard-Cut Impact Flash Overlay */}
        <AbsoluteFill
          style={{
            background: 'radial-gradient(circle, #ffffff 0%, #26c6da 65%, transparent 100%)',
            opacity: flashOpacity,
            pointerEvents: 'none',
            zIndex: 10,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

export const BannerShowcaseVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      <Audio src={staticFile('musor_audio.mp3')} />
      <Sequence from={0} durationInFrames={162}>
        <SliderBannerScene />
      </Sequence>
      <Sequence from={162} durationInFrames={122}>
        <BannerTitleDropScene />
      </Sequence>
    </AbsoluteFill>
  );
};

