// Mobile SAHA-AI JavaScript
// Enhanced mobile functionality for SAHA-AI

class MobileSAHA {
    constructor() {
        this.isInitialized = false;
        this.chatHistory = [];
        this.currentUser = null;
        this.marketData = null;
        this.isOnline = navigator.onLine;
        
        this.init();
    }
    
    init() {
        if (this.isInitialized) return;
        
        this.setupEventListeners();
        this.setupOfflineDetection();
        this.loadMarketData();
        this.setupSwipeGestures();
        this.setupTouchOptimizations();
        
        this.isInitialized = true;
        console.log('Mobile SAHA-AI initialized');
    }
    
    setupEventListeners() {
        // Chat functionality
        const sendButton = document.getElementById('send-button-mobile');
        const userInput = document.getElementById('user-input-mobile');
        
        if (sendButton && userInput) {
            sendButton.addEventListener('click', () => this.sendMessage());
            userInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.sendMessage();
                }
            });
        }
        
        // Quick suggestions
        const suggestions = document.querySelectorAll('.suggestion-chip-mobile');
        suggestions.forEach(chip => {
            chip.addEventListener('click', () => {
                const text = chip.textContent.trim();
                this.handleQuickSuggestion(text);
            });
        });
        
        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle-mobile');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
        
        // Refresh button
        const refreshBtn = document.getElementById('refresh-portfolio-mobile');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshPortfolio());
        }
    }
    
    setupOfflineDetection() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.showNotification('Connection restored', 'success');
            this.loadMarketData();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showNotification('You are offline', 'warning');
        });
    }
    
    setupSwipeGestures() {
        let startX = 0;
        let startY = 0;
        let isSwipe = false;
        
        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
            isSwipe = false;
        });
        
        document.addEventListener('touchmove', (e) => {
            if (!isSwipe) {
                const deltaX = Math.abs(e.touches[0].clientX - startX);
                const deltaY = Math.abs(e.touches[0].clientY - startY);
                
                if (deltaX > deltaY && deltaX > 50) {
                    isSwipe = true;
                    e.preventDefault();
                }
            }
        });
        
        document.addEventListener('touchend', (e) => {
            if (isSwipe) {
                const deltaX = e.changedTouches[0].clientX - startX;
                
                if (Math.abs(deltaX) > 100) {
                    if (deltaX > 0) {
                        this.handleSwipeRight();
                    } else {
                        this.handleSwipeLeft();
                    }
                }
            }
        });
    }
    
    setupTouchOptimizations() {
        // Prevent zoom on double tap
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (e) => {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        });
        
        // Optimize scroll performance
        document.addEventListener('touchmove', (e) => {
            if (e.target.closest('.swipe-container')) {
                e.preventDefault();
            }
        }, { passive: false });
    }
    
    async sendMessage() {
        const userInput = document.getElementById('user-input-mobile');
        const message = userInput.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        this.addMessageToChat(message, 'user');
        userInput.value = '';
        
        // Show typing indicator
        this.showTypingIndicator();
        
        try {
            const response = await fetch('/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                credentials: 'include',
                body: JSON.stringify({ message: message })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.hideTypingIndicator();
            this.addMessageToChat(data.response, 'bot');
            
            // Handle special responses (charts, portfolio updates, etc.)
            if (data.chart_data) {
                this.renderChart(data.chart_data);
            }
            
            if (data.portfolio_update) {
                this.updatePortfolioDisplay();
            }
            
        } catch (error) {
            this.hideTypingIndicator();
            this.addMessageToChat('Sorry, I encountered an error. Please try again.', 'bot');
            console.error('Chat error:', error);
        }
    }
    
    addMessageToChat(message, sender) {
        const chatWindow = document.getElementById('chat-window-mobile');
        if (!chatWindow) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-bubble chat-bubble-${sender}`;
        messageDiv.textContent = message;
        
        chatWindow.appendChild(messageDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        
        // Store in chat history
        this.chatHistory.push({ message, sender, timestamp: new Date() });
    }
    
    showTypingIndicator() {
        const chatWindow = document.getElementById('chat-window-mobile');
        if (!chatWindow) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.id = 'typing-indicator';
        typingDiv.className = 'chat-bubble chat-bubble-bot';
        typingDiv.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
        
        chatWindow.appendChild(typingDiv);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }
    
    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    handleQuickSuggestion(text) {
        const userInput = document.getElementById('user-input-mobile');
        if (userInput) {
            userInput.value = text;
            this.sendMessage();
        }
    }
    
    async loadMarketData() {
        if (!this.isOnline) return;
        
        try {
            const response = await fetch('/api/market-snapshot/', {
                method: 'GET',
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                this.marketData = data;
                this.renderMarketCards(data);
            }
        } catch (error) {
            console.error('Error loading market data:', error);
        }
    }
    
    renderMarketCards(data) {
        const marketCards = document.getElementById('market-cards-mobile');
        if (!marketCards) return;
        
        const cards = [
            { name: 'NIFTY 50', value: data.nifty_price, change: data.nifty_change, change_pct: data.nifty_change_pct },
            { name: 'SENSEX', value: data.sensex_price, change: data.sensex_change, change_pct: data.sensex_change_pct },
            { name: 'BANK NIFTY', value: data.bank_nifty_price, change: data.bank_nifty_change, change_pct: data.bank_nifty_change_pct }
        ];
        
        marketCards.innerHTML = cards.map(card => `
            <div class="swipe-item mobile-card min-w-[280px]">
                <div class="flex items-center justify-between mb-2">
                    <h3 class="font-semibold text-gray-900 dark:text-gray-100">${card.name}</h3>
                    <span class="text-xs px-2 py-1 rounded-full ${card.change >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">
                        ${card.change >= 0 ? '+' : ''}${card.change_pct}%
                    </span>
                </div>
                <div class="text-2xl font-bold text-gray-900 dark:text-gray-100">${card.value}</div>
                <div class="text-sm text-gray-600 dark:text-gray-400">
                    ${card.change >= 0 ? '+' : ''}${card.change}
                </div>
            </div>
        `).join('');
    }
    
    handleSwipeLeft() {
        // Navigate to next section or page
        console.log('Swipe left detected');
    }
    
    handleSwipeRight() {
        // Navigate to previous section or page
        console.log('Swipe right detected');
    }
    
    toggleTheme() {
        const html = document.documentElement;
        const isDark = html.classList.contains('dark');
        
        if (isDark) {
            html.classList.remove('dark');
            localStorage.setItem('color-theme', 'light');
        } else {
            html.classList.add('dark');
            localStorage.setItem('color-theme', 'dark');
        }
        
        this.updateThemeIcons();
    }
    
    updateThemeIcons() {
        const darkIcon = document.getElementById('theme-toggle-dark-icon-mobile');
        const lightIcon = document.getElementById('theme-toggle-light-icon-mobile');
        const isDark = document.documentElement.classList.contains('dark');
        
        if (darkIcon && lightIcon) {
            if (isDark) {
                darkIcon.classList.add('hidden');
                lightIcon.classList.remove('hidden');
            } else {
                darkIcon.classList.remove('hidden');
                lightIcon.classList.add('hidden');
            }
        }
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'warning' ? 'bg-yellow-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : '';
    }
    
    async refreshPortfolio() {
        try {
            await this.loadPortfolioData();
            this.showNotification('Portfolio refreshed', 'success');
        } catch (error) {
            this.showNotification('Error refreshing portfolio', 'error');
            console.error('Portfolio refresh error:', error);
        }
    }
    
    async loadPortfolioData() {
        // This will be implemented when we integrate with the portfolio API
        console.log('Loading portfolio data...');
    }
}

// Initialize Mobile SAHA when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mobileSAHA = new MobileSAHA();
});

// Export for global access
window.MobileSAHA = MobileSAHA;
