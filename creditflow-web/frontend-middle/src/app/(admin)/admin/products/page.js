"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import toast from "react-hot-toast";
import { useRequirePermission } from "@/hooks/useRequirePermission";
import { PERMISSIONS } from "@/lib/rbac/permissions";
import { useAdminProducts, useDeactivateAdminProduct } from "@/hooks/useAdminProducts";
import { ProductsTable } from "@/components/admin/ProductsTable";
import { Button } from "@/components/ui/Button";
import { DetailSkeleton } from "@/components/feedback/Skeleton";

const ProductFormModal = dynamic(() => import("@/components/admin/ProductFormModal"), {
  loading: () => <DetailSkeleton />,
  ssr: false,
});

export default function AdminProductsPage() {
  const allowed = useRequirePermission(PERMISSIONS.PRODUCT_MANAGE);
  const [page, setPage] = useState(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);

  const { data, isLoading, isError, refetch } = useAdminProducts({ page });
  const deactivateProduct = useDeactivateAdminProduct();

  if (!allowed) return <DetailSkeleton />;

  const openCreate = () => {
    setEditingProduct(null);
    setModalOpen(true);
  };

  const openEdit = (product) => {
    setEditingProduct(product);
    setModalOpen(true);
  };

  const onDeactivate = async (id) => {
    if (!window.confirm("Деактивировать продукт?")) return;
    try {
      await deactivateProduct.mutateAsync(id);
      toast.success("Продукт деактивирован");
    } catch {
      toast.error("Не удалось деактивировать продукт");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Кредитные продукты
        </h1>
        <Button onClick={openCreate}>Создать продукт</Button>
      </div>
      <ProductsTable
        data={data}
        isLoading={isLoading}
        isError={isError}
        onRetry={refetch}
        page={page}
        onPageChange={setPage}
        onEdit={openEdit}
        onDeactivate={onDeactivate}
        deactivatingId={deactivateProduct.isPending ? deactivateProduct.variables : null}
      />
      {modalOpen && (
        <ProductFormModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          product={editingProduct}
        />
      )}
    </div>
  );
}
