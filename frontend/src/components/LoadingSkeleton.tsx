interface LoadingSkeletonProps {
  variant: 'card' | 'text' | 'avatar' | 'speech';
  count?: number;
}

function CardSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border border-studio-border bg-studio-card p-5">
      <div className="mb-3 h-6 w-3/4 rounded bg-studio-border" />
      <div className="mb-2 h-4 w-full rounded bg-studio-border" />
      <div className="mb-4 h-4 w-2/3 rounded bg-studio-border" />
      <div className="flex items-center justify-between">
        <div className="h-4 w-16 rounded bg-studio-border" />
        <div className="h-6 w-14 rounded-full bg-studio-border" />
      </div>
    </div>
  );
}

function TextSkeleton() {
  return (
    <div className="animate-pulse space-y-3">
      <div className="h-4 w-full rounded bg-studio-border" />
      <div className="h-4 w-5/6 rounded bg-studio-border" />
      <div className="h-4 w-2/3 rounded bg-studio-border" />
    </div>
  );
}

function AvatarSkeleton() {
  return (
    <div className="animate-pulse flex items-center gap-3">
      <div className="h-12 w-12 rounded-full bg-studio-border" />
      <div className="flex-1 space-y-2">
        <div className="h-4 w-24 rounded bg-studio-border" />
        <div className="h-3 w-32 rounded bg-studio-border" />
      </div>
    </div>
  );
}

function SpeechSkeleton() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="flex justify-start">
        <div className="w-3/4 rounded-xl bg-studio-card p-4">
          <div className="mb-2 h-3 w-20 rounded bg-studio-border" />
          <div className="space-y-2">
            <div className="h-3 w-full rounded bg-studio-border" />
            <div className="h-3 w-5/6 rounded bg-studio-border" />
            <div className="h-3 w-2/3 rounded bg-studio-border" />
          </div>
        </div>
      </div>
      <div className="flex justify-end">
        <div className="w-2/3 rounded-xl bg-studio-card p-4">
          <div className="mb-2 h-3 w-20 rounded bg-studio-border" />
          <div className="space-y-2">
            <div className="h-3 w-full rounded bg-studio-border" />
            <div className="h-3 w-3/4 rounded bg-studio-border" />
          </div>
        </div>
      </div>
    </div>
  );
}

const variants = {
  card: CardSkeleton,
  text: TextSkeleton,
  avatar: AvatarSkeleton,
  speech: SpeechSkeleton,
};

export default function LoadingSkeleton({
  variant,
  count = 1,
}: LoadingSkeletonProps) {
  const Component = variants[variant];

  return (
    <>
      {Array.from({ length: count }, (_, i) => (
        <Component key={i} />
      ))}
    </>
  );
}
