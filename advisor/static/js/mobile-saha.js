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
        this.setupPullToRefresh();
        
        // Live refresh market data every 30 seconds (like PC version)
        setInterval(() => {
            this.loadMarketData();
        }, 30000);
        
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
        
        // Connection status monitoring
        this.setupConnectionStatus();
        
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
            this.updateConnectionStatus('online');
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.showNotification('You are offline', 'warning');
            this.updateConnectionStatus('offline');
        });
    }
    
    setupConnectionStatus() {
        const connectionStatus = document.getElementById('connection-status-mobile');
        const connectionText = document.getElementById('connection-text-mobile');
        
        if (connectionStatus && connectionText) {
            // Initial status
            this.updateConnectionStatus(navigator.onLine ? 'online' : 'offline');
            
            // Periodic connection check
            setInterval(() => {
                this.checkConnectionStatus();
            }, 30000); // Check every 30 seconds
        }
    }
    
    updateConnectionStatus(status) {
        const connectionStatus = document.getElementById('connection-status-mobile');
        const connectionText = document.getElementById('connection-text-mobile');
        
        if (connectionStatus && connectionText) {
            if (status === 'online') {
                connectionStatus.classList.remove('hidden');
                connectionText.textContent = '🟢 Connected';
                connectionText.className = 'text-xs text-green-600 dark:text-green-400';
            } else if (status === 'offline') {
                connectionStatus.classList.remove('hidden');
                connectionText.textContent = '🔴 Offline';
                connectionText.className = 'text-xs text-red-600 dark:text-red-400';
            } else if (status === 'checking') {
                connectionStatus.classList.remove('hidden');
                connectionText.textContent = '🟡 Checking connection...';
                connectionText.className = 'text-xs text-yellow-600 dark:text-yellow-400';
            }
            
            // Hide status after 3 seconds if online
            if (status === 'online') {
                setTimeout(() => {
                    connectionStatus.classList.add('hidden');
                }, 3000);
            }
        }
    }
    
    async checkConnectionStatus() {
        try {
            this.updateConnectionStatus('checking');
            
            // Try to fetch a small resource to test connectivity
            const response = await fetch('/market-snapshot/', {
                method: 'HEAD',
                cache: 'no-cache'
            });
            
            if (response.ok) {
                this.isOnline = true;
                this.updateConnectionStatus('online');
            } else {
                this.isOnline = false;
                this.updateConnectionStatus('offline');
            }
        } catch (error) {
            this.isOnline = false;
            this.updateConnectionStatus('offline');
        }
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
            const csrfToken = this.getCSRFToken();
            console.log('CSRF Token:', csrfToken ? 'Found' : 'Not found');
            
            const response = await fetch('/mobile-chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'include',
                body: JSON.stringify({ message: message })
            });
            
            console.log('Chat API Response:', response.status, response.statusText);
            
            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error('Authentication required. Please refresh the page and try again.');
                } else if (response.status === 404) {
                    throw new Error('API endpoint not found. Please check server configuration.');
                } else {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
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
            
            // Check if response contains stock analysis and add portfolio button
            this.addPortfolioButtonsIfNeeded(data.response, message);
            
            // Auto-scroll to bottom after adding message
            this.scrollToBottom();
            
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
        messageDiv.className = `chat-bubble chat-bubble-${sender} mb-4`;
        
        // Check if this is a structured response that needs visual rendering
        if (sender === 'bot' && this.isStructuredResponse(message)) {
            messageDiv.innerHTML = this.renderStructuredResponse(message);
        } else {
            messageDiv.textContent = message;
        }
        
        chatWindow.appendChild(messageDiv);
        
        // Smooth scroll to bottom
        setTimeout(() => {
            chatWindow.scrollTo({
                top: chatWindow.scrollHeight,
                behavior: 'smooth'
            });
        }, 100);
        
        // Store in chat history
        this.chatHistory.push({ message, sender, timestamp: new Date() });
    }
    
    isStructuredResponse(message) {
        return message.includes('**ANALYSIS**') || 
               message.includes('**PORTFOLIO ANALYSIS**') || 
               message.includes('**MUTUAL FUND ANALYSIS**') ||
               message.includes('Current Price:') ||
               message.includes('Current NAV:');
    }
    
    renderStructuredResponse(message) {
        // Stock Analysis
        if (message.includes('**ANALYSIS**') && message.includes('Current Price:')) {
            return this.renderStockAnalysis(message);
        }
        
        // Mutual Fund Analysis
        if (message.includes('**ANALYSIS**') && message.includes('Current NAV:')) {
            return this.renderMutualFundAnalysis(message);
        }
        
        // Portfolio Analysis
        if (message.includes('**PORTFOLIO ANALYSIS**')) {
            return this.renderPortfolioAnalysis(message);
        }
        
        // Default structured response
        return this.renderDefaultStructured(message);
    }
    
    renderStockAnalysis(message) {
        // Extract data from message
        const priceMatch = message.match(/\*\*Current Price:\*\* ₹([0-9,]+\.?\d*)/);
        const changeMatch = message.match(/\(([+-]?\d+\.?\d*), ([+-]?\d+\.?\d*)%\)/);
        const marketCapMatch = message.match(/\*\*Market Cap:\*\* (₹[0-9,]+ \w+)/);
        const peMatch = message.match(/P\/E Ratio: ([\d.]+)/);
        const roeMatch = message.match(/ROE: ([\d.]+)%/);
        const recommendationMatch = message.match(/\*\*([^*]+)\*\*/g);
        
        const stockName = message.match(/\*\*([^*]+) ANALYSIS\*\*/)?.[1] || 'Stock Analysis';
        const currentPrice = priceMatch?.[1] || '0';
        const change = changeMatch?.[1] || '0';
        const changePercent = changeMatch?.[2] || '0';
        const marketCap = marketCapMatch?.[1] || 'N/A';
        const peRatio = peMatch?.[1] || 'N/A';
        const roe = roeMatch?.[1] || 'N/A';
        const recommendation = recommendationMatch?.[recommendationMatch.length - 1]?.replace(/\*/g, '') || 'HOLD';
        
        const isPositive = parseFloat(change) >= 0;
        
        return `
            <div class="stock-analysis-card bg-white dark:bg-gray-800 rounded-xl p-4 shadow-lg border border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">${stockName}</h3>
                    <div class="text-right">
                        <div class="text-xl font-bold text-gray-900 dark:text-white">₹${currentPrice}</div>
                        <div class="text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}">
                            ${isPositive ? '+' : ''}${change} (${isPositive ? '+' : ''}${changePercent}%)
                        </div>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <div class="metric-card bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                        <div class="text-xs text-gray-500 dark:text-gray-400">Market Cap</div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">${marketCap}</div>
                    </div>
                    <div class="metric-card bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                        <div class="text-xs text-gray-500 dark:text-gray-400">P/E Ratio</div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">${peRatio}</div>
                    </div>
                    <div class="metric-card bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                        <div class="text-xs text-gray-500 dark:text-gray-400">ROE</div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">${roe}%</div>
                    </div>
                    <div class="metric-card bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                        <div class="text-xs text-gray-500 dark:text-gray-400">Trend</div>
                        <div class="text-sm font-semibold text-green-600">Bullish</div>
                    </div>
                </div>
                
                <div class="recommendation-card bg-gradient-to-r ${isPositive ? 'from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20' : 'from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-800/20'} p-3 rounded-lg mb-4">
                    <div class="flex items-center">
                        <div class="w-2 h-2 ${isPositive ? 'bg-green-500' : 'bg-red-500'} rounded-full mr-2"></div>
                        <span class="text-sm font-semibold ${isPositive ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'}">${recommendation}</span>
                    </div>
                </div>
                
                <div class="flex space-x-2">
                    <button class="action-btn bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex-1">
                        📊 Add to Portfolio
                    </button>
                    <button class="action-btn bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-lg text-sm font-medium flex-1">
                        📈 Set Alert
                    </button>
                </div>
            </div>
        `;
    }
    
    renderMutualFundAnalysis(message) {
        // Extract data from message
        const navMatch = message.match(/\*\*Current NAV:\*\* ₹([0-9,]+\.?\d*)/);
        const changeMatch = message.match(/\(([+-]?\d+\.?\d*), ([+-]?\d+\.?\d*)%\)/);
        const categoryMatch = message.match(/\*\*Category:\*\* ([^*]+)/);
        const amcMatch = message.match(/\*\*AMC:\*\* ([^*]+)/);
        const aumMatch = message.match(/\*\*AUM:\*\* (₹[0-9,]+ \w+)/);
        const expenseMatch = message.match(/\*\*Expense Ratio:\*\* ([\d.]+)%/);
        
        const fundName = message.match(/\*\*([^*]+) ANALYSIS\*\*/)?.[1] || 'Fund Analysis';
        const nav = navMatch?.[1] || '0';
        const change = changeMatch?.[1] || '0';
        const changePercent = changeMatch?.[2] || '0';
        const category = categoryMatch?.[1] || 'N/A';
        const amc = amcMatch?.[1] || 'N/A';
        const aum = aumMatch?.[1] || 'N/A';
        const expenseRatio = expenseMatch?.[1] || 'N/A';
        
        const isPositive = parseFloat(change) >= 0;
        
        return `
            <div class="mf-analysis-card bg-white dark:bg-gray-800 rounded-xl p-4 shadow-lg border border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">${fundName}</h3>
                    <div class="text-right">
                        <div class="text-xl font-bold text-gray-900 dark:text-white">₹${nav}</div>
                        <div class="text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}">
                            ${isPositive ? '+' : ''}${change} (${isPositive ? '+' : ''}${changePercent}%)
                        </div>
                    </div>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-4">
                    <div class="metric-card bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                        <div class="text-xs text-gray-500 dark:text-gray-400">Category</div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">${category}</div>
                    </div>
                    <div class="metric-card bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                        <div class="text-xs text-gray-500 dark:text-gray-400">AMC</div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">${amc}</div>
                    </div>
                    <div class="metric-card bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                        <div class="text-xs text-gray-500 dark:text-gray-400">AUM</div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">${aum}</div>
                    </div>
                    <div class="metric-card bg-gray-50 dark:bg-gray-700 p-3 rounded-lg">
                        <div class="text-xs text-gray-500 dark:text-gray-400">Expense Ratio</div>
                        <div class="text-sm font-semibold text-gray-900 dark:text-white">${expenseRatio}%</div>
                    </div>
                </div>
                
                <div class="recommendation-card bg-gradient-to-r ${isPositive ? 'from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20' : 'from-red-50 to-red-100 dark:from-red-900/20 dark:to-red-800/20'} p-3 rounded-lg mb-4">
                    <div class="flex items-center">
                        <div class="w-2 h-2 ${isPositive ? 'bg-green-500' : 'bg-red-500'} rounded-full mr-2"></div>
                        <span class="text-sm font-semibold ${isPositive ? 'text-green-800 dark:text-green-200' : 'text-red-800 dark:text-red-200'}">${isPositive ? 'BUY' : 'HOLD'}</span>
                    </div>
                </div>
                
                <div class="flex space-x-2">
                    <button class="action-btn bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex-1">
                        💰 Start SIP
                    </button>
                    <button class="action-btn bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-lg text-sm font-medium flex-1">
                        📊 Compare
                    </button>
                </div>
            </div>
        `;
    }
    
    renderPortfolioAnalysis(message) {
        // Extract portfolio data
        const totalValueMatch = message.match(/\*\*Total Value:\*\* (₹[0-9,]+)/);
        const returnMatch = message.match(/\(([+-]₹[0-9,]+), ([+-]?\d+\.?\d*)%\)/);
        
        const totalValue = totalValueMatch?.[1] || '₹0';
        const returnAmount = returnMatch?.[1] || '+₹0';
        const returnPercent = returnMatch?.[2] || '0';
        
        const isPositive = parseFloat(returnPercent) >= 0;
        
        return `
            <div class="portfolio-analysis-card bg-white dark:bg-gray-800 rounded-xl p-4 shadow-lg border border-gray-200 dark:border-gray-700">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">Portfolio Overview</h3>
                    <div class="text-right">
                        <div class="text-xl font-bold text-gray-900 dark:text-white">${totalValue}</div>
                        <div class="text-sm ${isPositive ? 'text-green-600' : 'text-red-600'}">
                            ${returnAmount} (${isPositive ? '+' : ''}${returnPercent}%)
                        </div>
                    </div>
                </div>
                
                <div class="holdings-list space-y-3 mb-4">
                    <div class="holding-item flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div class="flex items-center">
                            <div class="w-3 h-3 bg-blue-500 rounded-full mr-3"></div>
                            <div>
                                <div class="font-semibold text-gray-900 dark:text-white">Reliance</div>
                                <div class="text-sm text-gray-500 dark:text-gray-400">₹85,000</div>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-sm font-semibold text-green-600">+3.2%</div>
                        </div>
                    </div>
                    
                    <div class="holding-item flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div class="flex items-center">
                            <div class="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
                            <div>
                                <div class="font-semibold text-gray-900 dark:text-white">TCS</div>
                                <div class="text-sm text-gray-500 dark:text-gray-400">₹65,000</div>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-sm font-semibold text-green-600">+2.8%</div>
                        </div>
                    </div>
                    
                    <div class="holding-item flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                        <div class="flex items-center">
                            <div class="w-3 h-3 bg-purple-500 rounded-full mr-3"></div>
                            <div>
                                <div class="font-semibold text-gray-900 dark:text-white">HDFC Bank</div>
                                <div class="text-sm text-gray-500 dark:text-gray-400">₹45,000</div>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-sm font-semibold text-green-600">+4.1%</div>
                        </div>
                    </div>
                </div>
                
                <div class="flex space-x-2">
                    <button class="action-btn bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium flex-1">
                        ➕ Add Stock
                    </button>
                    <button class="action-btn bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 px-4 py-2 rounded-lg text-sm font-medium flex-1">
                        📊 Rebalance
                    </button>
                </div>
            </div>
        `;
    }
    
    renderDefaultStructured(message) {
        // For other structured responses, format with better styling
        return `
            <div class="structured-response bg-white dark:bg-gray-800 rounded-xl p-4 shadow-lg border border-gray-200 dark:border-gray-700">
                <div class="prose dark:prose-invert max-w-none">
                    ${message.replace(/\*\*(.*?)\*\*/g, '<strong class="text-gray-900 dark:text-white">$1</strong>')
                             .replace(/\n/g, '<br>')
                             .replace(/•/g, '•')}
                </div>
            </div>
        `;
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
            // Remove emoji and clean up the text
            const cleanText = text.replace(/[📊💼📈💡]/g, '').trim();
            
            // Handle different suggestion types
            if (cleanText.includes('Analyze Stock')) {
                userInput.value = 'Analyze Stock';
            } else if (cleanText.includes('Mutual Funds')) {
                userInput.value = 'Mutual Fund Analysis';
            } else if (cleanText.includes('Portfolio')) {
                userInput.value = 'Portfolio';
            } else if (cleanText.includes('Investment Tips')) {
                userInput.value = 'Investment Tips';
            } else {
                userInput.value = cleanText;
            }
            
            this.sendMessage();
        }
    }
    
    // New function to handle quick action buttons
    handleQuickAction(action) {
        const userInput = document.getElementById('user-input-mobile');
        if (!userInput) return;
        
        switch(action) {
            case 'analyze-stock':
                userInput.value = 'Analyze Stock';
                userInput.placeholder = "Type stock name (e.g., 'Reliance' or 'Analyze TCS, I have 50 shares at ₹2,200')";
                break;
            case 'mutual-funds':
                userInput.value = 'Mutual Fund Analysis';
                userInput.placeholder = "Type fund name (e.g., 'SBI Bluechip' or 'HDFC Top 100')";
                break;
            case 'portfolio':
                // Show portfolio overview instead of sending message
                this.showPortfolioOverview();
                return; // Don't send message for portfolio
            case 'investment-tips':
                userInput.value = 'Investment Tips';
                userInput.placeholder = "Ask for investment advice or tips";
                break;
        }
        
        this.sendMessage();
    }
    
    // Function to show/hide portfolio overview
    showPortfolioOverview() {
        const portfolioOverview = document.getElementById('portfolio-overview-mobile');
        if (portfolioOverview) {
            if (portfolioOverview.style.display === 'none') {
                portfolioOverview.style.display = 'block';
                // Scroll to portfolio overview
                portfolioOverview.scrollIntoView({ behavior: 'smooth', block: 'start' });
            } else {
                portfolioOverview.style.display = 'none';
            }
        }
    }
    
    async loadMarketData() {
        if (!this.isOnline) return;
        
        try {
            const response = await fetch('/market-snapshot/', {
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
            { name: 'NIFTY 50', value: data.nifty_price, change: data.nifty_change, change_pct: data.nifty_change_pct, icon: '📈' },
            { name: 'SENSEX', value: data.sensex_price, change: data.sensex_change, change_pct: data.sensex_change_pct, icon: '📊' },
            { name: 'BANK NIFTY', value: data.bank_nifty_price, change: data.bank_nifty_change, change_pct: data.bank_nifty_change_pct, icon: '🏦' }
        ];
        
        marketCards.innerHTML = cards.map(card => `
            <div class="flex-1 mobile-card bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm">
                <div class="flex items-center justify-between mb-1">
                    <div class="flex items-center space-x-1">
                        <span class="text-sm">${card.icon}</span>
                        <h3 class="font-semibold text-gray-900 dark:text-gray-100 text-xs">${card.name}</h3>
                    </div>
                    <span class="text-xs px-1 py-0.5 rounded-full ${card.change >= 0 ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'}">
                        ${card.change >= 0 ? '+' : ''}${card.change_pct}%
                    </span>
                </div>
                <div class="text-sm font-bold text-gray-900 dark:text-gray-100 mb-1">${card.value}</div>
                <div class="text-xs text-gray-600 dark:text-gray-400">
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
        // Try multiple ways to get CSRF token
        let token = document.querySelector('[name=csrfmiddlewaretoken]');
        if (token) return token.value;
        
        token = document.querySelector('meta[name="csrf-token"]');
        if (token) return token.getAttribute('content');
        
        token = document.cookie.match(/csrftoken=([^;]+)/);
        if (token) return token[1];
        
        // Fallback: get from Django's CSRF cookie
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        
        console.warn('CSRF token not found');
        return '';
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
        // Show loading animation
        const loadingDiv = document.getElementById('portfolio-loading');
        const noHoldingsDiv = document.getElementById('no-holdings-message');
        
        if (loadingDiv) loadingDiv.style.display = 'block';
        if (noHoldingsDiv) noHoldingsDiv.classList.add('hidden');
        
        // Simulate loading delay
        setTimeout(() => {
            // Hide loading animation
            if (loadingDiv) loadingDiv.style.display = 'none';
            
            // Show no holdings message
            if (noHoldingsDiv) noHoldingsDiv.classList.remove('hidden');
        }, 2000);
        
        console.log('Loading portfolio data...');
    }
    
    // Add portfolio buttons to chat responses when stocks are analyzed
    addPortfolioButtonsIfNeeded(response, userMessage) {
        const userMessageLower = userMessage.toLowerCase();
        const responseLower = response.toLowerCase();
        
        console.log('Checking for portfolio buttons:', {
            userMessage: userMessage,
            responseLower: responseLower.substring(0, 100) + '...',
            hasAnalysis: responseLower.includes('analysis'),
            hasReliance: responseLower.includes('reliance'),
            hasTcs: responseLower.includes('tcs'),
            hasHdfc: responseLower.includes('hdfc'),
            hasInfosys: responseLower.includes('infosys')
        });
        
        // Check if this is a stock analysis response (detect any stock analysis, not just hardcoded ones)
        const isStockAnalysis = responseLower.includes('analysis') && 
                               responseLower.includes('current price') && // Real analysis has current price
                               !responseLower.includes('which stock') && // Don't show buttons when asking which stock
                               !responseLower.includes('let\'s start') && // Don't show buttons for initial prompts
                               !responseLower.includes('popular options'); // Don't show buttons for stock suggestions
        
        console.log('Is stock analysis:', isStockAnalysis);
        
        if (isStockAnalysis) {
            // Extract stock symbol from user message or response
            let stockSymbol = '';
            let stockName = '';
            let stockPrice = 0;
            
            if (userMessageLower.includes('reliance') || responseLower.includes('reliance')) {
                stockSymbol = 'RELIANCE';
                stockName = 'Reliance Industries Ltd';
                stockPrice = 2450.75;
            } else if (userMessageLower.includes('tcs') || responseLower.includes('tcs')) {
                stockSymbol = 'TCS';
                stockName = 'Tata Consultancy Services Ltd';
                stockPrice = 3680.50;
            } else if (userMessageLower.includes('hdfc') || responseLower.includes('hdfc')) {
                stockSymbol = 'HDFCBANK';
                stockName = 'HDFC Bank Ltd';
                stockPrice = 1650.25;
            } else if (userMessageLower.includes('infosys') || responseLower.includes('infosys')) {
                stockSymbol = 'INFY';
                stockName = 'Infosys Ltd';
                stockPrice = 1420.80;
            }
            
            console.log('Detected stock:', { stockSymbol, stockName, stockPrice });
            
            if (stockSymbol) {
                // Add portfolio button to the last bot message
                setTimeout(() => {
                    this.addPortfolioButtonToLastMessage(stockSymbol, stockName, stockPrice);
                }, 100);
            }
        }
    }
    
    addPortfolioButtonToLastMessage(symbol, name, price) {
        const chatWindow = document.getElementById('chat-window-mobile');
        if (!chatWindow) return;
        
        const botMessages = chatWindow.querySelectorAll('.chat-bubble-bot');
        const lastBotMessage = botMessages[botMessages.length - 1];
        
        if (lastBotMessage) {
            // Create portfolio button container
            const buttonContainer = document.createElement('div');
            buttonContainer.className = 'mt-3 flex space-x-2';
            buttonContainer.innerHTML = `
                <button onclick="mobileSAHA.addToPortfolioFromChat('${symbol}', '${name}', ${price})" 
                        class="flex-1 bg-green-500 hover:bg-green-600 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors">
                    📈 Add ${name.split(' ')[0]} to Portfolio
                </button>
                <button onclick="mobileSAHA.viewPortfolio()" 
                        class="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors">
                    💼 View Portfolio
                </button>
            `;
            
            lastBotMessage.appendChild(buttonContainer);
            
            // Scroll to bottom after adding portfolio buttons
            this.scrollToBottom();
        }
    }
    
    async addToPortfolioFromChat(symbol, name, price) {
        try {
            const quantity = prompt(`Enter quantity for ${name}:`, '1');
            if (!quantity || isNaN(quantity) || quantity <= 0) {
                alert('Invalid quantity');
                return;
            }
            
            const csrfToken = this.getCSRFToken();
            const response = await fetch('/portfolio/add/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'include',
                body: JSON.stringify({
                    symbol: symbol,
                    name: name,
                    quantity: parseInt(quantity),
                    price: parseFloat(price)
                })
            });
            
            if (response.ok) {
                this.addMessageToChat(`✅ ${name} added to portfolio successfully!`, 'bot');
                this.showNotification(`${name} added to portfolio`, 'success');
            } else {
                this.addMessageToChat('❌ Error adding to portfolio. Please try again.', 'bot');
            }
        } catch (error) {
            console.error('Error adding to portfolio:', error);
            this.addMessageToChat('❌ Error adding to portfolio. Please try again.', 'bot');
        }
    }
    
    viewPortfolio() {
        // Navigate to portfolio page
        window.location.href = '/mobile/portfolio/';
    }
    
    scrollToBottom() {
        const chatWindow = document.getElementById('chat-window-mobile');
        if (chatWindow) {
            // Multiple attempts to ensure scrolling works
            setTimeout(() => {
                chatWindow.scrollTo({
                    top: chatWindow.scrollHeight,
                    behavior: 'smooth'
                });
            }, 100);
            
            setTimeout(() => {
                chatWindow.scrollTo({
                    top: chatWindow.scrollHeight,
                    behavior: 'smooth'
                });
            }, 300);
            
            setTimeout(() => {
                chatWindow.scrollTo({
                    top: chatWindow.scrollHeight,
                    behavior: 'smooth'
                });
            }, 500);
        }
    }
    
    // Add pull-to-refresh functionality
    setupPullToRefresh() {
        let startY = 0;
        let currentY = 0;
        let isRefreshing = false;
        
        document.addEventListener('touchstart', (e) => {
            if (window.scrollY === 0) {
                startY = e.touches[0].clientY;
            }
        });
        
        document.addEventListener('touchmove', (e) => {
            if (window.scrollY === 0 && !isRefreshing) {
                currentY = e.touches[0].clientY;
                const pullDistance = currentY - startY;
                
                if (pullDistance > 0) {
                    // Show pull-to-refresh indicator
                    this.showPullToRefreshIndicator(pullDistance);
                }
            }
        });
        
        document.addEventListener('touchend', () => {
            if (window.scrollY === 0 && !isRefreshing) {
                const pullDistance = currentY - startY;
                
                if (pullDistance > 100) {
                    this.triggerRefresh();
                } else {
                    this.hidePullToRefreshIndicator();
                }
            }
        });
    }
    
    showPullToRefreshIndicator(distance) {
        // Create or update pull-to-refresh indicator
        let indicator = document.getElementById('pull-to-refresh-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'pull-to-refresh-indicator';
            indicator.className = 'fixed top-0 left-0 right-0 bg-blue-500 text-white text-center py-2 z-50';
            indicator.innerHTML = 'Pull to refresh';
            document.body.appendChild(indicator);
        }
        
        const opacity = Math.min(distance / 100, 1);
        indicator.style.opacity = opacity;
        indicator.style.transform = `translateY(${Math.min(distance - 50, 50)}px)`;
    }
    
    hidePullToRefreshIndicator() {
        const indicator = document.getElementById('pull-to-refresh-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    async triggerRefresh() {
        const indicator = document.getElementById('pull-to-refresh-indicator');
        if (indicator) {
            indicator.innerHTML = 'Refreshing...';
            indicator.style.transform = 'translateY(0)';
        }
        
        try {
            await this.loadMarketData();
            this.showNotification('Data refreshed', 'success');
        } catch (error) {
            this.showNotification('Refresh failed', 'error');
        } finally {
            this.hidePullToRefreshIndicator();
        }
    }
}

// Initialize Mobile SAHA when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mobileSAHA = new MobileSAHA();
    
    // Register service worker for PWA functionality
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js')
            .then((registration) => {
                console.log('Service Worker registered successfully:', registration);
            })
            .catch((error) => {
                console.log('Service Worker registration failed:', error);
            });
    }
});

// Global function for quick action buttons
function handleQuickAction(action) {
    if (window.mobileSAHA) {
        window.mobileSAHA.handleQuickAction(action);
    }
}

// Export for global access
window.MobileSAHA = MobileSAHA;
