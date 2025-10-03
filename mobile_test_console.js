// Mobile Testing Console Commands
// Run these in your browser's developer console (F12)

// Test 1: Check if mobile templates are loading
console.log('Testing Mobile SAHA-AI...');

// Test 2: Simulate mobile viewport
function testMobileView() {
    // Set mobile viewport
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
        viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, user-scalable=no');
    }
    
    // Add mobile class to body
    document.body.classList.add('mobile-test');
    
    // Test touch events
    document.addEventListener('touchstart', (e) => {
        console.log('Touch detected:', e.touches[0].clientX, e.touches[0].clientY);
    });
    
    console.log('Mobile viewport set! Refresh the page to see mobile layout.');
}

// Test 3: Check mobile-specific elements
function checkMobileElements() {
    const mobileElements = [
        'beta-welcome-mobile',
        'chat-window-mobile',
        'user-input-mobile',
        'send-button-mobile',
        'market-cards-mobile'
    ];
    
    mobileElements.forEach(id => {
        const element = document.getElementById(id);
        console.log(`${id}: ${element ? '✅ Found' : '❌ Missing'}`);
    });
}

// Test 4: Simulate mobile gestures
function testSwipeGestures() {
    console.log('Testing swipe gestures...');
    
    // Simulate swipe left
    const swipeEvent = new TouchEvent('touchstart', {
        touches: [new Touch({
            identifier: 1,
            target: document.body,
            clientX: 100,
            clientY: 100
        })]
    });
    
    document.dispatchEvent(swipeEvent);
    console.log('Swipe gesture simulated');
}

// Test 5: Check mobile JavaScript functionality
function testMobileJS() {
    if (window.mobileSAHA) {
        console.log('✅ Mobile SAHA JavaScript loaded');
        console.log('Mobile SAHA instance:', window.mobileSAHA);
    } else {
        console.log('❌ Mobile SAHA JavaScript not loaded');
    }
}

// Test 6: Mobile theme toggle
function testMobileTheme() {
    const themeToggle = document.getElementById('theme-toggle-mobile');
    if (themeToggle) {
        console.log('✅ Mobile theme toggle found');
        themeToggle.click();
        console.log('Theme toggled!');
    } else {
        console.log('❌ Mobile theme toggle not found');
    }
}

// Run all tests
function runAllMobileTests() {
    console.log('🧪 Running Mobile SAHA-AI Tests...');
    console.log('================================');
    
    checkMobileElements();
    testMobileJS();
    testMobileTheme();
    
    console.log('================================');
    console.log('✅ Mobile tests completed!');
}

// Quick mobile view test
function quickMobileTest() {
    // Resize window to mobile size
    window.resizeTo(375, 667);
    
    // Add mobile styles
    const style = document.createElement('style');
    style.textContent = `
        body { max-width: 375px; margin: 0 auto; }
        .mobile-container { padding-bottom: 80px; }
    `;
    document.head.appendChild(style);
    
    console.log('📱 Mobile view activated! Window resized to iPhone dimensions.');
}

// Export functions for easy access
window.mobileTests = {
    testMobileView,
    checkMobileElements,
    testSwipeGestures,
    testMobileJS,
    testMobileTheme,
    runAllMobileTests,
    quickMobileTest
};

console.log('📱 Mobile testing functions loaded!');
console.log('Available commands:');
console.log('- mobileTests.runAllMobileTests()');
console.log('- mobileTests.quickMobileTest()');
console.log('- mobileTests.checkMobileElements()');
console.log('- mobileTests.testMobileJS()');
