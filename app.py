"""
Flask application for SMB/Samba file management.
Supports separate Xi and Xing pages while keeping Xi API routes compatible.
"""

import json
import zipfile
from io import BytesIO

from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from smb.SMBConnection import SMBConnection
from smb.smb_structs import OperationFailure
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

PRODUCTS = {'xi', 'xing'}


def load_config():
    """Load configuration from config.json."""
    try:
        with open('config.json', 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        print('Warning: config.json not found, using defaults')
        return {
            'smb': {
                'share': '//192.168.8.4/Ocean',
                'path': '/Inbox/QubeXP/Xi-FeatureFiles',
                'domain': 'WORKGROUP',
                'user': 'username',
                'password': 'password'
            },
            'xing': {
                'share': '//192.168.8.4/Ocean',
                'path': '/Inbox/QubeXP/Xing-LicenseFiles',
                'domain': 'WORKGROUP',
                'user': 'username',
                'password': 'password'
            },
            'server': {
                'port': 3000,
                'debug': False
            }
        }


config = load_config()


def normalize_product(product):
    """Validate and normalize the requested product name."""
    normalized = (product or 'xi').lower()
    if normalized not in PRODUCTS:
        raise ValueError(f'Unsupported product: {product}')
    return normalized


def parse_smb_share(share_path):
    """Parse SMB share path to extract host and share name."""
    clean_path = share_path.replace('\\', '/').lstrip('/')
    parts = clean_path.split('/')
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None


def get_product_config(product):
    """Return the SMB settings for a product."""
    normalized = normalize_product(product)

    if normalized == 'xi':
        smb_config = config.get('smb', {})
        return {
            'name': 'xi',
            'display_name': 'Xi',
            'page_title': 'Xi-IMB Feature File Organizer',
            'description': 'Upload and download Xi feature files to/from SBNAS',
            'share': smb_config.get('share', ''),
            'path': smb_config.get('path', ''),
            'domain': smb_config.get('domain', 'WORKGROUP'),
            'user': smb_config.get('user', 'username'),
            'password': smb_config.get('password', 'password'),
            'requires_folder_from_filename': True,
            'allowed_extensions': None
        }

    xing_config = config.get('xing', {})
    fallback_config = config.get('smb', {})
    return {
        'name': 'xing',
        'display_name': 'Xing',
        'page_title': 'Xing License File Organizer',
        'description': 'Upload and download Xing License files to/from SBNAS',
        'share': xing_config.get('share', fallback_config.get('share', '')),
        'path': xing_config.get('path', '/'),
        'domain': xing_config.get('domain', fallback_config.get('domain', 'WORKGROUP')),
        'user': xing_config.get('user', fallback_config.get('user', 'username')),
        'password': xing_config.get('password', fallback_config.get('password', 'password')),
        'requires_folder_from_filename': False,
        'allowed_extensions': ['.toml']
    }


def get_smb_connection(product='xi'):
    """Create and return an authenticated SMB connection for a product."""
    product_config = get_product_config(product)
    host, share_name = parse_smb_share(product_config['share'])

    if not host or not share_name:
        raise ValueError(f"Invalid SMB share format for {product}: {product_config['share']}")

    connection = SMBConnection(
        username=product_config['user'],
        password=product_config['password'],
        my_name='web-smb-app',
        remote_name=host.split('.')[0],
        domain=product_config.get('domain', 'WORKGROUP'),
        use_ntlm_v2=True,
        is_direct_tcp=True
    )

    if not connection.connect(host, 445):
        raise ConnectionError(f'Failed to connect to SMB server: {host}')

    return connection, share_name, product_config


def get_remote_path(base_path, folder=''):
    """Combine base path with a folder to get the full remote path."""
    normalized_base_path = (base_path or '').replace('\\', '/').strip('/')
    normalized_folder = (folder or '').replace('\\', '/').strip('/')

    if normalized_folder:
        return f'{normalized_base_path}/{normalized_folder}' if normalized_base_path else normalized_folder
    return normalized_base_path


def extract_folder_from_filename(filename):
    """Extract folder name from a Xi filename."""
    try:
        parts = filename.split('-')
        if len(parts) > 1:
            last_part = parts[-1]
            folder_name = last_part.split('.')[0]
            return folder_name if folder_name else None
    except Exception as error:
        print(f'Error extracting folder from filename {filename}: {error}')
    return None


def is_allowed_extension(filename, allowed_extensions):
    """Check if a filename has one of the allowed extensions."""
    if not allowed_extensions:
        return True
    lower_name = filename.lower()
    return any(lower_name.endswith(extension) for extension in allowed_extensions)


def json_error(message, status_code=500):
    """Return a JSON error response."""
    return jsonify({'success': False, 'error': message}), status_code


def try_store_file(connection, share_name, remote_path, file_obj):
    """Try common SMB path formats when storing a file."""
    normalized_path = (remote_path or '').replace('\\', '/').strip('/')
    path_candidates = [normalized_path, f'/{normalized_path}' if normalized_path else '/']

    last_error = None
    for path_candidate in path_candidates:
        file_obj.seek(0)
        try:
            connection.storeFile(share_name, path_candidate, file_obj)
            return path_candidate
        except Exception as error:
            last_error = error

    raise last_error


def ensure_remote_directory(connection, share_name, remote_path):
    """Ensure a remote SMB directory exists."""
    normalized_path = (remote_path or '').replace('\\', '/').strip('/')
    if not normalized_path:
        return

    current_path = ''
    for path_part in normalized_path.split('/'):
        current_path = f'{current_path}/{path_part}' if current_path else path_part

        try:
            connection.listPath(share_name, current_path)
        except (OperationFailure, Exception):
            try:
                connection.createDirectory(share_name, current_path)
            except (OperationFailure, Exception):
                # If another request created it between the list and create calls,
                # continue without failing the upload.
                pass


def list_directories_for_product(product):
    """List directories for a product."""
    connection = None
    try:
        connection, share_name, product_config = get_smb_connection(product)
        remote_path = get_remote_path(product_config['path'])

        try:
            entries = connection.listPath(share_name, remote_path if remote_path else '/')
            directories = []
            for entry in entries:
                if entry.isDirectory and entry.filename not in ['.', '..']:
                    directories.append(entry.filename)

            return jsonify({'success': True, 'directories': sorted(directories)})
        finally:
            connection.close()
    except Exception as error:
        print(f'List directories error for {product}: {error}')
        return json_error(str(error))


def list_files_for_product(product):
    """List files for a product."""
    connection = None
    try:
        folder = request.args.get('folder', '') if normalize_product(product) == 'xi' else ''
        connection, share_name, product_config = get_smb_connection(product)
        remote_path = get_remote_path(product_config['path'], folder)

        try:
            entries = connection.listPath(share_name, remote_path if remote_path else '/')
            files = []
            for entry in entries:
                if not entry.isDirectory:
                    files.append({
                        'name': entry.filename,
                        'size': entry.file_size,
                        'modified': entry.last_write_time
                    })

            return jsonify({
                'success': True,
                'files': files,
                'folder': folder,
                'product': normalize_product(product)
            })
        finally:
            connection.close()
    except Exception as error:
        print(f'List files error for {product}: {error}')
        return json_error(str(error))


def upload_files_for_product(product):
    """Upload files for a product."""
    connection = None
    try:
        if 'files' not in request.files:
            return json_error('No files provided', 400)

        files = request.files.getlist('files')
        if not files:
            return json_error('No files selected', 400)

        product_name = normalize_product(product)
        connection, share_name, product_config = get_smb_connection(product_name)
        uploaded_files = []
        errors = []

        try:
            for file in files:
                if file.filename == '':
                    continue

                filename = secure_filename(file.filename)

                if not is_allowed_extension(filename, product_config['allowed_extensions']):
                    errors.append(f'{filename}: Unsupported file extension')
                    continue

                if product_name == 'xi':
                    folder = extract_folder_from_filename(filename)
                    if not folder:
                        errors.append(f'{filename}: Could not extract folder name')
                        continue

                    remote_path = get_remote_path(product_config['path'], folder)
                    try:
                        ensure_remote_directory(connection, share_name, remote_path)
                    except Exception as error:
                        print(f'Error creating folder {remote_path}: {error}')
                        errors.append(f'{filename}: Failed to create folder {folder}')
                        continue

                    target_folder = folder
                else:
                    remote_path = get_remote_path(product_config['path'])
                    try:
                        ensure_remote_directory(connection, share_name, remote_path)
                    except Exception as error:
                        print(f'Error creating Xing base folder {remote_path}: {error}')
                        errors.append(f'{filename}: Failed to prepare upload folder')
                        continue
                    target_folder = ''

                try:
                    file_path = f'{remote_path}/{filename}'.replace('//', '/')
                    file_obj = BytesIO(file.read())
                    stored_path = try_store_file(connection, share_name, file_path, file_obj)
                    uploaded_files.append({
                        'filename': filename,
                        'folder': target_folder,
                        'product': product_name
                    })
                    print(f'Uploaded {filename} for {product_name} to {file_path}')
                    print(f'Uploaded {filename} for {product_name} to {stored_path}')
                except Exception as error:
                    print(f'Error uploading {filename}: {error}')
                    errors.append(f'{filename}: {error}')

            return jsonify({
                'success': len(uploaded_files) > 0,
                'files': uploaded_files,
                'uploaded': uploaded_files,
                'errors': errors,
                'count': len(uploaded_files),
                'product': product_name
            })
        finally:
            connection.close()
    except Exception as error:
        print(f'Upload error for {product}: {error}')
        return json_error(str(error))


def download_file_for_product(product, filename):
    """Download a single file for a product."""
    connection = None
    try:
        product_name = normalize_product(product)
        folder = request.args.get('folder', '') if product_name == 'xi' else ''
        connection, share_name, product_config = get_smb_connection(product_name)
        remote_path = get_remote_path(product_config['path'], folder)
        file_path = f'{remote_path}/{filename}'.replace('//', '/')

        try:
            file_obj = BytesIO()
            connection.retrieveFile(share_name, file_path, file_obj)
            file_obj.seek(0)

            return send_file(
                file_obj,
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
        finally:
            connection.close()
    except Exception as error:
        print(f'Download error for {product}: {error}')
        return json_error(str(error))


def download_multiple_for_product(product):
    """Download multiple files as a ZIP archive for a product."""
    connection = None
    try:
        data = request.json or {}
        files = data.get('files', [])
        folder = data.get('folder', '') if normalize_product(product) == 'xi' else ''

        if not files:
            return json_error('No files specified', 400)

        product_name = normalize_product(product)
        connection, share_name, product_config = get_smb_connection(product_name)
        remote_path = get_remote_path(product_config['path'], folder)

        try:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename in files:
                    try:
                        file_path = f'{remote_path}/{filename}'.replace('//', '/')
                        file_obj = BytesIO()
                        connection.retrieveFile(share_name, file_path, file_obj)
                        file_obj.seek(0)
                        zip_file.writestr(filename, file_obj.read())
                    except Exception as error:
                        print(f'Error adding {filename} to ZIP for {product_name}: {error}')

            zip_buffer.seek(0)
            zip_name = f"{product_name}-files-{folder if folder else 'root'}.zip"
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name=zip_name,
                mimetype='application/zip'
            )
        finally:
            connection.close()
    except Exception as error:
        print(f'Download multiple error for {product}: {error}')
        return json_error(str(error))


def delete_file_for_product(product, filename):
    """Delete a file for a product."""
    connection = None
    try:
        product_name = normalize_product(product)
        folder = request.args.get('folder', '') if product_name == 'xi' else ''
        connection, share_name, product_config = get_smb_connection(product_name)
        remote_path = get_remote_path(product_config['path'], folder)
        file_path = f'{remote_path}/{filename}'.replace('//', '/')

        try:
            connection.deleteFiles(share_name, file_path)
            return jsonify({'success': True, 'message': f'File {filename} deleted successfully', 'product': product_name})
        finally:
            connection.close()
    except Exception as error:
        print(f'Delete error for {product}: {error}')
        return json_error(str(error))


@app.route('/')
def index():
    """Serve the product landing page."""
    return send_from_directory('public', 'index.html')


@app.route('/xi')
@app.route('/xi/')
def xi_page():
    """Serve the Xi page."""
    return send_from_directory('public', 'xi.html')


@app.route('/xing')
@app.route('/xing/')
def xing_page():
    """Serve the Xing page."""
    return send_from_directory('public', 'xing.html')


@app.route('/api/<product>/directories', methods=['GET'])
@app.route('/api/directories', methods=['GET'])
def list_directories(product='xi'):
    return list_directories_for_product(product)


@app.route('/api/<product>/files', methods=['GET'])
@app.route('/api/files', methods=['GET'])
def list_files(product='xi'):
    return list_files_for_product(product)


@app.route('/api/<product>/upload', methods=['POST'])
@app.route('/api/upload', methods=['POST'])
def upload_files(product='xi'):
    return upload_files_for_product(product)


@app.route('/api/<product>/download/<filename>', methods=['GET'])
@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename, product='xi'):
    return download_file_for_product(product, filename)


@app.route('/api/<product>/download-multiple', methods=['POST'])
@app.route('/api/download-multiple', methods=['POST'])
def download_multiple(product='xi'):
    return download_multiple_for_product(product)


@app.route('/api/<product>/delete/<filename>', methods=['DELETE'])
@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_file(filename, product='xi'):
    return delete_file_for_product(product, filename)


if __name__ == '__main__':
    server_config = config.get('server', {})
    port = server_config.get('port', 5000)
    debug_mode = server_config.get('debug', False)
    print(f'Starting Flask server on port {port}')
    print(f"Xi SMB Share: {config.get('smb', {}).get('share', '')}")
    print(f"Xi SMB Path: {config.get('smb', {}).get('path', '/')}")
    if 'xing' in config:
        print(f"Xing SMB Share: {config.get('xing', {}).get('share', '')}")
        print(f"Xing SMB Path: {config.get('xing', {}).get('path', '/')}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)