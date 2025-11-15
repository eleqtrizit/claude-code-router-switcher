"""Configuration manager for handling JSON config file operations."""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages configuration file operations."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize the config manager.

        :param config_path: Path to the config file. If None, defaults to config.json in current directory.
        :type config_path: Optional[Path]
        """
        if config_path is None:
            config_path = Path.cwd() / "config.json"
        self.config_path = config_path

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from the JSON file.

        :return: Configuration dictionary
        :rtype: Dict[str, Any]
        :raises FileNotFoundError: If config file doesn't exist
        :raises json.JSONDecodeError: If config file is invalid JSON
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to the JSON file.

        :param config: Configuration dictionary to save
        :type config: Dict[str, Any]
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def get_router_config(self) -> Dict[str, Any]:
        """
        Get the Router section from config.

        :return: Router configuration dictionary
        :rtype: Dict[str, Any]
        """
        config = self.load_config()
        return config.get("Router", {})

    def update_router_config(self, router_config: Dict[str, Any]) -> None:
        """
        Update the Router section in config.

        :param router_config: Router configuration dictionary
        :type router_config: Dict[str, Any]
        """
        config = self.load_config()
        config["Router"] = router_config
        self.save_config(config)

    def get_providers(self) -> list[Dict[str, Any]]:
        """
        Get all providers from config.

        :return: List of provider dictionaries
        :rtype: list[Dict[str, Any]]
        """
        config = self.load_config()
        return config.get("Providers", [])

    def add_provider(self, provider: Dict[str, Any]) -> None:
        """
        Add a new provider to the config.

        :param provider: Provider dictionary with name, api_base_url, and optionally api_key and models
        :type provider: Dict[str, Any]
        :raises ValueError: If provider with same name or base URL already exists
        """
        # Check for duplicates before adding
        self._check_duplicate_provider(provider)

        config = self.load_config()
        providers = config.get("Providers", [])
        providers.append(provider)
        config["Providers"] = providers
        self.save_config(config)

    def _check_duplicate_provider(self, new_provider: Dict[str, Any]) -> None:
        """
        Check if a provider with the same name or base URL already exists.

        :param new_provider: New provider to check
        :type new_provider: Dict[str, Any]
        :raises ValueError: If provider with same name or base URL already exists
        """
        providers = self.get_providers()
        new_name = new_provider.get("name")
        new_base_url = new_provider.get("api_base_url")

        for provider in providers:
            # Check for duplicate name
            if provider.get("name") == new_name:
                raise ValueError(f"Provider with name '{new_name}' already exists")

            # Check for duplicate base URL
            if provider.get("api_base_url") == new_base_url:
                raise ValueError(f"Provider with base URL '{new_base_url}' already exists")

    def add_model_to_provider(self, provider_name: str, model_name: str) -> None:
        """
        Add a model to an existing provider.

        :param provider_name: Name of the provider
        :type provider_name: str
        :param model_name: Name of the model to add
        :type model_name: str
        :raises ValueError: If provider not found
        """
        config = self.load_config()
        providers = config.get("Providers", [])
        for provider in providers:
            if provider.get("name") == provider_name:
                models = provider.get("models", [])
                if model_name not in models:
                    models.append(model_name)
                    provider["models"] = models
                    self.save_config(config)
                return
        raise ValueError(f"Provider '{provider_name}' not found")

    def get_all_models(self) -> Dict[str, list[str]]:
        """
        Get all models grouped by provider.

        :return: Dictionary mapping provider names to lists of model names
        :rtype: Dict[str, list[str]]
        """
        providers = self.get_providers()
        return {provider["name"]: provider.get("models", []) for provider in providers}

    def find_providers_for_model(self, model_name: str) -> list[str]:
        """
        Find all providers that have a model with the given name.

        :param model_name: Name of the model to search for
        :type model_name: str
        :return: List of provider names that have this model
        :rtype: list[str]
        """
        models_by_provider = self.get_all_models()
        matching_providers = []
        for provider_name, models in models_by_provider.items():
            if model_name in models:
                matching_providers.append(provider_name)
        return matching_providers

    def validate_provider_model(self, provider_name: str, model_name: str) -> bool:
        """
        Validate that a provider has a specific model.

        :param provider_name: Name of the provider
        :type provider_name: str
        :param model_name: Name of the model
        :type model_name: str
        :return: True if the provider has the model, False otherwise
        :rtype: bool
        """
        models_by_provider = self.get_all_models()
        provider_models = models_by_provider.get(provider_name, [])
        return model_name in provider_models

    def delete_provider(self, provider_name: str) -> None:
        """
        Delete a provider from the config.

        :param provider_name: Name of the provider to delete
        :type provider_name: str
        :raises ValueError: If provider not found
        """
        config = self.load_config()
        providers = config.get("Providers", [])
        original_count = len(providers)
        providers = [p for p in providers if p.get("name") != provider_name]
        if len(providers) == original_count:
            raise ValueError(f"Provider '{provider_name}' not found")
        config["Providers"] = providers
        self.save_config(config)

    def delete_model(self, model_name: str) -> None:
        """
        Delete a model from all providers that contain it.

        :param model_name: Name of the model to delete
        :type model_name: str
        :raises ValueError: If model not found in any provider
        """
        config = self.load_config()
        providers = config.get("Providers", [])
        model_found = False
        for provider in providers:
            models = provider.get("models", [])
            if model_name in models:
                models.remove(model_name)
                provider["models"] = models
                model_found = True
        if not model_found:
            raise ValueError(f"Model '{model_name}' not found in any provider")
        self.save_config(config)

    def validate_provider_endpoint(self, base_url: str) -> str:
        """
        Validate a provider endpoint by checking if /v1 is needed in the base URL.

        This function will:
        1. Try base_url/v1/models first
        2. If that fails, try base_url/models
        3. Return the correct base URL format based on which endpoint responds

        :param base_url: Base URL of the provider
        :type base_url: str
        :return: Corrected base URL
        :rtype: str
        """
        import requests

        # Remove trailing slash if present
        base_url = base_url.rstrip('/')

        # Flag to track if we should try without /v1
        should_try_without_v1 = False

        # Check if base_url already ends with /v1 or /v1/... to avoid double /v1
        if base_url.endswith('/v1') or '/v1/' in base_url:
            # Extract the base part before /v1
            if base_url.endswith('/v1'):
                # URL ends with /v1, so we can try /v1/models and /models
                v1_url = f"{base_url}/models"  # This becomes /v1/models
                no_v1_url = f"{base_url[:-3]}/models"  # This becomes /models (without v1)
            else:
                # URL contains /v1/ somewhere, extract the part before /v1/
                v1_index = base_url.find('/v1/')
                base_part = base_url[:v1_index]
                v1_url = f"{base_part}/v1/models"  # Standard /v1/models
                no_v1_url = f"{base_part}/models"  # Without v1
        else:
            # No /v1 in URL, try adding /v1
            v1_url = f"{base_url}/v1/models"
            no_v1_url = f"{base_url}/models"

        try:
            response = requests.get(v1_url, timeout=10)
            # If we get a successful response (2xx) it means the endpoint exists with /v1
            if 200 <= response.status_code < 300:
                if base_url.endswith('/v1'):
                    return base_url  # Already has /v1, so return as-is
                else:
                    return f"{base_url}/v1"
            # If we get a 404, it means /v1 doesn't exist, so we should try without /v1
            elif response.status_code == 404:
                should_try_without_v1 = True
            # If we get other 4xx errors (like 401, 403), it means the endpoint exists but requires auth
            elif 400 <= response.status_code < 500:
                if base_url.endswith('/v1'):
                    return base_url  # Already has /v1, so return as-is
                else:
                    return f"{base_url}/v1"
        except requests.RequestException:
            # If there's a network error, we'll try the other option
            should_try_without_v1 = True

        # Try without /v1 if needed
        if should_try_without_v1:
            try:
                response = requests.get(no_v1_url, timeout=10)
                # If we get a successful response (2xx) it means the endpoint exists without /v1
                if 200 <= response.status_code < 300:
                    if base_url.endswith('/v1'):
                        return base_url[:-3]  # Remove /v1 from the base URL
                    else:
                        return base_url
                # If we get other 4xx errors (like 401, 403), it means the endpoint exists but requires auth
                elif 400 <= response.status_code < 500:
                    if base_url.endswith('/v1'):
                        return base_url[:-3]  # Remove /v1 from the base URL
                    else:
                        return base_url
            except requests.RequestException:
                # If both attempts fail, return the original URL
                pass

        # If both attempts fail, return the original URL
        return base_url
