"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import toast from "react-hot-toast";
import { useRequirePermission } from "@/entities/user/lib/useRequirePermission";
import { PERMISSIONS } from "@/shared/config/permissions";
import { useAdminProducts, useDeactivateAdminProduct } from "@/entities/product/model/useAdminProducts";
import { ProductsTable } from "@/widgets/admin-products-table/ui/ProductsTable";
import { Button } from "@/shared/ui/Button";
import { DetailSkeleton } from "@/shared/ui/Skeleton";
import { WidgetErrorBoundary } from "@/shared/lib/ErrorBoundary";

const ProductFormModal = dynamic(() => import("@/widgets/admin-products-table/ui/ProductFormModal"), {
  loading: () => <DetailSkeleton />,
  ssr: false,
});

export function AdminProductsPage() {
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
      <WidgetErrorBoundary name="admin-products-table">
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
      </WidgetErrorBoundary>
      {modalOpen && (
        <WidgetErrorBoundary name="admin-product-form-modal">
          <ProductFormModal
            open={modalOpen}
            onClose={() => setModalOpen(false)}
            product={editingProduct}
          />
        </WidgetErrorBoundary>
      )}
    </div>
  );
}
