import { useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import type { UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import apiClient, { hl7Api } from './client';
import type { ApiResponse, ApiError, PaginatedResponse } from './types';

type ApiConfig<T = unknown> = Omit<
  UseQueryOptions<ApiResponse<T>, ApiError>,
  'queryKey' | 'queryFn'
> & {
  enabled?: boolean;
  params?: Record<string, unknown>;
};

export const useApi = <T>(
  key: string | unknown[],
  url: string,
  config: ApiConfig<T> = {}
) => {
  const fetchData = useCallback(async () => {
    const response = await apiClient.get<ApiResponse<T>>(url, { params: config.params });
    return response.data; // Return the data property from the Axios response
  }, [url, config.params]);

  return useQuery<ApiResponse<T>, ApiError>({
    queryKey: Array.isArray(key) ? [...key, config.params] : [key, config.params],
    queryFn: fetchData,
    enabled: config.enabled,
    retry: (failureCount, error) => {
      // Don't retry on 4xx errors
      if (error.status && error.status >= 400 && error.status < 500) {
        return false;
      }
      // Retry up to 3 times for other errors
      return failureCount < 3;
    },
    ...config,
  });
};

export const usePaginatedApi = <T>(
  key: string | unknown[],
  url: string,
  params: Record<string, unknown> = {},
  config: Omit<ApiConfig<PaginatedResponse<T>>, 'params'> = {}
) => {
  const fetchData = useCallback(async () => {
    const response = await apiClient.get<ApiResponse<PaginatedResponse<T>>>(url, { params });
    return response.data; // Return the data property from the Axios response
  }, [url, params]);

  return useQuery<ApiResponse<PaginatedResponse<T>>, ApiError>({
    queryKey: [...(Array.isArray(key) ? key : [key]), params],
    queryFn: fetchData,
    placeholderData: (previousData) => previousData || undefined,
    ...config,
  });
};

export const usePostApi = <T, D = unknown>(
  url: string,
  config: Omit<UseMutationOptions<ApiResponse<T>, ApiError, D>, 'mutationFn'> = {}
) => {
  return useMutation<ApiResponse<T>, ApiError, D>({
    mutationFn: async (data: D) => {
      const response = await apiClient.post<ApiResponse<T>>(url, data);
      return response.data; // Return the data property from the Axios response
    },
    ...config,
  });
};

export const usePutApi = <T, D = unknown>(
  url: string,
  config: Omit<UseMutationOptions<ApiResponse<T>, ApiError, D>, 'mutationFn'> = {}
) => {
  return useMutation<ApiResponse<T>, ApiError, D>({
    mutationFn: async (data: D) => {
      const response = await apiClient.put<ApiResponse<T>>(url, data);
      return response.data; // Return the data property from the Axios response
    },
    ...config,
  });
};

export const useDeleteApi = <T,>(
  url: string,
  config: Omit<UseMutationOptions<ApiResponse<T>, ApiError, void>, 'mutationFn'> = {}
) => {
  return useMutation<ApiResponse<T>, ApiError, void>({
    mutationFn: async () => {
      const response = await apiClient.delete<ApiResponse<T>>(url);
      return response.data; // Return the data property from the Axios response
    },
    ...config,
  });
};

// HL7 specific hooks
export const useHl7Stats = (config?: Omit<ApiConfig<{
  total: number;
  processed: number;
  failed: number;
  lastProcessed: string | null;
}>, 'params'>) => {
  return useApi('hl7-stats', '/hl7/stats', config);
};

export const useUploadHl7File = () => {
  return useMutation({
    mutationFn: (file: File) => hl7Api.uploadFile(file).then(response => response.data),
  });
};

export const useProcessHl7Content = () => {
  return useMutation({
    mutationFn: (content: string) => hl7Api.processContent(content).then(response => response.data),
  });
};
