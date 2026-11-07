import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Source Code & Smells Inspector',
  description: 'Line-by-line source code inspection with localized code smells, cyclomatic complexity, and dependency imports tree.',
  alternates: {
    canonical: 'https://repomentor.netlify.app',
  },
  openGraph: {
    title: 'Source Code & Smells Inspector | RepoMentor AI',
    description: 'Line-by-line source code inspection with localized code smells, cyclomatic complexity, and dependency imports tree.',
    url: 'https://repomentor.netlify.app',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Source Code Inspector',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Source Code & Smells Inspector | RepoMentor AI',
    description: 'Line-by-line source code inspection with localized code smells, cyclomatic complexity, and dependency imports tree.',
    images: ['/og-image.png'],
  },
};

export default function FileDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
