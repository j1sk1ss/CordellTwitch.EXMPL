async function getVideoDate(url) {
    let response = await fetch(url, { method: 'HEAD' });
    let lastModified = response.headers.get('Last-Modified');
    return lastModified ? new Date(lastModified).getTime() : 0;
}

let loadedVideos = 0;
const batchSize = 20;
let allVideos = [];

async function loadVideos() {
    let response = await fetch('/streams_src/');
    let text = await response.text();
    let parser = new DOMParser();
    let doc = parser.parseFromString(text, 'text/html');
    let links = doc.querySelectorAll("a[href$='.mp4']");
    
    allVideos = [];

    for (let link of links) {
        let url = link.href;
        let fileName = decodeURIComponent(url.split('/').pop());
        let displayName = fileName.replace(/\.\w+$/, '');
        let lastModified = await getVideoDate(url);
        
        allVideos.push({ url, displayName, lastModified });
    }

    allVideos.sort((a, b) => b.lastModified - a.lastModified);
    loadedVideos = 0;
    renderNextBatch();
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
}

document.getElementById('video-list').addEventListener('scroll', function () {
    if (this.scrollTop + this.clientHeight >= this.scrollHeight - 10) {
        renderNextBatch();
    }
});

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

window.onload = async function () {
    await loadVideos();
    document.querySelectorAll('.video-item').forEach(item => observer.observe(item));
};