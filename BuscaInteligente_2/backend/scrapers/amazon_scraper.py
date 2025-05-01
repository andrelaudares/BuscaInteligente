import requests
from bs4 import BeautifulSoup
import logging
import re
from urllib.parse import quote, urljoin
from typing import List, Dict, Optional
import random
import time  # Importar time para backoff

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Lista de User-Agents para rotacionar (manter atualizada)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0'
]

KNOWN_BRANDS = [
    "Growth Supplements", "Integral Medica", "Max Titanium", "Dux Nutrition",
    "Optimum Nutrition", "Black Skull", "Probiotica", "Atlhetica Nutrition",
    "Vitafor", "Essential Nutrition", "Dark Lab", "Soldiers Nutrition", "Adaptogen"
] # Adicionar mais marcas se necessário

def _get_random_headers():
    # Headers mais robustos para simular navegador
    user_agent = random.choice(USER_AGENTS)
    sec_ch_ua = '"Not/A)Brand";v="99", "Google Chrome";v="123", "Chromium";v="123"' # Exemplo, ajustar se necessário
    if "Firefox" in user_agent:
        sec_ch_ua = '"Firefox";v="124", "Not/A)Brand";v="99"'

    return {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1', # Do Not Track
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin', # Ou 'none' ou 'cross-site' dependendo do contexto
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'Connection': 'keep-alive',
        'Referer': 'https://www.amazon.com.br/',
        'Pragma': 'no-cache',
        'Cache-Control': 'max-age=0', # Da versão antiga
        'sec-ch-ua': sec_ch_ua,
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"' # Pode ser ajustado ou omitido
    }

def _parse_price(price_text: Optional[str]) -> float:
    # Função mantida, parece robusta
    if not price_text:
        return 0.0
    try:
        # Remove "R$", espaços, pontos de milhar e troca vírgula por ponto decimal
        price_clean = re.sub(r'[R$\s.]', '', price_text).replace(',', '.')
        # Lida com casos onde a limpeza removeu o ponto decimal por engano (ex: 1.234,50 -> 1234.50)
        if '.' not in price_clean and len(price_clean) > 2:
             # Assume os últimos 2 dígitos são centavos se não houver ponto
             price_clean = price_clean[:-2] + '.' + price_clean[-2:]
        elif price_clean.count('.') > 1:
             # Remove pontos de milhar se ainda existirem
             parts = price_clean.split('.')
             price_clean = "".join(parts[:-1]) + "." + parts[-1]
        return float(price_clean)
    except (ValueError, TypeError):
        logging.warning(f"Não foi possível converter preço '{price_text}'")
        return 0.0
    except Exception as e:
        logging.error(f"Erro inesperado ao converter preço '{price_text}': {str(e)}")
        return 0.0

def _extract_brand(title: str) -> str:
    # Função mantida, pode precisar de ajustes/expansão da lista KNOWN_BRANDS
    title_lower = title.lower()
    for brand in KNOWN_BRANDS:
        # Verifica a marca como palavra completa para evitar substrings (ex: "Integral" em "Integral Rice")
        if re.search(r'\b' + re.escape(brand.lower()) + r'\b', title_lower):
            return brand
    # Tenta pegar a primeira palavra capitalizada como último recurso
    match = re.search(r'\b([A-Z][a-zA-ZÀ-ÖØ-öø-ÿ]+(?:\s+[A-Z][a-zA-ZÀ-ÖØ-öø-ÿ]+)*)\b', title)
    generic_words = ['whey', 'protein', 'creatina', 'bcaa', 'glutamina', 'albumina', 'colageno', 'omega', 'multivitaminico'
                     'hipercalorico', 'termogenico', 'pre treino', 'capsulas', 'sabor', 'refil', 'pote', 'g', 'kg', 'sem', 'com', 'kit']
    if match and match.group(1).lower() not in generic_words and len(match.group(1)) > 2: # Evita palavras curtas
        return match.group(1)
    return "Marca Desconhecida"

def search_amazon(query: str, max_results: int = 5, retries: int = 3) -> List[Dict]:
    results = []
    search_query = quote(query)
    url = f"https://www.amazon.com.br/s?k={search_query}&i=hpc&rh=n%3A16210003011"
    current_try = 0

    while current_try < retries:
        current_try += 1
        try:
            headers = _get_random_headers()
            logging.info(f"[Amazon] Buscando (Tentativa {current_try}/{retries}): {url}")
            response = requests.get(url, headers=headers, timeout=25) # Aumentar timeout

            # Checar por bloqueio (pode ter status 200 mas ser página de captcha/bloqueio)
            if "api-services-support@amazon.com" in response.text or "Something went wrong" in response.text or response.status_code == 503:
                logging.warning(f"[Amazon] Bloqueio detectado ou erro 503 (Status: {response.status_code}). Tentando novamente em {current_try * 2}s...")
                time.sleep(current_try * 2) # Backoff exponencial simples
                continue # Pula para próxima tentativa

            response.raise_for_status() # Lança exceção para outros erros HTTP
            logging.info(f"[Amazon] Status: {response.status_code}")

            soup = BeautifulSoup(response.content, 'html.parser')
            # ** Novos Seletores (Ajustar conforme necessário após inspeção manual) **
            items = soup.select('div.s-result-item[data-asin]:not([data-asin=""])')
            logging.info(f"[Amazon] Itens brutos encontrados com seletor principal: {len(items)}")

            # Se o seletor principal falhar, tente um alternativo (menos comum)
            if not items:
                items = soup.select('div[data-component-type="s-search-result"]')
                logging.info(f"[Amazon] Itens brutos encontrados com seletor alternativo: {len(items)}")

            processed_asins = set()

            for item in items:
                if len(results) >= max_results:
                    break

                asin = item.get('data-asin')
                if not asin or asin in processed_asins:
                    continue

                try:
                    # Seletores atualizados (baseados em inspeção comum, podem precisar de ajuste fino)
                    title_element = item.select_one('h2 a.a-link-normal span.a-text-normal')
                    price_element = item.select_one('span.a-price > span.a-offscreen') # Preço geralmente está em 'a-offscreen'
                    # Seletor de link refinado com base na versão antiga
                    link_element = item.select_one('a.a-link-normal.s-link-style[href*="/dp/"]')
                    if not link_element:
                         # Fallback se o seletor mais específico falhar
                         link_element = item.select_one('h2 a.a-link-normal[href*="/dp/"]')
                    image_element = item.select_one('img.s-image')

                    if not (title_element and price_element and link_element):
                        # logging.debug(f"[Amazon] Item incompleto (sem título, preço ou link): ASIN {asin}")
                        continue

                    title = title_element.text.strip()
                    price_text = price_element.text.strip()
                    price = _parse_price(price_text)
                    brand = _extract_brand(title)
                    # Garante que o link seja absoluto
                    relative_link = link_element.get('href')
                    if relative_link and relative_link.startswith('/'):
                         link = urljoin("https://www.amazon.com.br", relative_link)
                    else:
                         # Se já for absoluto ou não começar com '/', usar como está (improvável mas seguro)
                         link = relative_link

                    image_url = image_element.get('src') if image_element else None

                    # Validar se os dados mínimos existem
                    if title and price > 0 and link and link.startswith('http'):
                        product_data = {
                            'brand': brand,
                            'title': title,
                            'price': price,
                            'store': 'Amazon',
                            'link': link,
                            'image_url': image_url
                        }
                        results.append(product_data)
                        processed_asins.add(asin)
                        logging.info(f"[Amazon] Produto adicionado: {title[:30]}... ({brand}) - R${price:.2f}")
                    else:
                         logging.warning(f"[Amazon] Dados inválidos para ASIN {asin}: title='{title}', price={price}, link='{link}'")

                except Exception as e:
                    logging.error(f"[Amazon] Erro processando item ASIN {asin}: {e}", exc_info=False) # Evitar stacktrace longo no log normal
                    continue

            # Se encontrou resultados, sair do loop de tentativas
            if results:
                 logging.info(f"[Amazon] Busca bem-sucedida na tentativa {current_try}.")
                 break
            elif current_try == retries:
                 logging.warning(f"[Amazon] Nao encontrou resultados apos {retries} tentativas.")

        except requests.exceptions.RequestException as e:
            logging.error(f"[Amazon] Erro na requisição (Tentativa {current_try}): {e}")
            if current_try < retries:
                time.sleep(current_try * 2)
            else:
                logging.error("[Amazon] Maximo de tentativas atingido.")
        except Exception as e:
            logging.error(f"[Amazon] Erro inesperado (Tentativa {current_try}): {e}", exc_info=True)
            # Sair do loop em caso de erro inesperado grave
            break

    logging.info(f"[Amazon] Total de produtos encontrados final: {len(results)}")
    return results

# Exemplo de uso local
if __name__ == '__main__':
    search_term = "creatina monohidratada"
    amazon_results = search_amazon(search_term, max_results=3)
    print(f"\nResultados da Amazon para '{search_term}':")
    if amazon_results:
        for res in amazon_results:
            print(f"  - {res['title']} ({res['brand']}) - R$ {res['price']:.2f} - {res['link']}")
    else:
        print("Nenhum resultado encontrado.") 