(function () {
    const filterForm = document.getElementById("prompt-filter-form");
    const applyBtn = document.getElementById("prompt-filter-apply");
    const resetBtn = document.getElementById("prompt-filter-reset");
    const categorySelect = document.getElementById("prompt-filter-category");
    const includeSystemCheckbox = document.getElementById("prompt-include-system");
    const includeInactiveCheckbox = document.getElementById("prompt-include-inactive");
    const tenantScopeSelect = document.getElementById("prompt-tenant-scope");

    function triggerTableRefresh() {
        document.body.dispatchEvent(
            new CustomEvent("promptFiltersChanged", { bubbles: true })
        );
    }

    function showToastMessage(message, type) {
        if (typeof window.showToast === "function") {
            window.showToast(message, type);
        }
    }

    function closeOpenModals() {
        document
            .querySelectorAll(".modal.show")
            .forEach((modalEl) => {
                const instance = bootstrap.Modal.getInstance(modalEl);
                if (instance) {
                    instance.hide();
                }
            });
    }

    function initializeFormListeners() {
        if (applyBtn) {
            applyBtn.addEventListener("click", function (event) {
                event.preventDefault();
                triggerTableRefresh();
            });
        }

        if (resetBtn && filterForm) {
            resetBtn.addEventListener("click", function (event) {
                event.preventDefault();
                filterForm.reset();
                triggerTableRefresh();
            });
        }

        const autoRefreshInputs = [
            categorySelect,
            includeSystemCheckbox,
            includeInactiveCheckbox,
            tenantScopeSelect,
        ].filter(Boolean);

        autoRefreshInputs.forEach((input) => {
            input.addEventListener("change", () => triggerTableRefresh());
        });
    }

    const toastEvents = {
        promptSaved: { message: "Prompt saved successfully", type: "success" },
        promptDeactivated: { message: "Prompt disabled", type: "warning" },
        promptRestored: { message: "Prompt restored", type: "success" },
    };

    Object.entries(toastEvents).forEach(([eventName, config]) => {
        document.body.addEventListener(eventName, () => {
            showToastMessage(config.message, config.type);
            triggerTableRefresh();
        });
    });

    document.body.addEventListener("refreshPromptTable", triggerTableRefresh);
    document.body.addEventListener("closeModal", closeOpenModals);

    document.addEventListener("htmx:afterSwap", (event) => {
        if (event.target.id === "prompt-form-modal-content") {
            const modalElement = document.getElementById("prompt-form-modal");
            if (modalElement) {
                const instance = bootstrap.Modal.getOrCreateInstance(modalElement);
                instance.show();
            }
        }

        if (event.target.id === "prompt-details-modal-content") {
            const modalElement = document.getElementById("prompt-details-modal");
            if (modalElement) {
                const instance = bootstrap.Modal.getOrCreateInstance(modalElement);
                instance.show();
            }
        }
    });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeFormListeners);
    } else {
        initializeFormListeners();
    }
})();
