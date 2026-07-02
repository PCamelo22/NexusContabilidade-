# consultas.py — Nexus v1.0
# Proxy para BrasilAPI — evita CORS no browser

import httpx
from fastapi import APIRouter, HTTPException
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/consultas", tags=["consultas"])

BRASILAPI = "https://brasilapi.com.br/api"


@router.get("/cnpj/{cnpj}")
async def consultar_cnpj(cnpj: str):
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    if len(cnpj_limpo) != 14:
        raise HTTPException(status_code=400, detail="CNPJ inválido")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(f"{BRASILAPI}/cnpj/v1/{cnpj_limpo}")
        logger.info(f"BrasilAPI CNPJ status: {res.status_code}")
        if res.status_code != 200:
            logger.warning(f"BrasilAPI CNPJ error body: {res.text[:200]}")
            raise HTTPException(status_code=404, detail="CNPJ não encontrado")
        return res.json()
    except httpx.TimeoutException:
        logger.error("Timeout ao consultar CNPJ na BrasilAPI")
        raise HTTPException(status_code=504, detail="Timeout ao consultar CNPJ")
    except httpx.RequestError as e:
        logger.error(f"Erro de rede ao consultar CNPJ: {e}")
        raise HTTPException(status_code=502, detail="Erro de conexão com BrasilAPI")


@router.get("/cep/{cep}")
async def consultar_cep(cep: str):
    cep_limpo = "".join(filter(str.isdigit, cep))
    if len(cep_limpo) != 8:
        raise HTTPException(status_code=400, detail="CEP inválido")
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.get(f"{BRASILAPI}/cep/v1/{cep_limpo}")
        if res.status_code != 200:
            raise HTTPException(status_code=404, detail="CEP não encontrado")
        return res.json()
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout ao consultar CEP")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail="Erro de conexão com BrasilAPI")
