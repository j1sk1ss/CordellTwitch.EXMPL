import os
import requests
import subprocess
from tqdm import tqdm


ACCESS_TOKEN = ""
GROUP_ID = ""
SAVE_FOLDER = "/mnt/external_disk/"
USE_YT_DLP = subprocess.run(["which", "yt-dlp"], capture_output=True).returncode == 0
os.makedirs(SAVE_FOLDER, exist_ok=True)


def get_videos():
    url = "https://api.vk.com/method/video.get"
    params = {
        "owner_id": f"-{GROUP_ID}",
        "count": 200,
        "access_token": ACCESS_TOKEN,
        "v": "5.199"
    }
    response = requests.get(url, params=params).json()
    
    if "error" in response:
        print(f"Error: {response['error']['error_msg']}")
        return []

    return response.get("response", {}).get("items", [])

def download_video(video):
    title = video["title"].replace("/", "_").replace("\\", "_").replace(":", "_")
    best_quality_url = None

    files = video.get("files", {})
    for quality in ["mp4_1080", "mp4_720", "mp4_480", "mp4_360", "mp4_240"]:
        if files.get(quality):
            best_quality_url = files[quality]
            break

    if not best_quality_url and USE_YT_DLP:
        vk_url = f"https://vk.com/video_ext.php?oid={video['owner_id']}&id={video['id']}"
        print(f"Downloading {title} using yt-dlp...")
        subprocess.run(["yt-dlp", "-o", f"{SAVE_FOLDER}/{title}.mp4", vk_url])
        return

    if not best_quality_url:
        print(f"Skipping {title}, no valid URL found.")
        return

    response = requests.get(best_quality_url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    filepath = os.path.join(SAVE_FOLDER, f"{title}.mp4")

    with open(filepath, "wb") as file, tqdm(
        desc=f"Downloading {title}",
        total=total_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for chunk in response.iter_content(1024):
            file.write(chunk)
            bar.update(len(chunk))

    print(f"Saved: {filepath}")

if __name__ == "__main__":
    videos = get_videos()
    if not videos:
        print("No videos found or access denied.")
    else:
        for video in videos[27:]:
            download_video(video)
