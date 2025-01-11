
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
    const actionTypeSelect = document.getElementById('action_type');
    if (actionTypeSelect) {
        actionTypeSelect.addEventListener('change', toggleFields);
    }

    const form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", function (event) {
            event.preventDefault();
            const formData = new FormData(form);

            // Convert date to the format "2 January 2025"
            const dateInput = formData.get('date');
            if (dateInput) {
                const dateObj = new Date(dateInput);
                if (isNaN(dateObj.getTime())) {
                    console.error("Invalid date");
                    alert("Please enter a valid date.");
                    return; // Prevent further processing
                }
                const day = dateObj.getDate();
                const month = dateObj.toLocaleString('en-US', { month: 'long' });
                const year = dateObj.getFullYear();
                const formattedDate = `${day} ${month} ${year}`;
                formData.set('date', formattedDate);
            }

            console.log('Sending form data:', Object.fromEntries(formData));

            fetch(form.action, {
                method: "POST",
                body: formData,
                headers: {
                    'Accept': 'application/json'
                }
            })
                .then(response => response.text())
                .then(text => {
                    try {
                        const data = JSON.parse(text);
                        if (data.error) {
                            console.error("Server error:", data.error);
                            alert(data.error);
                        } else {
                            window.location.reload();
                        }
                    } catch (e) {
                        console.error("Parsing error:", e);
                        alert("An error occurred while processing your request.");
                    }
                })
                .catch(error => {
                    console.error("Error:", error);
                    alert("An error occurred while processing your request.");
                });
        });
    }

    // Dark mode toggle functionality
    const darkModeToggle = document.getElementById('darkModeToggleProfile');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function () {
            const isDarkMode = document.body.classList.toggle('dark-mode');
            updateThemeClasses(isDarkMode);

            // Store the theme preference
            localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
        });
    }

    // Check the stored theme preference on page load
    const storedTheme = localStorage.getItem('theme');
    if (storedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        updateThemeClasses(true);
    } else {
        updateThemeClasses(false);
    }
});

// Function to update theme classes
function updateThemeClasses(isDark) {
    const cards = document.querySelectorAll('.card');
    const formFields = document.querySelectorAll('.form-control, .form-select');
    const leftSidebar = document.querySelector('.left-sidebar');
    const rightSidebar = document.querySelector('.right-sidebar');

    // Update classes for cards
    cards.forEach(card => {
        card.classList.toggle('bg-dark', isDark);
        card.classList.toggle('text-light', isDark);
        card.classList.toggle('bg-light', !isDark);
        card.classList.toggle('text-dark', !isDark);
    });

    // Update classes for form fields
    formFields.forEach(field => {
        field.classList.toggle('bg-dark', isDark);
        field.classList.toggle('text-light', isDark);
        field.classList.toggle('bg-light', !isDark);
        field.classList.toggle('text-dark', !isDark);
    });

    // Update classes for sidebars
    if (leftSidebar) {
        leftSidebar.classList.toggle('bg-dark', isDark);
        leftSidebar.classList.toggle('text-light', isDark);
    }
    if (rightSidebar) {
        rightSidebar.classList.toggle('bg-dark', isDark);
        rightSidebar.classList.toggle('text-light', isDark);
    }
}

//Manage categories modal popup

// Initialize the modal
document.addEventListener('DOMContentLoaded', function () {
    loadCategories();
});

// Handle form submission
function handleAddCategory(event) {
    event.preventDefault();

    const categoryName = document.getElementById('newCategoryName').value;
    const categoryEmoji = document.getElementById('newCategoryEmoji').value;

    if (!categoryName) {
        alert('Please enter a category name');
        return;
    }

    // Add category to the database via fetch API
    fetch('/api/categories', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            name: categoryName,
            emoji: categoryEmoji || '⚡️' // Default emoji if none provided
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear the form
                document.getElementById('addCategoryForm').reset();
                // Reload categories list
                loadCategories();
            } else {
                alert('Error adding category: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error adding category');
        });
}

// Load existing categories
function loadCategories() {
    fetch('/api/categories')
        .then(response => response.json())
        .then(data => {
            const categoriesList = document.getElementById('categoriesList');
            categoriesList.innerHTML = '';

            data.forEach(category => {
                const categoryElement = document.createElement('div');
                categoryElement.className = 'category-item d-flex justify-content-between align-items-center p-2 border-bottom';
                categoryElement.innerHTML = `
                            <span>${category.emoji || '⚡️'} ${category.name}</span>
                            <button class="btn btn-sm btn-danger" onclick="deleteCategory('${category.id}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        `;
                categoriesList.appendChild(categoryElement);
            });
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('categoriesList').innerHTML = '<p class="text-danger">Error loading categories</p>';
        });
}

// Delete category
function deleteCategory(categoryId) {
    if (confirm('Are you sure you want to delete this category?')) {
        fetch(`/api/categories/${categoryId}`, {
            method: 'DELETE'
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    loadCategories();
                } else {
                    alert('Error deleting category: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error deleting category');
            });
    }
}
