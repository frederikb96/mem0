import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface AttachmentListItem {
  id: string;
  content: string;           // Preview (200 chars)
  content_length: number;
  created_at: number;        // Unix timestamp
  updated_at: number;        // Unix timestamp
}

interface AttachmentsState {
  attachments: AttachmentListItem[];
  selectedAttachmentIds: string[];
  status: 'idle' | 'loading' | 'succeeded' | 'failed';
  error: string | null;
}

const initialState: AttachmentsState = {
  attachments: [],
  selectedAttachmentIds: [],
  status: 'idle',
  error: null,
};

const attachmentsSlice = createSlice({
  name: 'attachments',
  initialState,
  reducers: {
    setAttachmentsLoading: (state) => {
      state.status = 'loading';
      state.error = null;
      state.attachments = [];
    },
    setAttachmentsSuccess: (state, action: PayloadAction<AttachmentListItem[]>) => {
      state.status = 'succeeded';
      state.attachments = action.payload;
      state.error = null;
    },
    setAttachmentsError: (state, action: PayloadAction<string>) => {
      state.status = 'failed';
      state.error = action.payload;
    },
    selectAttachment: (state, action: PayloadAction<string>) => {
      if (!state.selectedAttachmentIds.includes(action.payload)) {
        state.selectedAttachmentIds.push(action.payload);
      }
    },
    deselectAttachment: (state, action: PayloadAction<string>) => {
      state.selectedAttachmentIds = state.selectedAttachmentIds.filter(
        id => id !== action.payload
      );
    },
    selectAllAttachments: (state) => {
      state.selectedAttachmentIds = state.attachments.map(a => a.id);
    },
    clearSelection: (state) => {
      state.selectedAttachmentIds = [];
    },
  },
});

export const {
  setAttachmentsLoading,
  setAttachmentsSuccess,
  setAttachmentsError,
  selectAttachment,
  deselectAttachment,
  selectAllAttachments,
  clearSelection,
} = attachmentsSlice.actions;

export default attachmentsSlice.reducer;
