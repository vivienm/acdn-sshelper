import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Collection, Iterable

from . import aioproc


@dataclass(frozen=True)
class Vault:
    vault_bin: str = "vault"
    vault_opts: Collection[str] = ()

    async def run(self, args: Iterable[str], **kwargs) -> subprocess.CompletedProcess:
        return await aioproc.run([self.vault_bin, *self.vault_opts, *args], **kwargs)

    async def sign_key(self, public_key: Path, signed_cert: Path):
        vault_proc = await self.run(
            [
                "write",
                "-field=signed_key",
                "ssh-client-signer/sign/admin",
                f"public_key=@{public_key}",
            ],
            text=False,
            stdout=subprocess.PIPE,
        )
        cert_data = vault_proc.stdout
        with os.fdopen(
            os.open(signed_cert, os.O_WRONLY | os.O_CREAT, 0o600),
            "wb",
        ) as cert_file:
            cert_file.write(cert_data)
