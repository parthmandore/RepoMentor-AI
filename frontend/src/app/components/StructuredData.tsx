import React from 'react';

export default function StructuredData() {
  const websiteSchema = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    '@id': 'https://repomentor.netlify.app/#website',
    url: 'https://repomentor.netlify.app',
    name: 'RepoMentor AI',
    description: 'Automated repository quality analysis, cyclomatic complexity grading, security vulnerability scanning, and evidence-grounded AI Code Mentorship.',
    inLanguage: 'en-US',
    publisher: {
      '@id': 'https://repomentor.netlify.app/#organization',
    },
  };

  const organizationSchema = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    '@id': 'https://repomentor.netlify.app/#organization',
    name: 'RepoMentor AI',
    url: 'https://repomentor.netlify.app',
    logo: {
      '@type': 'ImageObject',
      url: 'https://repomentor.netlify.app/android-chrome-512x512.png',
      width: '512',
      height: '512',
    },
    sameAs: [
      'https://github.com/parthmandore/RepoMentor-AI',
    ],
  };

  const softwareAppSchema = {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    '@id': 'https://repomentor.netlify.app/#software',
    name: 'RepoMentor AI',
    applicationCategory: 'DeveloperApplication',
    operatingSystem: 'All modern web browsers',
    browserRequirements: 'Requires JavaScript. Requires HTML5.',
    softwareVersion: '1.0.0',
    description: 'Automated codebase quality analysis, cyclomatic complexity grading, security vulnerability scanning, and evidence-grounded AI Code Mentorship.',
    url: 'https://repomentor.netlify.app',
    image: 'https://repomentor.netlify.app/og-image.png',
    author: {
      '@type': 'Person',
      name: 'Parth Mandore',
      url: 'https://github.com/parthmandore',
    },
    publisher: {
      '@id': 'https://repomentor.netlify.app/#organization',
    },
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareAppSchema) }}
      />
    </>
  );
}
