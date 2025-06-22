import { Box, Typography, Paper, Tabs, Tab } from '@mui/material';
import { useState } from 'react';

const Logs = () => {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Logs
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        View and monitor system and integration logs
      </Typography>

      <Paper sx={{ width: '100%', mt: 3 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="log types"
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            px: 2,
          }}
        >
          <Tab label="All Logs" />
          <Tab label="System" />
          <Tab label="API" />
          <Tab label="Errors" />
        </Tabs>
        
        <Box sx={{ p: 3, textAlign: 'center', minHeight: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Box>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Logs will appear here
            </Typography>
            <Typography variant="body2" color="text.secondary">
              System and integration logs will be displayed in this section.
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              Select a log entry to view details
            </Typography>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default Logs;