import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { About } from './components/About';
import { Features } from './components/Features';
import { UseCases } from './components/UseCases';
import { Benefits } from './components/Benefits';
import { Footer } from './components/Footer';

export default function App() {
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
