import React, { useState } from 'react';
import { Box, Container, Typography } from '@mui/material';
import { HL7FileUpload } from '../components/hl7/HL7FileUpload';
import { HL7Monitoring } from '../components/hl7/HL7Monitoring';

const Monitoring: React.FC = () => {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploadSuccess = () => {
    // Increment the key to force a refresh of the monitoring component
    setRefreshKey(prev => prev + 1);
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          HL7 Message Processing
        </Typography>
        
        <Box sx={{ mb: 4 }}>
          <HL7FileUpload 
            onUploadSuccess={handleUploadSuccess} 
            onUploadError={(error) => console.error('Upload error:', error)}
          />
        </Box>
        
        <Box>
          <HL7Monitoring key={refreshKey} />
        </Box>
      </Box>
    </Container>
  );
};

export default Monitoring;
