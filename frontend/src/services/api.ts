import { ChatResponse, ChatTurn, DocumentListResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function askQuestion(
  question: string,
  topK: number = 5,
  conversationHistory: ChatTurn[] = [],
  sessionId?: string
): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question,
        top_k: topK,
        conversation_history: conversationHistory,
        session_id: sessionId,
      }),
    });
  } catch (netErr: any) {
    throw new Error('Cannot connect to backend server. Please verify the FastAPI backend is running on http://127.0.0.1:8000.');
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    if (response.status === 500 && !errorData.detail) {
      throw new Error('Backend server is not reachable on http://127.0.0.1:8000. Please make sure the FastAPI backend is started in a separate terminal.');
    }
    throw new Error(errorData.detail || `Server error (${response.status})`);
  }

  return response.json();
}

export async function listDocuments(): Promise<DocumentListResponse> {
  const response = await fetch(`${API_BASE}/api/v1/documents`);
  if (!response.ok) {
    throw new Error('Failed to fetch indexed documents list');
  }
  return response.json();
}

export async function uploadDocument(file: File, adminKey: string): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/v1/documents/upload`, {
    method: 'POST',
    headers: {
      'X-Admin-Key': adminKey,
    },
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed (${response.status})`);
  }

  return response.json();
}

export async function deleteDocument(docId: string, adminKey: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/v1/documents/${encodeURIComponent(docId)}`, {
    method: 'DELETE',
    headers: {
      'X-Admin-Key': adminKey,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Deletion failed (${response.status})`);
  }

  return response.json();
}

