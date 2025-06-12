# api/routes/alerts.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

alerts_bp = Blueprint('alerts', __name__, url_prefix='/api/alerts')

@alerts_bp.route('/rules', methods=['GET'])
@jwt_required()
def get_alert_rules():
    """Get user's alert rules"""
    user_id = get_jwt_identity()['user_id']
    
    rules = current_app.config['db_manager'].fetch_all("""
        SELECT * FROM alert_rules WHERE user_id = ?
    """, (user_id,))
    
    return jsonify({'rules': rules}), 200

@alerts_bp.route('/rules', methods=['POST'])
@jwt_required()
def create_alert_rule():
    """Create new alert rule"""
    user_id = get_jwt_identity()['user_id']
    data = request.get_json()
    
    # Validate alert configuration
    required_fields = ['name', 'condition_type', 'operator', 'threshold']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
        
    # Create alert
    current_app.config['alert_manager'].create_alert_rule(user_id, data)
    
    return jsonify({'message': 'Alert rule created successfully'}), 201
