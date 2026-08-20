(function () {
  'use strict';
  var widget = document.querySelector('[data-opd-map]');
  if (!widget) return;
  var selected = widget.querySelector('.gbp-opd-map-selected');
  var cities = widget.querySelectorAll('[data-city]');
  function update(city) {
    if (selected) selected.textContent = 'Showing ' + city + ' OPD centre';
    cities.forEach(function (button) {
      var active = button.getAttribute('data-city') === city;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
  }
  cities.forEach(function (button) { button.addEventListener('click', function () { update(button.getAttribute('data-city')); }); });
}());
