// simulate-typing.js

// Function to simulate typing characters with delays
export function simulateTyping(element, value) {
    element.value = "";

    const typeCharacter = (str, index) => {
        if (index < str.length) {
            element.value += str[index];
            const inputEvent = new Event("input", {
                bubbles: true,
                cancelable: true,
            });
            element.dispatchEvent(inputEvent);

            // Dispatch key events
            ["keydown", "keypress", "keyup"].forEach((eventType) => {
                const keyEvent = new KeyboardEvent(eventType, {
                    bubbles: true,
                    cancelable: true,
                    key: str[index],
                    char: str[index],
                    shiftKey: false,
                    ctrlKey: false,
                    metaKey: false,
                });
                element.dispatchEvent(keyEvent);
            });

            // Schedule the next character
            setTimeout(() => typeCharacter(str, index + 1), 50);
        } else {
            // After typing is complete, dispatch blur and change events
            element.dispatchEvent(
                new FocusEvent("focusout", { bubbles: true, cancelable: true })
            );
            element.blur();
            element.dispatchEvent(
                new FocusEvent("blur", { bubbles: true, cancelable: true })
            );
            const changeEvent = new Event("change", {
                bubbles: true,
                cancelable: true,
            });
            element.dispatchEvent(changeEvent);
        }
    };

    typeCharacter(value.toString(), 0);
}
