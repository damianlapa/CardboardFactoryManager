document.addEventListener("DOMContentLoaded", function () {
    const clothes = document.getElementsByClassName('cloth')
    const personClothes = document.getElementsByClassName('person-cloth')

    console.log(personClothes)
    for (let i=0; i < clothes.length; i++) {
        clothes[i].addEventListener('click', function () {
            clothType = this.dataset.cloth
            console.log(clothType)
            for (let j=0; j < personClothes.length; j++) {
                personClothType = personClothes[j].dataset.cloth
                console.log(personClothType)
                if (personClothType === clothType) {
                    personClothes[j].style.display = 'block'
                } else {
                    personClothes[j].style.display = 'none'
                }
            }
        })
    }
})