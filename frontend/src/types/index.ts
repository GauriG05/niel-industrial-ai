export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface Citation {
  source_filename: string;
  page_number: number;
  chunk_id: string;
  quote_snippet?: string;
}

export interface UsageMetadata {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  evidence_sufficient: boolean;
  clarification_needed: boolean;
  request_id: string;
  usage?: UsageMetadata;
}

export interface Message {
  id: string;
  sender: 'user' | 'assistant' | 'agent';
  text: string;
  citations?: Citation[];
  evidence_sufficient?: boolean;
  timestamp: string;
  isError?: boolean;
}

export interface DocumentSummary {
  doc_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  created_at: string;
  file_size_bytes: number;
}

export interface DocumentListResponse {
  total_documents: number;
  total_chunks: number;
  documents: DocumentSummary[];
}

export interface SupportTicket {
  id: string;
  customer_id?: string;
  session_id?: string;
  product_category: string;
  issue_description: string;
  severity: string;
  status: string;
  created_at: string;
  resolved_at?: string;
}

export interface SalesLead {
  id: number;
  customer_id?: string;
  session_id?: string;
  product_interest: string;
  requirement_details?: string;
  required_quantity?: number;
  location?: string;
  status: string;
  priority: string;
  created_at: string;
}

export interface CustomerProfile {
  customer_id: string;
  name?: string;
  email?: string;
  phone?: string;
  company?: string;
  industry?: string;
  interests?: string[];
  preferences?: Record<string, any>;
  has_consented: boolean;
  open_tickets_count: number;
  recent_tickets: any[];
  recent_leads: any[];
}

export interface EscalatedSession {
  session_id: string;
  created_at: string;
  escalated_at: string;
  human_active: boolean;
  last_message?: string;
  last_message_role?: string;
}
