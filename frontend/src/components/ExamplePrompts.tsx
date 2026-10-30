import React from 'react';
import { HelpCircle } from 'lucide-react';

interface ExamplePromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const PROMPTS = [
  'What power ratings are documented for NIEL motors?',
  'What voltage and insulation class is mentioned?',
  'What mounting types are listed for these motors?',
  'What cooling method and duty cycle are specified?',
  'What is the price of a 50 kW motor?',
];

export const ExamplePrompts: React.FC<ExamplePromptsProps> = ({ onSelectPrompt, disabled }) => {
  return (
    <div className="niel-examples-container">
      <div className="niel-examples-header">
        <HelpCircle size={14} />
        <span>Example Inquiries:</span>
      </div>
      <div className="niel-examples-grid">
        {PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            className="niel-example-pill"
            onClick={() => onSelectPrompt(prompt)}
            disabled={disabled}
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
};

