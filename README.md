# Auto Fill KDP Price Form

## Project goal

That project aims to create a way to auto-fill the Amazon KDP book prices form. Having doezns of books created through the [AIGEN project] (https://gitlab.com/CyrilGendarme/ai-content-generator), modifying each by hand sounded like a waste of time.

## Challenges

Filling the form wasn't enough. Amazon has set up sequences of function calls to required the management of timing and events.

## Technologies

That project is pure native JavaScript.
It involves mimic of events happening when an user interact with the web page.
There also a general mutation-observer.js script that can be used to monitor which html elements (id, attributes, etc) are modified following an event or user interaction with the page.
