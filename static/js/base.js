function toggleFields() {
    const actionType = document.getElementById('action_type').value;
    const transactionFields = document.getElementById('transaction-fields');
    const depositWithdrawFields = document.getElementById('deposit-withdraw-fields');
    transactionFields.style.display = 'none';
    depositWithdrawFields.style.display = 'none';
    if (actionType === 'transaction') {
        transactionFields.style.display = 'block';
    } else if (actionType === 'deposit' || actionType === 'withdraw') {
        depositWithdrawFields.style.display = 'block';
    }
}

document.querySelector("form").addEventListener("submit", function (event) {
    console.log(new FormData(this));
});


document.getElementById('darkModeToggle').addEventListener('click', function () {
    document.body.classList.toggle('dark-mode');
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        if (document.body.classList.contains('dark-mode')) {
            card.classList.add('bg-dark', 'text-light');
            card.classList.remove('bg-light', 'text-dark');
        } else {
            card.classList.add('bg-light', 'text-dark');
            card.classList.remove('bg-dark', 'text-light');
        }
    });

    const leftSidebar = document.querySelector('.left-sidebar');
    const rightSidebar = document.querySelector('.right-sidebar');
    leftSidebar.classList.toggle('bg-dark');
    rightSidebar.classList.toggle('bg-dark');
    leftSidebar.classList.toggle('text-light');
    rightSidebar.classList.toggle('text-light');


    if (document.body.classList.contains('dark-mode')) {
        localStorage.setItem('theme', 'dark');
    } else {
        localStorage.setItem('theme', 'light');
    }
});

window.onload = function () {
    // Check the stored theme preference on page load
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');

        // Apply dark mode classes to all cards
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            card.classList.add('bg-dark', 'text-light');
            card.classList.remove('bg-light', 'text-dark');
        });

        // Apply dark mode classes to sidebars
        const leftSidebar = document.querySelector('.left-sidebar');
        const rightSidebar = document.querySelector('.right-sidebar');
        leftSidebar.classList.add('bg-dark', 'text-light');
        rightSidebar.classList.add('bg-dark', 'text-light');
    } else {

        // Ensure light mode classes are applied in case of missing or "light" theme preference
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            card.classList.add('bg-light', 'text-dark');
            card.classList.remove('bg-dark', 'text-light');
        });
    }
};

document.addEventListener("DOMContentLoaded", function () {
    const withdrawForm = document.querySelector("form[action='{{ url_for('index') }}']");
    withdrawForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const formData = new FormData(withdrawForm);
        fetch(withdrawForm.action, {
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
});