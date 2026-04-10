function highlight(keys) {
    if (!keys || !Array.isArray(keys) || keys.length === 0) return;
    var hasHighlights = document.querySelector('.highlight');
    if (hasHighlights) {
        var highlights = document.querySelectorAll('.highlight');
        highlights.forEach(function (element) {
            element.classList.remove('highlight');
        });
    } else {
        keys.forEach(function (term) {
            var regex = new RegExp(term, 'gi'); // global, case insensitive
            var elementsToSearch = document.querySelectorAll('.paper'); // find within the .paper elements
            elementsToSearch.forEach(function (element) {
                highlightMatchesInElement(element, regex);
            });
        });
    }
}

function highlightMatchesInElement(element, regex) {
    traverseNodes(element, function (node) {
        if (node.nodeType === 3) {
            var html = node.nodeValue;
            html = html.replace(regex, function (match) {
                return '<span class="highlight">' + match + '</span>';
        });
            var wrapper = document.createElement('span');
            wrapper.innerHTML = html;
            node.parentNode.replaceChild(wrapper, node);
        }
    });
}

function traverseNodes(node, callback) {
    if (node.nodeType === 1) { 
        for (var i = 0; i < node.childNodes.length; i++) {
            traverseNodes(node.childNodes[i], callback);
        }
    } else {
            callback(node);
    }
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

function filterPapers(query) {
    var wrappers = document.querySelectorAll('.paper-wrapper');
    var term = query.toLowerCase().trim();
    wrappers.forEach(function (wrapper) {
        if (!term || wrapper.textContent.toLowerCase().indexOf(term) !== -1) {
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
