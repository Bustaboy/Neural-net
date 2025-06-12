# emergency/kill_switch.py
class EmergencyKillSwitch:
    def __init__(self, bot_manager, notification_manager):
        self.bot_manager = bot_manager
        self.notification_manager = notification_manager
        self.activated = False
        
    def activate(self, reason: str, triggered_by: str):
        """Emergency stop all trading activities"""
        if self.activated:
            return
            
        self.activated = True
        
        # 1. Stop all bots
        self.bot_manager.stop_all_bots()
        
        # 2. Cancel all open orders
        open_orders = self.bot_manager.get_all_open_orders()
        for order in open_orders:
            self.bot_manager.cancel_order(order['id'])
            
        # 3. Close all positions at market
        positions = self.bot_manager.get_all_positions()
        for position in positions:
            self.bot_manager.close_position_market(position)
            
        # 4. Notify all stakeholders
        self.notification_manager.send_emergency_alert(
            f"EMERGENCY KILL SWITCH ACTIVATED\nReason: {reason}\nTriggered by: {triggered_by}"
        )
        
        # 5. Log everything
        self.log_emergency_activation(reason, triggered_by)
