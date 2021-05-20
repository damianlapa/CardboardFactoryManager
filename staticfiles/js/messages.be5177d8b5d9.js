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

    const composeMessageHeader = document.getElementById('write-message')
    const sentMessagesHeader = document.getElementById('sent-messages')
    const receivedMessagesHeader = document.getElementById('received-messages')
    const draftMessagesHeader = document.getElementById('draft-messages')

    const messageForm = document.getElementById('compose-message')
    const sentMessages = document.getElementsByClassName('sent-message')
    const receivedMessages = document.getElementsByClassName('received-message')
    const draftMessages = document.getElementsByClassName('draft-message')

    const messagesDescription = document.getElementById('messages-description')
    const draftMessagesTitles = document.getElementsByClassName('draft-message-title')

    const messageTitles = document.getElementsByClassName('message-title')
    const messageContents = document.getElementsByClassName('message-content')

    composeMessageHeader.addEventListener('click', function () {
        this.classList.add('bg-light-orange')
        receivedMessagesHeader.classList.remove('bg-light-orange')
        draftMessagesHeader.classList.remove('bg-light-orange')
        sentMessagesHeader.classList.remove('bg-light-orange')
        hideAllElements(receivedMessages)
        hideAllElements(draftMessages)
        hideAllElements(sentMessages)
        messageForm.style.display = 'block'
        messagesDescription.style.display = 'none'
    })

    sentMessagesHeader.addEventListener('click', function () {
        this.classList.add('bg-light-orange')
        receivedMessagesHeader.classList.remove('bg-light-orange')
        draftMessagesHeader.classList.remove('bg-light-orange')
        composeMessageHeader.classList.remove('bg-light-orange')
        hideAllElements(receivedMessages)
        hideAllElements(draftMessages)
        showAllElements(sentMessages)
        messageForm.style.display = 'none'
        messagesDescription.style.display = 'block'
    })

    receivedMessagesHeader.addEventListener('click', function () {
        this.classList.add('bg-light-orange')
        sentMessagesHeader.classList.remove('bg-light-orange')
        draftMessagesHeader.classList.remove('bg-light-orange')
        composeMessageHeader.classList.remove('bg-light-orange')
        hideAllElements(sentMessages)
        hideAllElements(draftMessages)
        showAllElements(receivedMessages)
        messageForm.style.display = 'none'
        messagesDescription.style.display = 'block'
    })

    draftMessagesHeader.addEventListener('click', function () {
        this.classList.add('bg-light-orange')
        sentMessagesHeader.classList.remove('bg-light-orange')
        receivedMessagesHeader.classList.remove('bg-light-orange')
        composeMessageHeader.classList.remove('bg-light-orange')
        hideAllElements(sentMessages)
        hideAllElements(receivedMessages)
        showAllElements(draftMessages)
        messageForm.style.display = 'none'
        messagesDescription.style.display = 'block'
    })

    for (let i=0; i < messageTitles.length; i++) {
        messageTitles[i].addEventListener('click', function() {
            changeClickDisplay(this.nextElementSibling, 'none', 'block')
            if (this.classList.contains('unread-message')) {
                this.classList.remove('unread-message')
                this.classList.remove('bold')
                $.ajax({
                url: '/message-read/' + this.dataset.message + '/',
                data: {},
                type: 'GET',
                dataType: 'json'
                }).done(function (){
                })
            }
        })
    }

    for (let i=0; i < draftMessagesTitles.length; i++) {
        draftMessagesTitles[i].addEventListener('click', function() {
            console.log(this.dataset.message)
            link = 'http://127.0.0.1:8000/messages/?message_id=' + this.dataset.message
            window.open(link, '_self')
        })
    }
})