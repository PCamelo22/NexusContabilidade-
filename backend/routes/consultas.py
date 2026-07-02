# consultas.py — Nexus v1.0
# Proxy para BrasilAPI — evita CORS no browser

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/consultas", tags=["consultas"])

BRASILAPI = "https://brasilapi.com.br/api"


@router.get("/cnpj/{cnpj}")
async def consultar_cnpj(cnpj: str):
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    if len(cnpj_limpo) != 14:
        raise HTTPException(status_code=400, detail="CNPJ inválido")
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(f"{BRASILAPI}/cnpj/v1/{cnpj_limpo}")
    if res.status_code != 200:
        raise HTTPException(status_code=404, detail="CNPJ não encontrado")
    return res.json()


@router.get("/cep/{cep}")
async def consultar_cep(cep: str):
    cep_limpo = "".join(filter(str.isdigit, cep))
    if len(cep_limpo) != 8:
        raise HTTPException(status_code=400, detail="CEP inválido")
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(f"{BRASILAPI}/cep/v1/{cep_limpo}")
    if res.status_code != 200:
        raise HTTPException(status_code=404, detail="CEP não encontrado")
    return res.json()
