document.addEventListener("DOMContentLoaded", function () {
    const status = document.getElementById('production-status')
    const selectStatus = document.getElementById('select-status')
    const changeBtn = document.getElementById('change-btn')

    selectStatus.addEventListener('click', function() {
        if (this.value !== status.innerHTML) {
            changeBtn.disabled = false
        }else {
            changeBtn.disabled = true
        }
    })
})