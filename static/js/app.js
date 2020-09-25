document.addEventListener("DOMContentLoaded", function () {
    const NewOrderForm = document.querySelectorAll('.new-order')
    if (NewOrderForm !== null) {
        const provider = document.querySelector('.provider')
        const order_num = document.querySelector('.order-number')
        const order_date = document.querySelector('.order-date')
        const add_order_button = document.querySelector('#add-order')
        const order_details = document.querySelector('.order-details')
        const all_orders = document.querySelector('.all-orders')
        const order_description = document.querySelector('.order-description')
        provider.addEventListener('click', function(event) {
            $.ajax({
                url: '/non/',
                data: {'provider_num': provider.value},
                type: 'GET',
                dataType: 'json'
            }).done(function (data) {
                order_num.value = data
                let today = new Date().toISOString().slice(0, 10)
                order_date.value = today
                })
            })
        add_order_button.addEventListener('click', function(event){
            order_details.style.display = 'none'
            all_orders.style.display = 'inline'
            order_description.innerText = 'okok'
            event.preventDefault()
        })
        }
})