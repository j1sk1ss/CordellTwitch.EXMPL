import os
import re
import uuid
import shutil
import datetime

from crypto import (
    encrypt_video,
    decrypt_video
)

from functools import wraps
from flask import (
    Flask, 
    Response, 
    request, 
    jsonify, 
    render_template,
    send_from_directory
)


# region Setup

video_tokens = {}
app = Flask(__name__, template_folder="static", static_folder="static")
VIDEO_DIR = "." # set video directory
KEY_DIR = "static\\data\\keys.txt"
ENCRYPT_KEY = os.urandom(32)

def _load_keys():
    try:
        with open(KEY_DIR, "r") as f:
            return set(line.strip() for line in f.readlines())
    except FileNotFoundError:
        return set()

ACCESS_KEYS = _load_keys()

def require_authorization(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_key = request.headers.get("Authorization")
        if not auth_key or auth_key not in ACCESS_KEYS:
            return jsonify({"error": "Unauthorized"}), 403
        
        return f(*args, **kwargs)
    return wrapper

# endregion

@app.route("/")
def _index():
    return render_template("index.html")


@app.route("/videos", methods=["GET"])
@require_authorization
def _list_videos():
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 10))
    query = request.args.get("query", "").lower()

    videos = [
        f for f in os.listdir(VIDEO_DIR)
        if f.endswith(".mp4")
    ]
    
    if query:
        videos = [video for video in videos if query in video.lower()]

    video_data = []
    for video in videos[offset:offset + limit]:
        video_path = os.path.join(VIDEO_DIR, video)
        creation_date = os.path.getctime(video_path)
        creation_date = datetime.datetime.fromtimestamp(creation_date).isoformat()
        video_data.append({
            "name": video,
            "creation_date": creation_date
        })

    return jsonify(video_data)


@app.route("/videos/count", methods=["GET"])
@require_authorization
def _videos_count():
    query = request.args.get("query", "").lower()
    videos = [f for f in os.listdir(VIDEO_DIR) if f.endswith(".mp4")]
    if query:
        videos = [video for video in videos if query in video.lower()]
        
    return jsonify({"count": len(videos)})


@app.route("/generate-token", methods=["POST"])
@require_authorization
def _generate_token():
    data: dict = request.json
    video_name = data.get("video_name")
    
    if not video_name:
        return jsonify({"error": "Video name is required"}), 400
    
    video_path = os.path.join(VIDEO_DIR, video_name)
    if not os.path.exists(video_path):
        return jsonify({"error": "Video not found"}), 404
    
    token = str(uuid.uuid4())
    video_tokens[token] = video_name

    return jsonify({"success": True, "token": token})


@app.route("/private-video", methods=["GET"])
def _get_private_video():
    token = request.args.get("token")
    if token not in video_tokens:
        return jsonify({"error": "Invalid token"}), 400
    
    video_path = os.path.join(VIDEO_DIR, video_tokens.get(token))
    creation_date = os.path.getctime(video_path)
    creation_date = datetime.datetime.fromtimestamp(creation_date).isoformat()
    return {
        "success": True,
        "name": video_tokens.get(token),
        "creation_date": creation_date
    }


@app.route("/video:download/<filename>", methods=["GET"])
def _download_video(filename):
    try:
        video_path = os.path.join(VIDEO_DIR, filename)
        if not os.path.exists(video_path):
            return jsonify({"error": "File not found"}), 404

        return send_from_directory(VIDEO_DIR, filename, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/video/<filename>", methods=["GET"])
def _stream_video(filename):
    file_path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("Range", None)

    def _generate(start, length):
        decrypted_chunk = decrypt_video(file_path=file_path, start=start, length=length, key=ENCRYPT_KEY)
        yield decrypted_chunk

    if range_header:
        range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            length = end - start + 1

            response: Response = Response(_generate(start, length), status=206, mimetype="video/mp4")
            response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
            response.headers.add("Accept-Ranges", "bytes")
            response.headers.add("Content-Length", str(length))
            return response

    response: Response = Response(_generate(0, file_size), mimetype="video/mp4")
    response.headers.add("Content-Length", str(file_size))
    response.headers.add("Accept-Ranges", "bytes")
    return response


@app.route("/upload", methods=["POST"])
@require_authorization
def _upload_video():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    
    file_path = os.path.join(VIDEO_DIR, request.form["title"])
    file.save(file_path)
    encrypt_video(file_path=file_path, key=ENCRYPT_KEY)
    return jsonify({"success": True, "filename": os.path.join(VIDEO_DIR, request.form["title"])})


@app.route('/delete-video', methods=['POST'])
@require_authorization
def _delete_video():
    data: dict = request.json
    video_name = data.get('video_name')

    if not video_name:
        return jsonify({'success': False, 'error': 'Video name is required'}), 400

    video_path = os.path.join(VIDEO_DIR, video_name)

    if os.path.exists(video_path):
        try:
            os.remove(video_path)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Video not found'}), 404


@app.route("/rename-video", methods=["POST"])
@require_authorization
def _rename_video():
    data: dict = request.json
    old_name = data.get("old_name")
    new_name = data.get("new_name")
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


if __name__ == "__main__":
    os.makedirs(VIDEO_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
