import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  Box,
  Typography,
  Avatar,
  Paper,
  Grid,
  Divider,
  Button,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
} from '@mui/material';
import {
  Email as EmailIcon,
  Badge as BadgeIcon,
  Work as WorkIcon,
  Business as BusinessIcon,
  Event as EventIcon,
  Edit as EditIcon,
  Lock as LockIcon,
  Notifications as NotificationsIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

const Profile: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  if (!user) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <Typography>Please log in to view your profile</Typography>
      </Box>
    );
  }


  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        My Profile
      </Typography>
      
      <Paper sx={{ p: 4, mb: 4 }}>
        <Grid container spacing={4}>
          <Grid item xs={12} md={4} sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Avatar
              src={user.avatar}
              sx={{
                width: 150,
                height: 150,
                mb: 2,
                fontSize: '3rem',
                border: '4px solid',
                borderColor: 'primary.main',
              }}
            >
              {user.name.split(' ').map(n => n[0]).join('').toUpperCase()}
            </Avatar>
            <Typography variant="h5" component="div" align="center" gutterBottom>
              {user.name}
            </Typography>
            <Typography variant="subtitle1" color="text.secondary" align="center" gutterBottom>
              {user.title || 'Staff Member'}
            </Typography>
            <Typography variant="body2" color="text.secondary" align="center" paragraph>
              {user.department || 'Department'}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={() => navigate('/settings')}
              sx={{ mt: 1 }}
            >
              Edit Profile
            </Button>
          </Grid>
          
          <Grid item xs={12} md={8}>
            <List disablePadding>
              <ListItem>
                <ListItemIcon>
                  <BadgeIcon color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary="Full Name"
                  secondary={user.name}
                />
              </ListItem>
              <Divider component="li" />
              
              <ListItem>
                <ListItemIcon>
                  <EmailIcon color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary="Email Address"
                  secondary={user.email}
                />
              </ListItem>
              <Divider component="li" />
              
              <ListItem>
                <ListItemIcon>
                  <WorkIcon color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary="Job Title"
                  secondary={user.title || 'Not specified'}
                />
                <ListItemSecondaryAction>
                  <IconButton edge="end" onClick={() => navigate('/settings')}>
                    <EditIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
              <Divider component="li" />
              
              <ListItem>
                <ListItemIcon>
                  <BusinessIcon color="primary" />
                </ListItemIcon>
                <ListItemText
                  primary="Department"
                  secondary={user.department || 'Not specified'}
                />
                <ListItemSecondaryAction>
                  <IconButton edge="end" onClick={() => navigate('/settings')}>
                    <EditIcon />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
              <Divider component="li" />
              
              {user.lastLogin && (
                <>
                  <ListItem>
                    <ListItemIcon>
                      <EventIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Last Login"
                      secondary={new Date(user.lastLogin).toLocaleString()}
                    />
                  </ListItem>
                  <Divider component="li" />
                </>
              )}
            </List>
          </Grid>
        </Grid>
      </Paper>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box display="flex" alignItems="center" mb={2}>
              <LockIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6" component="h2">
                Security
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" paragraph>
              Manage your password and security settings
            </Typography>
            <Button
              variant="outlined"
              onClick={() => navigate('/settings/security')}
              sx={{ mt: 1 }}
            >
              Update Password
            </Button>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Box display="flex" alignItems="center" mb={2}>
              <NotificationsIcon color="primary" sx={{ mr: 1 }} />
              <Typography variant="h6" component="h2">
                Notifications
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" paragraph>
              Manage your notification preferences
            </Typography>
            <Button
              variant="outlined"
              onClick={() => navigate('/settings/notifications')}
              sx={{ mt: 1 }}
            >
              Notification Settings
            </Button>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Profile;
