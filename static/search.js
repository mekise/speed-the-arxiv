$(document).ready(function() {
    $('.search').on('click', function(event) {
        var value = $(this).val();
        loadSearch('/search', value, $(this));
        event.preventDefault();
    });

    $(document).on('click', '#refresh-btn', function(event) {
        var value = $(this).data('search');
        loadSearch('/refresh', value, $(this));
        event.preventDefault();
    });

    // Arxiv ad-hoc search form
    $('#arxiv-search-form').on('submit', function(event) {
        event.preventDefault();
        var query = $('#arxiv-search-query').val().trim();
        if (!query) return;
        var $btn = $('#arxiv-search-btn');
        $btn.html('<span class="spinner-inline"></span>');
        $btn.prop('disabled', true);
        $.ajax({
            type: 'POST',
            url: '/arxiv_search',
            contentType: 'application/json',
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            data: JSON.stringify({
                query: query,
                field: $('#arxiv-search-field').val(),
                max_results: $('#arxiv-search-max').val(),
                sortby: $('#arxiv-search-sortby').val(),
                sortorder: $('#arxiv-search-sortorder').val()
            }),
            success: function(html) {
                var $header = $('#fixed-header');
                $header.find('#search-toolbar').remove();
                var $content = $('#main-content');
                $content.html(html);
                // Move new search toolbar into the fixed header
                var $toolbar = $content.find('#search-toolbar');
                if ($toolbar.length) $toolbar.appendTo($header);
                if (typeof updateBodyPadding === 'function') updateBodyPadding();
                window.scrollTo(0, 0);
                currentPage = 1;
                applyPagination();
            },
            error: function(xhr) {
                var msg = 'Error performing search.';
                try { msg = xhr.responseJSON.error || msg; } catch(e) {}
                $btn.html('Search');
                $btn.prop('disabled', false);
                alert(msg);
            }
        });
    });

    // Save ad-hoc search to Speed the Arxiv
    $(document).on('click', '#save-adhoc-btn', function() {
        var $btn = $(this);
        var name = $('#save-adhoc-name').val().trim();
        if (!name) { alert('Please enter a name for the search'); return; }
        $btn.text('saving...');
        $.ajax({
            type: 'POST',
            url: '/save_adhoc_search',
            contentType: 'application/json',
            data: JSON.stringify({
                name: name,
                query: $btn.data('query'),
                field: $btn.data('field'),
                max_results: $btn.data('max-results'),
                sortby: $btn.data('sortby'),
                sortorder: $btn.data('sortorder')
            }),
            success: function() {
                $btn.text('saved!');
                setTimeout(function() { $btn.text('save to Speed the Arxiv'); }, 2000);
            },
            error: function(xhr) {
                $btn.text('save to Speed the Arxiv');
                var msg = 'Error saving search.';
                try { msg = xhr.responseJSON.error || msg; } catch(e) {}
                alert(msg);
            }
        });
    });

    $('#new-config-btn').on('click', function() {
        $('#new-config-form').toggle();
    });

    $('#create-config-btn').on('click', function() {
        var name = $('#new-cfg-name').val().trim();
        if (!name) { alert('Please enter a config name'); return; }
        var data = { name: name };
        $('#new-config-form .config-input').each(function() {
            var id = $(this).attr('id');
            if (id && id !== 'new-cfg-name') {
                var field = id.replace('new-cfg-', '');
                data[field] = $(this).val();
            }
        });
        $.ajax({
            type: 'POST', url: '/new_config',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() { location.reload(); },
            error: function(xhr) { alert(xhr.responseJSON ? xhr.responseJSON.error : 'Error creating config'); }
        });
    });

    $(document).on('click', '.save-config-btn', function() {
        var block = $(this).closest('.search-config-block');
        var name = block.data('config-name');
        if (!confirm('Save changes to "' + name + '" config?')) return;
        var data = { name: name };
        block.find('.config-input').each(function() {
            data[$(this).data('field')] = $(this).val();
        });
        var btn = $(this);
        btn.text('saving...');
        $.ajax({
            type: 'POST', url: '/save_config',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() { btn.text('saved!'); setTimeout(function() { btn.text('save'); }, 1500); },
            error: function(xhr) { btn.text('save'); alert(xhr.responseJSON ? xhr.responseJSON.error : 'Error saving config'); }
        });
    });

    $(document).on('click', '.delete-config-btn', function() {
        var block = $(this).closest('.search-config-block');
        var name = block.data('config-name');
        if (!confirm('Delete "' + name + '" config?')) return;
        $.ajax({
            type: 'POST', url: '/delete_config',
            contentType: 'application/json',
            data: JSON.stringify({ name: name }),
            success: function() { block.remove(); },
            error: function(xhr) { alert(xhr.responseJSON ? xhr.responseJSON.error : 'Error deleting config'); }
        });
    });

    $(document).on('click', '.reload-config-btn', function() {
        var block = $(this).closest('.search-config-block');
        var name = block.data('config-name');
        var btn = $(this);
        btn.text('reloading...');
        $.ajax({
            type: 'POST', url: '/get_config',
            contentType: 'application/json',
            data: JSON.stringify({ name: name }),
            success: function(cfg) {
                block.find('.config-input').each(function() {
                    var field = $(this).data('field');
                    if (!field) return;
                    var val = cfg[field];
                    if (Array.isArray(val)) val = val.join(', ');
                    $(this).val(String(val));
                });
                btn.text('reloaded!');
                setTimeout(function() { btn.text('reload'); }, 1500);
            },
            error: function(xhr) { btn.text('reload'); alert(xhr.responseJSON ? xhr.responseJSON.error : 'Error reloading config'); }
        });
    });

    $(document).on('click', '.duplicate-config-btn', function() {
        var block = $(this).closest('.search-config-block');
        var origName = block.data('config-name');
        var newName = prompt('Name for the duplicate:', origName + '-copy');
        if (!newName || !newName.trim()) return;
        newName = newName.trim();
        var data = { name: newName };
        block.find('.config-input').each(function() {
            data[$(this).data('field')] = $(this).val();
        });
        $.ajax({
            type: 'POST', url: '/new_config',
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() { location.reload(); },
            error: function(xhr) { alert(xhr.responseJSON ? xhr.responseJSON.error : 'Error duplicating config'); }
        });
    });
});

function loadSearch(url, searchName, $btn) {
    var origHtml = $btn ? $btn.html() : '';
    if ($btn) {
        $btn.html('<span class="spinner-inline"></span>');
        $btn.prop('disabled', true);
    }
    $.ajax({
        type: 'POST',
        url: url,
        contentType: 'application/json',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        data: JSON.stringify({'search': searchName}),
        success: function(html) {
            // Remove old toolbar from fixed header before inserting new content
            var $header = $('#fixed-header');
            $header.find('#search-toolbar').remove();
            var $content = $('#main-content');
            $content.html(html);
            // Move new search toolbar into the fixed header
            var $toolbar = $content.find('#search-toolbar');
            if ($toolbar.length) $toolbar.appendTo($header);
            if (typeof updateBodyPadding === 'function') updateBodyPadding();
            window.scrollTo(0, 0);
            currentPage = 1;
            applyPagination();
        },
        error: function(xhr) {
            var msg = 'Error loading search.';
            try { msg = xhr.responseJSON.error || msg; } catch(e) {}
            if ($btn) {
                $btn.html(origHtml);
                $btn.prop('disabled', false);
            }
            alert(msg);
        }
    });
}