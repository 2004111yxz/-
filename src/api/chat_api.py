from flask import Blueprint, request, Response, jsonify

from src.services.chat_service import ChatService
from src.services.user_service import UserService

chat_bp = Blueprint('chat', __name__)

chat_service = ChatService()
user_service = UserService()

@chat_bp.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
def chat_completions():
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
            'Access-Control-Allow-Headers': '*'
        }
    
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer sk-'):
        return jsonify({"error": {"message": "Invalid API Key"}}), 401, {'Access-Control-Allow-Origin': '*'}
    
    api_key = auth.replace('Bearer ', '').strip()
    
    user = user_service.get_user_by_api_key(api_key)
    if not user:
        return jsonify({"error": {"message": "API Key not found or disabled"}}), 401, {'Access-Control-Allow-Origin': '*'}
    
    body = request.json
    if not body:
        return jsonify({"error": {"message": "Empty request body"}}), 400, {'Access-Control-Allow-Origin': '*'}
    
    model_name = body.get('model', 'gpt-3.5-turbo')
    is_streaming = body.get('stream', False)
    
    if is_streaming:
        def generate():
            for chunk in chat_service.chat_completion_stream(user['id'], model_name, body):
                yield chunk
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Headers': '*',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
    else:
        success, response, error = chat_service.chat_completion(user['id'], model_name, body)
        if not success:
            return jsonify({"error": {"message": error}}), 500, {'Access-Control-Allow-Origin': '*'}
        return jsonify(response), 200, {'Access-Control-Allow-Origin': '*'}
