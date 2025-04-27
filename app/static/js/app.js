// Main application logic
document.addEventListener('DOMContentLoaded', function() {
    // App state
    const state = {
        token: localStorage.getItem('token'),
        currentUser: null,
        documents: [],
        currentDocument: null,
        websocket: null,
        realtimeUpdates: localStorage.getItem('realtimeUpdates') === 'true',
        newDocument: null,
        isAuthenticated: false,
        ocrFile: null,
        ocrImageUrl: null,
        ocrText: null
    };

    // DOM elements
    const elements = {
        appView: document.getElementById('app-view'),
        loginModal: document.getElementById('login-modal'),
        loginForm: document.getElementById('login-form'),
        email: document.getElementById('email'),
        password: document.getElementById('password'),
        userEmail: document.getElementById('user-email'),
        logoutBtn: document.getElementById('logout-btn'),
        documentsList: document.getElementById('documents-list'),
        emptyState: document.getElementById('empty-state'),
        loadingState: document.getElementById('loading-state'),
        newDocumentBtn: document.getElementById('new-document-btn'),
        documentModal: document.getElementById('document-modal'),
        documentForm: document.getElementById('document-form'),
        documentTitle: document.getElementById('document-title'),
        documentContent: document.getElementById('document-content'),
        saveDocumentBtn: document.getElementById('save-document-btn'),
        closeModalBtn: document.getElementById('close-modal-btn'),
        viewDocumentModal: document.getElementById('view-document-modal'),
        viewDocumentTitle: document.getElementById('view-document-title'),
        viewDocumentContent: document.getElementById('view-document-content'),
        editDocumentBtn: document.getElementById('edit-document-btn'),
        closeViewModalBtn: document.getElementById('close-view-modal-btn'),
        deleteModal: document.getElementById('delete-modal'),
        confirmDeleteBtn: document.getElementById('confirm-delete-btn'),
        cancelDeleteBtn: document.getElementById('cancel-delete-btn'),
        wsStatus: document.getElementById('ws-status'),
        realtimeUpdates: document.getElementById('realtime-updates'),
        documentNotificationModal: document.getElementById('document-notification-modal'),
        notificationDocTitle: document.getElementById('notification-doc-title'),
        viewNotificationDocBtn: document.getElementById('view-notification-doc-btn'),
        closeNotificationBtn: document.getElementById('close-notification-btn'),
        ocrBtn: document.getElementById('ocr-btn'),
        ocrModal: document.getElementById('ocr-modal'),
        ocrFile: document.getElementById('ocr-file'),
        fileUploadArea: document.getElementById('file-upload-area'),
        filePreview: document.getElementById('file-preview'),
        ocrPreviewImage: document.getElementById('ocr-preview-image'),
        removeFileBtn: document.getElementById('remove-file'),
        uploadOcrBtn: document.getElementById('upload-ocr-btn'),
        ocrUrl: document.getElementById('ocr-url'),
        urlOcrBtn: document.getElementById('url-ocr-btn'),
        ocrResultContainer: document.getElementById('ocr-result-container'),
        ocrResultText: document.getElementById('ocr-result-text'),
        copyOcrBtn: document.getElementById('copy-ocr-btn'),
        createDocFromOcrBtn: document.getElementById('create-document-from-ocr'),
        ocrLoading: document.getElementById('ocr-loading'),
        closeOcrModalBtn: document.getElementById('close-ocr-modal-btn')
    };

    // API endpoints
    const API = {
        baseUrl: '/api/v1',
        login: '/token',
        currentUser: '/users/me',
        documents: '/documents',
        document: (id) => `/documents/${id}`,
        ocrFile: '/ocr/file',
        ocrUrl: '/ocr/url',
        ocrBase64: '/ocr/base64'
    };

    // Helper functions
    const helpers = {
        showToast: function(message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = `toast ${type === 'success' ? 'bg-emerald-600' : 'bg-red-600'}`;
            toast.textContent = message;
            
            document.getElementById('toast-container').appendChild(toast);
            
            // Trigger reflow for animation
            void toast.offsetWidth;
            toast.classList.add('show');
            
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    toast.remove();
                }, 300);
            }, 3000);
        },
        
        formatDate: function(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        },
        
        api: async function(endpoint, method = 'GET', data = null) {
            const url = API.baseUrl + endpoint;
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            if (state.token) {
                options.headers['Authorization'] = `Bearer ${state.token}`;
            }
            
            if (data) {
                options.body = JSON.stringify(data);
            }
            
            try {
                const response = await fetch(url, options);
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'API request failed');
                }
                return response.json();
            } catch (error) {
                console.error('API error:', error);
                throw error;
            }
        },
        
        connectWebSocket: function() {
            if (state.websocket) {
                state.websocket.close();
            }
            
            if (!state.token || !state.realtimeUpdates) {
                elements.wsStatus.classList.remove('connected');
                elements.wsStatus.classList.add('disconnected');
                elements.wsStatus.innerHTML = '<span class="status-dot"></span> Disconnected';
                return;
            }
            
            // Update UI to show connecting
            elements.wsStatus.classList.remove('connected', 'disconnected');
            elements.wsStatus.classList.add('connecting');
            elements.wsStatus.innerHTML = '<span class="status-dot"></span> Connecting...';
            
            // Create WebSocket connection with token
            state.websocket = new WebSocket(`wss://${window.location.host}/ws/documents?token=${state.token}`);
            
            state.websocket.onopen = function() {
                elements.wsStatus.classList.remove('connecting', 'disconnected');
                elements.wsStatus.classList.add('connected');
                elements.wsStatus.innerHTML = '<span class="status-dot"></span> Connected';
                helpers.showToast('Connected to real-time updates');
            };
            
            state.websocket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                
                if (data.status === 'connected') {
                    console.log('WebSocket connected:', data.message);
                } else if (data.type === 'document_created') {
                    console.log('New document received:', data.data.title);
                    
                    // Save the new document data
                    state.newDocument = data.data;
                    
                    // Show document in view modal instead of notification
                    if (state.realtimeUpdates) {
                        // Force refresh documents first to ensure it's in the list
                        actions.fetchDocuments().then(() => {
                            // Find the document in the refreshed list to get complete data
                            const fullDoc = state.documents.find(d => d.id === data.data.id) || data.data;
                            // Show the document modal
                            viewDocument(fullDoc);
                        });
                    } else {
                        helpers.showToast('New document received: ' + data.data.title);
                        // Still refresh the list
                        actions.fetchDocuments();
                    }
                } else if (data.type === 'document_updated') {
                    helpers.showToast('Document updated: ' + data.data.title);
                    
                    // Force refresh documents
                    actions.fetchDocuments().then(() => {
                        // If currently viewing this document, update the view
                        if (state.currentDocument && state.currentDocument.id === data.data.id) {
                            // Find updated doc in the list
                            const updatedDoc = state.documents.find(d => d.id === data.data.id);
                            if (updatedDoc) {
                                viewDocument(updatedDoc);
                            }
                        }
                    });
                } else if (data.type === 'document_deleted') {
                    helpers.showToast('Document deleted: ' + data.data.title);
                    
                    // If currently viewing this document, close the modal
                    if (state.currentDocument && state.currentDocument.id === data.data.id) {
                        closeViewDocumentModal();
                    }
                    
                    // Remove from list
                    actions.fetchDocuments();
                }
            };
            
            state.websocket.onclose = function() {
                elements.wsStatus.classList.remove('connected', 'connecting');
                elements.wsStatus.classList.add('disconnected');
                elements.wsStatus.innerHTML = '<span class="status-dot"></span> Disconnected';
                
                // Don't automatically reconnect if user has turned off real-time updates
                if (state.realtimeUpdates) {
                    setTimeout(() => {
                        helpers.connectWebSocket();
                    }, 3000);
                }
            };
            
            state.websocket.onerror = function(error) {
                console.error('WebSocket error:', error);
                helpers.showToast('WebSocket connection error', 'error');
            };
        }
    };

    // Application actions
    const actions = {
        login: async function(email, password) {
            try {
                const data = await helpers.api(API.login, 'POST', { email, password });
                state.token = data.access_token;
                localStorage.setItem('token', state.token);
                await actions.fetchCurrentUser();
                actions.showApp();
                helpers.showToast('Login successful');
                
                // Connect to WebSocket if real-time updates are enabled
                if (state.realtimeUpdates) {
                    helpers.connectWebSocket();
                }
            } catch (error) {
                helpers.showToast('Login failed: ' + error.message, 'error');
            }
        },
        
        logout: function() {
            state.token = null;
            state.currentUser = null;
            state.documents = [];
            state.isAuthenticated = false;
            localStorage.removeItem('token');
            
            // Close WebSocket connection
            if (state.websocket) {
                state.websocket.close();
                state.websocket = null;
            }
            
            actions.showLogin();
            helpers.showToast('Logged out successfully');
        },
        
        fetchCurrentUser: async function() {
            try {
                state.currentUser = await helpers.api(API.currentUser);
                elements.userEmail.textContent = state.currentUser.email;
                state.isAuthenticated = true;
            } catch (error) {
                console.error('Error fetching current user:', error);
                actions.logout();
            }
        },
        
        fetchDocuments: async function() {
            elements.loadingState.classList.remove('hidden');
            elements.emptyState.classList.add('hidden');
            
            try {
                state.documents = await helpers.api(API.documents);
                renderDocuments();
                return state.documents; // Return documents for promise chaining
            } catch (error) {
                console.error('Error fetching documents:', error);
                helpers.showToast('Error loading documents', 'error');
                return []; // Return empty array on error
            } finally {
                elements.loadingState.classList.add('hidden');
                if (state.documents.length === 0) {
                    elements.emptyState.classList.remove('hidden');
                }
            }
        },
        
        createDocument: async function(title, content) {
            try {
                const docData = {
                    title,
                    data: {
                        pages: [{
                            text: content
                        }]
                    }
                };
                
                const newDoc = await helpers.api(API.documents, 'POST', docData);
                closeDocumentModal();
                actions.fetchDocuments();
                helpers.showToast('Document created successfully');
                
                // Show the newly created document
                setTimeout(() => {
                    viewDocument(newDoc);
                }, 200);
            } catch (error) {
                console.error('Error creating document:', error);
                helpers.showToast('Error creating document: ' + error.message, 'error');
            }
        },
        
        updateDocument: async function(id, title, content) {
            try {
                const docData = {
                    title,
                    data: {
                        pages: [{
                            text: content
                        }]
                    }
                };
                
                await helpers.api(API.document(id), 'PUT', docData);
                closeDocumentModal();
                actions.fetchDocuments();
                helpers.showToast('Document updated successfully');
            } catch (error) {
                console.error('Error updating document:', error);
                helpers.showToast('Error updating document: ' + error.message, 'error');
            }
        },
        
        deleteDocument: async function(id) {
            try {
                await helpers.api(API.document(id), 'DELETE');
                closeDeleteModal();
                actions.fetchDocuments();
                helpers.showToast('Document deleted successfully');
            } catch (error) {
                console.error('Error deleting document:', error);
                helpers.showToast('Error deleting document: ' + error.message, 'error');
            }
        },
        
        showApp: function() {
            // Hide login modal
            elements.loginModal.classList.add('hidden');
            actions.fetchDocuments();
        },
        
        showLogin: function() {
            // Show login modal
            elements.loginModal.classList.remove('hidden');
            
            // Clear login form
            elements.loginForm.reset();
        }
    };

    // OCR Functions
    const ocr = {
        // Process file upload for OCR
        handleFileUpload: function(e) {
            const file = e.target.files[0];
            if (!file) return;
            
            // Check if file is an image
            if (!file.type.startsWith('image/')) {
                helpers.showToast('Please select an image file', 'error');
                return;
            }
            
            // Save file to state
            state.ocrFile = file;
            
            // Show preview
            const reader = new FileReader();
            reader.onload = function(e) {
                elements.ocrPreviewImage.src = e.target.result;
                elements.fileUploadArea.classList.add('hidden');
                elements.filePreview.classList.remove('hidden');
                elements.uploadOcrBtn.disabled = false;
            };
            reader.readAsDataURL(file);
        },
        
        // Remove uploaded file
        removeFile: function() {
            state.ocrFile = null;
            elements.ocrFile.value = '';
            elements.filePreview.classList.add('hidden');
            elements.fileUploadArea.classList.remove('hidden');
            elements.uploadOcrBtn.disabled = true;
        },
        
        // Handle URL input
        handleUrlInput: function() {
            const url = elements.ocrUrl.value.trim();
            elements.urlOcrBtn.disabled = !url;
        },
        
        // Process OCR from uploaded file
        processFileOcr: async function() {
            if (!state.ocrFile) {
                helpers.showToast('Please select an image file', 'error');
                return;
            }
            
            // Show loading state
            ocr.showLoading();
            
            try {
                // Create form data
                const formData = new FormData();
                formData.append('file', state.ocrFile);
                
                // Call OCR API
                const response = await fetch(API.baseUrl + API.ocrFile, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.token}`
                    },
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('OCR processing failed');
                }
                
                const result = await response.json();
                
                // Process OCR result
                ocr.handleOcrResult(result);
            } catch (error) {
                console.error('OCR error:', error);
                helpers.showToast('OCR processing failed: ' + error.message, 'error');
                ocr.hideLoading();
            }
        },
        
        // Process OCR from URL
        processUrlOcr: async function() {
            const url = elements.ocrUrl.value.trim();
            if (!url) {
                helpers.showToast('Please enter a valid image URL', 'error');
                return;
            }
            
            // Save URL to state
            state.ocrImageUrl = url;
            
            // Show loading state
            ocr.showLoading();
            
            try {
                // Call OCR API
                const response = await fetch(API.baseUrl + API.ocrUrl, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${state.token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ url })
                });
                
                if (!response.ok) {
                    throw new Error('OCR processing failed');
                }
                
                const result = await response.json();
                
                // Process OCR result
                ocr.handleOcrResult(result);
            } catch (error) {
                console.error('OCR error:', error);
                helpers.showToast('OCR processing failed: ' + error.message, 'error');
                ocr.hideLoading();
            }
        },
        
        // Handle OCR result
        handleOcrResult: function(result) {
            // Hide loading
            ocr.hideLoading();
            
            // Extract text from result
            const text = result.text || '';
            state.ocrText = text;
            
            // Show result
            elements.ocrResultText.textContent = text;
            elements.ocrResultContainer.classList.remove('hidden');
            
            helpers.showToast('OCR processing complete');
        },
        
        // Create document from OCR result
        createDocumentFromOcr: async function() {
            if (!state.ocrText) {
                helpers.showToast('No OCR text available', 'error');
                return;
            }
            
            // Create document data
            const now = new Date();
            const title = `Scanned Document ${now.toLocaleDateString()}, ${now.toLocaleTimeString()}`;
            
            const docData = {
                title,
                data: {
                    pages: [{
                        text: state.ocrText
                    }]
                }
            };
            
            // If we have an image, add it to the page
            if (state.ocrFile) {
                // Read file as base64
                const reader = new FileReader();
                reader.onload = async function(e) {
                    // Upload the image and get URL
                    try {
                        const imageData = e.target.result.split(',')[1]; // Remove data URL prefix
                        
                        // Try to upload to backend if there's an upload endpoint (assumed)
                        const response = await fetch(API.baseUrl + '/upload-image', {
                            method: 'POST',
                            headers: {
                                'Authorization': `Bearer ${state.token}`,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({ 
                                file: state.ocrFile.name,
                                base64_image: imageData 
                            })
                        });
                        
                        if (response.ok) {
                            const imageResult = await response.json();
                            docData.data.pages[0].image_url = imageResult.image_url;
                        }
                    } catch (error) {
                        console.error('Image upload error:', error);
                        // Continue with document creation even if image upload fails
                    }
                    
                    // Create document
                    try {
                        await helpers.api(API.documents, 'POST', docData);
                        helpers.showToast('Document created successfully');
                        ocr.closeModal();
                        actions.fetchDocuments();
                    } catch (error) {
                        console.error('Document creation error:', error);
                        helpers.showToast('Error creating document: ' + error.message, 'error');
                    }
                };
                reader.readAsDataURL(state.ocrFile);
            } else if (state.ocrImageUrl) {
                // Use the image URL directly
                docData.data.pages[0].image_url = state.ocrImageUrl;
                
                try {
                    await helpers.api(API.documents, 'POST', docData);
                    helpers.showToast('Document created successfully');
                    ocr.closeModal();
                    actions.fetchDocuments();
                } catch (error) {
                    console.error('Document creation error:', error);
                    helpers.showToast('Error creating document: ' + error.message, 'error');
                }
            } else {
                // No image, just create with text
                try {
                    await helpers.api(API.documents, 'POST', docData);
                    helpers.showToast('Document created successfully');
                    ocr.closeModal();
                    actions.fetchDocuments();
                } catch (error) {
                    console.error('Document creation error:', error);
                    helpers.showToast('Error creating document: ' + error.message, 'error');
                }
            }
        },
        
        // Show OCR modal
        showModal: function() {
            elements.ocrModal.classList.remove('hidden');
            elements.ocrModal.style.display = 'flex';
        },
        
        // Close OCR modal and reset state
        closeModal: function() {
            elements.ocrModal.classList.add('hidden');
            
            // Reset state
            ocr.resetState();
            
            setTimeout(() => {
                elements.ocrModal.style.display = '';
            }, 300);
        },
        
        // Show loading state
        showLoading: function() {
            elements.ocrLoading.classList.remove('hidden');
        },
        
        // Hide loading state
        hideLoading: function() {
            elements.ocrLoading.classList.add('hidden');
        },
        
        // Reset OCR state
        resetState: function() {
            state.ocrFile = null;
            state.ocrImageUrl = null;
            state.ocrText = null;
            
            // Reset UI
            elements.ocrFile.value = '';
            elements.ocrUrl.value = '';
            elements.filePreview.classList.add('hidden');
            elements.fileUploadArea.classList.remove('hidden');
            elements.uploadOcrBtn.disabled = true;
            elements.urlOcrBtn.disabled = true;
            elements.ocrResultContainer.classList.add('hidden');
            elements.ocrResultText.textContent = '';
            ocr.hideLoading();
            
            // Reset tabs
            const tabs = document.querySelectorAll('#ocr-modal .tab-btn');
            const tabContents = document.querySelectorAll('#ocr-modal .tab-content');
            
            tabs.forEach(tab => {
                tab.classList.toggle('active', tab.getAttribute('data-tab') === 'upload');
            });
            
            tabContents.forEach(content => {
                content.classList.toggle('active', content.getAttribute('data-tab') === 'upload');
            });
        },
        
        // Copy OCR text to clipboard
        copyText: function() {
            if (!state.ocrText) return;
            
            navigator.clipboard.writeText(state.ocrText).then(() => {
                helpers.showToast('Text copied to clipboard');
            }).catch(err => {
                console.error('Could not copy text: ', err);
                helpers.showToast('Failed to copy text', 'error');
            });
        }
    };

    // Initialize application
    function init() {
        // Set up event listeners
        elements.loginForm.addEventListener('submit', function(e) {
            e.preventDefault();
            actions.login(elements.email.value, elements.password.value);
        });
        
        elements.logoutBtn.addEventListener('click', actions.logout);
        
        elements.newDocumentBtn.addEventListener('click', function() {
            state.currentDocument = null;
            elements.documentTitle.value = '';
            elements.documentContent.value = '';
            elements.documentModal.classList.remove('hidden');
        });
        
        elements.documentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const title = elements.documentTitle.value;
            const content = elements.documentContent.value;
            
            if (state.currentDocument) {
                actions.updateDocument(state.currentDocument.id, title, content);
            } else {
                actions.createDocument(title, content);
            }
        });
        
        elements.closeModalBtn.addEventListener('click', closeDocumentModal);
        elements.closeViewModalBtn.addEventListener('click', closeViewDocumentModal);
        
        elements.editDocumentBtn.addEventListener('click', function() {
            closeViewDocumentModal();
            
            // Populate edit form with current document
            elements.documentTitle.value = state.currentDocument.title;
            elements.documentContent.value = state.currentDocument.data.pages[0]?.text || '';
            elements.documentModal.classList.remove('hidden');
        });
        
        elements.cancelDeleteBtn.addEventListener('click', closeDeleteModal);
        
        elements.realtimeUpdates.checked = state.realtimeUpdates;
        elements.realtimeUpdates.addEventListener('change', function(e) {
            state.realtimeUpdates = e.target.checked;
            localStorage.setItem('realtimeUpdates', state.realtimeUpdates);
            
            if (state.realtimeUpdates) {
                helpers.connectWebSocket();
            } else if (state.websocket) {
                state.websocket.close();
                state.websocket = null;
            }
        });
        
        // Document notification modal
        elements.closeNotificationBtn.addEventListener('click', closeNotificationModal);
        
        // WebSocket status button click
        elements.wsStatus.addEventListener('click', function() {
            if (elements.wsStatus.classList.contains('disconnected') && state.token) {
                helpers.connectWebSocket();
            }
        });
        
        // Close login modal when clicking on overlay
        document.querySelector('#login-modal .modal-overlay').addEventListener('click', function(e) {
            // Only close if already authenticated
            if (state.isAuthenticated) {
                elements.loginModal.classList.add('hidden');
            }
        });
        
        // Check if user is already logged in
        if (state.token) {
            actions.fetchCurrentUser()
                .then(() => {
                    actions.showApp();
                    // Connect to WebSocket if real-time updates are enabled
                    if (state.realtimeUpdates) {
                        helpers.connectWebSocket();
                    }
                })
                .catch(() => {
                    // Token might be invalid or expired
                    state.token = null;
                    localStorage.removeItem('token');
                    actions.showLogin();
                });
        } else {
            actions.showLogin();
        }
        
        // Tab switching in document viewer
        document.querySelectorAll('.modal-tabs .tab-btn').forEach(tabBtn => {
            tabBtn.addEventListener('click', function() {
                const tabName = this.getAttribute('data-tab');
                
                // Update active tab button
                document.querySelectorAll('.modal-tabs .tab-btn').forEach(btn => {
                    btn.classList.toggle('active', btn === this);
                });
                
                // Show selected tab content
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.toggle('active', content.getAttribute('data-tab') === tabName);
                });
            });
        });
        
        // Copy document text button
        document.getElementById('copy-document-btn').addEventListener('click', function() {
            if (state.currentDocument && state.currentDocument.data.pages) {
                const text = state.currentDocument.data.pages[0]?.text || '';
                if (text) {
                    navigator.clipboard.writeText(text).then(() => {
                        helpers.showToast('Text copied to clipboard');
                    }).catch(err => {
                        console.error('Could not copy text: ', err);
                        helpers.showToast('Failed to copy text', 'error');
                    });
                } else {
                    helpers.showToast('No text to copy', 'error');
                }
            }
        });
        
        // OCR button
        elements.ocrBtn.addEventListener('click', ocr.showModal);
        
        // OCR file upload area
        elements.fileUploadArea.addEventListener('click', () => {
            elements.ocrFile.click();
        });
        
        // Drag and drop for file upload
        elements.fileUploadArea.addEventListener('dragover', e => {
            e.preventDefault();
            elements.fileUploadArea.classList.add('border-primary');
        });
        
        elements.fileUploadArea.addEventListener('dragleave', () => {
            elements.fileUploadArea.classList.remove('border-primary');
        });
        
        elements.fileUploadArea.addEventListener('drop', e => {
            e.preventDefault();
            elements.fileUploadArea.classList.remove('border-primary');
            
            if (e.dataTransfer.files.length) {
                elements.ocrFile.files = e.dataTransfer.files;
                const event = new Event('change');
                elements.ocrFile.dispatchEvent(event);
            }
        });
        
        // OCR file input
        elements.ocrFile.addEventListener('change', ocr.handleFileUpload);
        
        // Remove file button
        elements.removeFileBtn.addEventListener('click', ocr.removeFile);
        
        // URL input
        elements.ocrUrl.addEventListener('input', ocr.handleUrlInput);
        
        // OCR scan buttons
        elements.uploadOcrBtn.addEventListener('click', ocr.processFileOcr);
        elements.urlOcrBtn.addEventListener('click', ocr.processUrlOcr);
        
        // Copy OCR text button
        elements.copyOcrBtn.addEventListener('click', ocr.copyText);
        
        // Create document from OCR button
        elements.createDocFromOcrBtn.addEventListener('click', ocr.createDocumentFromOcr);
        
        // Close OCR modal button
        elements.closeOcrModalBtn.addEventListener('click', ocr.closeModal);
        
        // Tab switching in OCR modal
        document.querySelectorAll('#ocr-modal .tab-btn').forEach(tabBtn => {
            tabBtn.addEventListener('click', function() {
                const tabName = this.getAttribute('data-tab');
                
                // Update active tab button
                document.querySelectorAll('#ocr-modal .tab-btn').forEach(btn => {
                    btn.classList.toggle('active', btn === this);
                });
                
                // Show selected tab content
                document.querySelectorAll('#ocr-modal .tab-content').forEach(content => {
                    content.classList.toggle('active', content.getAttribute('data-tab') === tabName);
                });
            });
        });
    }

    // Render document list
    function renderDocuments() {
        elements.documentsList.innerHTML = '';
        
        state.documents.forEach(doc => {
            const row = document.createElement('tr');
            row.className = 'document-row';
            
            row.innerHTML = `
                <td>
                    <div class="document-title-cell document-title-link">${doc.title}</div>
                </td>
                <td>
                    <div class="date-cell">${helpers.formatDate(doc.created_at)}</div>
                </td>
                <td>
                    <div class="date-cell">${helpers.formatDate(doc.updated_at)}</div>
                </td>
                <td class="actions-cell">
                    <button class="view-btn">View</button>
                    <button class="edit-btn">Edit</button>
                    <button class="delete-btn">Delete</button>
                </td>
            `;
            
            // Add event listeners for row actions
            const viewBtn = row.querySelector('.view-btn');
            const editBtn = row.querySelector('.edit-btn');
            const deleteBtn = row.querySelector('.delete-btn');
            const titleCell = row.querySelector('.document-title-link');
            
            // Make document title clickable to view document
            titleCell.addEventListener('click', () => viewDocument(doc));
            
            viewBtn.addEventListener('click', () => viewDocument(doc));
            editBtn.addEventListener('click', () => editDocument(doc));
            deleteBtn.addEventListener('click', () => confirmDeleteDocument(doc));
            
            elements.documentsList.appendChild(row);
        });
    }

    // Document actions
    function viewDocument(doc) {
        if (!doc) {
            console.error("No document provided to viewDocument function");
            return;
        }
        
        console.log("Opening document in modal:", doc.title);
        
        // Set current document
        state.currentDocument = doc;
        
        // Update modal title
        elements.viewDocumentTitle.textContent = doc.title;
        
        // Update text content in the document tab
        const textContent = doc.data.pages[0]?.text || '';
        elements.viewDocumentContent.textContent = textContent;
        
        // Set up image slider
        setupImageSlider(doc);
        
        // Reset tabs to show document tab as active
        resetTabsToDefault();
        
        // Show the modal with explicit display settings
        elements.viewDocumentModal.style.display = 'flex';
        elements.viewDocumentModal.classList.remove('hidden');
        
        // Force a reflow to ensure modal display updates
        void elements.viewDocumentModal.offsetWidth;
    }

    function setupImageSlider(doc) {
        const imagesContainer = document.getElementById('document-images');
        const sliderContainer = imagesContainer.querySelector('.image-slider-container');
        const slider = document.getElementById('image-slider');
        const paginationContainer = document.getElementById('slider-pagination');
        const emptyMessage = imagesContainer.querySelector('.empty-images-message');
        const prevButton = document.getElementById('prev-slide');
        const nextButton = document.getElementById('next-slide');
        
        // Clear previous content
        slider.innerHTML = '';
        paginationContainer.innerHTML = '';
        
        // Check if there are pages with images to display
        const hasPages = doc.data.pages && doc.data.pages.length > 0;
        const hasImages = hasPages && doc.data.pages.some(page => page.image_url);
        
        if (hasImages) {
            // Hide empty message
            emptyMessage.style.display = 'none';
            sliderContainer.classList.remove('single-slide');
            
            // Add each page as a slide
            doc.data.pages.forEach((page, index) => {
                if (page.image_url) {
                    // Create slide
                    const slide = document.createElement('div');
                    slide.className = 'slide';
                    slide.dataset.index = index;
                    
                    // Create slide content with image and text
                    slide.innerHTML = `
                        <div class="slide-content">
                            <div class="slide-image-container">
                                <img class="slide-image" src="${page.image_url}" alt="Page ${index + 1}" loading="lazy">
                            </div>
                            <div class="slide-text">${page.text || 'No text available for this image'}</div>
                        </div>
                    `;
                    
                    slider.appendChild(slide);
                    
                    // Create pagination dot
                    const dot = document.createElement('div');
                    dot.className = 'pagination-dot';
                    dot.dataset.index = index;
                    if (index === 0) dot.classList.add('active');
                    
                    dot.addEventListener('click', () => goToSlide(index));
                    paginationContainer.appendChild(dot);
                }
            });
            
            // Check if we need navigation (more than one slide)
            if (slider.children.length <= 1) {
                sliderContainer.classList.add('single-slide');
            } else {
                // Set up event listeners for navigation buttons
                prevButton.addEventListener('click', () => navigateSlider('prev'));
                nextButton.addEventListener('click', () => navigateSlider('next'));
                
                // Add keyboard navigation
                document.addEventListener('keydown', handleSliderKeyboard);
            }
        } else {
            // Show empty message
            emptyMessage.style.display = 'block';
            sliderContainer.classList.add('single-slide');
        }
    }

    // Global variables for slider state
    let currentSlide = 0;
    let totalSlides = 0;

    function navigateSlider(direction) {
        const slider = document.getElementById('image-slider');
        totalSlides = slider.children.length;
        
        if (totalSlides <= 1) return;
        
        if (direction === 'prev') {
            currentSlide = (currentSlide > 0) ? currentSlide - 1 : totalSlides - 1;
        } else {
            currentSlide = (currentSlide < totalSlides - 1) ? currentSlide + 1 : 0;
        }
        
        goToSlide(currentSlide);
    }

    function goToSlide(index) {
        const slider = document.getElementById('image-slider');
        const dots = document.querySelectorAll('.pagination-dot');
        totalSlides = slider.children.length;
        
        if (index < 0 || index >= totalSlides) return;
        
        currentSlide = index;
        
        // Update slider position
        slider.style.transform = `translateX(-${currentSlide * 100}%)`;
        
        // Update pagination dots
        dots.forEach((dot, i) => {
            dot.classList.toggle('active', i === currentSlide);
        });
    }

    function handleSliderKeyboard(e) {
        // Only handle keys when modal is visible and image tab is active
        const modal = document.getElementById('view-document-modal');
        const imageTab = document.querySelector('.tab-content[data-tab="images"]');
        
        if (modal.classList.contains('hidden') || !imageTab.classList.contains('active')) {
            return;
        }
        
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            navigateSlider(e.key === 'ArrowLeft' ? 'prev' : 'next');
            e.preventDefault();
        }
    }

    function resetTabsToDefault() {
        // Reset current slide
        currentSlide = 0;
        
        // Set Document tab as active
        const tabButtons = document.querySelectorAll('.modal-tabs .tab-btn');
        tabButtons.forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-tab') === 'document');
        });
        
        // Show Document content, hide Images content
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            content.classList.toggle('active', content.getAttribute('data-tab') === 'document');
        });
    }

    function editDocument(doc) {
        state.currentDocument = doc;
        elements.documentTitle.value = doc.title;
        elements.documentContent.value = doc.data.pages[0]?.text || '';
        elements.documentModal.classList.remove('hidden');
    }

    function confirmDeleteDocument(doc) {
        state.currentDocument = doc;
        elements.deleteModal.classList.remove('hidden');
        
        // Set up the delete confirmation button
        elements.confirmDeleteBtn.onclick = function() {
            actions.deleteDocument(doc.id);
        };
    }

    // Modal helpers
    function closeDocumentModal() {
        elements.documentModal.classList.add('hidden');
    }

    function closeViewDocumentModal() {
        elements.viewDocumentModal.classList.add('hidden');
        
        // Remove keyboard event listener when closing modal
        document.removeEventListener('keydown', handleSliderKeyboard);
        
        setTimeout(() => {
            elements.viewDocumentModal.style.display = '';
        }, 300); // Match the animation duration
    }

    function closeDeleteModal() {
        elements.deleteModal.classList.add('hidden');
    }
    
    function closeNotificationModal() {
        elements.documentNotificationModal.classList.remove('show');
    }

    // Initialize the application
    init();
}); 