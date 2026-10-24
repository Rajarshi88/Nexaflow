# NexaFlow sample data

The primary dashboard data source is `backend/seed.py`, which populates `backend/nexaflow.db`. The seed script creates 29 products, 1,500 customers, 12 months of order history, six settings, two demo campaigns, and 12 demo WhatsApp messages.

The frontend includes a small matching fallback in `frontend/src/utils.ts` so pages still show useful records while the backend is offline. When the backend is running, the API response from the SQLite database takes priority.

- `inventory_sample.csv` mirrors real SKUs from `backend/seed.py` and can be selected in Inventory → Connect inventory.
- `customers_sample.csv` is a small audience-shaped CSV using the same fields shown by the customer API.
- `campaigns_sample.csv` mirrors the two campaigns added by `seed.py`.
- `seed_snapshot.json` is a readable snapshot of the current SQLite database counts and representative rows.

To reset the SQLite demo database, run `python seed.py` from the `backend` directory. This deletes existing demo rows and recreates them, so do not run it against production data.
