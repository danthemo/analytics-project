import type { Product } from "../types/domain";
import { ProductCard } from "./ProductCard";


type ProductListProps = {
  products: Product[];
};


export function ProductList({ products }: ProductListProps) {
  return (
    <div className="product-grid">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
