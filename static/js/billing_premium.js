(() => {
    "use strict";

    const reduceMotion =
        window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;


    const clamp = (
        value,
        min,
        max
    ) => Math.min(
        Math.max(
            value,
            min
        ),
        max
    );


    const addSpotlight = (
        element
    ) => {

        if (!element) {
            return;
        }

        const update = (
            event
        ) => {

            const rect =
                element.getBoundingClientRect();

            const x =
                clamp(
                    (
                        (
                            event.clientX
                            - rect.left
                        )
                        / rect.width
                    )
                    * 100,
                    0,
                    100
                );

            const y =
                clamp(
                    (
                        (
                            event.clientY
                            - rect.top
                        )
                        / rect.height
                    )
                    * 100,
                    0,
                    100
                );


            element.style.setProperty(
                "--mx",
                `${x}%`
            );

            element.style.setProperty(
                "--my",
                `${y}%`
            );
        };


        element.addEventListener(
            "pointermove",
            update,
            {
                passive: true
            }
        );


        element.addEventListener(
            "pointerleave",
            () => {

                element.style.setProperty(
                    "--mx",
                    "50%"
                );

                element.style.setProperty(
                    "--my",
                    "45%"
                );
            }
        );
    };


    const planCards = [
        ...document.querySelectorAll(
            ".pricing-card"
        )
    ];


    planCards.forEach(
        (
            card,
            index
        ) => {

            const heading =
                card.querySelector(
                    "h3"
                );

            if (heading) {

                const planName =
                    heading.textContent
                    .trim()
                    .toLowerCase();

                card.dataset.plan =
                    planName;
            }


            card.dataset.cardIndex =
                String(index + 1);


            if (!reduceMotion) {

                addSpotlight(
                    card
                );
            }
        }
    );


    const checkout =
        document.querySelector(
            ".payment-checkout-card"
        );


    if (
        checkout
        && !reduceMotion
    ) {

        addSpotlight(
            checkout
        );
    }


    document
        .querySelectorAll(
            ".pricing-card button, "
            + ".mock-payment-actions button"
        )
        .forEach(
            button => {

                button.addEventListener(
                    "pointerdown",
                    () => {

                        if (
                            reduceMotion
                        ) {
                            return;
                        }

                        button.style.transform =
                            "translateY(0) scale(.985)";
                    }
                );


                button.addEventListener(
                    "pointerup",
                    () => {

                        button.style.transform =
                            "";
                    }
                );


                button.addEventListener(
                    "pointercancel",
                    () => {

                        button.style.transform =
                            "";
                    }
                );


                button.addEventListener(
                    "pointerleave",
                    () => {

                        button.style.transform =
                            "";
                    }
                );
            }
        );


    document.documentElement
        .dataset
        .billingPremiumReady =
        "true";

})();
