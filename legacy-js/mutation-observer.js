// mutation-observer.js

const targetNode = document.body; // You can change this to any specific target node
const config = {
    attributes: true,
    childList: true,
    subtree: true,
    attributeOldValue: true,
};

// Callback function to execute when mutations are observed
const callback = function (mutationsList, observer) {
    for (const mutation of mutationsList) {
        if (mutation.type === "childList") {
            console.log("A child node has been added or removed.", mutation);
        } else if (mutation.type === "attributes") {
            // Exclude style attribute modifications
            if (mutation.attributeName !== "style") {
                const oldValue = mutation.oldValue;
                const newValue = mutation.target.getAttribute(
                    mutation.attributeName
                );
                console.log(mutation.target);
                console.log(
                    `The ${mutation.attributeName} attribute was modified. Old value: ${oldValue}, New value: ${newValue}`
                );
            }
        }
    }
};

// Create an observer instance linked to the callback function
const observer = new MutationObserver(callback);

// Start observing the target node for configured mutations
observer.observe(targetNode, config);
