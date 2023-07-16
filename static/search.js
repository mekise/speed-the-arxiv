$(document).ready(function() {
    $('.search').on('click', function(event) {
        var value = $(this).val();
        $.ajax({
            type: 'POST',
            url: '/search',
            contentType: 'application/json',
            data: JSON.stringify({'search': value}),
            success: function(response){document.write(response);}
        });
        event.preventDefault();
    });
});