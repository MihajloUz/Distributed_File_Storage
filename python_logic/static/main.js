const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const messageDiv = document.getElementById('message');
const filesList = document.getElementById('filesList');

const overlay = document.getElementById("overlay");
const content = document.querySelector(".content");
const close_button = document.getElementById("close");

filesList.addEventListener("submit", async (event) => {
    if (!event.target.matches(".get_overlay_info")) {
        return;
    }

    event.preventDefault();

    overlay.classList.add("active");
    overlay.style.display = "flex";

    close_button.innerHTML = "&times;";

    const form = event.target;

    try {
        const response = await fetch(form.action, {
            method: "GET"
        });

        const data = await response.json();

        const rust_response = await fetch(`/api/view/${data.file_id}`);
        const blob = await rust_response.blob();

        switch (data.type) {
            case "image":
                const img = document.createElement("img");
                img.src = URL.createObjectURL(blob);

                content.innerHTML = "";
                content.appendChild(img);
                break;
            case "text":
            case "md":
                const text = document.createElement("pre");
                text.textContent = await blob.text();

                content.innerHTML = "";
                content.appendChild(text);
                break;
            case "pdf":
                const embed = document.createElement("embed");
                embed.src = `/api/view/${data.file_id}`;
                embed.type = "application/pdf";
                embed.width = "100%";
                embed.height = "100%";

                content.innerHTML = "";
                content.appendChild(embed);
                break;

            default: 
                console.log("something went wrong in switch statement");
        }

        // кнопка download
        const download_div = document.getElementById("download_div");
        if (download_div) {
            download_div.innerHTML = "";

            const download_link = document.createElement("a");
            download_link.textContent = "Download";
            download_link.href = `/api/files/${data.file_id}`;
            download_link.setAttribute("download", "");
            download_div.appendChild(download_link);
        }

    } catch (error) {
        console.error("Error:", error);
    }
});

// Для закриття оверлею
close_button.addEventListener("click", () => {
    content.innerHTML = "";
    
    const download_div = document.getElementById("download_div");
    if (download_div) {
        download_div.innerHTML = "";
    }

    overlay.classList.remove("active");
    overlay.style.display = "none";
});

async function loadFilesList() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        console.log(data);
        filesList.innerHTML = '';

        if (!data.files || data.files.length === 0) {
            filesList.innerHTML = "<li>The files haven't been uploaded yet</li>";
            return;
        }

        data.files.forEach(file => {
            const li = document.createElement('li');

            li.innerHTML = `
                <div>
                    <img src="/static/icons/${file.file_type}.svg" alt="icon">
                    <form class="get_overlay_info" action="/view/${file.id}" method="GET">
                        <button type="submit">${file.file_name}</button>
                    </form>
                    <div class="date">${file.uploaded_at}</div>
                </div>
            `;
            filesList.appendChild(li);
        });
    } catch (error) {
        console.error("Error:", error);
    }
}

uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!fileInput.files[0]) return;

    const file = fileInput.files[0];

    messageDiv.style.color = 'var(--text-main)';
    messageDiv.textContent = 'Loading...';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            headers: {
                'Filename': file.name,
            },
            body: file 
        });

        const result = await response.json();

        if (response.ok) {
            messageDiv.style.color = 'var(--success)';
            messageDiv.textContent = result.message;
            fileInput.value = ''; 
            console.log("SUCCESSFUL UPLOAD. TRYING TO LOAD FILES FROM THE SERVER");
            loadFilesList(); 
        } else {
            messageDiv.style.color = 'var(--danger)';
            messageDiv.textContent = result.detail || 'Upload error';
        }
    } catch (error) {
        messageDiv.style.color = 'var(--danger)';
        messageDiv.textContent = 'Network connection error';
    }
});

document.addEventListener('paste', async (e) => {
    const items = e.clipboardData?.items;
    if (!items || items.length === 0) return;

    const files = [];
    for (const item of items) {
        if (item.kind === 'file') {
            const file = item.getAsFile();
            if (file) files.push(file);
        }
    }

    if (files.length === 0) return;

    e.preventDefault();
    const file = files[0];

    messageDiv.style.color = 'var(--text-main)';
    messageDiv.textContent = 'Loading...';

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            headers: {
                'Filename': file.name,
            },
            body: file 
        });

        const result = await response.json();

        if (response.ok) {
            messageDiv.style.color = 'var(--success)';
            messageDiv.textContent = result.message;
            fileInput.value = ''; 
            console.log("SUCCESSFUL UPLOAD. TRYING TO LOAD FILES FROM THE SERVER");
            loadFilesList(); 
        } else {
            messageDiv.style.color = 'var(--danger)';
            messageDiv.textContent = result.detail || 'Upload error';
        }
    } catch (error) {
        messageDiv.style.color = 'var(--danger)';
        messageDiv.textContent = 'Network connection error';
    } 
});

document.addEventListener('DOMContentLoaded', loadFilesList);

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}