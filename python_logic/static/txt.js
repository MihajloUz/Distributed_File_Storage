window.onload = function(){
    const field = "{{ file_id }}"
    try {
        const response = await fetch(`/api/view`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                file_id: field 
            })
        });

        if (!response.ok) {
            throw new Error("Failed to load file");
        }

        const data = await response.text();


        document.getElementById('data').textContent = data; 
        if (response.redirected) {
            window.location.href = response.url;
            return;
        }

    } catch (error) {
        //todo
    }
}
