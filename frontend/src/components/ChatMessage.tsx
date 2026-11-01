import React from 'react';
import { FileText, ExternalLink } from 'lucide-react';
import { Message, PdfAttachment } from '../types';

interface ChatMessageProps {
  message: Message;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.sender === 'user';

  // Extract PDF attachments from message.pdf_attachments or derive from citations
  const pdfAttachments: PdfAttachment[] = [];
  const seenFiles = new Set<string>();

  if (message.pdf_attachments && message.pdf_attachments.length > 0) {
    message.pdf_attachments.forEach((pdf) => {
      if (!seenFiles.has(pdf.filename)) {
        seenFiles.add(pdf.filename);
        pdfAttachments.push(pdf);
      }
    });
  } else if (message.citations && message.citations.length > 0) {
    message.citations.forEach((c) => {
      const displayFilename = c.source_filename.replace(/\.txt$/i, '.pdf');
      if (!seenFiles.has(displayFilename)) {
        seenFiles.add(displayFilename);
        pdfAttachments.push({
          filename: displayFilename,
          page: c.page_number,
          url: `/pdfs/${encodeURIComponent(displayFilename)}#page=${c.page_number}`,
          title: `${displayFilename.replace('.pdf', '')} (Page ${c.page_number})`,
        });
      }
    });
  }

  return (
    <div className={`niel-msg-row ${isUser ? 'niel-msg-user' : 'niel-msg-assistant'}`}>
      <div className="niel-msg-bubble-container">
        <div className={`niel-msg-bubble ${message.isError ? 'niel-msg-error' : ''}`}>
          {message.sender === 'agent' && (
            <div className="niel-agent-badge">
              <span>NIEL Support Engineer</span>
            </div>
          )}
          <div className="niel-msg-text">
            {message.text.split('\n').map((line, i) => {
              const cleanLine = line.replace(/\*\*/g, '');
              return (
                <p key={i} style={{ marginBottom: cleanLine ? '6px' : '0' }}>
                  {cleanLine}
                </p>
              );
            })}
          </div>

          {/* Clean PDF Brochure Attachments when customer inquires about products */}
          {!isUser && pdfAttachments.length > 0 && (
            <div className="niel-pdf-attachments-container">
              <div className="niel-pdf-attachment-header">Official Product Documentation</div>
              <div className="niel-pdf-attachments-list">
                {pdfAttachments.map((pdf, idx) => (
                  <a
                    key={idx}
                    href={pdf.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="niel-pdf-attachment-card"
                    title={`Click to open ${pdf.filename}`}
                  >
                    <div className="niel-pdf-attachment-icon">
                      <FileText size={18} color="#dc2626" />
                    </div>
                    <div className="niel-pdf-attachment-meta">
                      <span className="niel-pdf-attachment-title">{pdf.filename}</span>
                      <span className="niel-pdf-attachment-sub">
                        {pdf.page ? `Official Brochure • Page ${pdf.page}` : 'Official NIEL Technical Brochure'}
                      </span>
                    </div>
                    <div className="niel-pdf-attachment-action">
                      <span>View PDF</span>
                      <ExternalLink size={12} />
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
