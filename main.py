import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from scraper import SupplementScraper

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração da página Streamlit
st.set_page_config(
    page_title="ProNutrition - Busca de Suplementos",
    page_icon="💪",
    layout="wide"
)

# Função para lidar com erros de forma graciosa
def handle_error(message):
    st.error(message)
    st.stop()

# Títulos e descrições
st.title("ProNutrition - Comparador de Suplementos")
st.markdown("Encontre o melhor preço para seus suplementos favoritos em diversas lojas!")

# Adiciona uma dica útil para o usuário
st.info("💡 Dica: Se estiver testando o app, digite 'teste' para ver resultados simulados!")

# Inicializa o scraper para busca de suplementos
try:
    scraper = SupplementScraper()
except Exception as e:
    handle_error(f"Erro ao inicializar o scraper: {str(e)}")

# Formulário de busca
with st.form(key='search_form'):
    search_query = st.text_input("Digite o nome do suplemento que deseja buscar:", placeholder="Ex: Whey Protein, Creatina...")
    col1, col2, col3 = st.columns(3)
    with col1:
        max_results = st.slider("Número máximo de resultados por loja:", min_value=1, max_value=10, value=3)
    with col2:
        sort_by = st.selectbox("Ordenar por:", options=["Menor preço", "Maior preço", "Nome"])
    with col3:
        wait_message = st.checkbox("Mostrar mensagens de debug", value=False)
    
    submit_button = st.form_submit_button(label="Buscar Suplementos")

# Quando o botão de busca for pressionado
if submit_button and search_query:
    # Adiciona spinner com mensagem personalizada
    with st.spinner('Buscando suplementos nas lojas. Isso pode demorar um pouco...'):
        try:
            # Configura o nível de log baseado na escolha do usuário
            if wait_message:
                # Adiciona um espaço para mensagens de log
                log_container = st.empty()
                log_container.info("Iniciando busca de suplementos...")
            
            # Busca suplementos usando o scraper
            results = scraper.search_supplements(search_query, max_results)
            
            if wait_message:
                log_container.success(f"Busca concluída! Encontrados {len(results)} suplementos.")
            
            if not results:
                st.warning(f"Não encontramos nenhum suplemento com o termo '{search_query}'. Tente outra busca ou digite 'teste' para ver resultados simulados!")
            else:
                # Ordenar resultados de acordo com a escolha do usuário
                if sort_by == "Menor preço":
                    results.sort(key=lambda x: x['price'] if x['price'] > 0 else float('inf'))
                elif sort_by == "Maior preço":
                    results.sort(key=lambda x: x['price'] if x['price'] > 0 else float('-inf'), reverse=True)
                elif sort_by == "Nome":
                    results.sort(key=lambda x: x['title'])
                
                # Mostrar resultados em cards
                st.subheader(f"Resultados para '{search_query}'")
                
                # Convertendo para DataFrame para análises
                df = pd.DataFrame(results)
                
                # Verifica se há preços válidos
                valid_prices = df[df['price'] > 0]['price']
                if len(valid_prices) == 0:
                    st.warning("Atenção: Não foi possível obter preços válidos para alguns produtos.")
                
                # Exibindo cards com os resultados
                cols = st.columns(3)
                for i, item in enumerate(results):
                    with cols[i % 3]:
                        with st.container():
                            st.markdown(f"### {item['title'][:40]}...")
                            st.image(item['image_url'], width=150)
                            if item['price'] > 0:
                                st.markdown(f"**Preço:** R$ {item['price']:.2f}")
                            else:
                                st.markdown("**Preço:** Indisponível")
                            st.markdown(f"**Loja:** {item['store']}")
                            st.markdown(f"[Ver oferta]({item['link']})")
                            st.markdown("---")
                
                # Análises só são exibidas se houver preços válidos
                if len(valid_prices) > 0:
                    # Análise de preços
                    st.subheader("Análise de Preços")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Estatísticas básicas
                        st.markdown("#### Estatísticas")
                        stats_df = df[df['price'] > 0]  # Ignora preços inválidos
                        if len(stats_df) > 0:
                            stats = pd.DataFrame({
                                'Estatística': ['Preço médio', 'Preço mínimo', 'Preço máximo', 'Desvio padrão'],
                                'Valor': [
                                    f"R$ {stats_df['price'].mean():.2f}", 
                                    f"R$ {stats_df['price'].min():.2f}",
                                    f"R$ {stats_df['price'].max():.2f}",
                                    f"R$ {stats_df['price'].std():.2f}"
                                ]
                            })
                            st.table(stats)
                    
                    with col2:
                        # Gráfico de preços por loja
                        try:
                            valid_store_df = df[df['price'] > 0]
                            if len(valid_store_df) > 0:
                                store_avg = valid_store_df.groupby('store')['price'].mean().reset_index()
                                if len(store_avg) > 0:
                                    fig, ax = plt.subplots(figsize=(10, 6))
                                    sns.barplot(x='store', y='price', data=store_avg, ax=ax)
                                    ax.set_title('Preço Médio por Loja')
                                    ax.set_xlabel('Loja')
                                    ax.set_ylabel('Preço Médio (R$)')
                                    plt.xticks(rotation=30, ha='right')
                                    st.pyplot(fig)
                        except Exception as e:
                            st.warning(f"Não foi possível gerar o gráfico de preços por loja: {str(e)}")
                    
                    # Gráfico de todos os preços - apenas se tiver um número razoável de produtos
                    if len(valid_prices) <= 15:  # Limite para evitar gráficos muito congestionados
                        st.markdown("#### Comparação de todos os preços")
                        try:
                            fig, ax = plt.subplots(figsize=(12, 6))
                            valid_df = df[df['price'] > 0].copy()
                            valid_df['title_short'] = valid_df['title'].str[:20] + '...'
                            sns.barplot(x='title_short', y='price', hue='store', data=valid_df, ax=ax)
                            ax.set_title('Comparação de Preços por Produto e Loja')
                            ax.set_xlabel('Produto')
                            ax.set_ylabel('Preço (R$)')
                            plt.xticks(rotation=45, ha='right')
                            plt.tight_layout()
                            st.pyplot(fig)
                        except Exception as e:
                            st.warning(f"Não foi possível gerar o gráfico de comparação de preços: {str(e)}")
                
        except Exception as e:
            st.error(f"Ocorreu um erro durante a busca: {str(e)}")
            logging.error(f"Erro na busca: {str(e)}")
            if wait_message:
                st.code(f"Erro detalhado: {str(e)}")
                st.info("Tente digitar 'teste' na busca apara ver resultados simulados.")

# Adicionar informações no rodapé
st.markdown("---")
st.markdown("© 2023 ProNutrition - Desenvolvido para ajudar você a encontrar os melhores preços em suplementos.")
st.markdown("*Dica: Em caso de problemas com a busca, digite 'teste' para ver resultados simulados.*")