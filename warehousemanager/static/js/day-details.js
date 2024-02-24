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

    allEvents = document.getElementsByClassName('day-details-row')

    for (let i=0; i < allEvents.length; i++) {
        allEvents[i].addEventListener('click', function() {
            link = localLink + 'deliveries/event-details/' + allEvents[i].dataset.eventid + '/'
            window.open(link, '_self')
        })
    }
})