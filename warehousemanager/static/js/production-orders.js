document.addEventListener("DOMContentLoaded", function () {
    const allOrders = document.getElementsByClassName('production-order')
    const ordersBtns = document.getElementsByClassName('production-order-btn')

    const ordersFilterInput = document.getElementById('production-orders-filter')

    function ordersShowHide(orders, value) {
        for (let i=0; i < orders.length; i++){
            if (orders[i].dataset.orderstatus === value){
                orders[i].style.display = 'block'
            }else {
                orders[i].style.display = 'none'
            }
            if (value === 'ALL') {
                orders[i].style.display = 'block'
            }
        }
    }

    function ordersFilter(orders, value) {
        for (let i=0; i < orders.length; i++){
            if (orders[i].dataset.orderstatus.toLowerCase().includes(value)){
            orders[i].style.display = 'block'
            }
            else if (orders[i].dataset.idnumber.toLowerCase().includes(value)){
            orders[i].style.display = 'block'
            }else if (orders[i].dataset.cardboard.toLowerCase().includes(value)){
            orders[i].style.display = 'block'
            }else if (orders[i].dataset.cardboarddimensions.toLowerCase().includes(value)){
            orders[i].style.display = 'block'
            }else if (orders[i].dataset.customer.toLowerCase().includes(value)){
            orders[i].style.display = 'block'
            }else if (orders[i].dataset.quantity.toLowerCase().includes(value)){
            orders[i].style.display = 'block'
            }else if (orders[i].dataset.notes.toLowerCase().includes(value)){
            orders[i].style.display = 'block'
            }else if (orders[i].dataset.dimensions.toLowerCase().includes(value)){
            orders[i].style.display = 'block'
            }else{
            orders[i].style.display = 'none'
            }
        }
    }

    for (let i=0; i < ordersBtns.length; i++){
        ordersBtns[i].addEventListener('click', function (){
            ordersShowHide(allOrders, this.innerText)
        })
    }

    ordersFilterInput.addEventListener('keyup', function(){
        ordersFilter(allOrders, this.value.toLowerCase())
    })
})