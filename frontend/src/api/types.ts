// API response type
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
  timestamp: string;
}

// Common pagination parameters
export interface PaginationParams {
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

// Common paginated response
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Common error response
export interface ApiError {
  status: number;
  message: string;
  errors?: Record<string, string[]>;
  timestamp?: string;
  path?: string;
  isNetworkError?: boolean;
  isAxiosError?: boolean;
  config?: unknown;
  response?: unknown;
}

// API configuration
export interface ApiConfig {
  requireAuth?: boolean;
  skipErrorHandling?: boolean;
}
