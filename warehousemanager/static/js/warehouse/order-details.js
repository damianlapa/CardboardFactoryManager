document.addEventListener("DOMContentLoaded", function () {
    const delivery = document.getElementById('order_delivered_cbx')
    const finished = document.getElementById('order_finished_cbx')

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

    const toggle = document.getElementById("results-toggle");
    const section = document.getElementById("results-section");

    toggle.addEventListener("click", function() {
      const isVisible = section.style.display === "block";
      section.style.display = isVisible ? "none" : "block";
      toggle.textContent = isVisible ? "Results ▸" : "Results ▾";
    });

})