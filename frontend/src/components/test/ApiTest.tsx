import React from 'react';
import { useHl7Stats } from '../../api/useApi';
import { Box, Typography, CircularProgress, Paper } from '@mui/material';

const ApiTest: React.FC = () => {
  const { data, isLoading, error } = useHl7Stats();

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={4}>
        <Typography color="error">
          Error: {error.message || 'Failed to fetch statistics'}
        </Typography>
      </Box>
    );
  }

  return (
    <Paper elevation={3} sx={{ p: 3, maxWidth: 600, mx: 'auto', mt: 4 }}>
      <Typography variant="h6" gutterBottom>
        HL7 Statistics Test
      </Typography>
      <Box sx={{ mt: 2 }}>
        <Typography>Total: {data?.data?.total || 0}</Typography>
        <Typography>Processed: {data?.data?.processed || 0}</Typography>
        <Typography>Failed: {data?.data?.failed || 0}</Typography>
        <Typography>
          Last Processed: {data?.data?.lastProcessed || 'Never'}
        </Typography>
      </Box>
    </Paper>
  );
};

export default ApiTest;
