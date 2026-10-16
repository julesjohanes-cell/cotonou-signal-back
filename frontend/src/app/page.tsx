'use client';

import { useEffect, useState } from 'react';
import { checkBackendHealth, fetchFeatures, HealthResponse, FeaturesResponse } from '@/lib/api';

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [features, setFeatures] = useState<FeaturesResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [healthData, featuresData] = await Promise.all([
          checkBackendHealth(),
          fetchFeatures(),
        ]);
        setHealth(healthData);
        setFeatures(featuresData);
        setError(null);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Erreur de connexion';
        setError(message);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-indigo-500 selection:text-white">
      {/* Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/40 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="h-3 w-3 rounded-full bg-indigo-500 shadow-[0_0_12px_rgba(99,102,241,0.8)]"></span>
            <span className="font-bold tracking-tight text-lg text-white">SandBos Monorepo</span>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono">
            <span className="px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">Next.js 15+</span>
            <span className="px-2.5 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700">Django 6 (DRF)</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 py-12 flex-1 w-full flex flex-col justify-center">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold mb-4 uppercase tracking-wider">
            Architecture Monorepo Découplée
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-4">
            Next.js <span className="text-indigo-400">+</span> Django REST
          </h1>
          <p className="text-slate-400 text-base sm:text-lg">
            Frontend et backend prêts, configurés avec typage TypeScript, Tailwind CSS, et communication API REST.
          </p>
        </div>

        {/* Backend Status Card */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">Statut Backend Django</h2>
            {loading ? (
              <div className="flex items-center gap-2 text-slate-400 text-sm">
                <div className="w-4 h-4 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                Vérification de l&apos;API...
              </div>
            ) : error ? (
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">
                  <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse"></span>
                  Serveur Django éteint
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  Lancez le serveur backend avec :<br />
                  <code className="text-indigo-300 bg-slate-950 px-1 py-0.5 rounded border border-slate-800">cd backend &amp;&amp; venv/bin/python manage.py runserver</code>
                </p>
              </div>
            ) : health ? (
              <div className="space-y-2">
                <div className="inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
                  En ligne ({health.status})
                </div>
                <p className="text-xs text-slate-400 font-mono">Service : {health.service}</p>
                <p className="text-xs text-slate-500 font-mono">Timestamp : {new Date(health.timestamp).toLocaleTimeString()}</p>
              </div>
            ) : null}
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">Frontend Next.js</h2>
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-md bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <span className="h-2 w-2 rounded-full bg-indigo-400"></span>
                Opérationnel (Port 3000)
              </div>
              <p className="text-xs text-slate-400 font-mono">Mode : App Router (src/)</p>
              <p className="text-xs text-slate-500 font-mono">Styling : Tailwind CSS</p>
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-xl backdrop-blur-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">CORS &amp; Sécurité</h2>
            <div className="space-y-2">
              <div className="inline-flex items-center gap-2 text-xs font-semibold px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
                CORS Headers activés
              </div>
              <p className="text-xs text-slate-400 font-mono">Origine : http://localhost:3000</p>
              <p className="text-xs text-slate-500 font-mono">Auth : DRF Ready</p>
            </div>
          </div>
        </div>

        {/* Features List */}
        <div className="rounded-2xl bg-slate-900/40 border border-slate-800 p-6">
          <h3 className="text-base font-semibold text-white mb-4">Modules &amp; Capacités configurées</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {(features?.items || [
              { id: 1, title: 'Frontend Next.js (App Router, Tailwind CSS)', status: 'Prêt' },
              { id: 2, title: 'Backend Django REST Framework', status: 'Actif' },
              { id: 3, title: 'CORS & Communication API', status: 'Configuré' },
              { id: 4, title: 'Base de données & Modèles', status: 'Prêt à être étendu' },
            ]).map((item) => (
              <div key={item.id} className="flex items-center justify-between p-3 rounded-lg bg-slate-950/60 border border-slate-800/80">
                <span className="text-sm text-slate-300">{item.title}</span>
                <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-800 text-indigo-300 border border-slate-700">
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/30 py-6 text-center text-xs text-slate-500">
        SandBos Monorepo — Next.js &amp; Django REST Framework
      </footer>
    </div>
  );
}
