from fastapi import APIRouter
from src.api.docker import (
    create_container,
    delete_container,
    get_container,
    get_container_logs,
    get_container_stats,
    get_containers,
    ContainerConfig,
    fetch,
    env
)

app = APIRouter()


#@app.put("/containers/{container}/start", tags=["containers"])
async def start_container_by_id(container: str):
    return await fetch(f"{env.DOCKER_URL}/containers/{container}/start", "POST")

#@app.put("/containers/{container}/stop", tags=["containers"])
async def stop_container_by_id(container: str):
    return await fetch(f"{env.DOCKER_URL}/containers/{container}/stop", "POST")

#@app.put("/containers/{container}/restart", tags=["containers"])
async def restart_container_by_id(container: str):
    return await fetch(f"{env.DOCKER_URL}/containers/{container}/restart", "POST")


@app.get("/containers", tags=["containers"])
async def get_all_containers():
    return await get_containers()

@app.get("/containers/{container}", tags=["containers"])
async def get_container_by_id(container: str):
    return await get_container(container)

#@app.get("/containers/{container}/logs", tags=["containers"])
async def get_container_logs_by_id(container: str):
    return await get_container_logs(container)

#@app.get("/containers/{container}/stats", tags=["containers"])
async def get_container_stats_by_id(container: str):
    return await get_container_stats(container)

@app.post("/containers", tags=["containers"])
async def create_new_container(name: str, config: ContainerConfig):
    container = await create_container(name, config)
    try:
        _id = container["Id"]
        await start_container_by_id(_id)
        return await get_container(_id)
    except:
        return container
    
@app.delete("/containers/{container}", tags=["containers"])
async def delete_container_by_id(container: str):
    await stop_container_by_id(container)
    return await delete_container(container)
