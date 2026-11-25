'use client';

import React, { useState, useEffect } from 'react';
import { useTheme } from '@/app/ThemeProvider';
import { Sun, Moon } from 'lucide-react';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div 
        className="w-12 h-6 rounded-full border border-borderPrimary bg-bgSecondary p-1 flex items-center justify-between opacity-60" 
        aria-hidden="true"
      >
        <div className="w-3 h-3" />
        <div className="w-3 h-3" />
      </div>
    );
  }

  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      className={`relative flex items-center justify-between p-1 w-12 h-6 rounded-full cursor-pointer transition-colors duration-200 border focus:outline-none focus-visible:ring-1 focus-visible:ring-signal ${
        isDark 
          ? 'bg-[#1A1917] border-[#2A2825] hover:border-[#403D37]' 
          : 'bg-[#EFECE4] border-[#E2DDD5] hover:border-[#CDC7BC]'
      }`}
      aria-label="Toggle Theme"
      title={`Switch to ${isDark ? 'Light' : 'Dark'} Paper Theme`}
    >
      <Sun className={`w-3 h-3 ml-0.5 z-10 transition-transform duration-200 ${
        isDark 
          ? 'text-textMuted opacity-40 scale-75' 
          : 'text-textPrimary scale-100'
      }`} />
      
      <Moon className={`w-3 h-3 mr-0.5 z-10 transition-transform duration-200 ${
        isDark 
          ? 'text-textPrimary scale-100' 
          : 'text-textMuted opacity-40 scale-75'
      }`} />
      
      <div
        className={`absolute w-4 h-4 rounded-full transition-transform duration-200 ease-out ${
          isDark 
            ? 'translate-x-[24px] bg-[#2A2825] border border-[#403D37]' 
            : 'translate-x-[2px] bg-white border border-[#E2DDD5]'
        }`}
      />
    </button>
  );
}
