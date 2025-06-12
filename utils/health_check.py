# utils/health_check.py
from typing import Dict, List
import asyncio

class HealthCheckSystem:
    def __init__(self):
        self.checks = {}
        
    def register_check(self, name: str, check_func, critical: bool = True):
        """Register a health check"""
        self.checks[name] = {
            'func': check_func,
            'critical': critical,
            'status': 'unknown',
            'last_check': None
        }
        
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {
            'status': 'healthy',
            'checks': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for name, check in self.checks.items():
            try:
                result = await check['func']() if asyncio.iscoroutinefunction(check['func']) else check['func']()
                self.checks[name]['status'] = 'healthy' if result else 'unhealthy'
                results['checks'][name] = {
                    'status': self.checks[name]['status'],
                    'critical': check['critical']
                }
                
                if not result and check['critical']:
                    results['status'] = 'unhealthy'
                    
            except Exception as e:
                self.checks[name]['status'] = 'error'
                results['checks'][name] = {
                    'status': 'error',
                    'error': str(e),
                    'critical': check['critical']
                }
                if check['critical']:
                    results['status'] = 'unhealthy'
                    
        return results

# Example health checks
health_system = HealthCheckSystem()

health_system.register_check('database', lambda: db_manager.execute("SELECT 1"))
health_system.register_check('redis', lambda: redis_client.ping())
health_system.register_check('model_loaded', lambda: trainer.model is not None)
health_system.register_check('api_responsive', lambda: requests.get('http://localhost:5000/health').ok)
