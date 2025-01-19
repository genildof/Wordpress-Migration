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
        Initializes the migrator with site credentials
        """
        # Configure detailed logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('wordpress_migration.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Configure session to maintain cookies and headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WordPress-Migration-Tool/1.0',
            'Accept': 'application/json'
        })
        
        # Remove trailing slashes and configure URLs
        self.source_url = source_url.rstrip('/')
        self.dest_url = dest_url.rstrip('/')
        self.source_api = f"{self.source_url}/wp-json/wp/v2"
        self.dest_api = f"{self.dest_url}/wp-json/wp/v2"
        self.source_auth = HTTPBasicAuth(source_user, source_pass)
        self.dest_auth = HTTPBasicAuth(dest_user, dest_pass)
        
        # Cache for image URLs
        self.image_cache = {}
        
        # Create temporary directory
        self.temp_dir = Path('temp_images')
        self.temp_dir.mkdir(exist_ok=True)
        
        # Flag for Legacy API
        self.use_legacy_api = False

    def check_wordpress_version(self):
        """Checks WordPress version and server settings"""
        try:
            # Try to access WordPress version file
            response = self.session.get(f"{self.source_url}/wp-includes/version.php")
            if response.status_code == 200:
                version_match = re.search(r"\$wp_version\s*=\s*'([^']+)'", response.text)
                if version_match:
                    wp_version = version_match.group(1)
                    self.logger.info(f"WordPress version: {wp_version}")
            
            # Check PHP settings
            response = self.session.get(f"{self.source_url}/wp-admin/admin-ajax.php", 
                                     params={'action': 'php_info'})
            if response.status_code == 200:
                self.logger.info("PHP info accessible")
                
        except Exception as e:
            self.logger.warning(f"Could not verify version: {str(e)}")

    def check_api_accessibility(self):
        """Checks if APIs are accessible and properly configured"""
        self.logger.info("Checking API accessibility...")

        # Check source API
        try:
            # Test base endpoint
            response = self.session.get(f"{self.source_url}/wp-json")
            self.logger.debug(f"API Base Response: {response.text[:500]}")
            
            if response.status_code != 200:
                raise Exception(f"Source API is not accessible. Status: {response.status_code}")

            # Test different endpoints to diagnose the problem
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
                    
                    # Check for authentication error
                    if response.status_code == 500:
                        response_data = response.json()
                        if response_data.get("code") == "incorrect_password":
                            self.logger.error("Authentication error: The provided password is incorrect.")
                            self.logger.error("Please verify the provided username and password.")
                            sys.exit(1)  # Exit script with error code
                    
                except Exception as e:
                    self.logger.error(f"Error in endpoint {endpoint}: {str(e)}")

            # Try using Legacy REST API if necessary
            if all(response.status_code == 500 for endpoint in endpoints):
                self.logger.warning("Attempting to use Legacy REST API...")
                response = self.session.get(
                    f"{self.source_url}/wp-json/posts",
                    auth=self.source_auth
                )
                if response.status_code == 200:
                    self.use_legacy_api = True
                    self.logger.info("Using Legacy REST API")

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Connection error: {str(e)}")
            raise Exception(f"Error connecting to source site: {str(e)}")

        # Check server settings
        self.check_wordpress_version()
        
        self.logger.info("API verification completed!")

    def get_all_posts(self, per_page=5):
        """Retrieves all posts from the source site"""
        posts = []
        page = 1
        
        self.logger.info("Starting post collection...")
        
        # Define endpoint based on API type
        api_endpoint = f"{self.source_url}/wp-json/posts" if self.use_legacy_api else f"{self.source_api}/posts"
        
        while True:
            try:
                self.logger.debug(f"Fetching page {page} of posts...")
                
                # Request parameters
                params = {
                    "page": page,
                    "per_page": per_page,
                    "status": "publish"
                }
                
                # Add specific fields only for API v2
                if not self.use_legacy_api:
                    params["_fields"] = "id,title,content,excerpt,featured_media,categories,tags"
                
                # Make request with increased timeout
                response = self.session.get(
                    api_endpoint,
                    params=params,
                    auth=self.source_auth,
                    timeout=60
                )
                
                # Log response
                self.logger.debug(f"Status Code: {response.status_code}")
                self.logger.debug(f"Headers: {dict(response.headers)}")
                self.logger.debug(f"Response: {response.text[:500]}")
                
                response.raise_for_status()
                current_posts = response.json()
                
                if not current_posts:
                    break
                    
                posts.extend(current_posts)
                self.logger.info(f"Collected {len(posts)} posts so far...")
                
                # Check if there are more pages
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
                self.logger.error(f"Error fetching page {page}: {str(e)}")
                self.logger.error(f"Response status: {response.status_code if 'response' in locals() else 'N/A'}")
                self.logger.error(f"Response body: {response.text[:1000] if 'response' in locals() else 'N/A'}")
                raise
                
        self.logger.info(f"Total of {len(posts)} posts collected.")
        return posts

    def migrate_all_posts(self):
        """Migrates all posts from source site to destination site, including images"""
        self.logger.info("Starting post migration...")
        
        # Get all posts from source site
        posts = self.get_all_posts()
        
        # Iterate over posts and send them to destination site
        for post in posts:
            try:
                self.logger.info(f"Migrating post: {post.get('title', {}).get('rendered', 'No title')}")
                
                # Prepare post data for sending
                post_data = {
                    "title": post.get("title", {}).get("rendered", ""),
                    "content": post.get("content", {}).get("rendered", ""),
                    "excerpt": post.get("excerpt", {}).get("rendered", ""),
                    "status": "publish",  # Set post status as "published"
                    "categories": post.get("categories", []),
                    "tags": post.get("tags", [])
                }
                
                # Check if post has a featured image
                featured_media_id = post.get("featured_media")
                if featured_media_id:
                    self.logger.info(f"Processing featured image (ID: {featured_media_id})...")
                    
                    # Get image details from source site
                    media_url = f"{self.source_api}/media/{featured_media_id}"
                    response = self.session.get(media_url, auth=self.source_auth)
                    if response.status_code == 200:
                        media_data = response.json()
                        image_url = media_data.get("source_url")
                        
                        # Download image
                        self.logger.info(f"Downloading image: {image_url}")
                        image_response = self.session.get(image_url, stream=True)
                        if image_response.status_code == 200:
                            # Upload image to destination site
                            self.logger.info("Uploading image to destination site...")
                            files = {'file': (os.path.basename(image_url), image_response.content)}
                            upload_response = self.session.post(
                                f"{self.dest_api}/media",
                                files=files,
                                auth=self.dest_auth
                            )
                            
                            if upload_response.status_code == 201:
                                new_media_id = upload_response.json().get("id")
                                post_data["featured_media"] = new_media_id
                                self.logger.info(f"Image uploaded successfully! New ID: {new_media_id}")
                            else:
                                self.logger.error(f"Error uploading image. Status: {upload_response.status_code}")
                                self.logger.error(f"Response: {upload_response.text[:1000]}")
                        else:
                            self.logger.error(f"Error downloading image. Status: {image_response.status_code}")
                    else:
                        self.logger.error(f"Error getting image details. Status: {response.status_code}")
                
                # Send post to destination site
                response = self.session.post(
                    f"{self.dest_api}/posts",
                    json=post_data,
                    auth=self.dest_auth,
                    timeout=60
                )
                
                # Check if post was created successfully
                if response.status_code == 201:
                    self.logger.info(f"Post migrated successfully! ID: {response.json().get('id')}")
                else:
                    self.logger.error(f"Error migrating post. Status: {response.status_code}")
                    self.logger.error(f"Response: {response.text[:1000]}")
                    
            except Exception as e:
                self.logger.error(f"Error migrating post: {str(e)}")
                raise

        self.logger.info("Post migration completed!")

# Usage example
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='WordPress Post Migrator')
    parser.add_argument('--source-url', required=True, help='Source site URL')
    parser.add_argument('--dest-url', required=True, help='Destination site URL')
    parser.add_argument('--source-user', required=True, help='Source site username')
    parser.add_argument('--source-pass', required=True, help='Source site password')
    parser.add_argument('--dest-user', required=True, help='Destination site username')
    parser.add_argument('--dest-pass', required=True, help='Destination site password')
    
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
        
        # Check APIs before starting
        migrator.check_api_accessibility()
        
        # Start post migration
        migrator.migrate_all_posts()
        
    except Exception as e:
        print(f"\nError during migration: {str(e)}")
        sys.exit(1)
