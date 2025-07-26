from flask import Flask, jsonify, Response, request
import pandas as pd
import requests
import time

app = Flask(__name__)

MAPPING_FILE = 'mapping.xlsx'
RAPIDAPI_HOST = 'yt-api.p.rapidapi.com'
RAPIDAPI_KEY = '36823397e2msh195c3184061ad92p1085d7jsn9c3fb06c518f'

# Đọc mapping

def load_mapping():
    df = pd.read_excel(MAPPING_FILE)
    mapping = []
    for _, row in df.iterrows():
        channel_id = str(row.get('channel_id', row.get('youtube_url')))
        profile_id = str(row['profile_id'])
        mapping.append((channel_id, profile_id))
    return mapping

# Lấy video shorts mới nhất qua RapidAPI

def get_latest_shorts(channel_id):
    url = f'https://yt-api.p.rapidapi.com/channel/videos?id={channel_id}&type=shorts'
    headers = {
        'x-rapidapi-host': RAPIDAPI_HOST,
        'x-rapidapi-key': RAPIDAPI_KEY
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if 'data' in data and data['data']:
            return data['data'][0]  # Video shorts mới nhất
        return None
    except Exception as e:
        return {'error': str(e)}

@app.route('/api/latest_shorts', methods=['GET'])
def api_latest_shorts():
    mapping = load_mapping()
    result = []
    for channel_id, profile_id in mapping:
        video = get_latest_shorts(channel_id)
        result.append({
            'channel_id': channel_id,
            'profile_id': profile_id,
            'latest_shorts': video
        })
    return jsonify(result)

@app.route('/api/latest_shorts/<channel_id>', methods=['GET'])
def api_latest_shorts_channel(channel_id):
    loop = request.args.get('loop', '0') == '1'
    if not loop:
        video = get_latest_shorts(channel_id)
        return jsonify({
            'channel_id': channel_id,
            'latest_shorts': video
        })
    def event_stream():
        last_video_id = None
        while True:
            video = get_latest_shorts(channel_id)
            video_id = video.get('videoId') if video else None
            if video_id != last_video_id:
                yield f'data: {jsonify({"channel_id": channel_id, "latest_shorts": video}).get_data(as_text=True)}\n\n'
                last_video_id = video_id
            time.sleep(1)
    return Response(event_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(port=5001, debug=True) 