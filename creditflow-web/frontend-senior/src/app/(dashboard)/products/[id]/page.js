import { ProductDetailPage } from "@/views/product-detail/ui/ProductDetailPage";

export default async function Page({ params }) {
  const { id } = await params;
  return <ProductDetailPage id={id} />;
}
