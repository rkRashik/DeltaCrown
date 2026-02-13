/**
 * Organization Create Page - vNext
 * Wizard-based multi-step form for creating organizations
 * Phase A: Demo mode with UI only
 * Phase B: Will wire to real API endpoints
 */

// --- CONFIGURATION ---
function getConfig() {
    return window.ORG_CREATE_CONFIG || {};
}

// --- STATE ---
let currentStep = 1;
const totalSteps = 5;

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', function() {
    initializeWizard();
    initializeDynamicFields();
    initializeImagePreviews();
    initializeBrandColorPicker();
    initializeDossierUpdates();
    initializeSubmitButton();
});

// --- WIZARD NAVIGATION ---
function initializeWizard() {
    // Next buttons
    document.querySelectorAll('.btn-next').forEach(btn => {
        btn.addEventListener('click', function() {
            const nextStep = parseInt(this.getAttribute('data-next'));
            goToStep(nextStep);
        });
    });

    // Previous buttons
    document.querySelectorAll('.btn-prev').forEach(btn => {
        btn.addEventListener('click', function() {
            const prevStep = parseInt(this.getAttribute('data-prev'));
            goToStep(prevStep);
        });
    });
}

function goToStep(step) {
    if (step < 1 || step > totalSteps) return;
    if (step > currentStep + 1) return; // Prevent skipping ahead

    // Hide all steps
    document.querySelectorAll('.step-section').forEach(el => {
        el.classList.remove('active');
    });

    // Show target step
    document.getElementById(`step${step}`).classList.add('active');

    // Update progress bars
    for (let i = 1; i <= totalSteps; i++) {
        const bar = document.getElementById(`progress${i}`);
        if (i <= step) {
            bar.classList.remove('bg-white/10');
            bar.classList.add('bg-yellow-500');
        } else {
            bar.classList.remove('bg-yellow-500');
            bar.classList.add('bg-white/10');
        }
    }

    // Update step label
    const labels = ["Identity", "Operations", "Treasury", "Branding", "Ratification"];
    document.getElementById('stepLabel').innerHTML = `
        <span class="text-yellow-500">0${step}. ${labels[step-1]}</span>
        <span>05. Ratification</span>
    `;

    currentStep = step;

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// --- DYNAMIC ORGANIZATION TYPE FIELDS ---
function initializeDynamicFields() {
    document.querySelectorAll('input[name="organization_type"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const type = this.value; // 'club', 'pro', 'guild'
            
            // Hide all dynamic fields
            document.querySelectorAll('.dynamic-field').forEach(el => {
                el.classList.remove('active');
            });

            // Show selected fields
            const targetFields = document.getElementById(`fields-${type}`);
            if (targetFields) {
                targetFields.classList.add('active');
            }

            // Update dossier structure label
            const labels = {
                'club': 'Esports Club',
                'pro': 'Pro Organization',
                'guild': 'Community Guild'
            };
            updateDossierField('dossierStructure', labels[type] || 'Esports Club');
        });
    });
}

// --- IMAGE UPLOAD PREVIEWS ---
function initializeImagePreviews() {
    const logoUpload = document.getElementById('orgLogoUpload');
    const bannerUpload = document.getElementById('orgBannerUpload');

    if (logoUpload) {
        logoUpload.addEventListener('change', function() {
            previewImage(this, 'logoPreview', 'dossierLogo');
        });
    }

    if (bannerUpload) {
        bannerUpload.addEventListener('change', function() {
            previewImage(this, 'bannerPreview');
        });
    }
}

function previewImage(input, previewId, dossierLogoId = null) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const img = document.getElementById(previewId);
            if (img) {
                img.src = e.target.result;
                img.classList.remove('hidden');
            }

            // Also update dossier logo if applicable
            if (dossierLogoId) {
                const dossierLogo = document.getElementById(dossierLogoId);
                if (dossierLogo) {
                    dossierLogo.innerHTML = `<img src="${e.target.result}" class="w-full h-full object-cover">`;
                }
            }
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// --- BRAND COLOR PICKER ---
function initializeBrandColorPicker() {
    const customColorInput = document.getElementById('customColor');
    if (customColorInput) {
        customColorInput.addEventListener('change', function() {
            setBrandColor(this.value);
        });
    }
}

function setBrandColor(color) {
    const colorPreview = document.getElementById('colorPreview');
    const certificateCard = document.getElementById('certificateCard');
    
    if (colorPreview) {
        colorPreview.innerText = color;
        colorPreview.style.color = color;
    }
    
    if (certificateCard) {
        certificateCard.style.borderColor = color;
    }

    // Update hidden input value
    const customColorInput = document.getElementById('customColor');
    if (customColorInput) {
        customColorInput.value = color;
    }
}

// Make setBrandColor globally available for onclick handlers
window.setBrandColor = setBrandColor;

// --- LIVE DOSSIER UPDATES ---
function initializeDossierUpdates() {
    // Organization Name
    const orgName = document.getElementById('orgName');
    if (orgName) {
        orgName.addEventListener('input', function() {
            updateDossierField('dossierName', (this.value || 'PENDING...').toUpperCase());
            debouncedValidate('name', this.value);
        });
    }

    // Ticker/Badge
    const orgTicker = document.getElementById('orgTicker');
    if (orgTicker) {
        orgTicker.addEventListener('input', function() {
            updateDossierField('dossierTicker', (this.value || '---').toUpperCase());
            debouncedValidate('badge', this.value);
        });
    }

    // Founded Year
    const orgEst = document.getElementById('orgEst');
    if (orgEst) {
        orgEst.addEventListener('input', function() {
            updateDossierField('dossierEst', this.value || '2026');
        });
    }

    // Slug
    const orgSlug = document.getElementById('orgSlug');
    if (orgSlug) {
        orgSlug.addEventListener('input', function() {
            updateDossierField('dossierUrl', `deltacrown.gg/org/${this.value || '---'}`);
            debouncedValidate('slug', this.value);
        });
    }

    // Region
    const orgRegion = document.getElementById('orgRegion');
    if (orgRegion) {
        orgRegion.addEventListener('change', function() {
            const selectedText = this.options[this.selectedIndex].text;
            updateDossierField('dossierRegion', selectedText);
        });
    }

    // Currency
    const walletCurrency = document.getElementById('walletCurrency');
    if (walletCurrency) {
        walletCurrency.addEventListener('change', function() {
            updateDossierField('dossierCurrency', this.value);
        });
    }

    // Character counter for manifesto
    const orgManifesto = document.getElementById('orgManifesto');
    if (orgManifesto) {
        orgManifesto.addEventListener('input', function() {
            const counter = this.parentElement.querySelector('.text-right.text-\\[10px\\]');
            if (counter) {
                counter.textContent = `${this.value.length}/500`;
            }
        });
    }
}

// Validation with debouncing (300ms delay)
let validationTimeouts = {};
function debouncedValidate(fieldType, value) {
    const config = getConfig();
    if (config.demoMode) return;
    
    // Clear previous timeout
    if (validationTimeouts[fieldType]) {
        clearTimeout(validationTimeouts[fieldType]);
    }
    
    // Set new timeout
    validationTimeouts[fieldType] = setTimeout(() => {
        validateField(fieldType, value);
    }, 300);
}

function validateField(fieldType, value) {
    const config = getConfig();
    if (!value || value.length < 2) return;
    
    let url;
    let paramName;
    let fieldId;
    
    if (fieldType === 'name') {
        url = config.validateNameUrl;
        paramName = 'name';
        fieldId = 'orgName';
    } else if (fieldType === 'badge') {
        url = config.validateBadgeUrl;
        paramName = 'badge';
        fieldId = 'orgTicker';
    } else if (fieldType === 'slug') {
        url = config.validateSlugUrl;
        paramName = 'slug';
        fieldId = 'orgSlug';
    } else {
        return;
    }
    
    fetch(`${url}?${paramName}=${encodeURIComponent(value)}`)
        .then(response => response.json())
        .then(data => {
            const field = document.getElementById(fieldId);
            if (!field) return;
            
            // Remove previous validation styling
            field.classList.remove('border-red-500', 'border-green-500');
            
            // Get or create error message element
            let errorEl = field.parentElement.querySelector('.validation-error');
            
            if (data.ok && data.available) {
                // Available - show green border
                field.classList.add('border-green-500');
                if (errorEl) errorEl.remove();
            } else if (data.field_errors && data.field_errors[paramName]) {
                // Not available - show red border and error
                field.classList.add('border-red-500');
                if (!errorEl) {
                    errorEl = document.createElement('p');
                    errorEl.className = 'validation-error text-xs text-red-500 mt-1 ml-1';
                    field.parentElement.appendChild(errorEl);
                }
                errorEl.textContent = data.field_errors[paramName];
            }
        })
        .catch(error => {
            console.error('Validation error:', error);
        });
}

function updateDossierField(fieldId, value) {
    const field = document.getElementById(fieldId);
    if (field) {
        field.innerText = value;
    }
}

// --- FORM SUBMISSION ---
function initializeSubmitButton() {
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', handleSubmit);
    }
}

function handleSubmit(e) {
    e.preventDefault();

    const termsCheck = document.getElementById('termsCheck');
    if (!termsCheck || !termsCheck.checked) {
        showSubmitError('You must sign the ratification agreement.');
        return;
    }

    const config = getConfig();
    
    if (config.demoMode) {
        // Phase A: Demo mode
        const btn = e.target.closest('button');
        const originalHTML = btn.innerHTML;
        
        btn.innerHTML = '<i class="fas fa-cog fa-spin"></i> Processing...';
        btn.disabled = true;
        btn.style.opacity = '0.7';

        setTimeout(() => {
            alert('✅ Phase A Demo: Organization form works!\n\n➡️ Phase B will connect to real backend and save to database.');
            btn.innerHTML = originalHTML;
            btn.disabled = false;
            btn.style.opacity = '1';
        }, 1500);
    } else {
        // Phase B: Real submission (to be implemented)
        submitOrganization();
    }
}

function showSubmitError(message, useHtml = false) {
    const submitBtn = document.getElementById('submitBtn');
    if (!submitBtn) {
        console.error(message);
        return;
    }

    let el = document.getElementById('orgSubmitError');
    if (!el) {
        el = document.createElement('div');
        el.id = 'orgSubmitError';
        el.className = 'mt-4 p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-xs text-red-300 font-mono';
        submitBtn.parentElement?.appendChild(el);
    }

    if (useHtml) {
        el.innerHTML = message;
    } else {
        el.textContent = message;
    }
    el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

function clearSubmitError() {
    const el = document.getElementById('orgSubmitError');
    if (el) el.remove();
}

// Phase B: Real submission function
function submitOrganization() {
    clearSubmitError();

    // Step 1: Identity
    const name = document.getElementById('orgName')?.value?.trim() || '';
    const badge = document.getElementById('orgTicker')?.value?.trim() || '';
    const slug = document.getElementById('orgSlug')?.value?.trim() || '';
    const description = document.getElementById('orgManifesto')?.value?.trim() || '';
    const foundedYearRaw = document.getElementById('orgEst')?.value?.trim() || '';
    const foundedYear = foundedYearRaw ? parseInt(foundedYearRaw, 10) : null;

    // Step 2: Operations
    const organizationType = document.querySelector('input[name="organization_type"]:checked')?.value || 'club';
    const hqCity = document.querySelector('input[name="hq_city"]')?.value?.trim() || '';
    const hqAddress = document.querySelector('input[name="hq_address"]')?.value?.trim() || '';
    const businessEmail = document.querySelector('input[name="business_email"]')?.value?.trim() || '';
    const tradeLicense = document.querySelector('input[name="trade_license"]')?.value?.trim() || '';
    const regionCode = document.getElementById('orgRegion')?.value?.trim() || '';

    // Social links — merge guild discord and social discord
    const discordGuild = document.querySelector('input[name="discord_link"]')?.value?.trim() || '';
    const discordSocial = document.querySelector('input[name="discord_social"]')?.value?.trim() || '';
    const discordLink = discordGuild || discordSocial;
    const facebook = document.querySelector('input[name="facebook"]')?.value?.trim() || '';
    const instagram = document.querySelector('input[name="instagram"]')?.value?.trim() || '';
    const youtube = document.querySelector('input[name="youtube"]')?.value?.trim() || '';

    // Guild-specific region fallback
    const regionCodeGuild = document.querySelector('select[name="region_code_guild"]')?.value?.trim() || '';
    const finalRegionCode = regionCode || regionCodeGuild;

    // Step 3: Treasury
    const payoutMethod = document.querySelector('input[name="payout_method"]:checked')?.value || 'mobile';
    const currency = document.getElementById('walletCurrency')?.value?.trim() || 'BDT';

    // Step 4: Branding
    const brandColor = document.getElementById('customColor')?.value?.trim() || '';

    // Build payload — top-level fields (matching expanded serializer)
    const payload = { name };
    if (slug) payload.slug = slug;
    if (badge) payload.badge = badge;
    if (description) payload.description = description;
    if (foundedYear) payload.founded_year = foundedYear;
    if (organizationType) payload.organization_type = organizationType;
    if (hqCity) payload.hq_city = hqCity;
    if (hqAddress) payload.hq_address = hqAddress;
    if (businessEmail) payload.business_email = businessEmail;
    if (tradeLicense) payload.trade_license = tradeLicense;
    if (finalRegionCode) payload.region_code = finalRegionCode;
    if (discordLink) payload.discord_link = discordLink;
    if (facebook) payload.facebook = facebook;
    if (instagram) payload.instagram = instagram;
    if (youtube) payload.youtube = youtube;
    if (currency) payload.currency = currency;
    if (payoutMethod) payload.payout_method = payoutMethod;
    if (brandColor) payload.brand_color = brandColor;

    const config = getConfig();
    const createUrl = config.createUrl || '/api/vnext/organizations/create/';

    // Check for file uploads (logo/banner)
    const logoInput = document.getElementById('orgLogoUpload');
    const bannerInput = document.getElementById('orgBannerUpload');
    const hasFiles = (logoInput && logoInput.files.length > 0) || (bannerInput && bannerInput.files.length > 0);

    let fetchOptions;
    if (hasFiles) {
        // Use FormData for multipart upload
        const formData = new FormData();
        Object.entries(payload).forEach(([key, val]) => {
            if (val !== null && val !== undefined && val !== '') formData.append(key, val);
        });
        if (logoInput && logoInput.files[0]) formData.append('logo', logoInput.files[0]);
        if (bannerInput && bannerInput.files[0]) formData.append('banner', bannerInput.files[0]);
        fetchOptions = {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin',
            body: formData,
        };
    } else {
        fetchOptions = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken(),
            },
            credentials: 'same-origin',
            body: JSON.stringify(payload),
        };
    }

    const submitBtn = document.getElementById('submitBtn');
    const originalHTML = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fas fa-cog fa-spin"></i> Incorporating...';
    submitBtn.disabled = true;

    fetch(createUrl, fetchOptions)
    .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw { response, data };
        }
        return data;
    })
    .then(data => {
        if (data.ok) {
            const orgUrl = data.organization_url;
            if (orgUrl) {
                window.location.href = orgUrl;
                return;
            }
        }

        console.error('Unexpected success payload:', data);
        showSubmitError('Organization created but redirect URL not found.');
        submitBtn.innerHTML = originalHTML;
        submitBtn.disabled = false;
    })
    .catch(error => {
        const data = error?.data || {};
        const errorCode = data?.error_code;

        // DRF serializer errors
        const details = data?.details;
        if (details && typeof details === 'object') {
            const flattenErrors = (obj, prefix = '') => {
                const out = {};
                for (const [key, value] of Object.entries(obj)) {
                    const fullKey = prefix ? `${prefix}.${key}` : key;
                    if (Array.isArray(value)) {
                        out[fullKey] = value[0] || 'Invalid value';
                    } else if (value && typeof value === 'object') {
                        Object.assign(out, flattenErrors(value, fullKey));
                    } else if (typeof value === 'string') {
                        out[fullKey] = value;
                    }
                }
                return out;
            };

            handleFieldErrors(flattenErrors(details));
            showSubmitError(data?.safe_message || data?.message || 'Please fix the highlighted fields.');
        } else if (errorCode) {
            // Service-layer errors
            showSubmitError(data?.safe_message || data?.message || 'Failed to create organization.');
            // Best-effort field highlight
            if (errorCode === 'NAME_CONFLICT' || errorCode === 'organization_already_exists') {
                handleFieldErrors({ name: data?.safe_message || 'Organization name already exists.' });
            }
            if (errorCode === 'SLUG_CONFLICT' || errorCode === 'slug_already_exists') {
                handleFieldErrors({ slug: data?.safe_message || 'Slug already exists.' });
            }
            if (errorCode === 'USER_ALREADY_CEO') {
                // User already owns an org - show which one and a link
                const orgSlug = data?.details?.existing_organization_slug;
                const orgName = data?.details?.existing_organization_name;
                const linkHtml = orgSlug
                    ? ` <a href="/orgs/${orgSlug}/" class="text-cyan-400 underline hover:text-cyan-300">Manage ${orgName || 'your organization'}</a>`
                    : '';
                showSubmitError((data?.safe_message || 'You already own an organization.') + linkHtml, true);
            }
        } else {
            console.error('Error:', error);
            showSubmitError('Network or server error. Please try again.');
        }
        submitBtn.innerHTML = originalHTML;
        submitBtn.disabled = false;
    });
}

function handleFieldErrors(errors) {
    // Map of field names to step numbers
    const fieldStepMap = {
        'name': 1,
        'badge': 1,
        'slug': 1,
        'description': 1,
        'branding.description': 1,
        'founded_year': 1,
        'organization_type': 2,
        'hq_city': 2,
        'hq_address': 2,
        'business_email': 2,
        'trade_license': 2,
        'region_code': 2,
        'discord_link': 2,
        'instagram': 2,
        'facebook': 2,
        'youtube': 2,
        'currency': 3,
        'payout_method': 3,
        'logo': 4,
        'banner': 4,
        'brand_color': 4,
        'branding.primary_color': 4,
    };
    
    // Find the earliest step with an error
    let firstErrorStep = 5;
    for (const fieldName in errors) {
        const stepNum = fieldStepMap[fieldName] || 5;
        if (stepNum < firstErrorStep) {
            firstErrorStep = stepNum;
        }
    }
    
    // Navigate to that step
    goToStep(firstErrorStep);
    
    // Display error messages next to fields
    for (const fieldName in errors) {
        let fieldId = fieldName;
        
        // Map backend field names to frontend IDs
        if (fieldName === 'name') fieldId = 'orgName';
        else if (fieldName === 'badge') fieldId = 'orgTicker';
        else if (fieldName === 'slug') fieldId = 'orgSlug';
        else if (fieldName === 'description') fieldId = 'orgManifesto';
        else if (fieldName === 'branding.description') fieldId = 'orgManifesto';
        else if (fieldName === 'founded_year') fieldId = 'orgEst';
        else if (fieldName === 'branding.primary_color') fieldId = 'customColor';
        
        const field = document.getElementById(fieldId) || document.querySelector(`[name="${fieldName}"]`);
        if (!field) continue;
        
        // Add red border
        field.classList.add('border-red-500');
        
        // Add error message
        let errorEl = field.parentElement.querySelector('.field-error');
        if (!errorEl) {
            errorEl = document.createElement('p');
            errorEl.className = 'field-error text-xs text-red-500 mt-1 ml-1';
            field.parentElement.appendChild(errorEl);
        }
        errorEl.textContent = errors[fieldName];
    }
}

function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}

// --- EXPORTS FOR INLINE EVENT HANDLERS ---
window.goToStep = goToStep;
window.updateDossierField = updateDossierField;
