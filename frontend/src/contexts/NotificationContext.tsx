import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: NotificationType;
  timestamp: Date;
  read: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  removeNotification: (id: string) => void;
  clearAllNotifications: () => void;
}

const NotificationContext = createContext<NotificationContextType | null>(null);

// Load notifications from localStorage
const loadNotifications = (): Notification[] => {
  if (typeof window === 'undefined') return [];
  
  try {
    const saved = localStorage.getItem('notifications');
    if (!saved) return [];
    
    const parsed = JSON.parse(saved);
    return parsed.map((n: any) => ({
      ...n,
      timestamp: new Date(n.timestamp)
    }));
  } catch (error) {
    console.error('Failed to load notifications:', error);
    return [];
  }
};

// Save notifications to localStorage
const saveNotifications = (notifications: Notification[]) => {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.setItem('notifications', JSON.stringify(notifications));
  } catch (error) {
    console.error('Failed to save notifications:', error);
  }
};

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isInitialized, setIsInitialized] = useState(false);

  // Load notifications on mount
  useEffect(() => {
    if (!isInitialized) {
      setNotifications(loadNotifications());
      setIsInitialized(true);
    }
  }, [isInitialized]);

  // Save notifications when they change
  useEffect(() => {
    if (isInitialized) {
      saveNotifications(notifications);
    }
  }, [notifications, isInitialized]);

  const addNotification = useCallback((notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      read: false,
    };
    
    setNotifications(prev => [newNotification, ...prev]);
    
    // Play notification sound
    if (typeof window !== 'undefined' && window.Notification && Notification.permission === 'granted') {
      new Notification(notification.title, {
        body: notification.message,
        icon: '/favicon.ico',
      });
    }
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev =>
      prev.map(n => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  const removeNotification = useCallback((id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // Calculate unread count
  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        unreadCount,
        addNotification,
        markAsRead,
        markAllAsRead,
        removeNotification,
        clearAllNotifications,
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = (): NotificationContextType => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};

// Helper hook for adding notifications
// Usage: const { notify } = useNotify();
// notify('Title', 'Message', 'success');
export const useNotify = () => {
  const { addNotification } = useNotifications();
  
  return {
    notify: (
      title: string, 
      message: string, 
      type: NotificationType = 'info',
      action?: { label: string; onClick: () => void }
    ) => {
      addNotification({
        title,
        message,
        type,
        ...(action && { action })
      });
    },
    success: (title: string, message: string, action?: { label: string; onClick: () => void }) => {
      addNotification({ title, message, type: 'success', ...(action && { action }) });
    },
    error: (title: string, message: string, action?: { label: string; onClick: () => void }) => {
      addNotification({ title, message, type: 'error', ...(action && { action }) });
    },
    warning: (title: string, message: string, action?: { label: string; onClick: () => void }) => {
      addNotification({ title, message, type: 'warning', ...(action && { action }) });
    },
    info: (title: string, message: string, action?: { label: string; onClick: () => void }) => {
      addNotification({ title, message, type: 'info', ...(action && { action }) });
    },
  };
};
