"use client";

import { useState } from "react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { useApproveApplication, useRejectApplication } from "@/hooks/useAdminApplications";

export default function ApplicationDecisionModal({ open, onClose, applicationId, mode }) {
  const [text, setText] = useState("");
  const isApprove = mode === "approve";
  const approve = useApproveApplication(applicationId);
  const reject = useRejectApplication(applicationId);
  const mutation = isApprove ? approve : reject;

  const onConfirm = async () => {
    try {
      await mutation.mutateAsync(isApprove ? { comment: text } : { reason: text });
      toast.success(isApprove ? "Заявка одобрена" : "Заявка отклонена");
      setText("");
      onClose();
    } catch (e) {
      toast.error(e.response?.data?.error?.message || "Действие недоступно в этом статусе");
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={isApprove ? "Одобрить заявку" : "Отклонить заявку"}>
      <div className="space-y-4">
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {isApprove ? "Комментарий (необязательно)" : "Причина (необязательно)"}
          </span>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={3}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          />
        </label>
        <div className="flex justify-end gap-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button
            type="button"
            variant={isApprove ? "primary" : "danger"}
            disabled={mutation.isPending}
            onClick={onConfirm}
          >
            {isApprove ? "Одобрить" : "Отклонить"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
