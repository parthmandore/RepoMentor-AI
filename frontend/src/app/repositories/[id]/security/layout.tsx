import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Security Vulnerabilities & Dependency Audit',
  description: 'Automated vulnerability scanning, hardcoded secret detection, SQL injection analysis, and dependency security audits.',
  alternates: {
    canonical: 'https://repomentor.netlify.app',
  },
  openGraph: {
    title: 'Security Vulnerabilities & Dependency Audit | RepoMentor AI',
    description: 'Automated vulnerability scanning, hardcoded secret detection, SQL injection analysis, and dependency security audits.',
    url: 'https://repomentor.netlify.app',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Security Vulnerabilities Analysis',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Security Vulnerabilities & Dependency Audit | RepoMentor AI',
    description: 'Automated vulnerability scanning, hardcoded secret detection, SQL injection analysis, and dependency security audits.',
    images: ['/og-image.png'],
  },
};

export default function SecurityLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
