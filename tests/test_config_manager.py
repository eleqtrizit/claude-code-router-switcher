"""Tests for ConfigManager class."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_code_router_switcher.config_manager import ConfigManager


@pytest.fixture
def temp_config_file() -> Path:
    """
    Create a temporary config file for testing.

    :return: Path to temporary config file
    :rtype: Path
    """
    config_data = {
        "Router": {
            "default": "provider1,model1",
            "background": "provider2,model2",
        },
        "Providers": [
            {
                "name": "provider1",
                "api_base_url": "http://example.com",
                "api_key": "key1",
                "models": ["model1", "model2"],
            },
            {
                "name": "provider2",
                "api_base_url": "http://example2.com",
                "api_key": "key2",
                "models": ["model2", "model3"],
            },
        ],
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def empty_config_file() -> Path:
    """
    Create an empty config file for testing.

    :return: Path to temporary empty config file
    :rtype: Path
    """
    config_data = {}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def config_manager(temp_config_file: Path) -> ConfigManager:
    """
    Create a ConfigManager instance with a temporary config file.

    :param temp_config_file: Temporary config file path
    :type temp_config_file: Path
    :return: ConfigManager instance
    :rtype: ConfigManager
    """
    return ConfigManager(temp_config_file)


class TestConfigManagerInit:
    """Tests for ConfigManager.__init__."""

    def test_init_with_path(self, temp_config_file: Path) -> None:
        """Test initialization with explicit config path."""
        manager = ConfigManager(temp_config_file)
        assert manager.config_path == temp_config_file

    def test_init_without_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization without config path uses current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            manager = ConfigManager()
            expected_path = Path(tmpdir) / "config.json"
            assert manager.config_path.resolve() == expected_path.resolve()

    def test_init_with_none_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test initialization with None path uses current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monkeypatch.chdir(tmpdir)
            manager = ConfigManager(None)
            expected_path = Path(tmpdir) / "config.json"
            assert manager.config_path.resolve() == expected_path.resolve()


class TestConfigManagerLoadConfig:
    """Tests for ConfigManager.load_config."""

    def test_load_config_success(self, config_manager: ConfigManager) -> None:
        """Test loading config from existing file."""
        config = config_manager.load_config()
        assert isinstance(config, dict)
        assert "Router" in config
        assert "Providers" in config

    def test_load_config_file_not_found(self) -> None:
        """Test loading config from non-existent file raises FileNotFoundError."""
        non_existent = Path("/nonexistent/path/config.json")
        manager = ConfigManager(non_existent)
        with pytest.raises(FileNotFoundError):
            manager.load_config()

    def test_load_config_invalid_json(self) -> None:
        """Test loading invalid JSON raises JSONDecodeError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            temp_path = Path(f.name)
        try:
            manager = ConfigManager(temp_path)
            with pytest.raises(json.JSONDecodeError):
                manager.load_config()
        finally:
            temp_path.unlink(missing_ok=True)


class TestConfigManagerSaveConfig:
    """Tests for ConfigManager.save_config."""

    def test_save_config_success(self, config_manager: ConfigManager) -> None:
        """Test saving config to file."""
        new_config = {"test": "value", "Router": {"default": "test"}}
        config_manager.save_config(new_config)
        loaded = config_manager.load_config()
        assert loaded == new_config

    def test_save_config_creates_directory(self, tmp_path: Path) -> None:
        """Test saving config creates parent directory if it doesn't exist."""
        config_path = tmp_path / "nested" / "dir" / "config.json"
        manager = ConfigManager(config_path)
        config = {"test": "value"}
        manager.save_config(config)
        assert config_path.exists()
        loaded = manager.load_config()
        assert loaded == config


class TestConfigManagerGetRouterConfig:
    """Tests for ConfigManager.get_router_config."""

    def test_get_router_config_success(self, config_manager: ConfigManager) -> None:
        """Test getting router config."""
        router_config = config_manager.get_router_config()
        assert router_config == {"default": "provider1,model1", "background": "provider2,model2"}

    def test_get_router_config_empty(self, empty_config_file: Path) -> None:
        """Test getting router config when Router section doesn't exist."""
        manager = ConfigManager(empty_config_file)
        router_config = manager.get_router_config()
        assert router_config == {}


class TestConfigManagerUpdateRouterConfig:
    """Tests for ConfigManager.update_router_config."""

    def test_update_router_config_success(self, config_manager: ConfigManager) -> None:
        """Test updating router config."""
        new_router_config = {"default": "new_provider,new_model"}
        config_manager.update_router_config(new_router_config)
        loaded = config_manager.get_router_config()
        assert loaded == new_router_config

    def test_update_router_config_preserves_other_sections(
        self, config_manager: ConfigManager
    ) -> None:
        """Test updating router config preserves other config sections."""
        original_config = config_manager.load_config()
        new_router_config = {"default": "new_provider,new_model"}
        config_manager.update_router_config(new_router_config)
        updated_config = config_manager.load_config()
        assert updated_config["Router"] == new_router_config
        assert "Providers" in updated_config
        assert updated_config["Providers"] == original_config["Providers"]


class TestConfigManagerGetProviders:
    """Tests for ConfigManager.get_providers."""

    def test_get_providers_success(self, config_manager: ConfigManager) -> None:
        """Test getting providers list."""
        providers = config_manager.get_providers()
        assert len(providers) == 2
        assert providers[0]["name"] == "provider1"
        assert providers[1]["name"] == "provider2"

    def test_get_providers_empty(self, empty_config_file: Path) -> None:
        """Test getting providers when Providers section doesn't exist."""
        manager = ConfigManager(empty_config_file)
        providers = manager.get_providers()
        assert providers == []


class TestConfigManagerAddProvider:
    """Tests for ConfigManager.add_provider."""

    def test_add_provider_success(self, config_manager: ConfigManager) -> None:
        """Test adding a new provider."""
        new_provider = {
            "name": "provider3",
            "api_base_url": "http://example3.com",
            "api_key": "key3",
            "models": ["model4"],
        }
        config_manager.add_provider(new_provider)
        providers = config_manager.get_providers()
        assert len(providers) == 3
        assert providers[2] == new_provider

    def test_add_provider_without_api_key(self, config_manager: ConfigManager) -> None:
        """Test adding a new provider without an API key."""
        new_provider = {
            "name": "provider3",
            "api_base_url": "http://example3.com",
            "models": ["model4"],
        }
        config_manager.add_provider(new_provider)
        providers = config_manager.get_providers()
        assert len(providers) == 3
        assert providers[2] == new_provider
        # Check that the provider doesn't have an api_key field
        assert "api_key" not in providers[2]

    def test_add_provider_to_empty_config(self, empty_config_file: Path) -> None:
        """Test adding provider to empty config."""
        manager = ConfigManager(empty_config_file)
        new_provider = {
            "name": "provider1",
            "api_base_url": "http://example.com",
            "api_key": "key1",
            "models": [],
        }
        manager.add_provider(new_provider)
        providers = manager.get_providers()
        assert len(providers) == 1
        assert providers[0] == new_provider

    def test_add_provider_duplicate_name(self, config_manager: ConfigManager) -> None:
        """Test adding provider with duplicate name raises ValueError."""
        new_provider = {
            "name": "provider1",  # Same name as existing provider
            "api_base_url": "http://different.com",
            "models": [],
        }
        with pytest.raises(ValueError, match="Provider with name 'provider1' already exists"):
            config_manager.add_provider(new_provider)

    def test_add_provider_duplicate_base_url(self, config_manager: ConfigManager) -> None:
        """Test adding provider with duplicate base URL raises ValueError."""
        new_provider = {
            "name": "different_provider",
            "api_base_url": "http://example.com",  # Same base URL as existing provider1
            "models": [],
        }
        with pytest.raises(ValueError, match="Provider with base URL 'http://example.com' already exists"):
            config_manager.add_provider(new_provider)


class TestConfigManagerAddModelToProvider:
    """Tests for ConfigManager.add_model_to_provider."""

    def test_add_model_to_provider_success(self, config_manager: ConfigManager) -> None:
        """Test adding a model to an existing provider."""
        config_manager.add_model_to_provider("provider1", "model3")
        providers = config_manager.get_providers()
        provider1 = next(p for p in providers if p["name"] == "provider1")
        assert "model3" in provider1["models"]

    def test_add_model_to_provider_duplicate(self, temp_config_file: Path) -> None:
        """Test adding duplicate model doesn't create duplicates."""
        config_manager = ConfigManager(temp_config_file)

        # Verify provider exists and model is already present
        providers_before = config_manager.get_providers()
        provider1_before = next((p for p in providers_before if p["name"] == "provider1"), None)
        assert provider1_before is not None
        assert "model1" in provider1_before["models"]
        initial_count = provider1_before["models"].count("model1")

        # Verify config file is valid before operation
        config_before = config_manager.load_config()
        assert "Providers" in config_before
        assert any(p.get("name") == "provider1" for p in config_before["Providers"])

        # Adding duplicate should not raise error
        # The function should return early when model already exists
        config_manager.add_model_to_provider("provider1", "model1")

        # Verify count hasn't changed
        providers_after = config_manager.get_providers()
        provider1_after = next((p for p in providers_after if p["name"] == "provider1"), None)
        assert provider1_after is not None
        assert provider1_after["models"].count("model1") == initial_count

    def test_add_model_to_provider_not_found(self, config_manager: ConfigManager) -> None:
        """Test adding model to non-existent provider raises ValueError."""
        with pytest.raises(ValueError, match="Provider 'nonexistent' not found"):
            config_manager.add_model_to_provider("nonexistent", "model1")


class TestConfigManagerGetAllModels:
    """Tests for ConfigManager.get_all_models."""

    def test_get_all_models_success(self, config_manager: ConfigManager) -> None:
        """Test getting all models grouped by provider."""
        models_by_provider = config_manager.get_all_models()
        assert "provider1" in models_by_provider
        assert "provider2" in models_by_provider
        assert models_by_provider["provider1"] == ["model1", "model2"]
        assert models_by_provider["provider2"] == ["model2", "model3"]

    def test_get_all_models_empty(self, empty_config_file: Path) -> None:
        """Test getting all models from empty config."""
        manager = ConfigManager(empty_config_file)
        models_by_provider = manager.get_all_models()
        assert models_by_provider == {}


class TestConfigManagerFindProvidersForModel:
    """Tests for ConfigManager.find_providers_for_model."""

    def test_find_providers_for_model_single_match(self, config_manager: ConfigManager) -> None:
        """Test finding providers for model with single match."""
        providers = config_manager.find_providers_for_model("model1")
        assert providers == ["provider1"]

    def test_find_providers_for_model_multiple_matches(
        self, config_manager: ConfigManager
    ) -> None:
        """Test finding providers for model with multiple matches."""
        providers = config_manager.find_providers_for_model("model2")
        assert set(providers) == {"provider1", "provider2"}

    def test_find_providers_for_model_not_found(self, config_manager: ConfigManager) -> None:
        """Test finding providers for non-existent model."""
        providers = config_manager.find_providers_for_model("nonexistent")
        assert providers == []


class TestConfigManagerValidateProviderModel:
    """Tests for ConfigManager.validate_provider_model."""

    def test_validate_provider_model_valid(self, config_manager: ConfigManager) -> None:
        """Test validating valid provider-model combination."""
        assert config_manager.validate_provider_model("provider1", "model1") is True

    def test_validate_provider_model_invalid_provider(
        self, config_manager: ConfigManager
    ) -> None:
        """Test validating with non-existent provider."""
        assert config_manager.validate_provider_model("nonexistent", "model1") is False

    def test_validate_provider_model_invalid_model(self, config_manager: ConfigManager) -> None:
        """Test validating with non-existent model."""
        assert config_manager.validate_provider_model("provider1", "nonexistent") is False


class TestConfigManagerDeleteProvider:
    """Tests for ConfigManager.delete_provider."""

    def test_delete_provider_success(self, config_manager: ConfigManager) -> None:
        """Test deleting an existing provider."""
        config_manager.delete_provider("provider1")
        providers = config_manager.get_providers()
        assert len(providers) == 1
        assert providers[0]["name"] == "provider2"

    def test_delete_provider_not_found(self, config_manager: ConfigManager) -> None:
        """Test deleting non-existent provider raises ValueError."""
        with pytest.raises(ValueError, match="Provider 'nonexistent' not found"):
            config_manager.delete_provider("nonexistent")


class TestConfigManagerDeleteModel:
    """Tests for ConfigManager.delete_model."""

    def test_delete_model_success(self, config_manager: ConfigManager) -> None:
        """Test deleting a model from all providers."""
        config_manager.delete_model("model2")
        models_by_provider = config_manager.get_all_models()
        assert "model2" not in models_by_provider["provider1"]
        assert "model2" not in models_by_provider["provider2"]

    def test_delete_model_not_found(self, config_manager: ConfigManager) -> None:
        """Test deleting non-existent model raises ValueError."""
        with pytest.raises(ValueError, match="Model 'nonexistent' not found"):
            config_manager.delete_model("nonexistent")


class TestConfigManagerValidateProviderEndpoint:
    """Tests for ConfigManager.validate_provider_endpoint."""

    @patch("requests.get")
    def test_validate_provider_endpoint_with_v1_success(self, mock_get: MagicMock) -> None:
        """Test validation when /v1/models endpoint responds successfully."""
        # Mock successful response for /v1/models
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        config_manager = ConfigManager(Path("/tmp/test.json"))  # Dummy path
        result = config_manager.validate_provider_endpoint("http://example.com")

        assert result == "http://example.com/v1"
        mock_get.assert_called_once_with("http://example.com/v1/models", timeout=10)

    @patch("requests.get")
    def test_validate_provider_endpoint_without_v1_success(self, mock_get: MagicMock) -> None:
        """Test validation when /v1/models fails but /models succeeds."""
        # Mock failure for /v1/models (404)
        mock_v1_response = MagicMock()
        mock_v1_response.status_code = 404

        # Mock success for /models (200)
        mock_models_response = MagicMock()
        mock_models_response.status_code = 200

        # Configure mock to return different responses based on URL
        def side_effect(url, timeout=10):
            if url == "http://example.com/v1/models":
                return mock_v1_response
            elif url == "http://example.com/models":
                return mock_models_response
            else:
                raise ValueError("Unexpected URL")

        mock_get.side_effect = side_effect

        config_manager = ConfigManager(Path("/tmp/test.json"))  # Dummy path
        result = config_manager.validate_provider_endpoint("http://example.com")

        assert result == "http://example.com"
        assert mock_get.call_count == 2
        mock_get.assert_any_call("http://example.com/v1/models", timeout=10)
        mock_get.assert_any_call("http://example.com/models", timeout=10)

    @patch("requests.get")
    def test_validate_provider_endpoint_both_fail(self, mock_get: MagicMock) -> None:
        """Test validation when both endpoints fail."""
        # Mock exceptions for both endpoints
        from requests import RequestException
        mock_get.side_effect = RequestException("Network error")

        config_manager = ConfigManager(Path("/tmp/test.json"))  # Dummy path
        result = config_manager.validate_provider_endpoint("http://example.com")

        assert result == "http://example.com"  # Should return original URL
        assert mock_get.call_count == 2

    @patch("requests.get")
    def test_validate_provider_endpoint_with_trailing_slash(self, mock_get: MagicMock) -> None:
        """Test validation handles trailing slashes correctly."""
        # Mock successful response for /v1/models
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        config_manager = ConfigManager(Path("/tmp/test.json"))  # Dummy path
        result = config_manager.validate_provider_endpoint("http://example.com/")

        assert result == "http://example.com/v1"
        mock_get.assert_called_once_with("http://example.com/v1/models", timeout=10)
