(function () {
  'use strict';

  var section = document.querySelector('[data-opd-sheet-url]');
  var table = section && section.querySelector('.services-opd-table');
  if (!section || !table) return;
  var tableBody = table.querySelector('tbody');

  var heading = section.querySelector('#services-opd-heading');
  var updateBadge = section.querySelector('.services-opd-update');
  var endpoint = section.getAttribute('data-opd-sheet-url');
  var doctorImages = {
    'dr. tensi': 'images/doctor-card-tensi-trivedi.png',
    'dr. dimple': 'images/doctor-card-dimple-parmar.png',
    'dr. pratiksha': 'images/doctor-card-pratiksha-patoliya.png',
    'dr. payal': 'images/doctor-card-payal-vadlani.png',
    'dr. disha': 'images/doctor-card-disha-soni.png'
  };

  function parseDisplayDate(value) {
    var match = String(value || '').match(/^(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})$/);
    if (!match) return null;
    var months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
    var month = months.indexOf(match[2].slice(0, 3).toLowerCase());
    if (month < 0) return null;
    var date = new Date(Number(match[3]), month, Number(match[1]));
    return isNaN(date.getTime()) ? null : date;
  }

  var fallbackRecords = tableBody ? Array.prototype.map.call(tableBody.querySelectorAll('tr'), function (row) {
    var cells = row.querySelectorAll('td');
    var date = cells[0] && parseDisplayDate(cells[0].textContent.trim());
    if (!date || !cells[1] || !cells[2] || !cells[3]) return null;
    return { city: cells[1].textContent.trim(), 'hospital name': cells[3].textContent.trim(), 'camp date': String(date.getDate()).padStart(2, '0') + '/' + String(date.getMonth() + 1).padStart(2, '0') + '/' + date.getFullYear(), 'doctor name': cells[2].textContent.trim() };
  }).filter(Boolean) : [];

  function normalizeName(value) { return String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(); }
  function enrichFallbackRecords(sheetRecords) {
    return fallbackRecords.map(function (fallback) {
      var cityKey = normalizeName(fallback.city);
      var hospitalKey = normalizeName(fallback['hospital name']);
      var matches = sheetRecords.filter(function (item) {
        var sheetCity = normalizeName(item.city);
        var sheetHospital = normalizeName(item['hospital name']);
        var cityMatch = sheetCity === cityKey || (cityKey && sheetCity.indexOf(cityKey) >= 0) || (sheetCity && cityKey.indexOf(sheetCity) >= 0);
        var hospitalMatch = hospitalKey && sheetHospital && (sheetHospital.indexOf(hospitalKey) >= 0 || hospitalKey.indexOf(sheetHospital) >= 0);
        return cityMatch && (hospitalMatch || sheetRecords.filter(function (candidate) { return normalizeName(candidate.city) === cityKey; }).length === 1);
      });
      if (!matches.length) return fallback;
      var merged = Object.assign({}, fallback, matches[0]);
      if (!matches[0]['camp date']) merged['camp date'] = fallback['camp date'];
      if (!matches[0]['doctor name']) merged['doctor name'] = fallback['doctor name'];
      return merged;
    });
  }

  function parseCsv(text) {
    var rows = [], row = [], field = '', quoted = false;
    for (var i = 0; i < text.length; i += 1) {
      var ch = text[i];
      if (ch === '"') {
        if (quoted && text[i + 1] === '"') { field += '"'; i += 1; }
        else quoted = !quoted;
      } else if (ch === ',' && !quoted) {
        row.push(field.trim()); field = '';
      } else if ((ch === '\n' || ch === '\r') && !quoted) {
        if (ch === '\r' && text[i + 1] === '\n') i += 1;
        row.push(field.trim()); field = '';
        if (row.some(function (value) { return value !== ''; })) rows.push(row);
        row = [];
      } else field += ch;
    }
    if (field !== '' || row.length) { row.push(field.trim()); rows.push(row); }
    if (!rows.length) return [];
    var headers = rows.shift().map(function (header) { return header.toLowerCase().replace(/\s+/g, ' ').trim(); });
    return rows.map(function (values) {
      var item = {};
      headers.forEach(function (header, index) { item[header] = (values[index] || '').trim(); });
      return item;
    }).filter(function (item) {
      if (!item['camp date']) item['camp date'] = item.date || item['opd date'] || item['campdate'] || '';
      return item.city && item['hospital name'];
    });
  }

  function escapeText(value) {
    return String(value || '').replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }
  function safeMapUrl(value) { return /^https:\/\/([\w-]+\.)?google\.(com|co\.in)\/maps\//i.test(value || '') ? value : ''; }
  function mapUrlFor(item, address) {
    var supplied = safeMapUrl(item['google map link']);
    if (supplied) return supplied;
    var query = [item['hospital name'], address, item.city].filter(Boolean).join(', ');
    return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(query);
  }
  function safeBookingUrl(value) { return /^https:\/\/bankersvascular\.com\//i.test(value || '') ? value : 'https://bankersvascular.com/contact-us'; }
  function parseDate(value) {
    var match = value.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})$/);
    if (!match) return null;
    var date = new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
    return isNaN(date.getTime()) ? null : date;
  }
  function monthKey(date) { return date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0'); }
  function monthLabel(key) {
    var parts = key.split('-');
    return new Date(Number(parts[0]), Number(parts[1]) - 1, 1).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
  }
  function formatDate(date) { return String(date.getDate()).padStart(2, '0') + ' ' + date.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }); }
  function daysLabel(date) { return date.toLocaleDateString('en-IN', { weekday: 'long' }); }
  function doctorImage(name) {
    var normalized = (name || '').toLowerCase();
    var match = Object.keys(doctorImages).filter(function (key) { return normalized.indexOf(key) === 0; })[0];
    return match ? doctorImages[match] : '';
  }

  function render(records) {
    var today = new Date(); today.setHours(0, 0, 0, 0);
    var parsed = records.map(function (item) { item._date = parseDate(item['camp date']); return item; }).filter(function (item) { return item._date; });
    if (!parsed.length) return;
    var upcoming = parsed.filter(function (item) { return item._date >= today; }).sort(function (a, b) { return a._date - b._date; });
    var anchor = upcoming[0] || parsed.sort(function (a, b) { return b._date - a._date; })[0];
    var selectedKey = monthKey(anchor._date);
    var current = parsed.filter(function (item) { return monthKey(item._date) === selectedKey; }).sort(function (a, b) { return a._date - b._date; });
    /* The shared sheet may be partially filled while the monthly plan is being
       prepared. Keep the complete September plan visible from the source table
       until the live sheet contains the full month, then let sheet data take
       over automatically. */
    if (selectedKey === '2026-09' && current.length < 2 && fallbackRecords.length) {
      var seen = {};
      current.concat(fallbackRecords).forEach(function (item) {
        var date = parseDate(item['camp date']);
        var key = [date && date.getTime(), item.city, item['hospital name']].join('|');
        if (!seen[key]) { seen[key] = true; current.push(item); }
      });
      current.sort(function (a, b) { return parseDate(a['camp date']) - parseDate(b['camp date']); });
    }
    var body = tableBody;
    if (!body || !current.length) return;
    body.innerHTML = current.map(function (item) {
      var doctor = item['doctor name'] || 'Bankers Vascular team';
      var image = doctorImage(doctor);
      var booking = safeBookingUrl(item['booking link']);
      var address = item.address || 'Address will be updated soon.';
      var map = mapUrlFor(item, address);
      var photo = image ? '<img src="' + image + '" alt="' + escapeText(doctor) + '">' : '<span class="services-opd-location-photo-fallback" aria-hidden="true">👨‍⚕️</span>';
      var mapAction = map ? '<a href="' + escapeText(map) + '" target="_blank" rel="noopener">📍 Location</a>' : '';
      return '<tr><td>' + escapeText(formatDate(item._date)) + '</td><td>' + escapeText(item.city) + '</td><td>' + escapeText(doctor) + '</td><td class="services-opd-hospital"><button type="button" class="services-opd-location" aria-expanded="false"><span class="services-opd-location-icon" aria-hidden="true">📍</span>' + escapeText(item['hospital name']) + '</button><span class="services-opd-location-popover" role="tooltip">' + photo + '<span class="services-opd-location-popover-body"><strong>' + escapeText(item['hospital name']) + '</strong><small>' + escapeText(item.city) + '</small><p>📍 ' + escapeText(address) + '</p><p>📅 ' + escapeText(formatDate(item._date)) + ' · ' + escapeText(daysLabel(item._date)) + '</p><p>🕒 ' + escapeText(item['camp time'] || 'Time to be announced') + '</p><p>👨‍⚕️ ' + escapeText(doctor) + '</p><span class="services-opd-location-actions">' + mapAction + '<a href="' + booking + '" target="_blank" rel="noopener">Book appointment</a></span></span></span></td></tr>';
    }).join('');
    if (heading) heading.textContent = monthLabel(selectedKey) + ' OPD Plan';
    if (updateBadge) updateBadge.textContent = 'Live sheet • auto-updated';
    bindLocationTriggers();
    document.dispatchEvent(new CustomEvent('services-opd-updated'));
  }

  function bindLocationTriggers() {
    document.querySelectorAll('.services-opd-location').forEach(function (trigger) {
      if (trigger.dataset.bound) return;
      trigger.dataset.bound = 'true';
      trigger.addEventListener('click', function () {
        var open = trigger.getAttribute('aria-expanded') === 'true';
        document.querySelectorAll('.services-opd-location[aria-expanded="true"]').forEach(function (other) { other.setAttribute('aria-expanded', 'false'); });
        trigger.setAttribute('aria-expanded', open ? 'false' : 'true');
      });
    });
  }

  function load() {
    fetch(endpoint + '&ts=' + Date.now(), { cache: 'no-store' })
      .then(function (response) { if (!response.ok) throw new Error('Sheet request failed'); return response.text(); })
      .then(function (text) {
        var sheetRecords = parseCsv(text);
        var hasDatedRows = sheetRecords.some(function (item) { return parseDate(item['camp date']); });
        render(hasDatedRows ? sheetRecords : enrichFallbackRecords(sheetRecords));
      })
      .catch(function () {
        /* Keep the complete source plan interactive if a browser blocks the
           shared-sheet request; the next five-minute refresh will retry it. */
        if (fallbackRecords.length) render(fallbackRecords);
        if (updateBadge) updateBadge.textContent = 'Monthly updates';
      });
  }

  bindLocationTriggers();
  load();
  window.setInterval(load, 300000);
}());
