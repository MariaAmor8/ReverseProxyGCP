import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()

@app.get("/")
def root():
    return FileResponse("index.html")

if __name__ == "__main__":
    # Configuración para permitir acceso externo
    uvicorn.run(app, host="0.0.0.0", port=8080)
