import React from 'react';
import { useNotifications } from '../contexts/NotificationContext';
import { useNotify } from '../contexts/NotificationContext';

export const useNotificationDemo = () => {
  const { notify } = useNotify();

  const addSampleNotifications = () => {
    // Clear existing notifications first
    // Add sample notifications
    notify(
      'Welcome to Healthcare Integration Engine',
      'You have successfully logged in to the dashboard.',
      'success',
      {
        label: 'View Dashboard',
        onClick: () => window.location.href = '/',
      }
    );

    notify(
      'System Update Available',
      'A new version of the application is available. Please update to the latest version for new features and security updates.',
      'info',
      {
        label: 'Update Now',
        onClick: () => window.location.href = '/settings',
      }
    );

    notify(
      'Scheduled Maintenance',
      'There will be scheduled maintenance on June 25th from 2:00 AM to 4:00 AM. The system may be temporarily unavailable during this time.',
      'warning'
    );

    notify(
      'New Message from Dr. Smith',
      'Please review the latest patient report when you get a chance.',
      'info',
      {
        label: 'View Message',
        onClick: () => window.location.href = '/messages',
      }
    );
  };

  return { addSampleNotifications };
};

// Add a hook to initialize demo notifications
export const useInitNotifications = () => {
  const { addSampleNotifications } = useNotificationDemo();
  
  React.useEffect(() => {
    // Only add demo notifications in development or when explicitly enabled
    if (process.env.NODE_ENV === 'development' || localStorage.getItem('enableDemoNotifications') === 'true') {
      addSampleNotifications();
    }
  }, []);
};
