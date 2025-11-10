"""Tests for CLI functions."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_code_router_switcher.cli import (
    add_model,
    add_provider,
    change_router,
    create_parser,
    delete_model,
    delete_provider,
    delete_router,
    list_models,
    main,
    set_long_context_threshold,
    show_config,
)
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
def config_manager(temp_config_file: Path) -> ConfigManager:
    """
    Create a ConfigManager instance with a temporary config file.

    :param temp_config_file: Temporary config file path
    :type temp_config_file: Path
    :return: ConfigManager instance
    :rtype: ConfigManager
    """
    return ConfigManager(temp_config_file)


class TestListModels:
    """Tests for list_models function."""

    @patch("claude_code_router_switcher.cli.console")
    def test_list_models_success(self, mock_console: MagicMock, config_manager: ConfigManager) -> None:
        """Test listing models successfully."""
        list_models(config_manager)
        assert mock_console.print.called
        call_args = mock_console.print.call_args[0][0]
        assert hasattr(call_args, "title")
        assert call_args.title == "Available Models"

    @patch("claude_code_router_switcher.cli.console")
    def test_list_models_empty(self, mock_console: MagicMock) -> None:
        """Test listing models when no providers exist."""
        empty_config = Path(tempfile.mktemp(suffix=".json"))
        try:
            with open(empty_config, "w") as f:
                json.dump({}, f)
            manager = ConfigManager(empty_config)
            list_models(manager)
            mock_console.print.assert_called_with("[yellow]No providers or models found in config[/yellow]")
        finally:
            empty_config.unlink(missing_ok=True)


class TestShowConfig:
    """Tests for show_config function."""

    @patch("claude_code_router_switcher.cli.console")
    def test_show_config_success(self, mock_console: MagicMock, config_manager: ConfigManager) -> None:
        """Test showing config successfully."""
        show_config(config_manager)
        assert mock_console.print.called
        call_args = mock_console.print.call_args[0][0]
        assert hasattr(call_args, "title")
        assert call_args.title == "Current Router Configuration"

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_show_config_empty(self, mock_sys: MagicMock, mock_console: MagicMock) -> None:
        """Test showing config when Router section is empty."""
        empty_config = Path(tempfile.mktemp(suffix=".json"))
        try:
            with open(empty_config, "w") as f:
                json.dump({}, f)
            manager = ConfigManager(empty_config)
            show_config(manager)
            mock_console.print.assert_called_with("[yellow]No router configuration found[/yellow]")
        finally:
            empty_config.unlink(missing_ok=True)

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_show_config_file_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test showing config when file doesn't exist."""
        non_existent = Path("/nonexistent/config.json")
        manager = ConfigManager(non_existent)
        show_config(manager)
        mock_console.print.assert_called()
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestChangeRouter:
    """Tests for change_router function."""

    @patch("claude_code_router_switcher.cli.console")
    def test_change_router_with_provider_model(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing router with provider,model format."""
        change_router(config_manager, "default", "provider1,model2")
        router_config = config_manager.get_router_config()
        assert router_config["default"] == "provider1,model2"
        mock_console.print.assert_called_with("[green]Updated default to: provider1,model2[/green]")

    @patch("claude_code_router_switcher.cli.console")
    def test_change_router_with_model_only(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing router with model only (auto-detect provider)."""
        change_router(config_manager, "background", "model1")
        router_config = config_manager.get_router_config()
        assert router_config["background"] == "provider1,model1"

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_change_router_invalid_type(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing router with invalid router type."""
        change_router(config_manager, "invalid", "model1")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_change_router_invalid_provider_model(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing router with invalid provider,model combination."""
        change_router(config_manager, "default", "provider1,invalid_model")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys.exit")
    def test_change_router_model_not_found(
        self, mock_exit: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing router with model not found in any provider."""
        mock_exit.side_effect = SystemExit(1)
        with pytest.raises(SystemExit):
            change_router(config_manager, "default", "nonexistent_model")
        assert mock_exit.called
        assert mock_exit.call_args[0][0] == 1

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_change_router_multiple_providers(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing router with model found in multiple providers."""
        change_router(config_manager, "default", "model2")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestAddProvider:
    """Tests for add_provider function."""

    @patch("claude_code_router_switcher.cli.console")
    def test_add_provider_success(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test adding a provider successfully."""
        add_provider(config_manager, "provider3", "http://example3.com", "key3")
        providers = config_manager.get_providers()
        assert len(providers) == 3
        assert providers[2]["name"] == "provider3"
        mock_console.print.assert_called_with("[green]Added provider: provider3[/green]")

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_add_provider_file_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test adding provider when config file doesn't exist."""
        non_existent = Path("/nonexistent/config.json")
        manager = ConfigManager(non_existent)
        add_provider(manager, "provider1", "http://example.com", "key1")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestAddModel:
    """Tests for add_model function."""

    @patch("claude_code_router_switcher.cli.console")
    def test_add_model_success(self, mock_console: MagicMock, config_manager: ConfigManager) -> None:
        """Test adding a model successfully."""
        add_model(config_manager, "provider1", "model3")
        providers = config_manager.get_providers()
        provider1 = next(p for p in providers if p["name"] == "provider1")
        assert "model3" in provider1["models"]
        mock_console.print.assert_called_with("[green]Added model 'model3' to provider 'provider1'[/green]")

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_add_model_provider_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test adding model to non-existent provider."""
        add_model(config_manager, "nonexistent", "model1")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_add_model_file_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock
    ) -> None:
        """Test adding model when config file doesn't exist."""
        non_existent = Path("/nonexistent/config.json")
        manager = ConfigManager(non_existent)
        add_model(manager, "provider1", "model1")
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestDeleteProvider:
    """Tests for delete_provider function."""

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.input")
    def test_delete_provider_success(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting a provider successfully with confirmation."""
        mock_input.return_value = "y"
        delete_provider(config_manager, "provider1")
        providers = config_manager.get_providers()
        assert len(providers) == 1
        assert providers[0]["name"] == "provider2"
        mock_console.print.assert_called_with("[green]Deleted provider: provider1[/green]")

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.input")
    def test_delete_provider_cancelled(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test cancelling provider deletion."""
        mock_input.return_value = "n"
        original_count = len(config_manager.get_providers())
        delete_provider(config_manager, "provider1")
        providers = config_manager.get_providers()
        assert len(providers) == original_count
        mock_console.print.assert_called_with("[yellow]Deletion cancelled[/yellow]")

    @patch("claude_code_router_switcher.cli.console")
    def test_delete_provider_auto_confirm(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting provider with auto-confirm."""
        delete_provider(config_manager, "provider1", auto_confirm=True)
        providers = config_manager.get_providers()
        assert len(providers) == 1
        mock_console.print.assert_called_with("[green]Deleted provider: provider1[/green]")

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_delete_provider_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting non-existent provider."""
        delete_provider(config_manager, "nonexistent", auto_confirm=True)
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestDeleteModel:
    """Tests for delete_model function."""

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.input")
    def test_delete_model_success(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting a model successfully with confirmation."""
        mock_input.return_value = "y"
        delete_model(config_manager, "model2")
        models_by_provider = config_manager.get_all_models()
        assert "model2" not in models_by_provider["provider1"]
        assert "model2" not in models_by_provider["provider2"]
        mock_console.print.assert_called_with("[green]Deleted model: model2[/green]")

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.input")
    def test_delete_model_cancelled(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test cancelling model deletion."""
        mock_input.return_value = "n"
        original_models = config_manager.get_all_models()
        delete_model(config_manager, "model2")
        current_models = config_manager.get_all_models()
        assert current_models == original_models
        mock_console.print.assert_called_with("[yellow]Deletion cancelled[/yellow]")

    @patch("claude_code_router_switcher.cli.console")
    def test_delete_model_auto_confirm(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting model with auto-confirm."""
        delete_model(config_manager, "model1", auto_confirm=True)
        models_by_provider = config_manager.get_all_models()
        assert "model1" not in models_by_provider["provider1"]
        mock_console.print.assert_called_with("[green]Deleted model: model1[/green]")

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_delete_model_not_found(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting non-existent model."""
        delete_model(config_manager, "nonexistent", auto_confirm=True)
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1


class TestCreateParser:
    """Tests for create_parser function."""

    def test_create_parser_returns_parser(self) -> None:
        """Test that create_parser returns an ArgumentParser."""
        parser = create_parser()
        assert parser.prog == "ccs"
        assert parser.description == "Claude Code Router Switcher - Manage router configuration"

    def test_create_parser_has_subcommands(self) -> None:
        """Test that parser has expected subcommands."""
        parser = create_parser()
        args = parser.parse_args(["ls"])
        assert args.command == "ls"

        args = parser.parse_args(["show"])
        assert args.command == "show"

        args = parser.parse_args(["change", "default", "provider1,model1"])
        assert args.command == "change"
        assert args.router_type == "default"
        assert args.model_value == "provider1,model1"

        args = parser.parse_args(["add", "provider", "--name", "test", "--base-url", "http://test.com", "--api-key", "key"])
        assert args.command == "add"
        assert args.add_type == "provider"
        assert args.name == "test"

        args = parser.parse_args(["add", "model", "provider1", "model1"])
        assert args.command == "add"
        assert args.add_type == "model"
        assert args.provider == "provider1"
        assert args.model_name == "model1"

        args = parser.parse_args(["delete", "provider", "provider1"])
        assert args.command == "delete"
        assert args.delete_type == "provider"
        assert args.provider_name == "provider1"

        args = parser.parse_args(["delete", "model", "model1"])
        assert args.command == "delete"
        assert args.delete_type == "model"
        assert args.model_name == "model1"

        args = parser.parse_args(["delete", "router", "background"])
        assert args.command == "delete"
        assert args.delete_type == "router"
        assert args.router_type == "background"

        args = parser.parse_args(["set", "longContextThreshold", "1000"])
        assert args.command == "set"
        assert args.set_type == "longContextThreshold"
        assert args.threshold == 1000


class TestMain:
    """Tests for main function."""

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "ls"])
    @patch("claude_code_router_switcher.cli.list_models")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_ls_command(self, mock_config_manager_class: MagicMock, mock_list_models: MagicMock) -> None:
        """Test main function with ls command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_list_models.assert_called_once_with(mock_manager)

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "show"])
    @patch("claude_code_router_switcher.cli.show_config")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_show_command(self, mock_config_manager_class: MagicMock, mock_show_config: MagicMock) -> None:
        """Test main function with show command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_show_config.assert_called_once_with(mock_manager)

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "change", "default", "provider1,model1"])
    @patch("claude_code_router_switcher.cli.change_router")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_change_command(
        self, mock_config_manager_class: MagicMock, mock_change_router: MagicMock
    ) -> None:
        """Test main function with change command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_change_router.assert_called_once_with(mock_manager, "default", "provider1,model1")

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "add", "provider", "--name", "test", "--base-url", "http://test.com", "--api-key", "key"])
    @patch("claude_code_router_switcher.cli.add_provider")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_add_provider_command(
        self, mock_config_manager_class: MagicMock, mock_add_provider: MagicMock
    ) -> None:
        """Test main function with add provider command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_add_provider.assert_called_once_with(mock_manager, "test", "http://test.com", "key")

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "add", "model", "provider1", "model1"])
    @patch("claude_code_router_switcher.cli.add_model")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_add_model_command(
        self, mock_config_manager_class: MagicMock, mock_add_model: MagicMock
    ) -> None:
        """Test main function with add model command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_add_model.assert_called_once_with(mock_manager, "provider1", "model1")

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "delete", "provider", "provider1"])
    @patch("claude_code_router_switcher.cli.delete_provider")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_delete_provider_command(
        self, mock_config_manager_class: MagicMock, mock_delete_provider: MagicMock
    ) -> None:
        """Test main function with delete provider command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_delete_provider.assert_called_once_with(mock_manager, "provider1", False)

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "delete", "provider", "provider1", "-y"])
    @patch("claude_code_router_switcher.cli.delete_provider")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_delete_provider_with_yes(
        self, mock_config_manager_class: MagicMock, mock_delete_provider: MagicMock
    ) -> None:
        """Test main function with delete provider command and -y flag."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_delete_provider.assert_called_once_with(mock_manager, "provider1", True)

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "delete", "model", "model1"])
    @patch("claude_code_router_switcher.cli.delete_model")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_delete_model_command(
        self, mock_config_manager_class: MagicMock, mock_delete_model: MagicMock
    ) -> None:
        """Test main function with delete model command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_delete_model.assert_called_once_with(mock_manager, "model1", False)

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "delete", "router", "background"])
    @patch("claude_code_router_switcher.cli.delete_router")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_delete_router_command(
        self, mock_config_manager_class: MagicMock, mock_delete_router: MagicMock
    ) -> None:
        """Test main function with delete router command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_delete_router.assert_called_once_with(mock_manager, "background", False)

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs", "set", "longContextThreshold", "1000"])
    @patch("claude_code_router_switcher.cli.set_long_context_threshold")
    @patch("claude_code_router_switcher.cli.ConfigManager")
    def test_main_set_long_context_threshold_command(
        self, mock_config_manager_class: MagicMock, mock_set_threshold: MagicMock
    ) -> None:
        """Test main function with set longContextThreshold command."""
        mock_manager = MagicMock()
        mock_config_manager_class.return_value = mock_manager
        main()
        mock_set_threshold.assert_called_once_with(mock_manager, 1000)

    @patch("claude_code_router_switcher.cli.sys.argv", ["ccs"])
    @patch("claude_code_router_switcher.cli.sys.exit")
    def test_main_no_command(self, mock_exit: MagicMock) -> None:
        """Test main function with no command prints help and exits."""
        with patch("claude_code_router_switcher.cli.create_parser") as mock_parser_class:
            mock_parser = MagicMock()
            mock_parser.parse_args.return_value = MagicMock(command=None)
            mock_parser_class.return_value = mock_parser
            main()
            mock_parser.print_help.assert_called_once()
            mock_exit.assert_called_once_with(1)


class TestSetLongContextThreshold:
    """Tests for set_long_context_threshold function."""

    @patch("claude_code_router_switcher.cli.console")
    def test_set_long_context_threshold_success(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test setting longContextThreshold successfully when longContext is set."""
        router_config = config_manager.get_router_config()
        router_config["longContext"] = "provider1,model1"
        config_manager.update_router_config(router_config)

        set_long_context_threshold(config_manager, 1000)
        updated_config = config_manager.get_router_config()
        assert updated_config["longContextThreshold"] == 1000
        mock_console.print.assert_called_with("[green]Updated longContextThreshold to: 1000[/green]")

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_set_long_context_threshold_without_long_context(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test setting longContextThreshold fails when longContext is not set."""
        set_long_context_threshold(config_manager, 1000)
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1
        assert any(
            "longContext model must be set" in str(call)
            for call in mock_console.print.call_args_list
        )


class TestDeleteRouter:
    """Tests for delete_router function."""

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.input")
    def test_delete_router_success(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting a router configuration successfully."""
        mock_input.return_value = "y"
        router_config = config_manager.get_router_config()
        router_config["think"] = "provider1,model1"
        config_manager.update_router_config(router_config)

        delete_router(config_manager, "think")
        updated_config = config_manager.get_router_config()
        assert "think" not in updated_config
        mock_console.print.assert_called_with("[green]Deleted router: think[/green]")

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.input")
    def test_delete_router_cancelled(
        self, mock_input: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test cancelling router deletion."""
        mock_input.return_value = "n"
        router_config = config_manager.get_router_config()
        router_config["think"] = "provider1,model1"
        config_manager.update_router_config(router_config)

        delete_router(config_manager, "think")
        updated_config = config_manager.get_router_config()
        assert "think" in updated_config
        mock_console.print.assert_called_with("[yellow]Deletion cancelled[/yellow]")

    @patch("claude_code_router_switcher.cli.console")
    def test_delete_router_auto_confirm(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting router with auto-confirm."""
        router_config = config_manager.get_router_config()
        router_config["background"] = "provider1,model1"
        config_manager.update_router_config(router_config)

        delete_router(config_manager, "background", auto_confirm=True)
        updated_config = config_manager.get_router_config()
        assert "background" not in updated_config
        mock_console.print.assert_called_with("[green]Deleted router: background[/green]")

    @patch("claude_code_router_switcher.cli.console")
    def test_delete_router_not_set(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting router that is not set."""
        delete_router(config_manager, "think", auto_confirm=True)
        mock_console.print.assert_called_with("[yellow]Router 'think' is not set[/yellow]")

    @patch("claude_code_router_switcher.cli.console")
    @patch("claude_code_router_switcher.cli.sys")
    def test_delete_router_invalid_type(
        self, mock_sys: MagicMock, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting router with invalid type."""
        delete_router(config_manager, "default", auto_confirm=True)
        assert mock_sys.exit.called
        assert mock_sys.exit.call_args[0][0] == 1

    @patch("claude_code_router_switcher.cli.console")
    def test_delete_long_context_removes_threshold(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting longContext router also removes longContextThreshold."""
        router_config = config_manager.get_router_config()
        router_config["longContext"] = "provider1,model1"
        router_config["longContextThreshold"] = 1000
        config_manager.update_router_config(router_config)

        delete_router(config_manager, "longContext", auto_confirm=True)
        updated_config = config_manager.get_router_config()
        assert "longContext" not in updated_config
        assert "longContextThreshold" not in updated_config
        print_calls = [str(call[0][0]) for call in mock_console.print.call_args_list if call[0]]
        assert any("Also removed longContextThreshold" in call for call in print_calls)

    @patch("claude_code_router_switcher.cli.console")
    def test_delete_long_context_without_threshold(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting longContext router when threshold is not set."""
        router_config = config_manager.get_router_config()
        router_config["longContext"] = "provider1,model1"
        config_manager.update_router_config(router_config)

        delete_router(config_manager, "longContext", auto_confirm=True)
        updated_config = config_manager.get_router_config()
        assert "longContext" not in updated_config
        mock_console.print.assert_called_with("[green]Deleted router: longContext[/green]")


class TestChangeRouterLongContext:
    """Tests for change_router function with longContext."""

    @patch("claude_code_router_switcher.cli.console")
    def test_change_router_long_context_shows_warning(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test changing longContext router shows warning about setting threshold."""
        change_router(config_manager, "longContext", "provider1,model1")
        router_config = config_manager.get_router_config()
        assert router_config["longContext"] == "provider1,model1"

        # Check that warning was printed
        print_calls = []
        for call in mock_console.print.call_args_list:
            if call and call[0]:
                print_calls.append(str(call[0][0]))
        assert any("longContextThreshold" in call and "Tip" in call for call in print_calls), f"Expected warning not found. Calls: {print_calls}"
        assert any("ccs set longContextThreshold" in call for call in print_calls)


class TestDeleteModelLongContext:
    """Tests for delete_model function when model is used as longContext."""

    @patch("claude_code_router_switcher.cli.console")
    def test_delete_model_that_is_long_context_removes_threshold(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting a model that is the longContext model removes threshold."""
        router_config = config_manager.get_router_config()
        router_config["longContext"] = "provider1,model1"
        router_config["longContextThreshold"] = 1000
        config_manager.update_router_config(router_config)

        delete_model(config_manager, "model1", auto_confirm=True)
        updated_config = config_manager.get_router_config()
        assert "longContextThreshold" not in updated_config
        print_calls = [str(call[0][0]) for call in mock_console.print.call_args_list if call[0]]
        assert any("Also removed longContextThreshold" in call for call in print_calls)

    @patch("claude_code_router_switcher.cli.console")
    def test_delete_model_that_is_long_context_without_threshold(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test deleting a model that is the longContext model when threshold not set."""
        router_config = config_manager.get_router_config()
        router_config["longContext"] = "provider1,model1"
        config_manager.update_router_config(router_config)

        delete_model(config_manager, "model1", auto_confirm=True)
        # Should still work, just no threshold to remove
        assert any(
            "Deleted model: model1" in str(call) for call in mock_console.print.call_args_list
        )


class TestShowConfigLongContextThreshold:
    """Tests for show_config function with longContextThreshold."""

    @patch("claude_code_router_switcher.cli.console")
    def test_show_config_displays_long_context_threshold(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test that show_config displays longContextThreshold when set."""
        router_config = config_manager.get_router_config()
        router_config["longContextThreshold"] = 1000
        config_manager.update_router_config(router_config)

        show_config(config_manager)
        assert mock_console.print.called
        call_args = mock_console.print.call_args[0][0]
        assert hasattr(call_args, "title")
        assert call_args.title == "Current Router Configuration"

    @patch("claude_code_router_switcher.cli.console")
    def test_show_config_shows_not_set_for_missing_threshold(
        self, mock_console: MagicMock, config_manager: ConfigManager
    ) -> None:
        """Test that show_config shows 'Not set' for missing longContextThreshold."""
        show_config(config_manager)
        assert mock_console.print.called

