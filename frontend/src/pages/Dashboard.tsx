import { useState, useEffect } from 'react';
import { 
  Box, 
  Card, 
  CardContent, 
  Grid, 
  Typography, 
  CircularProgress,
  alpha,
  styled
} from '@mui/material';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import PendingActionsIcon from '@mui/icons-material/PendingActions';

interface DashboardStats {
  totalMessages: number;
  successfulMessages: number;
  failedMessages: number;
  pendingMessages: number;
}

const StatCard = styled(Card)(() => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.2s',
  '&:hover': {
    transform: 'translateY(-4px)',
  },
}));

const StatCardContent = styled(CardContent)(() => ({
  flexGrow: 1,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  textAlign: 'center',
}));

interface StatIconProps {
  color?: 'primary' | 'success' | 'error' | 'warning';
}

const StatIcon = styled('div', {
  shouldForwardProp: (prop) => prop !== 'color',
})<StatIconProps>(({ theme, color = 'primary' }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 60,
  height: 60,
  borderRadius: '50%',
  backgroundColor: alpha(theme.palette[color].main, 0.1),
  color: theme.palette[color].main,
  marginBottom: theme.spacing(2),
  '& svg': {
    fontSize: 30,
  },
}));

const StatContent = styled('div')(({ theme }) => ({
  marginTop: theme.spacing(1),
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
}));

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardStats = async () => {
      try {
        setLoading(true);
        // TODO: Replace with actual API call
        // const response = await api.get('/dashboard/stats');
        // setStats(response.data);
        
        // Mock data for now
        setTimeout(() => {
          setStats({
            totalMessages: 1245,
            successfulMessages: 1150,
            failedMessages: 42,
            pendingMessages: 53,
          });
          setLoading(false);
        }, 500);
      } catch (err) {
        console.error('Failed to fetch dashboard stats:', err);
        setError('Failed to load dashboard data. Please try again later.');
        setLoading(false);
      }
    };

    fetchDashboardStats();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box color="error.main" textAlign="center" p={3}>
        <ErrorOutlineIcon fontSize="large" />
        <Typography variant="h6" mt={2}>
          {error}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        HL7 Dashboard
      </Typography>
      
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard>
            <StatCardContent>
              <StatIcon>
                <MonitorHeartIcon />
              </StatIcon>
              <Typography variant="h4" component="div">
                {stats?.totalMessages.toLocaleString()}
              </Typography>
              <Typography color="textSecondary">
                Total Messages
              </Typography>
            </StatCardContent>
          </StatCard>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard>
            <StatCardContent>
              <StatIcon color="success">
                <CheckCircleOutlineIcon />
              </StatIcon>
              <Typography variant="h4" component="div">
                {stats?.successfulMessages.toLocaleString()}
              </Typography>
              <Typography color="textSecondary">
                Successful
              </Typography>
            </StatCardContent>
          </StatCard>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard>
            <StatCardContent>
              <StatIcon color="error">
                <ErrorOutlineIcon />
              </StatIcon>
              <Typography variant="h4" component="div">
                {stats?.failedMessages.toLocaleString()}
              </Typography>
              <Typography color="textSecondary">
                Failed
              </Typography>
            </StatCardContent>
          </StatCard>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard>
            <StatContent>
              <StatIcon color="warning">
                <PendingActionsIcon />
              </StatIcon>
              <Typography variant="h4" component="div">
                {stats?.pendingMessages.toLocaleString()}
              </Typography>
              <Typography color="textSecondary">
                Pending
              </Typography>
            </StatContent>
          </StatCard>
        </Grid>
      </Grid>
      
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Recent Activity
          </Typography>
          <Typography color="textSecondary">
            Activity feed will be displayed here
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Dashboard;
