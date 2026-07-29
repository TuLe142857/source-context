import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import { ACCESS_TOKEN_STORAGE_KEY } from '@/api/http';
import type { UserResponse } from '@/api/types/auth';

export interface AuthState {
  user: UserResponse | null;
  token: string | null;
}

const initialState: AuthState = {
  user: null,
  token: localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY),
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials(state, action: PayloadAction<{ user: UserResponse; token: string }>) {
      state.user = action.payload.user;
      state.token = action.payload.token;
      localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, action.payload.token);
    },
    setUser(state, action: PayloadAction<UserResponse>) {
      state.user = action.payload;
    },
    logout(state) {
      state.user = null;
      state.token = null;
      localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    },
  },
});

export const { setCredentials, setUser, logout } = authSlice.actions;
export default authSlice.reducer;
