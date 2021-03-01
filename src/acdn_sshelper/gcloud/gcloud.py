import json
import subprocess
from dataclasses import dataclass
from ipaddress import IPv4Address
from typing import Collection, Iterable, List

from .. import aioproc
from .account import Account
from .instance import Instance
from .project import Project
from .zone import Zone


@dataclass(frozen=True)
class GCloud:
    gcloud_bin: str = "gcloud"
    gcloud_opts: Collection[str] = ()

    async def run(self, args: Iterable[str], **kwargs) -> subprocess.CompletedProcess:
        return await aioproc.run([self.gcloud_bin, *self.gcloud_opts, *args], **kwargs)

    async def get_account(self) -> Account:
        proc = await self.run(
            [
                "--format=json(account)",
                "auth",
                "list",
                "--filter=status:ACTIVE",
            ],
            stdout=subprocess.PIPE,
        )
        return Account(json.loads(proc.stdout)[0]["account"])

    async def get_projects(self) -> List[Project]:
        proc = await self.run(
            [
                "--format=json(projectId, name)",
                "projects",
                "list",
            ],
            stdout=subprocess.PIPE,
        )
        return [
            Project(id_=project_data["projectId"], name=project_data["name"])
            for project_data in json.loads(proc.stdout)
        ]

    async def get_project_instances(self, project: Project) -> List[Instance]:
        proc = await self.run(
            [
                "--project={}".format(project.id_),
                "--format=json({})".format(
                    ", ".join(
                        [
                            "name",
                            "zone.scope()",
                            "networkInterfaces[0].networkIP",
                            "networkInterfaces[0].accessConfigs[0].natIP",
                        ],
                    ),
                ),
                "compute",
                "instances",
                "list",
            ],
            stdout=subprocess.PIPE,
        )
        return [
            Instance(
                name=instance_data["name"],
                zone=Zone(instance_data["zone"]),
                internal_ip=IPv4Address(
                    instance_data["networkInterfaces"][0]["networkIP"],
                ),
                external_ip=(
                    None
                    if "accessConfigs" not in instance_data["networkInterfaces"][0]
                    else IPv4Address(
                        instance_data["networkInterfaces"][0]["accessConfigs"][0][
                            "natIP"
                        ],
                    )
                ),
            )
            for instance_data in json.loads(proc.stdout)
            if "networkInterfaces" in instance_data
        ]
