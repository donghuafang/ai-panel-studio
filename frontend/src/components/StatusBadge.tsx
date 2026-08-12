import { STATUS_LABELS } from '../lib/constants';

interface StatusBadgeProps {
  status: string;
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const label = STATUS_LABELS[status] || status;

  const styles: Record<string, string> = {
    pending: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    active:
      'bg-green-500/20 text-green-400 border-green-500/30',
    ended: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    error: 'bg-red-500/20 text-red-400 border-red-500/30',
  };

  const dotStyles: Record<string, string> = {
    active: 'bg-green-400 animate-pulse-dot',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
        styles[status] || styles.pending
      }`}
    >
      {dotStyles[status] && (
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${dotStyles[status]}`}
        />
      )}
      {label}
    </span>
  );
}
