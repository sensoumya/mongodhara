# Test Suite

This directory contains the comprehensive test suite for the MongoDB Management API Gateway.

## Running Tests

### All Tests

```bash
pytest
```

### Specific Test File

```bash
pytest tests/test_api_gateway.py
pytest tests/test_api_gateway_opaque.py
```

### Specific Test Class/Method

```bash
pytest tests/test_api_gateway.py::TestAPIGateway::test_enable_authz_configuration
```

### With Coverage

```bash
pytest --cov=app --cov-report=html
```

### Filter by Keywords

```bash
pytest -k "database"        # Run database-related tests
pytest -k "permission"      # Run permission-related tests
pytest -k "security"        # Run security-related tests
```

## Test Structure

- `test_api_gateway.py`: Comprehensive API endpoint tests (opaque IDs disabled)
- `test_api_gateway_opaque.py`: API endpoint tests with opaque ID encryption enabled
- `conftest.py`: Shared test fixtures and configuration

## Test Categories

- **Authentication & Authorization**: RBAC security testing
- **Database Management**: CRUD operations on databases
- **Collection Management**: Collection operations
- **Document Management**: CRUD + import/export
- **GridFS**: File storage operations
- **Index Management**: Database indexes
- **Permission Management**: User permission administration
- **Opaque ID Security**: Encryption/decryption validation and error handling
- **Security**: Input validation, injection prevention
- **Integration**: End-to-end workflows

## Configuration

Test configuration is defined in `pytest.ini` with:

- Coverage reporting (80% minimum)
- Automatic test discovery
- HTML coverage reports
- Custom markers for test categorization
