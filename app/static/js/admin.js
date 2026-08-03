document.querySelector('[data-sidebar-toggle]')?.addEventListener('click', () => {
  document.querySelector('[data-sidebar]')?.classList.toggle('open');
});

document.querySelector('[data-flash-close]')?.addEventListener('click', (event) => {
  event.currentTarget.closest('.admin-flash')?.remove();
});

const imageInput = document.querySelector('[data-image-input]');
const imagePreview = document.querySelector('[data-image-preview]');
imageInput?.addEventListener('change', () => {
  const file = imageInput.files?.[0];
  if (!file || !imagePreview) return;
  const reader = new FileReader();
  reader.onload = () => { imagePreview.innerHTML = `<img src="${reader.result}" alt="Selected product image preview">`; };
  reader.readAsDataURL(file);
});
