import requests  # Manter para type hints talvez, mas a lógica principal usará selenium
from bs4 import BeautifulSoup
import logging
import re
from urllib.parse import quote, urljoin
from typing import List, Dict, Optional
import random
import time

# Importar Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

# Reutilizar funções auxiliares (idealmente mover para utils, mas mantendo por enquanto)
from .amazon_scraper import _get_random_headers, _parse_price, _extract_brand

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def search_mercado_livre(query: str, max_results: int = 5, retries: int = 2) -> List[Dict]:
    results = []
    search_query = quote(query.replace(" ", "-")) # Mantém o formato de URL do ML
    url = f"https://lista.mercadolivre.com.br/{search_query}_Desde_1_NoIndex_True"
    current_try = 0

    while current_try < retries:
        current_try += 1
        driver = None # Inicializa driver como None
        try:
            # Configurar opções do Selenium para rodar em modo headless (sem abrir janela)
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu") # Necessário em alguns sistemas
            chrome_options.add_argument("--no-sandbox") # Necessário em alguns sistemas
            chrome_options.add_argument("--disable-dev-shm-usage") # Necessário em alguns sistemas
            chrome_options.add_argument("user-agent=" + random.choice(_get_random_headers()['User-Agent'])) # Usar User-Agent aleatório

            logging.info(f"[Mercado Livre] Iniciando Selenium (Tentativa {current_try}/{retries})")
            # Tenta inicializar o driver
            try:
                 # O ideal é ter o chromedriver no PATH ou especificar o caminho:
                 # driver = webdriver.Chrome(executable_path='/path/to/chromedriver', options=chrome_options)
                 driver = webdriver.Chrome(options=chrome_options)
            except WebDriverException as e:
                 logging.error(f"[Mercado Livre] Falha ao iniciar Selenium. Certifique-se que ChromeDriver está instalado e no PATH. Erro: {e}")
                 # Se falhar na primeira tentativa, não adianta tentar de novo sem corrigir o driver
                 return [] # Retorna lista vazia se não conseguir iniciar o Selenium

            logging.info(f"[Mercado Livre] Acessando URL com Selenium: {url}")
            driver.get(url)
            
            # Espera um tempo para o conteúdo dinâmico carregar (ajuste conforme necessário)
            time.sleep(random.uniform(3, 5)) # Aumentar um pouco o sleep

            logging.info(f"[Mercado Livre] Página carregada. Extraindo HTML.")
            page_source = driver.page_source # Pega o HTML renderizado pelo Selenium

            # Salvar HTML para inspeção (temporário para depuração)
            with open(f"mercadolivre_debug_selenium_{current_try}.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            logging.info(f"[Mercado Livre] HTML (via Selenium) salvo para depuração em mercadolivre_debug_selenium_{current_try}.html")

            soup = BeautifulSoup(page_source, 'html.parser')

            # Verificação se a página de resultados foi carregada (mantém a lógica anterior, mas no HTML do Selenium)
            if "ui-search-layout" not in page_source and "ui-search-item__title" not in page_source:
                 logging.warning(f"[Mercado Livre] Página de resultados não reconhecida (via Selenium). Tentando novamente em {current_try * 1.5}s...")
                 time.sleep(current_try * 1.5)
                 if driver: driver.quit() # Fecha o navegador antes de tentar novamente
                 continue

            # Seletores (mantidos da versão anterior, baseados no contexto)
            items = soup.select('li.ui-search-layout__item')
            if not items: items = soup.select('ol.ui-search-layout li')
            if not items: items = soup.select('section.ui-search-results .ui-search-result')
            if not items: items = soup.select('div[class*="ui-search-result"]')

            logging.info(f"[Mercado Livre] Itens brutos encontrados (via Selenium): {len(items)}")
            processed_ids = set()

            for i, item in enumerate(items):
                if len(results) >= max_results:
                    break

                try:
                    item_id = None
                    id_input = item.select_one('input[name="itemId"]')
                    if id_input: item_id = id_input.get('value')
                    else:
                        link_el = item.select_one('a[href*="MLB-"]')
                        if link_el:
                            match = re.search(r'(MLB-\d+)', link_el.get('href', ''))
                            if match: item_id = match.group(1)

                    logging.info(f"[Mercado Livre] Processando item {i+1}/{len(items)} - ID: {item_id or 'desconhecido'}")
                    if item_id and item_id in processed_ids: continue

                    # Seletores (mantidos da versão anterior, baseados no contexto)
                    title_selectors = ['h2.ui-search-item__title', 'a.ui-search-item__group__element h2', '.ui-search-result__content-title', 'h2[class*="ui-search"]']
                    link_selectors = ['a.ui-search-link', 'a.ui-search-item__group__element', 'a[class*="ui-search-link"]', '.ui-search-result__content a']
                    price_selectors = ['span.price-tag-fraction', 'span.andes-money-amount__fraction', '.ui-search-price__part .andes-money-amount__fraction', '.price-tag-amount .price-tag-fraction']
                    cents_selectors = ['span.andes-money-amount__cents', 'span.price-tag-cents', '.ui-search-price__part .andes-money-amount__cents', '.price-tag-amount .price-tag-cents']
                    image_selectors = ['img.ui-search-result-image__element', 'img[class*="ui-search-result-image"]', '.slick-slide.slick-active img', 'img[data-src]']

                    # Extração com fallback (conforme sugestão do contexto)
                    title_element = next((item.select_one(s) for s in title_selectors if item.select_one(s)), None)
                    link_element = next((item.select_one(s) for s in link_selectors if item.select_one(s)), None)
                    price_element = next((item.select_one(s) for s in price_selectors if item.select_one(s)), None)
                    cents_element = next((item.select_one(s) for s in cents_selectors if item.select_one(s)), None)
                    image_element = next((item.select_one(s) for s in image_selectors if item.select_one(s)), None)

                    # Implementar fallback para salvar dados parciais
                    title = "Título não encontrado"
                    if title_element and title_element.text.strip():
                        title = title_element.text.strip()
                        logging.info(f"[Mercado Livre] Título encontrado: {title[:30]}...")
                    else:
                        logging.warning(f"[Mercado Livre] Título não encontrado para item {i+1}")

                    link = "Link não encontrado"
                    if link_element and link_element.get('href'):
                        link = link_element.get('href')
                        logging.info(f"[Mercado Livre] Link encontrado: {link[:50]}...")
                    else:
                        logging.warning(f"[Mercado Livre] Link não encontrado para item {i+1}")

                    price = 0.0
                    if price_element:
                        price_text = price_element.text.strip()
                        if cents_element:
                            price_text += f",{cents_element.text.strip()}"
                        price = _parse_price(price_text)
                        logging.info(f"[Mercado Livre] Preço encontrado: R${price:.2f}")
                    else:
                        logging.warning(f"[Mercado Livre] Preço não encontrado para item {i+1}")

                    image_url = None
                    if image_element:
                        image_url = image_element.get('data-src') or image_element.get('src')
                        logging.info(f"[Mercado Livre] Imagem encontrada: {image_url[:50] if image_url else 'N/A'}...")
                    else:
                         logging.warning(f"[Mercado Livre] Imagem não encontrada para item {i+1}")


                    # Mesmo que título ou link não sejam encontrados, adiciona o produto com o que foi achado
                    brand = _extract_brand(title) # Extrai marca mesmo se título for "Título não encontrado"

                    product_data = {
                        'brand': brand,
                        'title': title,
                        'price': price,
                        'store': 'Mercado Livre',
                        'link': link,
                        'image_url': image_url
                    }
                    results.append(product_data)
                    if item_id:
                        processed_ids.add(item_id)
                    logging.info(f"[Mercado Livre] Produto adicionado (parcial ou completo): {title[:30]}... ({brand}) - R${price:.2f}")

                except Exception as e:
                    logging.error(f"[Mercado Livre] Erro processando item {i+1}: {e}", exc_info=True)
                    continue

            # Sair do loop de tentativas se encontrar resultados
            if results:
                 logging.info(f"[Mercado Livre] Busca bem-sucedida (via Selenium) na tentativa {current_try}. Produtos encontrados: {len(results)}")
                 break # Sai do while loop
            elif current_try == retries:
                 logging.warning(f"[Mercado Livre] Nao encontrou resultados (via Selenium) apos {retries} tentativas.")

        except WebDriverException as e:
            logging.error(f"[Mercado Livre] Erro no Selenium (Tentativa {current_try}): {e}")
            if current_try < retries:
                time.sleep(current_try * 1.5)
            else:
                 logging.error("[Mercado Livre] Máximo de tentativas atingido com Selenium.")
        except Exception as e:
            logging.error(f"[Mercado Livre] Erro inesperado (Tentativa {current_try}): {e}", exc_info=True)
            break # Sair em caso de erro grave e inesperado
        finally:
            # Garantir que o driver do Selenium seja fechado
            if driver:
                driver.quit()
                logging.info(f"[Mercado Livre] Driver Selenium fechado (Tentativa {current_try}).")


    logging.info(f"[Mercado Livre] Total de produtos encontrados final: {len(results)}")
    return results

# Exemplo de uso local
if __name__ == '__main__':
    search_term = "creatina monohidratada"
    print(f"Iniciando busca local por '{search_term}' no Mercado Livre usando Selenium...")
    ml_results = search_mercado_livre(search_term, max_results=3)
    print(f"\nResultados do Mercado Livre para '{search_term}':")
    if ml_results:
        for res in ml_results:
            print(f"  - {res['title']} ({res['brand']}) - R$ {res['price']:.2f} - Link: {res['link'][:60]}...")
    else:
        print("Nenhum resultado encontrado.")
 