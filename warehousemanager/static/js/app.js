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
    const ordersFilterBtn = document.getElementById('order-filters')

    if (ordersFilterBtn !== null) {
        const orderFiltersContainer = document.getElementById('order-filters-container')
        ordersFilterBtn.addEventListener('click', function () {
            state = orderFiltersContainer.style.display
            if (state === 'none' || state === ''){
                orderFiltersContainer.style.display = 'block'}
            else{
                 orderFiltersContainer.style.display = 'none'
            }
        })
    }

    const filterByProvider = document.querySelector('#filter-by-provider')

    if (filterByProvider !== null) {
        filterByProvider.addEventListener('click', function () {

        const allRows = document.querySelectorAll('.zamowienie')
        const rows = allRows[0].rows
        const tableDescription = document.querySelector('.order-table-description')
        for (let i=0; i < rows.length; i++) {
            if (rows[i].classList.contains(filterByProvider.value)) {
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


    const newOrderWidth = document.querySelector('#id_format_width')
    const newOrderHeight = document.querySelector('#id_format_height')
    const newOrderDimOne = document.querySelector('#id_dimension_one')
    const newOrderDimTwo = document.querySelector('#id_dimension_two')
    const newOrderDimThree = document.querySelector('#id_dimension_three')
    const newOrderSort = document.querySelector('#id_sort')
    const newOrderWeight = document.querySelector('#id_cardboard_weight')
    const newOrderType = document.querySelector('#id_cardboard_type')
    const newOrderBuyer = document.querySelector('#id_buyer')
    const newOrderName = document.querySelector('#id_name')
    const newOrderScores = document.querySelector('#id_scores')

    function autoFillNewOrder (listElements) {
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
                    newOrderName.value = data.name
                    newOrderScores.value = data.scores
                    })
            })
        }
    }

    if (lastOrderedItems !== null) {
        const listElements = lastOrderedItems.getElementsByTagName('ol')
        autoFillNewOrder(listElements)
    }

    const buyerSelector = document.querySelector('#id_buyer')

    if (buyerSelector !== null) {
        buyerSelector.addEventListener('click', function () {
            let selectedOption = ''
            const allFormats = document.querySelector('.right-column-1').querySelectorAll('p')
            autoFillNewOrder(allFormats)
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
                        if (data[0][i][2] === 'CH') {
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
                    extraHours[0].style.backgroundColor = '#59E817'
                    extraHours[0].style.color = 'black'
                    extraHours[0].style.textAlign = 'center'
                    }
            }
            for (let s=0; s < data[3].length; s++){
                    worker_id = 'worker' + String(data[3][s][0])
                    day_id = 'day' + String(data[3][s][1])
                    query_text = worker_id + ' ' + day_id
                    let extraHours = document.getElementsByClassName(query_text)
                    if (extraHours.length > 0) {
                    extraHours[0].innerText = data[3][s][2]
                    extraHours[0].style.backgroundColor = '#806517'
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

    const fefcoTypesBtns = document.getElementsByClassName('fefco-type')
    const typeCells = document.getElementsByClassName('punch-type')

    if (filterPunchesBtn !== null) {
        const filterContainer = document.getElementById('punch-filters')
        filterPunchesBtn.addEventListener('click', function () {
        console.log(filterContainer.style.display)
            if (filterContainer.style.display === 'none' || filterContainer.style.display === '') {
                console.log('click')
                filterContainer.style.display = 'flex'
                filterPunchesBtn.style.backgroundColor = 'pink'
            }
            else {
                filterContainer.style.display = 'none'
                filterPunchesBtn.style.backgroundColor = 'red'
            }
        })

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

    const nameFilter = document.getElementById('name-filter')

    if (nameFilter) {
        nameFilter.addEventListener('keyup', function () {
            for (let f=0; f < allRows.length; f++) {
                if (nameFilter.value.length === 0) {
                    allRows[f].style.display = 'table-row';
                    for (let x=0; x < fefcoTypesBtns.length; x++) {
                        if (fefcoTypesBtns[x].classList.contains('fefco-type-click')) {
                            if (fefcoTypesBtns[x].value !== 'all'){
                            fefcoTypesBtns[x].classList.remove('fefco-type-click')
                            }
                        }else {
                            if (fefcoTypesBtns[x].value === 'all'){
                            fefcoTypesBtns[x].classList.add('fefco-type-click')
                            }
                        }
                    }
                }else if (allRows[f].style.display === 'table-row' || allRows[f].style.display === '' || allRows[f].style.display === 'none') {
                    if (allRows[f].children[5].innerText.toLowerCase().includes(nameFilter.value.toLowerCase())) {
                        allRows[f].style.display = 'table-row'
                    }else {
                        allRows[f].style.display = 'none'
                    }
                }
            }
        })
    }

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

    function filterWhenExists(input, comparator, element, input2, comparator2) {
        if (input !== null) {
            if (input === comparator) {
                element.style.display = 'table-row'
                if (input2 !== '') {
                    if (input2 === comparator2) {
                        element.style.display = 'table-row'
                    }
                    else {
                        element.style.display = 'none'
                    }
                }
            } else {
                element.style.display = 'none'
            }
        }
    }

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
                            filterWhenExists(lengthValue, allRows[i].children[3].innerText, allRows[i], heightValue, allRows[i].children[4].innerText)
                        }
                        else {
                            allRows[i].style.display = 'none'
                        }
                    }else if (lengthValue !== ''){
                        if (lengthValue === allRows[i].children[3].innerText) {
                            allRows[i].style.display = 'table-row'
                            filterWhenExists(widthValue, allRows[i].children[2].innerText, allRows[i], heightValue, allRows[i].children[4].innerText)
                        }
                        else {
                            allRows[i].style.display = 'none'
                        }
                    }else if (heightValue !== ''){
                        if (heightValue === allRows[i].children[4].innerText) {
                            allRows[i].style.display = 'table-row'
                            filterWhenExists(widthValue, allRows[i].children[2].innerText, allRows[i], lengthValue, allRows[i].children[3].innerText)
                        }
                        else {
                            allRows[i].style.display = 'none'
                        }
                    }
                    /*
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
                    */
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
                window.open(link, '_self')
            })
        }
    }

    const cardboardChoice = document.getElementById('id_cardboard')

    if (cardboardChoice !== null) {

        for (let i=0; i < cardboardChoice.children.length; i++){
            if ( isNaN(cardboardChoice.children[i]) ) {

            }else {
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

    }

    // warning about uncompleted orders before add a new one

    const warningBtn = document.getElementById('continue-with-uc')
    const addOrderDiv = document.getElementsByClassName('add-order')
    const warningDiv = document.getElementsByClassName('uc-orders')

    if (warningBtn !== null) {
        warningBtn.addEventListener('click', function () {
            warningDiv[0].style.display = 'none'
            addOrderDiv[0].style.display = 'block'
        })
    }

    // function checking correctness

    function ScoresCorrectness(scores) {
        if (scores[0] !== scores[scores.length - 1]){
            return false
        }
        return true
    }

    function FormatCorrectness(type, cardboard, fDim1, fDim2, dim1, dim2, dim3, scores){
        fDim1 = parseInt(fDim1)
        fDim2 = parseInt(fDim2)

        dim1 = parseInt(dim1)
        dim2 = parseInt(dim2)
        if (dim3 !== null){
            dim3 = parseInt(dim3)
        }

        if (dim2 % 2 === 1){
            dim2 += 1
        }

        switch(type){
            case '201':
                switch(cardboard){
                    case 'B':

                    condition1 = ((fDim1 === 2*(dim1 + dim2) + 49) && (fDim2 === dim2 + dim3 + 12 ));
                    condition2 = ((fDim1 === dim1 + dim2 + 42) && (fDim2 === dim2 + dim3 + 12 ));
                    console.log(condition1, condition2)
                    console.log(dim1, dim2, dim3)
                    console.log(dim1 + dim2)
                    scoresCorrectness = ScoresCorrectness(scores)
                    return (condition1 || condition2) && scoresCorrectness;
                    case 'C':
                    condition1 = ((fDim1 === 2*(dim1 + dim2) + 49) && (fDim2 === dim2 + dim3 + 13 ));
                    condition2 = ((fDim1 === dim1 + dim2 + 47) && (fDim2 === dim2 + dim3 + 13 ));
                    console.log(condition1, condition2)
                    console.log(dim1, dim2, dim3)
                    console.log(dim1 + dim2)
                    return condition1 || condition2;
                    case 'BC':
                    condition1 = ((fDim1 === 2*(dim1 + dim2) + 60) && (fDim2 === dim2 + dim3 + 22 ));
                    condition2 = ((fDim1 === dim1 + dim2 + 47) && (fDim2 === dim2 + dim3 + 22 ));
                    return condition1 || condition2;
                }
            case '202':
                return true;
            case '203':
                return true;
            default:
                return true;
        }
    }

    // checking correctness ordered item

    const formAddContainer = document.getElementById('add-items-container')
    const allOrderedItems = document.getElementsByClassName('order-item-add')

    if (formAddContainer !== null) {
        for (let i=0; i<allOrderedItems.length; i++){
            if (allOrderedItems[i].children[1].innerText === '203'){
                allOrderedItems[i].style.backgroundColor = 'pink'
            }

            type = allOrderedItems[i].children[1].innerText
            cardboard = allOrderedItems[i].children[6].innerText
            cardboard_type = cardboard.split(/([0-9]+)/)[0]
            width = parseInt(allOrderedItems[i].children[2].innerText)
            height = parseInt(allOrderedItems[i].children[3].innerText)
            boxDimensions = allOrderedItems[i].children[7].innerText.split(/([0-9]+)/)
            scores = allOrderedItems[i].children[8].innerText.split(/([0-9]+)/)

            scores_result = scores.filter(score => score.length > 1)

            console.log(scores_result)

            if (boxDimensions.length > 5){
                dim1 = parseInt(boxDimensions[1])
                dim2 = parseInt(boxDimensions[3])
                dim3 = parseInt(boxDimensions[5])
            }else {
                dim1 = parseInt(boxDimensions[1])
                dim2 = parseInt(boxDimensions[3])
                dim3 = 0
            }

            if (FormatCorrectness(type, cardboard_type, width, height, dim1, dim2, dim3, scores_result) === false){
                allOrderedItems[i].style.backgroundColor = 'red'
            }

            // result = FormatCorrectness(type, cardboard_type, 1, 1, 1, 1, 1)
        }
    }

    // usuwanie wykrojnika

    const deletePunchBtn = document.getElementById('delete-punch')

    if (deletePunchBtn !== null) {
        deletePunchBtn.addEventListener('click', function () {
            if (!confirm('Are you sure that you want to delete this punch?')) {
                event.preventDefault(); }
        })
    }

    const deliveriesRows = document.getElementsByClassName('delivery-row')

    if (deliveriesRows.length > 0) {
        for (let i=0; i < deliveriesRows.length; i++) {
            deliveriesRows[i].addEventListener('click', function () {
                link = localLink + 'delivery/' + deliveriesRows[i].dataset.delivery
                window.location.replace(link)
            })
        }
    }

    const stateCells = document.getElementsByClassName('state-cell')

    if (stateCells.length > 0) {
        for (let i=0; i < stateCells.length; i++) {
            stateCells[i].addEventListener('click', function () {
                event.preventDefault();
                $.ajax({
                    url: '/oic/',
                    data: {'order_item_id': stateCells[i].parentElement.dataset.orderitemid},
                    type: 'GET',
                    dataType: 'json'
                }).done(function (data) {
                    if (data === true) {
                        stateCells[i].innerHTML = '<i class="demo-icon icon-toggle-on">'
                        stateCells[i].children[0].style.color = 'green'
                    }else {
                        stateCells[i].innerHTML = '<i class="demo-icon icon-toggle-off">'
                        stateCells[i].children[0].style.color = 'red'
                    }
                    })
            })
        }
    }


    const printCells = document.getElementsByClassName('print-icon')

    if (printCells.length > 0) {
        for (let i=0; i < printCells.length; i++) {
            printCells[i].addEventListener('auxclick', function () {
            $.ajax({
                    url: '/get-local-var/PAKER_MAIN/',
                    data: {},
                    type: 'GET',
                    dataType: 'json'
                    }).done(function (data) {
                        link = data + 'gst/?orderitemid=' + printCells[i].parentElement.dataset.orderitemid
                        window.open(link, '_blank')
                        })
            })
            printCells[i].addEventListener('click', function () {
            $.ajax({
                    url: '/get-local-var/PAKER_MAIN/',
                    data: {},
                    type: 'GET',
                    dataType: 'json'
                    }).done(function (data) {
                        link = data + 'gst/?orderitemid=' + printCells[i].parentElement.dataset.orderitemid
                        window.open(link, '_blank')
                        })
            })
        }
    }

    const orderItems = document.getElementsByClassName('zamowienie-row')

    for (let i=0; i < orderItems.length; i++) {

        let nf = 0

        if (orderItems[i].children[0].classList.contains('order-num')) {
            nf = 2
        }

        let dimensions = orderItems[i].children[8 + nf].innerText.split('x')
        let cardboard_full = orderItems[i].children[7 + nf].innerText
        let cardboard = ''

        if (cardboard_full.charAt(0) === '3') {
            cardboard = cardboard_full.charAt(1)
        }
        else if (cardboard_full.charAt(0) === '5') {
            cardboard = cardboard_full.charAt(1) + cardboard_full.charAt(2)
        }

        let type = orderItems[i].children[1 + nf].innerText
        // let cardboard = orderItems[i].children[9]
        let format_width = orderItems[i].children[2 + nf].innerText
        let format_height = orderItems[i].children[3 + nf].innerText
        let dimension1 = dimensions[0]
        let dimension2 = dimensions[1]
        let dimension3 = dimensions[2]
        let scores = orderItems[i].children[10 + nf]

        if (FormatCorrectness(type, cardboard, format_width, format_height, dimension1, dimension2, dimension3, scores)) {
        }else {
            orderItems[i].style.backgroundColor = 'orange'
        }

        for (let j=0; j < orderItems[i].children.length; j++) {
            if (!(orderItems[i].children[j].classList.contains('state-cell') || orderItems[i].children[j].classList.contains('print-icon'))) {
                    orderItems[i].children[j].addEventListener('click', function () {
                    $.ajax({
                    url: '/get-local-var/PAKER_MAIN/',
                    data: {},
                    type: 'GET',
                    dataType: 'json'
                    }).done(function (data) {
                        link = data + 'order-item-details/' + orderItems[i].dataset.orderitemid + '/'
                        window.location.replace(link)
                        })
                    })
                }
        }
    }

    const manySheetsForm = document.getElementById('many-sheets')

    if (manySheetsForm !== null) {
        const allItems = manySheetsForm.children[1]
        const pickedItems = document.getElementById('picked-items')
        const prepareBtn = document.getElementById('prepare-sheets')

        const orderNames = document.getElementsByClassName('order-name')

        const picked = document.getElementsByClassName('picked')

        const allListItems = document.getElementsByClassName('order-item')

        for (let i=0; i < orderNames.length; i++){
            orderNames[i].addEventListener('click', function () {
                var order = orderNames[i].cloneNode(true)
                pickedItems.appendChild(order)
                orderNames[i].style.display = 'none'
            })
        }

        for (let i=0; i < allListItems.length; i++) {
            allListItems[i].addEventListener('click', function () {
                var element = allListItems[i].cloneNode(true)
                element.classList.toggle('picked')
                allListItems[i].style.display = 'none'
                pickedItems.appendChild(element)

            })
        }

        prepareBtn.addEventListener('click', function () {
            let allItemsText = ''
            for (let i=0; i < picked.length; i++) {
                allItemsText += picked[i].dataset.itemid
                allItemsText += '*'
            }
            $.ajax({
                url: '/prepared-gs/',
                data: {'items_nums': allItemsText},
                type: 'GET',
                dataType: 'json'
                }).done(function (data) {
                    console.log(data)
                })

            manySheetsForm.style.display = 'none'
        })
    }

    const printLinks = document.getElementsByClassName('print-link')

    if (printLinks.length > 0) {
        for (let i=0; i < printLinks.length; i++) {
            printLinks[i].addEventListener('click', function () {

                link = 'https://docs.google.com/spreadsheets/d/' + printLinks[i].dataset.printlink + '/edit#gid=1727884471'
                window.open(link, '_blank')
            })

        }
    }

    const polymerRows = document.getElementsByClassName('polymer-row')

    if (polymerRows.length > 0) {
        for (let i=0; i < polymerRows.length; i++){
            polymerRows[i].addEventListener('click', function () {

                link = localLink + 'polymer/' + polymerRows[i].dataset.polymerid + '/'
                window.open(link, '_self')

            })
        }
    }

    // edycja polimerów

    const editPolymerCells = document.getElementsByClassName('edit-polymer')

    if (editPolymerCells.length > 0) {
        for (let i=0; i < editPolymerCells.length; i++) {
            editPolymerCells[i].addEventListener('click', function () {
            $.ajax({
                    url: '/get-local-var/PAKER_MAIN/',
                    data: {},
                    type: 'GET',
                    dataType: 'json'
                    }).done(function (data) {
                        link = data + 'polymer-update/' + editPolymerCells[i].parentElement.dataset.polymerid + '/'
                        window.open(link, '_self')
                        })
            })
            }}

    // kasowanie polimwerów

    const deletePolymerCells = document.getElementsByClassName('delete-polymer')

    if (deletePolymerCells.length > 0) {
        for (let i=0; i < deletePolymerCells.length; i++) {
            deletePolymerCells[i].addEventListener('click', function () {
            $.ajax({
                    url: '/get-local-var/PAKER_MAIN/',
                    data: {},
                    type: 'GET',
                    dataType: 'json'
                    }).done(function (data) {
                        link = data + 'polymer-delete/' + deletePolymerCells[i].parentElement.dataset.polymerid + '/'
                        window.open(link, '_self')
                        })
            })
            }}

    // funkcja kasowania/edytowania elementow przedstawionych w tabeli

    function deleteOrEdit(cells, path) {
        if (cells.length > 0) {
            for (let i=0; i < cells.length; i++) {
                cells[i].addEventListener('click', function () {
                $.ajax({
                        url: '/get-local-var/PAKER_MAIN/',
                        data: {},
                        type: 'GET',
                        dataType: 'json'
                        }).done(function (data) {
                            link = data + path + cells[i].parentElement.dataset.serviceid + '/'
                            window.open(link, '_self')
                            })
            })
            }
        }
    }

    const deleteServiceCells = document.getElementsByClassName('delete-service')
    const editServiceCells = document.getElementsByClassName('edit-service')

    console.log(editServiceCells)

    deleteOrEdit(deleteServiceCells, 'service-delete/')
    deleteOrEdit(editServiceCells, 'service-update/')

    const colors = document.getElementsByClassName('color-item')

    for (let i=0; i < colors.length; i++){
        colors[i].addEventListener('click', function () {
            $.ajax({
                url: '/get-local-var/PAKER_MAIN/',
                data: {},
                type: 'GET',
                dataType: 'json'
                }).done(function (data) {
                    link = data + 'color/' + colors[i].dataset.colorid + '/'
                    window.open(link, '_self')
                    })
        })
    }

})

function drag(ev) {
      ev.dataTransfer.setData("text", ev.target.id);
      console.log('ok')
    }

function allowDrop(ev) {
  ev.preventDefault();
}

function drop(ev) {
  ev.preventDefault();
  var data = ev.dataTransfer.getData("text");
  console.log(data)
  ev.target.appendChild(document.getElementById(data));
}