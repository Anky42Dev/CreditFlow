export function Loader({ fullscreen = false }) {
  const spinner = (
    <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
  );

  if (!fullscreen) return spinner;

  return (
    <div className="flex min-h-screen items-center justify-center">
      {spinner}
    </div>
  );
}
