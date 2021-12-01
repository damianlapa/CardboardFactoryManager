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

    id_number = document.getElementById('id_id_number')
    submitBtn = document.getElementById('submitBtn')

    id_number.addEventListener('keyup', function() {
        console.log(this.value)
        $.ajax({
            url: '/production/get-production-by-id/',
            data: {'id_number': this.value},
            type: 'GET',
            dataType: 'json'
            }).done(function (data){
                console.log(data)
               if (data === true) {
                    submitBtn.disabled = true
                    submitBtn.style.backgroundColor = 'red'
                    submitBtn.style.color = 'white'
                    submitBtn.value = 'Id number can\'t repeat'
               } else {
                    submitBtn.disabled = false
                    submitBtn.style.backgroundColor = 'green'
                    submitBtn.value = 'Add'
                    submitBtn.style.color = 'black'
               }
            })
    })

})