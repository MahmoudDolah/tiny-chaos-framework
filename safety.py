# safety.py
import os
import socket
import re

class SafetyChecker:
    def __init__(self):
        # Load production environment identifiers
        self.prod_identifiers = self._load_prod_identifiers()
    
    def _load_prod_identifiers(self):
        # This could be loaded from a config file
        return ["prod", "production", "prd"]
    
    def is_safe_to_run(self, experiment):
        # Check environment tags
        if self._is_production_environment(experiment['target']['environment']):
            return False
        
        # Check for protected services
        if self._is_protected_service(experiment['target']['service']):
            return False
            
        # Validate experiment parameters
        if not self._has_safe_parameters(experiment):
            return False
            
        return True
    
    def _is_production_environment(self, env_name):
        for prod_id in self.prod_identifiers:
            if prod_id in env_name.lower():
                return True
        return False
    
    def _is_protected_service(self, service_name):
        protected_services = ["database", "auth", "payment"]
        return any(ps in service_name.lower() for ps in protected_services)
    
    def _has_safe_parameters(self, experiment):
        # Check if experiment duration is reasonable
        if experiment.get('duration', 0) > 600:  # Max 10 minutes
            return False
            
        # Other parameter safety checks
        return True
