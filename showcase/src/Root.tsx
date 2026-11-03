import React from 'react';
import { Composition } from 'remotion';
import { ShowcaseVideo } from './Showcase';
import { ZackDShortVideo } from './ZackDShort';

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
      <Composition
        id="ZackDShort"
        component={ZackDShortVideo}
        durationInFrames={1280}
        fps={30}
        width={1080}
        height={1920}
      />
    </>
  );
};
