const form = document.getElementById('verification_form');
const params = new URLSearchParams(window.location.search);
const email = params.get("email");

form.addEventListener('submit', async (e) => {
    e.preventDefault(); 

    const code = document.getElementById('verification_code').value;

    try {
        const response = await fetch(`/api/email_verification?email=${encodeURIComponent(email)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                verification_code: code
            })
        });

        if (response.redirected) {
            window.location.href = response.url;
            return;
        }
        const data = await response.json();

    } catch (error) {
        //todo
    }
});
 
