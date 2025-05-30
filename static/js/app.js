// Global variables
let selectedFiles = [];
let personFiles = [];
let backgroundFiles = [];
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

    // Person swap process button
    const personSwapProcessBtn = document.getElementById('personSwapProcessBtn');
    if (personSwapProcessBtn) {
        personSwapProcessBtn.addEventListener('click', handlePersonSwapProcess);
    }

    // Frame type change
    const frameTypeInputs = document.querySelectorAll('input[name="frameType"]');
    frameTypeInputs.forEach(input => {
        input.addEventListener('change', handleFrameTypeChange);
    });

    // Frame file upload
    const frameFileInput = document.getElementById('frameFile');
    if (frameFileInput) {
        frameFileInput.addEventListener('change', handleFrameFileSelect);
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

    // Person swap file inputs
    const personFileInput = document.getElementById('personFiles');
    const backgroundFileInput = document.getElementById('backgroundFiles');
    const personDropZone = document.getElementById('personDropZone');
    const backgroundDropZone = document.getElementById('backgroundDropZone');

    if (personFileInput) {
        personFileInput.addEventListener('change', (e) => handlePersonFileSelect(e));
    }
    if (backgroundFileInput) {
        backgroundFileInput.addEventListener('change', (e) => handleBackgroundFileSelect(e));
    }

    // Person drop zone events
    if (personDropZone) {
        personDropZone.addEventListener('dragover', (e) => handlePersonDragOver(e));
        personDropZone.addEventListener('drop', (e) => handlePersonDrop(e));
        personDropZone.addEventListener('click', () => personFileInput?.click());
    }

    // Background drop zone events
    if (backgroundDropZone) {
        backgroundDropZone.addEventListener('dragover', (e) => handleBackgroundDragOver(e));
        backgroundDropZone.addEventListener('drop', (e) => handleBackgroundDrop(e));
        backgroundDropZone.addEventListener('click', () => backgroundFileInput?.click());
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
    event.stopPropagation();
    if (uploadArea) {
        uploadArea.classList.add('drag-over');
    }
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    // Проверяем, действительно ли мы покинули область
    if (uploadArea && !uploadArea.contains(event.relatedTarget)) {
        uploadArea.classList.remove('drag-over');
    }
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    
    if (uploadArea) {
        uploadArea.classList.remove('drag-over');
    }
    
    const files = Array.from(event.dataTransfer.files);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    
    if (imageFiles.length !== files.length) {
        showAlert('Пожалуйста, выберите только изображения', 'warning');
    }
    
    if (imageFiles.length > 0) {
        addFiles(imageFiles);
    }
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
    
    // Для подстановки людей используем отдельную логику
    if (processingType === 'person-swap') {
        updatePersonSwapButton();
        return;
    }
    
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
    const personSwapOptions = document.getElementById('personSwapOptions');
    const collageOptions = document.getElementById('collageOptions');
    const frameOptions = document.getElementById('frameOptions');
    const smartCropOptions = document.getElementById('smartCropOptions');
    const uploadCard = document.querySelector('.card:has(#fileInput)') || document.querySelector('.upload-area')?.closest('.card');
    
    if (backgroundOptions) {
        backgroundOptions.classList.toggle('d-none', processingType !== 'remove-background');
    }
    
    if (personSwapOptions) {
        personSwapOptions.classList.toggle('d-none', processingType !== 'person-swap');
    }
    
    if (collageOptions) {
        collageOptions.classList.toggle('d-none', processingType !== 'create-collage');
    }
    
    if (frameOptions) {
        frameOptions.classList.toggle('d-none', processingType !== 'add-frame');
    }
    
    if (smartCropOptions) {
        smartCropOptions.classList.toggle('d-none', processingType !== 'smart-crop');
    }
    
    // Скрываем стандартную форму загрузки для подстановки людей
    const fileUploadCard = document.querySelector('.card:has(#fileInput)');
    if (!fileUploadCard) {
        // Поиск по тексту заголовка если селектор не работает
        const allCards = document.querySelectorAll('.card');
        allCards.forEach(card => {
            const header = card.querySelector('.card-header');
            if (header && header.textContent.includes('Загрузить фотографии')) {
                card.classList.toggle('d-none', processingType === 'person-swap');
            }
        });
    } else {
        fileUploadCard.classList.toggle('d-none', processingType === 'person-swap');
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
            case 'person-swap':
                result = await processPersonSwap();
                break;
            case 'smart-crop':
                result = await processSmartCrop();
                break;
            case 'social-media':
                result = await processSocialMediaOptimization();
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
    const frameType = document.querySelector('input[name="frameType"]:checked')?.value;
    const frameStyle = document.getElementById('frameStyle')?.value;
    const results = [];
    
    // Проверяем есть ли собственная рамка для загрузки
    if (frameType === 'custom' && !frameFile) {
        showAlert('Загрузите файл рамки', 'warning');
        return results;
    }
    
    updateProgress(10, 'Начинаем обработку...');
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const formData = new FormData();
        formData.append('file', selectedFiles[i]);
        
        if (frameType === 'custom') {
            formData.append('frame_type', 'custom');
            formData.append('frame_file', frameFile);
        } else {
            formData.append('frame_type', 'preset');
            formData.append('frame_style', frameStyle);
        }
        
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

async function processPersonSwap() {
    const results = [];
    
    updateProgress(10, 'Начинаем подстановку людей...');
    
    // Отправляем файлы людей и фонов отдельно
    const formData = new FormData();
    
    // Добавляем файлы людей
    personFiles.forEach((file, index) => {
        formData.append('person_files', file);
    });
    
    // Добавляем файлы фонов
    backgroundFiles.forEach((file, index) => {
        formData.append('background_files', file);
    });
    
    updateProgress(50, 'Обрабатываем изображения...');
    
    // Добавляем токен аутентификации если есть
    const token = localStorage.getItem('token');
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    
    const response = await fetch('/api/person-swap', {
        method: 'POST',
        headers: headers,
        body: formData
    });
    
    if (response.ok) {
        const result = await response.json();
        results.push(...result.results);
    }
    
    updateProgress(100, 'Завершено!');
    
    return results;
}

async function processSmartCrop() {
    const aspectRatio = document.getElementById('aspectRatio')?.value || '1:1';
    const results = [];
    
    updateProgress(10, 'Начинаем умную обрезку...');
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const formData = new FormData();
        formData.append('file', selectedFiles[i]);
        formData.append('aspect_ratio', aspectRatio);
        
        updateProgress(20 + (60 * (i + 1) / selectedFiles.length), `Умная обрезка (${i + 1}/${selectedFiles.length})...`);
        
        // Добавляем токен аутентификации если есть
        const token = localStorage.getItem('token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        
        const response = await fetch('/api/smart-crop', {
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

// Handle person swap process specifically
async function handlePersonSwapProcess() {
    if (personFiles.length === 0 || backgroundFiles.length === 0) {
        showAlert('Загрузите фотографии людей и фоны', 'warning');
        return;
    }

    const personSwapProcessBtn = document.getElementById('personSwapProcessBtn');
    if (personSwapProcessBtn) {
        personSwapProcessBtn.disabled = true;
    }

    showProgressCard();

    try {
        const result = await processPersonSwap();
        console.log('Person swap results:', result);
        showResults(result);
    } catch (error) {
        console.error('Person swap error:', error);
        showAlert('Ошибка при подстановке людей: ' + error.message, 'danger');
    } finally {
        hideProgressCard();
        if (personSwapProcessBtn) {
            personSwapProcessBtn.disabled = false;
        }
    }
}

// Frame handling functions
function handleFrameTypeChange() {
    const frameType = document.querySelector('input[name="frameType"]:checked')?.value;
    const presetOptions = document.getElementById('presetFrameOptions');
    const customOptions = document.getElementById('customFrameOptions');
    
    if (presetOptions && customOptions) {
        if (frameType === 'custom') {
            presetOptions.classList.add('d-none');
            customOptions.classList.remove('d-none');
        } else {
            presetOptions.classList.remove('d-none');
            customOptions.classList.add('d-none');
        }
    }
}

let frameFile = null;

function handleFrameFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        frameFile = file;
        updateFrameFilePreview();
    }
}

function updateFrameFilePreview() {
    const preview = document.getElementById('frameFilePreview');
    if (!preview || !frameFile) return;
    
    preview.innerHTML = `
        <div class="file-item d-flex align-items-center justify-content-between p-2 border rounded">
            <div class="d-flex align-items-center">
                <i class="fas fa-image me-2"></i>
                <span>${frameFile.name}</span>
                <small class="text-muted ms-2">(${formatFileSize(frameFile.size)})</small>
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFrameFile()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
}

function removeFrameFile() {
    frameFile = null;
    const preview = document.getElementById('frameFilePreview');
    const input = document.getElementById('frameFile');
    if (preview) preview.innerHTML = '';
    if (input) input.value = '';
}

// Person swap file handling functions
function handlePersonFileSelect(event) {
    const files = Array.from(event.target.files);
    addPersonFiles(files);
}

function handleBackgroundFileSelect(event) {
    const files = Array.from(event.target.files);
    addBackgroundFiles(files);
}

function handlePersonDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.add('drag-over');
}

function handlePersonDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');
    const files = Array.from(event.dataTransfer.files);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    
    if (imageFiles.length !== files.length) {
        showAlert('Пожалуйста, выберите только изображения', 'warning');
    }
    
    if (imageFiles.length > 0) {
        addPersonFiles(imageFiles);
    }
}

function handleBackgroundDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.add('drag-over');
}

function handleBackgroundDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');
    const files = Array.from(event.dataTransfer.files);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    
    if (imageFiles.length !== files.length) {
        showAlert('Пожалуйста, выберите только изображения', 'warning');
    }
    
    if (imageFiles.length > 0) {
        addBackgroundFiles(imageFiles);
    }
}

function addPersonFiles(files) {
    files.forEach(file => {
        if (file.type.startsWith('image/')) {
            personFiles.push(file);
        }
    });
    updatePersonPreview();
    updatePersonSwapButton();
}

function addBackgroundFiles(files) {
    files.forEach(file => {
        if (file.type.startsWith('image/')) {
            backgroundFiles.push(file);
        }
    });
    updateBackgroundPreview();
    updatePersonSwapButton();
}

function updatePersonPreview() {
    const preview = document.getElementById('personPreview');
    if (!preview) return;
    
    preview.innerHTML = '';
    personFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <img src="${URL.createObjectURL(file)}" alt="Person ${index + 1}">
            <span class="file-name">${file.name}</span>
            <button type="button" class="btn btn-sm btn-danger" onclick="removePersonFile(${index})">
                <i class="fas fa-times"></i>
            </button>
        `;
        preview.appendChild(fileItem);
    });
}

function updateBackgroundPreview() {
    const preview = document.getElementById('backgroundPreview');
    if (!preview) return;
    
    preview.innerHTML = '';
    backgroundFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <img src="${URL.createObjectURL(file)}" alt="Background ${index + 1}">
            <span class="file-name">${file.name}</span>
            <button type="button" class="btn btn-sm btn-danger" onclick="removeBackgroundFile(${index})">
                <i class="fas fa-times"></i>
            </button>
        `;
        preview.appendChild(fileItem);
    });
}

function removePersonFile(index) {
    personFiles.splice(index, 1);
    updatePersonPreview();
    updatePersonSwapButton();
}

function removeBackgroundFile(index) {
    backgroundFiles.splice(index, 1);
    updateBackgroundPreview();
    updatePersonSwapButton();
}

function updatePersonSwapButton() {
    const processingType = document.querySelector('input[name="processingType"]:checked')?.value;
    const personSwapProcessBtn = document.getElementById('personSwapProcessBtn');
    
    if (processingType === 'person-swap' && personSwapProcessBtn) {
        const hasPersons = personFiles.length > 0;
        const hasBackgrounds = backgroundFiles.length > 0;
        
        if (hasPersons && hasBackgrounds) {
            personSwapProcessBtn.classList.remove('d-none');
            personSwapProcessBtn.disabled = false;
        } else {
            personSwapProcessBtn.classList.add('d-none');
            personSwapProcessBtn.disabled = true;
        }
    }
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
    
    let imagesHTML = '';
    let downloadButtons = '';
    
    // Handle social media optimization results
    if (result && result.optimized_versions) {
        console.log('Processing social media optimization results:', result);
        
        imagesHTML = '<div class="row g-3">';
        downloadButtons = '<div class="mb-3"><h5>Скачать по платформам:</h5></div>';
        
        try {
            Object.entries(result.optimized_versions).forEach(([platform, info]) => {
                console.log('Processing platform:', platform, info);
                imagesHTML += `
                    <div class="col-lg-3 col-md-4 col-sm-6 mb-3">
                        <div class="card h-100">
                            <img src="${info.path}" class="card-img-top result-image" alt="${info.name}" style="height: 150px; object-fit: cover;">
                            <div class="card-body p-2">
                                <h6 class="card-title mb-1" style="font-size: 0.85rem;">${info.name}</h6>
                                <small class="text-muted d-block">${info.dimensions}</small>
                                <small class="text-muted">${info.file_size}</small>
                            </div>
                        </div>
                    </div>
                `;
                
                downloadButtons += `
                    <a href="${info.path}" download class="btn btn-outline-primary btn-sm me-2 mb-2">
                        <i class="fas fa-download me-1"></i>
                        ${info.name}
                    </a>
                `;
            });
            
            imagesHTML += '</div>';
            downloadButtons += `
                <div class="mt-3">
                    <small class="text-muted">Создано ${result.total_created} оптимизированных версий из оригинала ${result.original_dimensions}</small>
                </div>
            `;
        } catch (error) {
            console.error('Error processing social media results:', error);
            imagesHTML = '<div class="alert alert-warning">Ошибка отображения результатов</div>';
        }
    }
    // Handle regular results
    else {
        // Поддержка как одного результата, так и массива результатов
        const results = Array.isArray(result) ? result : [result];
        
        console.log('Processing results array:', results);
        
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
    }
    
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
            // Переходим на страницу загрузки после успешной регистрации
            window.location.href = '/upload';
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

async function processSocialMediaOptimization() {
    updateProgress(10, 'Запуск оптимизации для социальных сетей...');
    
    const formData = new FormData();
    formData.append('file', selectedFiles[0]);
    
    updateProgress(30, 'Создание версий для разных платформ...');
    
    const token = localStorage.getItem('token');
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    
    const response = await fetch('/api/social-media-optimize', {
        method: 'POST',
        headers: headers,
        body: formData
    });
    
    if (!response.ok) {
        throw new Error('Ошибка при оптимизации для социальных сетей');
    }
    
    updateProgress(100, 'Оптимизация завершена!');
    const result = await response.json();
    console.log('Social media optimization result:', result);
    return result;
}

// Export functions for global access
window.removeFile = removeFile;
window.resetForm = resetForm;
window.showLoginModal = showLoginModal;
window.showRegisterModal = showRegisterModal;
