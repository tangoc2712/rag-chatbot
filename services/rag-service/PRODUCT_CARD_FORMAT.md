# Product Card JSON Format

## Overview
The chatbot now returns product recommendations as structured JSON objects for better UI integration. Each product is formatted as a single-line JSON object.

## Format Specification

```json
{"type":"product","name":"Product Name","price":29.99,"sale_price":19.99,"image":"https://...","url":"https://...","stock":50,"colors":["Blue","White"],"sizes":["S","M","L","XL"]}
```

## Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `type` | string | Always "product" | `"product"` |
| `name` | string | Product name | `"DRY-EX T-Shirt"` |
| `price` | number | Original price | `56.00` |
| `sale_price` | number/null | Sale price (null if no sale) | `37.60` or `null` |
| `image` | string | First photo URL from photos array | `"https://image.uniqlo.com/..."` |
| `url` | string | Product page URL | `"https://hackathon-478514.web.app/product/xxx"` |
| `stock` | number | Available stock quantity | `226` |
| `colors` | array | Available color options | `["Blue","White"]` or `[]` |
| `sizes` | array | Available size options | `["S","M","L","XL"]` |

## Example Response

```
Here are some great options for you:

{"type":"product","name":"DRY-EX T-Shirt","price":56.00,"sale_price":null,"image":"https://image.uniqlo.com/UQ/ST3/us/imagesgoods/476141/item/usgoods_69_476141_3x4.jpg","url":"https://hackathon-478514.web.app/product/f2ceb5bc-e129-474d-8322-0bbdc6f187db","stock":226,"colors":[],"sizes":["S","M","L","XL"]}
{"type":"product","name":"Men's Formal Shirt","price":47.00,"sale_price":37.60,"image":"https://example.com/shirt.jpg","url":"https://hackathon-478514.web.app/product/08c4d433-20d3-4f80-b2bf-e598b97c70e3","stock":15,"colors":["Blue","White"],"sizes":["M","L"]}

Would you like to see more from a specific category?
```

## Frontend Parsing

### JavaScript Example
```javascript
function parseProductCards(response) {
  const lines = response.split('\n');
  const products = [];
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('{"type":"product"')) {
      try {
        const product = JSON.parse(trimmed);
        products.push(product);
      } catch (e) {
        console.error('Failed to parse product JSON:', e);
      }
    }
  }
  
  return products;
}

// Usage
const chatResponse = "Here are some...\n{\"type\":\"product\",...}\n{\"type\":\"product\",...}";
const products = parseProductCards(chatResponse);
```

### React Component Example
```jsx
function ProductCard({ product }) {
  return (
    <div className="product-card">
      <img src={product.image} alt={product.name} />
      <h3>{product.name}</h3>
      <div className="price">
        {product.sale_price ? (
          <>
            <span className="original-price">${product.price}</span>
            <span className="sale-price">${product.sale_price}</span>
          </>
        ) : (
          <span>${product.price}</span>
        )}
      </div>
      {product.stock < 10 && <div className="low-stock">Only {product.stock} left!</div>}
      {product.sizes.length > 0 && (
        <div className="sizes">Sizes: {product.sizes.join(', ')}</div>
      )}
      <a href={product.url} className="view-product">View Product</a>
    </div>
  );
}
```

## Notes

- Each product JSON is on its own line
- The response will include friendly text before/after product JSONs
- Products are extracted from the database with all available fields
- The `image` field uses the first item from the `photos` array
- Empty arrays for `colors` or `sizes` indicate no options stored
- `sale_price` is `null` when there's no active sale

## Database Fields Used

The following fields are queried from the `product` table:
- `product_id`
- `name`
- `description`
- `price`
- `sale_price`
- `stock`
- `category_name`
- `colors` (jsonb)
- `sizes` (array)
- `materials`
- `product_url`
- `photos` (array)
- `care`
- `featured`
