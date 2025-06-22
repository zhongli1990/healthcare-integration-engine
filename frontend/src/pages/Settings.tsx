import { Box, Typography, Paper, Tabs, Tab, Divider, TextField, Button, FormControlLabel, Switch } from '@mui/material';
import { useState } from 'react';
import SaveIcon from '@mui/icons-material/Save';

const Settings = () => {
  const [tabValue, setTabValue] = useState(0);
  const [settings, setSettings] = useState({
    emailNotifications: true,
    darkMode: false,
    apiKey: '••••••••••••••••••••••••••••••••',
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleSettingChange = (field: string, value: any) => {
    setSettings(prev => ({
      ...prev,
      [field]: value
    }));
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Configure your application preferences
      </Typography>

      <Paper sx={{ width: '100%', mt: 3, overflow: 'hidden' }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="settings tabs"
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            px: 2,
          }}
        >
          <Tab label="General" />
          <Tab label="Notifications" />
          <Tab label="API" />
          <Tab label="Security" />
        </Tabs>
        
        <Box sx={{ p: 4 }}>
          {tabValue === 0 && (
            <Box>
              <Typography variant="h6" gutterBottom>General Settings</Typography>
              <Divider sx={{ mb: 3 }} />
              <Box sx={{ maxWidth: 600 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.darkMode}
                      onChange={(e) => handleSettingChange('darkMode', e.target.checked)}
                      color="primary"
                    />
                  }
                  label="Dark Mode"
                  sx={{ mb: 2, display: 'block' }}
                />
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Toggle between light and dark theme
                </Typography>
              </Box>
            </Box>
          )}

          {tabValue === 1 && (
            <Box>
              <Typography variant="h6" gutterBottom>Notification Settings</Typography>
              <Divider sx={{ mb: 3 }} />
              <Box sx={{ maxWidth: 600 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={settings.emailNotifications}
                      onChange={(e) => handleSettingChange('emailNotifications', e.target.checked)}
                      color="primary"
                    />
                  }
                  label="Email Notifications"
                  sx={{ mb: 2, display: 'block' }}
                />
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Receive email notifications for important updates
                </Typography>
              </Box>
            </Box>
          )}

          {tabValue === 2 && (
            <Box>
              <Typography variant="h6" gutterBottom>API Settings</Typography>
              <Divider sx={{ mb: 3 }} />
              <Box sx={{ maxWidth: 600 }}>
                <Typography variant="subtitle2" gutterBottom>
                  API Key
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
                  <TextField
                    value={settings.apiKey}
                    variant="outlined"
                    fullWidth
                    disabled
                    size="small"
                  />
                  <Button variant="outlined" color="primary">
                    Regenerate
                  </Button>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Use this API key to authenticate with our REST API
                </Typography>
              </Box>
            </Box>
          )}

          {tabValue === 3 && (
            <Box>
              <Typography variant="h6" gutterBottom>Security Settings</Typography>
              <Divider sx={{ mb: 3 }} />
              <Typography variant="body2" color="text.secondary">
                Security settings will be available soon
              </Typography>
            </Box>
          )}

          <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              variant="contained"
              color="primary"
              startIcon={<SaveIcon />}
              onClick={() => console.log('Settings saved', settings)}
            >
              Save Changes
            </Button>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default Settings;