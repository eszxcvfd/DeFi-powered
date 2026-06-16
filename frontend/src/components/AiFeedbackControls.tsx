import { useState } from "react";
import { Button } from "@/components/ui/button";
import { AI_FEEDBACK_REASONS, type ViewerFeedback } from "@/types/aiFeedback";

type CopilotProps = {
  mode: "copilot";
  current: ViewerFeedback | null | undefined;
  busy?: boolean;
  onSubmit: (payload: { state: string; reason_code?: string; note?: string }) => Promise<void>;
};

type AudienceProps = {
  mode: "audience";
  current: ViewerFeedback | null | undefined;
  busy?: boolean;
  onSubmit: (payload: { state: string; reason_code?: string; note?: string }) => Promise<void>;
};

export function AiFeedbackControls(props: CopilotProps | AudienceProps) {
  const { current, busy, onSubmit, mode } = props;
  const [pendingNegative, setPendingNegative] = useState<string | null>(null);
  const [reason, setReason] = useState("weak_usefulness");
  const [note, setNote] = useState("");

  const needsReason = (state: string) => {
    if (mode === "copilot") return state === "not_helpful";
    return state === "incorrect" || state === "uncertain";
  };

  const submit = async (state: string) => {
    if (needsReason(state)) {
      setPendingNegative(state);
      return;
    }
    await onSubmit({ state });
    setPendingNegative(null);
    setNote("");
  };

  const confirmReason = async () => {
    if (!pendingNegative) return;
    await onSubmit({
      state: pendingNegative,
      reason_code: reason,
      note: note.trim() || undefined,
    });
    setPendingNegative(null);
    setNote("");
  };

  return (
    <div className="mt-3 border-t border-slate-100 pt-3" data-testid="ai-feedback-controls">
      <p className="text-[11px] text-slate-500 mb-2" data-testid="ai-feedback-disclaimer">
        Feedback is saved for later review. It does not change scores, prompts, or this AI output.
      </p>
      {current?.state && (
        <p className="text-xs text-slate-600 mb-2" data-testid="ai-feedback-current">
          Your feedback: <span className="font-mono">{current.state}</span>
          {current.reason_code ? ` · ${current.reason_code}` : ""}
        </p>
      )}
      {mode === "copilot" ? (
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="border border-slate-200"
            data-testid="copilot-feedback-helpful"
            disabled={busy}
            onClick={() => void submit("helpful")}
          >
            Helpful
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="border border-slate-200"
            data-testid="copilot-feedback-not-helpful"
            disabled={busy}
            onClick={() => void submit("not_helpful")}
          >
            Not helpful
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="border border-slate-200"
            data-testid="audience-feedback-correct"
            disabled={busy}
            onClick={() => void submit("correct")}
          >
            Correct
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="border border-slate-200"
            data-testid="audience-feedback-incorrect"
            disabled={busy}
            onClick={() => void submit("incorrect")}
          >
            Incorrect
          </Button>
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="border border-slate-200"
            data-testid="audience-feedback-uncertain"
            disabled={busy}
            onClick={() => void submit("uncertain")}
          >
            Uncertain
          </Button>
        </div>
      )}
      {pendingNegative && (
        <div className="mt-2 p-2 bg-slate-50 rounded-md text-xs space-y-2" data-testid="ai-feedback-reason-form">
          <label className="block">
            Reason
            <select
              className="mt-1 w-full border border-slate-200 rounded p-1"
              data-testid="ai-feedback-reason-select"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            >
              {AI_FEEDBACK_REASONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            Note (optional)
            <input
              className="mt-1 w-full border border-slate-200 rounded p-1"
              data-testid="ai-feedback-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </label>
          <div className="flex gap-2">
            <Button type="button" size="sm" data-testid="ai-feedback-reason-submit" disabled={busy} onClick={() => void confirmReason()}>
              Save feedback
            </Button>
            <Button type="button" size="sm" variant="ghost" disabled={busy} onClick={() => setPendingNegative(null)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}