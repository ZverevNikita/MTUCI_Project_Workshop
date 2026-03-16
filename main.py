from fastapi import FastAPI
from pywebio.platform.fastapi import webio_routes
import uvicorn
from ip_identifier import get_local_ip
from routes import router
from chat import main

app = FastAPI()
app.include_router(router)
app.routes.extend(webio_routes(main))

if __name__ == "__main__":
    ip = get_local_ip()
    uvicorn.run(app, host=ip, port=8080)