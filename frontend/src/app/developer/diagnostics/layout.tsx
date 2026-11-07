import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'System Diagnostics & Health Telemetry',
  description: 'Real-time telemetry, service health monitoring, database connectivity, and active ingestion queue status for RepoMentor AI.',
  alternates: {
    canonical: 'https://repomentor.netlify.app/developer/diagnostics',
  },
  openGraph: {
    title: 'System Diagnostics & Health Telemetry | RepoMentor AI',
    description: 'Real-time telemetry, service health monitoring, database connectivity, and active ingestion queue status for RepoMentor AI.',
    url: 'https://repomentor.netlify.app/developer/diagnostics',
    type: 'website',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: 'RepoMentor AI — System Diagnostics & Health Telemetry',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'System Diagnostics & Health Telemetry | RepoMentor AI',
    description: 'Real-time telemetry, service health monitoring, database connectivity, and active ingestion queue status for RepoMentor AI.',
    images: ['/og-image.png'],
  },
};

export default function DiagnosticsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
