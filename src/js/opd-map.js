(function () {
  'use strict';
  var widget = document.querySelector('[data-opd-map]');
  if (!widget) return;
  var frame = widget.querySelector('.gbp-opd-map-frame');
  var link = widget.querySelector('.gbp-opd-map-link');
  var cities = widget.querySelectorAll('[data-city]');
  function update(city) {
    var query = 'Bankers Vascular Hospital, ' + city + ', Gujarat';
    var encoded = encodeURIComponent(query);
    frame.src = 'https://maps.google.com/maps?output=embed&q=' + encoded;
    frame.title = city + ' OPD location map';
    link.href = 'https://www.google.com/maps/search/?api=1&query=' + encoded;
    link.textContent = 'Open ' + city + ' in Google Maps ↗';
    cities.forEach(function (button) {
      var active = button.getAttribute('data-city') === city;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
  }
  cities.forEach(function (button) { button.addEventListener('click', function () { update(button.getAttribute('data-city')); }); });
}());
