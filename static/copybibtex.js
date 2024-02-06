function copyTextToClipboard() {
    var textToCopy = document.getElementById("textToCopy");
    var textRange = document.createRange();
    textRange.selectNode(textToCopy);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(textRange);
    document.execCommand("copy");
    window.getSelection().removeAllRanges();
}