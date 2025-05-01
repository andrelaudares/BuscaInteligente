```markdown
# Web App de Busca Inteligente de Suplementos

Este documento apresenta o escopo claro e objetivo das funcionalidades para guiar a IA Coding na implementação do projeto.

## 1. Objetivo
Desenvolver um web app que permita ao usuário pesquisar suplementos alimentares em múltiplos marketplaces e sites de marca, comparar preços e parâmetros, aplicar filtros avançados e exportar resultados para CSV.

## 2. Funcionalidades Principais

### 2.1 Pesquisa de Produtos
- **Input de busca**: campo de texto para inserir o nome do suplemento.
- **Envio da consulta**: ao submeter, o backend realiza requisições de scraping ou APIs em marketplaces e sites de marca.

### 2.2 Filtros e Ordenação
Disponíveis antes ou após a pesquisa, aplicáveis em tempo real:
1. **Faixa de Preço**: definir valor mínimo e máximo.
2. **Ordenação por Preço**: crescente ou decrescente.
3. **Ordenação por Nome**: de A–Z ou Z–A.
4. **Marca do Suplemento**: selecionar uma ou múltiplas marcas.
5. **Marketplace**: escolher quais lojas consultar e limitar quantidade de itens por loja.

### 2.3 Exibição de Resultados
- **Formato**: Cards estruturados:
  - Marca do produto
  - Título completo do produto
  - Preço
  - Loja (marketplace ou site de marca)
  - Botão "ver na loja" para o link para pagina da oferta
- **Paginação**: navegar entre páginas de resultados (opcional).

### 2.4 Exportação de Dados
Após a exibição, o usuário pode exportar todos os resultados atuais para um arquivo CSV compatível com Excel, contendo as colunas:
- Marca do produto
- Título completo do produto
- Preço
- Link para compra
- Data da consulta (DD/MM/AAAA HH:MM)
- Loja

Botão “Exportar Excel” disponível acima ou abaixo da lista de resultados.

## 3. Marketplaces e Sites Suportados
- Amazon
- Mercado Livre
- Americanas
- Drogaria Araújo
- Drogasil / Droga Raia
- Mundo Verde
- Corpo Ideal
- GSuplementos
- Growth Supplements
- Integralmedica
- Natue
- Suplementos Mais Baratos
- Power Suplementos

## 4. Arquitetura da Solução

### 4.1 Backend (FastAPI + Python)
- **Rotas**:
  - `GET /search` – parâmetros: `q`, `min_price`, `max_price`, `brands[]`, `marketplaces[]`, `sort_by`, `order`.
  - `GET /export` – mesmos parâmetros de `/search`, retorna CSV.
  - `GET /marketplaces` – lista de lojas disponíveis.
  - `GET /brands` – lista de marcas extraídas.
- **Módulos**:
  - **Scrapers**: lógica de coleta para cada site.
  - **Services**: agregação, aplicação de filtros, ordenação.
  - **Models**: schemas Pydantic para request/response.
  - **Utils**: cache de resultados e formatação de data para CSV.

### 4.2 Frontend (HTML + CSS)
- **Páginas**:
  - `index.html`: campo de busca, painel de filtros, botão de exportação.
  - `results.html`: tabela/card de resultados dinâmicos.
- **Componentes**:
  - Campo de texto e botão de busca.
  - Painel lateral de filtros com checkboxes, sliders e dropdowns.
  - Tabela adaptativa responsiva.
  - Botão “Exportar CSV” acionando requisição para `GET /export`.
  - **Paleta de cores**:
  - #62ac44
  - #8c54a4
  - #53aacd 
  - #040404 
  

## 5. Plano de Implementação Rápido
1. **Setup Inicial**: ambiente Python, FastAPI, Uvicorn, templates estáticos.
2. **Mock de Backend**: rota `/search` com dados de exemplo.
3. **Frontend Básico**: page `index.html`, form de pesquisa.
4. **Scraping Essencial**: Amazon e Mercado Livre.
5. **Filtros e Ordenação**: lógica no serviço e UI.
6. **CSV Export**: gerar CSV com biblioteca Python (`csv` ou `pandas`).
7. **Testes**: rotas e rotina de exportação.
8. **Documentação**: OpenAPI e instruções de uso.
```

