let currentFilter = ""

let loadedVideos = 0;
const batchSize = 6;
let allVideos = [];
let limit = 10;

let totalVideos = 0;
let currentPage = 0;


async function getVideoDate(url) {
    let response = await fetch(url, { method: 'HEAD' });
    let lastModified = response.headers.get('Last-Modified');
    return lastModified ? new Date(lastModified).getTime() : 0;
}


function filterVideos(query) {
    let videoItems = document.querySelectorAll('.video-item');
    videoItems.forEach(item => {
        let title = item.querySelector('span').textContent.toLowerCase();
        item.style.display = title.includes(query) ? 'flex' : 'none';
    });
}


function nextPage() {
    if (currentPage < totalPages - 1) {
        currentPage++;
        loadVideos();
    }
}


function prevPage() {
    if (currentPage > 0) {
        currentPage--;
        loadVideos();
    }
}


function updatePagination() {
    let pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    let prevButton = document.createElement('button');
    prevButton.textContent = "Prev";
    prevButton.disabled = currentPage <= 0;
    prevButton.onclick = prevPage;
    pagination.appendChild(prevButton);

    let pageButton = document.createElement('button');
    pageButton.textContent = `${currentPage + 1} / ${totalPages + 1}`;
    pagination.appendChild(pageButton);

    let nextButton = document.createElement('button');
    nextButton.textContent = "Next";
    nextButton.disabled = currentPage >= totalPages - 1;
    nextButton.onclick = nextPage;
    pagination.appendChild(nextButton);
}


async function loadVideos() {
    let list = document.getElementById('video-list');
    list.innerHTML = "";

    let countResponse = await fetch(`/videos/count?query=${currentFilter}`);
    let countData = await countResponse.json();
    totalVideos = countData.count;
    totalPages = Math.ceil(totalVideos / limit);

    const offset = currentPage * limit;
    let response = await fetch(`/videos?offset=${offset}&limit=${limit}&query=${currentFilter}`);
    let videoData = await response.json();

    allVideos = [];
    for (let video of videoData) {
        let url = `/video/${video.name}`;
        let displayName = video.name;
        let lastModified = video.creation_date;
        
        allVideos.push({ url, displayName, lastModified });
    }

    allVideos.sort((a, b) => new Date(b.lastModified) - new Date(a.lastModified));

    loadedVideos = 0;
    renderNextBatch();
    updatePagination();
}


function selectVideo(url, displayName, lastModified) {
    let videoPlayer = document.getElementById('player');
    let videoSource = document.getElementById('video-source');
    
    videoSource.src = url;
    videoPlayer.load();
    videoPlayer.play();
    
    let videoTitle = document.getElementById('video-title');
    let videoDate = document.getElementById('video-date');
    videoTitle.textContent = displayName;
    videoDate.textContent = new Date(lastModified).toLocaleDateString();
}


function renderNextBatch() {
    let list = document.getElementById('video-list');
    let fragment = document.createDocumentFragment();

    for (let i = loadedVideos; i < Math.min(loadedVideos + batchSize, allVideos.length); i++) {
        let { url, displayName, lastModified } = allVideos[i];
        let div = document.createElement('div');
        div.className = "video-item";
        div.setAttribute("data-video", url);

        let canvas = document.createElement('canvas');
        canvas.width = 80;
        canvas.height = 45;

        let span = document.createElement('span');
        span.textContent = displayName;

        let dateSpan = document.createElement('span');
        dateSpan.style.marginLeft = "auto";
        dateSpan.style.fontSize = "12px";
        dateSpan.style.color = "#aaa";
        dateSpan.textContent = new Date(lastModified).toLocaleDateString();

        div.appendChild(canvas);
        div.appendChild(span);
        div.appendChild(dateSpan);
        fragment.appendChild(div);

        div.onclick = () => selectVideo(url, displayName, lastModified);
    }

    list.appendChild(fragment);
    loadedVideos += batchSize;
    document.querySelectorAll('.video-item').forEach(item => observer.observe(item));
}


async function validateKey() {
    let key = document.getElementById("access-key").value;
    let response = await fetch(`${window.location.protocol}//${window.location.hostname}:5000/check_key`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key })
    });

    let result = await response.json();
    if (result.access === "granted") {
        document.getElementById("auth-screen").style.display = "none";
    } else {
        alert("Неверный ключ!");
    }
}


let observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            let canvas = entry.target.querySelector("canvas");
            let videoSrc = entry.target.getAttribute("data-video");
            
            let tempVideo = document.createElement('video');
            tempVideo.src = videoSrc;
            tempVideo.currentTime = 5;
            tempVideo.onloadeddata = () => {
                let ctx = canvas.getContext('2d');
                ctx.drawImage(tempVideo, 0, 0, 80, 45);
            };
            observer.unobserve(entry.target);
        }
    });
}, { root: document.getElementById('video-list'), threshold: 0.1 });


function editTitle() {
    let videoTitle = document.getElementById('video-title');
    let newTitle = prompt("Enter new title:", videoTitle.textContent.trim());

    if (newTitle && newTitle !== videoTitle.textContent.trim()) {
        fetch('/rename-video', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                old_name: videoTitle.textContent.trim(),
                new_name: newTitle
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log("Video renamed successfully!");
            } else {
                alert(data.error || "Error renaming video");
            }
        })
        .catch(error => {
            alert("Failed to rename video: " + error.message);
        });

        videoTitle.textContent = newTitle;
        loadVideos();
    }
}


function deleteVideo() {
    let videoName = document.getElementById('video-title');
    if (confirm(`Are you sure you want to delete the video: ${videoName.textContent.trim()}?`)) {
        fetch('/delete-video', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                video_name: videoName.textContent.trim()
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log("Video deleted successfully!");
                loadVideos();
            } else {
                alert(data.error || "Error deleting video");
            }
        })
        .catch(error => {
            alert("Failed to delete video: " + error.message);
        });
    }
}


window.onload = async function () {
    await loadVideos();
};


document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('video-list').addEventListener('scroll', function () {
        if (this.scrollTop + this.clientHeight >= this.scrollHeight - 10) {
            renderNextBatch();
        }
    });

    document.getElementById('video-search').addEventListener('input', function () {
        currentFilter = this.value.toLowerCase();
        loadVideos();
    });

    document.getElementById('download-link').addEventListener('click', function(event) {
        event.preventDefault();
        let videoName = document.getElementById('video-title').textContent.trim();
        let url = `/video:download/${videoName}`;
        window.location.href = url; 
    });    

    document.getElementById('file-input').addEventListener('change', function () {
        let fileInput = document.getElementById('file-input');
        let fileTitle = document.getElementById('file-title');
        if (fileInput.files.length > 0) {
            fileTitle.value = fileInput.files[0].name.replace(/\.[^/.]+$/, "");
        }
    });

    document.getElementById('upload-form').addEventListener('submit', async function (event) {
        event.preventDefault();
    
        let fileInput = document.getElementById('file-input');
        let fileTitle = document.getElementById('file-title');
        let uploadStatus = document.getElementById('upload-status');
    
        if (!fileInput.files[0]) {
            uploadStatus.textContent = "Please select a video file!";
            return;
        }
    
        if (!fileTitle.value.trim()) {
            uploadStatus.textContent = "Please enter a title for the video!";
            return;
        }
    
        let formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('title', fileTitle.value.trim());
    
        uploadStatus.textContent = "Uploading...";
        try {
            let response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
    
            if (!response.ok) {
                throw new Error('Failed to upload video');
            }
    
            let result = await response.json();
            if (result.success) {
                uploadStatus.textContent = "Upload successful!";
            } else {
                uploadStatus.textContent = `Error: ${result.message}`;
            }
        } catch (error) {
            uploadStatus.textContent = `Upload failed: ${error.message}`;
        }
    });    
});
