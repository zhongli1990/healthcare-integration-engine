import React, { useState } from 'react';
import {
  Badge,
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  Box,
  Button,
  Paper,
  useTheme,
  alpha,
  Tooltip,
} from '@mui/material';
import {
  Notifications as NotificationsIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  NotificationsNone as NotificationsNoneIcon,
  ClearAll as ClearAllIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useNotifications, Notification, NotificationType } from '../../contexts/NotificationContext';
import { formatDistanceToNow } from 'date-fns';

const NotificationIcon: React.FC<{ type: NotificationType }> = ({ type }) => {
  const theme = useTheme();
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

const NotificationItem: React.FC<{ notification: Notification }> = ({ notification }) => {
  const { markAsRead, removeNotification } = useNotifications();
  const theme = useTheme();
  
  const handleClick = () => {
    if (notification.action) {
      notification.action.onClick();
    }
    markAsRead(notification.id);
  };

  return (
    <MenuItem
      onClick={handleClick}
      sx={{
        py: 1.5,
        px: 2,
        borderLeft: `3px solid ${theme.palette[notification.type].main}`,
        backgroundColor: notification.read 
          ? 'transparent' 
          : alpha(theme.palette.primary.main, 0.05),
        '&:hover': {
          backgroundColor: alpha(theme.palette.primary.main, 0.1),
        },
      }}
    >
      <ListItemIcon sx={{ minWidth: 36 }}>
        <NotificationIcon type={notification.type} />
      </ListItemIcon>
      <ListItemText
        primary={
          <Typography variant="body2" fontWeight={notification.read ? 'normal' : 'medium'}>
            {notification.title}
          </Typography>
        }
        secondary={
          <>
            <Typography variant="caption" color="text.secondary" display="block">
              {notification.message}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
            </Typography>
          </>
        }
        secondaryTypographyProps={{ component: 'div' }}
      />
      <IconButton
        size="small"
        onClick={(e) => {
          e.stopPropagation();
          removeNotification(notification.id);
        }}
        sx={{
          visibility: 'hidden',
          'div:hover > &': {
            visibility: 'visible',
          },
        }}
      >
        <ClearAllIcon fontSize="small" />
      </IconButton>
    </MenuItem>
  );
};

const NotificationMenu: React.FC = () => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const {
    notifications,
    unreadCount,
    markAllAsRead,
    clearAllNotifications,
  } = useNotifications();
  const theme = useTheme();
  const navigate = useNavigate();

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleViewAll = () => {
    handleMenuClose();
    navigate('/notifications');
  };

  const handleMarkAllAsRead = () => {
    markAllAsRead();
  };

  const handleClearAll = () => {
    clearAllNotifications();
  };

  return (
    <>
      <Tooltip title="Notifications">
        <IconButton
          onClick={handleMenuOpen}
          color="inherit"
          size="large"
          sx={{
            position: 'relative',
            '&:hover': {
              backgroundColor: alpha(theme.palette.primary.contrastText, 0.1),
            },
          }}
        >
          <Badge
            badgeContent={unreadCount}
            color="error"
            invisible={unreadCount === 0}
            overlap="circular"
            variant="dot"
          >
            <NotificationsIcon />
          </Badge>
        </IconButton>
      </Tooltip>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        onClick={(e) => e.stopPropagation()}
        PaperProps={{
          sx: {
            width: 380,
            maxWidth: '100%',
            maxHeight: '80vh',
            overflow: 'hidden',
            mt: 1,
          },
        }}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
      >
        <Box sx={{ px: 2, pt: 1, pb: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="subtitle1" fontWeight="medium">
            Notifications
          </Typography>
          <Box>
            <Button
              size="small"
              onClick={handleMarkAllAsRead}
              disabled={notifications.every(n => n.read) || notifications.length === 0}
              sx={{ minWidth: 'auto', mr: 1 }}
            >
              Mark all as read
            </Button>
            <Button
              size="small"
              onClick={handleClearAll}
              disabled={notifications.length === 0}
              color="error"
              sx={{ minWidth: 'auto' }}
            >
              Clear all
            </Button>
          </Box>
        </Box>
        
        <Divider />
        
        <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
          {notifications.length === 0 ? (
            <Box sx={{ p: 3, textAlign: 'center' }}>
              <NotificationsNoneIcon sx={{ fontSize: 40, color: 'text.disabled', mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                No notifications yet
              </Typography>
            </Box>
          ) : (
            notifications.map((notification) => (
              <div key={notification.id}>
                <NotificationItem notification={notification} />
                <Divider />
              </div>
            ))
          )}
        </Box>
        
        {notifications.length > 0 && (
          <Box sx={{ p: 1, display: 'flex', justifyContent: 'center' }}>
            <Button size="small" onClick={handleViewAll}>
              View all notifications
            </Button>
          </Box>
        )}
      </Menu>
    </>
  );
};

export default NotificationMenu;
