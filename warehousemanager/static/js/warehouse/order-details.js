document.addEventListener("DOMContentLoaded", function () {
    const delivery = document.getElementById('delivery_cbx')
    const finished = document.getElementById('finished_cbx')

    console.log(order_id)

    delivery.addEventListener('click', function() {
        $.ajax({
            url: '/warehouse/orders/status/',
            data: {'order_id': order_id, 'action': 'delivered'},
            type: 'GET',
            dataType: 'json'
            }).done(function (data) {
                    console.log(data)
                })
    })

    finished.addEventListener('click', function() {
        $.ajax({
            url: '/warehouse/orders/status/',
            data: {'order_id': order_id, 'action': 'finished'},
            type: 'GET',
            dataType: 'json'
            }).done(function (data) {
                    console.log(data)
                })
    })

})