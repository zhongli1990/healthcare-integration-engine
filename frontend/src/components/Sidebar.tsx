import { Drawer, List, ListItemButton, ListItemIcon, ListItemText, styled, Toolbar } from '@mui/material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import DashboardIcon from '@mui/icons-material/Dashboard';
import StorageIcon from '@mui/icons-material/Storage';
import IntegrationInstructionsIcon from '@mui/icons-material/IntegrationInstructions';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import { ReactNode } from 'react';

const drawerWidth = 240;

const StyledDrawer = styled(Drawer)({
  width: drawerWidth,
  flexShrink: 0,
  '& .MuiDrawer-paper': {
    width: drawerWidth,
    boxSizing: 'border-box',
    position: 'fixed',
    top: 0,
    height: '100%',
    borderRight: '1px solid',
    borderColor: 'divider',
    pt: '64px', // Account for TopBar height
  },
}) as typeof Drawer;

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Protocols', icon: <StorageIcon />, path: '/protocols' },
  { text: 'Integration', icon: <IntegrationInstructionsIcon />, path: '/integration' },
  { text: 'Monitoring', icon: <MonitorHeartIcon />, path: '/monitoring' },
];

interface MenuItem {
  text: string;
  icon: ReactNode;
  path: string;
}

interface SidebarProps {
  mobileOpen: boolean;
  handleDrawerToggle: () => void;
  drawerWidth: number;
}

const Sidebar = ({ mobileOpen, handleDrawerToggle, drawerWidth }: SidebarProps) => {
  const location = useLocation();

  const drawer = (
    <div>
      <Toolbar />
      <List>
        {menuItems.map((item: MenuItem) => (
          <ListItemButton 
            key={item.text} 
            component={RouterLink} 
            to={item.path}
            selected={location.pathname === item.path}
          >
            <ListItemIcon sx={{ 
              color: location.pathname === item.path ? 'primary.main' : 'inherit',
              minWidth: '40px'
            }}>
              {item.icon}
            </ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItemButton>
        ))}
      </List>
    </div>
  );

  return (
    <>
      <StyledDrawer
        variant="temporary"
        open={mobileOpen}
        onClose={handleDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          display: { xs: 'block', sm: 'none' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
        }}
      >
        {drawer}
      </StyledDrawer>
      <StyledDrawer
        variant="permanent"
        sx={{
          display: { xs: 'none', sm: 'block' },
          '& .MuiDrawer-paper': { 
            boxSizing: 'border-box', 
            width: drawerWidth,
            borderRight: 0,
            boxShadow: '1px 0 4px rgba(0, 0, 0, 0.1)'
          },
        }}
        open
      >
        {drawer}
      </StyledDrawer>
    </>
  );
};

export default Sidebar;
