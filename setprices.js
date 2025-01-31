// ebook.js

import { simulateTyping } from "./common.js";

// Function to update input values based on language slug
function updateInputValues(prices, html_input_filed_pos, main_form_id) {
    const form = document.getElementById(main_form_id);
    const validation_button = document.getElementById(
        "save-and-publish-announce"
    );
    var cntPriceTyped = 0;
    let cnt = 0;

    if (form) {
        for (const [lang, price] of Object.entries(prices)) {
            // Find input elements with the specified language slug within the form
            const elements = form.querySelectorAll(`input[name*='[${lang}]']`);

            console.log(elements);

            cnt = 0;
            elements.forEach((element) => {
                if (cnt == html_input_filed_pos) {
                    console.log(
                        `Changing value of element with name containing '[${lang}]' to '${price}'`
                    );

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

                    // Clear the current value
                    element.value = "";

                    // Start typing the price string
                    setTimeout(
                        () => simulateTyping(element, price.toString()),
                        60 * cntPriceTyped
                    );
                    cntPriceTyped++;
                }

                cnt++;
            });
        }
        setTimeout(() => validation_button.click(), 60 * cntPriceTyped + 300);
    } else {
        console.error('Form with ID "' + main_form_id + '" not found.');
    }
}
