'use client';

import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content) return null;

  // Split content by fenced code blocks
  const parts: Array<{ type: 'text' | 'code'; content: string; language?: string }> = [];
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: content.substring(lastIndex, match.index)
      });
    }
    parts.push({
      type: 'code',
      language: match[1] || 'code',
      content: match[2].trimEnd()
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      content: content.substring(lastIndex)
    });
  }

  return (
    <div className="space-y-3 font-sans text-xs sm:text-sm leading-relaxed text-textPrimary">
      {parts.map((part, index) => {
        if (part.type === 'code') {
          return (
            <CodeBlock 
              key={index} 
              code={part.content} 
              language={part.language || 'code'} 
            />
          );
        }
        return <FormattedText key={index} text={part.content} />;
      })}
    </div>
  );
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded border border-borderPrimary bg-bgTertiary overflow-hidden shadow-sm font-mono text-xs">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-borderPrimary bg-bgSecondary text-[11px] text-textSecondary">
        <span className="uppercase tracking-wider font-bold">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-textPrimary transition-colors"
          title="Copy code"
        >
          {copied ? <Check className="w-3 h-3 text-good" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-textPrimary font-mono text-[11px] leading-relaxed whitespace-pre">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function FormattedText({ text }: { text: string }) {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let currentList: string[] = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="my-2 space-y-1 pl-4 list-disc marker:text-signal">
          {currentList.map((item, idx) => (
            <li key={idx} className="text-textPrimary">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  lines.forEach((line, lineIdx) => {
    const trimmed = line.trim();

    // Check for headings
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(
        <h4 key={lineIdx} className="font-serif text-base font-bold text-textPrimary mt-3 mb-1">
          {renderInline(trimmed.substring(4))}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(
        <h3 key={lineIdx} className="font-serif text-lg font-bold text-textPrimary mt-4 mb-1 border-b border-borderPrimary pb-1">
          {renderInline(trimmed.substring(3))}
        </h3>
      );
    } else if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(
        <h2 key={lineIdx} className="font-serif text-xl font-bold text-textPrimary mt-4 mb-2">
          {renderInline(trimmed.substring(2))}
        </h2>
      );
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      currentList.push(trimmed.substring(2));
    } else if (/^\d+\.\s/.test(trimmed)) {
      currentList.push(trimmed.replace(/^\d+\.\s/, ''));
    } else if (trimmed === '') {
      flushList();
    } else {
      flushList();
      elements.push(
        <p key={lineIdx} className="my-1.5 leading-relaxed text-textPrimary">
          {renderInline(trimmed)}
        </p>
      );
    }
  });

  flushList();

  return <>{elements}</>;
}

function renderInline(text: string): React.ReactNode {
  // Parse inline code, bold, italics
  const parts = text.split(/(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g);

  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code key={i} className="px-1.5 py-0.5 rounded bg-bgTertiary border border-borderPrimary font-mono text-[11px] text-signal font-semibold">
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i} className="font-bold text-textPrimary">{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={i} className="italic text-textSecondary">{part.slice(1, -1)}</em>;
    }
    return part;
  });
}
