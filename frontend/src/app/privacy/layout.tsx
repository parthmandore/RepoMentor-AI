import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy & Data Protection',
  description: 'Understand how RepoMentor AI collects, processes, and protects your information, cookies, and repository analysis data.',
  alternates: {
    canonical: 'https://repomentor.netlify.app/privacy',
  },
  openGraph: {
    title: 'Privacy Policy & Data Protection | RepoMentor AI',
    description: 'Understand how RepoMentor AI collects, processes, and protects your information, cookies, and repository analysis data.',
    url: 'https://repomentor.netlify.app/privacy',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Privacy Policy',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Privacy Policy & Data Protection | RepoMentor AI',
    description: 'Understand how RepoMentor AI collects, processes, and protects your information, cookies, and repository analysis data.',
    images: ['/og-image.png'],
  },
};

export default function PrivacyLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
