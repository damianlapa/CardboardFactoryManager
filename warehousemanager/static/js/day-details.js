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
        allEvents[i].addEventListener('click', function(event) {
        if (event.target.classList.contains('checkbox')) {
            console.log(this);
            var self = this
            $.ajax({
            url: localLink + 'deliveries/event-check/' + this.dataset['eventid']+ '/',
            data: {},
            type: 'GET',
            dataType: 'json'
            }).done(function (data) {
                var eventType = self.getElementsByTagName("td")[1];
                var checkbox = self.getElementsByTagName("input")[0]
                eventType.innerText = "ZREALIZOWANA DOSTAWA";
                checkbox.checked = true;
            })
            event.stopPropagation();
        }
        else {
            //link = localLink + 'deliveries/event-details/' + allEvents[i].dataset.eventid + '/'
            //window.open(link, '_self')
        }
        })
    }
})