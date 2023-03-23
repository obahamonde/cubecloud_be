import asyncio
from typing import *
from aiohttp import ClientSession
from src.config import env, fetch
from pydantic import BaseModel, Field

class ContainerConfig(BaseModel):
    image: str = Field(..., example="ubuntu")
    shell: str = Field(..., example="/bin/bash")
    cmd: str = Field(..., example="echo hello world")
    environment: List[str] = Field(..., example=["FOO=bar"])
    container_port: int = Field(..., example=8080)
    host_port: int = Field(..., example=8080)
    protocol: str = Field(default="tcp", example="tcp")


async def pull_image(image: str):
    return await fetch(f"{env.DOCKER_URL}/images/create?fromImage={image}", "POST")

async def start_container(container: str):
    return await fetch(f"{env.DOCKER_URL}/containers/{container}/start", "POST")

async def get_container(container: str):
    return await fetch(f"{env.DOCKER_URL}/containers/{container}/json")

async def get_container_logs(container: str):
    return await fetch(f"{env.DOCKER_URL}/containers/{container}/logs?stdout=1&stderr=1")

async def get_containers() -> List[Dict[str, Any]]:
    containers = await fetch(f"{env.DOCKER_URL}/containers/json?all=1")

    return await asyncio.gather(
        *[get_container(container["Id"]) for container in containers]
    )

async def create_container(name: str, container: ContainerConfig) -> Dict[str, Any]:
    """
    Creates a new Docker container with the specified name and configuration.
    Args:
    - name: The name to assign to the new container
    - container: An object representing the configuration of the new container, with the following fields:
        - image: The name of the Docker image to use
        - shell: The shell to use inside the container (e.g. "/bin/bash")
        - cmd: The command to run inside the container
        - environment: A list of environment variables to set inside the container
        - container_port: The port number to expose on the container
        - host_port: The port number to map the container port to on the Docker host
        - protocol: The protocol to use (e.g. "tcp")

    Returns:
        A dictionary representing the newly created container, with the following fields:
        - Id: The container's unique identifier
        - Name: The container's name
        - Image: The name of the image used to create the container
        - State: The container's current state (running, stopped, etc.)
        - Created: The timestamp of when the container was created
        - Ports: A list of port mappings for the container
        - Labels: A dictionary of key-value pairs representing metadata about the container
    """

    payload = {
        "Image": container.image,
        "Shell": container.shell,
        "Cmd": container.cmd,
        "Env": container.environment,
        "ExposedPorts": {
            f"{container.container_port}/{container.protocol}": {
                "HostPort": str(container.host_port)
            }
        },
        "HostConfig": {
            "PortBindings": {
                f"{container.container_port}/{container.protocol}": [
                    {"HostPort": str(container.host_port)}
                ]
            }
        },
    }
    async with ClientSession() as session:
        async with session.post(
            f"{env.DOCKER_URL}/containers/create?name={name}", json=payload
        ) as response:
            image_status = await pull_image(container.image)
            if image_status["status"] == "success":
                id_ = (await response.json())["Id"]
                await start_container(id_)
                return await get_container(id_)
            else:
                return image_status

async def delete_container(container: str):
    async with ClientSession() as session:
        async with session.delete(
            f"{env.DOCKER_URL}/containers/{container}"
        ) as response:
            if response.status == status.HTTP_204_NO_CONTENT:
                return {
                    "message": "Container deleted",
                    "status": "success",
                }
            else:
                return {
                    "message": "Something went wrong",
                    "status": "error",
                }

async def get_container_stats(container: str) -> Dict[str, Any]:
    """
    Returns statistics about the specified Docker container.

    Args:
    - container: The name or ID of the container to get statistics for

    Returns:
    A dictionary containing various statistics about the container, including:
    - CPU usage
    - Memory usage
    - Network I/O
    - Block I/O
    """

    async with ClientSession() as session:
        async with session.get(
            f"{env.DOCKER_URL}/containers/{container}/stats?stream=0"
        ) as response:
            return await response.json()
        
        