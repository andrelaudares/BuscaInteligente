# Como Testar a API Busca Inteligente

Este guia explica como testar os endpoints da API backend usando uma ferramenta como o Postman ou `curl`.

**Pré-requisitos:**

1.  Navegue até a pasta do backend no seu terminal:
    ```bash
    cd /Users/palma/Busca\ Inteligente/BuscaInteligente_2/backend 
    ```
2.  Inicie o servidor FastAPI:
    ```bash
    python main.py
    ```
    O servidor estará rodando em `http://localhost:8000` (ou `http://127.0.0.1:8000`).

---

## Endpoints

**Nota:** Atualmente, os endpoints `/search`, `/export`, e `/brands` retornam dados *mockados* (simulados) definidos em `services/search_service.py`. A funcionalidade real de scraping e filtragem ainda precisa ser implementada.

### 1. Listar Marketplaces Disponíveis

*   **Método:** `GET`
*   **URL:** `http://localhost:8000/marketplaces`
*   **Descrição:** Retorna uma lista com os nomes das lojas/marketplaces que *serão* suportados.
*   **Exemplo de Resposta (JSON):**
    ```json
    [
        "Amazon",
        "Mercado Livre",
        "Growth Supplements"
    ]
    ```

### 2. Listar Marcas Encontradas (Simulado)

*   **Método:** `GET`
*   **URL:** `http://localhost:8000/brands?q=suplemento`
*   **Parâmetros:**
    *   `q` (obrigatório): O termo de busca usado para simular a extração de marcas.
*   **Descrição:** Retorna uma lista de marcas únicas baseada em uma busca *simulada* com o termo `q`. No exemplo atual, ele sempre retorna a marca 'Mock Brand'.
*   **Exemplo de URL (copiar/colar no Postman):**
    ```
    http://localhost:8000/brands?q=creatina
    ```
*   **Exemplo de Resposta (JSON):**
    ```json
    [
        "Mock Brand"
    ]
    ```

### 3. Buscar Produtos

*   **Método:** `GET`
*   **URL Base:** `http://localhost:8000/search`
*   **Parâmetros de Query (adicione após `?` separados por `&`):**
    *   `q` (obrigatório): Termo de busca. Ex: `q=whey%20protein` (use `%20` para espaços)
    *   `min_price` (opcional): Preço mínimo. Ex: `min_price=50.0`
    *   `max_price` (opcional): Preço máximo. Ex: `max_price=200.50`
    *   `brands` (opcional): Lista de marcas (repita o parâmetro). Ex: `brands=Marca1&brands=Marca2`
    *   `marketplaces` (opcional): Lista de lojas (repita o parâmetro). Ex: `marketplaces=Amazon&marketplaces=Growth%20Supplements`
    *   `sort_by` (opcional): Campo para ordenar (`price` ou `name`). Ex: `sort_by=price`
    *   `order` (opcional): Ordem (`asc` ou `desc`). Ex: `order=desc`
*   **Descrição:** Realiza a busca (atualmente simulada) e retorna uma lista de produtos.
*   **Exemplo de URL Completa (copiar/colar no Postman):**
    ```
    http://localhost:8000/search?q=creatina&min_price=40&max_price=100&marketplaces=Mock%20Store&sort_by=price&order=asc
    ```
*   **Exemplo de Resposta (JSON):**
    ```json
    [
        {
            "brand": "Mock Brand",
            "title": "Mock Product for creatina",
            "price": 50.0,
            "store": "Mock Store",
            "link": "#",
            "query_date": "2024-01-01 10:00:00",
            "image_url": "#"
        },
        {
            "brand": "Mock Brand",
            "title": "Mock Product for creatina",
            "price": 50.0,
            "store": "Mock Store",
            "link": "#",
            "query_date": "2024-01-01 10:00:00",
            "image_url": "#"
        },
        {
            "brand": "Mock Brand",
            "title": "Mock Product for creatina",
            "price": 50.0,
            "store": "Mock Store",
            "link": "#",
            "query_date": "2024-01-01 10:00:00",
            "image_url": "#"
        }
    ]
    ```

### 4. Exportar Resultados para CSV

*   **Método:** `GET`
*   **URL Base:** `http://localhost:8000/export`
*   **Parâmetros de Query:** Idênticos aos do endpoint `/search`.
*   **Descrição:** Executa a mesma lógica de busca (simulada) do `/search` e retorna os resultados como um arquivo CSV para download.
*   **Exemplo de URL Completa (copiar/colar no Postman ou navegador):**
    ```
    http://localhost:8000/export?q=whey&min_price=80
    ```
*   **Resposta:** A ferramenta (Postman/navegador) deve iniciar o download de um arquivo `.csv` (ex: `busca_suplementos_whey.csv`) com o seguinte conteúdo (exemplo):
    ```csv
    Marca do produto,Título Completo,Preco,Link,Data da consulta,Loja
    Mock Brand,Mock Product for whey,50.0,#,2024-01-01 10:00:00,Mock Store
    Mock Brand,Mock Product for whey,50.0,#,2024-01-01 10:00:00,Mock Store
    Mock Brand,Mock Product for whey,50.0,#,2024-01-01 10:00:00,Mock Store
    ```

---

Lembre-se de parar o servidor FastAPI no terminal (geralmente com `Ctrl+C`) quando terminar os testes. 