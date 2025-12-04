# Order Card JSON Format

## Overview
The chatbot returns order information as structured JSON objects for better UI integration. Each order is formatted as a single-line JSON object, similar to product cards.

## Format Specification

```json
{"type":"order","order_id":"7e804fe7-2628-4a91-8188-ab6c598b8c30","status":"Delivered","total":161.64,"currency":"USD","placed_date":"2025-10-15","url":"https://hackathon-478514.web.app/order/7e804fe7-2628-4a91-8188-ab6c598b8c30","items_count":2,"item_names":["Kids Athletic Shorts","Kids Sport Hat"]}
```

## Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `type` | string | Always "order" | `"order"` |
| `order_id` | string | Unique order identifier (UUID) | `"7e804fe7-2628-4a91-8188-ab6c598b8c30"` |
| `status` | string | Current order status | `"Delivered"`, `"Shipped"`, `"Processing"`, `"Cancelled"` |
| `total` | number | Total order amount | `161.64` |
| `currency` | string | Currency code | `"USD"` |
| `placed_date` | string | Order placement date (YYYY-MM-DD) | `"2025-10-15"` |
| `url` | string | Order details page URL | `"https://hackathon-478514.web.app/order/{order_id}"` |
| `items_count` | number | Number of items in order | `2` |
| `item_names` | array | List of product names in the order | `["Product 1","Product 2"]` |

## Example Response

```
Here are your recent orders:

{"type":"order","order_id":"7e804fe7-2628-4a91-8188-ab6c598b8c30","status":"Delivered","total":161.64,"currency":"USD","placed_date":"2025-10-15","url":"https://hackathon-478514.web.app/order/7e804fe7-2628-4a91-8188-ab6c598b8c30","items_count":2,"item_names":["Kids Athletic Shorts","Kids Sport Hat"]}
{"type":"order","order_id":"a1b2c3d4-5678-90ef-ghij-klmnopqrstuv","status":"Shipped","total":299.99,"currency":"USD","placed_date":"2025-11-20","url":"https://hackathon-478514.web.app/order/a1b2c3d4-5678-90ef-ghij-klmnopqrstuv","items_count":1,"item_names":["Sony WH-1000XM5 Headphones"]}

Need help with any specific order?
```

## Frontend Parsing

### JavaScript Example
```javascript
function parseOrderCards(response) {
  const lines = response.split('\n');
  const orders = [];
  
  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('{"type":"order"')) {
      try {
        const order = JSON.parse(trimmed);
        orders.push(order);
      } catch (e) {
        console.error('Failed to parse order JSON:', e);
      }
    }
  }
  
  return orders;
}

// Usage
const chatResponse = "Here are your orders...\n{\"type\":\"order\",...}\n{\"type\":\"order\",...}";
const orders = parseOrderCards(chatResponse);
```

### React Component Example
```jsx
function OrderCard({ order }) {
  const getStatusColor = (status) => {
    const statusColors = {
      'Delivered': 'green',
      'Shipped': 'blue',
      'Processing': 'orange',
      'Cancelled': 'red'
    };
    return statusColors[status] || 'gray';
  };

  return (
    <div className="order-card">
      <div className="order-header">
        <span className="order-id">Order #{order.order_id.slice(0, 8)}</span>
        <span 
          className="order-status" 
          style={{ color: getStatusColor(order.status) }}
        >
          {order.status}
        </span>
      </div>
      
      <div className="order-info">
        <p className="order-date">Placed on {order.placed_date}</p>
        <p className="order-total">
          Total: {order.currency} {order.total.toFixed(2)}
        </p>
      </div>
      
      <div className="order-items">
        <p className="items-count">{order.items_count} item(s):</p>
        <ul>
          {order.item_names.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ul>
      </div>
      
      <a href={order.url} className="view-order">View Order Details</a>
    </div>
  );
}
```

### Parse Mixed Response (Products + Orders)
```javascript
function parseCards(response) {
  const lines = response.split('\n');
  const cards = {
    products: [],
    orders: []
  };
  
  for (const line of lines) {
    const trimmed = line.trim();
    
    if (trimmed.startsWith('{"type":"product"')) {
      try {
        cards.products.push(JSON.parse(trimmed));
      } catch (e) {
        console.error('Failed to parse product JSON:', e);
      }
    } else if (trimmed.startsWith('{"type":"order"')) {
      try {
        cards.orders.push(JSON.parse(trimmed));
      } catch (e) {
        console.error('Failed to parse order JSON:', e);
      }
    }
  }
  
  return cards;
}
```

## Order Status Values

Common status values returned:
- **Delivered** - Order has been delivered to customer
- **Shipped** - Order is in transit
- **Processing** - Order is being prepared
- **Pending** - Order placed but not yet processed
- **Cancelled** - Order has been cancelled

## Notes

- Each order JSON is on its own line
- The response will include friendly text before/after order JSONs
- The `url` field always follows the pattern: `https://hackathon-478514.web.app/order/{order_id}`
- Orders are user-specific - customers only see their own orders
- `item_names` provides a quick preview of what's in the order
- For full order details (shipping, payment, etc.), users should click the order URL

## Database Fields Used

The following fields are queried from the `order` table:
- `order_id` (UUID)
- `status`
- `order_total`
- `currency`
- `created_at` (formatted as placed_date)
- Items are joined from `order_item` table to get product names

## Related Documentation

- See [PRODUCT_CARD_FORMAT.md](./PRODUCT_CARD_FORMAT.md) for product card formatting
- See [API_GUIDE.md](./API_GUIDE.md) for complete API documentation
