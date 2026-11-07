import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Architecture & Maintainability Assessment',
  description: 'Detailed code health grade, maintainability index, technical debt forecasting, and categorized smells distribution.',
  alternates: {
    canonical: 'https://repomentor.netlify.app',
  },
  openGraph: {
    title: 'Architecture & Maintainability Assessment | RepoMentor AI',
    description: 'Detailed code health grade, maintainability index, technical debt forecasting, and categorized smells distribution.',
    url: 'https://repomentor.netlify.app',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Maintainability Assessment',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Architecture & Maintainability Assessment | RepoMentor AI',
    description: 'Detailed code health grade, maintainability index, technical debt forecasting, and categorized smells distribution.',
    images: ['/og-image.png'],
  },
};

export default function AssessmentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
