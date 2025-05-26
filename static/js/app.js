// Global variables
let selectedFiles = [];
let currentProcessing = null;

// DOM elements
const fileInput = document.getElementById('fileInput');
const filePreview = document.getElementById('filePreview');
const processBtn = document.getElementById('processBtn');
const progressCard = document.getElementById('progressCard');
const resultsCard = document.getElementById('resultsCard');
const uploadArea = document.querySelector('.upload-area');

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    checkAuthStatus();
});

function initializeEventListeners() {
    // File input handling
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelect);
    }

    // Drag and drop
    if (uploadArea) {
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleDrop);
    }

    // Process button
    if (processBtn) {
        processBtn.addEventListener('click', handleProcess);
    }

    // Processing type change
    const processingTypeInputs = document.querySelectorAll('input[name="processingType"]');
    processingTypeInputs.forEach(input => {
        input.addEventListener('change', handleProcessingTypeChange);
    });

    // Collage type change
    const collageTypeSelect = document.getElementById('collageType');
    if (collageTypeSelect) {
        collageTypeSelect.addEventListener('change', handleCollageTypeChange);
    }

    // Auth forms
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
}

// File handling
function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    addFiles(files);
}

function handleDragOver(event) {
    event.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(event) {
    event.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = Array.from(event.dataTransfer.files);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    
    if (imageFiles.length !== files.length) {
        showAlert('Пожалуйста, выберите только изображения', 'warning');
    }
    
    addFiles(imageFiles);
}

function addFiles(files) {
    // Validate file types and sizes
    const validFiles = files.filter(file => {
        if (!file.type.startsWith('image/')) {
            showAlert(`Файл ${file.name} не является изображением`, 'warning');
            return false;
        }
        
        if (file.size > 10 * 1024 * 1024) { // 10MB
            showAlert(`Файл ${file.name} слишком большой (более 10 МБ)`, 'warning');
            return false;
        }
        
        return true;
    });

    selectedFiles = [...selectedFiles, ...validFiles];
    updateFilePreview();
    updateProcessButton();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFilePreview();
    updateProcessButton();
}

function updateFilePreview() {
    if (!filePreview) return;
    
    filePreview.innerHTML = '';
    
    selectedFiles.forEach((file, index) => {
        const previewItem = document.createElement('div');
        previewItem.className = 'file-preview-item fade-in';
        
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        img.alt = file.name;
        
        previewItem.innerHTML = `
            <img src="${URL.createObjectURL(file)}" alt="${file.name}">
            <div class="file-info">
                <div class="fw-bold">${file.name}</div>
                <small class="text-muted">${formatFileSize(file.size)}</small>
            </div>
            <div class="file-actions">
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFile(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        filePreview.appendChild(previewItem);
    });
}

function updateProcessButton() {
    if (!processBtn) return;
    
    const processingType = document.querySelector('input[name="processingType"]:checked')?.value;
    const requiredFiles = getRequiredFilesCount(processingType);
    
    if (selectedFiles.length >= requiredFiles) {
        processBtn.classList.remove('d-none');
        processBtn.disabled = false;
    } else {
        processBtn.classList.add('d-none');
        processBtn.disabled = true;
    }
}

function getRequiredFilesCount(processingType) {
    if (processingType === 'create-collage') {
        const collageType = document.getElementById('collageType')?.value;
        const requirements = { 
            'polaroid': 1, 
            '5x15': 3, 
            '5x5': 2,
            'magazine': 1,
            'passport': 1,
            'filmstrip': 1,
            'grid': 1,
            'vintage': 1,
            'universal': 1
        };
        return requirements[collageType] || 1;
    }
    return 1;
}

function handleProcessingTypeChange() {
    const processingType = document.querySelector('input[name="processingType"]:checked')?.value;
    
    // Show/hide options
    const backgroundOptions = document.getElementById('backgroundOptions');
    const collageOptions = document.getElementById('collageOptions');
    const frameOptions = document.getElementById('frameOptions');
    
    if (backgroundOptions) {
        backgroundOptions.classList.toggle('d-none', processingType !== 'remove-background');
    }
    
    if (collageOptions) {
        collageOptions.classList.toggle('d-none', processingType !== 'create-collage');
    }
    
    if (frameOptions) {
        frameOptions.classList.toggle('d-none', processingType !== 'add-frame');
    }
    
    updateProcessButton();
}

function handleCollageTypeChange() {
    const collageType = document.getElementById('collageType')?.value;
    const captionInput = document.getElementById('captionInput');
    
    if (captionInput) {
        captionInput.style.display = collageType === 'polaroid' ? 'block' : 'none';
    }
    
    updateProcessButton();
}

// Image processing
async function handleProcess() {
    const processingType = document.querySelector('input[name="processingType"]:checked')?.value;
    
    if (!processingType || selectedFiles.length === 0) {
        showAlert('Выберите файлы и тип обработки', 'warning');
        return;
    }
    
    processBtn.disabled = true;
    showProgressCard();
    
    try {
        let result;
        
        switch (processingType) {
            case 'remove-background':
                result = await processRemoveBackground();
                break;
            case 'create-collage':
                result = await processCreateCollage();
                break;
            case 'add-frame':
                result = await processAddFrame();
                break;
            case 'retouch':
                result = await processRetouch();
                break;
            default:
                throw new Error('Неизвестный тип обработки');
        }
        
        console.log('Showing results:', result);
        showResults(result);
        
    } catch (error) {
        console.error('Processing error:', error);
        showAlert('Ошибка при обработке изображения: ' + error.message, 'danger');
    } finally {
        hideProgressCard();
        processBtn.disabled = false;
    }
}

async function processRemoveBackground() {
    const bgMethod = document.querySelector('input[name="bgMethod"]:checked')?.value || 'rembg';
    const results = [];
    
    updateProgress(10, 'Начинаем обработку...');
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const formData = new FormData();
        formData.append('file', selectedFiles[i]);
        formData.append('method', bgMethod);
        
        updateProgress(20 + (60 * (i + 1) / selectedFiles.length), `Удаление фона (${i + 1}/${selectedFiles.length})...`);
        
        // Добавляем токен аутентификации если есть
        const token = localStorage.getItem('token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        
        const response = await fetch('/api/remove-background', {
            method: 'POST',
            headers: headers,
            body: formData
        });
        
        console.log(`Response ${i + 1} status:`, response.status);
        
        if (response.ok) {
            const result = await response.json();
            console.log(`Received result ${i + 1}:`, result);
            results.push(result);
        } else {
            const errorText = await response.text();
            console.error(`Error processing file ${i + 1}:`, response.status, errorText);
        }
    }
    
    updateProgress(100, 'Завершено!');
    
    console.log('All results collected:', results);
    return results.length === 1 ? results[0] : results;
}

async function processCreateCollage() {
    const collageType = document.getElementById('collageType')?.value;
    const caption = document.getElementById('caption')?.value || '';
    
    updateProgress(20, 'Подготовка изображений...');
    
    const formData = new FormData();
    formData.append('collage_type', collageType);
    formData.append('caption', caption);
    
    selectedFiles.forEach(file => {
        formData.append('files', file);
    });
    
    updateProgress(60, 'Создание коллажа...');
    
    const response = await fetchWithAuth('/api/create-collage', {
        method: 'POST',
        body: formData
    });
    
    updateProgress(100, 'Завершено!');
    
    return response;
}

async function processAddFrame() {
    const frameStyle = document.getElementById('frameStyle')?.value;
    const results = [];
    
    updateProgress(10, 'Начинаем обработку...');
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const formData = new FormData();
        formData.append('file', selectedFiles[i]);
        formData.append('frame_style', frameStyle);
        
        updateProgress(20 + (60 * (i + 1) / selectedFiles.length), `Добавление рамки (${i + 1}/${selectedFiles.length})...`);
        
        // Добавляем токен аутентификации если есть
        const token = localStorage.getItem('token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        
        const response = await fetch('/api/add-frame', {
            method: 'POST',
            headers: headers,
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            results.push(result);
        }
    }
    
    updateProgress(100, 'Завершено!');
    
    return results.length === 1 ? results[0] : results;
}

async function processRetouch() {
    const results = [];
    
    updateProgress(10, 'Начинаем обработку...');
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const formData = new FormData();
        formData.append('file', selectedFiles[i]);
        
        updateProgress(20 + (60 * (i + 1) / selectedFiles.length), `Ретушь изображения (${i + 1}/${selectedFiles.length})...`);
        
        // Добавляем токен аутентификации если есть
        const token = localStorage.getItem('token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        
        const response = await fetch('/api/retouch', {
            method: 'POST',
            headers: headers,
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            results.push(result);
        }
    }
    
    updateProgress(100, 'Завершено!');
    
    return results.length === 1 ? results[0] : results;
}

// Progress handling
function showProgressCard() {
    if (progressCard) {
        progressCard.classList.remove('d-none');
    }
    if (resultsCard) {
        resultsCard.classList.add('d-none');
    }
}

function hideProgressCard() {
    if (progressCard) {
        progressCard.classList.add('d-none');
    }
}

function updateProgress(percentage, text) {
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.getElementById('progressText');
    
    if (progressBar) {
        progressBar.style.width = percentage + '%';
    }
    
    if (progressText) {
        progressText.textContent = text;
    }
}

function showResults(result) {
    if (!resultsCard) return;
    
    const resultsContent = document.getElementById('resultsContent');
    
    console.log('showResults received:', result);
    
    // Поддержка как одного результата, так и массива результатов
    const results = Array.isArray(result) ? result : [result];
    
    console.log('Processing results array:', results);
    
    let imagesHTML = '';
    let downloadButtons = '';
    
    results.forEach((res, index) => {
        console.log(`Processing result ${index}:`, res);
        
        // Поддержка разных форматов ответа API
        const outputPath = res.output_path || res.processed_path || (res.success && res.output_path);
        
        console.log(`Output path for result ${index}:`, outputPath);
        
        if (outputPath) {
            imagesHTML += `
                <div class="col-md-6 mb-3">
                    <img src="${outputPath}" class="result-image w-100" alt="Обработанное изображение ${index + 1}">
                </div>
            `;
            downloadButtons += `
                <a href="${outputPath}" download class="btn btn-primary me-2 mb-2">
                    <i class="fas fa-download me-2"></i>
                    Скачать ${results.length > 1 ? `фото ${index + 1}` : 'результат'}
                </a>
            `;
        }
    });
    
    console.log('Generated HTML:', { imagesHTML, downloadButtons });
    
    resultsContent.innerHTML = `
        <div class="text-center">
            <div class="row justify-content-center mb-3">
                ${imagesHTML}
            </div>
            <div class="d-flex flex-wrap justify-content-center gap-2">
                ${downloadButtons}
                <button type="button" class="btn btn-outline-secondary" onclick="resetForm()">
                    <i class="fas fa-redo me-2"></i>
                    Обработать еще
                </button>
            </div>
        </div>
    `;
    
    resultsCard.classList.remove('d-none');
    resultsCard.scrollIntoView({ behavior: 'smooth' });
}

function resetForm() {
    selectedFiles = [];
    updateFilePreview();
    updateProcessButton();
    
    if (fileInput) {
        fileInput.value = '';
    }
    
    if (resultsCard) {
        resultsCard.classList.add('d-none');
    }
    
    if (progressCard) {
        progressCard.classList.add('d-none');
    }
}

// Authentication
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('token', data.access_token);
            showAlert('Вход выполнен успешно!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('loginModal')).hide();
            updateAuthStatus(true);
        } else {
            showAlert(data.detail || 'Ошибка входа', 'danger');
        }
    } catch (error) {
        console.error('Login error:', error);
        showAlert('Ошибка подключения к серверу', 'danger');
    }
}

async function handleRegister(event) {
    event.preventDefault();
    
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            localStorage.setItem('token', data.access_token);
            showAlert('Регистрация выполнена успешно!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('registerModal')).hide();
            updateAuthStatus(true);
        } else {
            showAlert(data.detail || 'Ошибка регистрации', 'danger');
        }
    } catch (error) {
        console.error('Register error:', error);
        showAlert('Ошибка подключения к серверу', 'danger');
    }
}

function checkAuthStatus() {
    const token = localStorage.getItem('token');
    updateAuthStatus(!!token);
}

function updateAuthStatus(isAuthenticated) {
    // Update navigation based on auth status
    // This is a simple implementation, you might want to make it more sophisticated
    console.log('Auth status:', isAuthenticated);
}

// Utility functions
async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('token');
    
    if (token) {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${token}`
        };
    }
    
    const response = await fetch(url, options);
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Ошибка сервера');
    }
    
    return response.json();
}

function showAlert(message, type = 'info') {
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Modal functions
function showLoginModal() {
    const modal = new bootstrap.Modal(document.getElementById('loginModal'));
    modal.show();
}

function showRegisterModal() {
    const modal = new bootstrap.Modal(document.getElementById('registerModal'));
    modal.show();
    
    // Hide login modal if it's open
    const loginModal = bootstrap.Modal.getInstance(document.getElementById('loginModal'));
    if (loginModal) {
        loginModal.hide();
    }
}

// Export functions for global access
window.removeFile = removeFile;
window.resetForm = resetForm;
window.showLoginModal = showLoginModal;
window.showRegisterModal = showRegisterModal;
