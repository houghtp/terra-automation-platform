(function () {
  function hideContentModal() {
    const modalElement = document.getElementById("content-form-modal");
    if (!modalElement) {
      return;
    }
    const instance =
      bootstrap.Modal.getInstance(modalElement) ||
      bootstrap.Modal.getOrCreateInstance(modalElement);
    instance.hide();
  }

  document.body.addEventListener("closeModal", hideContentModal);

  document.addEventListener("htmx:afterSwap", function (event) {
    if (event.target && event.target.id === "content-form-modal-body") {
      const modalElement = document.getElementById("content-form-modal");
      if (modalElement) {
        const instance =
          bootstrap.Modal.getInstance(modalElement) ||
          bootstrap.Modal.getOrCreateInstance(modalElement);
        instance.show();
      }
    }
  });

  // Ensure "View" links in snapshot cards activate tabs reliably
  document.addEventListener("click", function (event) {
    const link = event.target.closest(".view-tab");
    if (link) {
      event.preventDefault();
      const tabTrigger = new bootstrap.Tab(link);
      tabTrigger.show();
    }
  });
})();
