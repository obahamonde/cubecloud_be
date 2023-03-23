import os
import io
import json
import tarfile
from typing import Any, Dict, Optional, Union, List
from aiohttp import ClientSession
from fastapi import APIRouter
from jinja2 import Template
from src.config import env, fetch
from src.utils import build_file_tree, gen_port
from src.api import cloudflare as cf
from src.api import docker as d

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {env.GH_API_KEY}",
}


NGINX_CONFIG = """server {
    listen 80;
    server_name {{ id }}.smartpro.solutions;

    location / {
        proxy_pass http://{{ id }}:{{ port }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
}"""

app = APIRouter()

async def get_latest_commit_sha(owner: str, repo: str) -> str:
    """


    Gets the SHA of the latest commit in the repository.



    :return: The SHA of the latest commit.
    """

    url = f"https://api.github.com/repos/{owner}/{repo}/commits"

    payload = await fetch(url, headers=HEADERS)
    
    return payload[0]["sha"]

@app.get("/clone")
async def git_clone(owner: str, repo: str):
    async with ClientSession() as session:
        sha = await get_latest_commit_sha(owner, repo)
        async with session.get(
            f"https://api.github.com/repos/{owner}/{repo}/tarball", headers=HEADERS
        ) as response:
            response.raise_for_status()
            content = await response.read()
            tarball = tarfile.open(fileobj=io.BytesIO(content), mode="r:gz")
            os.makedirs(f"/containers/{sha}", exist_ok=True)
            tarball.extractall(path=f"/containers/{sha}")
            return build_file_tree(f"/containers/{sha}")["children"][0]["children"]


async def docker_build_from_github_tarball(owner: str, repo: str):
    """
    Builds a Docker image from the latest code for the given GitHub repository.
    :param owner: The owner of the repository.
    :param repo: The name of the repository.
    :return: The output of the Docker build.
    """
    async with ClientSession() as session:
        sha = await get_latest_commit_sha(owner, repo)
        async with session.get(
            f"https://api.github.com/repos/{owner}/{repo}/tarball", headers=HEADERS
        ) as response:
            response.raise_for_status()
            local_path = f"{owner}-{repo}-{sha[:7]}"
            build_args = json.dumps({"LOCAL_PATH": local_path})
            content = await response.read()
            async with session.post(
                f"{env.DOCKER_URL}/build?dockerfile={local_path}/Dockerfile&buildargs={build_args}",
                data=content,
            ) as response:
                streamed_data = await response.text()
                id_ = streamed_data.split("Successfully built ")[1].split("\\n")[0]
                return id_

async def build_from_tree(tree: Union[List[Dict[str, Any]], Dict[str, Any]]):
    """
    Builds a Docker image from the given file tree.
    :param tree: The file tree.
    :return: The output of the Docker build.
    """
    if isinstance(tree, list):
        for item in tree:
            await build_from_tree(item)
    else:
        if tree["type"] == "file":
            with open(tree["path"], "w") as f:
                f.write(tree["content"])
        else:
            os.makedirs(tree["path"], exist_ok=True)
            await build_from_tree(tree["children"])
    

@app.post("/build/{owner}/{repo}")
async def build(owner: str, repo: str):
    """
    Builds a Docker image from the latest code for the given GitHub repository.
    :param owner: The owner of the repository.
    :param repo: The name of the repository.
    :return: The output of the Docker build.
    """
    return await docker_build_from_github_tarball(owner, repo)


@app.get("/clone/{owner}/{repo}")
async def git_clone_endpoint(owner: str, repo: str):
    return await git_clone(owner, repo)

@app.post("/deploy/{owner}/{repo}")
async def deploy_container_from_repo(
    owner:str, repo:str, port: int = 8080, env_vars: str = "DOCKER=1"
):
    name = f"{owner}-{repo}"
    image = await docker_build_from_github_tarball(owner, repo)
    host_port = str(gen_port())
    payload = {
        "Image": image,
        "Env": env_vars.split(" "),
        "ExposedPorts": {f"{str(port)}/tcp": {"HostPort": host_port}},
        "HostConfig": {"PortBindings": {f"{str(port)}/tcp": [{"HostPort": host_port}]}},
    }
    container = await fetch(
        f"{env.DOCKER_URL}/containers/create?name={name}",
        "POST",
        headers={"Content-Type": "application/json"},
        json=payload,
    )
    print(container)
    return container