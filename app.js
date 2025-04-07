// DOM Elements
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const uploadBtn = document.getElementById('upload-btn');
const uploadProgress = document.getElementById('upload-progress');
const progressBar = uploadProgress.querySelector('.progress');
const wardrobeGrid = document.getElementById('wardrobe-grid');
const categoryFilter = document.getElementById('category-filter');
const colorFilter = document.getElementById('color-filter');
const seasonFilter = document.getElementById('season-filter');
const occasionSelect = document.getElementById('occasion-select');
const dateSelect = document.getElementById('date-select');
const getSuggestionsBtn = document.getElementById('get-suggestions');
const outfitsContainer = document.getElementById('outfits-container');
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendMessageBtn = document.getElementById('send-message');
const toggleChatbotBtn = document.getElementById('toggle-chatbot');
const chatbotBody = document.getElementById('chatbot-body');

// Hardcoded user ID for testing
const USER_ID = "user123";
const BASE_URL = "http://localhost:5000";

// Set today's date as default
const today = new Date();
const formattedDate = today.toISOString().split('T')[0];
dateSelect.value = formattedDate;

// Local wardrobe items cache
let wardrobeItems = [];

// Event Listeners
uploadArea.addEventListener('click', () => fileInput.click());
uploadBtn.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', handleFileUpload);
getSuggestionsBtn.addEventListener('click', getOutfitSuggestions);
toggleChatbotBtn.addEventListener('click', toggleChatbot);
sendMessageBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Filter event listeners
categoryFilter.addEventListener('change', filterWardrobe);
colorFilter.addEventListener('change', filterWardrobe);
seasonFilter.addEventListener('change', filterWardrobe);

// Initialize chatbot
let isChatbotVisible = true;

// Drag and drop functionality
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('active');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('active');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('active');
    if (e.dataTransfer.files.length) {
        fileInput.files = e.dataTransfer.files;
        handleFileUpload();
    }
});

// Functions
async function handleFileUpload() {
    if (!fileInput.files.length) return;

    uploadProgress.style.display = 'block';
    progressBar.style.width = '0%';

    const formData = new FormData();
    Array.from(fileInput.files).forEach(file => {
        formData.append('file', file);
    });

    try {
        const response = await fetch(`${BASE_URL}/api/upload/${USER_ID}`, {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.status === 'success') {
            wardrobeItems.push(data.item);
            displayWardrobeItems();
            addChatMessage(`I've added your ${data.item.colors[0]} ${data.item.category} to your wardrobe.`, 'assistant');
            // Display organization result
            addChatMessage(data.organization.message, 'assistant');
        }

        let progress = 0;
        const interval = setInterval(() => {
            progress += 5;
            progressBar.style.width = `${progress}%`;
            if (progress >= 100) {
                clearInterval(interval);
                uploadProgress.style.display = 'none';
            }
        }, 100);
    } catch (error) {
        console.error('Upload error:', error);
        addChatMessage('Sorry, there was an error uploading your file.', 'assistant');
        uploadProgress.style.display = 'none';
    }
}

function displayWardrobeItems(filtered = wardrobeItems) {
    wardrobeGrid.innerHTML = '';
    filtered.forEach(item => {
        const itemElement = document.createElement('div');
        itemElement.className = 'clothing-item';
        itemElement.innerHTML = `
            <img src="${item.image_url}" alt="${item.name}">
            <div class="item-actions">
                <button onclick="editItem('${item.id}')"><i class="fas fa-edit"></i></button>
                <button onclick="deleteItem('${item.id}')"><i class="fas fa-trash"></i></button>
            </div>
            <div class="item-info">
                <h4>${item.name}</h4>
                <p>${item.colors[0]} ${item.category}</p>
                <p>Seasons: ${item.seasons.join(', ')}</p>
            </div>
        `;
        wardrobeGrid.appendChild(itemElement);
    });
    if (filtered.length === 0) {
        wardrobeGrid.innerHTML = '<p>No items match your filters.</p>';
    }
}

window.editItem = async function(id) {
    // Basic edit functionality - could be expanded with a modal
    const newName = prompt('Enter new name:');
    if (newName) {
        try {
            const response = await fetch(`${BASE_URL}/api/wardrobe/${USER_ID}/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName })
            });
            const data = await response.json();
            if (data.status === 'success') {
                wardrobeItems = wardrobeItems.map(item => item.id === id ? data.item : item);
                displayWardrobeItems();
            }
        } catch (error) {
            console.error('Edit error:', error);
        }
    }
};

window.deleteItem = async function(id) {
    if (confirm('Are you sure you want to delete this item?')) {
        try {
            const response = await fetch(`${BASE_URL}/api/wardrobe/${USER_ID}/${id}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            if (data.status === 'success') {
                wardrobeItems = wardrobeItems.filter(item => item.id !== id);
                displayWardrobeItems();
            }
        } catch (error) {
            console.error('Delete error:', error);
        }
    }
};

async function filterWardrobe() {
    const category = categoryFilter.value;
    const color = colorFilter.value;
    const season = seasonFilter.value;

    try {
        const response = await fetch(`${BASE_URL}/api/wardrobe/${USER_ID}?category=${category}&color=${color}&season=${season}`);
        const data = await response.json();
        displayWardrobeItems(data.wardrobe);
    } catch (error) {
        console.error('Filter error:', error);
        displayWardrobeItems([]);
    }
}

async function getOutfitSuggestions() {
    const occasion = occasionSelect.value;
    const date = dateSelect.value;
    outfitsContainer.innerHTML = '';

    try {
        const response = await fetch(`${BASE_URL}/api/outfits/${USER_ID}?occasion=${occasion}&date=${date}&count=3`);
        const data = await response.json();

        if (data.outfits.length === 0) {
            outfitsContainer.innerHTML = '<p>You need more items in your wardrobe to get outfit suggestions.</p>';
            return;
        }

        data.outfits.forEach((outfit, index) => displayOutfit(outfit, index + 1));
        addChatMessage(`I've created ${data.outfits.length} outfit suggestions for your ${occasion} occasion on ${date}.`, 'assistant');
    } catch (error) {
        console.error('Suggestions error:', error);
        outfitsContainer.innerHTML = '<p>Error fetching outfit suggestions.</p>';
    }
}

function displayOutfit(outfit, number) {
    const outfitElement = document.createElement('div');
    outfitElement.className = 'outfit-card';

    let itemsHTML = '';
    outfit.items.forEach(item => {
        itemsHTML += `<img src="${item.image_url}" class="outfit-item" alt="${item.name}">`;
    });

    outfitElement.innerHTML = `
        <div class="outfit-items">
            ${itemsHTML}
        </div>
        <div class="outfit-info">
            <h4>Outfit ${number}</h4>
            <p>${outfit.description}</p>
            <button class="btn" onclick="saveOutfit('${outfit.id}')">Save Outfit</button>
        </div>
    `;
    outfitsContainer.appendChild(outfitElement);
}

window.saveOutfit = async function(outfitId) {
    try {
        const outfit = (await (await fetch(`${BASE_URL}/api/outfits/${USER_ID}?occasion=${occasionSelect.value}&date=${dateSelect.value}`)).json()).outfits.find(o => o.id === outfitId);
        const response = await fetch(`${BASE_URL}/api/outfits/${USER_ID}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                items: outfit.items.map(item => item.id),
                occasion: outfit.occasion,
                name: `Outfit ${outfitsContainer.children.length + 1}`
            })
        });
        const data = await response.json();
        if (data.status === 'success') {
            alert('Outfit saved!');
        }
    } catch (error) {
        console.error('Save error:', error);
    }
};

function toggleChatbot() {
    isChatbotVisible = !isChatbotVisible;
    chatbotBody.style.display = isChatbotVisible ? 'flex' : 'none';
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    addChatMessage(message, 'user');
    userInput.value = '';

    try {
        const response = await fetch(`${BASE_URL}/api/chat/${USER_ID}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: message })
        });
        const data = await response.json();
        addChatMessage(data.response, 'assistant');
    } catch (error) {
        console.error('Chat error:', error);
        addChatMessage('Sorry, I couldn’t process that. Try again!', 'assistant');
    }
}

function addChatMessage(message, sender) {
    const messageElement = document.createElement('div');
    messageElement.className = `message ${sender}`;
    messageElement.innerHTML = `
        <div class="message-content">
            ${message}
        </div>
    `;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Initialize with wardrobe data and welcome message
window.onload = async function() {
    toggleChatbot(); // Start with open chatbot
    try {
        const response = await fetch(`${BASE_URL}/api/wardrobe/${USER_ID}`);
        const data = await response.json();
        wardrobeItems = data.wardrobe;
        displayWardrobeItems();
        
        setTimeout(() => {
            addChatMessage("Welcome to SmartWardrobe! Start by uploading some of your favorite clothes, and I'll help you organize them and create outfit suggestions.", 'assistant');
        }, 1000);
    } catch (error) {
        console.error('Initialization error:', error);
    }
};