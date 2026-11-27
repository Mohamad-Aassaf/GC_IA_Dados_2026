"""
API Casa de Sucos
Integra com a API pública Fruityvice para calcular os valores nutricionais dos sucos.
Valores considerados: 100 g de cada fruta informada.
"""

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

FRUITYVICE_URL = "https://www.fruityvice.com/api/fruit"

app = FastAPI(
    title="API Casa de Sucos",
    description="Cadastro de sucos com informações nutricionais obtidas da API Fruityvice "
    "(considerando 100 g de cada fruta).",
    version="1.0.0",
)


class Fruta(BaseModel):
    nome: str
    calorias: float
    acucar: float


class SucoEntrada(BaseModel):
    nome: str = Field(..., examples=["Vitamina Tropical"])
    frutas: list[str] = Field(..., min_length=1, examples=[["banana", "strawberry"]])
    tem_gosto_de: str = Field(..., examples=["Tamarindo"])


class SucoAtualizacao(BaseModel):
    frutas: list[str] = Field(..., min_length=1, examples=[["mango", "orange"]])


class Suco(BaseModel):
    id: int
    nome: str
    frutas: list[str]
    tem_gosto_de: str
    total_calorias: float
    total_acucar: float


sucos: list[Suco] = []
proximo_id = 1


def buscar_fruta(nome: str) -> Fruta:
    """Consulta uma fruta na Fruityvice e devolve apenas nome, calorias e açúcar."""
    try:
        resposta = httpx.get(f"{FRUITYVICE_URL}/{nome.strip().lower()}", timeout=10)
    except httpx.RequestError:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar à API Fruityvice. Tente novamente mais tarde.",
        )

    if resposta.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail=f"A fruta '{nome}' não foi encontrada. "
            "Verifique o nome (use o nome em inglês, ex.: 'strawberry').",
        )
    if resposta.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="A API Fruityvice retornou um erro inesperado.",
        )

    dados = resposta.json()
    nutricao = dados.get("nutritions", {})
    return Fruta(
        nome=dados["name"],
        calorias=nutricao.get("calories", 0),
        acucar=nutricao.get("sugar", 0),
    )


def calcular_nutricao(frutas: list[str]) -> tuple[float, float]:
    """Soma calorias e açúcar de todas as frutas (100 g de cada)."""
    infos = [buscar_fruta(f) for f in frutas]
    total_calorias = round(sum(f.calorias for f in infos), 2)
    total_acucar = round(sum(f.acucar for f in infos), 2)
    return total_calorias, total_acucar


def encontrar_suco(suco_id: int) -> Suco:
    for suco in sucos:
        if suco.id == suco_id:
            return suco
    raise HTTPException(status_code=404, detail=f"Suco com id {suco_id} não encontrado.")


# Edpoints

@app.get("/", tags=["Início"])
def inicio():
    return {"mensagem": "Bem-vindo à API Casa de Sucos! Acesse /docs para o Swagger."}


@app.get("/frutas/{nome}", response_model=Fruta, tags=["Frutas"])
def consultar_fruta(nome: str):
    """Consulta uma fruta na Fruityvice (valores por 100 g)."""
    return buscar_fruta(nome)


@app.post("/sucos", response_model=Suco, status_code=201, tags=["Sucos"])
def cadastrar_suco(entrada: SucoEntrada):
    """Cadastra um suco e calcula calorias e açúcar totais."""
    global proximo_id
    total_calorias, total_acucar = calcular_nutricao(entrada.frutas)

    suco = Suco(
        id=proximo_id,
        nome=entrada.nome,
        frutas=[f.strip().lower() for f in entrada.frutas],
        tem_gosto_de=entrada.tem_gosto_de,
        total_calorias=total_calorias,
        total_acucar=total_acucar,
    )
    sucos.append(suco)
    proximo_id += 1
    return suco


@app.get("/sucos", response_model=list[Suco], tags=["Sucos"])
def listar_sucos():
    """Lista todos os sucos cadastrados."""
    return sucos


@app.put("/sucos/{suco_id}", response_model=Suco, tags=["Sucos"])
def atualizar_suco(suco_id: int, atualizacao: SucoAtualizacao):
    """(Bônus) Atualiza as frutas de um suco e recalcula os valores nutricionais."""
    suco = encontrar_suco(suco_id)
    total_calorias, total_acucar = calcular_nutricao(atualizacao.frutas)

    suco.frutas = [f.strip().lower() for f in atualizacao.frutas]
    suco.total_calorias = total_calorias
    suco.total_acucar = total_acucar
    return suco
