window.onload = async function(){
    try {
        const download_link = document.createElement("a");
        download_link.textContent = "Download";
        download_link.href = `/api/files/${file_id}`;
        document.getElementById("download_div").append(download_link);

        document.getElementById('image').src = `/api/view/${file_id}`; 

    } catch (error) {
        console.log(error);
    }
}
