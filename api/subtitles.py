import os
import tempfile
import subprocess
import json
from http.server import BaseHTTPRequestHandler
from io import BytesIO

YT_DLP_PATH = os.path.join(os.path.dirname(__file__), 'yt-dlp')

def handle_subtitles(video_url):
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cmd = [
                YT_DLP_PATH,
                '--skip-download',
                '--write-subs',
                '--write-auto-subs',
                '--sub-lang', 'en',
                '--sub-format', 'json',
                '--convert-subs', 'json',
                '--output', f'{tmp_dir}/subtitle',
                '--no-warnings',
                video_url
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20
            )

            if result.returncode != 0:
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': 'Failed to extract subtitles',
                        'details': result.stderr
                    })
                }

            for f in os.listdir(tmp_dir):
                if f.endswith('.json'):
                    with open(os.path.join(tmp_dir, f), 'r') as sub_file:
                        subtitles = json.load(sub_file)
                        formatted = '\n'.join([entry['text'] for entry in subtitles])
                        return {
                            'statusCode': 200,
                            'body': json.dumps({
                                'subtitles': formatted,
                                'raw': subtitles
                            })
                        }

            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'No subtitles found'})
            }

    except subprocess.TimeoutExpired:
        return {
            'statusCode': 504,
            'body': json.dumps({'error': 'Processing timed out'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handler(request, context):
    video_url = request.get('queryStringParameters', {}).get('url')
    
    if not video_url:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'URL parameter is required'})
        }

    return handle_subtitles(video_url)
