"use client";

import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { useRepayLoan } from "@/hooks/useLoans";

export function RepayModal({ open, onClose, loanId, nextPayment }) {
  const [amount, setAmount] = useState("");
  const [fieldError, setFieldError] = useState("");
  const idemKeyRef = useRef(null);
  const repay = useRepayLoan(loanId);

  useEffect(() => {
    if (open) {
      idemKeyRef.current = crypto.randomUUID();
      setAmount(nextPayment ? String(nextPayment.amount) : "");
      setFieldError("");
    }
  }, [open, nextPayment]);

  const onConfirm = async () => {
    setFieldError("");
    try {
      await repay.mutateAsync({
        amount,
        idempotency_key: idemKeyRef.current,
      });
      toast.success("Платёж выполнен");
      onClose();
    } catch (e) {
      const status = e.response?.status;
      const code = e.response?.data?.error?.code;
      const details = e.response?.data?.error?.details;
      if (status === 409 && code === "DUPLICATE") {
        toast.error("Платёж уже обработан");
      } else if (details?.amount) {
        setFieldError(Array.isArray(details.amount) ? details.amount[0] : details.amount);
      } else {
        toast.error("Что-то пошло не так");
      }
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Внести платёж">
      <div className="space-y-4">
        <Input
          label="Сумма"
          type="number"
          step="0.01"
          min="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          error={fieldError}
        />
        <div className="flex justify-end gap-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button type="button" disabled={repay.isPending} onClick={onConfirm}>
            Подтвердить
          </Button>
        </div>
      </div>
    </Modal>
  );
}
