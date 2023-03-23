__name__ = 'cubecloud'
__version__ = '0.1.0'
__author__ = '@obahamonde'  

from fastapi import FastAPI
from src.router import containers, workers, domains, build

def create_app():
    app = FastAPI(
        title='CubeCloud',
        description='CubeCloud is a cloud computing platform that allows you to run your own cloud.',
        version=__version__,
        docs_url='/'
       
    )
    
    app.include_router(build.app, prefix='/build', tags=['build'])
    app.include_router(containers.app, prefix='/containers', tags=['containers'])
    app.include_router(workers.app, prefix='/workers', tags=['workers'])
    app.include_router(domains.app, prefix='/domains', tags=['domains'])
    
    return app