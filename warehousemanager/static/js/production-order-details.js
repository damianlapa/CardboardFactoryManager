document.addEventListener("DOMContentLoaded", function () {

    function changeQuantity (order_id_value, value) {
        $.ajax({
            url: '/production/change-order-quantity/',
            data: {'order_id': order_id_value, 'value': value},
            type: 'GET',
            dataType: 'json'
            }).done(function (data){
            })
    }

    const status = document.getElementById('production-status')
    const selectStatus = document.getElementById('select-status')
    const changeBtn = document.getElementById('change-btn')
    const order_id = document.getElementById('order_id').innerText

    selectStatus.addEventListener('click', function() {
        if (this.value !== status.innerHTML) {
            changeBtn.disabled = false
        }else {
            changeBtn.disabled = true
        }
    })

    const productionOrderQuantity = document.getElementById('production-order-quantity')
    //const

    productionOrderQuantity.addEventListener('click', function () {
        parentEl = this.parentElement
        const children = this.children
//        let quantity_value = this.innerText
        if (children.length === 0) {
            textInput = document.createElement('input')
            textInput.setAttribute('type', 'number')
            textInput.setAttribute('id', 'quantity-input')
            textInput.setAttribute('value', '')
            textInput.style.width = '60%'
            this.innerText = ''
            this.appendChild(textInput)
            textInput.focus()
            submitBtn = document.createElement('button')
            submitBtn.innerHTML = 'Submit'
            this.appendChild(submitBtn)
            submitBtn.addEventListener('click', function() {
                this.style.display = 'none'
                changeQuantity(order_id, textInput.value)
                quantity_value = textInput.value
            })
            textInput.addEventListener('click', function () {
                submitBtn.style.display = 'inline-block'
            })
            textInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    submitBtn.style.display = 'none'
                    changeQuantity(order_id, textInput.value)
                    quantity_value = textInput.value
                }
            })
        }
        else {
            this.innerHTML = ''
            this.innerText = quantity_value
        }
    })
})