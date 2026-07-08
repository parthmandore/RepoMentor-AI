import './globals.css';
import type { Metadata } from 'next';
import { ThemeProvider } from './ThemeProvider';

export const metadata: Metadata = {
  title: 'Repository Mentor AI — Portfolio Project',
  description: 'Instant AI code mentoring and repo structural evaluation for software engineers.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased min-h-screen bg-bgPrimary text-textPrimary flex flex-col justify-between">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
