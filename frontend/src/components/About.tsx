import { motion } from 'motion/react';
import { RadialDiagram } from './RadialDiagram';
import { GitCommit, GitPullRequest, FileText, Code2 } from 'lucide-react';

export function About() {
  return (
    <section id="about" className="section-padding content-container flex flex-col items-center">
      <motion.div 
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="flex flex-col items-center text-center w-full"
      >
        <h2 className="font-display text-[36px] md:text-[56px] lg:text-[60px] font-extrabold text-text-primary leading-[1.1] max-w-[800px] tracking-tight">
          One graph. Every decision.<br />Permanently searchable.
        </h2>
        <p className="font-display text-[16px] md:text-[18px] text-text-muted max-w-[640px] mt-6 leading-[1.7]">
          DevBrain builds a living knowledge graph from your repo's full history.
          Every node is traceable. Every answer is sourced.
        </p>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.5, ease: "easeOut", delay: 0.1 }}
        className="w-full max-w-[1300px] mt-12 md:mt-16 mb-12 md:mb-20"
      >
        <RadialDiagram />
      </motion.div>
      
    </section>
  );
}
