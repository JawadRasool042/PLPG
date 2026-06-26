import React from 'react';

/** Render plain text with **bold** markers and paragraph breaks. */
export function formatLessonExplanation(text: string): React.ReactNode {
  const trimmed = text?.trim() || '';
  if (!trimmed) return null;

  const paragraphs = trimmed.split(/\n\n+/);
  return paragraphs.map((para, pIdx) => {
    const parts = para.split(/(\*\*[^*]+\*\*)/g);
    return (
      <p key={pIdx} className="text-sm text-slate-800 leading-relaxed mb-3 last:mb-0">
        {parts.map((part, i) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return (
              <strong key={i} className="font-semibold text-slate-900">
                {part.slice(2, -2)}
              </strong>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </p>
    );
  });
}
