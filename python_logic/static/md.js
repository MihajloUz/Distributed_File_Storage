window.onload = async function(){
    try {
        const response = await fetch(`/api/view/${file_id}`);

        if (!response.ok) {
            throw new Error("Failed to load file");
        }

        const download_link = document.createElement("a");
        download_link.textContent = "Download";
        download_link.href = `/api/files/${file_id}`;
        document.getElementById("download_div").append(download_link);

        const data = await response.text();

        document.getElementById('data').innerHTML = marked.parse(data); 

    } catch (error) {
        console.log(error);
    }
}
