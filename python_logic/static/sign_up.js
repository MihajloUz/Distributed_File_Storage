  const form = document.getElementById("signupForm");

    const email = document.getElementById("mail");
    const emailError = document.querySelector("#mail + span.error");

    const pass1 = document.getElementById("pass1");
    const pass1Error = document.querySelector("#pass1 + span.error");

    const pass2 = document.getElementById("pass2");
    const pass2Error = document.querySelector("#pass2 + span.error");

    // Валідація Email під час вводу
    email.addEventListener("input", function () {
        if (email.validity.valid) {
            emailError.textContent = "";
            emailError.className = "error";
        } else {
            showEmailError();
        }
    });

    // Валідація першого пароля
    pass1.addEventListener("input", function () {
        if (pass1.validity.valid) {
            pass1Error.textContent = "";
            pass1Error.className = "error";
        } else {
            showPass1Error();
        }

        if (pass2.value) validatePasswordMatch();
    });

    // Валідація збігу паролів
    pass2.addEventListener("input", validatePasswordMatch);

    function validatePasswordMatch() {
        if (pass2.validity.valueMissing) {
            pass2Error.textContent = "Please repeat your password.";
            pass2Error.className = "error active";
        } else if (pass1.value !== pass2.value) {
            pass2Error.textContent = "Passwords do not match.";
            pass2Error.className = "error active";
        } else {
            pass2Error.textContent = "";
            pass2Error.className = "error";
        }
    }

    function showEmailError() {
        if (email.validity.valueMissing) {
            emailError.textContent = "You need to enter an e-mail address.";
        } else if (email.validity.typeMismatch) {
            emailError.textContent = "Entered value needs to be an e-mail address.";
        } else if (email.validity.tooShort) {
            emailError.textContent = `Email should be at least ${email.minLength} characters; you entered ${email.value.length}.`;
        }
        emailError.className = "error active";
    }

    function showPass1Error() {
        if (pass1.validity.valueMissing) {
            pass1Error.textContent = "You need to enter a password.";
        } else if (pass1.validity.tooShort) {
            pass1Error.textContent = `Password should be at least ${pass1.minLength} characters; you entered ${pass1.value.length}.`;
        }
        pass1Error.className = "error active";
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        let isValid = true;

        if (!email.validity.valid) {
            showEmailError();
            isValid = false;
        }

        if (!pass1.validity.valid) {
            showPass1Error();
            isValid = false;
        }

        if (!pass2.value || pass1.value !== pass2.value) {
            validatePasswordMatch();
            isValid = false;
        }

        if (!isValid) {
            e.preventDefault();
            return;
        }
        const emailValue = email.value;
        const passwordValue = pass1.value;
        
        const response = await fetch('/api/sign_up', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                email: emailValue, 
                password: passwordValue 
            })
        });
        
        if (response.redirected) {
            window.location.href = response.url;
            return;
        }
        
    });