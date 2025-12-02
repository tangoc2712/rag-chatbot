# Database Schema: shopspot

## Table: _prisma_migrations

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | character varying | NO |  |
| checksum | character varying | NO |  |
| finished_at | timestamp with time zone | YES |  |
| migration_name | character varying | NO |  |
| logs | text | YES |  |
| rolled_back_at | timestamp with time zone | YES |  |
| started_at | timestamp with time zone | NO | now() |
| applied_steps_count | integer | NO | 0 |

### Constraints

| Column | Type | References |
|---|---|---|
| id | PRIMARY KEY |  |

## Table: coupons

| Column | Type | Nullable | Default |
|---|---|---|---|
| id | uuid | NO |  |
| code | text | NO |  |
| amount | numeric | NO |  |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| updated_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |

### Constraints

| Column | Type | References |
|---|---|---|
| id | PRIMARY KEY |  |

## Table: order_items

| Column | Type | Nullable | Default |
|---|---|---|---|
| order_item_id | uuid | NO |  |
| order_id | uuid | YES |  |
| product_id | uuid | YES |  |
| quantity | integer | YES |  |
| unit_price | numeric | YES |  |
| total_price | numeric | YES |  |

### Constraints

| Column | Type | References |
|---|---|---|
| order_item_id | PRIMARY KEY |  |
| order_id | FOREIGN KEY | orders(order_id) |
| product_id | FOREIGN KEY | products(product_id) |

## Table: orders

| Column | Type | Nullable | Default |
|---|---|---|---|
| order_id | uuid | NO |  |
| user_id | text | YES |  |
| status | text | YES |  |
| order_total | numeric | YES |  |
| currency | character | YES | 'USD'::bpchar |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| updated_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| shipping_info | jsonb | YES |  |
| subtotal | numeric | YES | 0 |
| tax | numeric | YES | 0 |
| shipping_charges | numeric | YES | 0 |
| discount | numeric | YES | 0 |

### Constraints

| Column | Type | References |
|---|---|---|
| order_id | PRIMARY KEY |  |
| user_id | FOREIGN KEY | users(uid) |

## Table: products

| Column | Type | Nullable | Default |
|---|---|---|---|
| product_id | uuid | NO |  |
| sku | text | YES |  |
| name | text | YES |  |
| description | text | YES |  |
| price | numeric | YES |  |
| currency | character | YES |  |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| updated_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| is_active | boolean | YES |  |
| sale_price | numeric | YES |  |
| category_id | integer | YES |  |
| product_url | character varying | YES |  |
| stock | integer | YES | 0 |
| photos | ARRAY | YES |  |
| colors | jsonb | YES | '[]'::jsonb |
| sizes | ARRAY | YES |  |
| materials | text | YES |  |
| care | text | YES |  |
| photo_public_id | text | YES |  |
| featured | boolean | YES | false |
| category_name | text | YES |  |

### Constraints

| Column | Type | References |
|---|---|---|
| product_id | PRIMARY KEY |  |

## Table: users

| Column | Type | Nullable | Default |
|---|---|---|---|
| user_id | uuid | NO |  |
| email | text | NO |  |
| password_hash | text | YES |  |
| full_name | text | YES |  |
| phone | text | YES |  |
| address | text | YES |  |
| created_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| updated_at | timestamp with time zone | YES | CURRENT_TIMESTAMP |
| is_active | boolean | YES |  |
| img_url | character varying | YES |  |
| role_id | integer | YES |  |
| date_of_birth | date | YES |  |
| job | text | YES |  |
| gender | text | YES |  |
| uid | text | YES |  |
| photo_url | text | YES |  |
| provider | text | YES |  |
| role | text | YES | 'user'::text |

### Constraints

| Column | Type | References |
|---|---|---|
| user_id | PRIMARY KEY |  |

