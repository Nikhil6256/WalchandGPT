/**
 * Global type definitions for WalchandGPT frontend.
 */

export interface User {
  id: string;
  name: string;
  email: string;
  role: 'student' | 'faculty' | 'admin';
  department?: string;
  year?: number;
  is_active: boolean;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Citation {
  document_id: string;
  document_title: string;
  chunk_content: string;
  page_number?: number;
  similarity_score: number;
  department?: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  created_at: string;
  metadata?: {
    citations?: Citation[];
    confidence?: 'high' | 'medium' | 'low';
    intent?: string;
    total_latency_ms?: number;
  };
  // Frontend-only fields for streaming
  isStreaming?: boolean;
  statusEvents?: string[];
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
}

export interface Document {
  id: string;
  title: string;
  description?: string;
  file_name: string;
  document_type: string;
  department?: string;
  document_category?: string;
  indexing_status: 'pending' | 'processing' | 'completed' | 'failed';
  chunk_count: number;
  created_at: string;
}

export interface AnalyticsData {
  total_conversations: number;
  total_messages: number;
  total_documents: number;
  helpful_count: number;
  not_helpful_count: number;
  helpful_percentage: number;
  documents_by_status: Record<string, number>;
  tool_usage_count: Record<string, number>;
}

// SSE event types from the streaming endpoint
export type SSEEventType = 'metadata' | 'status' | 'token' | 'done' | 'error' | 'end';

export interface SSEEvent {
  type: SSEEventType;
  data: Record<string, any>;
}
