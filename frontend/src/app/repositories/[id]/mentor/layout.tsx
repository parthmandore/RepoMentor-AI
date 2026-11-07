import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'AI Code Mentor & Knowledge Search',
  description: 'Interactive AI-driven code mentoring with grounded file citations, principle explanations, and contextual refactoring advice.',
  alternates: {
    canonical: 'https://repomentor.netlify.app',
  },
  openGraph: {
    title: 'AI Code Mentor & Knowledge Search | RepoMentor AI',
    description: 'Interactive AI-driven code mentoring with grounded file citations, principle explanations, and contextual refactoring advice.',
    url: 'https://repomentor.netlify.app',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — AI Code Mentor',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'AI Code Mentor & Knowledge Search | RepoMentor AI',
    description: 'Interactive AI-driven code mentoring with grounded file citations, principle explanations, and contextual refactoring advice.',
    images: ['/og-image.png'],
  },
};

export default function MentorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
