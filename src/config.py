from pydantic import BaseSettings, Field, BaseConfig
import aiohttp
from typing import Dict, Optional, Any

async def fetch(    
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[bytes] = None,
    json: Optional[Dict[str, Any]] = None,
) -> Any:
    async with aiohttp.ClientSession() as session:
        async with session.request(
            method=method, url=url, headers=headers, data=body,
            json=json
        ) as response:
            if response.content_type.endswith("json"):
                return await response.json()
            if response.content_type.startswith("text/"):
                return await response.text()
            return await response.read()    

class Settings(BaseSettings):
    CF_API_KEY: str = Field(..., env="CF_API_KEY")
    CF_EMAIL: str = Field(..., env="CF_EMAIL")
    CF_ZONE_ID: str = Field(..., env="CF_ZONE_ID")
    GH_API_KEY: str = Field(..., env="GH_API_KEY")
    DOCKER_URL: str = Field(..., env="DOCKER_URL")
    DOCKER_IP: str = Field(..., env="DOCKER_IP")
    
    class Config(BaseConfig):
        env_file = ".env"
        env_file_encoding = "utf-8"

env:Any = Settings()

