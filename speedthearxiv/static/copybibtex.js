// One-click: fetch Crossref bibtex for a related DOI, then copy to clipboard
$(document).on('click', '.copy-crossref-bibtex-btn', function() {
    var $btn = $(this);
    var doi = $btn.data('doi');
    if (!doi) return;
    var $svg = $btn.find('svg');
    var origSvg = $svg.prop('outerHTML');
    $btn.html('<span class="spinner-inline"></span>');
    $btn.prop('disabled', true);
    $.ajax({
        type: 'POST',
        url: '/doi',
        contentType: 'application/json',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        data: JSON.stringify({ doi: doi }),
        success: function(data) {
            navigator.clipboard.writeText(data.bibtex).then(function() {
                $btn.html('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-check-lg" viewBox="0 0 16 16"><path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/></svg>');
                $btn.prop('disabled', false);
                setTimeout(function() { $btn.html(origSvg); }, 2000);
            }, function() {
                alert('Could not copy to clipboard');
                $btn.html(origSvg);
                $btn.prop('disabled', false);
            });
        },
        error: function(xhr) {
            var msg = 'Could not fetch Crossref BibTeX for DOI: ' + doi;
            try { msg = xhr.responseJSON.error || msg; } catch(e) {}
            alert(msg);
            $btn.html(origSvg);
            $btn.prop('disabled', false);
        }
    });
});

function copyTextToClipboard() {
    var textToCopy = document.getElementById("textToCopy");
    if (!textToCopy) return;
    var text = textToCopy.textContent;
    var btn = document.getElementById("crossref-copy-btn");
    navigator.clipboard.writeText(text).then(function() {
        if (btn) {
            var svg = btn.querySelector('svg');
            var original = svg.innerHTML;
            svg.innerHTML = '<path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>';
            setTimeout(function() { svg.innerHTML = original; }, 1500);
        }
    });
}

$(document).ready(function() {
    $('#doi-form').on('submit', function(e) {
        e.preventDefault();
        var doi = $('#search_query').val().trim();
        if (!doi) return;
        var btn = $('#doi-search-btn');
        btn.html('<span class="spinner-inline"></span>');
        btn.prop('disabled', true);
        $.ajax({
            type: 'POST', url: '/doi',
            contentType: 'application/json',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            data: JSON.stringify({ doi: doi }),
            success: function(data) {
                btn.html('Search');
                btn.prop('disabled', false);
                $('#doi-result').html('<br><div class="card card-body"><pre id="textToCopy">' + $('<span>').text(data.bibtex).html() + '</pre></div>');
            },
            error: function(xhr) {
                btn.html('Search');
                btn.prop('disabled', false);
                var msg = xhr.responseJSON ? xhr.responseJSON.error : 'Error looking up DOI';
                $('#doi-result').html('<br><div class="alert-msg">' + $('<span>').text(msg).html() + '</div>');
            }
        });
    });
});

document.addEventListener('click', function(e) {
    var btn = e.target.closest('.copy-bibtex-btn');
    if (btn) {
        var bibtex = btn.getAttribute('data-bibtex');
        navigator.clipboard.writeText(bibtex).then(function() {
            var svg = btn.querySelector('svg');
            var original = svg.innerHTML;
            svg.innerHTML = '<path d="M13.854 3.646a.5.5 0 0 1 0 .708l-7 7a.5.5 0 0 1-.708 0l-3.5-3.5a.5.5 0 1 1 .708-.708L6.5 10.293l6.646-6.647a.5.5 0 0 1 .708 0z"/>';
            setTimeout(function() { svg.innerHTML = original; }, 1500);
        });
    }
});