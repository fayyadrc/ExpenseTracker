// Define toggleFields globally
function toggleFields() {
    const actionType = document.getElementById('action_type').value;
    const transactionFields = document.getElementById('transaction-fields');
    const depositWithdrawFields = document.getElementById('deposit-withdraw-fields');

    // Hide all fields initially
    transactionFields.style.display = 'none';
    depositWithdrawFields.style.display = 'none';

    // Show relevant fields based on action type
    if (actionType === 'transaction') {
        transactionFields.style.display = 'block';
    } else if (actionType === 'deposit' || actionType === 'withdraw') {
        depositWithdrawFields.style.display = 'block';
    }
}

document.addEventListener("DOMContentLoaded", function () {
    // Add event listener for action type change
    const actionTypeSelect = document.getElementById('action_type');
    if (actionTypeSelect) {
        actionTypeSelect.addEventListener('change', toggleFields);
    }

    // Form submission handling
    const form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            const formData = new FormData(form);
            fetch(form.action, {
                method: "POST",
                body: formData
            }).then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        if (text === "Insufficient funds") {
                            const modal = new bootstrap.Modal(document.getElementById("insufficientFundsModal"));
                            modal.show();
                        }
                    });
                } else {
                    window.location.reload();
                }
            }).catch(error => console.error("Error:", error));
        });
    }

    // Dark mode toggle functionality
    const darkModeToggle = document.getElementById('darkModeToggleProfile');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function () {
            document.body.classList.toggle('dark-mode');
            const cards = document.querySelectorAll('.card');
            const formFields = document.querySelectorAll('.form-control, .form-select');

            // Toggle classes for cards
            cards.forEach(card => {
                if (document.body.classList.contains('dark-mode')) {
                    card.classList.add('bg-dark', 'text-light');
                    card.classList.remove('bg-light', 'text-dark');
                } else {
                    card.classList.add('bg-light', 'text-dark');
                    card.classList.remove('bg-dark', 'text-light');
                }
            });

            // Toggle classes for form fields
            formFields.forEach(field => {
                field.classList.toggle('bg-dark', document.body.classList.contains('dark-mode'));
                field.classList.toggle('text-light', document.body.classList.contains('dark-mode'));
                field.classList.toggle('bg-light', !document.body.classList.contains('dark-mode'));
                field.classList.toggle('text-dark', !document.body.classList.contains('dark-mode'));
            });

            // Toggle classes for sidebars
            const leftSidebar = document.querySelector('.left-sidebar');
            const rightSidebar = document.querySelector('.right-sidebar');
            if (leftSidebar) leftSidebar.classList.toggle('bg-dark');
            if (rightSidebar) rightSidebar.classList.toggle('bg-dark');
            if (leftSidebar) leftSidebar.classList.toggle('text-light');
            if (rightSidebar) rightSidebar.classList.toggle('text-light');

            // Store the theme preference
            localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
        });
    }

    // Check the stored theme preference on page load
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');

        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            card.classList.add('bg-dark', 'text-light');
            card.classList.remove('bg-light', 'text-dark');
        });

        const formFields = document.querySelectorAll('.form-control, .form-select');
        formFields.forEach(field => {
            field.classList.add('bg-dark', 'text-light');
            field.classList.remove('bg-light', 'text-dark');
        });

        const leftSidebar = document.querySelector('.left-sidebar');
        const rightSidebar = document.querySelector('.right-sidebar');
        if (leftSidebar) {
            leftSidebar.classList.add('bg-dark', 'text-light');
        }
        if (rightSidebar) {
            rightSidebar.classList.add('bg-dark', 'text-light');
        }
    } else {
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            card.classList.add('bg-light', 'text-dark');
            card.classList.remove('bg-dark', 'text-light');
        });

        const formFields = document.querySelectorAll('.form-control, .form-select');
        formFields.forEach(field => {
            field.classList.add('bg-light', 'text-dark');
            field.classList.remove('bg-dark', 'text-light');
        });
    }
});