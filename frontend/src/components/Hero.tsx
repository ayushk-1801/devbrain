import { motion, useScroll, useTransform } from 'motion/react';
import React from 'react';
import { GoogleGeminiEffect } from './ui/gemini-effect';

export function Hero() {
  const ref = React.useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });

  // Complete the animation quickly (within the first 70% of the scroll track)
  const pathLengthFirst = useTransform(scrollYProgress, [0, 0.70], [0.2, 1.2]);
  const pathLengthSecond = useTransform(scrollYProgress, [0, 0.70], [0.15, 1.2]);
  const pathLengthThird = useTransform(scrollYProgress, [0, 0.70], [0.1, 1.2]);
  const pathLengthFourth = useTransform(scrollYProgress, [0, 0.70], [0.05, 1.2]);
  const pathLengthFifth = useTransform(scrollYProgress, [0, 0.70], [0, 1.2]);

  return (
    <section ref={ref} className="min-h-[120vh] flex flex-col items-center pt-[140px] md:pt-[204px] pb-[80px] md:pb-[140px] px-6 relative overflow-hidden">
      <motion.div 
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex flex-col items-center text-center w-full z-10"
      >
        <h1 className="font-display text-[48px] md:text-[64px] lg:text-[70px] font-black text-text-primary leading-[1.05] max-w-[900px] tracking-tight">
          Your Codebase Has a<br />Memory. Ask It Anything.
        </h1>
        <p className="font-display text-[16px] md:text-[18px] text-text-muted max-w-[580px] mt-6 leading-[1.7]">
          DevBrain turns every commit, pull request, and architectural decision
          into a permanently queryable knowledge graph. Stop guessing why
          code exists - get sourced answers in seconds.
        </p>
         <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4 mt-10 w-full sm:w-auto px-4 sm:px-0">
          <button className="bg-btn-dark text-btn-dark-text text-[14px] md:text-[15px] font-medium px-6 py-[14px] rounded-full transition-[background-color,box-shadow] duration-200 cursor-pointer hover:bg-[#3a3836] text-center">
            Explore the graph
          </button>
          <button className="bg-transparent border-[1.5px] border-border text-text-primary text-[14px] md:text-[15px] font-medium px-6 py-[14px] rounded-full transition-[background-color,box-shadow] duration-200 cursor-pointer hover:bg-bg-secondary text-center">
            Read the docs
          </button>
        </div>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut", delay: 0.2 }}
        className="w-screen shrink-0 relative -mt-32 md:-mt-48 h-[300px] md:h-[450px] z-0"
      >
        <GoogleGeminiEffect
          className="relative top-0 w-full"
          pathLengths={[
            pathLengthFirst,
            pathLengthSecond,
            pathLengthThird,
            pathLengthFourth,
            pathLengthFifth,
          ]}
        />
      </motion.div>
    </section>
  );
}
