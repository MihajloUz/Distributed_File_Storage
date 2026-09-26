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
    
    close_button.style.display = "block";
    close_button.style.width = "50px";
    close_button.style.height = "50px";
    close_button.style.fontSize = "25px";   
    overlay.style.background = "rgba(0, 0, 0, 0.5)";
    overlay.style.width = "100%";
    overlay.style.height = "100%";


    event.preventDefault();

    const form = event.target;

    try {
        const response = await fetch(form.action, {
            method: "GET"
        });

        const data = await response.json();

        const rust_response = await fetch(`/api/view/${data.file_id}`);
        const blob = await rust_response.blob();

        switch (data.type){
            case "image":
                const img = document.createElement("img");
                img.src = URL.createObjectURL(blob);

                content.innerHTML = "";
                content.appendChild(img);
                break;
            case "text": // maybe make separate for md later
            case "md":
                const text = document.createElement("pre");
                text.innerHTML = await blob.text();

                content.innerHTML = "";
                content.appendChild(text);
                break;
            case "pdf":
                const embed = document.createElement("embed");
                embed.src = `/api/view/${data.file_id}`;
                embed.width = "100%";
                embed.height = "800px"; //tweak this a bit so it would fit download link aswell as the pdf itself later

                content.innerHTML = "";
                content.appendChild(embed);
                break;


            default: 
                console.log("something went wrong in switch statement");
        }

        //const img = document.createElement("img");
        //img.src = URL.createObjectURL(blob);


        console.log(data);
    } catch (error) {
        console.error("Error:", error);
    }
});

close_button.addEventListener("click", () => {
    content.innerHTML = "";
    overlay.style.background = "rgba(0, 0, 0, 0)";
    close_button.style.display = "none";
    close_button.style.width = "0";
    close_button.style.height = "0";
    close_button.style.fontSize = "0";
    overlay.style.width = "0";
    overlay.style.height = "0";
});

async function loadFilesList() {
    try {
        const response = await fetch('/api/files');
        const data = await response.json();
        console.log(data)
        filesList.innerHTML = '';

        if (data.files.length === 0) {
            filesList.innerHTML = "<li>The files haven't been uploaded yet</li>";
            return;
        }

        data.files.forEach(file => {
            const li = document.createElement('li');

            li.innerHTML = `
                <div>
                    <img src="/static/icons/${file.file_type}.svg">
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

    const formData = new FormData();
    const file = fileInput.files[0];
    formData.append('file', file);

    messageDiv.style.color = 'black';
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
            messageDiv.style.color = 'green';
            messageDiv.textContent = result.message;
            fileInput.value = ''; 
            console.log("SUCCESSFUL UPLOAD. TRYING TO LOAD FILES FRO MTHE SERVER");
            loadFilesList(); 
        } else {
            messageDiv.style.color = 'red';
            messageDiv.textContent = result.detail || 'Upload error';
        }
    } catch (error) {
        messageDiv.style.color = 'red';
        messageDiv.textContent = 'Network connection error';
    }
});

document.addEventListener('paste', async (e) => {
    e.preventDefault();
    const items = event.clipboardData?.items;
    if (!items || items.length === 0) return;

    const files = [];
    for (const item of items) {
        if (item.kind === 'file') {
            const file = item.getAsFile();
            if (file) files.push(file);
        }
    }

    if (files.length === 0) {
        return;
    }

    const file = files[0];

    const formData = new FormData();
    formData.append('file', file);

    messageDiv.style.color = 'black';
    messageDiv.textContent = 'Loading...';
    
    // add some type of pop up that informs whether the file was 
    // uploaded or not 

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
            messageDiv.style.color = 'green';
            messageDiv.textContent = result.message;
            fileInput.value = ''; 
            console.log("SUCCESSFUL UPLOAD. TRYING TO LOAD FILES FRO MTHE SERVER");
            loadFilesList(); 
        } else {
            messageDiv.style.color = 'red';
            messageDiv.textContent = result.detail || 'Upload error';
        }
    } catch (error) {
        messageDiv.style.color = 'red';
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
