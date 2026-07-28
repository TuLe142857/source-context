from dataclasses import dataclass
from typing import Callable
import tarfile
import io
import docker
from docker import DockerClient  # type: ignore[attr-defined]
from docker.types import Mount  # type: ignore[import-not-found]
from docker.models.containers import Container  # type: ignore[import-not-found]

from functools import lru_cache


@lru_cache
def get_docker_client() -> DockerClient:
    """Docker Client singleton"""
    return docker.from_env()  # type: ignore[attr-defined]


@dataclass(frozen=True, kw_only=True)
class SCIPSandbox:
    language: str
    """Language name"""

    command_builder: Callable[[str, str], str]
    """
    Callable (project_path, output_path) -> command.
    Use to generate command to run in docker container
    """

    image_tags: list[str]
    """Docker image tags"""

    def __post_init__(self) -> None:
        docker_client = get_docker_client()
        all_images = docker_client.images.list()
        all_tags = [t for image in all_images for t in image.tags]
        for tag in self.image_tags:
            if tag not in all_tags:
                raise ValueError(f"Image tags not found in local device: '{tag}'")

    @staticmethod
    def read_file_in_container(container: Container, file_path: str) -> bytes | None:
        raw_tar, stats = container.get_archive(file_path)
        file_stream = io.BytesIO()
        for chunk in raw_tar:
            file_stream.write(chunk)

        file_stream.seek(0)
        with tarfile.open(fileobj=file_stream) as tar:
            member = tar.getmembers()[0]
            extracted_file = tar.extractfile(member)
            if extracted_file is None:
                return None
            raw_bytes = extracted_file.read()
            return raw_bytes

    def index(self, project_path: str, image_tag: str | None = None) -> bytes:
        """
        Run SCIP indexing for a project inside a Docker container.

        This method follows the Docker-out-of-Docker (DooD) pattern:
            - The process calling this method is itself running inside a
              Docker container (e.g. a backend or worker container).
            - That container has the host machine's Docker socket mounted,
              allowing it to control containers on the host's Docker daemon
              via the Docker Python SDK.
            - The container also has a named volume mounted, pointing to
              where repositories are stored on the host.
            - The name of this named volume corresponds to
              ``settings.repository_workspace_root``.

        Args:
            project_path: Path to the project, relative to
                ``settings.repository_workspace_root``.
            image_tag: Tag of the Docker image to use for indexing. If
                ``None``, the first tag in ``self.image_tags`` is used.

        Returns:
            bytes: Contents of the generated SCIP index file (``index.scip``).

        Raises:
            ValueError: If ``image_tag`` is provided but is not found in
                ``self.image_tags``.
            RuntimeError: If the indexing container exits with a non-zero
                status code, or if the generated index file cannot be read
                from the container.

        Example:
            Given:
                - ``settings.repository_workspace_root`` = "/repository-workspaces"
                - The repository is stored at "/repository-workspaces/repo_name"
                - The repository contains a project "backend/"

            Then ``project_path`` should be "repo_name/backend".
        """
        if image_tag is None:
            image_tag = self.image_tags[0]
        else:
            if image_tag not in self.image_tags:
                raise ValueError(f"Image tag not found in local device: '{image_tag}'")

        docker_client = get_docker_client()
        container = None

        try:
            mounts = [
                Mount(
                    target="/sandbox/projects/",
                    source="workspace_repo",
                    type="volume",
                    read_only=True,
                )
            ]

            container = docker_client.containers.run(
                image=image_tag,
                command=self.command_builder(
                    f"/sandbox/projects/{project_path}", "/sandbox/output/index.scip"
                ),
                mounts=mounts,
                detach=True,
                working_dir=f"/sandbox/projects/{project_path}",
            )

            result = container.wait()
            status_code = result.get("StatusCode", -1)
            if status_code != 0:
                raise RuntimeError(
                    f"Container run failed. Command={self.command_builder(f'/sandbox/projects/{project_path}', '/sandbox/output/index.scip')} Logs={container.logs()}"
                )

            index_bytes = self.read_file_in_container(
                container, "/sandbox/output/index.scip"
            )
            if index_bytes is None:
                raise RuntimeError("indexing error")
            return index_bytes
        finally:
            if container is not None:
                container.remove(force=True, v=True)


class SCIPSandboxRegistry:
    def __init__(self, sandboxes: list[SCIPSandbox] | tuple[SCIPSandbox, ...]) -> None:
        self._sandboxes = {sandbox.language: sandbox for sandbox in sandboxes}

    def get_available_language(self) -> list[str]:
        return list(self._sandboxes.keys())

    def get_sandbox(self, language: str) -> SCIPSandbox | None:
        return self._sandboxes.get(language)


@lru_cache
def get_scip_sandbox_registry() -> SCIPSandboxRegistry:
    sandboxes = (
        SCIPSandbox(
            language="python",
            image_tags=[
                "sandbox/python310:latest",
                "sandbox/python311:latest",
                "sandbox/python312:latest",
                "sandbox/python313:latest",
                "sandbox/python314:latest",
            ],
            command_builder=lambda project_path, output_path: (
                f"scip-python index --output {output_path}"
            ),
        ),
        # Currently java have some error when config sandboxes
        # SCIPSandbox(
        #     language="java",
        #     image_tags=[
        #         "sandbox/java21:latest",
        #         "sandbox/java25:latest",
        #     ],
        #     command_builder=lambda project_path, output_path: (
        #         f"scip-java index --output {output_path}"
        #     ),
        # ),
        SCIPSandbox(
            language="javascript",
            image_tags=["sandbox/node24:latest"],
            command_builder=lambda project_path, output_path: (
                f"scip-typescript index --output {output_path}"
            ),
        ),
        SCIPSandbox(
            language="typescript",
            image_tags=["sandbox/node24:latest"],
            command_builder=lambda project_path, output_path: (
                f"scip-typescript index --output {output_path}"
            ),
        ),
    )
    return SCIPSandboxRegistry(sandboxes)
