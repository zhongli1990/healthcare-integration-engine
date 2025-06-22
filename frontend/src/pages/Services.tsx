import { Box, Typography, Paper } from '@mui/material';

const Services = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Services
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Manage and monitor your integration services
      </Typography>
      
      <Paper sx={{ p: 4, mt: 3, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          Services management coming soon
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          This section will allow you to manage and monitor all your integration services.
        </Typography>
      </Paper>
    </Box>
  );
};

export default Services;