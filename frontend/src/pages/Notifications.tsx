import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  List,
  Divider,
  Button,
  ToggleButtonGroup,
  ToggleButton,
  IconButton,
  Tooltip,
  useTheme,
  alpha,
  Chip,
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  NotificationsNone as NotificationsNoneIcon,
  ClearAll as ClearAllIcon,
  FilterList as FilterListIcon,
} from '@mui/icons-material';
import { useNotifications, Notification, NotificationType } from '../contexts/NotificationContext';
import { format } from 'date-fns';

const NotificationIcon: React.FC<{ type: NotificationType }> = ({ type }) => {
  const iconStyle = { fontSize: 20 };
  
  switch (type) {
    case 'success':
      return <CheckCircleIcon color="success" style={iconStyle} />;
    case 'error':
      return <ErrorIcon color="error" style={iconStyle} />;
    case 'warning':
      return <WarningIcon color="warning" style={iconStyle} />;
    default:
      return <InfoIcon color="info" style={iconStyle} />;
  }
};

const NotificationsPage: React.FC = () => {
  const { notifications, markAsRead, markAllAsRead, removeNotification, clearAllNotifications } = useNotifications();
  const [filter, setFilter] = useState<NotificationType | 'all'>('all');
  const theme = useTheme();

  const filteredNotifications = notifications.filter(
    notification => filter === 'all' || notification.type === filter
  );

  const unreadCount = notifications.filter(n => !n.read).length;
  const filteredUnreadCount = filteredNotifications.filter(n => !n.read).length;

  const handleFilterChange = (_: React.MouseEvent<HTMLElement>, newFilter: NotificationType | 'all') => {
    if (newFilter !== null) {
      setFilter(newFilter);
    }
  };

  const handleMarkAllAsRead = () => {
    markAllAsRead();
  };

  const handleClearAll = () => {
    clearAllNotifications();
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
    if (notification.action) {
      notification.action.onClick();
    }
  };

  const getTypeLabel = (type: NotificationType) => {
    switch (type) {
      case 'success': return 'Success';
      case 'error': return 'Error';
      case 'warning': return 'Warning';
      default: return 'Info';
    }
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Notifications
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {unreadCount} unread {unreadCount === 1 ? 'notification' : 'notifications'}
          </Typography>
        </Box>
        <Box>
          <Tooltip title="Mark all as read">
            <span>
              <Button
                variant="outlined"
                startIcon={<CheckCircleIcon />}
                onClick={handleMarkAllAsRead}
                disabled={unreadCount === 0}
                sx={{ mr: 1 }}
              >
                Mark all as read
              </Button>
            </span>
          </Tooltip>
          <Tooltip title="Clear all notifications">
            <span>
              <Button
                variant="outlined"
                color="error"
                startIcon={<ClearAllIcon />}
                onClick={handleClearAll}
                disabled={notifications.length === 0}
              >
                Clear all
              </Button>
            </span>
          </Tooltip>
        </Box>
      </Box>

      <Paper sx={{ mb: 3, p: 2 }}>
        <Box display="flex" alignItems="center" mb={2}>
          <FilterListIcon color="action" sx={{ mr: 1 }} />
          <Typography variant="subtitle2" color="text.secondary" sx={{ mr: 2 }}>
            Filter by:
          </Typography>
          <ToggleButtonGroup
            value={filter}
            exclusive
            onChange={handleFilterChange}
            aria-label="notification filter"
            size="small"
          >
            <ToggleButton value="all" aria-label="all">
              All
            </ToggleButton>
            <ToggleButton value="info" aria-label="info">
              <InfoIcon color="info" fontSize="small" sx={{ mr: 0.5 }} />
              Info
            </ToggleButton>
            <ToggleButton value="success" aria-label="success">
              <CheckCircleIcon color="success" fontSize="small" sx={{ mr: 0.5 }} />
              Success
            </ToggleButton>
            <ToggleButton value="warning" aria-label="warning">
              <WarningIcon color="warning" fontSize="small" sx={{ mr: 0.5 }} />
              Warning
            </ToggleButton>
            <ToggleButton value="error" aria-label="error">
              <ErrorIcon color="error" fontSize="small" sx={{ mr: 0.5 }} />
              Error
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Paper>

      <Paper>
        {filteredNotifications.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <NotificationsNoneIcon sx={{ fontSize: 60, color: 'text.disabled', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              No notifications found
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 400, mx: 'auto' }}>
              {filter === 'all'
                ? 'You don\'t have any notifications yet.'
                : `You don't have any ${filter} notifications.`}
            </Typography>
          </Box>
        ) : (
          <List disablePadding>
            {filteredNotifications.map((notification, index) => (
              <React.Fragment key={notification.id}>
                <Box
                  component="li"
                  onClick={() => handleNotificationClick(notification)}
                  sx={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    p: 2,
                    cursor: 'pointer',
                    transition: 'background-color 0.2s',
                    '&:hover': {
                      backgroundColor: theme.palette.action.hover,
                    },
                    backgroundColor: notification.read
                      ? 'transparent'
                      : alpha(theme.palette.primary.main, 0.04),
                    borderLeft: `4px solid ${theme.palette[notification.type].main}`,
                  }}
                >
                  <Box sx={{ mr: 2, mt: 0.5 }}>
                    <NotificationIcon type={notification.type} />
                  </Box>
                  <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="flex-start">
                      <Typography
                        variant="subtitle2"
                        sx={{
                          fontWeight: notification.read ? 'normal' : 'medium',
                          mb: 0.5,
                        }}
                      >
                        {notification.title}
                      </Typography>
                      <Chip
                        label={getTypeLabel(notification.type)}
                        size="small"
                        sx={{
                          ml: 1,
                          textTransform: 'capitalize',
                          bgcolor: `${theme.palette[notification.type].light}22`,
                          color: `${theme.palette[notification.type].dark}`,
                          fontSize: '0.65rem',
                          height: 20,
                        }}
                      />
                    </Box>
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        mb: 1,
                        whiteSpace: 'pre-line',
                        wordBreak: 'break-word',
                      }}
                    >
                      {notification.message}
                    </Typography>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="caption" color="text.disabled">
                        {format(new Date(notification.timestamp), 'MMM d, yyyy h:mm a')}
                      </Typography>
                      {!notification.read && (
                        <Chip
                          label="New"
                          size="small"
                          color="primary"
                          sx={{ height: 20, fontSize: '0.65rem' }}
                        />
                      )}
                    </Box>
                  </Box>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeNotification(notification.id);
                    }}
                    sx={{
                      ml: 1,
                      visibility: 'hidden',
                      'li:hover &': {
                        visibility: 'visible',
                      },
                    }}
                  >
                    <ClearAllIcon fontSize="small" />
                  </IconButton>
                </Box>
                {index < filteredNotifications.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </Paper>
    </Box>
  );
};

export default NotificationsPage;
