"""
============================================
Audit Log Model - MongoDB
============================================

Handles audit logging for admin actions
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId

from database import get_collection


class AuditLog:
    """Audit log model class"""
    
    collection_name = 'audit_logs'
    
    VALID_ACTIONS = [
        'LOGIN',
        'LOGOUT',
        'USER_CREATE',
        'USER_UPDATE',
        'USER_DELETE',
        'USER_SUSPEND',
        'CONTENT_CREATE',
        'CONTENT_UPDATE',
        'CONTENT_DELETE',
        'LEARNING_PATH_UPDATE',
        'REPORT_GENERATED',
        'SETTINGS_UPDATE',
        'ADMIN_CREATE',
        'ADMIN_UPDATE',
        'ADMIN_DELETE',
        'ROLE_UPDATE',
        'PERMISSION_UPDATE',
        'EXPORT_DATA',
        'LOGIN_FAILED',
        'UNAUTHORIZED_ACCESS',
        'OTHER'
    ]
    
    VALID_STATUSES = ['success', 'failure', 'warning']
    
    @staticmethod
    def get_collection():
        """Get the audit_logs collection"""
        return get_collection(AuditLog.collection_name)
    
    @staticmethod
    def create(log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new audit log entry
        
        Args:
            log_data: Dictionary containing log data
            
        Returns:
            Created log document
        """
        collection = AuditLog.get_collection()
        
        log = {
            'admin': log_data.get('admin'),  # ObjectId or None
            'action': log_data.get('action'),
            'resource': log_data.get('resource'),
            'resourceId': log_data.get('resourceId'),
            'description': log_data.get('description'),
            'changes': log_data.get('changes'),
            'ipAddress': log_data.get('ipAddress'),
            'userAgent': log_data.get('userAgent'),
            'status': log_data.get('status', 'success'),
            'details': log_data.get('details'),
            'createdAt': datetime.utcnow()
        }
        
        result = collection.insert_one(log)
        log['_id'] = result.inserted_id
        
        return log
    
    @staticmethod
    def find_by_id(log_id: str) -> Optional[Dict[str, Any]]:
        """Find a log entry by ID"""
        collection = AuditLog.get_collection()
        log = collection.find_one({'_id': ObjectId(log_id)})
        
        if log:
            log = AuditLog._populate_admin(log)
        
        return log
    
    @staticmethod
    def _populate_admin(log: Dict[str, Any]) -> Dict[str, Any]:
        """Populate admin reference"""
        if log.get('admin'):
            from models.admin import Admin
            admin = Admin.find_by_id(str(log['admin']))
            if admin:
                log['admin'] = {
                    'id': str(admin['_id']),
                    'name': admin.get('name'),
                    'email': admin.get('email')
                }
        return log
    
    @staticmethod
    def find_many(
        filter_query: Dict = None, 
        skip: int = 0, 
        limit: int = 10,
        populate_admin: bool = True
    ) -> List[Dict[str, Any]]:
        """Find multiple log entries with pagination"""
        collection = AuditLog.get_collection()
        
        cursor = collection.find(filter_query or {}).sort('createdAt', -1).skip(skip).limit(limit)
        logs = list(cursor)
        
        if populate_admin:
            logs = [AuditLog._populate_admin(log) for log in logs]
        
        return logs
    
    @staticmethod
    def count(filter_query: Dict = None) -> int:
        """Count log entries matching filter"""
        collection = AuditLog.get_collection()
        return collection.count_documents(filter_query or {})
    
    @staticmethod
    def aggregate(pipeline: List[Dict]) -> List[Dict]:
        """Run aggregation pipeline"""
        collection = AuditLog.get_collection()
        return list(collection.aggregate(pipeline))
    
    @staticmethod
    def get_action_stats(days: int = 7) -> List[Dict]:
        """Get action statistics for last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {'$match': {'createdAt': {'$gte': start_date}}},
            {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        
        return AuditLog.aggregate(pipeline)
    
    @staticmethod
    def get_resource_stats(days: int = 7) -> List[Dict]:
        """Get resource statistics for last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {'$match': {'createdAt': {'$gte': start_date}}},
            {'$group': {'_id': '$resource', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        
        return AuditLog.aggregate(pipeline)
    
    @staticmethod
    def get_status_stats(days: int = 7) -> List[Dict]:
        """Get status statistics for last N days"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        pipeline = [
            {'$match': {'createdAt': {'$gte': start_date}}},
            {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
        ]
        
        return AuditLog.aggregate(pipeline)
    
    @staticmethod
    def to_response(log: Dict[str, Any]) -> Dict[str, Any]:
        """Convert log document to API response"""
        if not log:
            return None
        
        return {
            'id': str(log['_id']),
            'admin': log.get('admin'),
            'action': log.get('action'),
            'resource': log.get('resource'),
            'resourceId': str(log['resourceId']) if log.get('resourceId') else None,
            'description': log.get('description'),
            'changes': log.get('changes'),
            'ipAddress': log.get('ipAddress'),
            'userAgent': log.get('userAgent'),
            'status': log.get('status'),
            'details': log.get('details'),
            'createdAt': log.get('createdAt')
        }
