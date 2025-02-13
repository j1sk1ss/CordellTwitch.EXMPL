from flask import Flask, request, jsonify, send_file, Response, render_template
import os
import shutil
import subprocess


app = Flask(__name__, template_folder='static', static_folder='static')
VIDEO_DIR = '/mnt/external_disk/'


def _load_keys():
    try:
        with open("keys.txt", "r") as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()

ACCESS_KEYS = _load_keys()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/videos', methods=['GET'])
def list_videos():
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 10))
    videos = [f for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')]
    return jsonify(videos[offset:offset+limit])


@app.route('/video/<filename>', methods=['GET'])
def stream_video(filename):
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    def generate():
        with open(file_path, 'rb') as f:
            while chunk := f.read(4096):
                yield chunk
    
    return Response(generate(), mimetype='video/mp4')


@app.route('/streams_src/<filename>', methods=['GET'])
def stream_src(filename):
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(file_path, mimetype='video/mp4')


@app.route('/upload', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    file_path = os.path.join(VIDEO_DIR, file.filename)
    file.save(file_path)
    return jsonify({"success": True, "filename": file.filename})


@app.route('/rename-video', methods=['POST'])
def rename_video():
    data = request.json
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    
    old_path = os.path.join(VIDEO_DIR, old_name)
    new_path = os.path.join(VIDEO_DIR, new_name)
    
    if not os.path.exists(old_path):
        return jsonify({"error": "File not found"}), 404
    
    shutil.move(old_path, new_path)
    return jsonify({"success": True})


@app.route("/check_key", methods=["POST"])
def check_key():
    data = request.json
    key = data.get("key")

    if key in ACCESS_KEYS:
        return jsonify({"access": "granted"})
    return jsonify({"access": "denied"}), 403


@app.route('/stream', methods=['POST'])
def start_stream():
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
