# WordPress Post Migrator 🚀

A powerful Python script for migrating posts between WordPress sites using the WordPress REST API. This tool handles complete post migration, including featured images, categories, and tags.

## Features 🌟

- Complete post migration between WordPress sites ✨
- Featured image handling and transfer 🖼️
- Support for both modern and legacy WordPress REST APIs 🔄
- Detailed logging system for troubleshooting 📝
- Rate limiting and error handling 🛡️
- Command-line interface for easy usage 💻

## Prerequisites 📋

Before using the script, ensure you have:

- Python 3.6 or higher installed
- Access to both source and destination WordPress sites
- Administrator credentials for both sites
- WordPress REST API enabled on both sites

Required Python packages:
```bash
pip install requests
```

## Configuration 🔧

The script requires the following parameters:

- Source site URL
- Destination site URL
- Source site username and password
- Destination site username and password

## Usage 🚀

Basic usage through command line:

```bash
python wordpress_migrator.py \
  --source-url "https://source-site.com" \
  --dest-url "https://destination-site.com" \
  --source-user "admin" \
  --source-pass "your-password" \
  --dest-user "admin" \
  --dest-pass "your-password"
```

## How It Works 🛠️

### 1. Initialization
The script starts by setting up logging and creating necessary session headers:

```python
migrator = WordPressMigrator(
    source_url="https://source-site.com",
    dest_url="https://destination-site.com",
    source_user="admin",
    source_pass="password",
    dest_user="admin",
    dest_pass="password"
)
```

### 2. API Verification
Before migration, the script:
- Checks WordPress version
- Verifies API accessibility
- Tests authentication
- Determines API version (modern or legacy)

### 3. Post Migration Process
For each post, the script:
1. Retrieves post content and metadata
2. Downloads featured images
3. Uploads images to destination site
4. Creates new post with all content
5. Maintains categories and tags
6. Verifies successful migration

## Error Handling 🔍

The script includes comprehensive error handling:
- Connection issues
- Authentication failures
- API limitations
- Image processing errors
- Rate limiting

Error logs are saved to `wordpress_migration.log` for troubleshooting.

## Best Practices 📌

1. **Backup First** 💾
   Always backup both sites before migration.

2. **Test Run** 🧪
   Test with a small number of posts first:
   ```python
   # In the code, modify the get_all_posts method
   def get_all_posts(self, per_page=5):
       # This will limit the initial fetch
   ```

3. **Rate Limiting** ⏲️
   The script includes built-in delays to prevent overwhelming the servers:
   ```python
   time.sleep(2)  # 2-second delay between requests
   ```

## Limitations ⚠️

- Does not migrate comments
- Does not migrate custom post types (only standard posts)
- Media files must be publicly accessible
- Requires direct access to both WordPress installations

## Troubleshooting 🔧

Common issues and solutions:

1. **API Not Accessible**
   - Verify WordPress REST API is enabled
   - Check permalinks settings
   - Ensure no security plugins are blocking API access

2. **Authentication Failures**
   - Verify credentials
   - Check user permissions
   - Ensure application passwords are enabled if using them

3. **Image Transfer Issues**
   - Check file permissions
   - Verify media upload settings
   - Ensure enough disk space is available

## Logging 📝

The script generates detailed logs in `wordpress_migration.log`:
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wordpress_migration.log'),
        logging.StreamHandler()
    ]
)
```

## Contributing 🤝

Feel free to contribute to this project by:
- Reporting bugs
- Suggesting enhancements
- Adding new features
- Improving documentation

## Security Note 🔒

- Never store credentials in the script
- Use environment variables or secure configuration files
- Always use HTTPS for API connections
- Implement proper error handling for sensitive operations

## Support ℹ️

For issues and questions:
1. Check the logging output
2. Verify WordPress configuration
3. Ensure all prerequisites are met
4. Check WordPress REST API documentation

Remember to always backup your data before performing any migration! 🔄
