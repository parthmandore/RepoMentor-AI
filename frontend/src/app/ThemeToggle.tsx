'use client';

import React from 'react';
import { useTheme } from '@/app/ThemeProvider';
import { Sun, Moon } from 'lucide-react';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === 'dark';

  return (
    <button
      onClick={toggleTheme}
      className={`relative flex items-center justify-between p-1 w-14 h-7 rounded-full cursor-pointer transition-all duration-500 shadow-inner border group focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 dark:focus-visible:ring-brand-400 focus-visible:ring-offset-2 ${
        isDark 
          ? 'bg-zinc-900 border-zinc-800 hover:border-indigo-500/50' 
          : 'bg-gradient-to-r from-amber-100 to-orange-100 border-orange-200 hover:border-orange-300'
      }`}
      aria-label="Toggle Theme"
    >
      {/* Sun Icon */}
      <Sun className={`w-3.5 h-3.5 ml-0.5 z-10 transition-all duration-500 ${
        isDark 
          ? 'text-zinc-500 scale-75 opacity-50' 
          : 'text-amber-600 scale-110 rotate-45'
      }`} />
      
      {/* Moon Icon */}
      <Moon className={`w-3.5 h-3.5 mr-0.5 z-10 transition-all duration-500 ${
        isDark 
          ? 'text-indigo-400 scale-110 -rotate-12' 
          : 'text-zinc-400 scale-75 opacity-50'
      }`} />
      
      {/* Spring Sliding Thumb */}
      <div
        className={`absolute w-5 h-5 rounded-full shadow-md transition-all duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] ${
          isDark 
            ? 'left-[30px] bg-indigo-950 border border-indigo-500/30' 
            : 'left-[4px] bg-white border border-amber-200'
        }`}
      />
    </button>
  );
}
