# This file will contain the core service logic:
# - Aggregating results from scrapers
# - Applying filters and sorting

import logging
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import concurrent.futures

# Importar funções dos scrapers
from scrapers.amazon_scraper import search_amazon
from scrapers.mercadolivre_scraper import search_mercado_livre
# Importar outros scrapers aqui quando forem implementados
# from scrapers.growth_scraper import search_growth

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Mapeamento de nomes de lojas para funções de scraper
SCRAPER_MAPPING = {
    "Amazon": search_amazon,
    "Mercado Livre": search_mercado_livre,
    # "Growth Supplements": search_growth, # Adicionar outros aqui
}

def get_search_results(
    query: str,
    min_price: Optional[float],
    max_price: Optional[float],
    brands: Optional[List[str]],
    marketplaces: Optional[List[str]],
    sort_by: Optional[str],
    order: Optional[str],
    max_results_per_store: int = 5 # Define um limite padrão
) -> List[Dict]:
    """
    Orquestra a busca nos scrapers, agrega, filtra e ordena os resultados.
    """
    logging.info(f"Serviço: Iniciando busca para '{query}' com filtros...")
    all_results = []
    current_time = datetime.now()

    # Determina quais scrapers executar
    if marketplaces:
        scrapers_to_run = {name: func for name, func in SCRAPER_MAPPING.items() if name in marketplaces}
        if not scrapers_to_run:
            logging.warning("Nenhuma loja selecionada ou válida foi fornecida.")
            return []
    else:
        # Se nenhuma loja for especificada, busca em todas as mapeadas
        scrapers_to_run = SCRAPER_MAPPING

    logging.info(f"Lojas selecionadas para busca: {list(scrapers_to_run.keys())}")

    # Executa scrapers concorrentemente
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(scrapers_to_run)) as executor:
        # Mapeia cada função de scraper para ser executada com a query e max_results
        future_to_store = {executor.submit(scraper_func, query, max_results_per_store): store_name
                           for store_name, scraper_func in scrapers_to_run.items()}

        for future in concurrent.futures.as_completed(future_to_store):
            store_name = future_to_store[future]
            try:
                store_results = future.result()
                if store_results:
                    logging.info(f"Resultados de {store_name}: {len(store_results)}")
                    # Adiciona a data/hora da consulta a cada resultado
                    for result in store_results:
                        result['query_date'] = current_time # Armazena como objeto datetime por enquanto
                    all_results.extend(store_results)
                else:
                    logging.info(f"Nenhum resultado encontrado em {store_name}.")
            except Exception as exc:
                logging.error(f"{store_name} gerou uma exceção: {exc}", exc_info=True)

    logging.info(f"Total de resultados brutos agregados: {len(all_results)}")

    # Converte para DataFrame para facilitar filtragem e ordenação
    if not all_results:
        return []

    df = pd.DataFrame(all_results)

    # Aplicar Filtros
    # 1. Preço
    if min_price is not None:
        df = df[df['price'] >= min_price]
    if max_price is not None:
        df = df[df['price'] <= max_price]

    # 2. Marca (case-insensitive)
    if brands:
        brands_lower = [b.lower() for b in brands]
        # Garante que a coluna 'brand' existe e lida com NaN
        df = df[df['brand'].fillna('').str.lower().isin(brands_lower)]

    logging.info(f"Resultados após filtros: {len(df)}")

    # Aplicar Ordenação
    if sort_by:
        ascending_order = (order == 'asc')
        if sort_by == 'price':
            df = df.sort_values(by='price', ascending=ascending_order, na_position='last')
        elif sort_by == 'name': # Ordena pelo título
            df = df.sort_values(by='title', ascending=ascending_order, key=lambda col: col.str.lower())
        # Adicionar mais campos de ordenação se necessário

    # Formatar data ANTES de converter para dict, se necessário, ou manter datetime
    # Para consistência com schema Pydantic, vamos formatar ao final
    # df['query_date'] = df['query_date'].dt.strftime('%Y-%m-%d %H:%M:%S') # Se precisar de string

    # Converter DataFrame de volta para lista de dicionários
    final_results = df.to_dict('records')

    # Formatar data para string no formato desejado APENAS para exibição/retorno final
    # Mantendo datetime internamente pode ser útil
    for result in final_results:
        if isinstance(result['query_date'], datetime):
             result['query_date'] = result['query_date'].strftime('%Y-%m-%d %H:%M:%S')

    logging.info(f"Total de resultados finais: {len(final_results)}")
    return final_results

def get_available_marketplaces() -> List[str]:
    """Retorna a lista de lojas com scrapers implementados."""
    return list(SCRAPER_MAPPING.keys())

def get_available_brands(results: List[Dict]) -> List[str]:
    """Extrai marcas únicas dos resultados fornecidos."""
    if not results:
        return []
    # Usa pandas para facilitar a extração e remoção de duplicatas/NaN
    df = pd.DataFrame(results)
    if 'brand' not in df.columns:
        return []
    # Pega valores únicos, remove NaN/None, converte para lista e ordena
    unique_brands = df['brand'].dropna().unique().tolist()
    return sorted(unique_brands)

def generate_csv_data(results: List[Dict]) -> str:
    """
    Gera uma string CSV a partir da lista de resultados.
    """
    if not results:
        return "Marca do produto,Título Completo,Preco,Link,Data da consulta,Loja\n" # Retorna apenas cabeçalho

    df = pd.DataFrame(results)

    # Selecionar e Renomear colunas conforme escopo
    df_export = df[['brand', 'title', 'price', 'link', 'query_date', 'store']].copy()
    df_export.rename(columns={
        'brand': 'Marca do produto',
        'title': 'Título Completo',
        'price': 'Preco',
        'link': 'Link',
        'query_date': 'Data da consulta',
        'store': 'Loja'
    }, inplace=True)

    # Formatar a coluna de data para DD/MM/AAAA HH:MM
    # Primeiro, garante que é datetime se veio direto da busca
    df_export['Data da consulta'] = pd.to_datetime(df_export['Data da consulta'])
    df_export['Data da consulta'] = df_export['Data da consulta'].dt.strftime('%d/%m/%Y %H:%M')

    # Gerar CSV como string
    csv_string = df_export.to_csv(index=False, encoding='utf-8')

    logging.info("CSV gerado com sucesso.")
    return csv_string 