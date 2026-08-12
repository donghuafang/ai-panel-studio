import type {
  Discussion,
  DiscussionDetail,
  DiscussionListResponse,
  GenerateGuestsResponse,
  StatusResponse,
  Consensus,
  Divergence,
  CreateDiscussionRequest,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    let detail = '未知错误';
    let code: string | undefined;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || errorBody.message || detail;
      code = errorBody.code;
    } catch {
      detail = `请求失败 (${response.status})`;
    }
    throw new ApiError(response.status, detail, code);
  }

  return response.json();
}

export const api = {
  healthCheck: () =>
    request<{ status: string }>('/api/health'),

  listDiscussions: (page = 1, pageSize = 20) =>
    request<DiscussionListResponse>(
      `/api/discussions?page=${page}&page_size=${pageSize}`,
    ),

  createDiscussion: (body: CreateDiscussionRequest) =>
    request<Discussion>('/api/discussions', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getDiscussion: (id: string) =>
    request<DiscussionDetail>(`/api/discussions/${id}`),

  generateGuests: (id: string) =>
    request<GenerateGuestsResponse>(`/api/discussions/${id}/generate-guests`, {
      method: 'POST',
    }),

  confirmDiscussion: (id: string) =>
    request<StatusResponse>(`/api/discussions/${id}/confirm`, {
      method: 'POST',
    }),

  endDiscussion: (id: string) =>
    request<StatusResponse>(`/api/discussions/${id}/end`, {
      method: 'POST',
    }),

  getConsensusList: (id: string) =>
    request<Consensus[]>(`/api/discussions/${id}/consensus`),

  getDivergenceList: (id: string) =>
    request<Divergence[]>(`/api/discussions/${id}/divergence`),
};
