// client/src/components/trading/TradingInterface.jsx
import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Box,
  Typography,
  Button,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  Snackbar,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Settings,
  TrendingUp,
  TrendingDown,
  Warning,
  CheckCircle,
  Error,
} from '@mui/icons-material';
import { useSelector, useDispatch } from 'react-redux';

import TradingChart from './TradingChart';
import PositionsTable from './PositionsTable';
import OrderForm from './OrderForm';
import BotControls from './BotControls';
import PerformanceMetrics from './PerformanceMetrics';
import ActivityLog from './ActivityLog';
import ConfigModal from './ConfigModal';

import { startBot, stopBot, getBotStatus } from '../../store/tradingSlice';
import websocketService from '../../services/websocketService';

const TradingInterface = () => {
  const dispatch = useDispatch();
  const { botStatus, positions, isLoading } = useSelector((state) => state.trading);
  const [configOpen, setConfigOpen] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDT');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  useEffect(() => {
    // Load initial bot status
    dispatch(getBotStatus());

    // Subscribe to real-time updates
    const unsubscribeBotStatus = websocketService.subscribe('bot_status', (data) => {
      dispatch({ type: 'trading/updateBotStatus', payload: data });
    });

    const unsubscribePositions = websocketService.subscribe('position_update', (data) => {
      dispatch({ type: 'trading/updatePositions', payload: data });
    });

    const unsubscribeTrades = websocketService.subscribe('trade_executed', (data) => {
      showSnackbar(`Trade executed: ${data.side} ${data.quantity} ${data.symbol}`, 'success');
    });

    return () => {
      unsubscribeBotStatus();
      unsubscribePositions();
      unsubscribeTrades();
    };
  }, [dispatch]);

  const handleStartBot = async () => {
    try {
      await dispatch(startBot()).unwrap();
      showSnackbar('Bot started successfully', 'success');
    } catch (error) {
      showSnackbar(`Failed to start bot: ${error.message}`, 'error');
    }
  };

  const handleStopBot = async () => {
    try {
      await dispatch(stopBot()).unwrap();
      showSnackbar('Bot stopped successfully', 'info');
    } catch (error) {
      showSnackbar(`Failed to stop bot: ${error.message}`, 'error');
    }
  };

  const showSnackbar = (message, severity) => {
    setSnackbar({ open: true, message, severity });
  };

  const getBotStatusIcon = () => {
    switch (botStatus?.status) {
      case 'running':
        return <CheckCircle color="success" />;
      case 'error':
        return <Error color="error" />;
      case 'paused':
        return <Warning color="warning" />;
      default:
        return <Error color="disabled" />;
    }
  };

  const getBotStatusColor = () => {
    switch (botStatus?.status) {
      case 'running':
        return 'success';
      case 'error':
        return 'error';
      case 'paused':
        return 'warning';
      default:
        return 'default';
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={3}>
        {/* Header Controls */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h5" component="h1">
                Trading Interface
              </Typography>
              <Chip
                icon={getBotStatusIcon()}
                label={botStatus?.status || 'Offline'}
                color={getBotStatusColor()}
                size="small"
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="contained"
                color="success"
                startIcon={<PlayArrow />}
                onClick={handleStartBot}
                disabled={botStatus?.status === 'running' || isLoading}
              >
                Start Bot
              </Button>
              <Button
                variant="contained"
                color="error"
                startIcon={<Stop />}
                onClick={handleStopBot}
                disabled={botStatus?.status !== 'running' || isLoading}
              >
                Stop Bot
              </Button>
              <Tooltip title="Bot Configuration">
                <IconButton onClick={() => setConfigOpen(true)}>
                  <Settings />
                </IconButton>
              </Tooltip>
            </Box>
          </Paper>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12}>
          <PerformanceMetrics />
        </Grid>

        {/* Main Trading Area */}
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 2, height: 500 }}>
            <TradingChart symbol={selectedSymbol} />
          </Paper>
        </Grid>

        {/* Order Form */}
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 2, height: 500 }}>
            <OrderForm symbol={selectedSymbol} />
          </Paper>
        </Grid>

        {/* Positions Table */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Active Positions
            </Typography>
            <PositionsTable 
              positions={positions}
              onSelectSymbol={setSelectedSymbol}
            />
          </Paper>
        </Grid>

        {/* Bot Controls and Activity */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              Bot Controls
            </Typography>
            <BotControls />
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: 400, overflow: 'hidden' }}>
            <Typography variant="h6" gutterBottom>
              Activity Log
            </Typography>
            <ActivityLog />
          </Paper>
        </Grid>
      </Grid>

      {/* Configuration Modal */}
      <ConfigModal
        open={configOpen}
        onClose={() => setConfigOpen(false)}
      />

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default TradingInterface;

// client/src/components/trading/PositionsTable.jsx
import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Typography,
  Box,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from '@mui/material';
import {
  Close,
  TrendingUp,
  TrendingDown,
  Info,
} from '@mui/icons-material';
import { formatCurrency, formatPercent } from '../../utils/formatters';

const PositionsTable = ({ positions = [], onSelectSymbol }) => {
  const [closeDialog, setCloseDialog] = useState({ open: false, position: null });

  const handleClosePosition = async (position) => {
    // Implement close position logic
    console.log('Closing position:', position);
    setCloseDialog({ open: false, position: null });
  };

  const getPnLColor = (pnl) => {
    return pnl >= 0 ? 'success.main' : 'error.main';
  };

  if (!positions || positions.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" color="text.secondary">
          No active positions
        </Typography>
      </Box>
    );
  }

  return (
    <>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Symbol</TableCell>
              <TableCell>Side</TableCell>
              <TableCell align="right">Quantity</TableCell>
              <TableCell align="right">Entry Price</TableCell>
              <TableCell align="right">Current Price</TableCell>
              <TableCell align="right">P&L</TableCell>
              <TableCell align="right">P&L %</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {positions.map((position) => (
              <TableRow
                key={position.id}
                hover
                onClick={() => onSelectSymbol(position.symbol)}
                sx={{ cursor: 'pointer' }}
              >
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {position.side === 'long' ? (
                      <TrendingUp color="success" fontSize="small" />
                    ) : (
                      <TrendingDown color="error" fontSize="small" />
                    )}
                    <Typography variant="body2" fontWeight="medium">
                      {position.symbol}
                    </Typography>
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={position.side}
                    size="small"
                    color={position.side === 'long' ? 'success' : 'error'}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell align="right">{position.quantity}</TableCell>
                <TableCell align="right">
                  {formatCurrency(position.entry_price)}
                </TableCell>
                <TableCell align="right">
                  {formatCurrency(position.current_price)}
                </TableCell>
                <TableCell align="right">
                  <Typography
                    variant="body2"
                    color={getPnLColor(position.unrealized_pnl)}
                    fontWeight="medium"
                  >
                    {formatCurrency(position.unrealized_pnl)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography
                    variant="body2"
                    color={getPnLColor(position.unrealized_pnl)}
                    fontWeight="medium"
                  >
                    {formatPercent(position.unrealized_pnl_percentage)}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Position Details">
                    <IconButton size="small">
                      <Info fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Close Position">
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        setCloseDialog({ open: true, position });
                      }}
                    >
                      <Close fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Close Position Dialog */}
      <Dialog
        open={closeDialog.open}
        onClose={() => setCloseDialog({ open: false, position: null })}
      >
        <DialogTitle>Close Position</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to close this {closeDialog.position?.side} position for{' '}
            {closeDialog.position?.symbol}?
          </Typography>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Quantity: {closeDialog.position?.quantity}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Current P&L:{' '}
              <span style={{ color: getPnLColor(closeDialog.position?.unrealized_pnl) }}>
                {formatCurrency(closeDialog.position?.unrealized_pnl)} (
                {formatPercent(closeDialog.position?.unrealized_pnl_percentage)})
              </span>
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCloseDialog({ open: false, position: null })}>
            Cancel
          </Button>
          <Button
            onClick={() => handleClosePosition(closeDialog.position)}
            color="error"
            variant="contained"
          >
            Close Position
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default PositionsTable;
