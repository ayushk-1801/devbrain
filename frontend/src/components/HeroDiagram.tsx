import { GoogleGeminiEffect } from "./ui/gemini-effect";
import { useScroll, useTransform } from "motion/react";
import React from "react";

export function HeroDiagram() {
  const ref = React.useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });

  const pathLengthFirst = useTransform(scrollYProgress, [0, 0.3], [0.2, 1.2]);
  const pathLengthSecond = useTransform(scrollYProgress, [0, 0.3], [0.15, 1.2]);
  const pathLengthThird = useTransform(scrollYProgress, [0, 0.3], [0.1, 1.2]);
  const pathLengthFourth = useTransform(scrollYProgress, [0, 0.3], [0.05, 1.2]);
  const pathLengthFifth = useTransform(scrollYProgress, [0, 0.3], [0, 1.2]);
  return (
    <div
      ref={ref}
      className="w-full relative overflow-hidden h-[40vh] md:h-[55vh] bg-transparent"
    >
      <GoogleGeminiEffect
        pathLengths={[
          pathLengthFirst,
          pathLengthSecond,
          pathLengthThird,
          pathLengthFourth,
          pathLengthFifth,
        ]}
      />
    </div>
  );
}
