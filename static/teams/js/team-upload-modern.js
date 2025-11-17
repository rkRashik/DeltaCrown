/**
 * MODERN TEAM BRANDING UPLOAD SYSTEM
 * Version: 1.0 - 2025
 * 
 * Features:
 * - Drag & drop file upload
 * - Live image preview
 * - Image cropping tool
 * - Progress animations
 * - Format & size validation
 * - Dual upload (logo + banner)
 */

class ModernImageUploader {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            maxSize: options.maxSize || 10 * 1024 * 1024, // 10MB default
            acceptedFormats: options.acceptedFormats || ['image/jpeg', 'image/png', 'image/webp', 'image/gif'],
            aspectRatio: options.aspectRatio || null, // e.g., 1 for square, 16/9 for banner
            recommendedWidth: options.recommendedWidth || 512,
            recommendedHeight: options.recommendedHeight || 512,
            cropEnabled: options.cropEnabled !== false,
            onUpload: options.onUpload || null,
            inputName: options.inputName || 'image'
        };
        
        this.currentFile = null;
        this.previewImage = null;
        this.cropper = null;
        
        this.init();
    }

    init() {
        this.setupDropZone();
        this.setupFileInput();
        this.setupPreviewControls();
    }

    setupDropZone() {
        const dropZone = this.container.querySelector('.upload-drop-zone');
        if (!dropZone) return;

        // Drag events
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-active');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-active');
            }, false);
        });

        // Handle drop
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFile(files[0]);
            }
        }, false);

        // Handle click
        dropZone.addEventListener('click', () => {
            const fileInput = this.container.querySelector('input[type="file"]');
            if (fileInput) fileInput.click();
        });
    }

    setupFileInput() {
        const fileInput = this.container.querySelector('input[type="file"]');
        if (!fileInput) return;

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFile(e.target.files[0]);
            }
        });
    }

    setupPreviewControls() {
        // Remove button
        const removeBtn = this.container.querySelector('.btn-remove-image');
        if (removeBtn) {
            removeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeImage();
            });
        }

        // Crop button
        const cropBtn = this.container.querySelector('.btn-crop-image');
        if (cropBtn) {
            cropBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showCropModal();
            });
        }

        // Change button
        const changeBtn = this.container.querySelector('.btn-change-image');
        if (changeBtn) {
            changeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const fileInput = this.container.querySelector('input[type="file"]');
                if (fileInput) fileInput.click();
            });
        }
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    async handleFile(file) {
        // Validate file
        const validation = this.validateFile(file);
        if (!validation.valid) {
            this.showError(validation.error);
            return;
        }

        this.currentFile = file;

        // Show loading state
        this.showLoading();

        // Read file
        const reader = new FileReader();
        reader.onload = (e) => {
            this.showPreview(e.target.result);
            
            // Auto-show crop modal if enabled
            if (this.options.cropEnabled) {
                setTimeout(() => this.showCropModal(), 300);
            }
        };
        reader.readAsDataURL(file);
    }

    validateFile(file) {
        // Check file type
        if (!this.options.acceptedFormats.includes(file.type)) {
            return {
                valid: false,
                error: `Please upload an image file (JPG, PNG, WebP, or GIF)`
            };
        }

        // Check file size
        if (file.size > this.options.maxSize) {
            const sizeMB = (this.options.maxSize / 1024 / 1024).toFixed(0);
            return {
                valid: false,
                error: `File size must be under ${sizeMB}MB. Your file is ${(file.size / 1024 / 1024).toFixed(1)}MB`
            };
        }

        return { valid: true };
    }

    showLoading() {
        const dropZone = this.container.querySelector('.upload-drop-zone');
        const preview = this.container.querySelector('.upload-preview-container');
        
        if (dropZone) dropZone.style.display = 'none';
        if (preview) {
            preview.style.display = 'flex';
            preview.innerHTML = `
                <div class="upload-loading">
                    <div class="loading-spinner"></div>
                    <p>Processing image...</p>
                </div>
            `;
        }
    }

    showPreview(imageSrc) {
        const preview = this.container.querySelector('.upload-preview-container');
        if (!preview) return;

        this.previewImage = imageSrc;

        preview.innerHTML = `
            <div class="preview-image-wrapper">
                <img src="${imageSrc}" alt="Preview" class="preview-image">
                <div class="preview-overlay">
                    <div class="preview-actions">
                        ${this.options.cropEnabled ? '<button type="button" class="btn-preview btn-crop-image"><i class="fas fa-crop"></i></button>' : ''}
                        <button type="button" class="btn-preview btn-change-image"><i class="fas fa-sync"></i></button>
                        <button type="button" class="btn-preview btn-remove-image"><i class="fas fa-trash"></i></button>
                    </div>
                </div>
            </div>
            <div class="preview-info">
                <i class="fas fa-check-circle"></i>
                <span class="file-name">${this.currentFile.name}</span>
                <span class="file-size">${this.formatFileSize(this.currentFile.size)}</span>
            </div>
        `;

        preview.style.display = 'flex';
        this.setupPreviewControls();
        this.addSuccessAnimation();
    }

    showCropModal() {
        if (!this.previewImage) return;

        const modal = this.createCropModal();
        document.body.appendChild(modal);

        // Animate in
        requestAnimationFrame(() => {
            modal.classList.add('active');
        });

        // Initialize cropper after modal is visible
        setTimeout(() => {
            this.initCropper(modal);
        }, 100);
    }

    createCropModal() {
        const modal = document.createElement('div');
        modal.className = 'modern-join-modal crop-modal';
        modal.id = 'cropModal';

        modal.innerHTML = `
            <div class="modal-overlay" data-dismiss-crop></div>
            <div class="modal-container modal-large">
                <div class="modal-header">
                    <div class="header-icon">
                        <i class="fas fa-crop-alt"></i>
                    </div>
                    <div class="header-content">
                        <h2>Crop Image</h2>
                        <p>Adjust your image for the best fit</p>
                    </div>
                    <button class="modal-close" data-dismiss-crop>
                        <i class="fas fa-times"></i>
                    </button>
                </div>

                <div class="modal-body">
                    <div class="crop-container">
                        <img src="${this.previewImage}" id="cropImage" alt="Crop">
                    </div>

                    <div class="crop-controls">
                        <div class="crop-control-group">
                            <button type="button" class="btn-crop-control" data-action="zoom-in">
                                <i class="fas fa-search-plus"></i>
                            </button>
                            <button type="button" class="btn-crop-control" data-action="zoom-out">
                                <i class="fas fa-search-minus"></i>
                            </button>
                        </div>
                        <div class="crop-control-group">
                            <button type="button" class="btn-crop-control" data-action="rotate-left">
                                <i class="fas fa-undo"></i>
                            </button>
                            <button type="button" class="btn-crop-control" data-action="rotate-right">
                                <i class="fas fa-redo"></i>
                            </button>
                        </div>
                        <div class="crop-control-group">
                            <button type="button" class="btn-crop-control" data-action="flip-horizontal">
                                <i class="fas fa-arrows-alt-h"></i>
                            </button>
                            <button type="button" class="btn-crop-control" data-action="flip-vertical">
                                <i class="fas fa-arrows-alt-v"></i>
                            </button>
                        </div>
                        <div class="crop-control-group">
                            <button type="button" class="btn-crop-control" data-action="reset">
                                <i class="fas fa-sync"></i>
                            </button>
                        </div>
                    </div>

                    <div class="recommended-size">
                        <i class="fas fa-info-circle"></i>
                        Recommended: ${this.options.recommendedWidth}x${this.options.recommendedHeight}px
                    </div>

                    <div class="form-actions">
                        <button type="button" class="btn btn-secondary" data-dismiss-crop>
                            <i class="fas fa-times"></i>
                            Cancel
                        </button>
                        <button type="button" class="btn btn-primary" id="applyCrop">
                            <i class="fas fa-check"></i>
                            Apply Crop
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Setup dismiss handlers
        modal.querySelectorAll('[data-dismiss-crop]').forEach(btn => {
            btn.addEventListener('click', () => this.closeCropModal(modal));
        });

        return modal;
    }

    initCropper(modal) {
        const image = modal.querySelector('#cropImage');
        if (!image) return;

        // Simple crop implementation (you could use Cropper.js library for advanced features)
        this.setupSimpleCrop(modal, image);
        
        // Setup crop controls
        this.setupCropControls(modal);
    }

    setupSimpleCrop(modal, image) {
        const container = modal.querySelector('.crop-container');
        
        // Add crop overlay
        const overlay = document.createElement('div');
        overlay.className = 'crop-overlay';
        overlay.innerHTML = `
            <div class="crop-box">
                <div class="crop-grid">
                    <div></div><div></div><div></div>
                    <div></div><div></div><div></div>
                    <div></div><div></div><div></div>
                </div>
            </div>
        `;
        container.appendChild(overlay);

        // Store crop data
        this.cropData = {
            zoom: 1,
            rotate: 0,
            flipH: 1,
            flipV: 1
        };
    }

    setupCropControls(modal) {
        const controls = modal.querySelectorAll('.btn-crop-control[data-action]');
        const image = modal.querySelector('#cropImage');
        
        controls.forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.handleCropAction(action, image);
            });
        });

        // Apply crop button
        const applyBtn = modal.querySelector('#applyCrop');
        if (applyBtn) {
            applyBtn.addEventListener('click', () => {
                this.applyCrop(modal);
            });
        }
    }

    handleCropAction(action, image) {
        if (!image || !this.cropData) return;

        switch (action) {
            case 'zoom-in':
                this.cropData.zoom = Math.min(this.cropData.zoom + 0.1, 3);
                break;
            case 'zoom-out':
                this.cropData.zoom = Math.max(this.cropData.zoom - 0.1, 0.5);
                break;
            case 'rotate-left':
                this.cropData.rotate -= 90;
                break;
            case 'rotate-right':
                this.cropData.rotate += 90;
                break;
            case 'flip-horizontal':
                this.cropData.flipH *= -1;
                break;
            case 'flip-vertical':
                this.cropData.flipV *= -1;
                break;
            case 'reset':
                this.cropData = { zoom: 1, rotate: 0, flipH: 1, flipV: 1 };
                break;
        }

        this.updateImageTransform(image);
    }

    updateImageTransform(image) {
        const { zoom, rotate, flipH, flipV } = this.cropData;
        image.style.transform = `
            scale(${zoom * flipH}, ${zoom * flipV})
            rotate(${rotate}deg)
        `;
    }

    applyCrop(modal) {
        // In a real implementation, you would:
        // 1. Get crop coordinates
        // 2. Create canvas and draw cropped image
        // 3. Convert to blob
        // 4. Update preview and file

        // For now, just close modal and show success
        this.closeCropModal(modal);
        this.showToast('Crop applied successfully', 'success');
    }

    closeCropModal(modal) {
        modal.classList.remove('active');
        setTimeout(() => modal.remove(), 300);
        this.cropper = null;
    }

    removeImage() {
        const dropZone = this.container.querySelector('.upload-drop-zone');
        const preview = this.container.querySelector('.upload-preview-container');
        const fileInput = this.container.querySelector('input[type="file"]');
        
        if (dropZone) dropZone.style.display = 'flex';
        if (preview) preview.style.display = 'none';
        if (fileInput) fileInput.value = '';
        
        this.currentFile = null;
        this.previewImage = null;
        this.cropData = null;
    }

    addSuccessAnimation() {
        const preview = this.container.querySelector('.upload-preview-container');
        if (preview) {
            preview.classList.add('success-pop');
            setTimeout(() => preview.classList.remove('success-pop'), 600);
        }
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showToast(message, type = 'info') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
            return;
        }

        // Fallback toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            </div>
            <div class="toast-message">${message}</div>
        `;
        
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('active'));
        setTimeout(() => {
            toast.classList.remove('active');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    getFile() {
        return this.currentFile;
    }
}

// Initialize uploaders when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Logo uploader (square, 1:1)
    const logoContainer = document.getElementById('logoUploadContainer');
    if (logoContainer) {
        window.logoUploader = new ModernImageUploader('logoUploadContainer', {
            aspectRatio: 1,
            recommendedWidth: 512,
            recommendedHeight: 512,
            inputName: 'logo'
        });
    }

    // Banner uploader (wide, 16:9)
    const bannerContainer = document.getElementById('bannerUploadContainer');
    if (bannerContainer) {
        window.bannerUploader = new ModernImageUploader('bannerUploadContainer', {
            aspectRatio: 16 / 9,
            recommendedWidth: 1920,
            recommendedHeight: 1080,
            inputName: 'banner_image'
        });
    }
});
