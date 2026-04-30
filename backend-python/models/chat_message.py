"""
============================================
Chat Message Model - MongoDB
============================================

Stores 1:1 direct messages between platform users.
"""

from datetime import datetime
from typing import Dict, Any, List

from bson import ObjectId

from database import get_collection


class ChatMessage:
    """Chat message model class"""

    collection_name = 'chat_messages'

    @staticmethod
    def get_collection():
        return get_collection(ChatMessage.collection_name)

    @staticmethod
    def create(sender_id: str, receiver_id: str, text: str) -> Dict[str, Any]:
        collection = ChatMessage.get_collection()

        message = {
            'senderId': ObjectId(sender_id),
            'receiverId': ObjectId(receiver_id),
            'text': text.strip(),
            'readAt': None,
            'createdAt': datetime.utcnow(),
            'updatedAt': datetime.utcnow(),
        }

        result = collection.insert_one(message)
        message['_id'] = result.inserted_id
        return message

    @staticmethod
    def get_conversation(user_a_id: str, user_b_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        collection = ChatMessage.get_collection()

        user_a = ObjectId(user_a_id)
        user_b = ObjectId(user_b_id)

        cursor = collection.find({
            '$or': [
                {'senderId': user_a, 'receiverId': user_b},
                {'senderId': user_b, 'receiverId': user_a},
            ]
        }).sort('createdAt', 1).limit(limit)

        return list(cursor)

    @staticmethod
    def get_last_message(user_a_id: str, user_b_id: str) -> Dict[str, Any] | None:
        collection = ChatMessage.get_collection()

        user_a = ObjectId(user_a_id)
        user_b = ObjectId(user_b_id)

        return collection.find_one(
            {
                '$or': [
                    {'senderId': user_a, 'receiverId': user_b},
                    {'senderId': user_b, 'receiverId': user_a},
                ]
            },
            sort=[('createdAt', -1)]
        )

    @staticmethod
    def count_unread(sender_id: str, receiver_id: str) -> int:
        collection = ChatMessage.get_collection()
        return collection.count_documents({
            'senderId': ObjectId(sender_id),
            'receiverId': ObjectId(receiver_id),
            'readAt': None,
        })

    @staticmethod
    def mark_conversation_read(reader_id: str, contact_id: str) -> int:
        collection = ChatMessage.get_collection()
        result = collection.update_many(
            {
                'senderId': ObjectId(contact_id),
                'receiverId': ObjectId(reader_id),
                'readAt': None,
            },
            {
                '$set': {
                    'readAt': datetime.utcnow(),
                    'updatedAt': datetime.utcnow(),
                }
            }
        )
        return result.modified_count

    @staticmethod
    def to_response(message: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'id': str(message['_id']),
            'sender_id': str(message['senderId']),
            'receiver_id': str(message['receiverId']),
            'text': message.get('text', ''),
            'is_read': message.get('readAt') is not None,
            'created_at': message.get('createdAt').isoformat() if message.get('createdAt') else None,
            'updated_at': message.get('updatedAt').isoformat() if message.get('updatedAt') else None,
        }
