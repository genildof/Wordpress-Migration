import requests
import json
import time
from requests.auth import HTTPBasicAuth
import os
import mimetypes
import base64
import re
import logging
from urllib.parse import urlparse, unquote
from pathlib import Path
import hashlib
import sys

class WordPressMigrator:
    def __init__(self, source_url, dest_url, source_user, source_pass, dest_user, dest_pass):
        """
        Inicializa o migrador com as credenciais dos sites
        """
        # Configura logging detalhado
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('wordpress_migration.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Configura sessão para manter cookies e headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WordPress-Migration-Tool/1.0',
            'Accept': 'application/json'
        })
        
        # Remove trailing slashes e configura URLs
        self.source_url = source_url.rstrip('/')
        self.dest_url = dest_url.rstrip('/')
        self.source_api = f"{self.source_url}/wp-json/wp/v2"
        self.dest_api = f"{self.dest_url}/wp-json/wp/v2"
        self.source_auth = HTTPBasicAuth(source_user, source_pass)
        self.dest_auth = HTTPBasicAuth(dest_user, dest_pass)
        
        # Cache para URLs de imagens
        self.image_cache = {}
        
        # Cria diretório temporário
        self.temp_dir = Path('temp_images')
        self.temp_dir.mkdir(exist_ok=True)
        
        # Flag para API Legacy
        self.use_legacy_api = False

    def check_wordpress_version(self):
        """Verifica a versão do WordPress e configurações do servidor"""
        try:
            # Tenta acessar arquivo de versão do WordPress
            response = self.session.get(f"{self.source_url}/wp-includes/version.php")
            if response.status_code == 200:
                version_match = re.search(r"\$wp_version\s*=\s*'([^']+)'", response.text)
                if version_match:
                    wp_version = version_match.group(1)
                    self.logger.info(f"WordPress version: {wp_version}")
            
            # Verifica configurações do PHP
            response = self.session.get(f"{self.source_url}/wp-admin/admin-ajax.php", 
                                     params={'action': 'php_info'})
            if response.status_code == 200:
                self.logger.info("PHP info acessível")
                
        except Exception as e:
            self.logger.warning(f"Não foi possível verificar versão: {str(e)}")

    def check_api_accessibility(self):
        """Verifica se as APIs estão acessíveis e configuradas corretamente"""
        self.logger.info("Verificando acessibilidade das APIs...")

        # Verifica API de origem
        try:
            # Testa endpoint base
            response = self.session.get(f"{self.source_url}/wp-json")
            self.logger.debug(f"API Base Response: {response.text[:500]}")
            
            if response.status_code != 200:
                raise Exception(f"API de origem não está acessível. Status: {response.status_code}")

            # Testa diferentes endpoints para diagnosticar o problema
            endpoints = [
                '/wp-json/wp/v2/posts',
                '/wp-json/wp/v2/pages',
                '/wp-json/wp/v2/categories',
                '/wp-json/wp/v2/tags'
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(
                        f"{self.source_url}{endpoint}",
                        auth=self.source_auth,
                        params={"per_page": 1}
                    )
                    self.logger.debug(f"Endpoint {endpoint} status: {response.status_code}")
                    self.logger.debug(f"Response: {response.text[:500]}")
                    
                    # Verifica se há erro de autenticação
                    if response.status_code == 500:
                        response_data = response.json()
                        if response_data.get("code") == "incorrect_password":
                            self.logger.error("Erro de autenticação: A senha informada está incorreta.")
                            self.logger.error("Por favor, verifique o usuário e senha fornecidos.")
                            sys.exit(1)  # Encerra o script com código de erro
                    
                except Exception as e:
                    self.logger.error(f"Erro no endpoint {endpoint}: {str(e)}")

            # Tenta usar REST API Legacy se necessário
            if all(response.status_code == 500 for endpoint in endpoints):
                self.logger.warning("Tentando usar REST API Legacy...")
                response = self.session.get(
                    f"{self.source_url}/wp-json/posts",
                    auth=self.source_auth
                )
                if response.status_code == 200:
                    self.use_legacy_api = True
                    self.logger.info("Usando REST API Legacy")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Erro de conexão: {str(e)}")
            raise Exception(f"Erro ao conectar com site de origem: {str(e)}")

        # Verifica configurações do servidor
        self.check_wordpress_version()
        
        self.logger.info("Verificação de APIs concluída!")

    def get_all_posts(self, per_page=5):
        """Obtém todos os posts do site de origem"""
        posts = []
        page = 1
        
        self.logger.info("Iniciando coleta de posts...")
        
        # Define o endpoint baseado no tipo de API
        api_endpoint = f"{self.source_url}/wp-json/posts" if self.use_legacy_api else f"{self.source_api}/posts"
        
        while True:
            try:
                self.logger.debug(f"Buscando página {page} de posts...")
                
                # Parâmetros da requisição
                params = {
                    "page": page,
                    "per_page": per_page,
                    "status": "publish"
                }
                
                # Adiciona campos específicos apenas para API v2
                if not self.use_legacy_api:
                    params["_fields"] = "id,title,content,excerpt,featured_media,categories,tags"
                
                # Faz a requisição com timeout aumentado
                response = self.session.get(
                    api_endpoint,
                    params=params,
                    auth=self.source_auth,
                    timeout=60
                )
                
                # Log da resposta
                self.logger.debug(f"Status Code: {response.status_code}")
                self.logger.debug(f"Headers: {dict(response.headers)}")
                self.logger.debug(f"Response: {response.text[:500]}")
                
                response.raise_for_status()
                current_posts = response.json()
                
                if not current_posts:
                    break
                    
                posts.extend(current_posts)
                self.logger.info(f"Coletados {len(posts)} posts até agora...")
                
                # Verifica se há mais páginas
                if self.use_legacy_api:
                    if len(current_posts) < per_page:
                        break
                else:
                    total_pages = int(response.headers.get('X-WP-TotalPages', 0))
                    if page >= total_pages:
                        break
                
                page += 1
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Erro ao buscar página {page}: {str(e)}")
                self.logger.error(f"Response status: {response.status_code if 'response' in locals() else 'N/A'}")
                self.logger.error(f"Response body: {response.text[:1000] if 'response' in locals() else 'N/A'}")
                raise
                
        self.logger.info(f"Total de {len(posts)} posts coletados.")
        return posts

    def migrate_all_posts(self):
        """Migra todos os posts do site de origem para o site de destino, incluindo imagens"""
        self.logger.info("Iniciando migração de posts...")
        
        # Obtém todos os posts do site de origem
        posts = self.get_all_posts()
        
        # Itera sobre os posts e os envia para o site de destino
        for post in posts:
            try:
                self.logger.info(f"Migrando post: {post.get('title', {}).get('rendered', 'Sem título')}")
                
                # Prepara os dados do post para envio
                post_data = {
                    "title": post.get("title", {}).get("rendered", ""),
                    "content": post.get("content", {}).get("rendered", ""),
                    "excerpt": post.get("excerpt", {}).get("rendered", ""),
                    "status": "publish",  # Define o status do post como "publicado"
                    "categories": post.get("categories", []),
                    "tags": post.get("tags", [])
                }
                
                # Verifica se o post tem uma imagem destacada
                featured_media_id = post.get("featured_media")
                if featured_media_id:
                    self.logger.info(f"Processando imagem destacada (ID: {featured_media_id})...")
                    
                    # Obtém os detalhes da imagem do site de origem
                    media_url = f"{self.source_api}/media/{featured_media_id}"
                    response = self.session.get(media_url, auth=self.source_auth)
                    if response.status_code == 200:
                        media_data = response.json()
                        image_url = media_data.get("source_url")
                        
                        # Baixa a imagem
                        self.logger.info(f"Baixando imagem: {image_url}")
                        image_response = self.session.get(image_url, stream=True)
                        if image_response.status_code == 200:
                            # Envia a imagem para o site de destino
                            self.logger.info("Enviando imagem para o site de destino...")
                            files = {'file': (os.path.basename(image_url), image_response.content)}
                            upload_response = self.session.post(
                                f"{self.dest_api}/media",
                                files=files,
                                auth=self.dest_auth
                            )
                            
                            if upload_response.status_code == 201:
                                new_media_id = upload_response.json().get("id")
                                post_data["featured_media"] = new_media_id
                                self.logger.info(f"Imagem enviada com sucesso! Novo ID: {new_media_id}")
                            else:
                                self.logger.error(f"Erro ao enviar imagem. Status: {upload_response.status_code}")
                                self.logger.error(f"Resposta: {upload_response.text[:1000]}")
                        else:
                            self.logger.error(f"Erro ao baixar imagem. Status: {image_response.status_code}")
                    else:
                        self.logger.error(f"Erro ao obter detalhes da imagem. Status: {response.status_code}")
                
                # Envia o post para o site de destino
                response = self.session.post(
                    f"{self.dest_api}/posts",
                    json=post_data,
                    auth=self.dest_auth,
                    timeout=60
                )
                
                # Verifica se o post foi criado com sucesso
                if response.status_code == 201:
                    self.logger.info(f"Post migrado com sucesso! ID: {response.json().get('id')}")
                else:
                    self.logger.error(f"Erro ao migrar post. Status: {response.status_code}")
                    self.logger.error(f"Resposta: {response.text[:1000]}")
                    
            except Exception as e:
                self.logger.error(f"Erro ao migrar post: {str(e)}")
                raise

        self.logger.info("Migração de posts concluída!")

# Exemplo de uso
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrador de posts WordPress')
    parser.add_argument('--source-url', required=True, help='URL do site de origem')
    parser.add_argument('--dest-url', required=True, help='URL do site de destino')
    parser.add_argument('--source-user', required=True, help='Usuário do site de origem')
    parser.add_argument('--source-pass', required=True, help='Senha do site de origem')
    parser.add_argument('--dest-user', required=True, help='Usuário do site de destino')
    parser.add_argument('--dest-pass', required=True, help='Senha do site de destino')
    
    args = parser.parse_args()
    
    try:
        migrator = WordPressMigrator(
            source_url=args.source_url,
            dest_url=args.dest_url,
            source_user=args.source_user,
            source_pass=args.source_pass,
            dest_user=args.dest_user,
            dest_pass=args.dest_pass
        )
        
        # Verifica APIs antes de começar
        migrator.check_api_accessibility()
        
        # Inicia a migração de posts
        migrator.migrate_all_posts()
        
    except Exception as e:
        print(f"\nErro durante a migração: {str(e)}")
        sys.exit(1)
