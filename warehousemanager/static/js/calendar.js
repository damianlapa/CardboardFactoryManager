document.addEventListener("DOMContentLoaded", function () {

    console.log('File loaded correctly')

    const allDays = document.getElementsByClassName('calendar-item')

    for (let i = 0; i < allDays.length; i++) {
        //console.log(allDays[i])
        //console.log(allDays[i].dataset.calendar)
        $.ajax({
            url: '/deliveries/events-by-day/',
            data: {'calendar': allDays[i].dataset.calendar},
            type: 'GET',
            dataType: 'json'
            }).done(function (data) {
            console.log(data.length)
            for (let j=0; j < data.length; j++) {
                var child = document.createElement('button')
                child.innerHTML = data[j]
                child.classList.add('red')
                child.classList.add('button-block')
                allDays[i].appendChild(child)
            }

                })
    }

})