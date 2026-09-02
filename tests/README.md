# Tests

Unit and integration tests for the MLSecOps platform. We use `pytest` for testing.

## Running Tests

From the project root:
```bash
pytest tests/
```

## Coverage

| File | Description |
|------|-------------|
| `test_data_quality.py` | Validates data quality checks and gate logic. |
| `test_ingestion.py` | Tests the data ingestion and download mechanisms. |
