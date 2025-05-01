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
                wait_time = current_try * random.uniform(3, 6) # Aumentar o tempo base e adicionar mais aleatoriedade
                logging.warning(f"[Amazon] Bloqueio detectado ou erro 503 (Status: {response.status_code}). Tentando novamente em {wait_time:.1f}s...")
                time.sleep(wait_time) # Backoff exponencial com jitter
                continue # Pula para próxima tentativa

            response.raise_for_status() # Lança exceção para outros erros HTTP
            logging.info(f"[Amazon] Status: {response.status_code}")

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Salvar HTML para inspeção (temporário para depuração)
            with open(f"amazon_debug_{current_try}.html", "w", encoding="utf-8") as f:
                f.write(str(soup))
            logging.info(f"[Amazon] HTML salvo para depuração em amazon_debug_{current_try}.html")
            
            # Seletores atualizados para Amazon
            # Primeiro seletor principal (mais específico)
            items = soup.select('div.s-result-item[data-asin]:not([data-asin=""])')
            logging.info(f"[Amazon] Itens brutos encontrados com seletor principal: {len(items)}")

            # Seletores alternativos se o principal falhar
            if not items:
                items = soup.select('div[data-component-type="s-search-result"]')
                logging.info(f"[Amazon] Itens brutos encontrados com seletor alternativo: {len(items)}")
                
            if not items:
                items = soup.select('.s-main-slot > div[data-asin]')
                logging.info(f"[Amazon] Itens brutos encontrados com terceiro seletor: {len(items)}")

            processed_asins = set()

            for i, item in enumerate(items):
                if len(results) >= max_results:
                    break

                asin = item.get('data-asin')
                if not asin or asin in processed_asins:
                    continue

                logging.info(f"[Amazon] Processando item {i+1}/{len(items)} - ASIN: {asin}")

                try:
                    # Seletores atualizados conforme arquivo de contexto
                    # Seletores para título
                    title_selectors = [
                        'h2 a span',
                        'h2 span.a-text-normal',
                        'h2 a.a-link-normal span',
                        '.a-size-base-plus.a-color-base.a-text-normal',
                        '.a-size-medium.a-color-base.a-text-normal'
                    ]
                    
                    # Seletores para preço
                    price_selectors = [
                        'span.a-price > span.a-offscreen',
                        'span.a-price span.a-offscreen',
                        'span.a-color-price',
                        '.a-price .a-offscreen'
                    ]
                    
                    # Seletores para link
                    link_selectors = [
                        'a.a-link-normal.s-no-outline',
                        'h2 a.a-link-normal[href*="/dp/"]',
                        'a.a-link-normal.s-link-style[href*="/dp/"]',
                        '.a-link-normal[href*="/dp/"]'
                    ]
                    
                    # Seletores para imagem
                    image_selectors = [
                        'img.s-image',
                        '.s-image',
                        'img[data-image-load]'
                    ]
                    
                    # Tentar todos os seletores para cada elemento
                    title_element = None
                    for selector in title_selectors:
                        title_element = item.select_one(selector)
                        if title_element:
                            logging.info(f"[Amazon] Título encontrado com seletor: {selector}")
                            break
                    
                    price_element = None
                    for selector in price_selectors:
                        price_element = item.select_one(selector)
                        if price_element:
                            logging.info(f"[Amazon] Preço encontrado com seletor: {selector}")
                            break
                    
                    link_element = None
                    for selector in link_selectors:
                        link_element = item.select_one(selector)
                        if link_element:
                            logging.info(f"[Amazon] Link encontrado com seletor: {selector}")
                            break
                    
                    image_element = None
                    for selector in image_selectors:
                        image_element = item.select_one(selector)
                        if image_element:
                            logging.info(f"[Amazon] Imagem encontrada com seletor: {selector}")
                            break
                    
                    # Log de resultados de extração
                    if not title_element:
                        logging.warning(f"[Amazon] Título não encontrado para ASIN {asin}")
                    if not price_element:
                        logging.warning(f"[Amazon] Preço não encontrado para ASIN {asin}")
                    if not link_element:
                        logging.warning(f"[Amazon] Link não encontrado para ASIN {asin}")
                    if not image_element:
                        logging.warning(f"[Amazon] Imagem não encontrada para ASIN {asin}")

                    # Condição mais flexível: só precisamos de título e link no mínimo
                    if title_element and link_element:
                        title = title_element.text.strip()
                        link = link_element.get('href')
                        
                        # Garantir que o link seja absoluto
                        if link and link.startswith('/'):
                            link = urljoin("https://www.amazon.com.br", link)
                            
                        # Se tiver preço, extrair; caso contrário, usar 0.0
                        price = 0.0
                        if price_element:
                            price_text = price_element.text.strip()
                            price = _parse_price(price_text)
                            
                        brand = _extract_brand(title)
                        image_url = image_element.get('src') if image_element else None

                        # Log do produto sendo adicionado (antes de validações finais)
                        logging.info(f"[Amazon] Produto extraído: {title[:30]}... (Preço: {price}, Link: {link[:50]}...)")
                        
                        # Condições menos rígidas para adicionar produto
                        if title and link and link.startswith('http'):
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
                            logging.warning(f"[Amazon] Dados inválidos para ASIN {asin}: title='{title}', link='{link}'")
                    else:
                        logging.warning(f"[Amazon] Elementos essenciais não encontrados para ASIN {asin}")

                except Exception as e:
                    logging.error(f"[Amazon] Erro processando item ASIN {asin}: {e}", exc_info=True)
                    continue

            # Se encontrou resultados, sair do loop de tentativas
            if results:
                 logging.info(f"[Amazon] Busca bem-sucedida na tentativa {current_try}. Produtos encontrados: {len(results)}")
                 break
            elif current_try == retries:
                 logging.warning(f"[Amazon] Nao encontrou resultados apos {retries} tentativas.")

        except requests.exceptions.RequestException as e:
            logging.error(f"[Amazon] Erro na requisição (Tentativa {current_try}): {e}")
            if current_try < retries:
                wait_time = current_try * random.uniform(3, 6) # Usar a mesma lógica de backoff
                logging.info(f"[Amazon] Aguardando {wait_time:.1f}s antes de tentar novamente...")
                time.sleep(wait_time)
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