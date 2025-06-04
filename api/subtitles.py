import os
import tempfile
import subprocess
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Path to the bundled yt-dlp binary
YT_DLP_PATH = os.path.join(os.path.dirname(__file__), 'yt-dlp')

@app.route('/api/subtitles', methods=['GET'])
def get_subtitles():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({'error': 'URL parameter is required'}), 400

    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Prepare command
            cmd = [
                YT_DLP_PATH,
                '--skip-download',
                '--write-subs',
                '--write-auto-subs',
                '--sub-lang', 'en',
                '--sub-format', 'json',  # Using JSON format for easier parsing
                '--convert-subs', 'json',
                '--output', f'{tmp_dir}/subtitle',
                '--no-warnings',
                video_url
            ]

            # Execute yt-dlp
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return jsonify({
                    'error': 'Failed to extract subtitles',
                    'details': result.stderr
                }), 500

            # Find the subtitle file
            subtitle_file = None
            for f in os.listdir(tmp_dir):
                if f.endswith('.json'):
                    subtitle_file = os.path.join(tmp_dir, f)
                    break

            if not subtitle_file:
                return jsonify({'error': 'No subtitles found'}), 404

            # Read and process subtitles
            with open(subtitle_file, 'r') as f:
                subtitles = json.load(f)
                formatted = '\n'.join([entry['text'] for entry in subtitles])

            return jsonify({
                'subtitles': formatted,
                'raw': subtitles
            })

    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Processing timed out'}), 504
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Vercel handler
def handler(request):
    from io import BytesIO
    environ = {
        'REQUEST_METHOD': request.method,
        'PATH_INFO': request.path,
        'QUERY_STRING': request.query_string.decode(),
        'wsgi.input': BytesIO(),
        'wsgi.errors': BytesIO(),
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https'
    }
    
    headers = []
    
    def start_response(status, response_headers):
        nonlocal headers
        headers = response_headers
        return BytesIO().write
    
    response = app(environ, start_response)
    
    return {
        'statusCode': 200,
        'headers': dict(headers),
        'body': b''.join(response).decode()
    }
