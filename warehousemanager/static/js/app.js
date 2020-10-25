document.addEventListener("DOMContentLoaded", function () {
    const NewOrderForm = document.querySelectorAll('.new-order')
    const NewItem = document.querySelectorAll('new-order-item')
    if (NewOrderForm !== null) {
        const provider = document.querySelector('.provider')
        const order_num = document.querySelector('.order-number')
        const order_date = document.querySelector('.order-date')
        const add_order_button = document.querySelector('#add-order')
        const order_details = document.querySelector('.order-details')
        const all_orders = document.querySelector('.all-orders')
        const order_description = document.querySelector('.order-description')

        if (provider !== null) {

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
                }

        if (add_order_button !== null) {

            add_order_button.addEventListener('click', function(event){
                let order_name = ''
                order_details.style.display = 'none'
                // all_orders.style.display = 'inline'
                if (order_num.value !== null){
                    if (provider.value === '1') {
                        order_name = 'PAS'
                    }
                    else if (provider.value === '2') {
                        order_name = 'CON'
                    }
                    else if (provider.value === '3') {
                        order_name = 'AQ'
                    }

                    order_name += '/'
                    order_name += order_num.value
                }
                // order_description.innerText = order_name

                $.ajax({
                    url: '/create-new-order/',
                    data: {'provider_num': provider.value},
                    type: 'GET',
                    dataType: 'json'
                }).done(function (data) {
                    if (NewItem !== null) {
                    const OrderId = document.getElementById('id_order')
                    console.log(OrderId)
                    let LastValue = OrderId.options[OrderId.options.length - 1].value
                    OrderId.value = LastValue
                    console.log(LastValue)
                    // OrderId.disabled = true
                    }
                    })

            // event.preventDefault()
        })
        }
        }
    const addOrders = document.querySelector('#add-orders')

    if (addOrders !== null) {
        const orderNumber = document.querySelector('#order-id-number').innerText
        const orderSelect = document.querySelector('#id_order')
        const itemNumber = document.querySelector('#id_item_number')
        const scores = document.querySelector('#id_scores')

        for (let i=0; i < orderSelect.options.length; i++){
            if (parseInt(orderSelect.options[i].value) === parseInt(orderNumber)){
                orderSelect.options[i].selected = true;
                orderSelect.hidden = true;
            }
        }

        $.ajax({
            url: '/nin/',
            data: {'order_num': parseInt(orderNumber)},
            type: 'GET',
            dataType: 'json'
        }).done(function (data) {
        itemNumber.value = parseInt(data)
        })
    }

    // marking an order as completed
    const completeOrderButton = document.querySelector('.save-and-end')

    if (completeOrderButton !== null) {
        completeOrderButton.addEventListener('click', function() {
            $.ajax({
            url: '/complete-order/',
            data: {'order_id': parseInt(this.value)},
            type: 'GET',
            dataType: 'json'
            })
        })
    }

    // marking an order as uncompleted
    const uncompletedOrderButton = document.querySelector('.save')

    // canceling an order
    const cancelButton = document.querySelector('.cancel-order')

    if (cancelButton !== null) {
        cancelButton.addEventListener('click', function() {
            $.ajax({
            url: '/delete-order/',
            data: {'order_id': parseInt(this.value)},
            type: 'GET',
            dataType: 'json'
            })
        })
    }

    // all orders filters
    const filterByProvider = document.querySelector('#filter-by-provider')

    if (filterByProvider !== null) {
        filterByProvider.addEventListener('click', function () {

        const allRows = document.querySelectorAll('.zamowienie')
        const rows = allRows[0].rows
        const tableDescription = document.querySelector('.order-table-description')
        for (let i=0; i < rows.length; i++) {
            console.log(rows[i].classList.value)
            if (rows[i].classList.value === filterByProvider.value) {
                rows[i].style.display = 'table-row'
            }
            else {
                rows[i].style.display = 'none'
            }
        }
        tableDescription.style.display = 'table-row'
        })
    }

    // filling a form from last orders list

    const lastOrderedItems = document.querySelector('.last-ordered-items')

    if (lastOrderedItems !== null) {
        const listElements = lastOrderedItems.getElementsByTagName('ol')
        const newOrderHeight = document.querySelector('#id_format_width')
        const newOrderWidth = document.querySelector('#id_format_height')
        const newOrderDimOne = document.querySelector('#id_dimension_one')
        const newOrderDimTwo = document.querySelector('#id_dimension_two')
        const newOrderDimThree = document.querySelector('#id_dimension_three')
        const newOrderSort = document.querySelector('#id_sort')
        const newOrderWeight = document.querySelector('#id_cardboard_weight')
        const newOrderType = document.querySelector('#id_cardboard_type')
        const newOrderBuyer = document.querySelector('#id_buyer')
        const newOrderScores = document.querySelector('#id_scores')
        for (let i=0; i < listElements.length; i++) {
            listElements[i].addEventListener('click', function() {
                console.log(this.id)
                $.ajax({
                    url: '/gid/',
                    data: {'item_id': listElements[i].id},
                    type: 'GET',
                    dataType: 'json'
                }).done(function (data) {
                console.log(data)
                    newOrderHeight.value = data.height
                    newOrderWidth.value = data.width
                    newOrderDimOne.value = data.dimension_one
                    newOrderDimTwo.value = data.dimension_two
                    if (data.dimension_three !== null) {
                        newOrderDimThree.value = data.dimension_three
                    }
                    else {
                        newOrderDimThree.value = ''
                    }
                    newOrderSort.value = data.sort
                    newOrderWeight.value = data.weight
                    newOrderType.value = data.cardboard_type
                    if (data.buyer === ''){
                        for (let i=0; i < newOrderBuyer.options.length; i++){
                            newOrderBuyer.options[i].selected = false
                        }
                    }
                    else {
                        for (let i=0; i < newOrderBuyer.options.length; i++){
                            if (newOrderBuyer.options[i].innerText === data.buyer) {
                                newOrderBuyer.options[i].selected = true
                            }
                        }
                    }
                    newOrderScores.value = data.scores
                    })
            })
        }
    }

    const buyerSelector = document.querySelector('#id_buyer')

    if (buyerSelector !== null) {
        buyerSelector.addEventListener('click', function () {
            let selectedOption = ''
            const allFormats = document.querySelector('.right-column-1').querySelectorAll('p')
            for (let i=0; i < buyerSelector.options.length; i++){
                if (buyerSelector.options[i].selected === true){
                    selectedOption = buyerSelector.options[i].innerText
                    console.log(selectedOption)
                    for (let j=0; j < allFormats.length; j++){
                        console.log(allFormats[j].classList.value)
                        if (allFormats[j].classList.value === selectedOption) {
                            allFormats[j].style.display = 'block'
                        }
                        else {
                            allFormats[j].style.display = 'none'
                        }
                    }

                }
            }
        })
    }

})