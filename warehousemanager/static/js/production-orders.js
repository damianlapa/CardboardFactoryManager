document.addEventListener("DOMContentLoaded", function () {
    const allOrders = document.getElementsByClassName('production-order')
    const ordersBtns = document.getElementsByClassName('production-order-btn')

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

    for (let i=0; i < ordersBtns.length; i++){
        ordersBtns[i].addEventListener('click', function (){
            ordersShowHide(allOrders, this.innerText)
        })
    }
})