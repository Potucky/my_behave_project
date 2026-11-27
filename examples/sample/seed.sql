-- Fictional fixture data from qa_data_factory.
-- Local test fixtures only.
-- seed=42

INSERT INTO customers (customer_id, first_name, last_name, email, phone, created_at, city, country, status) VALUES ('CUS-000001', 'Danielle', 'Johnson', 'danielle.johnson.1@example.com', '+12025550100', '2024-11-23', 'Johnberg', 'United States', 'inactive');
INSERT INTO customers (customer_id, first_name, last_name, email, phone, created_at, city, country, status) VALUES ('CUS-000002', 'Jill', 'Rhodes', 'jill.rhodes.2@example.com', '+12025550101', '2024-01-13', 'New Roberttown', 'United States', 'active');

INSERT INTO orders (order_id, customer_id, order_date, status, currency, subtotal, tax, total) VALUES ('ORD-000001', 'CUS-000002', '2024-01-28', 'paid', 'USD', '129.16', '10.33', '139.49');

INSERT INTO order_lines (line_id, order_id, sku, product_name, quantity, unit_price, line_total) VALUES ('LIN-000001', 'ORD-000001', 'SKU-TEE-001', 'Cotton Tee', 4, '19.99', '79.96');
INSERT INTO order_lines (line_id, order_id, sku, product_name, quantity, unit_price, line_total) VALUES ('LIN-000002', 'ORD-000001', 'SKU-BTL-001', 'Water Bottle', 3, '16.40', '49.20');

INSERT INTO payments (payment_id, order_id, amount, method, paid_at, status) VALUES ('PAY-000001', 'ORD-000001', '139.49', 'card', '2024-01-28T17:27:02Z', 'captured');

INSERT INTO invoices (invoice_id, order_id, invoice_number, issued_at, due_at, amount, status) VALUES ('INV-000001', 'ORD-000001', 'INV-20240128-000001', '2024-01-28', '2024-02-27', '139.49', 'paid');
