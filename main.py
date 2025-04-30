import streamlit as st
import pandas as pd
import plotly.express as px
import logging
from scraper import SupplementScraper
from io import BytesIO
from datetime import datetime
from PIL import Image

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar o logo
try:
    logo = Image.open("logo pro nutrition .png")
except FileNotFoundError:
    logo = None

# Configuração da página Streamlit
st.set_page_config(
    page_title="ProNutrition Busca Inteligente",
    page_icon="💪",
    layout="wide"
)

# Função para converter DataFrame para Excel em memória
@st.cache_data
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Resultados')
    processed_data = output.getvalue()
    return processed_data

# Função para lidar com erros de forma graciosa
def handle_error(message):
    st.error(message)
    st.stop()

# --- Layout da Página ---

col1_title, col2_title = st.columns([1, 4])
with col1_title:
    if logo:
        st.image(logo, width=100)
with col2_title:
    st.title("ProNutrition Busca Inteligente")
    st.markdown("Encontre o melhor preço para seus suplementos favoritos em diversas lojas!")

st.markdown("--- ")

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
        max_results = st.slider("Máximo de resultados por loja:", min_value=1, max_value=10, value=5, help="Define quantos produtos buscar em cada loja.")
    with col2:
        sort_by = st.selectbox("Ordenar resultados por:", options=["Menor preço", "Maior preço", "Nome (A-Z)", "Loja"], index=0)
    with col3:
        show_charts = st.checkbox("Mostrar gráficos de análise", value=True)

    submit_button = st.form_submit_button(label="Buscar Suplementos")

# Armazenar resultados no estado da sessão para exportação
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'last_query' not in st.session_state:
    st.session_state.last_query = ""

# Quando o botão de busca for pressionado
if submit_button and search_query:
    st.session_state.last_query = search_query
    with st.spinner(f"Buscando por '{search_query}'... Isso pode levar um minuto! ⏳"):
        try:
            log_container = st.empty()
            log_container.info("Iniciando busca de suplementos...")

            results = scraper.search_supplements(search_query, max_results)
            st.session_state.search_results = results

            log_container.success(f"Busca concluída! Encontrados {len(results)} produtos.")
            sleep(2)
            log_container.empty()

        except Exception as e:
            st.error(f"Ocorreu um erro durante a busca: {str(e)}")
            logging.error(f"Erro na busca por '{search_query}': {str(e)}", exc_info=True)
            st.session_state.search_results = None
            st.info("Tente digitar 'teste' na busca para ver resultados simulados.")
            st.stop()

# Exibir resultados se existirem no estado da sessão
if st.session_state.search_results is not None:
    results = st.session_state.search_results
    current_query = st.session_state.last_query

    if not results:
        st.warning(f"Não encontramos nenhum suplemento com o termo '{current_query}'. Tente outra busca ou use 'teste' para simulação.")
    else:
        if sort_by == "Menor preço":
            results.sort(key=lambda x: x['price'] if x['price'] > 0 else float('inf'))
        elif sort_by == "Maior preço":
            results.sort(key=lambda x: x['price'] if x['price'] > 0 else float('-inf'), reverse=True)
        elif sort_by == "Nome (A-Z)":
            results.sort(key=lambda x: x['title'].lower())
        elif sort_by == "Loja":
            results.sort(key=lambda x: (x['store'], x['price'] if x['price'] > 0 else float('inf')))

        st.subheader(f"Resultados para '{current_query}' ({len(results)} encontrados)")

        df_export = pd.DataFrame(results)
        if not df_export.empty:
            df_export_final = df_export[['brand', 'price', 'link', 'query_date', 'store', 'title']].copy()
            df_export_final.rename(columns={
                'brand': 'Marca do produto',
                'price': 'Preco',
                'link': 'Link',
                'query_date': 'Data da consulta',
                'store': 'Loja',
                'title': 'Título Completo'
            }, inplace=True)
            excel_data = to_excel(df_export_final)
            st.download_button(
                label="📥 Exportar para Excel",
                data=excel_data,
                file_name=f"pronutrition_busca_{current_query.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Clique para baixar a tabela com os resultados da busca."
            )

        cols = st.columns(3)
        for i, item in enumerate(results):
            with cols[i % 3]:
                with st.container(border=True):
                    display_title = item['title']
                    if len(display_title) > 55:
                        display_title = display_title[:52] + "..."

                    st.markdown(f"**{display_title}**", help=item['title'] if len(item['title']) > 55 else None)
                    st.image(item['image_url'], width=120, use_column_width='auto')

                    price_display = f"R$ {item['price']:.2f}" if item['price'] > 0 else "Indisponível"
                    st.markdown(f"<span style='font-size: 1.1em; font-weight: bold;'>{price_display}</span>", unsafe_allow_html=True)

                    st.caption(f"Loja: {item['store']} | Marca: {item['brand']}")
                    st.link_button("Ver na loja 🛒", item['link'], use_container_width=True)

        if show_charts:
            df_analysis = pd.DataFrame(results)
            valid_price_df = df_analysis[df_analysis['price'] > 0].copy()

            if valid_price_df.empty:
                st.warning("Não há dados de preço válidos para gerar gráficos de análise.")
            else:
                st.markdown("--- ")
                st.subheader("📊 Análise de Preços")

                col_an1, col_an2 = st.columns(2)

                with col_an1:
                    st.markdown("##### Estatísticas Gerais")
                    stats = pd.DataFrame({
                        'Métrica': ['Preço Médio', 'Preço Mínimo', 'Preço Máximo', 'Desvio Padrão'],
                        'Valor': [
                            f"R$ {valid_price_df['price'].mean():.2f}",
                            f"R$ {valid_price_df['price'].min():.2f}",
                            f"R$ {valid_price_df['price'].max():.2f}",
                            f"R$ {valid_price_df['price'].std():.2f}"
                        ]
                    }).set_index('Métrica')
                    st.dataframe(stats, use_container_width=True)

                with col_an2:
                    st.markdown("##### Preço Médio por Loja")
                    if len(valid_price_df['store'].unique()) > 1:
                        try:
                            store_avg = valid_price_df.groupby('store')['price'].mean().reset_index()
                            fig_store_avg = px.bar(store_avg,
                                                   x='store',
                                                   y='price',
                                                   title="Preço Médio por Loja",
                                                   labels={'store': 'Loja', 'price': 'Preço Médio (R$)'},
                                                   text_auto='.2f',
                                                   color='store',
                                                   height=350
                                                   )
                            fig_store_avg.update_layout(showlegend=False)
                            st.plotly_chart(fig_store_avg, use_container_width=True)
                        except Exception as e:
                            st.warning(f"Não foi possível gerar o gráfico de preço médio por loja: {str(e)}")
                    else:
                        st.info("Gráfico de preço médio por loja requer resultados de mais de uma loja.")

                if len(valid_price_df['store'].unique()) > 0:
                    st.markdown("##### Distribuição de Preços por Loja")
                    try:
                        fig_box = px.box(valid_price_df, x='store', y='price',
                                         title="Distribuição de Preços por Loja",
                                         labels={'store': 'Loja', 'price': 'Preço (R$)'},
                                         points="all",
                                         color='store',
                                         height=400
                                         )
                        fig_box.update_layout(showlegend=False)
                        st.plotly_chart(fig_box, use_container_width=True)
                    except Exception as e:
                         st.warning(f"Não foi possível gerar o gráfico de distribuição de preços: {str(e)}")

                st.markdown("##### Comparação de Preços entre Produtos")
                if len(valid_price_df) <= 20:
                    try:
                        valid_price_df['title_short'] = valid_price_df['title'].str[:30] + '...'
                        fig_compare = px.bar(valid_price_df.sort_values('price'),
                                             x='title_short', y='price', color='store',
                                             title='Comparativo de Preços (Produtos Individuais)',
                                             labels={'title_short': 'Produto', 'price': 'Preço (R$)', 'store': 'Loja'},
                                             hover_data=['title', 'brand'],
                                             height=450,
                                             barmode='group'
                                             )
                        fig_compare.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig_compare, use_container_width=True)
                    except Exception as e:
                         st.warning(f"Não foi possível gerar o gráfico comparativo de barras: {str(e)}")
                elif len(valid_price_df) > 20:
                    try:
                         fig_scatter = px.scatter(valid_price_df,
                                                x='title', y='price', color='store', size='price',
                                                title='Comparativo de Preços (Produtos Individuais)',
                                                labels={'title': 'Produto', 'price': 'Preço (R$)', 'store': 'Loja'},
                                                hover_data=['brand'],
                                                height=450
                                                )
                         fig_scatter.update_layout(xaxis={'categoryorder':'total descending'})
                         st.plotly_chart(fig_scatter, use_container_width=True)
                         st.caption("Tamanho do ponto proporcional ao preço.")
                    except Exception as e:
                         st.warning(f"Não foi possível gerar o gráfico comparativo de dispersão: {str(e)}")

# Rodapé
st.markdown("--- ")
st.markdown("© 2024 ProNutrition Busca Inteligente - Encontrando os melhores preços para você.")