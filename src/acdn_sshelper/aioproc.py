import asyncio
import io
import subprocess
from typing import Union


async def run(
    args,
    text=True,
    check=True,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Run a subprocess command, with a decent API."""
    proc = await asyncio.create_subprocess_exec(*args, **kwargs)
    stdout: Union[str, bytes, None]
    stderr: Union[str, bytes, None]
    stdout, stderr = await proc.communicate()
    assert proc.returncode is not None

    if text:
        if stdout is not None:
            stdout = io.TextIOWrapper(io.BytesIO(stdout)).read()
        if stderr is not None:
            stderr = io.TextIOWrapper(io.BytesIO(stderr)).read()

    if check and (proc.returncode != 0):
        raise subprocess.CalledProcessError(proc.returncode, args, stdout, stderr)

    return subprocess.CompletedProcess(args, proc.returncode, stdout, stderr)
