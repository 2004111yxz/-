from flask import Blueprint, request, jsonify

from src.services.video_service import VideoService, TaskStatus
from src.services.user_service import UserService

video_bp = Blueprint('video', __name__)

video_service = VideoService()
user_service = UserService()

@video_bp.route('/v1/videos/generations', methods=['POST'])
def create_video_task():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer sk-'):
        return jsonify({"error": {"message": "Invalid API Key"}}), 401
    
    api_key = auth.replace('Bearer ', '').strip()
    
    user = user_service.get_user_by_api_key(api_key)
    if not user:
        return jsonify({"error": {"message": "API Key not found or disabled"}}), 401
    
    body = request.json
    if not body:
        return jsonify({"error": {"message": "Empty request body"}}), 400
    
    prompt = body.get('prompt')
    if not prompt:
        return jsonify({"error": {"message": "Prompt is required"}}), 400
    
    try:
        task_id = video_service.create_task(
            user_id=user['id'],
            prompt=prompt,
            negative_prompt=body.get('negative_prompt'),
            style=body.get('style'),
            duration=body.get('duration'),
            resolution=body.get('resolution'),
            reference_url=body.get('reference_url'),
            extra_params=body.get('extra_params'),
            webhook_url=body.get('webhook_url')
        )
        
        return jsonify({
            'task_id': task_id,
            'status': 'pending',
            'message': 'Task created successfully'
        }), 201
    except Exception as e:
        return jsonify({"error": {"message": str(e)}}), 500

@video_bp.route('/v1/videos/generations/<task_id>', methods=['GET'])
def get_video_task(task_id):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer sk-'):
        return jsonify({"error": {"message": "Invalid API Key"}}), 401
    
    api_key = auth.replace('Bearer ', '').strip()
    
    user = user_service.get_user_by_api_key(api_key)
    if not user:
        return jsonify({"error": {"message": "API Key not found or disabled"}}), 401
    
    task = video_service.get_task(task_id)
    if not task:
        return jsonify({"error": {"message": "Task not found"}}), 404
    
    if task['user_id'] != user['id']:
        return jsonify({"error": {"message": "Access denied"}}), 403
    
    return jsonify({
        'task_id': task['task_id'],
        'prompt': task['prompt'],
        'negative_prompt': task['negative_prompt'],
        'style': task['style'],
        'duration': task['duration'],
        'resolution': task['resolution'],
        'status': task['status'],
        'progress': task['progress'],
        'result_url': task['result_url'],
        'error_message': task['error_message'],
        'created_at': task['created_at'],
        'updated_at': task['updated_at']
    }), 200

@video_bp.route('/v1/videos/generations/<task_id>', methods=['DELETE'])
def cancel_video_task(task_id):
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer sk-'):
        return jsonify({"error": {"message": "Invalid API Key"}}), 401
    
    api_key = auth.replace('Bearer ', '').strip()
    
    user = user_service.get_user_by_api_key(api_key)
    if not user:
        return jsonify({"error": {"message": "API Key not found or disabled"}}), 401
    
    task = video_service.get_task(task_id)
    if not task:
        return jsonify({"error": {"message": "Task not found"}}), 404
    
    if task['user_id'] != user['id']:
        return jsonify({"error": {"message": "Access denied"}}), 403
    
    success = video_service.cancel_task(task_id)
    if not success:
        return jsonify({"error": {"message": "Cannot cancel task in current state"}}), 400
    
    return jsonify({'message': 'Task cancelled successfully'}), 200

@video_bp.route('/v1/videos/generations', methods=['GET'])
def list_video_tasks():
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer sk-'):
        return jsonify({"error": {"message": "Invalid API Key"}}), 401
    
    api_key = auth.replace('Bearer ', '').strip()
    
    user = user_service.get_user_by_api_key(api_key)
    if not user:
        return jsonify({"error": {"message": "API Key not found or disabled"}}), 401
    
    limit = int(request.args.get('limit', 50))
    tasks = video_service.get_user_tasks(user['id'], limit)
    
    return jsonify([{
        'task_id': task['task_id'],
        'prompt': task['prompt'],
        'status': task['status'],
        'progress': task['progress'],
        'created_at': task['created_at']
    } for task in tasks]), 200
