# SAHA-AI Mobile App Documentation

## Overview

SAHA-AI Mobile is a Progressive Web App (PWA) designed to provide AI-powered financial assistance on mobile devices. The app offers a native-like experience with offline capabilities, push notifications, and seamless integration with the desktop version.

## Features

### Core Features
- **AI Chat Interface**: Interactive chat with SAHA-AI for financial queries
- **Portfolio Management**: View and manage your investment portfolio
- **Market Data**: Real-time market updates and analysis
- **Stock Analysis**: Detailed analysis of individual stocks
- **Mutual Fund Research**: Comprehensive mutual fund information
- **User Profile**: Account management and settings

### Mobile-Specific Features
- **Progressive Web App**: Installable on mobile devices
- **Offline Support**: Basic functionality works without internet
- **Pull-to-Refresh**: Refresh data by pulling down on the screen
- **Touch Optimizations**: Optimized for touch interactions
- **Dark/Light Theme**: Automatic theme switching
- **Connection Status**: Real-time connection monitoring
- **Swipe Gestures**: Navigate between sections with swipes

## Installation

### As a PWA
1. Open the mobile app in your browser
2. Look for the "Add to Home Screen" prompt
3. Tap "Add" to install the app
4. The app will appear on your home screen like a native app

### Browser Support
- **Chrome**: Full PWA support
- **Safari**: Basic PWA support (iOS 11.3+)
- **Firefox**: Full PWA support
- **Edge**: Full PWA support

## Navigation

### Bottom Navigation
The app uses a bottom navigation bar with four main sections:

1. **Chat** (`/mobile/`): Main AI chat interface
2. **Portfolio** (`/mobile/portfolio/`): Portfolio management
3. **About** (`/mobile/about/`): App information and team
4. **Profile** (`/mobile/profile/`): User account settings

### Gestures
- **Swipe Left/Right**: Navigate between sections
- **Pull Down**: Refresh data
- **Tap**: Select items and interact with UI
- **Long Press**: Access additional options

## Usage Guide

### Getting Started
1. **Login**: Use your existing SAHA-AI account credentials
2. **First Time**: Accept the beta testing agreement
3. **Theme**: Toggle between light and dark themes using the theme button
4. **Navigation**: Use the bottom navigation to explore different sections

### Chat Interface
- **Ask Questions**: Type your financial questions in the input field
- **Quick Suggestions**: Tap on suggestion chips for common queries
- **Send Messages**: Tap the send button or press Enter
- **View Responses**: Scroll through the chat history

### Portfolio Management
- **View Holdings**: See all your current investments
- **Add Holdings**: Use the "+ Add" button to add new investments
- **Search**: Search for stocks or mutual funds to add
- **Remove Holdings**: Swipe left on holdings to reveal delete option
- **Refresh**: Pull down or tap the refresh button to update data

### Market Data
- **Live Updates**: Market cards show real-time data
- **Swipe Cards**: Swipe horizontally to see different market indices
- **Refresh**: Pull down to refresh market data

## Technical Details

### Architecture
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Styling**: Tailwind CSS with custom mobile optimizations
- **PWA**: Service Worker for offline functionality
- **Backend**: Django REST API integration

### Performance Optimizations
- **Lazy Loading**: Images and content load as needed
- **Caching**: Service worker caches static assets
- **Compression**: Optimized assets for faster loading
- **Touch Targets**: Minimum 44px touch targets for accessibility

### Offline Capabilities
- **Cached Pages**: Core pages work offline
- **Offline Indicators**: Visual indicators when offline
- **Background Sync**: Actions sync when connection restored
- **Fallback Content**: Graceful degradation when offline

## API Integration

### Endpoints Used
- `/api/api/chat/`: Chat functionality
- `/api/api/portfolio/`: Portfolio data
- `/api/api/market-snapshot/`: Market data
- `/api/api/stock-search/`: Stock search
- `/api/api/mutual-fund-search/`: Mutual fund search

### Authentication
- **CSRF Protection**: All API calls include CSRF tokens
- **Session Management**: Maintains user sessions
- **Error Handling**: Graceful error handling for API failures

## Customization

### Themes
- **Light Theme**: Default light appearance
- **Dark Theme**: Dark mode for low-light usage
- **Auto Theme**: Follows system theme preference
- **Manual Toggle**: Override system preference

### Settings
- **Notifications**: Enable/disable push notifications
- **Data Privacy**: Manage data sharing preferences
- **Account Settings**: Update profile information

## Troubleshooting

### Common Issues

#### App Won't Install
- **Solution**: Ensure you're using a supported browser
- **Alternative**: Bookmark the app for quick access

#### Offline Mode Not Working
- **Solution**: Clear browser cache and reload
- **Check**: Service worker registration in browser dev tools

#### Chat Not Responding
- **Solution**: Check internet connection
- **Alternative**: Refresh the page and try again

#### Portfolio Data Not Loading
- **Solution**: Ensure you're logged in
- **Check**: API endpoint availability

### Performance Issues
- **Slow Loading**: Clear browser cache
- **High Data Usage**: Disable auto-refresh
- **Battery Drain**: Close unused tabs

## Development

### File Structure
```
advisor/
├── static/
│   ├── css/mobile-saha.css
│   ├── js/mobile-saha.js
│   ├── manifest.json
│   └── sw.js
├── templates/advisor/
│   ├── mobile_index.html
│   ├── mobile_portfolio.html
│   ├── mobile_profile.html
│   └── mobile_about.html
└── views.py
```

### Key Components
- **MobileSAHA Class**: Main JavaScript controller
- **Service Worker**: Offline functionality
- **PWA Manifest**: App installation metadata
- **Mobile CSS**: Responsive styling

### Adding New Features
1. **Frontend**: Update HTML templates and JavaScript
2. **Styling**: Add CSS for mobile-specific styles
3. **Backend**: Create/update API endpoints
4. **Testing**: Test on multiple devices and browsers

## Support

### Getting Help
- **Documentation**: Refer to this guide
- **Issues**: Report bugs through the app
- **Feedback**: Use the feedback form in the app

### Contact Information
- **Email**: contact@saha-ai.com
- **Support**: 24/7 support available
- **Updates**: Regular updates and improvements

## Version History

### v1.0.0 (Current)
- Initial mobile app release
- PWA functionality
- Core features implementation
- Offline support
- Dark/light themes

### Future Updates
- Push notifications
- Advanced analytics
- Social features
- Enhanced offline capabilities

---

*This documentation is regularly updated. Last updated: January 2025*
