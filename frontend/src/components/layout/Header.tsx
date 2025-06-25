import React from 'react';
import { styled, AppBar, Toolbar, IconButton, Typography, Box, Badge, Tooltip } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import SettingsIcon from '@mui/icons-material/Settings';
import { useThemeContext } from '../../contexts/ThemeContext';
import { useNavigate } from 'react-router-dom';
import ProfileMenu from './ProfileMenu';
import NotificationMenu from '../notifications/NotificationMenu';

interface HeaderProps {
  onMenuToggle: () => void;
}

const StyledAppBar = styled(AppBar)(({ theme }) => ({
  zIndex: theme.zIndex.drawer + 1,
  transition: theme.transitions.create(['width', 'margin'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.primary.contrastText,
}));

const Header: React.FC<HeaderProps> = ({ onMenuToggle }) => {
  const { mode, toggleColorMode } = useThemeContext();
  const navigate = useNavigate();
  
  const handleSettingsClick = () => {
    navigate('/settings');
  };
  
  return (
    <StyledAppBar position="fixed">
      <Toolbar>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          onClick={onMenuToggle}
          edge="start"
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>
        
        <Typography 
          variant="h6" 
          noWrap 
          component="div" 
          sx={{ 
            flexGrow: 1,
            cursor: 'pointer',
            '&:hover': {
              opacity: 0.8
            }
          }}
          onClick={() => navigate('/')}
        >
          Healthcare Integration Engine
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <IconButton 
            color="inherit" 
            onClick={toggleColorMode}
            aria-label={mode === 'dark' ? 'switch to light mode' : 'switch to dark mode'}
            sx={{ ml: 1 }}
          >
            {mode === 'dark' ? (
              <Box component="span" sx={{ display: 'flex' }}>☀️</Box>
            ) : (
              <Box component="span" sx={{ display: 'flex' }}>🌙</Box>
            )}
          </IconButton>
          
          <NotificationMenu />
          
          <Tooltip title="Settings">
            <IconButton 
              color="inherit" 
              size="large"
              onClick={handleSettingsClick}
              sx={{ ml: 1 }}
              aria-label="settings"
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>
          
          <ProfileMenu />
        </Box>
      </Toolbar>
    </StyledAppBar>
  );
};

export default Header;