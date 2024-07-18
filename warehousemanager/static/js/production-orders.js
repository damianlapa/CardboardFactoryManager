document.addEventListener("DOMContentLoaded", function () {
    const allOrders = document.getElementsByClassName('production-order')
    const ordersBtns = document.getElementsByClassName('production-order-btn')

    const ordersFilterInput = document.getElementById('production-orders-filter')

    const ordersQuantity = document.getElementById('orders-num')

    function ordersShowHide(orders, value) {
        number = 0
        for (let i=0; i < orders.length; i++){
            if (orders[i].dataset.orderstatus === value){
                orders[i].style.display = 'block'
                number += 1
            }else {
                orders[i].style.display = 'none'
            }
            if (value === 'ALL') {
                orders[i].style.display = 'block'
                number = orders.length
            }
        }
        ordersQuantity.innerText = number
    }

    function ordersFilter(orders, value) {
        number = 0
        for (let i=0; i < orders.length; i++){
            if (orders[i].dataset.orderstatus.toLowerCase().includes(value)){
            orders[i].style.display = 'block';
            number += 1
            }
            else if (orders[i].dataset.idnumber.toLowerCase().includes(value)){
            orders[i].style.display = 'block';
            number += 1
            }else if (orders[i].dataset.cardboard.toLowerCase().includes(value)){
            orders[i].style.display = 'block';
            number += 1
            }else if (orders[i].dataset.cardboarddimensions.toLowerCase().includes(value)){
            orders[i].style.display = 'block';
            number += 1
            }else if (orders[i].dataset.customer.toLowerCase().includes(value)){
            orders[i].style.display = 'block';
            number += 1
            }else if (orders[i].dataset.quantity.toLowerCase().includes(value)){
            orders[i].style.display = 'block';
            number += 1
            }else if (orders[i].dataset.notes.toLowerCase().includes(value)){
            orders[i].style.display = 'block';
            number += 1
            }else if (orders[i].dataset.dimensions.toLowerCase().includes(value)){
            orders[i].style.display = 'block';
            number += 1
            }else{
            orders[i].style.display = 'none'
            }
        }
        ordersQuantity.innerText = number
    }

    for (let i=0; i < ordersBtns.length; i++){
        ordersBtns[i].addEventListener('click', function (){
            ordersShowHide(allOrders, this.innerText)
        })
    }

    ordersFilterInput.addEventListener('keyup', function(){
        ordersFilter(allOrders, this.value.toLowerCase())
    })

    document.getElementById('showButton').addEventListener('click', function() {
    const hiddenDiv = document.getElementById('hiddenDiv');
    if (hiddenDiv.style.display === 'none') {
        hiddenDiv.style.display = 'block';
    } else {
        hiddenDiv.style.display = 'none';
    }

    document.getElementById('submitButton').addEventListener('click', function() {
    const value1 = document.getElementById('value1').value;
    const value2 = document.getElementById('value2').value;

    $.ajax({
            url: 'https://paker-wroclaw.herokuapp.com/production/prepare-orders/',
            data: {'number': value1,
                   'number2': value2},
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
        console.log(data)
        })
});
});

})