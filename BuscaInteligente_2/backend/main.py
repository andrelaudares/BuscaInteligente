from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional
import io

# Importações dos módulos locais
from models.schemas import Product
from services import search_service

app = FastAPI(title="Busca Inteligente API", version="0.1.0")

# Configurar CORS (ajuste a origem conforme necessário para seu frontend)
# Se o frontend rodar na mesma máquina na porta 3000: "http://localhost:3000"
# Se for HTML estático aberto direto no navegador, pode precisar de "*" ou "null" (menos seguro)
origins = [
    "http://localhost:3000", # Exemplo: React Dev Server
    "http://127.0.0.1:5500", # Exemplo: Live Server VSCode
    "null" # Para arquivos HTML abertos localmente (file://)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"], # Permitir apenas GET conforme escopo
    allow_headers=["*"]
)

# --- Endpoints da API ---

@app.get("/search", response_model=List[Product], summary="Busca de Produtos")
async def search_products(
    q: str = Query(..., description="Termo de busca para o suplemento"),
    min_price: Optional[float] = Query(None, description="Preço mínimo"),
    max_price: Optional[float] = Query(None, description="Preço máximo"),
    brands: Optional[List[str]] = Query(None, description="Lista de marcas para filtrar"),
    marketplaces: Optional[List[str]] = Query(None, description="Lista de lojas para buscar"),
    sort_by: Optional[str] = Query(None, description="Campo para ordenação (ex: price, name)"),
    order: Optional[str] = Query("asc", description="Ordem da ordenação (asc ou desc)")
):
    """
    Realiza a busca de suplementos com base nos filtros fornecidos.
    """
    try:
        # Chama o serviço para obter os resultados
        results_data = search_service.get_search_results(
            query=q,
            min_price=min_price,
            max_price=max_price,
            brands=brands or [],
            marketplaces=marketplaces or [],
            sort_by=sort_by,
            order=order
        )
        # Converte os dicionários para o modelo Pydantic Product
        products = [Product(**item) for item in results_data]
        return products
    except Exception as e:
        # Em produção, logar o erro `e`
        print(f"Erro em /search: {e}") # Log simplificado para console
        raise HTTPException(status_code=500, detail="Ocorreu um erro interno ao processar a busca.")

@app.get("/export", summary="Exporta Resultados para CSV")
async def export_results_to_csv(
    q: str = Query(..., description="Termo de busca para o suplemento"),
    min_price: Optional[float] = Query(None, description="Preço mínimo"),
    max_price: Optional[float] = Query(None, description="Preço máximo"),
    brands: Optional[List[str]] = Query(None, description="Lista de marcas para filtrar"),
    marketplaces: Optional[List[str]] = Query(None, description="Lista de lojas para buscar"),
    sort_by: Optional[str] = Query(None, description="Campo para ordenação (ex: price, name)"),
    order: Optional[str] = Query("asc", description="Ordem da ordenação (asc ou desc)")
):
    """
    Retorna os resultados da busca formatados como um arquivo CSV.
    """
    try:
        # 1. Obter os resultados (reutiliza a lógica de busca)
        results_data = search_service.get_search_results(
            query=q,
            min_price=min_price,
            max_price=max_price,
            brands=brands or [],
            marketplaces=marketplaces or [],
            sort_by=sort_by,
            order=order
        )

        # 2. Gerar o conteúdo CSV usando o serviço
        csv_content = search_service.generate_csv_data(results_data)

        # 3. Preparar a resposta para download
        file_name = f"busca_suplementos_{q.replace(' ', '_')}.csv"
        csv_bytes = io.BytesIO(csv_content.encode('utf-8'))

        return StreamingResponse(
            iter([csv_bytes.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={file_name}"}
        )
    except Exception as e:
        print(f"Erro em /export: {e}") # Log simplificado
        raise HTTPException(status_code=500, detail="Ocorreu um erro interno ao gerar o CSV.")

@app.get("/marketplaces", response_model=List[str], summary="Lista de Lojas Disponíveis")
async def get_marketplaces():
    """
    Retorna a lista de nomes das lojas/marketplaces suportados pela busca.
    """
    try:
        return search_service.get_available_marketplaces()
    except Exception as e:
        print(f"Erro em /marketplaces: {e}") # Log simplificado
        raise HTTPException(status_code=500, detail="Erro ao obter lista de lojas.")

# Rota /brands é mais complexa pois depende dos resultados da busca.
# Poderia ser um endpoint separado que retorna todas as marcas já vistas
# ou as marcas *filtradas* após uma busca.
# Vamos implementar retornando marcas dos resultados de uma busca específica.
# Uma alternativa seria ter uma lista pré-definida ou que é atualizada.
@app.get("/brands", response_model=List[str], summary="Lista de Marcas Encontradas (Baseado na Última Busca Simulada)")
async def get_brands(
     q: str = Query(..., description="Termo de busca para basear a lista de marcas")
     # Poderia receber outros filtros se a lógica fosse buscar e depois extrair
):
    """
    Retorna uma lista de marcas únicas encontradas para um termo de busca (simulado).
    NOTA: Idealmente, as marcas seriam extraídas dos resultados *reais* de uma busca.
    """
    try:
        # Simula uma busca para obter dados e extrair marcas (poderia ser otimizado)
        simulated_results = search_service.get_search_results(q, None, None, [], [], None, "asc")
        return search_service.get_available_brands(simulated_results)
    except Exception as e:
        print(f"Erro em /brands: {e}") # Log simplificado
        raise HTTPException(status_code=500, detail="Erro ao obter lista de marcas.")

# --- Execução (para desenvolvimento local) ---
if __name__ == "__main__":
    import uvicorn
    # Use reload=True para que o servidor reinicie automaticamente com mudanças no código
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 