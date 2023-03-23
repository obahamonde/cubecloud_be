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

DOCKERFILE = """
FROM python:3.7
ARG LOCAL_PATH
WORKDIR /app
COPY ${LOCAL_PATH}/requirements.txt /app
RUN pip install --upgrade pip \    
    pip install --no-cache-dir -r requirements.txt
COPY ${LOCAL_PATH} /app
CMD ["python", "main.py"]
"""

PYTHON_FILE="""from flask import Flask, jsonify, request
import socket

app = Flask(__name__)

@app.route('/')
def main(): 
    return jsonify({
        "message": "Hello World!",
        "hostname": socket.gethostname(),
        "ip": request.remote_addr
    })
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
        """

app = APIRouter()

async def get_latest_commit_sha(owner: str, repo: str) -> str:
    """


    Gets the SHA of the latest commit in the repository.



    :return: The SHA of the latest commit.
    """

    url = f"https://api.github.com/repos/{owner}/{repo}/commits"

    payload = await fetch(url, headers=HEADERS)
    
    return payload[0]["sha"]

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

async def get_local_tree(sub:str, name:str):
    os.makedirs(f"/containers/{sub}", exist_ok=True)
    os.makedirs(f"/containers/{sub}/{name}", exist_ok=True)
    with open(f"/containers/{sub}/{name}/main.py", "w") as f:
        f.write(PYTHON_FILE)  
    with open(f"/containers/{sub}/{name}/Dockerfile", "w") as f:
        f.write(DOCKERFILE)
    with open(f"/containers/{sub}/{name}/requirements.txt", "w") as f:
        f.write("flask")

    return build_file_tree(f"/containers/{sub}/{name}")["children"]
    
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


async def docker_build_from_tree(tree: Union[List[Dict[str, Any]], Dict[str, Any]]):
    """
    Builds a Docker image from the given file tree.
    :param tree: The file tree.
    :return: The output of the Docker build.
    """
    tarball = io.BytesIO()
    with tarfile.open(fileobj=tarball, mode="w:gz") as tar:
        if isinstance(tree, dict):
            tree = [tree]
        for file in tree:
            if file["type"] == "file":
                tarinfo = tarfile.TarInfo(name=file["name"])
                tarinfo.size = len(file["content"])
                tarinfo.mtime = 0
                tar.addfile(tarinfo, io.BytesIO(file["content"].encode("utf-8")))
            elif file["type"] == "directory":
                tar.addfile(tarfile.TarInfo(name=file["name"] + "/"))
                await docker_build_from_tree(file["children"])
    tarball.seek(0)
    with ClientSession() as session:
        async with session.post(
            f"{env.DOCKER_URL}/build?dockerfile=Dockerfile", data=tarball.read()
        ) as response:
            streamed_data = await response.text()
            id_ = streamed_data.split("Successfully built ")[1].split("\\n")[0]
            return id_
            


@app.get("/tree/{sub}/{name}")
async def get_tree(sub:str, name:str):
    return await get_local_tree(sub, name)

@app.post("/tree/{sub}/{name}")
async def build_container_from_tree(
    sub:str, name:str):
    name = f"{sub}-{name}"
    image = await docker_build_from_tree(await get_local_tree(sub, name))
    return image

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
    if "error" in image:
        return image
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
    try:
        _id = container["Id"]
        await d.start_container(_id)
        res = await cf.create_dns_record(name)
        nginx_config = Template(NGINX_CONFIG).render(id=name, port=port)
        for path in ["/etc/nginx/conf.d","/etc/nginx/sites-enabled",
    "/etc/nginx/sites-available"]:
            os.remove(f"{path}/{name}.conf")
            with open(f"{path}/{name}.conf", "w") as f:
                f.write(nginx_config)
        os.system("nginx -s reload")
        data = await d.get_container(_id)
        return {
            "url": f"{name}.smartpro.solutions",
            "port": host_port,
            "container": data,
            "dns": res,
        }
    except KeyError:
        return container