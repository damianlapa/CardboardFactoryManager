document.addEventListener("DOMContentLoaded", function () {

    function getLocalLink() {
        let localLinkURL = ''
        $.ajax({
            url: '/get-local-var/PAKER_MAIN/',
            data: {},
            type: 'GET',
            dataType: 'json'
            }).done(function (data) {
                localLink = data
            })

        return localLinkURL
    }

    let localLink = getLocalLink()

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
            for (let j=0; j < data.length; j++) {
                var child = document.createElement('button')
                child.innerHTML = data[j][0]
                child.classList.add('button-24')
                child.classList.add('button-block')
                if (data[j][1] == 'INNE') {
                    child.classList.add('bg-orange')
                }else if (data[j][1] == 'PLANOWANA DOSTAWA') {
                    child.classList.add('bg-blue')
                }else if (data[j][1] == 'ZREALIZOWANA DOSTAWA') {
                    child.classList.add('bg-black')
                }else if (data[j][1] == 'SPOTKANIE') {
                    child.classList.add('bg-pink')
                    child.style.color = 'black'
                }else if (data[j][1] == 'ODBIÓR OSOBISTY') {
                    child.classList.add('bg-yellow')
                    child.style.color = 'black'
                }
                allDays[i].appendChild(child)
            }

                })

        allDays[i].addEventListener('click', function() {
                date = this.dataset.calendar
                link = localLink + 'deliveries/day-details/' + date + '/'
                window.open(link, '_self')

        })
    }


})