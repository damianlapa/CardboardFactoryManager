function createOrderElement(order) {
    // Określenie koloru w zależności od statusu
    let bgClass = '';
    if (order.status === 'PLANNED') bgClass = 'bg-orange';
    else if (order.status === 'FINISHED') bgClass = 'bg-green';
    else if (order.status === 'COMPLETED') bgClass = 'bg-yellow';
    else if (order.status === 'ORDERED') bgClass = 'bg-pink';

    // Tworzenie elementu
    const orderDiv = `
    <a href="/production/order/details/${order.id}/" class="no-decor black">
        <div
            data-orderstatus="${order.status}"
            data-idnumber="${order.id_number}"
            data-cardboard="${order.cardboard}"
            data-cardboarddimensions="${order.cardboard_dimensions}"
            data-customer="${order.customer}"
            data-dimensions="${order.dimensions}"
            data-quantity="${order.quantity}"
            data-notes="${order.notes}"
            class="production-order prod-item ${bgClass}">

            <p>${order.id_number}</p>
            <p>${order.customer}</p>
            <p>${order.dimensions}</p>
            <p>${order.cardboard}</p>
            <p>${order.cardboard_dimensions}</p>
            <h4 class="${order.status === 'PLANNED' ? 'red' : ''}">${order.status}</h4>

            ${order.status === 'PLANNED' ? `<p>${order.planned_end}</p>` : ''}
        </div>
    </a>
    `;
    return orderDiv;
}

function loadOrders(query = '') {
    $.ajax({
        url: "{% url 'add-more-orders' %}",
        data: { 'query': query },
        dataType: 'json',
        success: function(data) {
            $('#orders').empty();
            data.orders.forEach(function(order){
                $('#orders').append(createOrderElement(order));
            });
        }
    });
}

$(document).ready(function(){
    // Początkowe ładowanie
    loadOrders();

    // Wyszukiwanie
    $('#search').on('input', function(){
        loadOrders($(this).val());
    });
});