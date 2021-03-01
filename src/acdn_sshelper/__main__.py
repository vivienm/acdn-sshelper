import asyncio
import logging
import os
import time
from datetime import timedelta
from functools import wraps
from pathlib import Path
from typing import Optional, TextIO

import click
import jinja2

from . import __version__
from .gcloud import GCloud
from .ssh import SSHConfigDumper
from .vault import Vault


logger = logging.getLogger(__name__)


ENV_PREFIX = "ACDN_SSHELPER"
RUNTIME_DIR = Path(
    os.getenv(
        f"{ENV_PREFIX}_RUNTIME_DIR",
        os.path.join(os.getenv("XDG_RUNTIME_DIR", "/tmp"), "acdn-sshelper"),
    ),
)


def click_async(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


async def create_signed_cert(
    public_key: Path,
    signed_cert: Path,
) -> None:
    vault = Vault()
    await vault.sign_key(
        public_key=public_key,
        signed_cert=signed_cert,
    )
    logger.info("Created signed certificate %r", str(signed_cert))


async def create_ssh_config(
    private_key: Path,
    signed_cert: Path,
    tld_format: str,
    ssh_config_template: jinja2.Template,
    ssh_config: TextIO,
) -> None:
    gcloud = GCloud()
    account, projects = await asyncio.gather(
        gcloud.get_account(),
        gcloud.get_projects(),
    )
    logger.info("Found GCS account %r", account)
    logger.info("Found GCS projects %r", [project.name for project in projects])
    instances_per_project = await asyncio.gather(
        *(gcloud.get_project_instances(project) for project in projects),
    )
    ssh_config_dumper = SSHConfigDumper(
        private_key=private_key,
        signed_cert=signed_cert,
        runtime_dir=RUNTIME_DIR,
        tld_format=tld_format,
        ssh_config_template=ssh_config_template,
    )
    ssh_config_dumper.dump(
        account=account,
        projects=zip(projects, instances_per_project),
        ssh_config=ssh_config,
    )
    logger.info("Created SSH config file %r", ssh_config.name)


async def run_once(
    tld_format: str,
    ssh_config_template: jinja2.Template,
    ssh_config: TextIO,
    private_key: Path,
    public_key: Path,
    signed_cert: Path,
) -> None:
    await asyncio.gather(
        create_signed_cert(
            public_key=public_key,
            signed_cert=signed_cert,
        ),
        create_ssh_config(
            private_key=private_key,
            signed_cert=signed_cert,
            tld_format=tld_format,
            ssh_config_template=ssh_config_template,
            ssh_config=ssh_config,
        ),
    )


async def run(
    tld_format: str,
    ssh_config_template: jinja2.Template,
    ssh_config: TextIO,
    private_key: Path,
    public_key: Path,
    signed_cert: Path,
    every: Optional[timedelta],
) -> None:
    while True:
        start = time.perf_counter()
        await run_once(
            tld_format=tld_format,
            ssh_config_template=ssh_config_template,
            ssh_config=ssh_config,
            private_key=private_key,
            public_key=public_key,
            signed_cert=signed_cert,
        )
        elapsed = time.perf_counter() - start
        if every is None:
            break
        else:
            sleep_delay = every.total_seconds() - elapsed
            logger.info("Next run in %0.2f sec", sleep_delay)
            await asyncio.sleep(sleep_delay)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-i",
    "--identity-file",
    show_default=True,
    type=click.Path(
        exists=True,
        dir_okay=False,
    ),
    help="SSH identity file (private key).",
    default="~/.ssh/id_rsa",
    metavar="IDENTITY_FILE",
    show_envvar=True,
)
@click.option(
    "--cert-file",
    show_default=True,
    type=click.Path(
        dir_okay=False,
    ),
    help="SSH signed certificate.",
    default=str(RUNTIME_DIR / "id_rsa.cert"),
    metavar="CERT_FILE",
    show_envvar=True,
)
@click.option(
    "--log-level",
    show_default=True,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    help="Logging level.",
    show_choices=True,
    default="INFO",
)
@click.option(
    "--tld-format",
    show_default=True,
    type=str,
    help="TLD format string.",
    default=".{project_slug}.gcp",
    metavar="TLD_FORMAT",
    show_envvar=True,
)
@click.option(
    "--ssh-config-template",
    show_default=True,
    type=click.File(),
    help="SSH config template file.",
    default=os.path.join(os.path.dirname(__file__), "ssh_config.jinja"),
    metavar="SSH_CONFIG_TEMPLATE",
    show_envvar=True,
)
@click.option(
    "--ssh-config",
    show_default=True,
    type=click.File("w", lazy=True, atomic=True),
    help="SSH config output file.",
    default=str(RUNTIME_DIR / "ssh_config"),
    metavar="SSH_CONFIG",
    show_envvar=True,
)
@click.option(
    "--loop/--once",
    help="Periodically regenerate SSH certificate and config.",
)
@click.option(
    "--loop-delay",
    show_default=True,
    type=click.INT,
    help="Duration in seconds between consecutive runs.",
    default=300,
    metavar="LOOP_DELAY",
    show_envvar=True,
)
@click.version_option(__version__)
@click_async
async def cli(
    identity_file,
    cert_file,
    log_level,
    tld_format,
    ssh_config_template,
    ssh_config,
    loop,
    loop_delay,
) -> None:
    """Generate SSH certificate and config for cloud instances."""
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    private_key = Path(identity_file).expanduser()
    public_key = private_key.with_suffix(".pub")
    signed_cert = Path(cert_file).expanduser()
    ssh_config_template = jinja2.Template(ssh_config_template.read())
    await run(
        tld_format=tld_format,
        ssh_config_template=ssh_config_template,
        ssh_config=ssh_config,
        private_key=private_key,
        public_key=public_key,
        signed_cert=signed_cert,
        every=timedelta(seconds=loop_delay) if loop else None,
    )


def main() -> None:
    cli(auto_envvar_prefix=ENV_PREFIX)


if __name__ == "__main__":
    main()
