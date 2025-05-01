import requests
from bs4 import BeautifulSoup
import logging
import re
from urllib.parse import quote, urljoin
from typing import List, Dict, Optional
import random
import time # Importar time para possível backoff

# Reutilizar funções auxiliares (idealmente mover para utils, mas mantendo por enquanto)
from .amazon_scraper import _get_random_headers, _parse_price, _extract_brand

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def search_mercado_livre(query: str, max_results: int = 5, retries: int = 2) -> List[Dict]:
    results = []
    search_query = quote(query.replace(" ", "-")) # Mantém o formato de URL do ML
    url = f"https://lista.mercadolivre.com.br/{search_query}_Desde_1_NoIndex_True" # Adiciona parâmetro para forçar exibição em lista e evitar redirects
    current_try = 0

    while current_try < retries:
        current_try += 1
        try:
            headers = _get_random_headers()
            headers['Referer'] = 'https://www.mercadolivre.com.br/'

            logging.info(f"[Mercado Livre] Buscando (Tentativa {current_try}/{retries}): {url}")
            response = requests.get(url, headers=headers, timeout=25)

            # Mercado Livre pode retornar 200 OK mas com página de "não encontrado" ou captcha
            # Verificar por um elemento chave que *deveria* existir na página de resultados (container principal)
            if "ui-search-layout" not in response.text or response.status_code >= 400:
                 # Não encontrou o container de resultados ou teve erro HTTP
                 if response.status_code >= 400:
                      logging.warning(f"[Mercado Livre] Erro HTTP {response.status_code}. Tentando novamente em {current_try * 1.5}s...")
                 else:
                      logging.warning(f"[Mercado Livre] Página de resultados não reconhecida (Status: {response.status_code}). Tentando novamente em {current_try * 1.5}s...")
                 time.sleep(current_try * 1.5) # Backoff um pouco menor para ML
                 continue

            logging.info(f"[Mercado Livre] Status: {response.status_code}")

            soup = BeautifulSoup(response.content, 'html.parser')
            # Seletor principal atualizado para os itens da lista (mais flexível)
            items = soup.select('li.ui-search-layout__item')

            logging.info(f"[Mercado Livre] Itens brutos encontrados: {len(items)}")
            processed_ids = set()

            for item in items:
                if len(results) >= max_results:
                    break

                try:
                    # Tentar obter dados essenciais primeiro
                    title_element = item.select_one('h2.ui-search-item__title, a.ui-search-item__group__element h2') # Título pode estar em link ou h2 direto
                    link_element = item.select_one('a.ui-search-link[title][href], a.ui-search-item__group__element') # Link principal do item
                    price_element = item.select_one('span.andes-money-amount__fraction')
                    cents_element = item.select_one('span.andes-money-amount__cents')
                    image_element = item.select_one('img.ui-search-result-image__element')

                    # Extrair ID único para evitar duplicatas (opcional, mas útil)
                    # O ID pode estar no input ou no próprio link
                    item_id = None
                    id_input = item.select_one('input[name="itemId"]')
                    if id_input:
                         item_id = id_input.get('value')
                    elif link_element:
                         match = re.search(r'(MLB-\d+)', link_element.get('href', ''))
                         if match:
                              item_id = match.group(1)

                    if item_id and item_id in processed_ids:
                         continue

                    if not (title_element and price_element and link_element):
                        # logging.debug(f"[Mercado Livre] Item incompleto (sem título, preço ou link)")
                        continue

                    title = title_element.text.strip()
                    price_text = price_element.text.strip()
                    if cents_element:
                        # Apenas adiciona centavos se existirem
                        price_text += f",{cents_element.text.strip()}"
                    price = _parse_price(price_text)
                    brand = _extract_brand(title)
                    link = link_element.get('href')

                    image_url = None
                    if image_element:
                        # Prioriza data-src para lazy loading
                        image_url = image_element.get('data-src') or image_element.get('src')

                    # Validar dados mínimos
                    if title and price > 0 and link and link.startswith('http'):
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
                        logging.info(f"[Mercado Livre] Produto adicionado: {title[:30]}... ({brand}) - R${price:.2f}")
                    else:
                        logging.warning(f"[Mercado Livre] Dados inválidos para item: title='{title}', price={price}, link='{link}'")

                except Exception as e:
                    logging.error(f"[Mercado Livre] Erro processando item: {e}", exc_info=False)
                    continue

            # Sair do loop de tentativas se encontrar resultados
            if results:
                 logging.info(f"[Mercado Livre] Busca bem-sucedida na tentativa {current_try}.")
                 break
            elif current_try == retries:
                 logging.warning(f"[Mercado Livre] Nao encontrou resultados apos {retries} tentativas.")

        except requests.exceptions.RequestException as e:
            logging.error(f"[Mercado Livre] Erro na requisição (Tentativa {current_try}): {e}")
            if current_try < retries:
                time.sleep(current_try * 1.5)
            else:
                 logging.error("[Mercado Livre] Maximo de tentativas atingido.")
        except Exception as e:
            logging.error(f"[Mercado Livre] Erro inesperado (Tentativa {current_try}): {e}", exc_info=True)
            break # Sair em caso de erro grave

    logging.info(f"[Mercado Livre] Total de produtos encontrados final: {len(results)}")
    return results

# Exemplo de uso local
if __name__ == '__main__':
    search_term = "creatina monohidratada"
    ml_results = search_mercado_livre(search_term, max_results=3)
    print(f"\nResultados do Mercado Livre para '{search_term}':")
    if ml_results:
        for res in ml_results:
            print(f"  - {res['title']} ({res['brand']}) - R$ {res['price']:.2f} - {res['link']}")
    else:
        print("Nenhum resultado encontrado.")
 