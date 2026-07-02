import { Navbar } from './Navbar';
import { Hero } from './Hero';
import { About } from './About';
import { Features } from './Features';
import { UseCases } from './UseCases';
import { Benefits } from './Benefits';
import { Footer } from './Footer';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg selection:bg-accent-mint selection:text-[#040200]">
      <Navbar />
      <main>
        <Hero />
        <About />
        <Features />
        <UseCases />
        <Benefits />
      </main>
      <Footer />
    </div>
  );
}
