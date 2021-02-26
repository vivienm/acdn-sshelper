from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import (
    Any,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    TextIO,
    Tuple,
)

import jinja2

from .gcloud import Account, Instance, Project, Zone


@lru_cache
def jumphost_user(account: Account) -> str:
    return "".join(("_" if c in "@." else c) for c in account)


def get_jumphosts(
    project: Project,
    instances: Iterable[Instance],
) -> Dict[Instance, Instance]:
    jumphost_prefixes = {}
    for instance in instances:
        parts = instance.name.split("-")
        if len(parts) >= 3 and parts[-2] == "jumphost":
            prefix = "-".join(parts[:-2])
            jumphost_prefixes[prefix] = instance

    jumphosts = {}
    for instance in instances:
        for prefix, jumphost in jumphost_prefixes.items():
            if instance.name.startswith(f"{prefix}-"):
                jumphosts[instance] = jumphost
                break
        else:
            jumphosts[instance] = jumphost_prefixes[project.name.lower()]
    return jumphosts


@dataclass(frozen=True)
class SSHConfigDumper:
    private_key: Path
    signed_cert: Path
    runtime_dir: Path
    tld_format: str
    ssh_config_template: jinja2.Template

    @lru_cache
    def get_tld(self, project: Project, zone: Zone) -> str:
        return self.tld_format.format(
            project_id=project.id_,
            project_name=project.name,
            project_slug=project.name.lower(),
            zone=zone,
        )

    def _iter_instances_aliases(
        self,
        instances: Collection[Instance],
    ) -> Iterator[Tuple[Instance, List[str]]]:
        alias_map = defaultdict(list)  # Map alias candidates to instances.
        for instance in instances:
            tokens = instance.name.split("-")
            while tokens:
                alias = "-".join(tokens)
                alias_map[alias].append(instance)
                tokens.pop()

        name_map = defaultdict(list)  # Map instance names to aliases.
        for alias, alias_instances in alias_map.items():
            if len(alias_instances) == 1:
                alias_instance = alias_instances[0]
            else:  # Alias is ambiguous.
                try:
                    # Corner case: alias is the exact name of an instance.
                    alias_instance = next(
                        instance
                        for instance in alias_instances
                        if instance.name == alias
                    )
                except StopIteration:
                    continue
            name_map[alias_instance.name].append(alias)

        for instance in instances:
            aliases = name_map[instance.name]
            aliases.sort()
            yield instance, aliases

    def _get_instance_vars(
        self,
        project: Project,
        aliases: Mapping[Instance, Collection[str]],
        instance: Instance,
        jumphost: Instance,
    ) -> Dict[str, Any]:
        tld = self.get_tld(project, instance.zone)
        is_jumphost = jumphost is instance
        vars = {
            "is_jumphost": is_jumphost,
            "host": f"{instance.name}{tld}",
            "host_aliases": [f"{alias}{tld}" for alias in aliases[instance]],
            "external_ip": instance.external_ip,
            "internal_ip": instance.internal_ip,
        }
        if jumphost is not instance:
            vars["jumphost"] = self._get_instance_vars(
                project=project,
                aliases=aliases,
                instance=jumphost,
                jumphost=jumphost,
            )
        return vars

    def dump(
        self,
        account: Account,
        projects: Iterable[Tuple[Project, Collection[Instance]]],
        ssh_config: TextIO,
    ) -> None:
        jh_user = jumphost_user(account)
        template_vars: Dict[str, Any] = {
            "now": datetime.now(),
            "runtime_dir": str(self.runtime_dir),
            "projects": [],
            "account": {"name": account, "ssh_user": jh_user},
            "private_key": str(self.private_key),
            "signed_cert": str(self.signed_cert),
        }
        for project, instances in projects:
            aliases = {
                instance: aliases
                for instance, aliases in self._iter_instances_aliases(instances)
            }
            jumphosts = get_jumphosts(project, instances)
            template_vars["projects"].append(
                {
                    "name": project.name,
                    "id": project.id_,
                    "instances": [
                        self._get_instance_vars(
                            project=project,
                            aliases=aliases,
                            instance=instance,
                            jumphost=jumphosts[instance],
                        )
                        for instance in instances
                    ],
                },
            )
        ssh_config.write(self.ssh_config_template.render(**template_vars))
