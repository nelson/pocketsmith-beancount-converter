import pytest
from unittest.mock import Mock
from src.pocketsmith.common import PocketSmithClient

@pytest.fixture
def mock_client():
    """Provide a PocketSmithClient mock."""
    return Mock(spec=PocketSmithClient)

@pytest.fixture
def patch_get_user(monkeypatch):
    """Patch get_user in a given pocketsmith module.

    Returns the mocked get_user function so tests can configure
    return values or assertions.
    """
    def _patch(module: str, user_id: int = 123):
        path = f"src.pocketsmith.{module}.get_user"
        mock = Mock(return_value={"id": user_id})
        monkeypatch.setattr(path, mock)
        return mock
    return _patch

@pytest.fixture
def patch_client_class(monkeypatch, mock_client):
    """Patch PocketSmithClient constructor in a module to return mock_client."""
    def _patch(module: str):
        path = f"src.pocketsmith.{module}.PocketSmithClient"
        mock_cls = Mock(return_value=mock_client)
        monkeypatch.setattr(path, mock_cls)
        return mock_cls
    return _patch
