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

    const NewOrderForm = document.querySelectorAll('.new-order')
    const NewItem = document.querySelectorAll('new-order-item')
    if (NewOrderForm !== null) {
        const provider = document.querySelector('#id_provider')
        const order_num = document.querySelector('#id_order_provider_number')
        const order_date = document.querySelector('#id_date_of_order')
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
                    let LastValue = OrderId.options[OrderId.options.length - 1].value
                    OrderId.value = LastValue
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
            data: {'order_id': parseInt(this.value), 'state': 'c'},
            type: 'GET',
            dataType: 'json'
            })
        })
    }

    // marking an order as uncompleted
    const uncompletedOrderButton = document.querySelector('.save')

    if (uncompletedOrderButton !== null) {
        uncompletedOrderButton.addEventListener('click', function() {
            $.ajax({
            url: '/complete-order/',
            data: {'order_id': parseInt(this.value), 'state': 'uc'},
            type: 'GET',
            dataType: 'json'
            })
        })
    }

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
                $.ajax({
                    url: '/gid/',
                    data: {'item_id': listElements[i].id},
                    type: 'GET',
                    dataType: 'json'
                }).done(function (data) {
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
                    for (let j=0; j < allFormats.length; j++){
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

    // cardboard format converter

    function FormatConverter(dim_1, dim_2, dim_3, box_type, cardboard_type) {

    dim_1 = parseInt(dim_1)
    dim_2 = parseInt(dim_2)
    dim_3 = parseInt(dim_3)

    let width = 0
    let height = 0

    if (box_type == 201 || box_type == 202) {
        width = 2*(dim_1 + dim_2)
        height = dim_2 + dim_3
    }else if(box_type == 203){
        width = 2*(dim_1 + dim_2)
        height = 2*dim_2 + dim_3
    }else {
        width = 0
        height = 0
    }

    if (cardboard_type === 'b') {
        width += 49
        height += 12
    }else if (cardboard_type === 'c') {
        width += 53
        height += 12
    }else if (cardboard_type === 'e') {
        width += 49
        height += 12
    }else if (cardboard_type === 'eb') {
        width += 53
        height += 10
    }else {
        width += 60
        height += 22
    }
    return [width, height]
    }

    // page to convert

    const converterDiv = document.querySelector('.converter-div')

    // if page exists

    if (converterDiv !== null) {
        // all values
        const boxType = document.querySelector('#sort-select')
        const cardboardType = document.querySelector('#cardboard-select')
        const boxWidth = document.querySelector('#width')
        const boxLength = document.querySelector('#length')
        const boxHeight = document.querySelector('#height')
        const result = document.querySelector('#cardboard-format')

        converterDiv.addEventListener('click', function () {

            re = FormatConverter(boxWidth.value, boxLength.value, boxHeight.value, boxType.value, cardboardType.value)

            result.innerText = String(re[0]) + 'x' + String(re[1])
        })


    }

    const AbsenceList = document.querySelector('.absence-list')
    const monthSelect = document.querySelector('#monthSelect')

    if (AbsenceList !== null) {
        $.ajax({
        url: '/absences/',
        data: {'month': monthSelect.value},
        type: 'GET',
        dataType: 'json'
        }).done(function (data) {
            for (let i=0; i < data[0].length; i++){
                day_text = 'day' + data[0][i][1]
                if (data[0][i][0] >= 0){
                    worker_text = 'worker' + data[0][i][0]
                    query_text = worker_text + ' ' + day_text
                    let absenceField = document.getElementsByClassName(query_text)
                    if (absenceField.length > 0) {
                        if (data[0][i][2] === 'UZ') {
                            console.log(data[0][i])
                        }
                        absenceField[0].innerText = data[0][i][2]
                        absenceField[0].style.backgroundColor = 'red'
                        absenceField[0].style.color = 'white'
                        absenceField[0].style.textAlign = 'center'
                    }}
                else {
                    let holidayFields = document.getElementsByClassName(day_text)
                    holidayFields[0].colSpan = holidayFields.length
                    holidayFields[0].innerText = data[0][i][2]
                    holidayFields[0].style.backgroundColor = 'pink'
                    holidayFields[0].style.textAlign = 'center'
                    holidayFieldsLength = holidayFields.length
                    for (let j=holidayFieldsLength - 1; j > 0; j--){
                        holidayFields[j].remove()
                    }
                }
            }
            for (let x=0; x < data[1].length; x++){
                for (let y=0; data[1][x][1][y]; y++){
                    worker_id = 'worker' + String(data[1][x][0])
                    day_id = 'day' + String(data[1][x][1][y])
                    query_text = worker_id + ' ' + day_id
                    let nonWorkField = document.getElementsByClassName(query_text)
                    if (nonWorkField.length > 0) {
                    nonWorkField[0].innerText = ''
                    nonWorkField[0].style.backgroundColor = 'white'
                    nonWorkField[0].style.color = 'white'
                    nonWorkField[0].style.textAlign = 'center'
                    }
                }
            }
            for (let z=0; z < data[2].length; z++){
                    worker_id = 'worker' + String(data[2][z][0])
                    day_id = 'day' + String(data[2][z][1])
                    query_text = worker_id + ' ' + day_id
                    let extraHours = document.getElementsByClassName(query_text)
                    if (extraHours.length > 0) {
                    extraHours[0].innerText = data[2][z][2]
                    extraHours[0].style.backgroundColor = 'blue'
                    extraHours[0].style.color = 'white'
                    extraHours[0].style.textAlign = 'center'
                    }
            }})
        monthSelect.addEventListener('click', function () {
            $.ajax({
            url: '/get-local-var/PAKER_MAIN/',
            data: {},
            type: 'GET',
            dataType: 'json'
            }).done(function (data) {
                link = data + 'absences-list/?month=' + monthSelect.value
                window.location.replace(link)
                })
        })
    }

    // add absences form
    const absencesButtonsContainer = document.getElementById('absenceAddContainer')
    const addShortAbsenceButton = document.getElementById('short-A')
    const addLongAbsenceButton = document.getElementById('long-A')
    const shortAbsenceForm = document.getElementById('shortAbsenceForm')

    if (absencesButtonsContainer !== null ) {
            addShortAbsenceButton.addEventListener('click', function () {
                absencesButtonsContainer.style.display = 'none';
                shortAbsenceForm.style.display = 'block';
            })
            addLongAbsenceButton.addEventListener('click', function () {
                absencesButtonsContainer.style.display = 'none';
                longAbsenceForm.style.display = 'block';
            })
        }

    const prevBtn = document.getElementById('prevBtn')
    const nextBtn = document.getElementById('nextBtn')

    const filterPunchesBtn = document.getElementById('punch-filters-button')

    if (filterPunchesBtn !== null) {
        const filterContainer = document.getElementById('punch-filters')
        filterPunchesBtn.addEventListener('click', function () {
            if (filterContainer.style.display === 'none') {
                filterContainer.style.display = 'flex'
                filterPunchesBtn.style.backgroundColor = 'pink'
            }
            else {
                filterContainer.style.display = 'none'
                filterPunchesBtn.style.backgroundColor = 'red'
            }
        })

        const fefcoTypesBtns = document.getElementsByClassName('fefco-type')
        const typeCells = document.getElementsByClassName('punch-type')

        for (let i=0; i < fefcoTypesBtns.length; i++){
            fefcoTypesBtns[i].addEventListener('click', function () {
                for (let x=0; x < fefcoTypesBtns.length; x++){
                    if (fefcoTypesBtns[x].classList.contains('fefco-type-click')) {
                        fefcoTypesBtns[x].classList.toggle('fefco-type-click')
                    }
                }
                fefcoTypesBtns[i].classList.toggle('fefco-type-click')

                for (let j=0; j < typeCells.length; j++){
                    if (fefcoTypesBtns[i].value === typeCells[j].innerText){
                        typeCells[j].parentElement.style.display = 'table-row'
                    }
                    else if (fefcoTypesBtns[i].value === 'all'){
                        typeCells[j].parentElement.style.display = 'table-row'
                    }
                    else {
                        typeCells[j].parentElement.style.display = 'none'
                    }
                filterByDimension(true)
                }
            })
        }
    }

    const dimOne = document.getElementById('dim1')
    const dimTwo = document.getElementById('dim2')
    const dimThree = document.getElementById('dim3')

    const widthFormat = document.getElementsByClassName('dim1')
    const lengthFormat = document.getElementsByClassName('dim2')
    const heightFormat = document.getElementsByClassName('dim3')

    const allRows = document.getElementsByClassName('punch-row')

    /*
    if (dimOne !== null){

        dimensionFilters = [dimOne, dimTwo, dimThree]

        for (let i=0; i < dimensionFilters.length; i++){
            dimensionFilters[i].addEventListener('keyup', function () {
                if (i === 0){
                    console.log(dimensionFilters[i].value)
                    for (let j=0; j < widthFormat.length; j++){
                        if (parseInt(widthFormat[j].innerText) > parseInt(dimensionFilters[i].value)){
                            widthFormat[j].parentElement.style.display = 'table-row'
                        }
                        else if (dimensionFilters[i].value === '') {
                            console.log('ok')
                        }
                        else {
                            widthFormat[j].parentElement.style.display = 'none'
                        }
                    }
                }
            })
        }
    }
    */

    function filterByDimension(onlyDisplayed) {
        var widthValue = dimOne.value
        var lengthValue = dimTwo.value
        var heightValue = dimThree.value

        for (let i=0; i < allRows.length; i++){
            if (onlyDisplayed === true) {
                if (allRows[i].style.display === 'table-row') {
                    if (widthValue !== ''){
                        if (widthValue === allRows[i].children[2].innerText) {
                            allRows[i].style.display = 'table-row'
                        }
                        else {
                            allRows[i].style.display = 'none'
                        }
                    }
                    if (lengthValue !== ''){
                        if (lengthValue === allRows[i].children[3].innerText) {
                            allRows[i].style.display = 'table-row'
                        }
                        else {
                            allRows[i].style.display = 'none'
                        }
                    }
                    if (heightValue !== ''){
                        if (heightValue === allRows[i].children[4].innerText) {
                            allRows[i].style.display = 'table-row'
                        }
                        else {
                            allRows[i].style.display = 'none'
                        }
                    }
                }
            }
            else {
                if (widthValue !== ''){
                    if (widthValue === allRows[i].children[2].innerText) {
                        allRows[i].style.display = 'table-row'
                    }
                    else {
                        allRows[i].style.display = 'none'
                    }
                }
                if (lengthValue !== ''){
                    if (lengthValue === allRows[i].children[3].innerText) {
                        allRows[i].style.display = 'table-row'
                    }
                    else {
                        allRows[i].style.display = 'none'
                    }
                }
                if (heightValue !== ''){
                    if (heightValue === allRows[i].children[4].innerText) {
                        allRows[i].style.display = 'table-row'
                    }
                    else {
                        allRows[i].style.display = 'none'
                    }
                }
            }
        }

    }

    const filterDimBtn = document.getElementById('dim-filter-btn')

    if (filterDimBtn !== null) {
        filterDimBtn.addEventListener('click', function() {
        filterByDimension(false)
    })
    }

    if (allRows.length > 0) {
        for (let i=0; i < allRows.length; i++) {
            allRows[i].addEventListener('click', function () {
                link = localLink + 'punch/' + allRows[i].dataset.punch_id
                window.open(link, '_blank')
            })
        }
    }

    const cardboardChoice = document.getElementById('id_cardboard')

    if (cardboardChoice !== null) {

        for (let i=0; i < cardboardChoice.children.length; i++){
            let slug = '/cardboard-availability/' + String(cardboardChoice[i].value)
            $.ajax({
            url: slug,
            data: {},
            type: 'GET',
            dataType: 'json'
            }).done(function (data) {
                if (data === true) {
                    cardboardChoice.children[i].style.display = 'none'
                }
            })

        }

    }
})