(function () {
    "use strict";


    function norm(value) {
        return (
            value || ""
        )
        .toLowerCase()
        .normalize("NFD")
        .replace(
            /[\u0300-\u036f]/g,
            ""
        );
    }


    function emojiSpan(
        emoji,
        className
    ) {
        const span =
            document.createElement(
                "span"
            );

        span.className =
            className || "";

        span.textContent =
            emoji;

        span.setAttribute(
            "aria-hidden",
            "true"
        );

        return span;
    }


    // ========================================================
    // HOME FORMAT CARDS
    // ========================================================

    const formats = [
        {
            find:
                "historia de frutas",

            emojis: [
                "\uD83C\uDF53",
                "\uD83C\uDF4C",
                "\uD83C\uDF4A",
            ],

            theme:
                "fruit",
        },

        {
            find:
                "drama corto",

            emojis: [
                "\uD83C\uDFAD",
                "\uD83C\uDFAC",
            ],

            theme:
                "drama",
        },

        {
            find:
                "historia infantil",

            emojis: [
                "\uD83E\uDDF8",
                "\uD83C\uDF88",
            ],

            theme:
                "kids",
        },

        {
            find:
                "crear desde cero",

            emojis: [
                "\u2728",
                "\uD83C\uDFA8",
            ],

            theme:
                "blank",
        },
    ];


    function enhanceTemplateCards() {

        const cards =
            document.querySelectorAll(
                ".template-card, "
                + ".idea-card, "
                + ".format-card"
            );

        cards.forEach(
            function (card) {

                const titleNode =
                    card.querySelector(
                        "h2, h3, "
                        + ".template-title"
                    );

                if (!titleNode) {
                    return;
                }

                const title =
                    norm(
                        titleNode.textContent
                    );

                const config =
                    formats.find(
                        function (item) {
                            return (
                                title.includes(
                                    item.find
                                )
                            );
                        }
                    );

                if (!config) {
                    return;
                }

                if (
                    card.querySelector(
                        ".gingao-premium-format-art"
                    )
                ) {
                    return;
                }

                card.classList.add(
                    "gingao-premium-card",
                    "gingao-theme-"
                    + config.theme
                );


                const visual =
                    card.querySelector(
                        ".template-visual, "
                        + ".template-art, "
                        + ".template-preview, "
                        + ".format-preview, "
                        + ".card-visual"
                    );


                const art =
                    document.createElement(
                        "div"
                    );

                art.className =
                    "gingao-premium-format-art";


                const halo =
                    document.createElement(
                        "span"
                    );

                halo.className =
                    "gingao-art-halo";

                art.appendChild(
                    halo
                );


                const emojiWrap =
                    document.createElement(
                        "div"
                    );

                emojiWrap.className =
                    "gingao-food-emoji-group";


                config.emojis.forEach(
                    function (
                        emoji,
                        index
                    ) {

                        const item =
                            emojiSpan(
                                emoji,
                                (
                                    "gingao-food-emoji "
                                    + "gingao-food-emoji-"
                                    + index
                                )
                            );

                        emojiWrap.appendChild(
                            item
                        );
                    }
                );


                art.appendChild(
                    emojiWrap
                );


                const shine =
                    document.createElement(
                        "span"
                    );

                shine.className =
                    "gingao-art-shine";

                art.appendChild(
                    shine
                );


                if (visual) {

                    visual.innerHTML = "";

                    visual.classList.add(
                        "gingao-art-host"
                    );

                    visual.appendChild(
                        art
                    );

                } else {

                    card.insertBefore(
                        art,
                        card.firstChild
                    );

                }

            }
        );
    }


    // ========================================================
    // PROJECT RECENT CARDS
    // ========================================================

    function projectEmojis(
        title
    ) {

        title = norm(
            title
        );

        const values = [];

        if (
            title.includes(
                "fresa"
            )
        ) {
            values.push(
                "\uD83C\uDF53"
            );
        }

        if (
            title.includes(
                "platano"
            )
            || title.includes(
                "banana"
            )
        ) {
            values.push(
                "\uD83C\uDF4C"
            );
        }

        if (
            title.includes(
                "naranja"
            )
        ) {
            values.push(
                "\uD83C\uDF4A"
            );
        }

        if (
            title.includes(
                "manzana"
            )
        ) {
            values.push(
                "\uD83C\uDF4E"
            );
        }

        if (
            title.includes(
                "uva"
            )
        ) {
            values.push(
                "\uD83C\uDF47"
            );
        }

        if (!values.length) {

            values.push(
                "\uD83C\uDFAC",
                "\u2728"
            );
        }

        return values.slice(
            0,
            3
        );
    }


    function enhanceProjectCards() {

        const cards =
            document.querySelectorAll(
                ".project-card"
            );

        cards.forEach(
            function (card, index) {

                // V3 cards already have their own
                // server-rendered premium markup.
                // Do not overwrite them.
                if (
                    card.classList.contains(
                        "project-card-v3"
                    )
                ) {
                    return;
                }

                card.classList.add(
                    "gingao-project-card-premium"
                );


                const titleNode =
                    card.querySelector(
                        "h2, h3, "
                        + ".project-title"
                    );

                const title =
                    titleNode
                    ? titleNode.textContent
                    : "";


                let media =
                    card.querySelector(
                        ".project-thumb, "
                        + ".project-cover, "
                        + ".project-thumbnail, "
                        + ".project-card-media, "
                        + ".project-preview"
                    );


                // If no explicit media container exists,
                // find the first visual area containing "?".
                if (!media) {

                    const candidates =
                        card.querySelectorAll(
                            "div"
                        );

                    for (
                        const candidate
                        of candidates
                    ) {

                        if (
                            candidate.children.length
                            <= 1
                            && candidate.textContent
                            .trim()
                            === "?"
                        ) {

                            media =
                                candidate;

                            break;
                        }
                    }

                }


                if (!media) {
                    return;
                }


                // Keep an actual project image.
                const realImage =
                    media.querySelector(
                        "img"
                    );

                if (
                    realImage
                    && realImage.getAttribute(
                        "src"
                    )
                    && !realImage
                        .getAttribute("src")
                        .includes(
                            "placeholder"
                        )
                ) {

                    media.classList.add(
                        "gingao-project-media-real"
                    );

                    return;
                }


                media.innerHTML = "";

                media.classList.add(
                    "gingao-project-cover-fallback",
                    "gingao-cover-theme-"
                    + (
                        index % 4
                    )
                );


                const inner =
                    document.createElement(
                        "div"
                    );

                inner.className =
                    "gingao-project-cover-inner";


                projectEmojis(
                    title
                ).forEach(
                    function (
                        emoji,
                        emojiIndex
                    ) {

                        inner.appendChild(
                            emojiSpan(
                                emoji,
                                (
                                    "gingao-project-emoji "
                                    + "gingao-project-emoji-"
                                    + emojiIndex
                                )
                            )
                        );

                    }
                );


                const badge =
                    document.createElement(
                        "span"
                    );

                badge.className =
                    "gingao-project-cover-badge";

                badge.textContent =
                    "GINGAO";


                media.appendChild(
                    inner
                );

                media.appendChild(
                    badge
                );

            }
        );
    }


    // ========================================================
    // PREMIUM BUTTON FEEDBACK
    // ========================================================

    function enhanceButtons() {

        document.querySelectorAll(
            ".primary-button, "
            + ".secondary-button, "
            + "button"
        ).forEach(
            function (button) {

                if (
                    button.dataset
                    .gingaoPremium
                ) {
                    return;
                }

                button.dataset
                    .gingaoPremium =
                    "1";

                button.addEventListener(
                    "pointerdown",
                    function () {

                        button.classList.add(
                            "gingao-pressed"
                        );

                    }
                );

                [
                    "pointerup",
                    "pointercancel",
                    "pointerleave",
                ].forEach(
                    function (eventName) {

                        button.addEventListener(
                            eventName,
                            function () {

                                button.classList.remove(
                                    "gingao-pressed"
                                );

                            }
                        );

                    }
                );

            }
        );
    }




    // GINGAO_PROJECT_FALLBACK_V3
    
function populateProjectFallbacks() {

        const covers =
            document.querySelectorAll(
                ".project-cover-fallback-v3"
            );

        covers.forEach(
            function (cover) {

                const host =
                    cover.querySelector(
                        ".project-fallback-emojis"
                    );

                if (!host) {
                    return;
                }

                host.innerHTML = "";

                const title =
                    norm(
                        cover.getAttribute(
                            "data-project-title"
                        ) || ""
                    );

                let emojis = [];

                if (
                    title.includes("fresa")
                ) {
                    emojis.push(
                        "\uD83C\uDF53"
                    );
                }

                if (
                    title.includes("platano")
                    || title.includes("banana")
                ) {
                    emojis.push(
                        "\uD83C\uDF4C"
                    );
                }

                if (
                    title.includes("naranja")
                ) {
                    emojis.push(
                        "\uD83C\uDF4A"
                    );
                }

                if (
                    title.includes("manzana")
                ) {
                    emojis.push(
                        "\uD83C\uDF4E"
                    );
                }

                if (
                    title.includes("uva")
                ) {
                    emojis.push(
                        "\uD83C\uDF47"
                    );
                }

                if (!emojis.length) {

                    emojis = [
                        "\uD83C\uDFAC",
                        "\u2728",
                    ];

                }

                emojis
                .slice(0, 3)
                .forEach(
                    function (emoji) {

                        const item =
                            document.createElement(
                                "span"
                            );

                        item.className =
                            "project-fallback-emoji";

                        item.textContent =
                            emoji;

                        host.appendChild(
                            item
                        );

                    }
                );

            }
        );
    }




    
    // GINGAO_CATALOG_FILTERS_V2
    function initCatalogFilters() {

        const filters =
            Array.from(
                document.querySelectorAll(
                    ".catalog-filter"
                )
            );

        const cards =
            Array.from(
                document.querySelectorAll(
                    ".catalog-card"
                )
            );

        const search =
            document.getElementById(
                "catalog-search"
            );

        const counter =
            document.getElementById(
                "catalog-results-count"
            );

        if (!cards.length) {
            return;
        }


        let activeFilter = "all";


        function normalizeText(value) {

            return (
                value || ""
            )
            .toLowerCase()
            .normalize("NFD")
            .replace(
                /[\u0300-\u036f]/g,
                ""
            );

        }


        function refreshCatalog() {

            const query =
                normalizeText(
                    search
                    ? search.value
                    : ""
                )
                .trim();


            let visibleCount = 0;


            cards.forEach(
                function (card) {

                    const categories =
                        (
                            card.dataset.category
                            || ""
                        )
                        .split(" ");


                    const content =
                        normalizeText(
                            card.textContent
                            + " "
                            + (
                                card.dataset.category
                                || ""
                            )
                        );


                    const categoryMatch =
                        activeFilter === "all"
                        || categories.includes(
                            activeFilter
                        );


                    const searchMatch =
                        !query
                        || content.includes(
                            query
                        );


                    const visible =
                        categoryMatch
                        && searchMatch;


                    if (visible) {

                        card.hidden = false;
                        card.classList.remove(
                            "catalog-card-hidden"
                        );

                        visibleCount += 1;

                    } else {

                        // IMPORTANT:
                        // hidden immediately so CSS Grid
                        // repacks with no empty holes.
                        card.hidden = true;
                        card.classList.add(
                            "catalog-card-hidden"
                        );

                    }

                }
            );


            if (counter) {

                counter.textContent =
                    visibleCount === 1
                    ? "1 formato"
                    : visibleCount
                        + " formatos";

            }

        }


        filters.forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        activeFilter =
                            button.dataset.filter
                            || "all";


                        filters.forEach(
                            function (item) {

                                item.classList.remove(
                                    "active"
                                );

                                item.setAttribute(
                                    "aria-selected",
                                    "false"
                                );

                            }
                        );


                        button.classList.add(
                            "active"
                        );

                        button.setAttribute(
                            "aria-selected",
                            "true"
                        );


                        refreshCatalog();

                    }
                );

            }
        );


        if (search) {

            search.addEventListener(
                "input",
                refreshCatalog
            );

        }


        refreshCatalog();

    }


// ========================================================
    // INITIALIZE
    // ========================================================

    function init() {

        // enhanceTemplateCards(); // disabled: professional covers now
        enhanceProjectCards();
        populateProjectFallbacks();
        enhanceButtons();
        initCatalogFilters();
        initAssetVideoPreview();

    }


    if (
        document.readyState
        === "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            init
        );

    } else {

        init();

    }

})();


/* ==========================================================
   GINGAO_MEDIA_LIBRARY_V2_STANDALONE
   ========================================================== */

(function () {

    function normalizeValue(value) {

        return (
            value || ""
        )
        .toLowerCase()
        .normalize("NFD")
        .replace(
            /[\u0300-\u036f]/g,
            ""
        );

    }


    function initMediaLibraryV2() {

        const cards =
            Array.from(
                document.querySelectorAll(
                    ".asset-card-v2"
                )
            );

        if (!cards.length) {
            return;
        }


        const buttons =
            Array.from(
                document.querySelectorAll(
                    ".asset-filter-button"
                )
            );

        const search =
            document.getElementById(
                "asset-search-input"
            );

        const counter =
            document.getElementById(
                "asset-results-count"
            );

        const empty =
            document.getElementById(
                "asset-no-results"
            );


        let active = "all";


        function refresh() {

            const query =
                normalizeValue(
                    search
                    ? search.value
                    : ""
                ).trim();


            let visible = 0;


            cards.forEach(
                function (card) {

                    const kind =
                        card.dataset.kind
                        || "";

                    const origin =
                        card.dataset.origin
                        || "";

                    const searchable =
                        normalizeValue(
                            card.dataset.search
                            || card.textContent
                        );


                    let filterMatch =
                        active === "all";


                    if (
                        active === "image"
                        || active === "video"
                        || active === "audio"
                    ) {

                        filterMatch =
                            kind === active;

                    }


                    if (active === "demo") {

                        filterMatch =
                            origin === "demo";

                    }


                    if (active === "real") {

                        filterMatch =
                            origin !== "demo";

                    }


                    const searchMatch =
                        !query
                        || searchable.includes(
                            query
                        );


                    const show =
                        filterMatch
                        && searchMatch;


                    card.hidden =
                        !show;


                    if (show) {
                        visible += 1;
                    }

                }
            );


            if (counter) {

                counter.textContent =
                    visible === 1
                    ? "1 activo"
                    : visible
                        + " activos";

            }


            if (empty) {

                empty.hidden =
                    visible !== 0;

            }

        }


        buttons.forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        active =
                            button.dataset
                            .assetFilter
                            || "all";


                        buttons.forEach(
                            function (item) {

                                item.classList.remove(
                                    "active"
                                );

                            }
                        );


                        button.classList.add(
                            "active"
                        );


                        refresh();

                    }
                );

            }
        );


        if (search) {

            search.addEventListener(
                "input",
                refresh
            );

        }


        document.querySelectorAll(
            ".asset-card-v2 video"
        ).forEach(
            function (video) {

                const card =
                    video.closest(
                        ".asset-card-v2"
                    );


                if (!card) {
                    return;
                }


                card.addEventListener(
                    "mouseenter",
                    function () {

                        video.play()
                        .catch(
                            function () {}
                        );

                    }
                );


                card.addEventListener(
                    "mouseleave",
                    function () {

                        video.pause();

                        try {
                            video.currentTime = 0;
                        }
                        catch (error) {}

                    }
                );

            }
        );


        refresh();

    }


    function initProjectCoverFraming() {

        document.querySelectorAll(
            ".project-preview-v3 .project-cover-image"
        ).forEach(
            function (image) {

                const host =
                    image.closest(
                        ".project-preview-v3"
                    );


                if (!host) {
                    return;
                }


                function applyBackdrop() {

                    const src =
                        image.currentSrc
                        || image.src;


                    if (!src) {
                        return;
                    }


                    host.classList.add(
                        "has-real-cover"
                    );


                    host.style.backgroundImage =
                        'url("' + src + '")';

                }


                if (image.complete) {

                    applyBackdrop();

                } else {

                    image.addEventListener(
                        "load",
                        applyBackdrop,
                        {
                            once: true
                        }
                    );

                }

            }
        );

    }


    function startGingaoMediaV2() {

        initMediaLibraryV2();
        initProjectCoverFraming();

    }


    if (
        document.readyState === "loading"
    ) {

        document.addEventListener(
            "DOMContentLoaded",
            startGingaoMediaV2
        );

    } else {

        startGingaoMediaV2();

    }

})();

