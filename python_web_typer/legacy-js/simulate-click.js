// simulate-click.js


function simulateClick(element) {
    // Simulate user interaction
    element.dispatchEvent(
        new MouseEvent("mousedown", {
            bubbles: true,
            cancelable: true,
        })
    );
    element.dispatchEvent(
        new MouseEvent("mouseup", {
            bubbles: true,
            cancelable: true,
        })
    );
    element.dispatchEvent(
        new FocusEvent("focusin", {
            bubbles: true,
            cancelable: true,
        })
    );
    element.focus();
    element.click();
    element.dispatchEvent(
        new FocusEvent("focus", {
            bubbles: true,
            cancelable: true,
        })
    );
}