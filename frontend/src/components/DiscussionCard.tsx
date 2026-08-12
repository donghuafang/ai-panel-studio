import type { Discussion } from '../types';
import StatusBadge from './StatusBadge';

interface DiscussionCardProps {
  discussion: Discussion;
  onClick: () => void;
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHr = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin} 分钟前`;
  if (diffHr < 24) return `${diffHr} 小时前`;
  if (diffDay < 30) return `${diffDay} 天前`;
  return new Date(dateStr).toLocaleDateString('zh-CN');
}

export default function DiscussionCard({
  discussion,
  onClick,
}: DiscussionCardProps) {
  const roundInfo =
    discussion.status === 'active'
      ? `第 ${discussion.current_round}/${discussion.max_rounds} 轮`
      : null;

  return (
    <button
      onClick={onClick}
      className="group w-full rounded-xl border border-studio-border bg-studio-card p-5 text-left transition-all hover:-translate-y-0.5 hover:border-studio-accent/50 hover:shadow-lg hover:shadow-studio-accent/5"
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <h3 className="text-lg font-semibold text-white line-clamp-2 group-hover:text-studio-accent transition-colors">
          {discussion.topic}
        </h3>
        <StatusBadge status={discussion.status} />
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-400">
        <span className="inline-flex items-center gap-1">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
          {discussion.expert_count} 位专家
        </span>
        {roundInfo && (
          <span className="inline-flex items-center gap-1 text-green-400">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-green-400 animate-pulse-dot" />
            {roundInfo}
          </span>
        )}
        <span className="ml-auto">{formatRelativeTime(discussion.created_at)}</span>
      </div>
    </button>
  );
}
