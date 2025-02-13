import os
import re
import shutil
import datetime
import subprocess

from flask import (
    Flask, 
    Response, 
    request, 
    jsonify, 
    render_template,
    send_from_directory
)


app = Flask(__name__, template_folder='static', static_folder='static')
VIDEO_DIR = '/Users/nikolaj/Downloads'


def _load_keys():
    try:
        with open("keys.txt", "r") as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()

ACCESS_KEYS = _load_keys()


@app.route('/')
def _index():
    return render_template('index.html')


@app.route('/videos', methods=['GET'])
def _list_videos():
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 10))
    query = request.args.get("query", "").lower()

    videos = [
        f for f in os.listdir(VIDEO_DIR)
        if f.endswith('.mp4')
    ]
    
    if query:
        videos = [video for video in videos if query in video.lower()]

    video_data = []
    for video in videos[offset:offset + limit]:
        video_path = os.path.join(VIDEO_DIR, video)
        creation_date = os.path.getctime(video_path)
        creation_date = datetime.datetime.fromtimestamp(creation_date).isoformat()
        video_data.append({
            'name': video,
            'creation_date': creation_date
        })

    return jsonify(video_data)


@app.route('/videos/count', methods=['GET'])
def _videos_count():
    videos = [f for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')]
    return jsonify({"count": len(videos)})


@app.route('/video:download/<filename>', methods=['GET'])
def download_video(filename):
    try:
        video_path = os.path.join(VIDEO_DIR, filename)
        if not os.path.exists(video_path):
            return jsonify({"error": "File not found"}), 404

        return send_from_directory(VIDEO_DIR, filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/video/<filename>', methods=['GET'])
def _stream_video(filename):
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)

    def generate(start, length):
        with open(file_path, 'rb') as f:
            f.seek(start)
            while length > 0:
                chunk = f.read(min(4096, length))
                if not chunk:
                    break
                yield chunk
                length -= len(chunk)

    if range_header:
        range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            length = end - start + 1

            response = Response(generate(start, length), status=206, mimetype='video/mp4')
            response.headers.add('Content-Range', f'bytes {start}-{end}/{file_size}')
            response.headers.add('Accept-Ranges', 'bytes')
            response.headers.add('Content-Length', str(length))
            return response

    response = Response(generate(0, file_size), mimetype='video/mp4')
    response.headers.add('Content-Length', str(file_size))
    response.headers.add('Accept-Ranges', 'bytes')
    return response


@app.route('/upload', methods=['POST'])
def _upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    file_path = os.path.join(VIDEO_DIR, request.form['title'])
    file.save(file_path)
    return jsonify({"success": True, "filename": os.path.join(VIDEO_DIR, request.form['title'])})


@app.route('/rename-video', methods=['POST'])
def _rename_video():
    data: dict = request.json
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    old_path = os.path.join(VIDEO_DIR, old_name)
    new_path = os.path.join(VIDEO_DIR, new_name)
    
    if not os.path.exists(old_path):
        return jsonify({"error": "File not found", "old_name": old_name}), 404
    
    shutil.move(old_path, new_path)
    return jsonify({"success": True})


@app.route("/check_key", methods=["POST"])
def _check_key():
    data: dict = request.json
    key = data.get("key")

    if key in ACCESS_KEYS:
        return jsonify({"access": "granted"})
    
    return jsonify({"access": "denied"}), 403


@app.route('/stream', methods=['POST'])
def _start_stream():
    stream_key = request.args.get('key')
    output_path = os.path.join(VIDEO_DIR, f'{stream_key}.mp4')
    command = [
        'ffmpeg', '-i', f'rtmp://localhost/live/{stream_key}',
        '-c:v', 'copy', '-c:a', 'copy', output_path
    ]
    
    subprocess.Popen(command)
    return jsonify({"success": True, "message": "Stream recording started."})


if __name__ == '__main__':
    os.makedirs(VIDEO_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
