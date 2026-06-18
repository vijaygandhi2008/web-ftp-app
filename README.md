# Xi and Xing Feature File Organizer

A Python-based web application to upload and download Xi feature files and Xing .toml files to/from SBNAS.

## Features

- 📤 **Upload Multiple Files**: Upload single or multiple files from your local machine to an SMB/Samba server
- 📁 **Auto Folder Organization**: Xi files are automatically organized into folders based on filename pattern
- 🔍 **Folder Browser**: Browse Xi files by folder using dropdown or search functionality
- 🧩 **Separate Product Pages**: Open Xi and Xing from the home page and manage each workspace separately
- 🧾 **Xing .toml Support**: Upload and download Xing files without automatic folder creation
- 📥 **Bulk Download**: Select multiple files with checkboxes and download as a ZIP archive
- 📂 **Directory Listing**: View all folders and files in the SMB directory with file details (size, modified date)
- 🗑️ **Delete Files**: Remove files from the SMB server
- 🔄 **Refresh**: Update the file list to see the latest changes
- 💅 **Modern UI**: Clean and responsive user interface

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Access to an SMB/Samba server

## Installation

1. Clone the repository:
```bash
git clone https://github.com/vijaygandhi2008/Xi-Feature-File-Organizer.git
cd Xi-Feature-File-Organizer
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Configure SMB settings:
  - Copy `config.example.json` to `config.json`
  - Update the SMB credentials in `config.json` for Xi and, if needed, Xing:
```json
{
  "smb": {
    "server_name": "192.168.8.4",
    "server_ip": "192.168.8.4",
    "share_name": "Ocean",
    "path": "/Inbox/QubeXP/Xi-FeatureFiles",
    "domain": "WORKGROUP",
    "username": "your-username",
    "password": "your-password"
  },
  "xing": {
    "share": "//192.168.8.4/Ocean",
    "path": "/Inbox/QubeXP/Xing-LicenseFiles",
    "domain": "WORKGROUP",
    "user": "your-username",
    "password": "your-password"
  },
  "server": {
    "host": "localhost",
    "port": 3000,
    "debug": false
  }
}
```

**Note**: Configure SBNAS settings:
- `server_name`: SBNAS server hostname (e.g., `192.168.8.4`)
- `server_ip`: SBNAS server IP address (e.g., `192.168.8.4`)
- `share_name`: Root SBNAS share name (e.g., `Ocean`)
- `path`: Subdirectory within the share (e.g., `/Inbox/QubeXP/Xi-FeatureFiles`)
- `xing.path`: Subdirectory within the share for Xing (e.g., `/Inbox/QubeXP/Xing-LicenseFiles`)

## Usage

1. Start the Python Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:3000
```

3. Use the home page to choose a product:
  - **Xi**: Uses the existing folder-organized workflow
  - **Xing**: Opens the .toml workflow without folder creation

4. Use the web interface to:
   - **Upload files**: Select one or multiple files, click "Upload to SBNAS"
     - Files are automatically organized into folders based on the filename pattern: `filename.split('-')[-1].split('.')[0]`
     - Example: `report-data-sales.pdf` will be stored in folder `sales`
     - Example: `feature-file-4k_hfr-304546.xml` will be stored in folder `304546`
  - **Xing uploads**: Select one or multiple `.toml` files and upload them without folder creation into `/Inbox/QubeXP/Xing-LicenseFiles`
   - **Browse folders**: Use the dropdown to select a folder or search for folders by name
   - **View files**: Click "Refresh" to load files from the selected folder
   - **Download single file**: Click the "Download" button next to any file
   - **Download multiple files**: Select files using checkboxes and click "Download Selected" to get a ZIP archive
   - **Delete files**: Click the "Delete" button (with confirmation)

## Configuration

The `config.json` file contains the following settings:

- `smb.server_name`: SBNAS server hostname (e.g., `192.168.8.4`)
- `smb.server_ip`: SBNAS server IP address (e.g., `192.168.8.4`)
- `smb.share_name`: Root SBNAS share name (e.g., `Ocean`)
- `smb.path`: Subdirectory within the share (e.g., `/Inbox/QubeXP/Xi-FeatureFiles`)
- `smb.domain`: SBNAS domain (default: `WORKGROUP`)
- `smb.username`: SBNAS username
- `smb.password`: SBNAS password
- `server.host`: Web server host (default: `localhost`)
- `server.port`: Web server port (default: `5000`)
- `server.debug`: Debug mode (default: `false`)

**Important**: Configure your SBNAS connection correctly:
- Full SBNAS path: `smb://192.168.8.4/Ocean/Inbox/QubeXP/Xi-FeatureFiles`
- Split into: 
  - `server_name`: `192.168.8.4`
  - `server_ip`: `192.168.8.4`
  - `share_name`: `Ocean`
  - `path`: `/Inbox/QubeXP/Xi-FeatureFiles`

## Testing

### Automated Unit Tests

Run the automated test suite to validate all functionality:

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=app

# Run tests in verbose mode
pytest -v
```

**Test Coverage:**
- File upload with folder organization
- Folder navigation (dropdown and search)
- File selection and download
- Complete workflow integration

See [TESTING.md](TESTING.md) for detailed test documentation.

## API Endpoints

The application exposes the following REST API endpoints:

- `POST /api/upload` - Xi upload endpoint kept for compatibility
- `POST /api/xi/upload` - Upload Xi files organized into folders automatically
- `POST /api/xing/upload` - Upload Xing `.toml` files without folder creation into `/Inbox/QubeXP/Xing-LicenseFiles`
- `GET /api/files?folder=<name>` - Xi file list for a folder
- `GET /api/xi/files?folder=<name>` - Xi file list for a folder
- `GET /api/xing/files` - Xing file list for the product root
- `GET /api/directories` - Xi directories in the configured root
- `GET /api/xi/directories` - Xi directories in the configured root
- `GET /api/download/<filename>?folder=<name>` - Xi download endpoint kept for compatibility
- `GET /api/xi/download/<filename>?folder=<name>` - Xi download endpoint
- `GET /api/xing/download/<filename>` - Xing download endpoint
- `POST /api/download-multiple` - Xi ZIP download endpoint kept for compatibility
- `POST /api/xi/download-multiple` - Xi ZIP download endpoint
- `POST /api/xing/download-multiple` - Xing ZIP download endpoint
- `DELETE /api/delete/<filename>` - Xi delete endpoint kept for compatibility
- `DELETE /api/xi/delete/<filename>` - Xi delete endpoint
- `DELETE /api/xing/delete/<filename>` - Xing delete endpoint

See [API.md](API.md) for detailed documentation.

## Technologies Used

- **Backend**: Python 3.8+, Flask
- **SMB Client**: pysmb (pure Python SMB implementation)
- **File Upload**: Flask file handling with Werkzeug
- **Frontend**: HTML5, CSS3, Vanilla JavaScript

## Architecture

- **Python Flask Backend**: RESTful API server with pysmb library for SMB operations
- **pysmb Library**: Well-maintained, pure Python SMB/CIFS library with SMB2/SMB3 support
- **Cross-Platform**: Works on macOS, Windows, and Linux without native dependencies
- **Async Operations**: Efficient file operations with Python's async capabilities

## Security Notes

⚠️ **Important**: 
- Never commit `config.json` with real credentials to version control
- Use environment variables for production deployments
- Implement authentication for the web interface in production
- The application follows Python PEP standards and security best practices

## License

ISC
