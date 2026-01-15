new QWebChannel(qt.webChannelTransport, function (channel) {
    window.bridge = channel.objects.bridge;

    function findUsernameAndPasswordFields(form) {
        let usernameField = null;
        let passwordField = null;
        const inputs = form.querySelectorAll('input');

        for (const input of inputs) {
            if (input.type === 'password') {
                passwordField = input;
            } else if (input.type === 'email' || input.type === 'text' || input.type === 'tel') {
                const name = (input.name || '').toLowerCase();
                const id = (input.id || '').toLowerCase();
                if (name.includes('user') || id.includes('user') || 
                    name.includes('email') || id.includes('email') || 
                    name.includes('login') || id.includes('login')) {
                    usernameField = input;
                }
            }
        }
        // If a username field was found next to a password field, we're more confident.
        if (passwordField && usernameField) {
            return { usernameField, passwordField };
        }
        return null;
    }

    // --- Capture Logic ---
    document.querySelectorAll('form').forEach(form => {
        const fields = findUsernameAndPasswordFields(form);
        if (fields) {
            form.addEventListener('submit', function () {
                const username = fields.usernameField.value;
                const password = fields.passwordField.value;
                if (username && password) {
                    // Send credentials back to Python
                    window.bridge.capture_credentials(username, password);
                }
            });
        }
    });

    // --- Autofill Logic ---
    window.autofill = function(username, password) {
        const forms = document.querySelectorAll('form');
        for (const form of forms) {
            const fields = findUsernameAndPasswordFields(form);
            if (fields) {
                fields.usernameField.value = username;
                fields.passwordField.value = password;
                break; // Stop after filling the first found form
            }
        }
    };
});