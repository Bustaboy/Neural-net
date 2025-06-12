// client/src/store/store.js
import { configureStore } from '@reduxjs/toolkit';
import authReducer from './authSlice';
import tradingReducer from './tradingSlice';
import marketReducer from './marketSlice';
import portfolioReducer from './portfolioSlice';
import notificationReducer from './notificationSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    trading: tradingReducer,
    market: marketReducer,
    portfolio: portfolioReducer,
    notifications: notificationReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['auth/login/fulfilled', 'trading/updatePositions'],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['meta.arg', 'payload.timestamp'],
        // Ignore these paths in the state
        ignoredPaths: ['auth.user', 'trading.positions'],
      },
    }),
});

// client/src/store/authSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import authService from '../services/api/authService';

// Async thunks
export const login = createAsyncThunk(
  'auth/login',
  async ({ username, password, totpCode }, { rejectWithValue }) => {
    try {
      const response = await authService.login(username, password, totpCode);
      return {
        user: authService.getCurrentUser(),
        token: response.access_token,
      };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Login failed');
    }
  }
);

export const register = createAsyncThunk(
  'auth/register',
  async (userData, { rejectWithValue }) => {
    try {
      const response = await authService.register(userData);
      return {
        user: authService.getCurrentUser(),
        token: response.access_token,
      };
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Registration failed');
    }
  }
);

export const logout = createAsyncThunk('auth/logout', async () => {
  await authService.logout();
});

export const checkAuthStatus = createAsyncThunk('auth/checkStatus', async () => {
  const token = authService.getAccessToken();
  if (token) {
    const user = authService.getCurrentUser();
    return { user, token };
  }
  return null;
});

// Slice
const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
  },
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
    updateUser: (state, action) => {
      state.user = { ...state.user, ...action.payload };
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.token = action.payload.token;
        state.error = null;
      })
      .addCase(login.rejected, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        state.error = action.payload;
      })
      // Register
      .addCase(register.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(register.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.token = action.payload.token;
        state.error = null;
      })
      .addCase(register.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Logout
      .addCase(logout.fulfilled, (state) => {
        state.user = null;
        state.token = null;
        state.isAuthenticated = false;
        state.error = null;
      })
      // Check auth status
      .addCase(checkAuthStatus.fulfilled, (state, action) => {
        if (action.payload) {
          state.user = action.payload.user;
          state.token = action.payload.token;
          state.isAuthenticated = true;
        } else {
          state.user = null;
          state.token = null;
          state.isAuthenticated = false;
        }
      });
  },
});

export const { clearError, updateUser } = authSlice.actions;
export default authSlice.reducer;

// client/src/store/tradingSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import tradingService from '../services/api/tradingService';

// Async thunks
export const startBot = createAsyncThunk(
  'trading/startBot',
  async (config, { rejectWithValue }) => {
    try {
      const response = await tradingService.startBot(config);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to start bot');
    }
  }
);

export const stopBot = createAsyncThunk(
  'trading/stopBot',
  async (_, { rejectWithValue }) => {
    try {
      const response = await tradingService.stopBot();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to stop bot');
    }
  }
);

export const getBotStatus = createAsyncThunk(
  'trading/getBotStatus',
  async (_, { rejectWithValue }) => {
    try {
      const response = await tradingService.getBotStatus();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to get bot status');
    }
  }
);

export const fetchPositions = createAsyncThunk(
  'trading/fetchPositions',
  async (_, { rejectWithValue }) => {
    try {
      const response = await tradingService.getPositions();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch positions');
    }
  }
);

export const placeOrder = createAsyncThunk(
  'trading/placeOrder',
  async (orderData, { rejectWithValue }) => {
    try {
      const response = await tradingService.placeOrder(orderData);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to place order');
    }
  }
);

// Slice
const tradingSlice = createSlice({
  name: 'trading',
  initialState: {
    botStatus: null,
    positions: [],
    orders: [],
    trades: [],
    performance: null,
    isLoading: false,
    error: null,
  },
  reducers: {
    updateBotStatus: (state, action) => {
      state.botStatus = action.payload;
    },
    updatePositions: (state, action) => {
      state.positions = action.payload;
    },
    addPosition: (state, action) => {
      state.positions.push(action.payload);
    },
    updatePosition: (state, action) => {
      const index = state.positions.findIndex((p) => p.id === action.payload.id);
      if (index !== -1) {
        state.positions[index] = action.payload;
      }
    },
    removePosition: (state, action) => {
      state.positions = state.positions.filter((p) => p.id !== action.payload);
    },
    updatePerformance: (state, action) => {
      state.performance = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Start bot
      .addCase(startBot.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(startBot.fulfilled, (state, action) => {
        state.isLoading = false;
        state.botStatus = action.payload;
      })
      .addCase(startBot.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Stop bot
      .addCase(stopBot.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(stopBot.fulfilled, (state) => {
        state.isLoading = false;
        state.botStatus = { status: 'stopped' };
      })
      .addCase(stopBot.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Get bot status
      .addCase(getBotStatus.fulfilled, (state, action) => {
        state.botStatus = action.payload;
      })
      // Fetch positions
      .addCase(fetchPositions.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchPositions.fulfilled, (state, action) => {
        state.isLoading = false;
        state.positions = action.payload;
      })
      .addCase(fetchPositions.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      // Place order
      .addCase(placeOrder.fulfilled, (state, action) => {
        // Order placed successfully - will be updated via WebSocket
      });
  },
});

export const {
  updateBotStatus,
  updatePositions,
  addPosition,
  updatePosition,
  removePosition,
  updatePerformance,
  clearError,
} = tradingSlice.actions;

export default tradingSlice.reducer;

// client/src/store/portfolioSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import tradingService from '../services/api/tradingService';

export const fetchPortfolio = createAsyncThunk(
  'portfolio/fetchPortfolio',
  async (_, { rejectWithValue }) => {
    try {
      const response = await tradingService.getPortfolio();
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch portfolio');
    }
  }
);

export const fetchPortfolioHistory = createAsyncThunk(
  'portfolio/fetchHistory',
  async (timeframe = '1d', { rejectWithValue }) => {
    try {
      const response = await tradingService.getPortfolioHistory(timeframe);
      return response;
    } catch (error) {
      return rejectWithValue(error.response?.data?.detail || 'Failed to fetch history');
    }
  }
);

const portfolioSlice = createSlice({
  name: 'portfolio',
  initialState: {
    balance: {
      total: 0,
      available: 0,
      locked: 0,
    },
    assets: [],
    history: [],
    performance: {
      daily_pnl: 0,
      total_pnl: 0,
      win_rate: 0,
      sharpe_ratio: 0,
    },
    isLoading: false,
    error: null,
  },
  reducers: {
    updateBalance: (state, action) => {
      state.balance = action.payload;
    },
    updateAssets: (state, action) => {
      state.assets = action.payload;
    },
    updatePerformance: (state, action) => {
      state.performance = { ...state.performance, ...action.payload };
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchPortfolio.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(fetchPortfolio.fulfilled, (state, action) => {
        state.isLoading = false;
        state.balance = action.payload.balance;
        state.assets = action.payload.assets;
        state.performance = action.payload.performance;
      })
      .addCase(fetchPortfolio.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload;
      })
      .addCase(fetchPortfolioHistory.fulfilled, (state, action) => {
        state.history = action.payload;
      });
  },
});

export const { updateBalance, updateAssets, updatePerformance } = portfolioSlice.actions;
export default portfolioSlice.reducer;