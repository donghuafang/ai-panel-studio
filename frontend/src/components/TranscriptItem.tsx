import type { Guest, Speech } from '../types';
import { SPEECH_TYPE_LABELS } from '../lib/constants';
import styles from './TranscriptItem.module.css';

interface TranscriptItemProps {
  speech: Speech;
  guest?: Guest;
  isLatest?: boolean;
  index: number;
}

function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 10) return '刚刚';
  if (diffSec < 60) return `${diffSec} 秒前`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} 分钟前`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr} 小时前`;
}

export default function TranscriptItem({
  speech,
  guest,
  isLatest = false,
  index,
}: TranscriptItemProps) {
  const guestColor = guest?.color || '#6B7280';
  const guestName = guest?.name || '未知嘉宾';
  const guestTitle = guest ? `${guest.profession} · ${guest.title}` : '';
  const speechTypeLabel =
    SPEECH_TYPE_LABELS[speech.speech_type] || speech.speech_type;
  const isHost = guest?.role === 'host';

  // Alternating alignment for visual variety: host stays left, guests alternate
  const isLeft = isHost || index % 2 === 0;

  return (
    <div
      data-testid="speech-item"
      className={`flex ${isLeft ? 'justify-start' : 'justify-end'} ${isLatest ? styles.slideIn : ''}`}
    >
      <div
        className={`max-w-[80%] rounded-xl bg-studio-card p-4 transition-colors ${
          isHost ? 'border border-studio-gold/20' : ''
        }`}
        style={{ borderLeftColor: guestColor, borderLeftWidth: '4px' }}
      >
        {/* Header */}
        <div className="mb-2 flex items-center gap-2 flex-wrap">
          <span
            className="text-sm font-semibold"
            style={{ color: guestColor }}
          >
            {guestName}
          </span>
          {isHost && (
            <span className="rounded-full border border-studio-gold/30 bg-studio-gold/10 px-2 py-0.5 text-xs text-studio-gold">
              主持人
            </span>
          )}
          {guestTitle && (
            <span className="text-xs text-gray-500">{guestTitle}</span>
          )}
          <span className="rounded bg-studio-border px-1.5 py-0.5 text-xs text-gray-400">
            {speechTypeLabel}
          </span>
          <span className="ml-auto text-xs text-gray-600">
            {formatRelativeTime(speech.timestamp)}
          </span>
        </div>

        {/* Content */}
        <p className="text-sm leading-relaxed text-gray-200 whitespace-pre-wrap">
          {speech.content}
        </p>
      </div>
    </div>
  );
}
