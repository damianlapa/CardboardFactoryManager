document.addEventListener("DOMContentLoaded", function () {
    const all_rows = document.getElementsByClassName('alltime')
    const todayBtn = document.getElementById('today-btn')
    const last7Btn = document.getElementById('last7-btn')
    const thisMonthBtn = document.getElementById('thismonth-btn')
    const allTimeBtn = document.getElementById('alltime-btn')

    const allButtons = [todayBtn, last7Btn, thisMonthBtn, allTimeBtn]

    function showHideRows(rows, className){
        if (rows !== null) {
            for (i=0; i < rows.length; i++) {
                if (rows[i].classList.contains(className)) {
                    rows[i].style.display = 'table-row'
                }else {
                    rows[i].style.display = 'none'
                }
            }
        }
    }

    function buttonsColor(button, buttons, color1, color2) {
        for (let i=0; i < buttons.length; i++) {
            if (buttons[i] === button) {
                buttons[i].style.background = color1
                console.log('btn:')
                console.log(button)
            }else {
                console.log('change')
                console.log(button)
                buttons[i].style.background = color2
            }
        }
    }

    todayBtn.addEventListener('click', function() {
        buttonsColor(this, allButtons, 'red', 'green')
        showHideRows(all_rows, 'today')
    })
    last7Btn.addEventListener('click', function() {
        buttonsColor(this, allButtons, 'red', 'green')
        showHideRows(all_rows, 'last7')
    })
    thisMonthBtn.addEventListener('click', function() {
        buttonsColor(this, allButtons, 'red', 'green')
        showHideRows(all_rows, 'thismonth')
    })
    allTimeBtn.addEventListener('click', function() {
        buttonsColor(this, allButtons, 'red', 'green')
        showHideRows(all_rows, 'alltime')
    })
})