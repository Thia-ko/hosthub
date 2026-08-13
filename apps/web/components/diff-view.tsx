import { diffLines, type Change } from "diff";

function DiffChangeLine({ change, index }: { change: Change; index: number }) {
  const prefix = change.added ? "+" : change.removed ? "-" : " ";
  const background = change.added ? "bg-emerald-50 text-emerald-900" : change.removed ? "bg-red-50 text-red-900" : "";
  const lines = change.value.endsWith("\n") ? change.value.slice(0, -1).split("\n") : change.value.split("\n");
  return (
    <>
      {lines.map((line, lineIndex) => (
        <div
          key={`${index}-${lineIndex}`}
          className={`whitespace-pre-wrap px-3 py-0.5 font-mono text-xs ${background}`}
        >
          {prefix} {line}
        </div>
      ))}
    </>
  );
}

export function DiffView({ from, to }: { from: string; to: string }) {
  const changes = diffLines(from, to);
  return (
    <div className="overflow-hidden rounded-md border">
      {changes.map((change, index) => (
        <DiffChangeLine key={index} change={change} index={index} />
      ))}
    </div>
  );
}
