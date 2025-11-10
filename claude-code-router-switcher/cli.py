"""CLI interface for the configuration switcher."""

import argparse
import sys
from pathlib import Path

from claude_code_router_switcher.config_manager import ConfigManager
from rich.console import Console
from rich.table import Table

console = Console()


def list_models(config_manager: ConfigManager) -> None:
    """
    List all models grouped by provider.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    """
    models_by_provider = config_manager.get_all_models()
    if not models_by_provider:
        console.print("[yellow]No providers or models found in config[/yellow]")
        return

    table = Table(title="Available Models")
    table.add_column("Provider", style="cyan")
    table.add_column("Models", style="green")

    for provider, models in models_by_provider.items():
        models_str = ", ".join(models) if models else "[red]No models[/red]"
        table.add_row(provider, models_str)

    console.print(table)


def show_config(config_manager: ConfigManager) -> None:
    """
    Show current router configuration.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    """
    try:
        router_config = config_manager.get_router_config()
        if not router_config:
            console.print("[yellow]No router configuration found[/yellow]")
            return

        table = Table(title="Current Router Configuration")
        table.add_column("Type", style="cyan")
        table.add_column("Value", style="green")

        router_types = ["default", "background", "think", "longContext", "webSearch"]
        for router_type in router_types:
            value = router_config.get(router_type, "[red]Not set[/red]")
            table.add_row(router_type, str(value))

        long_context_threshold = router_config.get("longContextThreshold", "[red]Not set[/red]")
        table.add_row("longContextThreshold", str(long_context_threshold))

        console.print(table)
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def change_router(
    config_manager: ConfigManager, router_type: str, model_value: str
) -> None:
    """
    Change a router configuration value.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param router_type: Type of router (default, background, think, longContext, webSearch)
    :type router_type: str
    :param model_value: Model value in format <provider>,<model> or just <model>
    :type model_value: str
    """
    valid_types = ["default", "background", "think", "longContext", "webSearch"]
    if router_type not in valid_types:
        console.print(
            f"[red]Invalid router type: {router_type}[/red]\n"
            f"Valid types: {', '.join(valid_types)}"
        )
        sys.exit(1)

    try:
        # Check if input is provider,model format or just model name
        if "," in model_value:
            parts = model_value.split(",", 1)
            provider_name = parts[0].strip()
            model_name = parts[1].strip()

            # Validate provider,model combination
            if not config_manager.validate_provider_model(provider_name, model_name):
                console.print(
                    f"[red]Error: Model '{model_name}' not found in provider '{provider_name}'[/red]"
                )
                console.print("\n[yellow]Available models:[/yellow]")
                list_models(config_manager)
                sys.exit(1)

            final_value = f"{provider_name},{model_name}"
        else:
            # Just model name provided - try to auto-detect provider
            model_name = model_value.strip()
            matching_providers = config_manager.find_providers_for_model(model_name)

            if not matching_providers:
                console.print(
                    f"[red]Error: Model '{model_name}' not found in any provider[/red]"
                )
                console.print("\n[yellow]Available models:[/yellow]")
                list_models(config_manager)
                sys.exit(1)

            if len(matching_providers) > 1:
                console.print(
                    f"[red]Error: Model '{model_name}' found in multiple providers: "
                    f"{', '.join(matching_providers)}[/red]"
                )
                console.print(
                    "\n[yellow]Please specify provider explicitly: "
                    f"<provider>,{model_name}[/yellow]"
                )
                console.print("\n[yellow]Available models:[/yellow]")
                list_models(config_manager)
                sys.exit(1)

            # Single match - auto-complete
            provider_name = matching_providers[0]
            final_value = f"{provider_name},{model_name}"

        router_config = config_manager.get_router_config()
        router_config[router_type] = final_value
        config_manager.update_router_config(router_config)
        console.print(
            f"[green]Updated {router_type} to: {final_value}[/green]"
        )
        if router_type == "longContext":
            console.print(
                "\n[yellow]Tip: Set longContextThreshold next to enable:[/yellow]"
            )
            console.print(
                "[yellow]  ccs set longContextThreshold <integer>[/yellow]"
            )
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def add_provider(
    config_manager: ConfigManager, name: str, base_url: str, api_key: str
) -> None:
    """
    Add a new provider to the configuration.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param name: Provider name
    :type name: str
    :param base_url: API base URL
    :type base_url: str
    :param api_key: API key
    :type api_key: str
    """
    provider = {
        "name": name,
        "api_base_url": base_url,
        "api_key": api_key,
        "models": [],
    }

    try:
        config_manager.add_provider(provider)
        console.print(f"[green]Added provider: {name}[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def add_model(config_manager: ConfigManager, provider: str, model_name: str) -> None:
    """
    Add a model to an existing provider.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param provider: Provider name
    :type provider: str
    :param model_name: Model name to add
    :type model_name: str
    """
    try:
        config_manager.add_model_to_provider(provider, model_name)
        console.print(f"[green]Added model '{model_name}' to provider '{provider}'[/green]")
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def delete_provider(config_manager: ConfigManager, provider_name: str, auto_confirm: bool = False) -> None:
    """
    Delete a provider from the configuration.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param provider_name: Name of the provider to delete
    :type provider_name: str
    :param auto_confirm: Skip confirmation prompt if True
    :type auto_confirm: bool
    """
    if not auto_confirm:
        response = input("ARE YOU SURE?! [y/N]: ").strip().lower()
        if response != "y":
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    try:
        config_manager.delete_provider(provider_name)
        console.print(f"[green]Deleted provider: {provider_name}[/green]")
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def delete_model(config_manager: ConfigManager, model_name: str, auto_confirm: bool = False) -> None:
    """
    Delete a model from all providers that contain it.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param model_name: Name of the model to delete
    :type model_name: str
    :param auto_confirm: Skip confirmation prompt if True
    :type auto_confirm: bool
    """
    if not auto_confirm:
        response = input("ARE YOU SURE?! [y/N]: ").strip().lower()
        if response != "y":
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    try:
        # Check if this model is used as longContext before deletion
        router_config = config_manager.get_router_config()
        long_context = router_config.get("longContext", "")
        has_threshold = "longContextThreshold" in router_config
        is_long_context_model = (
            long_context and (
                long_context.endswith(f",{model_name}") or
                long_context == model_name
            )
        )

        config_manager.delete_model(model_name)

        # If the deleted model was the longContext model, remove longContextThreshold
        if is_long_context_model and has_threshold:
            router_config = config_manager.get_router_config()
            router_config.pop("longContextThreshold", None)
            config_manager.update_router_config(router_config)
            console.print(
                f"[green]Deleted model: {model_name}[/green]\n"
                f"[yellow]Also removed longContextThreshold (longContext model was deleted)[/yellow]"
            )
        else:
            console.print(f"[green]Deleted model: {model_name}[/green]")
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def delete_router(config_manager: ConfigManager, router_type: str, auto_confirm: bool = False) -> None:
    """
    Delete/unset a router configuration value.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param router_type: Type of router to delete (background, think, longContext, webSearch)
    :type router_type: str
    :param auto_confirm: Skip confirmation prompt if True
    :type auto_confirm: bool
    """
    valid_types = ["background", "think", "longContext", "webSearch"]
    if router_type not in valid_types:
        console.print(
            f"[red]Invalid router type: {router_type}[/red]\n"
            f"Valid types: {', '.join(valid_types)}\n"
            f"[yellow]Note: 'default' cannot be deleted[/yellow]"
        )
        sys.exit(1)

    if not auto_confirm:
        response = input("ARE YOU SURE?! [y/N]: ").strip().lower()
        if response != "y":
            console.print("[yellow]Deletion cancelled[/yellow]")
            return

    try:
        router_config = config_manager.get_router_config()
        if router_type not in router_config:
            console.print(f"[yellow]Router '{router_type}' is not set[/yellow]")
            return

        # If deleting longContext, also remove longContextThreshold
        removed_threshold = False
        if router_type == "longContext" and "longContextThreshold" in router_config:
            router_config.pop("longContextThreshold", None)
            removed_threshold = True

        router_config.pop(router_type, None)
        config_manager.update_router_config(router_config)

        if removed_threshold:
            console.print(
                f"[green]Deleted router: {router_type}[/green]\n"
                f"[yellow]Also removed longContextThreshold[/yellow]"
            )
        else:
            console.print(f"[green]Deleted router: {router_type}[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def set_long_context_threshold(config_manager: ConfigManager, threshold: int) -> None:
    """
    Set the long context threshold value.

    :param config_manager: Configuration manager instance
    :type config_manager: ConfigManager
    :param threshold: Threshold value as integer
    :type threshold: int
    """
    try:
        router_config = config_manager.get_router_config()
        long_context = router_config.get("longContext")
        if not long_context:
            console.print(
                "[red]Error: longContext model must be set before setting longContextThreshold[/red]"
            )
            console.print("\n[yellow]Use 'ccs change longContext <provider>,<model>' to set it first[/yellow]")
            sys.exit(1)
        router_config["longContextThreshold"] = threshold
        config_manager.update_router_config(router_config)
        console.print(f"[green]Updated longContextThreshold to: {threshold}[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    :return: Configured argument parser
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="ccs",
        description="Claude Code Router Switcher - Manage router configuration",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file (default: ~/.claude-code-router/config.json)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ls command
    subparsers.add_parser("ls", help="List all models grouped by provider")

    # show command
    subparsers.add_parser("show", help="Show current router configuration")

    # change command
    change_parser = subparsers.add_parser(
        "change", help="Change a router configuration value"
    )
    change_parser.add_argument(
        "router_type",
        choices=["default", "background", "think", "longContext", "webSearch"],
        help="Type of router to change",
    )
    change_parser.add_argument(
        "model_value",
        help="Model value in format <provider>,<model> or just <model> (auto-detects provider if unique)",
    )

    # add command with subcommands
    add_parser = subparsers.add_parser("add", help="Add provider or model")
    add_subparsers = add_parser.add_subparsers(dest="add_type", help="What to add")

    # add provider subcommand
    add_provider_parser = add_subparsers.add_parser(
        "provider", help="Add a new provider"
    )
    add_provider_parser.add_argument("--name", required=True, help="Provider name")
    add_provider_parser.add_argument(
        "--base-url", required=True, help="API base URL", dest="base_url"
    )
    add_provider_parser.add_argument(
        "--api-key", required=True, help="API key", dest="api_key"
    )

    # add model subcommand
    add_model_parser = add_subparsers.add_parser(
        "model", help="Add a model to a provider"
    )
    add_model_parser.add_argument("provider", help="Provider name")
    add_model_parser.add_argument("model_name", help="Model name to add")

    # delete command with subcommands
    delete_parser = subparsers.add_parser("delete", help="Delete provider or model")
    delete_subparsers = delete_parser.add_subparsers(dest="delete_type", help="What to delete")

    # delete provider subcommand
    delete_provider_parser = delete_subparsers.add_parser(
        "provider", help="Delete a provider"
    )
    delete_provider_parser.add_argument("provider_name", help="Provider name to delete")
    delete_provider_parser.add_argument(
        "-y", "--yes", action="store_true", dest="auto_confirm", help="Auto-confirm deletion"
    )

    # delete model subcommand
    delete_model_parser = delete_subparsers.add_parser(
        "model", help="Delete a model"
    )
    delete_model_parser.add_argument("model_name", help="Model name to delete")
    delete_model_parser.add_argument(
        "-y", "--yes", action="store_true", dest="auto_confirm", help="Auto-confirm deletion"
    )

    # delete router subcommand
    delete_router_parser = delete_subparsers.add_parser(
        "router", help="Delete/unset a router configuration"
    )
    delete_router_parser.add_argument(
        "router_type",
        choices=["background", "think", "longContext", "webSearch"],
        help="Type of router to delete (default cannot be deleted)",
    )
    delete_router_parser.add_argument(
        "-y", "--yes", action="store_true", dest="auto_confirm", help="Auto-confirm deletion"
    )

    # set command with subcommands
    set_parser = subparsers.add_parser("set", help="Set configuration values")
    set_subparsers = set_parser.add_subparsers(dest="set_type", help="What to set")

    # set longContextThreshold subcommand
    set_threshold_parser = set_subparsers.add_parser(
        "longContextThreshold", help="Set the long context threshold"
    )
    set_threshold_parser.add_argument(
        "threshold", type=int, help="Threshold value as integer"
    )

    return parser


def main() -> None:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    default_config_path = Path.home() / ".claude-code-router" / "config.json"
    config_path_to_use = getattr(args, "config", None) or default_config_path
    config_manager = ConfigManager(config_path_to_use)

    if args.command == "ls":
        list_models(config_manager)
    elif args.command == "show":
        show_config(config_manager)
    elif args.command == "change":
        change_router(config_manager, args.router_type, args.model_value)
    elif args.command == "add":
        if not hasattr(args, "add_type") or args.add_type is None:
            parser.parse_args(["add", "--help"])
            sys.exit(1)
        elif args.add_type == "provider":
            add_provider(config_manager, args.name, args.base_url, args.api_key)
        elif args.add_type == "model":
            add_model(config_manager, args.provider, args.model_name)
    elif args.command == "delete":
        if not hasattr(args, "delete_type") or args.delete_type is None:
            parser.parse_args(["delete", "--help"])
            sys.exit(1)
        elif args.delete_type == "provider":
            auto_confirm = getattr(args, "auto_confirm", False)
            delete_provider(config_manager, args.provider_name, auto_confirm)
        elif args.delete_type == "model":
            auto_confirm = getattr(args, "auto_confirm", False)
            delete_model(config_manager, args.model_name, auto_confirm)
        elif args.delete_type == "router":
            auto_confirm = getattr(args, "auto_confirm", False)
            delete_router(config_manager, args.router_type, auto_confirm)
    elif args.command == "set":
        if not hasattr(args, "set_type") or args.set_type is None:
            parser.parse_args(["set", "--help"])
            sys.exit(1)
        elif args.set_type == "longContextThreshold":
            set_long_context_threshold(config_manager, args.threshold)
