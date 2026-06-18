const product = (document.body.dataset.product || 'xi').toLowerCase();
const apiBase = product === 'xing' ? '/api/xing' : '/api/xi';
const supportsFolders = product === 'xi';

let currentFolder = '';
let allFolders = [];
let selectedFiles = new Set();

function pageTitle() {
    return product === 'xing' ? 'Xing License File Organizer' : 'Xi-IMB Feature File Organizer';
}

function pageDescription() {
    return product === 'xing'
        ? 'Upload and download Xing license files to/from SBNAS'
        : 'Upload and download Xi feature files to/from SBNAS';
}

function uploadLabel() {
    return product === 'xing' ? 'Upload Xing License Files' : 'Upload Xi Feature Files';
}

function filesHeading() {
    return product === 'xing' ? '⬇️ Xing License Files Downloader' : '⬇️ Xi Feature Files Downloader';
}

function fileInputAccept() {
    return product === 'xing' ? '.toml' : '*/*';
}

function folderDisplayValue() {
    return currentFolder || 'Root';
}

function filesUrl() {
    if (!supportsFolders || !currentFolder) {
        return `${apiBase}/files`;
    }
    return `${apiBase}/files?folder=${encodeURIComponent(currentFolder)}`;
}

function downloadUrl(filename) {
    if (!supportsFolders || !currentFolder) {
        return `${apiBase}/download/${encodeURIComponent(filename)}`;
    }
    return `${apiBase}/download/${encodeURIComponent(filename)}?folder=${encodeURIComponent(currentFolder)}`;
}

function deleteUrl(filename) {
    if (!supportsFolders || !currentFolder) {
        return `${apiBase}/delete/${encodeURIComponent(filename)}`;
    }
    return `${apiBase}/delete/${encodeURIComponent(filename)}?folder=${encodeURIComponent(currentFolder)}`;
}

function archiveName() {
    if (!supportsFolders || !currentFolder) {
        return `${product}-files.zip`;
    }
    return `${currentFolder}.zip`;
}

function setHeaderContent() {
    const titleElement = document.getElementById('pageTitle');
    const descriptionElement = document.getElementById('pageDescription');
    const uploadHeadingElement = document.getElementById('uploadHeading');
    const filesHeadingElement = document.getElementById('filesHeading');
    const uploadButton = document.getElementById('uploadButton');
    const fileInput = document.getElementById('fileInput');

    if (titleElement) titleElement.textContent = pageTitle();
    if (descriptionElement) descriptionElement.textContent = pageDescription();
    if (uploadHeadingElement) uploadHeadingElement.textContent = product === 'xing' ? '📤 Xing License Files Uploader' : '📤 Xi Feature Files Uploader';
    if (filesHeadingElement) filesHeadingElement.textContent = filesHeading();
    if (uploadButton) uploadButton.textContent = uploadLabel();
    if (fileInput) fileInput.accept = fileInputAccept();
}

function setupLayout() {
    const folderControls = document.getElementById('folderControls');
    const currentFolderDisplay = document.getElementById('currentFolderDisplay');
    const currentFolderName = document.getElementById('currentFolderName');
    const selectAllLabel = document.querySelector('.select-all-label');

    if (supportsFolders) {
        if (folderControls) folderControls.classList.remove('hidden');
        if (currentFolderDisplay) currentFolderDisplay.classList.remove('hidden');
        if (selectAllLabel) selectAllLabel.classList.remove('hidden');
        if (currentFolderName) currentFolderName.textContent = folderDisplayValue();
    } else {
        if (folderControls) folderControls.classList.add('hidden');
        if (currentFolderDisplay) currentFolderDisplay.classList.add('hidden');
        if (selectAllLabel) selectAllLabel.classList.add('hidden');
    }
}

async function uploadFiles() {
    const fileInput = document.getElementById('fileInput');
    const statusDiv = document.getElementById('uploadStatus');

    if (!fileInput || !fileInput.files.length) {
        showStatus('Please select at least one file to upload', 'error');
        return;
    }

    const formData = new FormData();
    for (const file of fileInput.files) {
        formData.append('files', file);
    }

    try {
        if (statusDiv) statusDiv.innerHTML = '<p>Uploading...</p>';

        const response = await fetch(`${apiBase}/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(`✓ ${(data.count ?? data.files?.length ?? 0)} file(s) uploaded successfully!`, 'success');
            fileInput.value = '';
            setTimeout(() => {
                loadFolders();
                refreshFileList();
            }, 300);
        } else {
            showStatus(`✗ Upload failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`✗ Upload failed: ${error.message}`, 'error');
    }
}

async function loadFolders() {
    if (!supportsFolders) return;

    try {
        const response = await fetch(`${apiBase}/directories`);
        const data = await response.json();

        if (response.ok) {
            allFolders = data.directories || [];
            updateFolderDropdown(allFolders);
        }
    } catch (error) {
        console.error('Failed to load folders:', error);
    }
}

function updateFolderDropdown(folders) {
    const select = document.getElementById('folderSelect');
    if (!select) return;

    const previousValue = select.value;
    select.innerHTML = '<option value="">Select folder from dropdown</option>';

    folders.forEach(folder => {
        const option = document.createElement('option');
        option.value = folder;
        option.textContent = folder;
        select.appendChild(option);
    });

    if (previousValue && folders.includes(previousValue)) {
        select.value = previousValue;
    }
}

function filterFolders() {
    if (!supportsFolders) return;

    const searchInput = document.getElementById('folderSearch');
    if (!searchInput) return;

    const term = searchInput.value.toLowerCase();
    if (!term) {
        updateFolderDropdown(allFolders);
        return;
    }

    const filtered = allFolders.filter(folder => folder.toLowerCase().includes(term));
    updateFolderDropdown(filtered);

    if (filtered.length === 1) {
        const select = document.getElementById('folderSelect');
        if (select) {
            select.value = filtered[0];
            onFolderChange();
        }
    }
}

function onFolderChange() {
    if (!supportsFolders) return;

    const select = document.getElementById('folderSelect');
    if (!select) return;

    currentFolder = select.value;
    const currentFolderName = document.getElementById('currentFolderName');
    if (currentFolderName) {
        currentFolderName.textContent = folderDisplayValue();
    }

    selectedFiles.clear();
    updateSelectedCount();
    refreshFileList();
}

async function refreshFileList() {
    const filesListDiv = document.getElementById('filesList');
    if (!filesListDiv) return;

    if (supportsFolders && !currentFolder) {
        filesListDiv.innerHTML = '<p class="empty">Please select a folder from the dropdown to view files</p>';
        return;
    }

    try {
        filesListDiv.innerHTML = '<p class="loading">Loading files...</p>';

        const response = await fetch(filesUrl());
        const data = await response.json();

        if (response.ok && data.files) {
            if (data.files.length === 0) {
                filesListDiv.innerHTML = product === 'xing'
                    ? '<p class="empty">No Xing files found</p>'
                    : '<p class="empty">No files found in this folder</p>';
                return;
            }

            filesListDiv.innerHTML = '';
            data.files.forEach(file => filesListDiv.appendChild(createFileItem(file)));
        } else {
            filesListDiv.innerHTML = `<p class="error">Failed to load files: ${data.error || 'Unknown error'}</p>`;
        }
    } catch (error) {
        filesListDiv.innerHTML = `<p class="error">Failed to load files: ${error.message}</p>`;
    }
}

function createFileItem(file) {
    const item = document.createElement('div');
    item.className = 'file-item';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'file-checkbox';
    checkbox.onchange = event => {
        if (event.target.checked) {
            selectedFiles.add(file.name);
        } else {
            selectedFiles.delete(file.name);
        }
        updateSelectedCount();
    };

    const info = document.createElement('div');
    info.className = 'file-info';

    const name = document.createElement('div');
    name.className = 'file-name';
    name.textContent = file.name;

    const meta = document.createElement('div');
    meta.className = 'file-meta';
    meta.textContent = `Size: ${formatFileSize(file.size)} | Modified: ${formatDate(file.modified)}`;

    info.appendChild(name);
    info.appendChild(meta);

    const actions = document.createElement('div');
    actions.className = 'file-actions';

    const downloadButton = document.createElement('button');
    downloadButton.className = 'btn btn-download';
    downloadButton.textContent = '⬇ Download';
    downloadButton.onclick = () => downloadFile(file.name);

    actions.appendChild(downloadButton);

    item.appendChild(checkbox);
    item.appendChild(info);
    item.appendChild(actions);

    return item;
}

function updateSelectedCount() {
    const count = selectedFiles.size;
    const selectedCount = document.getElementById('selectedCount');
    const downloadSelectedBtn = document.getElementById('downloadSelectedBtn');

    if (selectedCount) selectedCount.textContent = count;
    if (downloadSelectedBtn) downloadSelectedBtn.disabled = count === 0;

    const checkboxes = document.querySelectorAll('.file-checkbox');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (selectAllCheckbox && checkboxes.length > 0) {
        selectAllCheckbox.checked = checkboxes.length === count;
        selectAllCheckbox.indeterminate = count > 0 && count < checkboxes.length;
    }
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    if (!selectAllCheckbox) return;

    const checkboxes = document.querySelectorAll('.file-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
        const fileName = checkbox.closest('.file-item').querySelector('.file-name').textContent;
        if (selectAllCheckbox.checked) {
            selectedFiles.add(fileName);
        } else {
            selectedFiles.delete(fileName);
        }
    });

    updateSelectedCount();
}

async function downloadSelected() {
    if (selectedFiles.size === 0) {
        showDownloadStatus('Please select at least one file', 'error');
        return;
    }

    try {
        const response = await fetch(`${apiBase}/download-multiple`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                files: Array.from(selectedFiles),
                folder: supportsFolders ? currentFolder : ''
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = url;
            anchor.download = archiveName();
            document.body.appendChild(anchor);
            anchor.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(anchor);

            showDownloadStatus(`✓ ${selectedFiles.size} file(s) downloaded successfully!`, 'success');
            selectedFiles.clear();
            updateSelectedCount();
            document.querySelectorAll('.file-checkbox').forEach(checkbox => (checkbox.checked = false));
            const selectAllCheckbox = document.getElementById('selectAllCheckbox');
            if (selectAllCheckbox) selectAllCheckbox.checked = false;
        } else {
            const data = await response.json();
            showDownloadStatus(`✗ Download failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showDownloadStatus(`✗ Download failed: ${error.message}`, 'error');
    }
}

async function downloadFile(filename) {
    try {
        window.location.href = downloadUrl(filename);
        showDownloadStatus(`✓ File "${filename}" download started`, 'success');
    } catch (error) {
        showDownloadStatus(`✗ Download failed: ${error.message}`, 'error');
    }
}

async function deleteFile(filename) {
    try {
        const response = await fetch(deleteUrl(filename), { method: 'DELETE' });
        const data = await response.json();

        if (response.ok) {
            showDownloadStatus(`✓ ${data.message}`, 'success');
            refreshFileList();
        } else {
            showDownloadStatus(`✗ Delete failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showDownloadStatus(`✗ Delete failed: ${error.message}`, 'error');
    }
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('uploadStatus');
    if (!statusDiv) return;

    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;

    setTimeout(() => {
        statusDiv.textContent = '';
        statusDiv.className = 'status-message';
    }, 5000);
}

function showDownloadStatus(message, type) {
    const statusDiv = document.getElementById('downloadStatus');
    if (!statusDiv) return;

    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;

    setTimeout(() => {
        statusDiv.textContent = '';
        statusDiv.className = 'status-message';
    }, 5000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const base = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const index = Math.floor(Math.log(bytes) / Math.log(base));
    return `${Math.round((bytes / Math.pow(base, index)) * 100) / 100} ${sizes[index]}`;
}

function formatDate(value) {
    if (!value) return 'N/A';
    return new Date(value).toLocaleString();
}

window.addEventListener('DOMContentLoaded', () => {
    setHeaderContent();
    setupLayout();

    if (supportsFolders) {
        loadFolders();
    }

    refreshFileList();
});