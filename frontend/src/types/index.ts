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
  sender: 'user' | 'assistant';
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
