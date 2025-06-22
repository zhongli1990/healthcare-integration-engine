import axios from 'axios';
import type {
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  AxiosError,
  InternalAxiosRequestConfig,
} from 'axios';
import { authService } from '../services/authService';
import type { ApiError, ApiResponse } from './types';

// Check if we should use mock API (for development without backend)
const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API === 'true';

// Create an Axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  timeout: 30000, // 30 seconds
  withCredentials: true,
});

// Request interceptor for API calls
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Skip auth for login/refresh token endpoints
    if (config.url?.includes('/auth/')) {
      return config;
    }

    // Add auth token if available
    const token = authService.getAuthToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject({
      status: error.response?.status || 0,
      message: error.message || 'Network Error',
      isAxiosError: true,
      config: error.config,
      response: error.response,
    } as ApiError);
  }
);

// Response interceptor for API calls
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Handle 401 Unauthorized - Token expired or invalid
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // In a real JWT implementation, we would refresh the token here
        // For now, we'll just clear the auth state and redirect to login
        if (authService.isAuthenticated()) {
          await authService.logout();
          window.location.href = '/login';
        }
      } catch (refreshError) {
        console.error('Failed to refresh token:', refreshError);
        return Promise.reject(error);
      }
    }

    // Handle network errors
    if (!error.response) {
      const networkError: ApiError = {
        status: 0,
        message: 'Network Error: Please check your internet connection',
        isNetworkError: true,
      };
      return Promise.reject(networkError);
    }

    const { status, data } = error.response;
    const errorMessage = data?.message || error.message || 'An unknown error occurred';
    
    // Create standardized error object
    const apiError: ApiError = {
      status: status || 500,
      message: errorMessage,
      errors: data?.errors,
      timestamp: data?.timestamp || new Date().toISOString(),
      path: data?.path || error.config?.url,
    };

    // Handle specific HTTP status codes
    switch (status) {
      case 401:
        // Clear auth and redirect to login
        if (typeof window !== 'undefined') {
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        break;
      case 403:
        console.error('Access forbidden:', errorMessage);
        break;
      case 404:
        console.error('Resource not found:', error.config?.url);
        break;
      case 422:
        console.error('Validation error:', data?.errors);
        break;
      case 500:
        console.error('Server error:', errorMessage);
        break;
      default:
        console.error(`Error ${status}:`, errorMessage);
    }

    return Promise.reject(apiError);
  }
);

// Helper function to handle API requests with proper typing
export async function apiRequest<T = any>(
  config: AxiosRequestConfig
): Promise<T> {
  // If using mock API and this is an auth endpoint, handle it locally
  if (USE_MOCK_API && config.url?.includes('/auth/')) {
    if (config.url.includes('login') && config.method?.toLowerCase() === 'post') {
      const { email, password } = JSON.parse(config.data);
      const { user, token } = await authService.login(email, password);
      return { user, token } as any;
    }
    
    if (config.url.includes('me') && config.method?.toLowerCase() === 'get') {
      const user = authService.getCurrentUser();
      if (!user) throw { status: 401, message: 'Not authenticated' };
      return { user } as any;
    }
  }

  // For non-auth endpoints or when not using mock API, make the actual request
  try {
    const response = await apiClient(config);
    if (response.data?.success) {
      return response.data.data;
    }
    throw response.data?.error || new Error('Unknown API error');
  } catch (error) {
    console.error('API Request Error:', error);
    throw error;
  }
}

// HL7 API methods
export const hl7Api = {
  // Upload HL7 file
  uploadFile: async (file: File): Promise<ApiResponse<{ id: string; filename: string }>> => {
    const formData = new FormData();
    formData.append('file', file);
    
    return apiRequest<ApiResponse<{ id: string; filename: string }>>({
      method: 'POST',
      url: '/hl7/upload',
      data: formData,
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },

  // Get processing statistics
  getStats: async (): Promise<ApiResponse<{
    total: number;
    processed: number;
    failed: number;
    lastProcessed: string | null;
  }>> => {
    return apiRequest<ApiResponse<{
      total: number;
      processed: number;
      failed: number;
      lastProcessed: string | null;
    }>>({
      method: 'GET',
      url: '/hl7/stats',
    });
  },

  // Process HL7 content directly
  processContent: async (content: string): Promise<ApiResponse<{
    message: string;
    data: unknown;
  }>> => {
    return apiRequest<ApiResponse<{
      message: string;
      data: unknown;
    }>>({
      method: 'POST',
      url: '/hl7/process',
      data: { content },
    });
  },
};

export default apiClient;
