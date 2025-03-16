import uvicorn
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response

# Configuración del backend al que el proxy redirige las solicitudes
BACKEND_URL = "http://10.128.0.63:8080"  # Dirección interna del app-server en GCP

app = FastAPI()

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(full_path: str, request: Request):
    """ Proxy inverso que redirige las solicitudes a app-server """
    async with httpx.AsyncClient() as client:
        url = f"{BACKEND_URL}/{full_path}"
        headers = dict(request.headers)

        if request.method == "GET":
            response = await client.get(url, headers=headers)
        elif request.method == "POST":
            response = await client.post(url, content=await request.body(), headers=headers)
        elif request.method == "PUT":
            response = await client.put(url, content=await request.body(), headers=headers)
        elif request.method == "DELETE":
            response = await client.delete(url, headers=headers)
        elif request.method == "PATCH":
            response = await client.patch(url, content=await request.body(), headers=headers)
        elif request.method == "OPTIONS":
            response = await client.options(url, headers=headers)
        elif request.method == "HEAD":
            response = await client.head(url, headers=headers)
        else:
            return Response("Método no soportado", status_code=405)

        return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))

if __name__ == "__main__":
    # Se inicia el proxy en 0.0.0.0 para aceptar tráfico externo
    uvicorn.run(app, host="0.0.0.0", port=443, ssl_keyfile="privkey.pem", ssl_certfile="fullchain.pem")

