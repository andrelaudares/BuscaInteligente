document.addEventListener('DOMContentLoaded', () => {
    const storesListContainer = document.getElementById('stores-list');
    const brandsListContainer = document.getElementById('brands-list');
    const searchButton = document.getElementById('search-button');
    const searchQueryInput = document.getElementById('search-query');
    const productsContainer = document.getElementById('products-container');
    const loadingIndicator = document.getElementById('loading-indicator');
    const errorMessage = document.getElementById('error-message');
    const exportButtonContainer = document.getElementById('export-button-container');
    const minPriceInput = document.getElementById('min-price');
    const maxPriceInput = document.getElementById('max-price');
    const sortBySelect = document.getElementById('sort-by');
    const maxResultsInput = document.getElementById('max-results');

    const API_BASE_URL = 'http://localhost:8000'; // URL do seu backend FastAPI

    // --- Carregar Lojas Disponíveis ---
    async function loadStores() {
        try {
            const response = await fetch(`${API_BASE_URL}/marketplaces`);
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }
            const stores = await response.json();

            storesListContainer.innerHTML = ''; // Limpa placeholder
            if (stores.length > 0) {
                stores.forEach(store => {
                    const div = document.createElement('div');
                    // Cria um ID mais seguro para o checkbox
                    const checkboxId = `store-${store.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}`;
                    div.innerHTML = `
                        <input type="checkbox" id="${checkboxId}" name="store" value="${store}" checked>
                        <label for="${checkboxId}">${store}</label>
                    `;
                    storesListContainer.appendChild(div);
                });
            } else {
                storesListContainer.innerHTML = '<p style="font-size:0.8em; color:#666;">Nenhuma loja encontrada.</p>';
            }
        } catch (error) {
            console.error("Erro ao carregar lojas:", error);
            storesListContainer.innerHTML = '<p style="font-size:0.8em; color:red;">Erro ao carregar lojas.</p>';
        }
    }

    // --- Lógica de Busca ---
    async function performSearch() {
        try {
            const filters = getSelectedFilters();
            
            // Mostrar indicador de carregamento
            loadingIndicator.style.display = 'flex';
            productsContainer.style.display = 'none';
            errorMessage.style.display = 'none';

            // Construir URL com parâmetros
            const params = new URLSearchParams({
                q: filters.query
            });

            if (filters.minPrice) params.append('min_price', filters.minPrice);
            if (filters.maxPrice) params.append('max_price', filters.maxPrice);
            if (filters.stores.length > 0) {
                filters.stores.forEach(store => params.append('marketplaces', store));
            }
            if (filters.brands.length > 0) {
                filters.brands.forEach(brand => params.append('brands', brand));
            }

            // Adicionar parâmetros de ordenação
            const [sortField, sortOrder] = filters.sortBy.split('_');
            params.append('sort_by', sortField);
            params.append('order', sortOrder);

            const response = await fetch(`${API_BASE_URL}/search?${params.toString()}`);
            
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }

            const products = await response.json();
            displayProducts(products);
            
            // Carregar marcas disponíveis após a busca
            loadBrands(filters.query);

        } catch (error) {
            console.error("Erro na busca:", error);
            errorMessage.textContent = 'Erro ao realizar a busca. Por favor, tente novamente.';
            errorMessage.style.display = 'block';
            productsContainer.style.display = 'none';
        } finally {
            loadingIndicator.style.display = 'none';
        }
    }

    // --- Exibir Produtos ---
    function displayProducts(products) {
        productsContainer.innerHTML = '';
        exportButtonContainer.innerHTML = '';

        if (products.length === 0) {
            productsContainer.innerHTML = '<p>Nenhum produto encontrado.</p>';
            return;
        }

        // Criar cards de produtos
        products.forEach(product => {
            const card = document.createElement('div');
            card.className = 'product-card';
            card.innerHTML = `
                <img src="${product.image_url || 'images/no-image.png'}" alt="${product.name}" class="product-image">
                <div class="product-info">
                    <h3>${product.name}</h3>
                    <p class="product-brand">${product.brand || 'Marca não especificada'}</p>
                    <p class="product-price">R$ ${product.price.toFixed(2)}</p>
                    <p class="product-store">${product.marketplace}</p>
                    <a href="${product.url}" target="_blank" class="product-link">Ver na Loja</a>
                </div>
            `;
            productsContainer.appendChild(card);
        });

        // Adicionar botão de exportar
        const exportButton = document.createElement('button');
        exportButton.className = 'export-button';
        exportButton.textContent = 'Exportar para CSV';
        exportButton.onclick = () => exportResults(getSelectedFilters());
        exportButtonContainer.appendChild(exportButton);

        productsContainer.style.display = 'grid';
    }

    // --- Exportar Resultados ---
    async function exportResults(filters) {
        try {
            const params = new URLSearchParams({
                q: filters.query
            });
            // Adicionar os mesmos filtros usados na busca
            if (filters.minPrice) params.append('min_price', filters.minPrice);
            if (filters.maxPrice) params.append('max_price', filters.maxPrice);
            if (filters.stores.length > 0) {
                filters.stores.forEach(store => params.append('marketplaces', store));
            }
            if (filters.brands.length > 0) {
                filters.brands.forEach(brand => params.append('brands', brand));
            }
            const [sortField, sortOrder] = filters.sortBy.split('_');
            params.append('sort_by', sortField);
            params.append('order', sortOrder);

            window.location.href = `${API_BASE_URL}/export?${params.toString()}`;
        } catch (error) {
            console.error("Erro ao exportar:", error);
            alert('Erro ao exportar resultados. Por favor, tente novamente.');
        }
    }

    // --- Carregar Marcas ---
    async function loadBrands(query) {
        try {
            const response = await fetch(`${API_BASE_URL}/brands?q=${encodeURIComponent(query)}`);
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }
            const brands = await response.json();

            brandsListContainer.innerHTML = '';
            if (brands.length > 0) {
                brands.forEach(brand => {
                    const div = document.createElement('div');
                    const checkboxId = `brand-${brand.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase()}`;
                    div.innerHTML = `
                        <input type="checkbox" id="${checkboxId}" name="brand" value="${brand}" checked>
                        <label for="${checkboxId}">${brand}</label>
                    `;
                    brandsListContainer.appendChild(div);
                });
            } else {
                brandsListContainer.innerHTML = '<p style="font-size:0.8em; color:#666;">Nenhuma marca encontrada.</p>';
            }
        } catch (error) {
            console.error("Erro ao carregar marcas:", error);
            brandsListContainer.innerHTML = '<p style="font-size:0.8em; color:red;">Erro ao carregar marcas.</p>';
        }
    }

    // --- Obter Filtros Selecionados ---
    function getSelectedFilters() {
        const query = searchQueryInput.value.trim();
        const minPrice = minPriceInput.value ? parseFloat(minPriceInput.value) : null;
        const maxPrice = maxPriceInput.value ? parseFloat(maxPriceInput.value) : null;
        const sortBy = sortBySelect.value;
        const maxResults = parseInt(maxResultsInput.value);

        // Obter lojas selecionadas
        const stores = Array.from(document.querySelectorAll('#stores-list input[type="checkbox"]:checked'))
            .map(checkbox => checkbox.value);

        // Obter marcas selecionadas
        const brands = Array.from(document.querySelectorAll('#brands-list input[type="checkbox"]:checked'))
            .map(checkbox => checkbox.value);

        return {
            query,
            minPrice,
            maxPrice,
            stores,
            brands,
            sortBy,
            maxResults
        };
    }

    // --- Event Listeners ---
    searchButton.addEventListener('click', performSearch);
    searchQueryInput.addEventListener('keypress', (event) => {
        // Permite buscar pressionando Enter no campo de texto
        if (event.key === 'Enter') {
            performSearch();
        }
    });

    // --- Atualizar Progresso do Slider ---
    function updateRangeProgress(rangeInput) {
        const value = rangeInput.value;
        const max = rangeInput.max || 10;
        const progress = (value / max) * 100;
        rangeInput.style.setProperty('--range-progress', `${progress}%`);
    }

    // Atualizar inicialmente e adicionar listener
    if (maxResultsInput) {
        updateRangeProgress(maxResultsInput);
        maxResultsInput.addEventListener('input', (e) => updateRangeProgress(e.target));
    }

    // --- Inicialização ---
    loadStores(); // Carrega as lojas disponíveis quando a página é carregada

}); 