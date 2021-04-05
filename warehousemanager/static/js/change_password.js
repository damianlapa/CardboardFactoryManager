document.addEventListener("DOMContentLoaded", function () {
    const passwordForm = document.getElementById('changePasswordForm')
    const changePasswordBtn = document.getElementById('changePasswordBtn')

    if (changePasswordBtn !== null) {
        changePasswordBtn.addEventListener('click', function() {
            if (passwordForm.style.display === 'block') {
                passwordForm.style.display = 'none'
            }else {
            passwordForm.style.display = 'block'}
        })
    }

    if (passwordForm !== null ) {
        const newPassword = document.getElementById('id_new_password')
        const repeatedPassword = document.getElementById('id_repeated_password')
        const changePasswordFormBtn = document.getElementById('changePasswordFormBtn')

        changePasswordFormBtn.disabled = true
        changePasswordFormBtn.style.background = 'grey'

        repeatedPassword.addEventListener('keyup', function() {
            if (newPassword.value === repeatedPassword.value) {
                changePasswordFormBtn.disabled = false;
                changePasswordFormBtn.style.background = 'orange'
            } else {
                changePasswordFormBtn.disabled = true
                changePasswordFormBtn.style.background = 'grey'
            }
        })
    }

})