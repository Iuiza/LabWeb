from dynaconf import Dynaconf
from pathlib import Path

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=["settings.toml", ".secrets.toml"],
    root_path=Path(__file__).parent,
    merge_enabled=True,
)