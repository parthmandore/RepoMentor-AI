import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Execution Profiling & Complexity Analysis',
  description: 'Deep cyclomatic and cognitive complexity hotspot analysis, large file diagnostics, and AST metrics.',
  alternates: {
    canonical: 'https://repomentor.netlify.app',
  },
  openGraph: {
    title: 'Execution Profiling & Complexity Analysis | RepoMentor AI',
    description: 'Deep cyclomatic and cognitive complexity hotspot analysis, large file diagnostics, and AST metrics.',
    url: 'https://repomentor.netlify.app',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Execution Profiling & Complexity Analysis',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Execution Profiling & Complexity Analysis | RepoMentor AI',
    description: 'Deep cyclomatic and cognitive complexity hotspot analysis, large file diagnostics, and AST metrics.',
    images: ['/og-image.png'],
  },
};

export default function PerformanceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
