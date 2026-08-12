import { useMemo } from 'react';
import type { Guest, Speech } from '../types';
import { AGENT_STATE_LABELS } from '../lib/constants';
import styles from './GuestStatusWindow.module.css';

interface GuestStatusWindowProps {
  guest: Guest;
  agentState: string;
  lastSpeech?: Speech;
}

const stateColors: Record<string, string> = {
  idle: '#6B7280',
  ready: '#FBBF24',
  thinking: '#F59E0B',
  speaking: '#10B981',
};

const stateIcons: Record<string, string> = {
  idle: '⚪',
  ready: '🟡',
  thinking: '🤔',
  speaking: '🟢',
};

export default function GuestStatusWindow({
  guest,
  agentState,
  lastSpeech,
}: GuestStatusWindowProps) {
  const stateColor = stateColors[agentState] || stateColors.idle;
  const stateLabel = AGENT_STATE_LABELS[agentState] || agentState;
  const isSpeaking = agentState === 'speaking';
  const isThinking = agentState === 'thinking';

  const thoughtSummary = useMemo(() => {
    if (!lastSpeech) return null;
    return lastSpeech.content.length > 50
      ? lastSpeech.content.slice(0, 50) + '...'
      : lastSpeech.content;
  }, [lastSpeech]);

  return (
    <div
      className={`flex items-center gap-3 rounded-xl border bg-studio-card p-3 transition-all ${styles.container}`}
      style={{
        borderColor: isSpeaking ? stateColor : undefined,
        ['--guest-color' as string]: stateColor,
      }}
    >
      {/* Avatar with state ring */}
      <div className="relative flex-shrink-0">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold text-white ${
            isSpeaking || isThinking ? styles.breatheBorder : ''
          } ${isThinking ? styles.pulseAvatar : ''}`}
          style={{
            backgroundColor: guest.color + '33',
          }}
        >
          {guest.name.charAt(0)}
        </div>
        <span className="absolute -bottom-0.5 -right-0.5 text-xs">
          {stateIcons[agentState] || stateIcons.idle}
        </span>
      </div>

      {/* Info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-white">
            {guest.name}
          </span>
          {guest.role === 'host' && (
            <span className="flex-shrink-0 text-xs text-studio-gold">主持</span>
          )}
        </div>
        <p className="text-xs text-gray-400 truncate">
          {guest.profession}
        </p>
        <p className="text-xs mt-0.5 flex items-center gap-1">
          <span
            className="inline-block h-1.5 w-1.5 rounded-full flex-shrink-0"
            style={{ backgroundColor: stateColor }}
          />
          <span className="text-gray-500">
            {stateLabel}
          </span>
        </p>
        {thoughtSummary && (
          <p className="mt-1 text-xs text-gray-600 italic truncate">
            {thoughtSummary}
          </p>
        )}
      </div>
    </div>
  );
}
