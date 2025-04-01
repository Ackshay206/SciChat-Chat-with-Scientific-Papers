// Global variables
let currentConversationId = null;
let conversations = {};
let papers = [];
let stats = {
    paperCount: 0,
    conversationCount: 0,
    questionCount: 0
};

// DOM elements
const paperCountEl = document.getElementById('paper-count');
const conversationCountEl = document.getElementById('conversation-count');
const questionCountEl = document.getElementById('question-count');
const recentPapersListEl = document.getElementById('recent-papers-list');
const recentQuestionsListEl = document.getElementById('recent-questions-list');
const papersTableBodyEl = document.getElementById('papers-table-body');
const conversationsListEl = document.getElementById('conversations-list');
const chatMessagesEl = document.getElementById('chat-messages');
const chatInputEl = document.getElementById('chat-input');
const sendMessageBtn = document.getElementById('send-message');
const paperDetailsModalEl = document.getElementById('paper-details-modal');
const paperModalTitleEl = document.getElementById('paper-modal-title');
const paperModalBodyEl = document.getElementById('paper-modal-body');
const chatAboutPaperBtn = document.getElementById('chat-about-paper');
const uploadFormEl = document.getElementById('upload-form');
const fileUploadEl = document.getElementById('file-upload');
const uploadProgressContainerEl = document.getElementById('upload-progress-container');
const uploadProgressEl = document.getElementById('upload-progress');
const uploadStatusEl = document.getElementById('upload-status');
const uploadResultsEl = document.getElementById('upload-results');
const paperDetailsEl = document.getElementById('paper-details');

// Navigation elements
const dashboardLinkEl = document.getElementById('dashboard-link');
const papersLinkEl = document.getElementById('papers-link');
const chatLinkEl = document.getElementById('chat-link');
const uploadLinkEl = document.getElementById('upload-link');
const pageTitleEl = document.getElementById('page-title');
const dashboardSectionEl = document.getElementById('dashboard-section');
const papersSectionEl = document.getElementById('papers-section');
const chatSectionEl = document.getElementById('chat-section');
const uploadSectionEl = document.getElementById('upload-section');
const newConversationEl = document.getElementById('new-conversation');
const paperSearchEl = document.getElementById('paper-search');

// Initialize Bootstrap modal
let paperDetailsModal = null;
if (paperDetailsModalEl) {
    paperDetailsModal = new bootstrap.Modal(paperDetailsModalEl);
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    // Load data
    loadPapers();
    
    // Set up event listeners
    setupEventListeners();
    
    // Show dashboard by default
    showDashboard();
});

// Setup event listeners
function setupEventListeners() {
    // Navigation
    dashboardLinkEl.addEventListener('click', showDashboard);
    papersLinkEl.addEventListener('click', showPapers);
    chatLinkEl.addEventListener('click', showChat);
    uploadLinkEl.addEventListener('click', showUpload);
    
    // Chat functionality
    sendMessageBtn.addEventListener('click', sendMessage);
    chatInputEl.addEventListener('keypress', event => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });
    newConversationEl.addEventListener('click', createNewConversation);
    
    // Upload functionality
    uploadFormEl.addEventListener('submit', uploadPaper);
    
    // Paper search
    paperSearchEl.addEventListener('input', filterPapers);
    
    // Chat about paper button
    chatAboutPaperBtn.addEventListener('click', () => {
        const paperId = chatAboutPaperBtn.getAttribute('data-paper-id');
        const paperTitle = chatAboutPaperBtn.getAttribute('data-paper-title');
        
        // Create a new conversation about this paper
        createNewConversation();
        showChat();
        
        // Add a system message about the selected paper
        appendMessage('bot', `You're now chatting about the paper: "${paperTitle}". What would you like to know?`);
        
        // Close the modal
        paperDetailsModal.hide();
    });
}

// Navigation functions
function showDashboard(event) {
    event?.preventDefault();
    setActiveLink(dashboardLinkEl);
    pageTitleEl.textContent = 'Dashboard';
    showSection(dashboardSectionEl);
    updateDashboardStats();
}

function showPapers(event) {
    event?.preventDefault();
    setActiveLink(papersLinkEl);
    pageTitleEl.textContent = 'Papers';
    showSection(papersSectionEl);
}

function showChat(event) {
    event?.preventDefault();
    setActiveLink(chatLinkEl);
    pageTitleEl.textContent = 'Chat';
    showSection(chatSectionEl);
    
    // Create a new conversation if none exists
    if (!currentConversationId) {
        createNewConversation();
    }
}

function showUpload(event) {
    event?.preventDefault();
    setActiveLink(uploadLinkEl);
    pageTitleEl.textContent = 'Upload Paper';
    showSection(uploadSectionEl);
}

function setActiveLink(element) {
    // Remove active class from all links
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    // Add active class to the clicked link
    element.classList.add('active');
}

function showSection(element) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(section => {
        section.classList.add('d-none');
    });
    
    // Show the selected section
    element.classList.remove('d-none');
}

// API functions
async function loadPapers() {
    try {
        const response = await fetch('/documents');
        papers = await response.json();
        
        // Update stats
        stats.paperCount = papers.length;
        
        // Update UI
        updatePapersTable();
        updateRecentPapersList();
        updateDashboardStats();
    } catch (error) {
        console.error('Error loading papers:', error);
    }
}

async function askQuestion(question, conversationId, metadata = false) {
    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                conversation_id: conversationId,
                metadata_only: metadata
            }),
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error asking question:', error);
        return {
            answer: 'Sorry, there was an error processing your question.',
            conversation_id: conversationId
        };
    }
}

// Chat functions
function createNewConversation() {
    currentConversationId = generateUUID();
    conversations[currentConversationId] = {
        messages: [],
        created: new Date().toISOString()
    };
    
    // Update stats
    stats.conversationCount++;
    updateDashboardStats();
    
    // Update UI
    updateConversationsList();
    clearChatMessages();
    appendMessage('bot', 'Hello! How can I help you with your scientific papers today?');
}

function clearChatMessages() {
    chatMessagesEl.innerHTML = '';
}

function appendMessage(sender, text) {
    const messageEl = document.createElement('div');
    messageEl.classList.add('chat-message');
    
    if (sender === 'user') {
        messageEl.classList.add('user-message');
        
        // Add message to the current conversation
        if (currentConversationId && conversations[currentConversationId]) {
            conversations[currentConversationId].messages.push({
                sender: 'user',
                text: text,
                timestamp: new Date().toISOString()
            });
        }
    } else {
        messageEl.classList.add('bot-message');
        
        // Add message to the current conversation
        if (currentConversationId && conversations[currentConversationId]) {
            conversations[currentConversationId].messages.push({
                sender: 'bot',
                text: text,
                timestamp: new Date().toISOString()
            });
        }
    }
    
    const textEl = document.createElement('div');
    textEl.textContent = text;
    messageEl.appendChild(textEl);
    
    const timeEl = document.createElement('div');
    timeEl.classList.add('message-time');
    timeEl.textContent = formatTime(new Date());
    messageEl.appendChild(timeEl);
    
    chatMessagesEl.appendChild(messageEl);
    
    // Scroll to bottom
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
    
    // Update recent questions list
    if (sender === 'user') {
        updateRecentQuestionsList();
        
        // Update stats
        stats.questionCount++;
        updateDashboardStats();
    }
}

async function sendMessage() {
    const question = chatInputEl.value.trim();
    
    if (!question) {
        return;
    }
    
    // Clear input
    chatInputEl.value = '';
    
    // Add user message to chat
    appendMessage('user', question);
    
    // Show typing indicator
    const typingIndicator = document.createElement('div');
    typingIndicator.classList.add('chat-message', 'bot-message', 'typing-indicator');
    typingIndicator.innerHTML = '<div class="typing-dots"><span>.</span><span>.</span><span>.</span></div>';
    chatMessagesEl.appendChild(typingIndicator);
    chatMessagesEl.scrollTop = chatMessagesEl.scrollHeight;
    
    // Get answer from API
    const response = await askQuestion(question, currentConversationId);
    
    // Remove typing indicator
    chatMessagesEl.removeChild(typingIndicator);
    
    // Add bot message to chat
    appendMessage('bot', response.answer);
}

// Upload functions
async function uploadPaper(event) {
    event.preventDefault();
    
    const fileInput = fileUploadEl;
    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please select a PDF file to upload.');
        return;
    }
    
    const file = fileInput.files[0];
    if (file.type !== 'application/pdf') {
        alert('Only PDF files are supported.');
        return;
    }
    
    // Show progress bar
    uploadProgressContainerEl.classList.remove('d-none');
    uploadResultsEl.classList.add('d-none');
    uploadProgressEl.style.width = '0%';
    uploadStatusEl.textContent = 'Uploading...';
    
    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 5;
            if (progress > 90) {
                clearInterval(progressInterval);
            }
            uploadProgressEl.style.width = `${progress}%`;
        }, 200);
        
        // Upload file
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        // Clear progress interval
        clearInterval(progressInterval);
        
        if (!response.ok) {
            throw new Error('Upload failed');
        }
        
        // Set progress to 100%
        uploadProgressEl.style.width = '100%';
        uploadStatusEl.textContent = 'Processing...';
        
        // Get paper details
        const paperData = await response.json();
        
        // Update UI
        uploadStatusEl.textContent = 'Upload complete!';
        uploadResultsEl.classList.remove('d-none');
        
        // Display paper details
        const paperDetailsHTML = `
            <p><strong>Title:</strong> ${paperData.title}</p>
            <p><strong>Authors:</strong> ${paperData.authors}</p>
            <p><strong>Organizations:</strong> ${paperData.organizations}</p>
            <p><strong>Email Contacts:</strong> ${paperData.emails}</p>
        `;
        
        document.getElementById('paper-details').innerHTML = paperDetailsHTML;
        
        // Update papers list
        papers.push(paperData);
        updatePapersTable();
        updateRecentPapersList();
        
        // Update stats
        stats.paperCount++;
        updateDashboardStats();
        
        // Reset form
        fileUploadEl.value = '';
        
    } catch (error) {
        console.error('Error uploading paper:', error);
        uploadStatusEl.textContent = 'Upload failed: ' + error.message;
        uploadProgressEl.classList.add('bg-danger');
    }
}

// UI update functions
function updatePapersTable() {
    papersTableBodyEl.innerHTML = '';
    
    if (papers.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="4" class="text-center">No papers uploaded yet</td>`;
        papersTableBodyEl.appendChild(row);
        return;
    }
    
    papers.forEach(paper => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${paper.title}</td>
            <td>${paper.authors}</td>
            <td>${paper.organizations}</td>
            <td>
                <button class="btn btn-sm btn-primary view-paper-btn" data-id="${paper.id}">
                    <i class="bi bi-eye"></i> View
                </button>
                <button class="btn btn-sm btn-success chat-paper-btn" data-id="${paper.id}" data-title="${paper.title}">
                    <i class="bi bi-chat"></i> Chat
                </button>
            </td>
        `;
        papersTableBodyEl.appendChild(row);
        
        // Add event listeners to buttons
        row.querySelector('.view-paper-btn').addEventListener('click', () => {
            showPaperDetails(paper);
        });
        
        row.querySelector('.chat-paper-btn').addEventListener('click', () => {
            createNewConversation();
            showChat();
            appendMessage('bot', `You're now chatting about the paper: "${paper.title}". What would you like to know?`);
        });
    });
}

function updateRecentPapersList() {
    recentPapersListEl.innerHTML = '';
    
    if (papers.length === 0) {
        recentPapersListEl.innerHTML = `
            <div class="text-center p-3">
                <p class="text-muted">No papers uploaded yet</p>
            </div>
        `;
        return;
    }
    
    // Show only the 5 most recent papers
    const recentPapers = [...papers].sort((a, b) => b.id.localeCompare(a.id)).slice(0, 5);
    
    recentPapers.forEach(paper => {
        const item = document.createElement('a');
        item.href = '#';
        item.classList.add('list-group-item', 'list-group-item-action', 'paper-list-item');
        item.innerHTML = `
            <div class="d-flex justify-content-between">
                <h6 class="mb-1">${paper.title}</h6>
            </div>
            <p class="mb-1">${paper.authors}</p>
        `;
        
        item.addEventListener('click', (event) => {
            event.preventDefault();
            showPaperDetails(paper);
        });
        
        recentPapersListEl.appendChild(item);
    });
}

function updateRecentQuestionsList() {
    recentQuestionsListEl.innerHTML = '';
    
    // Get all questions from all conversations
    const allQuestions = [];
    
    Object.entries(conversations).forEach(([id, conversation]) => {
        conversation.messages.forEach(message => {
            if (message.sender === 'user') {
                allQuestions.push({
                    text: message.text,
                    timestamp: message.timestamp,
                    conversationId: id
                });
            }
        });
    });
    
    if (allQuestions.length === 0) {
        recentQuestionsListEl.innerHTML = `
            <div class="text-center p-3">
                <p class="text-muted">No questions asked yet</p>
            </div>
        `;
        return;
    }
    
    // Sort by timestamp (newest first) and take only the 5 most recent
    const recentQuestions = allQuestions
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, 5);
    
    recentQuestions.forEach(question => {
        const item = document.createElement('a');
        item.href = '#';
        item.classList.add('list-group-item', 'list-group-item-action');
        item.innerHTML = `
            <div class="d-flex justify-content-between">
                <h6 class="mb-1">${question.text}</h6>
                <small>${formatDate(new Date(question.timestamp))}</small>
            </div>
        `;
        
        item.addEventListener('click', (event) => {
            event.preventDefault();
            
            // Switch to the conversation
            currentConversationId = question.conversationId;
            showChat();
            
            // Reload the conversation
            loadConversation(question.conversationId);
        });
        
        recentQuestionsListEl.appendChild(item);
    });
}

function updateConversationsList() {
    // Keep the "New Conversation" button
    conversationsListEl.innerHTML = '';
    conversationsListEl.appendChild(newConversationEl);
    
    // Add all conversations
    Object.entries(conversations).forEach(([id, conversation]) => {
        // Get the first user message as the conversation title
        let title = 'Conversation';
        for (const message of conversation.messages) {
            if (message.sender === 'user') {
                title = message.text.substring(0, 30) + (message.text.length > 30 ? '...' : '');
                break;
            }
        }
        
        const item = document.createElement('a');
        item.href = '#';
        item.classList.add('list-group-item', 'list-group-item-action');
        
        if (id === currentConversationId) {
            item.classList.add('active');
        }
        
        item.innerHTML = `
            <div class="d-flex justify-content-between">
                <div>${title}</div>
                <button class="btn btn-sm btn-outline-danger delete-conversation-btn">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
            <small>${formatDate(new Date(conversation.created))}</small>
        `;
        
        // Add event listener to switch to this conversation
        item.addEventListener('click', (event) => {
            if (event.target.closest('.delete-conversation-btn')) {
                // Delete conversation button was clicked
                return;
            }
            
            event.preventDefault();
            currentConversationId = id;
            loadConversation(id);
            
            // Update active class
            document.querySelectorAll('#conversations-list .list-group-item').forEach(el => {
                el.classList.remove('active');
            });
            item.classList.add('active');
        });
        
        // Add event listener to delete button
        item.querySelector('.delete-conversation-btn').addEventListener('click', async (event) => {
            event.preventDefault();
            event.stopPropagation();
            
            if (confirm('Are you sure you want to delete this conversation?')) {
                // Delete conversation
                try {
                    await fetch(`/conversations/${id}`, {
                        method: 'DELETE'
                    });
                    
                    // Remove from local store
                    delete conversations[id];
                    
                    // Update UI
                    updateConversationsList();
                    
                    // If this was the current conversation, create a new one
                    if (id === currentConversationId) {
                        createNewConversation();
                    }
                    
                    // Update stats
                    stats.conversationCount--;
                    updateDashboardStats();
                } catch (error) {
                    console.error('Error deleting conversation:', error);
                }
            }
        });
        
        conversationsListEl.appendChild(item);
    });
}

function loadConversation(id) {
    if (!conversations[id]) {
        return;
    }
    
    // Clear chat messages
    clearChatMessages();
    
    // Add all messages
    conversations[id].messages.forEach(message => {
        appendMessage(message.sender, message.text);
    });
}

function showPaperDetails(paper) {
    // Set modal title
    paperModalTitleEl.textContent = paper.title;
    
    // Set modal body
    paperModalBodyEl.innerHTML = `
        <div class="paper-info">
            <h6>Authors</h6>
            <p>${paper.authors}</p>
        </div>
        <div class="paper-info">
            <h6>Organizations</h6>
            <p>${paper.organizations}</p>
        </div>
        <div class="paper-info">
            <h6>Email Contacts</h6>
            <p>${paper.emails}</p>
        </div>
    `;
    
    // Set paper ID for chat button
    chatAboutPaperBtn.setAttribute('data-paper-id', paper.id);
    chatAboutPaperBtn.setAttribute('data-paper-title', paper.title);
    
    // Show modal
    paperDetailsModal.show();
}

function filterPapers() {
    const searchTerm = paperSearchEl.value.toLowerCase();
    
    // Get all table rows
    const rows = papersTableBodyEl.querySelectorAll('tr');
    
    // Loop through all rows
    rows.forEach(row => {
        const title = row.cells[0]?.textContent.toLowerCase() || '';
        const authors = row.cells[1]?.textContent.toLowerCase() || '';
        const orgs = row.cells[2]?.textContent.toLowerCase() || '';
        
        // Show/hide row based on search term
        if (title.includes(searchTerm) || authors.includes(searchTerm) || orgs.includes(searchTerm)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function updateDashboardStats() {
    // Update counters
    paperCountEl.textContent = stats.paperCount;
    conversationCountEl.textContent = stats.conversationCount;
    questionCountEl.textContent = stats.questionCount;
}

// Add the CSS for the typing indicator
function addTypingIndicatorCSS() {
    const style = document.createElement('style');
    style.textContent = `
        .typing-indicator {
            background-color: #f5f5f5;
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            max-width: 80%;
            margin-right: auto;
            border-top-left-radius: 0;
        }
        
        .typing-dots {
            display: flex;
            align-items: center;
            height: 20px;
        }
        
        .typing-dots span {
            height: 8px;
            width: 8px;
            margin-right: 4px;
            background-color: #aaa;
            border-radius: 50%;
            display: inline-block;
            animation: typing-dot 1.4s infinite ease-in-out both;
        }
        
        .typing-dots span:nth-child(1) {
            animation-delay: 0s;
        }
        
        .typing-dots span:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-dots span:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes typing-dot {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
}

// Utility functions
function formatTime(date) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatDate(date) {
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Add typing indicator CSS when DOM is loaded
document.addEventListener('DOMContentLoaded', addTypingIndicatorCSS);
