import { ChatResponse, DocumentListResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export async function askQuestion(question: string, topK: number = 5): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/v1/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
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

