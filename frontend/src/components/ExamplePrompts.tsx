import React from 'react';

interface ExamplePromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const PROMPT_ROWS = [
  [
    'What does NIEL make?',
    'Transformer details',
    'Switchgear & panels',
    'Industries served',
  ],
  [
    'What do you need for a quote?',
    'Request a quote',
    'Talk to sales',
  ],
];

export const ExamplePrompts: React.FC<ExamplePromptsProps> = ({ onSelectPrompt, disabled }) => {
  return (
    <div className="niel-pills-wrapper">
      {PROMPT_ROWS.map((row, rowIdx) => (
        <div key={rowIdx} className="niel-pills-row">
          {row.map((prompt, idx) => (
            <button
              key={idx}
              type="button"
              className="niel-action-pill"
              onClick={() => onSelectPrompt(prompt)}
              disabled={disabled}
            >
              {prompt}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
};
