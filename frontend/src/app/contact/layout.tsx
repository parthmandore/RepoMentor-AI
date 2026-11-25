import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Contact & Engineering Inquiries',
  description: 'Get in touch with the RepoMentor AI team for questions, technical feedback, bug reports, or engineering inquiries.',
  alternates: {
    canonical: 'https://repomentor.netlify.app/contact',
  },
  openGraph: {
    title: 'Contact & Engineering Inquiries | RepoMentor AI',
    description: 'Get in touch with the RepoMentor AI team for questions, technical feedback, bug reports, or engineering inquiries.',
    url: 'https://repomentor.netlify.app/contact',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — Contact & Support',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Contact & Engineering Inquiries | RepoMentor AI',
    description: 'Get in touch with the RepoMentor AI team for questions, technical feedback, bug reports, or engineering inquiries.',
    images: ['/og-image.png'],
  },
};

export default function ContactLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
