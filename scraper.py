import requests
from bs4 import BeautifulSoup
import re
import random
from time import sleep
from urllib.parse import quote
import logging
from datetime import datetime # Adicionado para data da consulta

# Configurar logging para depuração
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Lista de marcas conhecidas para extração
KNOWN_BRANDS = [
    "Growth Supplements", "Integral Medica", "Max Titanium", "Dux Nutrition",
    "Optimum Nutrition", "Black Skull", "Probiotica", "Atlhetica Nutrition",
    "Vitafor", "Essential Nutrition"
]

class SupplementScraper:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.138 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.0.0'
        ]
        self.current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Data da consulta
    
    def _get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
    
    def _extract_brand(self, title):
        """Tenta extrair a marca do título do produto."""
        title_lower = title.lower()
        for brand in KNOWN_BRANDS:
            if brand.lower() in title_lower:
                return brand
        # Tenta pegar a primeira palavra capitalizada como último recurso
        match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', title)
        if match and match.group(1).lower() not in ['whey', 'creatina', 'bcaa', 'glutamina', 'protein', 'capsulas', 'sabor']: # Evitar palavras genéricas
             return match.group(1)
        return "Marca Desconhecida"

    def _parse_price(self, price_text):
        """Converte texto de preço para float, lidando com diferentes formatos."""
        try:
            # Remove 'R$', espaços e troca vírgula por ponto
            price_clean = re.sub(r'[^\d,]', '', price_text).replace(',', '.')
            # Se houver múltiplos pontos (milhar), remove exceto o último
            if price_clean.count('.') > 1:
                parts = price_clean.split('.')
                price_clean = "".join(parts[:-1]) + "." + parts[-1]
            return float(price_clean)
        except (ValueError, TypeError):
            return 0.0
        except Exception as e:
             logging.error(f"Erro inesperado ao converter preço '{price_text}': {str(e)}")
             return 0.0

    def search_amazon(self, query, max_results=5):
        search_query = quote(query)
        # Adicionamos filtros comuns para suplementos na busca da Amazon
        url = f"https://www.amazon.com.br/s?k={search_query}&i=drugstore&rh=n%3A16210003011"
        results = []
        try:
            logging.info(f"Buscando na Amazon: {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=15) # Aumentado timeout
            logging.info(f"Status code Amazon: {response.status_code}")

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser') # Usar response.content para encoding
                items = soup.select('.s-result-item[data-asin]:not([data-asin=""])')
                logging.info(f"Encontrados {len(items)} itens na Amazon com seletor principal.")

                if not items:
                    # Tentar seletores alternativos se o principal falhar
                    items = soup.select('div[data-component-type="s-search-result"]')
                    logging.info(f"Encontrados {len(items)} itens na Amazon com seletor alternativo.")

                count = 0
                processed_asins = set() # Evitar duplicatas

                for item in items:
                    asin = item.get('data-asin')
                    if not asin or asin in processed_asins:
                        continue # Pular itens sem ASIN ou já processados

                    if count >= max_results:
                        break

                    title_element = item.select_one('h2 .a-link-normal .a-text-normal, h2 .a-size-medium')
                    price_whole = item.select_one('.a-price-whole')
                    price_fraction = item.select_one('.a-price-fraction')
                    image_element = item.select_one('.s-image')
                    link_element = item.select_one('h2 a.a-link-normal, a.a-link-normal[href*="/dp/"]')

                    if title_element and price_whole and price_fraction and link_element:
                        title = title_element.text.strip()
                        price_text = f"{price_whole.text.strip()}{price_fraction.text.strip()}"
                        price = self._parse_price(price_text)
                        brand = self._extract_brand(title)

                        logging.debug(f"Amazon - Título: {title}, Preço Texto: {price_text}, Preço Num: {price}, Marca: {brand}")

                        image_url = image_element.get('src') if image_element else "https://via.placeholder.com/150"
                        href = link_element.get('href')
                        product_link = "https://www.amazon.com.br" + href if href and not href.startswith('http') else href

                        if price > 0 and product_link: # Garantir que temos preço e link válidos
                            results.append({
                                'title': title,
                                'price': price,
                                'image_url': image_url,
                                'link': product_link,
                                'store': 'Amazon',
                                'brand': brand,
                                'query_date': self.current_date
                            })
                            processed_asins.add(asin)
                            count += 1
                            logging.info(f"Adicionado produto Amazon: {title[:30]}... (Marca: {brand})")
                        else:
                            logging.warning(f"Item Amazon pulado (sem preço ou link): {title[:30]}...")
                    else:
                         logging.debug(f"Item Amazon incompleto pulado: {item.select_one('h2')}")


        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de conexão ao buscar na Amazon: {str(e)}")
        except Exception as e:
            logging.error(f"Erro inesperado ao buscar na Amazon: {str(e)}", exc_info=True)

        sleep(random.uniform(1.5, 3.0)) # Delay um pouco maior e aleatório
        logging.info(f"Total de produtos encontrados na Amazon: {len(results)}")
        return results
    
    def search_growth_suplementos(self, query, max_results=5):
        search_query = quote(query)
        url = f"https://www.gsuplementos.com.br/busca?q={search_query}" # URL atualizada
        results = []
        try:
            logging.info(f"Buscando na Growth: {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=15)
            logging.info(f"Status code Growth: {response.status_code}")

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # O seletor pode variar, inspecione a página de busca da Growth
                items = soup.select('.list-product .list-product__item')
                logging.info(f"Encontrados {len(items)} itens na Growth.")

                if not items:
                    # Tentar outro seletor comum
                    items = soup.select('.product-item')
                    logging.info(f"Encontrados {len(items)} itens na Growth com seletor alternativo.")


                count = 0
                for item in items:
                    if count >= max_results:
                        break

                    title_element = item.select_one('.product-name, .list-product__name')
                    price_element = item.select_one('.list-product__price--sell-price .valor, .product-price')
                    image_element = item.select_one('.list-product__image img, .product-image img')
                    link_element = item.select_one('a.list-product__link, a.product-item__link')

                    if title_element and price_element and link_element:
                        title = title_element.text.strip()
                        price_text = price_element.text.strip()
                        price = self._parse_price(price_text)
                        # Growth é a própria marca na maioria dos casos
                        brand = "Growth Suplements" if "growth" in title.lower() else self._extract_brand(title)

                        logging.debug(f"Growth - Título: {title}, Preço Texto: {price_text}, Preço Num: {price}, Marca: {brand}")

                        image_url = image_element.get('src') if image_element else "https://via.placeholder.com/150"
                        product_link = link_element.get('href')

                        # A Growth pode retornar links relativos
                        if product_link and not product_link.startswith('http'):
                             product_link = "https://www.gsuplementos.com.br" + product_link

                        if price > 0 and product_link:
                            results.append({
                                'title': title,
                                'price': price,
                                'image_url': image_url,
                                'link': product_link,
                                'store': 'Growth Suplements',
                                'brand': brand,
                                'query_date': self.current_date
                            })
                            count += 1
                            logging.info(f"Adicionado produto Growth: {title[:30]}... (Marca: {brand})")
                        else:
                            logging.warning(f"Item Growth pulado (sem preço ou link): {title[:30]}...")
                    else:
                         logging.debug(f"Item Growth incompleto pulado: {item.select_one('.list-product__name, .product-name')}")


        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de conexão ao buscar na Growth: {str(e)}")
        except Exception as e:
            logging.error(f"Erro inesperado ao buscar na Growth: {str(e)}", exc_info=True)

        sleep(random.uniform(1.5, 3.0))
        logging.info(f"Total de produtos encontrados na Growth: {len(results)}")
        return results
    
    def search_integralmedica(self, query, max_results=5):
        search_query = quote(query)
        url = f"https://www.integralmedica.com.br/catalogsearch/result/?q={search_query}"
        results = []
        try:
            logging.info(f"Buscando na Integral Medica: {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=15)
            logging.info(f"Status code Integral Medica: {response.status_code}")

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                items = soup.select('.product-item-info')
                logging.info(f"Encontrados {len(items)} itens na Integral Medica")

                count = 0
                for item in items:
                    if count >= max_results:
                        break

                    title_element = item.select_one('.product-item-link')
                    # Preço pode estar em 'price' ou 'special-price .price'
                    price_element = item.select_one('.special-price .price') or item.select_one('.price-final_price .price') or item.select_one('.price')
                    image_element = item.select_one('.product-image-photo')
                    link_element = item.select_one('.product-item-link')

                    if title_element and price_element and link_element:
                        title = title_element.text.strip()
                        price_text = price_element.text.strip()
                        price = self._parse_price(price_text)
                        # Integral Medica é a marca principal aqui
                        brand = "Integral Medica" if "integral" in title.lower() else self._extract_brand(title)

                        logging.debug(f"Integral - Título: {title}, Preço Texto: {price_text}, Preço Num: {price}, Marca: {brand}")

                        image_url = image_element.get('src') if image_element else "https://via.placeholder.com/150"
                        product_link = link_element.get('href')

                        if price > 0 and product_link:
                            results.append({
                                'title': title,
                                'price': price,
                                'image_url': image_url,
                                'link': product_link,
                                'store': 'Integral Medica',
                                'brand': brand,
                                'query_date': self.current_date
                            })
                            count += 1
                            logging.info(f"Adicionado produto Integral: {title[:30]}... (Marca: {brand})")
                        else:
                            logging.warning(f"Item Integral pulado (sem preço ou link): {title[:30]}...")
                    else:
                         logging.debug(f"Item Integral incompleto pulado: {item.select_one('.product-item-link')}")


        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de conexão ao buscar na Integral Medica: {str(e)}")
        except Exception as e:
            logging.error(f"Erro inesperado ao buscar na Integral Medica: {str(e)}", exc_info=True)

        sleep(random.uniform(1.5, 3.0))
        logging.info(f"Total de produtos encontrados na Integral Medica: {len(results)}")
        return results
    
    def search_netshoes(self, query, max_results=5):
        """Busca suplementos na Netshoes."""
        search_query = quote(query)
        # A Netshoes tem uma seção específica para suplementos
        url = f"https://www.netshoes.com.br/busca?nsCat=Natural&q={search_query}"
        results = []
        try:
            logging.info(f"Buscando na Netshoes: {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=15)
            logging.info(f"Status code Netshoes: {response.status_code}")

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # O seletor pode variar, inspecione a página de busca da Netshoes
                items = soup.select('.item-card')
                logging.info(f"Encontrados {len(items)} itens na Netshoes.")

                count = 0
                for item in items:
                    if count >= max_results:
                        break

                    title_element = item.select_one('.item-card__description__product-name')
                    price_element = item.select_one('.item-card__prices__price-value')
                    image_element = item.select_one('.item-card__images__image-link img')
                    link_element = item.select_one('.item-card__images__image-link') or item.select_one('.item-card__description__product-name') # Link pode estar na imagem ou no título

                    if title_element and price_element and link_element:
                        title = title_element.get('alt') or title_element.text.strip() # Título pode estar no alt da imagem ou texto
                        price_text = price_element.text.strip()
                        price = self._parse_price(price_text)
                        brand = self._extract_brand(title)

                        logging.debug(f"Netshoes - Título: {title}, Preço Texto: {price_text}, Preço Num: {price}, Marca: {brand}")

                        # A imagem pode ter carregamento lento (lazy load)
                        image_url = image_element.get('data-src') or image_element.get('src') if image_element else "https://via.placeholder.com/150"
                        # Garante que a URL da imagem comece com http
                        if image_url and image_url.startswith('//'):
                            image_url = 'https:' + image_url

                        product_link = link_element.get('href')
                        # Garante que a URL do link comece com http
                        if product_link and product_link.startswith('//'):
                            product_link = 'https:' + product_link
                        elif product_link and not product_link.startswith('http'):
                             product_link = 'https://www.netshoes.com.br' + product_link # Assume relativo se não for completo


                        if price > 0 and product_link:
                            results.append({
                                'title': title,
                                'price': price,
                                'image_url': image_url,
                                'link': product_link,
                                'store': 'Netshoes',
                                'brand': brand,
                                'query_date': self.current_date
                            })
                            count += 1
                            logging.info(f"Adicionado produto Netshoes: {title[:30]}... (Marca: {brand})")
                        else:
                            logging.warning(f"Item Netshoes pulado (sem preço ou link): {title[:30]}...")
                    else:
                        logging.debug(f"Item Netshoes incompleto pulado: {item.select_one('.item-card__description__product-name')}")

        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de conexão ao buscar na Netshoes: {str(e)}")
        except Exception as e:
            logging.error(f"Erro inesperado ao buscar na Netshoes: {str(e)}", exc_info=True)

        sleep(random.uniform(1.5, 3.0))
        logging.info(f"Total de produtos encontrados na Netshoes: {len(results)}")
        return results
    
    def search_supplements(self, query, max_results=5):
        """Busca em todas as lojas disponíveis e combina os resultados."""
        logging.info(f"Iniciando busca por: '{query}' com máximo de {max_results} resultados por loja")
        self.current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Atualiza data/hora da busca

        # Usar dados simulados se 'teste' for a query
        if query.strip().lower() == 'teste':
            logging.warning("Modo de teste ativado: retornando dados simulados.")
            return self._get_mock_data(max_results)

        # Executa as buscas em paralelo (poderia usar threading/asyncio para otimizar)
        amazon_results = self.search_amazon(query, max_results)
        growth_results = self.search_growth_suplementos(query, max_results)
        integralmedica_results = self.search_integralmedica(query, max_results)
        netshoes_results = self.search_netshoes(query, max_results) # Adiciona Netshoes

        # Combina os resultados de todas as lojas
        all_results = amazon_results + growth_results + integralmedica_results + netshoes_results
        # Removendo a ordenação aqui, será feita no main.py conforme seleção do usuário
        # all_results.sort(key=lambda x: x['price'] if x['price'] > 0 else float('inf'))

        logging.info(f"Busca concluída. Total de resultados agregados: {len(all_results)}")
        return all_results

    def _get_mock_data(self, max_count=5):
        """Retorna dados simulados para testes."""
        logging.info(f"Gerando {max_count * 4} dados simulados para testes.") # 4 lojas
        mock_data = [
            {
                'title': 'Whey Protein Concentrado (1kg) - Growth Suplements',
                'price': random.uniform(80, 120),
                'image_url': 'https://via.placeholder.com/150?text=Growth+Whey',
                'link': 'https://www.gsuplementos.com.br/mock/whey-concentrado',
                'store': 'Growth Suplements',
                'brand': 'Growth Suplements',
                'query_date': self.current_date
            },
            {
                'title': 'Creatina Monohidratada (250g) - Growth Suplements',
                'price': random.uniform(60, 90),
                'image_url': 'https://via.placeholder.com/150?text=Growth+Creatina',
                'link': 'https://www.gsuplementos.com.br/mock/creatina',
                'store': 'Growth Suplements',
                'brand': 'Growth Suplements',
                'query_date': self.current_date
            },
            {
                'title': 'Iso Triple Zero (900g) - Integral Medica',
                'price': random.uniform(150, 220),
                'image_url': 'https://via.placeholder.com/150?text=Integral+Iso',
                'link': 'https://www.integralmedica.com.br/mock/iso-triple-zero',
                'store': 'Integral Medica',
                'brand': 'Integral Medica',
                'query_date': self.current_date
            },
            {
                'title': 'BCAA 2400 (100 Caps) - Integral Medica',
                'price': random.uniform(40, 70),
                'image_url': 'https://via.placeholder.com/150?text=Integral+BCAA',
                'link': 'https://www.integralmedica.com.br/mock/bcaa-2400',
                'store': 'Integral Medica',
                'brand': 'Integral Medica',
                'query_date': self.current_date
            },
            {
                'title': 'Gold Standard 100% Whey (907g) - Optimum Nutrition',
                'price': random.uniform(250, 350),
                'image_url': 'https://via.placeholder.com/150?text=Optimum+Whey',
                'link': 'https://www.amazon.com.br/mock/whey-gold-standard',
                'store': 'Amazon',
                'brand': 'Optimum Nutrition',
                'query_date': self.current_date
            },
            {
                'title': 'Creatine Powder (300g) - Optimum Nutrition',
                'price': random.uniform(100, 150),
                'image_url': 'https://via.placeholder.com/150?text=Optimum+Creatine',
                'link': 'https://www.amazon.com.br/mock/creatine-powder',
                'store': 'Amazon',
                'brand': 'Optimum Nutrition',
                'query_date': self.current_date
            },
             {
                'title': 'Whey Protein Isolado Dux Nutrition 900g',
                'price': random.uniform(180, 250),
                'image_url': 'https://via.placeholder.com/150?text=Dux+Whey',
                'link': 'https://www.netshoes.com.br/mock/dux-whey-isolado',
                'store': 'Netshoes',
                'brand': 'Dux Nutrition',
                'query_date': self.current_date
            },
            {
                'title': 'Creatina Max Titanium 300g',
                'price': random.uniform(90, 130),
                'image_url': 'https://via.placeholder.com/150?text=Max+Creatina',
                'link': 'https://www.netshoes.com.br/mock/max-creatina',
                'store': 'Netshoes',
                'brand': 'Max Titanium',
                'query_date': self.current_date
            }
        ]
        # Replica e mistura os dados para simular mais resultados
        full_mock_list = (mock_data * (max_count // 2 + 1))[:max_count * 4] # Garante dados suficientes
        random.shuffle(full_mock_list)
        # Atualiza os preços para serem diferentes
        for item in full_mock_list:
            item['price'] = round(item['price'] * random.uniform(0.95, 1.05), 2)

        return full_mock_list

# Exemplo de uso (para teste local)
if __name__ == '__main__':
    scraper = SupplementScraper()
    # Teste com busca real
    # results = scraper.search_supplements('creatina', max_results=2)
    # print(f"\nResultados da busca por 'creatina':")
    # for res in results:
    #     print(f" - {res['title']} ({res['brand']}) - R$ {res['price']:.2f} [{res['store']}]")

    # Teste com dados simulados
    mock_results = scraper.search_supplements('teste', max_results=3)
    print(f"\nResultados da busca por 'teste' (simulado):")
    for res in mock_results:
        print(f" - {res['title']} ({res['brand']}) - R$ {res['price']:.2f} [{res['store']}] - Data: {res['query_date']}") 