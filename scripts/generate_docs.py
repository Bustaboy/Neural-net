# scripts/generate_docs.py
import inspect
import ast
from typing import Dict, List

class DocGenerator:
    def generate_api_docs(self, app):
        """Generate API documentation from Flask routes"""
        docs = []
        
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':
                func = app.view_functions[rule.endpoint]
                docs.append({
                    'endpoint': rule.rule,
                    'methods': list(rule.methods),
                    'description': inspect.getdoc(func),
                    'parameters': self._extract_parameters(func)
                })
                
        return self._format_markdown(docs)
    
    def generate_ml_docs(self, ml_module):
        """Generate ML pipeline documentation"""
        classes = inspect.getmembers(ml_module, inspect.isclass)
        
        docs = {
            'models': [],
            'features': [],
            'pipelines': []
        }
        
        for name, cls in classes:
            docs['models'].append({
                'name': name,
                'description': inspect.getdoc(cls),
                'methods': self._extract_methods(cls)
            })
            
        return docs
