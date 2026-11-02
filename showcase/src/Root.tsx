import React from 'react';
import { Composition } from 'remotion';
import { ShowcaseVideo } from './Showcase';

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="ChessAnalyzerShowcase"
        component={ShowcaseVideo}
        durationInFrames={480}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};

