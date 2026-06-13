from flask import Flask, request, Response
import json
import requests

app = Flask(__name__)

@app.route('/test', methods=['POST'])
def test():
    data = request.json
    print(f"Received data: {data}")
    return {"status": "ok", "data": data}

@app.route('/stream', methods=['POST'])
def stream():
    data = request.json
    is_stream = data.get('stream', False)
    print(f"Stream request: {is_stream}")
    
    if is_stream:
        def generate():
            for i in range(3):
                yield f"data: {json.dumps({'chunk': i})}\n\n"
            yield "data: [DONE]\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    else:
        return {"status": "ok", "message": "non-stream"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)