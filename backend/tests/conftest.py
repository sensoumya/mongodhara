import os

import pytest
from fastapi.testclient import TestClient

# Test configurations
TEST_CONFIGS = {
    "basic": {
        "ENABLE_AUTHZ": "false",
        "ENABLE_OPAQUE_IDS": "false",
        "BASE_PATH": "",
    },
    "authz": {
        "ENABLE_AUTHZ": "true",
        "ENABLE_OPAQUE_IDS": "false",
        "BASE_PATH": "",
    },
    "opaque": {
        "ENABLE_AUTHZ": "false",
        "ENABLE_OPAQUE_IDS": "true",
        "BASE_PATH": "",
        "OPAQUE_ID_ENCRYPTION_KEY": "+mr9wrbd1X34sKNHUyZZUg==",
    },
    "full": {
        "ENABLE_AUTHZ": "true",
        "ENABLE_OPAQUE_IDS": "true",
        "BASE_PATH": "",
        "OPAQUE_ID_ENCRYPTION_KEY": "+mr9wrbd1X34sKNHUyZZUg==",
    },
}


@pytest.fixture(params=list(TEST_CONFIGS.keys()))
def test_config(request):
    """Fixture that provides different test configurations"""
    return request.param


@pytest.fixture(scope="function")
def test_client(test_config):
    """Create test client with specific configuration"""
    # Set environment variables for this test
    original_env = {}
    for key in TEST_CONFIGS[test_config]:
        if key in os.environ:
            original_env[key] = os.environ[key]
        os.environ[key] = TEST_CONFIGS[test_config][key]

    # Clear any modules that might have cached the old config
    import sys
    modules_to_clear = [
        'app.core.config',
        'app.dependencies.auth',
        'app.services.opaque_id_service',
        'app.main',
        'app.services.database',
        'app.services.collection',
        'app.services.document',
        'app.services.index',
        'app.services.gridfs',
        'app.services.permission_service',
        'app.services.audit_service',
        'app.services.base',
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]

    # Import app after setting environment
    from app.main import app
    
    # Use raise_server_exceptions=False to prevent event loop issues
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    # Restore original environment
    for key, value in original_env.items():
        os.environ[key] = value
    for key in TEST_CONFIGS[test_config]:
        if key not in original_env:
            os.environ.pop(key, None)


@pytest.fixture(autouse=True)
def set_test_env():
    """Set up test environment variables"""
    # Ensure we have a clean test environment
    pass