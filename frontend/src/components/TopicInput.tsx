interface TopicInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  maxLength?: number;
}

export default function TopicInput({
  value,
  onChange,
  disabled = false,
  maxLength = 200,
}: TopicInputProps) {
  const remaining = maxLength - value.length;
  const isAtLimit = remaining <= 0;
  const isNearLimit = remaining <= 20;

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-gray-300">
        讨论话题
      </label>
      <div className="relative">
        <textarea
          data-testid="topic-input"
          value={value}
          onChange={(e) => {
            if (e.target.value.length <= maxLength) {
              onChange(e.target.value);
            }
          }}
          disabled={disabled}
          rows={4}
          className={`w-full resize-none rounded-xl border bg-studio-card p-4 text-white placeholder-gray-500 transition-colors focus:outline-none focus:ring-2 focus:ring-studio-accent/50 ${
            disabled
              ? 'cursor-not-allowed border-studio-border opacity-60'
              : 'border-studio-border hover:border-gray-600'
          }`}
          placeholder="输入你想讨论的话题，例如：AI 会取代人类创造力吗？"
        />
        <span
          className={`absolute bottom-3 right-3 text-xs ${
            isAtLimit
              ? 'text-red-400'
              : isNearLimit
                ? 'text-yellow-400'
                : 'text-gray-500'
          }`}
        >
          {remaining}
        </span>
      </div>
    </div>
  );
}
