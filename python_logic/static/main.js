const uploadForm = document.getElementById('uploadForm');
        const fileInput = document.getElementById('fileInput');
        const messageDiv = document.getElementById('message');
        const filesList = document.getElementById('filesList');

        //функция загрузки и отображения списка файлов
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
                            <a href="/api/files/${file.id}" target="_blank">${file.file_name}</a>
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

        document.addEventListener('DOMContentLoaded', loadFilesList);
        function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}