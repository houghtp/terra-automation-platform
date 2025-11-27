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
})();
