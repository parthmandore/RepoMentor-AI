import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Repository Knowledge Base Wiki & Vector Index',
  description: 'Vector-indexed architectural knowledge wiki, module classifications, entry points, and semantic code search.',
  alternates: {
    canonical: 'https://repomentor.netlify.app',
  },
  openGraph: {
    title: 'Repository Knowledge Base Wiki & Vector Index | RepoMentor AI',
    description: 'Vector-indexed architectural knowledge wiki, module classifications, entry points, and semantic code search.',
    url: 'https://repomentor.netlify.app',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Knowledge Base Wiki',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Repository Knowledge Base Wiki & Vector Index | RepoMentor AI',
    description: 'Vector-indexed architectural knowledge wiki, module classifications, entry points, and semantic code search.',
    images: ['/og-image.png'],
  },
};

export default function KnowledgeLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
