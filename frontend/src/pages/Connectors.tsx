import { Box, Typography, Paper, Button } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';

const Connectors = () => {
  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Connectors
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Configure and manage your integration connectors
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          sx={{ height: 'fit-content' }}
        >
          Add Connector
        </Button>
      </Box>
      
      <Paper sx={{ p: 4, mt: 2, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          No connectors configured
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2, mb: 3 }}>
          Get started by adding your first connector to begin integrating systems.
        </Typography>
        <Button variant="outlined" startIcon={<AddIcon />}>
          Add Your First Connector
        </Button>
      </Paper>
    </Box>
  );
};

export default Connectors;