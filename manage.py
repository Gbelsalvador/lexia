#!/usr/bin/env python
"""Point d'entrée des commandes Django."""
import os
import sys


def main() -> None:
    """Exécute les commandes administratives Django."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django n'est pas installé. Activez le venv puis installez "
            "les dépendances avec: pip install -r requirements.txt"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
