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

    // Notes panel: auto-show abstract and load content on open
    $(document).on('show.bs.collapse', '.notes-panel', function() {
        var $panel = $(this);
        var arxivId = $panel.attr('data-arxiv-id');
        if (!$panel.data('notes-loaded')) {
            $.getJSON('/get_note/' + arxivId, function(res) {
                $panel.find('.notes-textarea').val(res.content || '');
            });
            $panel.data('notes-loaded', true);
        }
    });

    // Render / edit toggle for notes
    $(document).on('click', '.render-note-btn', function() {
        var $btn = $(this);
        var $panel = $btn.closest('.notes-panel');
        var $textarea = $panel.find('.notes-textarea');
        var $rendered = $panel.find('.notes-rendered');
        if ($btn.text() === 'render') {
            $rendered[0].textContent = $textarea.val();
            $textarea.hide();
            $rendered.show();
            $btn.text('edit');
            if (window.MathJax && MathJax.typesetPromise) {
                MathJax.typesetClear([$rendered[0]]);
                MathJax.typesetPromise([$rendered[0]]);
            }
        } else {
            $rendered.hide();
            $textarea.show();
            $btn.text('render');
        }
    });

    // Copy note
    $(document).on('click', '.copy-note-btn', function() {
        var $btn = $(this);
        var text = $btn.closest('.notes-panel').find('.notes-textarea').val();
        navigator.clipboard.writeText(text).then(function() {
            var orig = $btn.text();
            $btn.text('copied!');
            setTimeout(function() { $btn.text(orig); }, 1500);
        });
    });

    // Delete note
    $(document).on('click', '.delete-note-btn', function() {
        if (!confirm('Delete this note permanently?')) return;
        var $btn = $(this);
        var arxivId = $btn.attr('data-arxiv-id');
        $.ajax({
            type: 'POST',
            url: '/delete_note/' + arxivId,
            success: function() {
                var $panel = $btn.closest('.notes-panel');
                $panel.find('.notes-textarea').val('').show();
                $panel.find('.notes-rendered').hide();
                $panel.find('.render-note-btn').text('render');
                $panel.removeData('notes-loaded');
            },
            error: function() { alert('Could not delete note.'); }
        });
    });

    // Save note
    $(document).on('click', '.save-note-btn', function() {
        var $btn = $(this);
        var $panel = $btn.closest('.notes-panel');
        var $msg = $panel.find('.note-saved-msg');
        $.ajax({
            type: 'POST',
            url: '/save_note',
            contentType: 'application/json',
            data: JSON.stringify({
                arxiv_id: $btn.attr('data-arxiv-id'),
                content: $panel.find('.notes-textarea').val(),
                title: $btn.data('title'),
                authors: $btn.data('authors'),
                date: $btn.data('date'),
                abs_url: $btn.data('abs-url'),
                pdf_url: $btn.data('pdf-url'),
                bibtex: $btn.data('bibtex'),
                category: $btn.data('category'),
                summary: $btn.data('summary'),
            }),
            success: function(res) {
                $msg.stop(true).show().delay(2000).fadeOut(400);
                if (res.auto_starred) {
                    $btn.closest('.paper-wrapper').find('.fav-btn').addClass('fav-active').attr('title', 'Remove from favourites');
                }
            },
            error: function() { alert('Could not save note.'); }
        });
    });

    // Star button: toggle favourite (with notes protection)
    $(document).on('click', '.fav-btn', function() {
        var $btn = $(this);
        var isCurrentlyFav = $btn.hasClass('fav-active');
        var arxivId = $btn.attr('data-arxiv-id');

        function doToggle() {
            $.ajax({
                type: 'POST',
                url: '/toggle_favourite',
                contentType: 'application/json',
                data: JSON.stringify({
                    arxiv_id: arxivId,
                    title: $btn.data('title'),
                    authors: $btn.data('authors'),
                    date: $btn.data('date'),
                    abs_url: $btn.data('abs-url'),
                    pdf_url: $btn.data('pdf-url'),
                    bibtex: $btn.data('bibtex'),
                    category: $btn.data('category'),
                    summary: $btn.data('summary'),
                }),
                success: function(res) {
                    $btn.toggleClass('fav-active', res.is_fav);
                    $btn.attr('title', res.is_fav ? 'Remove from favourites' : 'Add to favourites');
                    if (!res.is_fav && $btn.closest('.fav-page').length) {
                        $btn.closest('.paper-wrapper').fadeOut(300, function() { $(this).remove(); });
                    }
                },
                error: function() { alert('Could not update favourites.'); }
            });
        }

        if (isCurrentlyFav) {
            $.getJSON('/has_note/' + arxivId, function(data) {
                if (data.has_note && !confirm('This paper has notes. Remove from favourites anyway?')) return;
                doToggle();
            }).fail(function() { doToggle(); });
        } else {
            doToggle();
        }
    });

    // Scan favourites folder for unimported PDFs
    $(document).on('click', '#scan-folder-btn', function() {
        var $btn = $(this);
        var $box = $('#scan-results');
        var $inner = $('#scan-results-inner');
        $btn.html('<span class="spinner-inline"></span>');
        $btn.prop('disabled', true);
        $.get('/scan_favourites', function(results) {
            $btn.text('scan folder').prop('disabled', false);
            $inner.empty();
            if (!results.length) {
                $inner.html('<span style="font-size:0.85rem;opacity:0.6;">No new PDFs found in the favourites folder.</span>');
                $box.show();
                return;
            }
            var sourceLabel = {
                'filename': 'filename', 'pdf_metadata': 'pdf metadata',
                'xmp': 'XMP metadata', 'page_text': 'page text',
                'unresolved': 'unresolved'
            };
            results.forEach(function(p) {
                var $row = $('<div>').css({'margin-bottom':'10px','padding-bottom':'10px','border-bottom':'1px solid var(--c-border)'});
                var src = '<span style="font-size:0.75rem;opacity:0.5;margin-left:6px;">detected via ' + (sourceLabel[p.detection_source] || p.detection_source) + '</span>';
                if (p.unresolved) {
                    $row.append('<div style="font-size:0.85rem;opacity:0.7;">' + p.filename + src + '</div>');
                    $row.append('<div style="font-size:0.8rem;opacity:0.5;">Could not resolve metadata.</div>');
                } else {
                    var titleHtml = p.abs_url
                        ? '<a href="' + p.abs_url + '" target="_blank" style="color:var(--c-secondary);font-size:0.95rem;">' + p.title + '</a>'
                        : '<span style="font-size:0.95rem;">' + p.title + '</span>';
                    $row.append('<div>' + titleHtml + src + '</div>');
                    $row.append('<div style="font-size:0.8rem;opacity:0.7;margin:2px 0;">' + p.authors + '</div>');
                    $row.append('<div style="font-size:0.8rem;opacity:0.5;margin-bottom:4px;">' + p.date + (p.category ? ' · ' + p.category : '') + ' · <em>' + p.filename + '</em></div>');
                    var $add = $('<button>').addClass('tools tools-box').text('add to favourites').css('font-size','0.8rem');
                    $add.on('click', function() {
                        $add.text('adding...').prop('disabled', true);
                        $.ajax({
                            type: 'POST', url: '/import_local_paper',
                            contentType: 'application/json',
                            data: JSON.stringify(p),
                            success: function() {
                                $row.html('<span style="font-size:0.85rem;opacity:0.6;">✓ added: ' + p.title + '</span>');
                            },
                            error: function() { $add.text('add to favourites').prop('disabled', false); }
                        });
                    });
                    $row.append($add);
                }
                $inner.append($row);
            });
            $box.show();
        }).fail(function() {
            $btn.text('scan folder').prop('disabled', false);
            alert('Scan failed.');
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