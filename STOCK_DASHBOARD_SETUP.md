# Stock Operations Dashboard

The new page is available in the main sidebar as **📦 Stock Operations**.

## Current Excel mode

The included snapshot is read from:

`data/BranchStockReport.xlsx`

Replace that file with a new export using the same column names, then use the
existing **Refresh Data** button in the sidebar.

## Stored-procedure mode

Add this section to `.streamlit/secrets.toml` or Streamlit Cloud Secrets:

```toml
[stock_dashboard]
source = "stored_procedure"
procedure = "dbo.YourStockProcedure"
use_date_parameters = false
```

If the procedure accepts `@StartDate` and `@EndDate`, set:

```toml
use_date_parameters = true
```

The procedure output should contain the same business columns as the Excel
report. At minimum, it must return `Branch`, `Stock Type`, and `GR #`.

## Stock-type definitions

The dashboard currently uses the exact report values:

- `BOOKING STOCK`
- `IN-TRANSIT STOCK`
- `TRANSIT STOCK`
- `DELIVERY STOCK`

No separate **Hub Stock** is inferred. Once its operational rule is confirmed,
add it as a derived field in `services/stock_data_loader.py` and use that field
in the dashboard.

## Files added or updated

- `pages/Home/Stock_Operations.py`
- `services/stock_data_loader.py`
- `data/BranchStockReport.xlsx`
- `app.py`
- `config/role_permissions.json`
