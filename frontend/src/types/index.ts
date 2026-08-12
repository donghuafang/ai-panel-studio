// ─── Core Entities ─────────────────────────────────────────────

export interface Discussion {
  id: string;
  topic: string;
  status: 'pending' | 'active' | 'ended';
  expert_count: number;
  host_id: string | null;
  max_rounds: number;
  current_round: number;
  created_at: string;
  updated_at: string;
}

export interface DiscussionDetail extends Discussion {
  guests: Guest[];
  speeches: Speech[];
}

export interface Guest {
  id: string;
  discussion_id: string;
  name: string;
  profession: string;
  title: string;
  stance: string;
  color: string;
  role: 'host' | 'guest';
  agent_state: 'idle' | 'ready' | 'speaking' | 'thinking';
  created_at: string;
}

export interface Speech {
  id: string;
  discussion_id: string;
  guest_id: string | null;
  round_number: number;
  content: string;
  speech_type: 'statement' | 'question' | 'reply' | 'summary';
  timestamp: string;
}

export interface Consensus {
  id: string;
  discussion_id: string;
  content: string;
  supporter_guest_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface Divergence {
  id: string;
  discussion_id: string;
  content: string;
  opposing_pairs: string[][];
  created_at: string;
  updated_at: string;
}

// ─── API Response Wrappers ──────────────────────────────────────

export interface DiscussionListResponse {
  discussions: Discussion[];
  total: number;
}

export interface GenerateGuestsResponse {
  guests: Guest[];
}

export interface StatusResponse {
  status: string;
}

// ─── SSE Event Payloads ─────────────────────────────────────────

export interface SpeechEvent {
  speech: Speech;
  round_number: number;
}

export interface GuestStateEvent {
  guest_id: string;
  agent_state: string;
}

export interface ConsensusEvent {
  consensus: Consensus;
}

export interface DivergenceEvent {
  divergence: Divergence;
}

export interface DiscussionEndedEvent {
  discussion_id: string;
  final_consensus: Consensus[];
  final_divergence: Divergence[];
}

export interface ErrorEvent {
  code: string;
  message: string;
}

// ─── Request Bodies ─────────────────────────────────────────────

export interface CreateDiscussionRequest {
  topic: string;
  expert_count: number;
  max_rounds: number;
}
