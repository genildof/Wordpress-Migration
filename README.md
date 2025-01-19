# WordPress Migration Script

This Python script automates the migration of posts (including images, categories, and tags) from one WordPress site to another using the WordPress REST API. It is designed to be secure, controlled, and reliable, ensuring that your content is transferred without depending on plugins or direct database access.

## Features

- Uses WordPress REST API: No need for plugins or direct database access.
- Post-by-Post Migration: Reduces the risk of timeouts or memory errors.
- Handles Embedded Images: Downloads and re-uploads images to the destination site.
- Preserves Categories and Tags: Maintains the structure of your content.
- Error Handling: Includes robust error handling and can resume from where it left off if something fails.
- Rate Limiting: Respects API limits with pauses between requests.

## Requirements

- Python 3.x: Install Python on your computer.
- Requests Library: Install the requests library using `pip install requests`.
- WordPress Application Passwords: Generate application passwords for both the source and destination WordPress sites (can be done via the Application Passwords plugin).

## How to Use

### 1. Install Python and Dependencies

Make sure you have Python 3.x installed. Then, install the required library:

```bash
pip install requests
```

### 2. Configure the Script

Clone this repository or download the script (wordpress-migration.py) to your local machine.

### 3. Run the Script

Execute the script from the command line with the following arguments:

```bash
python wordpress-migration.py \
  --source-url SOURCE_URL \
  --dest-url DEST_URL \
  --source-user SOURCE_USER \
  --source-pass SOURCE_PASS \
  --dest-user DEST_USER \
  --dest-pass DEST_PASS
```

#### Arguments:
- `--source-url`: The URL of the source WordPress site.
- `--dest-url`: The URL of the destination WordPress site.
- `--source-user`: The username for the source WordPress site.
- `--source-pass`: The application password for the source WordPress site.
- `--dest-user`: The username for the destination WordPress site.
- `--dest-pass`: The application password for the destination WordPress site.

#### Example:
```bash
python wordpress-migration.py \
  --source-url https://source-site.com \
  --dest-url https://destination-site.com \
  --source-user admin \
  --source-pass xxxx-xxxx-xxxx-xxxx \
  --dest-user admin \
  --dest-pass yyyy-yyyy-yyyy-yyyy
```

### 4. Monitor the Migration

The script will log its progress to both the console and a file named `wordpress_migration.log`. You can monitor the migration in real-time and review the logs afterward.

## Important Considerations

- **New Posts**: The script creates new posts on the destination site and does not attempt to maintain the original post IDs.
- **Image URLs**: Images are re-uploaded to the destination site, generating new URLs.
- **Test First**: It is recommended to run a test migration with a small number of posts before migrating the entire site.
- **Performance**: The process may be slow due to pauses between API requests to avoid rate limits.

## Customization

This script can be adapted to meet specific needs, such as:

- Migrating custom post types.
- Handling additional metadata.
- Adjusting the rate of API requests.

If you need help customizing the script or have questions about specific parts of the code, feel free to open an issue in this repository or reach out for assistance.

## Code Overview

### Key Functions

**check_api_accessibility()**:
- Verifies that the source and destination WordPress sites are accessible and that the REST API is properly configured.

**get_all_posts()**:
- Retrieves all posts from the source site, including their titles, content, categories, tags, and featured images.

**migrate_all_posts()**:
- Migrates posts from the source site to the destination site, including downloading and re-uploading images.

**Error Handling**:
- The script includes robust error handling to ensure that issues are logged and the migration can be resumed if interrupted.

## License

This project is open-source and available under the MIT License. Feel free to use, modify, and distribute it as needed.

## Contributing

If you would like to contribute to this project, please fork the repository and submit a pull request. Your contributions are welcome!

## Support

If you encounter any issues or have questions, please open an issue in this repository or contact the maintainers.

Happy migrating! 🚀
