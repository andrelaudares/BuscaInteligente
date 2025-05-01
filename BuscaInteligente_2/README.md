# BuscaInteligente_2

## Visão Geral

BuscaInteligente_2 é uma aplicação web para pesquisa inteligente de suplementos alimentares em múltiplos sites. Foi construída com arquitetura frontend-backend separada:

- **Backend**: FastAPI (Python)
- **Frontend**: React + Material-UI (TypeScript)
- **Orquestração**: Docker Compose

O design atual preserva o título e o logotipo do projeto original e utiliza uma paleta de cores verde (`#62ac44`) integrada a todos os componentes.

---

## Estrutura de Pastas

```text
BuscaInteligente_2/
├── backend/                  # API e scrapers em Python
│   ├── requirements.txt      # Dependências do backend
│   ├── Dockerfile            # Imagem do backend
│   ├── main.py               # Roteiros da API FastAPI
│   └── scrapers/             # Módulos de scraping por domínio
│       ├── base_scraper.py   # Classe abstrata base
│       └── amazon_scraper.py # Exemplo de scraper (Amazon)
│       └── ...               # Outros scrapers (MercadoLivre, etc.)
├── frontend/                 # Aplicação React
│   ├── package.json          # Dependências e scripts NPM
│   ├── Dockerfile            # Imagem do frontend
│   └── src/
│       ├── theme.ts          # Configuração de tema Material-UI
│       └── ...               # Componentes, páginas e assets
├── docker-compose.yml        # Orquestração de serviços (backend + frontend)
└── README.md                 # Documentação do projeto (você está aqui)
```

---

## Backend (FastAPI)

### Dependências
- fastapi, uvicorn, pydantic, aiohttp, beautifulsoup4, etc.

### Endpoints Disponíveis

| Método | Rota            | Descrição                                           |
|--------|-----------------|-----------------------------------------------------|
| GET    | `/api/stores`   | Lista de chaves (ids) dos scrapers disponíveis      |
| POST   | `/api/search`   | Busca produtos por `query`, `stores`, `min_price`, `max_price`

#### Exemplo de Payload (POST `/api/search`)
```json
{
  "query": "whey protein",
  "stores": ["amazon", "growth"],
  "min_price": 50.0,
  "max_price": 300.0
}
```

---

## Scrapers Modulares

Todos os scrapers herdam de `BaseScraper`:

- **base_scraper.py**: classe abstrata, contém métodos de requisição e parsing genéricos
- **amazon_scraper.py**: implementa `search()` para o domínio Amazon

### Como adicionar um novo scraper
1. Criar arquivo `nome_scraper.py` em `backend/scrapers/`
2. Implementar classe que estenda `BaseScraper` e sobrescreva `async def search(query)`
3. Adicionar instância no dicionário `scrapers` em `main.py`

---

## Frontend (React + MUI)

- Baseado em Create React App (TypeScript)
- **theme.ts**: define a paleta e estilos globais com `createTheme`
- Conecta-se ao backend via `REACT_APP_API_URL` (variável de ambiente)

### Scripts Disponíveis (em `frontend/package.json`)
```bash
npm install          # Instala dependências
npm start            # Inicia em modo desenvolvimento (http://localhost:3000)
npm run build        # Gera build de produção em /build
```

---

## Docker & Docker Compose

Para facilitar deploy e execução em qualquer máquina, há configuração Docker:

1. Buildar e subir serviços:
```bash
docker-compose up --build
```
2. API disponível em `http://localhost:8000`
3. Frontend disponível em `http://localhost:3000`

---

## Contribuição

- Adicione novos scrapers em `backend/scrapers`
- Amplie endpoints no FastAPI conforme necessidade
- Crie componentes React em `frontend/src/components`
- Atualize `theme.ts` para ajustar estilos

---

## Licença

Este projeto é fornecido sem licença explícita. Consulte a equipe para detalhes de uso interno. 