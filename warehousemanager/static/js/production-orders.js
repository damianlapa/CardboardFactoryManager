document.addEventListener("DOMContentLoaded", function () {
    const allOrders = document.getElementsByClassName('production-order')
    const ordersBtns = document.getElementsByClassName('production-order-btn')

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
    const value3 = document.getElementById('value3').value;

    $.ajax({
            url: 'https://paker-wroclaw.herokuapp.com/production/prepare-orders/',
            data: {'number': value1,
                   'number2': value2,
                   'year': value3},
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
        // Przetwarzanie danych otrzymanych z zapytania AJAX
        var results = response.results;

        results.forEach(function (item) {
        if (item.exception !== false) {
            var newElement = document.createElement('p');
            var textNode = document.createTextNode('Klient: ' + item.klient + ', Numer zamówienia: ' + item.order_number);
            newElement.appendChild(textNode);

            // Dodanie nowego elementu do istniejącego diva
            var parentDiv = document.getElementById('result');
            parentDiv.appendChild(newElement);
        }else {
            var newElement = document.createElement('p');
            var textNode = document.createTextNode('Numer zamówienia: ' + item.order_number + 'Exception: ' + item.exception);
            newElement.appendChild(textNode);

            // Dodanie nowego elementu do istniejącego diva
            var parentDiv = document.getElementById('result');
            parentDiv.appendChild(newElement);
        }
    });
})
});
});

})