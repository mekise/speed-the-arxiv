var _highlightState = {};

function highlight(keys, type) {
    if (!keys || !Array.isArray(keys) || keys.length === 0) return;

    // Toggle this type
    if (_highlightState[type]) {
        delete _highlightState[type];
    } else {
        _highlightState[type] = keys;
    }

    // Clear all highlights (properly unwrap spans)
    document.querySelectorAll('.highlight').forEach(function(span) {
        var parent = span.parentNode;
        while (span.firstChild) {
            parent.insertBefore(span.firstChild, span);
        }
        parent.removeChild(span);
        parent.normalize();
    });

    // Re-apply all active highlights
    var allKeys = [];
    for (var t in _highlightState) {
        allKeys = allKeys.concat(_highlightState[t]);
    }
    if (allKeys.length > 0) {
        allKeys.forEach(function(term) {
            var escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            var regex = new RegExp(escaped, 'gi');
            document.querySelectorAll('.paper').forEach(function(el) {
                _highlightTextNodes(el, regex);
            });
        });
    }

    // Update button active states
    document.querySelectorAll('[data-highlight-type]').forEach(function(btn) {
        btn.classList.toggle('highlight-active', !!_highlightState[btn.getAttribute('data-highlight-type')]);
    });
}

function _highlightTextNodes(element, regex) {
    var walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(function(node) {
        var text = node.nodeValue;
        if (!regex.test(text)) return;
        regex.lastIndex = 0;
        var frag = document.createDocumentFragment();
        var lastIndex = 0;
        var match;
        while ((match = regex.exec(text)) !== null) {
            if (match.index > lastIndex) {
                frag.appendChild(document.createTextNode(text.slice(lastIndex, match.index)));
            }
            var span = document.createElement('span');
            span.className = 'highlight';
            span.textContent = match[0];
            frag.appendChild(span);
            lastIndex = regex.lastIndex;
        }
        if (lastIndex < text.length) {
            frag.appendChild(document.createTextNode(text.slice(lastIndex)));
        }
        node.parentNode.replaceChild(frag, node);
    });
}

function toggleAllAbstracts() {
    var abstracts = document.querySelectorAll('.paper-wrapper:not([data-hidden]) .paper .collapse');
    var allExpanded = Array.from(abstracts).every(function (el) {
        return el.classList.contains('show');
    });
    abstracts.forEach(function (el) {
        var bsCollapse = bootstrap.Collapse.getOrCreateInstance(el, {toggle: false});
        if (allExpanded) {
            bsCollapse.hide();
        } else {
            bsCollapse.show();
        }
    });
}

var PAPERS_PER_PAGE = 25;
var currentPage = 1;

(function() {
    document.addEventListener('input', function(e) {
        if (e.target && e.target.id === 'filter-input') {
            filterPapers(e.target.value);
        }
    });
})();

function getFilterText(wrapper) {
    var clone = wrapper.cloneNode(true);
    var excluded = clone.querySelectorAll('.filter-exclude');
    excluded.forEach(function(el) { el.remove(); });
    return clone.textContent.toLowerCase();
}

function filterPapers(query) {
    var wrappers = document.querySelectorAll('.paper-wrapper');
    var term = query.toLowerCase().trim();
    wrappers.forEach(function (wrapper) {
        if (!term || getFilterText(wrapper).indexOf(term) !== -1) {
            wrapper.removeAttribute('data-filtered');
        } else {
            wrapper.setAttribute('data-filtered', '1');
        }
    });
    currentPage = 1;
    applyPagination();
}

function getVisibleWrappers() {
    return Array.from(document.querySelectorAll('.paper-wrapper:not([data-filtered])'));
}

function applyPagination() {
    var visible = getVisibleWrappers();
    var totalPages = Math.max(1, Math.ceil(visible.length / PAPERS_PER_PAGE));
    if (currentPage > totalPages) currentPage = totalPages;
    var start = (currentPage - 1) * PAPERS_PER_PAGE;
    var end = start + PAPERS_PER_PAGE;

    // hide all first
    document.querySelectorAll('.paper-wrapper').forEach(function (w) {
        w.style.display = 'none';
        w.setAttribute('data-hidden', '1');
    });
    // show current page slice of non-filtered papers
    visible.forEach(function (w, i) {
        if (i >= start && i < end) {
            w.style.display = '';
            w.removeAttribute('data-hidden');
        }
    });

    renderPaginationControls(totalPages, visible.length);

    // typeset only visible papers
    if (window.MathJax && MathJax.typesetPromise) {
        var visibleEls = document.querySelectorAll('.paper-wrapper:not([data-hidden])');
        if (visibleEls.length) {
            MathJax.typesetPromise(Array.from(visibleEls));
        }
    }
}

function renderPaginationControls(totalPages, totalVisible) {
    var container = document.getElementById('pagination-controls');
    if (!container) return;
    var allWrappers = document.querySelectorAll('.paper-wrapper');
    var filterInput = document.getElementById('filter-input');
    var isFiltered = filterInput && filterInput.value.trim().length > 0;

    // update filter count
    var countEl = document.getElementById('filter-count');
    if (countEl) {
        countEl.textContent = isFiltered ? totalVisible + ' / ' + allWrappers.length : '';
    }

    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    var html = '<button class="page-btn" data-page="prev">&laquo; prev</button> ';
    for (var i = 1; i <= totalPages; i++) {
        html += '<button class="page-btn' + (i === currentPage ? ' page-active' : '') + '" data-page="' + i + '">' + i + '</button> ';
    }
    html += '<button class="page-btn" data-page="next">next &raquo;</button>';
    html += '<span style="font-size: 0.8rem; opacity: 0.6; margin-left: 8px;">page ' + currentPage + ' / ' + totalPages + '</span>';
    container.innerHTML = html;
}

(function() {
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('page-btn')) {
            var page = e.target.getAttribute('data-page');
            var visible = getVisibleWrappers();
            var totalPages = Math.max(1, Math.ceil(visible.length / PAPERS_PER_PAGE));
            if (page === 'prev') {
                if (currentPage > 1) currentPage--;
            } else if (page === 'next') {
                if (currentPage < totalPages) currentPage++;
            } else {
                currentPage = parseInt(page, 10);
            }
            applyPagination();
            window.scrollTo(0, 0);
        }
    });
})();

(function() {
    function sortPapers(sortKey, order) {
        var container = document.querySelector('.topmargin-papers');
        if (!container) return;
        var wrappers = Array.from(container.querySelectorAll('.paper-wrapper'));
        wrappers.sort(function(a, b) {
            var va, vb;
            if (sortKey === 'title') {
                va = (a.querySelector('.title') || {}).textContent || '';
                vb = (b.querySelector('.title') || {}).textContent || '';
                va = va.toLowerCase(); vb = vb.toLowerCase();
            } else {
                va = a.getAttribute('data-' + sortKey) || '';
                vb = b.getAttribute('data-' + sortKey) || '';
            }
            if (sortKey === 'scirate') {
                va = parseFloat(va) || 0;
                vb = parseFloat(vb) || 0;
            }
            var cmp = va < vb ? -1 : (va > vb ? 1 : 0);
            if (cmp === 0) {
                var ia = parseInt(a.getAttribute('data-index'), 10) || 0;
                var ib = parseInt(b.getAttribute('data-index'), 10) || 0;
                return ia - ib;
            }
            return order === 'asc' ? cmp : -cmp;
        });
        var pagination = container.querySelector('#pagination-controls');
        wrappers.forEach(function(w) { container.appendChild(w); });
        if (pagination) container.appendChild(pagination);
        currentPage = 1;
        applyPagination();
    }

    document.addEventListener('click', function(e) {
        var el = e.target.closest('.sort-option');
        if (!el) return;
        e.preventDefault();
        sortPapers(el.getAttribute('data-sort'), el.getAttribute('data-order'));
        window.scrollTo(0, 0);
    });

    // Default sort: date added (newest) on favourites page
    document.addEventListener('DOMContentLoaded', function() {
        if (document.querySelector('.fav-page')) {
            sortPapers('added-at', 'desc');
        }
    });
})();
