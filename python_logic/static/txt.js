window.onload = async function(){
    try {
        const response = await fetch(`/api/view/${file_id}`);

        if (!response.ok) {
            throw new Error("Failed to load file");
        }

        const data = await response.text();


        document.getElementById('data').textContent = data; 

    } catch (error) {
        //todo
    }
}
