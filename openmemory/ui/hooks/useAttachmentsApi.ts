import { useState, useCallback } from 'react';
import axios from 'axios';

export interface Attachment {
  id: string;
  content: string;
  created_at: string;
  updated_at: string;
}

interface UseAttachmentsApiReturn {
  fetchAttachment: (id: string) => Promise<Attachment>;
  createAttachment: (content: string, id?: string) => Promise<Attachment>;
  updateAttachment: (id: string, content: string) => Promise<Attachment>;
  deleteAttachment: (id: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

export const useAttachmentsApi = (): UseAttachmentsApiReturn => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

  const fetchAttachment = useCallback(async (id: string): Promise<Attachment> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.get<Attachment>(`${URL}/api/v1/attachments/${id}`);
      setIsLoading(false);
      return response.data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch attachment';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  }, [URL]);

  const createAttachment = useCallback(async (content: string, id?: string): Promise<Attachment> => {
    setIsLoading(true);
    setError(null);
    try {
      const payload = id ? { content, id } : { content };
      const response = await axios.post<Attachment>(`${URL}/api/v1/attachments`, payload);
      setIsLoading(false);
      return response.data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create attachment';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  }, [URL]);

  const updateAttachment = useCallback(async (id: string, content: string): Promise<Attachment> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await axios.put<Attachment>(`${URL}/api/v1/attachments/${id}`, { content });
      setIsLoading(false);
      return response.data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to update attachment';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  }, [URL]);

  const deleteAttachment = useCallback(async (id: string): Promise<void> => {
    setIsLoading(true);
    setError(null);
    try {
      await axios.delete(`${URL}/api/v1/attachments/${id}`);
      setIsLoading(false);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to delete attachment';
      setError(errorMessage);
      setIsLoading(false);
      throw new Error(errorMessage);
    }
  }, [URL]);

  return {
    fetchAttachment,
    createAttachment,
    updateAttachment,
    deleteAttachment,
    isLoading,
    error,
  };
};
