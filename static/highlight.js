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
