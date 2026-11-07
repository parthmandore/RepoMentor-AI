import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Module Dependency & Architecture Graph',
  description: 'Interactive module dependency graph, circular import analysis, coupling indicators, and architectural pattern classification.',
  alternates: {
    canonical: 'https://repomentor.netlify.app',
  },
  openGraph: {
    title: 'Module Dependency & Architecture Graph | RepoMentor AI',
    description: 'Interactive module dependency graph, circular import analysis, coupling indicators, and architectural pattern classification.',
    url: 'https://repomentor.netlify.app',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Architecture & Dependency Graph',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Module Dependency & Architecture Graph | RepoMentor AI',
    description: 'Interactive module dependency graph, circular import analysis, coupling indicators, and architectural pattern classification.',
    images: ['/og-image.png'],
  },
};

export default function ArchitectureLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
