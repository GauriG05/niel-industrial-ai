/**
 * WhatsApp Click-to-Chat Integration for NIEL Support
 * Target WhatsApp number: +91 97413 07999
 */

import { Message } from '../types';

export const NIEL_WHATSAPP_NUMBER = '919741307999';

export interface WhatsAppContext {
  query: string;
  selectedProduct: string;
  requirements: string;
  unresolvedIssue: string;
  sessionId?: string;
}

export function extractConversationSummary(messages: Message[]): WhatsAppContext | null {
  const userMessages = messages.filter((m) => m.sender === 'user' && m.text.trim());
  if (userMessages.length === 0) {
    return null;
  }

  const firstQuery = userMessages[0].text.trim();
  const latestQuery = userMessages[userMessages.length - 1].text.trim();
  const allUserText = userMessages.map((m) => m.text).join(' ');

  // Product Detection
  let selectedProduct = 'Industrial Electrical Equipment';
  if (/\b(ac motor|ac motors|cage rotor|wound rotor|flameproof|crane duty|mill duty)\b/i.test(allUserText)) {
    selectedProduct = 'AC Motors';
  } else if (/\b(dc motor|dc motors)\b/i.test(allUserText)) {
    selectedProduct = 'DC Motors';
  } else if (/\b(transformer|transformers|distribution transformer|power transformer|oltc)\b/i.test(allUserText)) {
    selectedProduct = 'Distribution / Power Transformers';
  } else if (/\b(switchgear|panel|mcc|pcc|vcb|breaker)\b/i.test(allUserText)) {
    selectedProduct = 'Switchgear & Control Panels (MV/LV)';
  } else if (/\b(pump|pumps|monoblock|submersible|vacuum pump)\b/i.test(allUserText)) {
    selectedProduct = 'Industrial & Utility Pumps';
  } else if (/\b(substation|css|compact secondary substation)\b/i.test(allUserText)) {
    selectedProduct = 'Substation Systems (CSS)';
  } else if (/\b(gearbox|gearboxes|brake motor|cycloidal)\b/i.test(allUserText)) {
    selectedProduct = 'Gearboxes & Brake Motors';
  } else if (/\b(drive|drives|vfd|ac drive|dc drive)\b/i.test(allUserText)) {
    selectedProduct = 'AC/DC Drives';
  }

  // Specifications & Technical Requirements Extraction
  const specTokens = allUserText.match(/\b\d+(\.\d+)?\s*(kw|hp|kva|mva|kv|v|rpm|bar|m3\/hr|amps?|mm\s*hg)\b/gi) || [];
  const uniqueSpecs = Array.from(new Set(specTokens.map((s) => s.trim())));
  const requirements = uniqueSpecs.length > 0 ? uniqueSpecs.join(', ') : 'As discussed in chat';

  return {
    query: firstQuery,
    selectedProduct,
    requirements,
    unresolvedIssue: latestQuery,
  };
}

export function generateWhatsAppMessage(messages: Message[], sessionId?: string): string {
  const summary = extractConversationSummary(messages);

  if (!summary) {
    // Scenario 2: Fallback when no conversation history
    return 'Hello NIEL Team, I would like to connect with your support team. Please assist me.';
  }

  // Scenario 1: Contextual summary with query, product, requirements & unresolved issue
  const lines = [
    'Hello NIEL Team,',
    '',
    'I would like human support assistance regarding an inquiry on your website:',
    '',
    `• Customer Query: ${summary.query}`,
    `• Selected Product: ${summary.selectedProduct}`,
    `• Requirements: ${summary.requirements}`,
    `• Unresolved Issue / Request: ${summary.unresolvedIssue}`,
  ];

  if (sessionId) {
    lines.push(`• Session Reference: ${sessionId}`);
  }

  lines.push('', 'Please connect me with a support engineer.');
  return lines.join('\n');
}

export function generateWhatsAppUrl(messages: Message[], sessionId?: string): string {
  const messageText = generateWhatsAppMessage(messages, sessionId);
  const encodedText = encodeURIComponent(messageText);
  return `https://wa.me/${NIEL_WHATSAPP_NUMBER}?text=${encodedText}`;
}

export function openWhatsAppChat(messages: Message[], sessionId?: string): string {
  const url = generateWhatsAppUrl(messages, sessionId);
  if (typeof window !== 'undefined') {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
  return url;
}

