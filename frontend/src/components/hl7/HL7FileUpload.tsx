import React, { useState, useCallback } from 'react';
import { Box, Button, Typography, CircularProgress, Paper, Alert } from '@mui/material';
import { Upload as UploadIcon } from '@mui/icons-material';
import { hl7Api } from '../../api/client';

interface HL7FileUploadProps {
  onUploadSuccess?: (response: any) => void;
  onUploadError?: (error: Error) => void;
}

export const HL7FileUpload: React.FC<HL7FileUploadProps> = ({
  onUploadSuccess,
  onUploadError,
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      // Validate file extension
      if (!file.name.endsWith('.hl7')) {
        setError('Only .hl7 files are allowed');
        return;
      }

      setIsUploading(true);
      setError(null);
      setSuccess(null);

      try {
        const response = await hl7Api.uploadFile(file);
        setSuccess('File uploaded and processing started');
        onUploadSuccess?.(response);
      } catch (err) {
        const error = err as Error;
        setError(error.message || 'Failed to upload file');
        onUploadError?.(error);
      } finally {
        setIsUploading(false);
      }
    },
    [onUploadSuccess, onUploadError]
  );

  return (
    <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Upload HL7 File
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success}
        </Alert>
      )}

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Button
          component="label"
          variant="contained"
          startIcon={isUploading ? <CircularProgress size={20} /> : <UploadIcon />}
          disabled={isUploading}
        >
          {isUploading ? 'Uploading...' : 'Select HL7 File'}
          <input
            type="file"
            hidden
            accept=".hl7"
            onChange={handleFileChange}
            disabled={isUploading}
          />
        </Button>
        <Typography variant="body2" color="textSecondary">
          Select a .hl7 file to upload
        </Typography>
      </Box>
    </Paper>
  );
};

export default HL7FileUpload;
