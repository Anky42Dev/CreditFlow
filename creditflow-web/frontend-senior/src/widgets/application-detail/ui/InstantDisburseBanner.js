import { Zap } from "lucide-react";
import { useFlag } from "@/app/providers/FeatureFlagsProvider";

/**
 * DOC 6 §6 example usage: gradual rollout of instant disbursement, shown
 * only for approved-but-not-yet-disbursed applications and only while the
 * `instant_disbursement` flag is on for the current user (AC-6: flag off
 * => this UI stays hidden).
 */
export function InstantDisburseBanner({ status }) {
  const instantDisbursement = useFlag("instant_disbursement");

  if (!instantDisbursement || status !== "APPROVED") return null;

  return (
    <div className="flex items-start gap-3 rounded-lg border border-green-200 bg-green-50 p-3 text-sm dark:border-green-900/40 dark:bg-green-900/20">
      <Zap size={18} className="mt-0.5 shrink-0 text-green-600 dark:text-green-400" />
      <p className="text-green-800 dark:text-green-300">
        Заявка одобрена — деньги будут выданы мгновенно, без ожидания
        стандартной обработки.
      </p>
    </div>
  );
}
