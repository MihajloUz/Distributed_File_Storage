 const form = document.getElementById('loginForm');
        const messageDiv = document.getElementById('message');

        form.addEventListener('submit', async (e) => {
            e.preventDefault(); 

            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;

            messageDiv.style.color = 'black';
            messageDiv.textContent = 'Verification..';

            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        email: username, 
                        password: password 
                    })
                });

                if (response.redirected) {
                    window.location.href = response.url;
                    return;
                }
                const data = await response.json();

                if (response.ok) {
                    messageDiv.style.color = 'green';
                    messageDiv.textContent = data.message;
                } else {
                    messageDiv.style.color = 'red';
                    messageDiv.textContent = data.detail || 'Authentication';
                }
            } catch (error) {
                messageDiv.style.color = 'red';
                messageDiv.textContent = 'No server connection';
            }
        });
        