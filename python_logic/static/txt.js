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

        const data = await response.json();
        document.getElementById('data').value = response; //to update 
        if (response.redirected) {
            window.location.href = response.url;
            return;
        }

    } catch (error) {
        //todo
    }
}
