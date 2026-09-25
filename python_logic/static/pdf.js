window.onload = function () {
    const viewerDiv = document.getElementById("viewer_div");
    const downloadDiv = document.getElementById("download_div");

    const download_link = document.createElement("a");
    download_link.textContent = "Download";
    download_link.href = `/api/files/${file_id}`;
    downloadDiv.append(download_link);

    const embed = document.createElement("embed");
    embed.src = `/api/view/${file_id}`;
    embed.width = "100%";
    embed.height = "800px"; //tweak this a bit so it would fit download link aswell as the pdf itself later
    viewerDiv.appendChild(embed);
};
