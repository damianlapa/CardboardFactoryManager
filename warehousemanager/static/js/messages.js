document.addEventListener("DOMContentLoaded", function () {

    function hideAllElements (array) {
        for (let i=0; i < array.length; i++) {
            array[i].style.display = 'none'
        }
    }

    function showAllElements (array) {
        for (let i=0; i < array.length; i++) {
            array[i].style.display = 'block'
        }
    }

    function changeClickDisplay(element, option1, option2) {
        if (element.style.display === option1) {
            element.style.display = option2
        }else {
            element.style.display = option1
        }
    }

    const sentMessagesHeader = document.getElementById('sent-messages')
    const receivedMessagesHeader = document.getElementById('received-messages')
    const draftMessagesHeader = document.getElementById('draft-messages')

    const sentMessages = document.getElementsByClassName('sent-message')
    const receivedMessages = document.getElementsByClassName('received-message')
    const draftMessages = document.getElementsByClassName('draft-message')

    const messageTitles = document.getElementsByClassName('message-title')
    const messageContents = document.getElementsByClassName('message-content')

    sentMessagesHeader.addEventListener('click', function () {
        this.classList.add('bg-light-orange')
        receivedMessagesHeader.classList.remove('bg-light-orange')
        draftMessagesHeader.classList.remove('bg-light-orange')
        hideAllElements(receivedMessages)
        hideAllElements(draftMessages)
        showAllElements(sentMessages)
    })

    receivedMessagesHeader.addEventListener('click', function () {
        this.classList.add('bg-light-orange')
        sentMessagesHeader.classList.remove('bg-light-orange')
        draftMessagesHeader.classList.remove('bg-light-orange')
        hideAllElements(sentMessages)
        hideAllElements(draftMessages)
        showAllElements(receivedMessages)
    })

    draftMessagesHeader.addEventListener('click', function () {
        this.classList.add('bg-light-orange')
        sentMessagesHeader.classList.remove('bg-light-orange')
        receivedMessagesHeader.classList.remove('bg-light-orange')
        hideAllElements(sentMessages)
        hideAllElements(receivedMessages)
        showAllElements(draftMessages)
    })

    for (let i=0; i < messageTitles.length; i++) {
        messageTitles[i].addEventListener('click', function() {
            if (this.nextElementSibling.style.display === 'none') {
            // hideAllElements(messageContents)
            changeClickDisplay(this.nextElementSibling, 'none', 'block')
            }else {
            changeClickDisplay(this.nextElementSibling, 'none', 'block')
            }

        })
    }
})