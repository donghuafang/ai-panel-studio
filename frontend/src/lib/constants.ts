export const STATUS_LABELS: Record<string, string> = {
  pending: '待确认',
  active: '进行中',
  ended: '已结束',
  error: '异常',
};

export const AGENT_STATE_LABELS: Record<string, string> = {
  idle: '待机',
  ready: '准备中',
  thinking: '思考中...',
  speaking: '发言中',
};

export const SPEECH_TYPE_LABELS: Record<string, string> = {
  statement: '陈述',
  question: '提问',
  reply: '回应',
  summary: '总结',
};

export const DEFAULT_EXPERT_COUNT = 4;
export const MIN_EXPERTS = 2;
export const MAX_EXPERTS = 8;
export const DEFAULT_MAX_ROUNDS = 3;

export const PAGE_SIZE = 20;
export const POLL_INTERVAL_MS = 30_000;
