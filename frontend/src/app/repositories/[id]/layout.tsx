import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Repository Quality Assessment',
  description: 'Automated codebase health scoring, maintainability metrics, code smells distribution, and refactoring timeline.',
  alternates: {
    canonical: 'https://repomentor.netlify.app',
  },
  openGraph: {
    title: 'Repository Quality Assessment | RepoMentor AI',
    description: 'Automated codebase health scoring, maintainability metrics, code smells distribution, and refactoring timeline.',
    url: 'https://repomentor.netlify.app',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Codebase Quality Assessment',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Repository Quality Assessment | RepoMentor AI',
    description: 'Automated codebase health scoring, maintainability metrics, code smells distribution, and refactoring timeline.',
    images: ['/og-image.png'],
  },
  robots: {
    index: false,
    follow: true,
  },
};

export default function RepositoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
