import requests
from bs4 import BeautifulSoup
import re
import random
from time import sleep
from urllib.parse import quote
import logging

# Configurar logging para depuração
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SupplementScraper:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.138 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 Edg/113.0.0.0'
        ]
    
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
    
    def search_amazon(self, query, max_results=5):
        search_query = quote(query)
        url = f"https://www.amazon.com.br/s?k={search_query}&i=drugstore"
        
        results = []
        try:
            logging.info(f"Buscando na Amazon: {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            logging.info(f"Status code Amazon: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tente diferentes seletores para produtos da Amazon, pois eles mudam com frequência
                items = soup.select('.s-result-item[data-asin]:not([data-asin=""])')
                logging.info(f"Encontrados {len(items)} itens na Amazon")
                
                if not items:
                    # Tente outro seletor comum
                    items = soup.select('.sg-col-inner .s-widget-container')
                    logging.info(f"Segundo seletor: encontrados {len(items)} itens na Amazon")
                
                count = 0
                for item in items:
                    if count >= max_results:
                        break
                    
                    # Try multiple selectors for each element as they might change
                    title_element = item.select_one('h2 .a-link-normal') or item.select_one('.a-size-base-plus') or item.select_one('.a-size-medium')
                    price_element = item.select_one('.a-price .a-offscreen') or item.select_one('.a-price')
                    image_element = item.select_one('img.s-image') or item.select_one('.s-image')
                    link_element = item.select_one('h2 a') or item.select_one('.a-link-normal[href*="/dp/"]')
                    
                    if title_element and price_element and link_element:
                        title = title_element.text.strip()
                        price_text = price_element.text.strip()
                        
                        # Logging para depuração
                        logging.info(f"Título Amazon: {title}")
                        logging.info(f"Preço Amazon texto: {price_text}")
                        
                        # Clean price text and convert to float - handle different formats
                        try:
                            # Remove tudo exceto números e vírgula decimal
                            price_clean = re.search(r'R?\$?\s*(\d+[,.]\d+|\d+)', price_text)
                            if price_clean:
                                price_str = price_clean.group(1).replace('.', '').replace(',', '.')
                                price = float(price_str)
                            else:
                                price = 0.0
                                
                            logging.info(f"Preço convertido: {price}")
                        except Exception as e:
                            logging.error(f"Erro ao converter preço: {str(e)}")
                            price = 0.0
                        
                        # Para a imagem, use um placeholder se não encontrar
                        image_url = image_element.get('src') if image_element else "https://via.placeholder.com/150"
                        
                        # Para o link, construa a URL completa
                        if link_element:
                            href = link_element.get('href')
                            product_link = "https://www.amazon.com.br" + href if not href.startswith('http') else href
                        else:
                            continue  # Pule este item se não tiver link
                        
                        results.append({
                            'title': title,
                            'price': price,
                            'image_url': image_url,
                            'link': product_link,
                            'store': 'Amazon'
                        })
                        count += 1
                        logging.info(f"Adicionado produto Amazon: {title}")
                
        except Exception as e:
            logging.error(f"Erro ao buscar na Amazon: {str(e)}")
        
        # Add small delay to prevent rate limiting
        sleep(1.5)
        logging.info(f"Total de produtos encontrados na Amazon: {len(results)}")
        return results
    
    def search_growth_suplementos(self, query, max_results=5):
        search_query = quote(query)
        url = f"https://www.gsuplementos.com.br/busca/?busca={search_query}"
        
        results = []
        try:
            logging.info(f"Buscando na Growth: {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            logging.info(f"Status code Growth: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Tente diferentes seletores para a Growth
                items = soup.select('.prateleira .product-item')
                if not items:
                    items = soup.select('.prateleira li')
                
                logging.info(f"Encontrados {len(items)} itens na Growth")
                
                count = 0
                for item in items:
                    if count >= max_results:
                        break
                    
                    title_element = item.select_one('.product-name') or item.select_one('.nome-produto')
                    price_element = item.select_one('.preco-por strong') or item.select_one('.preco')
                    image_element = item.select_one('.product-image img') or item.select_one('img')
                    link_element = item.select_one('.product-image') or item.select_one('a[href*="product"]')
                    
                    if title_element and price_element:
                        title = title_element.text.strip()
                        price_text = price_element.text.strip()
                        
                        # Logging para depuração
                        logging.info(f"Título Growth: {title}")
                        logging.info(f"Preço Growth texto: {price_text}")
                        
                        # Clean price text and convert to float - handle different formats
                        try:
                            price_clean = re.search(r'R?\$?\s*(\d+[,.]\d+|\d+)', price_text)
                            if price_clean:
                                price_str = price_clean.group(1).replace('.', '').replace(',', '.')
                                price = float(price_str)
                            else:
                                price = 0.0
                                
                            logging.info(f"Preço convertido: {price}")
                        except Exception as e:
                            logging.error(f"Erro ao converter preço: {str(e)}")
                            price = 0.0
                        
                        # Para a imagem, use um placeholder se não encontrar
                        image_url = image_element.get('src') if image_element else "https://via.placeholder.com/150"
                        
                        # Para o link
                        if link_element:
                            href = link_element.get('href')
                            product_link = href
                        else:
                            continue  # Pule este item se não tiver link
                        
                        results.append({
                            'title': title,
                            'price': price,
                            'image_url': image_url,
                            'link': product_link,
                            'store': 'Growth Suplementos'
                        })
                        count += 1
                        logging.info(f"Adicionado produto Growth: {title}")
                
        except Exception as e:
            logging.error(f"Erro ao buscar na Growth Suplementos: {str(e)}")
        
        # Add small delay to prevent rate limiting
        sleep(1.5)
        logging.info(f"Total de produtos encontrados na Growth: {len(results)}")
        return results
    
    def search_integralmedica(self, query, max_results=5):
        """Adicionar outra loja popular para aumentar as chances de resultados"""
        search_query = quote(query)
        url = f"https://www.integralmedica.com.br/catalogsearch/result/?q={search_query}"
        
        results = []
        try:
            logging.info(f"Buscando na Integral Medica: {url}")
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            logging.info(f"Status code Integral Medica: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('.product-item-info')
                logging.info(f"Encontrados {len(items)} itens na Integral Medica")
                
                count = 0
                for item in items:
                    if count >= max_results:
                        break
                    
                    title_element = item.select_one('.product-item-link')
                    price_element = item.select_one('.price')
                    image_element = item.select_one('.product-image-photo')
                    link_element = item.select_one('.product-item-link')
                    
                    if title_element and price_element:
                        title = title_element.text.strip()
                        price_text = price_element.text.strip()
                        
                        # Logging para depuração
                        logging.info(f"Título Integral: {title}")
                        logging.info(f"Preço Integral texto: {price_text}")
                        
                        # Clean price text and convert to float
                        try:
                            price_clean = re.search(r'R?\$?\s*(\d+[,.]\d+|\d+)', price_text)
                            if price_clean:
                                price_str = price_clean.group(1).replace('.', '').replace(',', '.')
                                price = float(price_str)
                            else:
                                price = 0.0
                                
                            logging.info(f"Preço convertido: {price}")
                        except Exception as e:
                            logging.error(f"Erro ao converter preço: {str(e)}")
                            price = 0.0
                        
                        # Para a imagem, use um placeholder se não encontrar
                        image_url = image_element.get('src') if image_element else "https://via.placeholder.com/150"
                        
                        # Para o link
                        if link_element:
                            product_link = link_element.get('href')
                        else:
                            continue  # Pule este item se não tiver link
                        
                        results.append({
                            'title': title,
                            'price': price,
                            'image_url': image_url,
                            'link': product_link,
                            'store': 'Integral Medica'
                        })
                        count += 1
                        logging.info(f"Adicionado produto Integral: {title}")
                
        except Exception as e:
            logging.error(f"Erro ao buscar na Integral Medica: {str(e)}")
        
        # Add small delay to prevent rate limiting
        sleep(1.5)
        logging.info(f"Total de produtos encontrados na Integral Medica: {len(results)}")
        return results
    
    def search_supplements(self, query, max_results=5):
        """Busca em todas as lojas disponíveis"""
        logging.info(f"Iniciando busca por: '{query}' com máximo de {max_results} resultados por loja")
        
        # Usar dados simulados se estiver em modo de desenvolvimento
        if query.strip().lower() == 'teste':
            logging.info("Modo de teste ativado: retornando dados simulados")
            return self._get_mock_data(max_results)
        
        # Buscar em todas as lojas
        amazon_results = self.search_amazon(query, max_results)
        growth_results = self.search_growth_suplementos(query, max_results)
        integralmedica_results = self.search_integralmedica(query, max_results)
        
        # Combine and sort results by price
        all_results = amazon_results + growth_results + integralmedica_results
        all_results.sort(key=lambda x: x['price'] if x['price'] > 0 else float('inf'))
        
        logging.info(f"Total de resultados encontrados em todas as lojas: {len(all_results)}")
        return all_results
    
    def _get_mock_data(self, max_count=5):
        """Retorna dados simulados para testes quando real scraping falha"""
        logging.info("Gerando dados simulados para testes")
        mock_data = [
            {
                'title': 'Whey Protein Concentrado (1kg) - Growth Supplements',
                'price': 89.90,
                'image_url': 'https://via.placeholder.com/150',
                'link': 'https://www.gsuplementos.com.br/whey-protein-concentrado-1kg-growth-supplements-p985828',
                'store': 'Growth Suplementos'
            },
            {
                'title': 'Creatina Monohidratada (300g) - Growth Supplements',
                'price': 69.90,
                'image_url': 'https://via.placeholder.com/150',
                'link': 'https://www.gsuplementos.com.br/creatina-monohidratada-300g-growth-supplements',
                'store': 'Growth Suplementos'
            },
            {
                'title': 'Whey Protein Isolado (1kg) - Integral Médica',
                'price': 119.90,
                'image_url': 'https://via.placeholder.com/150',
                'link': 'https://www.integralmedica.com.br/whey-protein-isolado-1kg',
                'store': 'Integral Medica'
            },
            {
                'title': 'BCAA 2400 - 200 Cápsulas - Integral Médica',
                'price': 49.90,
                'image_url': 'https://via.placeholder.com/150',
                'link': 'https://www.integralmedica.com.br/bcaa-2400-200-capsulas',
                'store': 'Integral Medica'
            },
            {
                'title': 'Whey Gold Standard 100% (900g) - Optimum Nutrition',
                'price': 199.90,
                'image_url': 'https://via.placeholder.com/150',
                'link': 'https://www.amazon.com.br/Whey-Gold-Standard-900g-Optimum-Nutrition',
                'store': 'Amazon'
            },
            {
                'title': 'Creatina (300g) - Optimum Nutrition',
                'price': 89.90,
                'image_url': 'https://via.placeholder.com/150',
                'link': 'https://www.amazon.com.br/Creatina-300g-Optimum-Nutrition',
                'store': 'Amazon'
            }
        ]
        # Retorna apenas o número solicitado de resultados
        return mock_data[:max_count*3]  # max_count por loja, 3 lojas 