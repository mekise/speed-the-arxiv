function openLocalFolder() {
    $.ajax({
        url: "/open_folder",
        method: "POST",
        success: function (response) {
            console.log(response);
        },
        error: function (error) {
            console.log(error);
        }
    });
}