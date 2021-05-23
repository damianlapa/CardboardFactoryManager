document.addEventListener("DOMContentLoaded", function () {

    const selectOption = document.getElementById('select-option')

    const clothes = document.getElementsByClassName('cloth')
    const personClothes = document.getElementsByClassName('person-cloth')
    const workers = document.getElementsByClassName('worker')

    const activeOnly = document.getElementById('active-workers')
    const activeOnlyParagraph = document.getElementsByClassName('active-workers')[0]

    function displayHideElements(option, elements) {
        if (option === 'hide') {
            for (let i=0; i < elements.length; i++) {
                elements[i].style.display = 'none'
            }}
        else if (option === 'display') {
            for (let i=0; i < elements.length; i++) {
                elements[i].style.display = 'block'
            }
        }
        else {}
    }

    function removeAddColors(colorFg, colorBg, elements) {
        for (let i=0; i < elements.length; i++) {
            elements[i].style.color = colorFg
            elements[i].style.background = colorBg
        }
    }

    activeOnly.addEventListener('click', function () {
        if (selectOption.value === 'WORKERS') {
            if (this.checked === true) {
                for (let i=0; i < workers.length; i++) {
                    if (workers[i].dataset.status === 'active') {
                        workers[i].style.display = 'block'
                    }else {
                        workers[i].style.display = 'none'
                    }
                }
            }else {
                displayHideElements('display', workers)
            }
        }
    })

    selectOption.addEventListener('click', function () {
        let value = this.value
        if (value === 'CLOTHES') {
            displayHideElements('hide', workers)
            displayHideElements('display', clothes)
            displayHideElements('hide', personClothes)
            activeOnly.checked = false
            activeOnlyParagraph.style.display = 'none'
        }else if (value === 'WORKERS') {
            displayHideElements('display', workers)
            displayHideElements('hide', clothes)
            displayHideElements('hide', personClothes)
            activeOnlyParagraph.style.display = 'block'
            activeOnly.checked = false
        }else if (value === 'ALL') {
            displayHideElements('hide', workers)
            displayHideElements('hide', clothes)
            displayHideElements('display', personClothes)
            activeOnlyParagraph.style.display = 'none'
        }
        removeAddColors('black', 'white', workers)
        removeAddColors('black', 'white', clothes)
    })

    for (let i=0; i < clothes.length; i++) {
        clothes[i].addEventListener('click', function () {
            clothType = this.dataset.cloth

            removeAddColors('black', 'white', clothes)
            removeAddColors('black', 'white', workers)

            this.style.color = 'white'
            this.style.background = 'black'

            for (let j=0; j < personClothes.length; j++) {
                personClothType = personClothes[j].dataset.cloth
                if (personClothType === clothType) {
                    if (activeOnly.checked === true) {
                        if (personClothWorker.dataset.workerstatus === 'active') {
                            personClothes[j].style.display = 'block'
                        }
                    } else {
                    personClothes[j].style.display = 'block'
                    }
                } else {
                    personClothes[j].style.display = 'none'
                }
            }
        })
    }

    for (let i=0; i < workers.length; i++) {
        workers[i].addEventListener('click', function () {

            removeAddColors('black', 'white', clothes)
            removeAddColors('black', 'white', workers)

            this.style.color = 'white'
            this.style.background = 'black'

            workerId = this.dataset.worker

            for (let j=0; j < personClothes.length; j++) {
                personClothWorker = personClothes[j].dataset.worker
                if (personClothWorker === workerId) {
                    if (activeOnly.checked === 'true') {
                        if (personClothWorker.dataset.status === 'active') {
                            personClothes[j].style.display = 'block'
                        }
                    } else {
                    personClothes[j].style.display = 'block'
                    }
                } else {
                    personClothes[j].style.display = 'none'
                }
            }
        })
    }
})