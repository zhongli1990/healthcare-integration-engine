import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography } from '@mui/material';
import {
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress,
  IconButton
} from '@mui/material';
import { 
  CheckCircle as CheckCircleIcon, 
  Error as ErrorIcon, 
  HourglassEmpty as HourglassEmptyIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { hl7Api } from '../../api/client';

interface HL7Stats {
  processed: number;
  errors: number;
  last_processed?: string;
  processing_time_avg?: number;
}

interface HL7Activity {
  id: string;
  timestamp: string;
  status: 'processing' | 'completed' | 'error';
  message: string;
  details?: Record<string, any>;
}

export const HL7Monitoring: React.FC = () => {
  const [stats, setStats] = useState<HL7Stats | null>(null);
  const [activity, setActivity] = useState<HL7Activity[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchStats = useCallback(async () => {
    try {
      const response = await hl7Api.getStats();
      // The API returns { data: { data: { ... } } } structure
      setStats({
        processed: response.data.processed,
        errors: response.data.failed,
        last_processed: response.data.lastProcessed || undefined,
        processing_time_avg: 0 // This field is not in the API response
      });
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }, []);

  const fetchActivity = useCallback(async () => {
    try {
      // In a real app, this would fetch from an activity endpoint
      // For now, we'll simulate some activity based on stats
      if (stats) {
        const mockActivity: HL7Activity[] = [
          {
            id: '1',
            timestamp: new Date().toISOString(),
            status: 'completed',
            message: 'Processed HL7 message',
            details: { message_type: 'ADT^A01' }
          } as const
        ];

        if (stats.errors > 0) {
          mockActivity.push({
            id: '2',
            timestamp: new Date(Date.now() - 60000).toISOString(),
            status: 'error',
            message: 'Failed to process HL7 message',
            details: { error: 'Invalid MSH segment' }
          } as const);
        }
        
        setActivity(mockActivity);
      }
    } catch (err) {
      console.error('Error fetching activity:', err);
    } finally {
      setLoading(false);
    }
  }, [stats]);

  const handleRefresh = useCallback(() => {
    setLoading(true);
    Promise.all([fetchStats(), fetchActivity()])
      .finally(() => setLoading(false));
  }, [fetchStats, fetchActivity]);

  useEffect(() => {
    handleRefresh();
  }, [handleRefresh]);

  useEffect(() => {
    const intervalId = setInterval(fetchStats, 10000); // Poll every 10 seconds
    
    return () => clearInterval(intervalId);
  }, [fetchStats]);



  return (
    <Box sx={{ p: 3, display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 3 }}>
      <Card>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6" component="div">
              HL7 Processing Stats
            </Typography>
            <IconButton 
              onClick={handleRefresh} 
              disabled={loading}
              size="small"
            >
              <RefreshIcon />
            </IconButton>
          </Box>
          {loading ? (
            <Box display="flex" justifyContent="center" p={2}>
              <CircularProgress size={24} />
            </Box>
          ) : stats ? (
            <List>
              <ListItem>
                <ListItemText 
                  primary="Processed Messages" 
                  secondary={stats.processed} 
                />
              </ListItem>
              <ListItem>
                <ListItemText 
                  primary="Errors" 
                  secondary={stats.errors} 
                  secondaryTypographyProps={{ 
                    color: stats.errors > 0 ? 'error' : 'textSecondary' 
                  }}
                />
              </ListItem>
            </List>
          ) : (
            <Typography color="textSecondary">No data available</Typography>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Activity
          </Typography>
          {loading ? (
            <Box display="flex" justifyContent="center" p={2}>
              <CircularProgress size={24} />
            </Box>
          ) : activity.length > 0 ? (
            <List>
              {activity.map((item) => (
                <ListItem key={item.id}>
                  <ListItemIcon>
                    {item.status === 'completed' ? (
                      <CheckCircleIcon color="success" />
                    ) : item.status === 'error' ? (
                      <ErrorIcon color="error" />
                    ) : (
                      <HourglassEmptyIcon color="disabled" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.message}
                    secondary={new Date(item.timestamp).toLocaleString()}
                  />
                </ListItem>
              ))}
            </List>
          ) : (
            <Typography color="textSecondary">No recent activity</Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default HL7Monitoring;
