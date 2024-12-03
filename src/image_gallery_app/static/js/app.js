       function viewImage(image) {
                    this.selectedImage = image;
                    console.log("Image sélectionnée :", image);
               }

          function  filteredImages() {
                console.log(this.images);
                if (!this.images || !Array.isArray(this.images)) {
                    alert("problème avec images")
                    return [];
                }

                const searchLower = this.search ? this.search.toLowerCase() : "";

                if (searchLower === "") {
                    return this.images;
                }

                return this.images.filter(image => {
                    return image && image.name && image.name.toLowerCase().includes(searchLower);
                });
            }
new Vue({
    el: '#app',
    data: {
        images: {{ images|tojson  }}, // Importation des images depuis Flask
        searchQuery: '', # {{ search | tojson | safe  }},
        selectedImage: null,
    },
    created: {
      console.log("Images après initialisation:", this.images);  // Vérifie que `images` est bien initialisé
      console.log("Selected Image: ", this.selectedImage);
      console.log("Search: ", search)
    },
    computed: {
        filteredImages
        },
    methods: {
        viewImage
    }
})
