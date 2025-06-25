# Notification System Documentation

## Overview
The notification system provides a way to display timely information to users about events and actions within the Healthcare Integration Engine. It includes a notification bell in the header, a dropdown menu for recent notifications, and a dedicated notifications page.

## Features

### Core Features
- Real-time notification display
- Different notification types (info, success, warning, error)
- Mark notifications as read/unread
- Clear individual or all notifications
- Persistent storage using localStorage
- Responsive design
- Dark mode support

### Notification Types
- `info`: General information (blue)
- `success`: Success messages (green)
- `warning`: Warnings (orange)
- `error`: Error messages (red)

## Implementation Details

### File Structure
```
frontend/src/
  ├── components/
  │   └── notifications/
  │       └── NotificationMenu.tsx  # Notification dropdown component
  ├── contexts/
  │   └── NotificationContext.tsx  # Notification context and hooks
  ├── pages/
  │   └── Notifications.tsx  # Full notifications page
  └── services/
      └── notificationService.ts  # Helper functions for notifications
```

### Key Components

#### 1. Notification Context (`NotificationContext.tsx`)
- Manages notification state
- Provides methods for adding, removing, and updating notifications
- Handles persistence to localStorage
- Exports `useNotifications` and `useNotify` hooks

#### 2. Notification Menu (`NotificationMenu.tsx`)
- Displays notification bell with unread count
- Shows dropdown with recent notifications
- Handles mark as read/clear actions

#### 3. Notifications Page (`Notifications.tsx`)
- Displays all notifications
- Filter by notification type
- Mark all as read/clear all functionality

## Usage

### Adding Notifications

#### Basic Usage
```typescript
import { useNotify } from '../contexts/NotificationContext';

function MyComponent() {
  const { notify } = useNotify();
  
  const handleClick = () => {
    notify('Title', 'This is a notification message', 'info');
  };
  
  return <button onClick={handleClick}>Show Notification</button>;
}
```

#### With Action Button
```typescript
notify('Action Required', 'Please review this item', 'warning', {
  label: 'Review',
  onClick: () => navigate('/items/123')
});
```

#### Using Convenience Methods
```typescript
const { success, error, warning, info } = useNotify();

// Success notification
success('Operation Successful', 'The item was created successfully');

// Error notification
error('Error', 'Failed to save changes');

// Warning notification
warning('Warning', 'This action cannot be undone');

// Info notification
info('Info', 'Your profile has been updated');
```

## API Reference

### useNotify()
Returns an object with notification methods:

| Method | Parameters | Description |
|--------|------------|-------------|
| `notify` | `(title: string, message: string, type: NotificationType, action?: { label: string, onClick: () => void })` | Show a notification with optional action |
| `success` | `(title: string, message: string, action?)` | Show success notification |
| `error` | `(title: string, message: string, action?)` | Show error notification |
| `warning` | `(title: string, message: string, action?)` | Show warning notification |
| `info` | `(title: string, message: string, action?)` | Show info notification |

### Notification Object
```typescript
interface Notification {
  id: string;           // Unique identifier
  title: string;         // Notification title
  message: string;       // Notification message
  type: NotificationType; // 'info' | 'success' | 'warning' | 'error'
  timestamp: Date;       // When the notification was created
  read: boolean;         // Whether the notification has been read
  action?: {             // Optional action
    label: string;       // Action button text
    onClick: () => void; // Action handler
  };
}
```

## Testing

### Manual Testing
1. Open the application
2. Click the notification bell in the header
3. Verify sample notifications are displayed
4. Test mark as read functionality
5. Test clear notification
6. Test "Mark all as read" and "Clear all" buttons
7. Navigate to /notifications and test filtering

### Automated Testing
Run the test suite:
```bash
npm test
```

## Best Practices

### When to Use Notifications
- **Do** use notifications for:
  - Important system events (e.g., "Backup completed")
  - User actions that require attention (e.g., "Document saved")
  - Time-sensitive information
  - Errors that need user action

- **Don't** use notifications for:
  - Confirmation of every user action
  - Information that's already visible on screen
  - Non-critical system messages

### Notification Guidelines
1. **Be Clear and Concise**
   - Keep titles under 50 characters
   - Keep messages under 120 characters
   - Use action buttons for complex flows

2. **Use Appropriate Types**
   - `success`: For completed actions
   - `error`: For problems that need attention
   - `warning`: For potential issues
   - `info`: For general information

3. **Performance**
   - Limit the number of notifications to 50
   - Old notifications are automatically archived
   - Use action buttons instead of multiple notifications for related events
1. Use appropriate notification types
2. Keep messages clear and concise
3. Include actions when additional steps are needed
4. Don't overuse notifications for non-critical information
5. Test notifications on different screen sizes

## Troubleshooting

### Notifications not persisting
- Check localStorage in browser dev tools
- Verify NotificationProvider is properly wrapped around the app

### Notifications not showing up
- Check for console errors
- Verify the notification is being added to the state
- Ensure the notification component is mounted

### Styling issues
- Check for CSS conflicts
- Verify theme variables are properly set up

## Version History

### v0.1.3 (2025-06-22)
#### Features
- Initial implementation of notification system
- Added notification context with full CRUD operations
- Created responsive notification menu with unread indicators
- Built dedicated notifications page with filtering
- Added local storage persistence
- Integrated with existing theme system
- Added comprehensive documentation

#### Components Added
- `NotificationContext`: Manages notification state and persistence
- `NotificationMenu`: Dropdown menu for recent notifications
- `Notifications` page: Full notifications interface
- `notificationService`: Helper for demo and testing

#### Usage Examples
```typescript
// Basic usage
const { notify } = useNotify();
notify('Title', 'Message', 'info');

// With action
notify('Action Required', 'Please review', 'warning', {
  label: 'Review',
  onClick: () => navigate('/items/123')
});

// Convenience methods
const { success, error } = useNotify();
success('Success', 'Operation completed');
error('Error', 'Something went wrong');
```

#### Implementation Notes
- Notifications persist across page refreshes using localStorage
- Unread count is automatically tracked and displayed
- Supports dark/light theme
- Fully responsive design
- Accessible with proper ARIA labels

### v0.1.2 (2025-06-21)
- Initial project setup
- Basic layout and routing
- Authentication system
- Theme support
- Profile management
