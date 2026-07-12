import { ProductDetail } from "@/components/products/ProductDetail";

export default async function ProductDetailPage({ params }) {
  const { id } = await params;
  return <ProductDetail id={id} />;
}
