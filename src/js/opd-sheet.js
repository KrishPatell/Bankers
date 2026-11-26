(function () {
  'use strict';

  var section = document.querySelector('[data-opd-spreadsheet-id], [data-opd-sheet-url]');
  var currentTable = section && section.querySelector('.services-opd-table:not(.services-opd-coming-table)');
  var upcomingTable = section && section.querySelector('.services-opd-coming-table');
  if (!section || !currentTable) return;

  var currentBody = currentTable.querySelector('tbody');
  var upcomingBody = upcomingTable && upcomingTable.querySelector('tbody');
  var comingSoon = section.querySelector('.services-opd-coming-soon');
  var heading = section.querySelector('#services-opd-heading');
  var comingHeading = section.querySelector('#services-opd-coming-heading');
  var updateBadge = section.querySelector('.services-opd-update');
  var spreadsheetId = section.getAttribute('data-opd-spreadsheet-id') || '';
  var sheetPrefix = section.getAttribute('data-opd-sheet-prefix') || '';
  var endpointTemplate = section.getAttribute('data-opd-sheet-url') || '';
  var doctorImages = {
    'dr. tensi': '/images/doctor-card-tensi-trivedi.png',
    'dr. dimple': '/images/doctor-card-dimple-parmar.png',
    'dr. pratiksha': '/images/doctor-card-pratiksha-patoliya.png',
    'dr. payal': '/images/doctor-card-payal-vadlani.png',
    'dr. disha': '/images/doctor-card-disha-soni.png',
    'dr. mohal': '/images/doctor-card-mohal-banker.png'
  };

  function escapeText(value) {
    return String(value || '').replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  function parseCsv(text) {
    var rows = [], row = [], field = '', quoted = false;
    text = String(text || '').replace(/^\uFEFF/, '');
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
      headers.forEach(function (header, index) { if (header) item[header] = (values[index] || '').trim(); });
      if (!item['camp date']) item['camp date'] = item.date || item['opd date'] || item.campdate || '';
      return item;
    }).filter(function (item) { return item.city && item['hospital name']; });
  }

  function parseDate(value) {
    var text = String(value || '').trim();
    var match;
    if (!text) return null;
    match = text.match(/^(\d{1,2})[\/-](\d{1,2})[\/-](\d{4})(?:\s|$)/);
    if (match) return validDate(Number(match[3]), Number(match[2]) - 1, Number(match[1]));
    match = text.match(/^(\d{4})[\/-](\d{1,2})[\/-](\d{1,2})(?:\s|$)/);
    if (match) return validDate(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    match = text.match(/^(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})$/);
    if (match) {
      var months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
      var month = months.indexOf(match[2].slice(0, 3).toLowerCase());
      return month < 0 ? null : validDate(Number(match[3]), month, Number(match[1]));
    }
    match = text.match(/^Date\((\d+),(\d+),(\d+)\)$/i);
    if (match) return validDate(Number(match[1]), Number(match[2]), Number(match[3]));
    return null;
  }

  function validDate(year, month, day) {
    var date = new Date(year, month, day);
    return date.getFullYear() === year && date.getMonth() === month && date.getDate() === day ? date : null;
  }

  function recordsFromTable(table) {
    if (!table) return [];
    return Array.prototype.map.call(table.querySelectorAll('tbody tr'), function (row) {
      var cells = row.querySelectorAll('td');
      if (!cells[0] || !cells[1] || !cells[2] || !cells[3]) return null;
      return {
        'camp date': cells[0].textContent.trim(),
        city: cells[1].textContent.trim(),
        'doctor name': cells[2].textContent.trim(),
        'hospital name': cells[3].textContent.trim(),
        address: cells[4] ? cells[4].textContent.trim() : ''
      };
    }).filter(Boolean);
  }

  var fallbackRecords = recordsFromTable(currentTable);
  var fallbackUpcomingRecords = recordsFromTable(upcomingTable);

  function safeMapUrl(value) {
    return /^https:\/\/(?:[\w-]+\.)?google\.(?:com|co\.in)\/maps\//i.test(value || '') ? value : '';
  }

  function mapUrlFor(item, address) {
    var supplied = safeMapUrl(item['google map link']);
    if (supplied) return supplied;
    var query = [item['hospital name'], address, item.city].filter(Boolean).join(', ');
    return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(query);
  }

  function safeBookingUrl(value) {
    return /^https:\/\/bankersvascular\.com\//i.test(value || '') ? value : 'https://bankersvascular.com/contact-us';
  }

  function monthKey(date) {
    return date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0');
  }

  function monthLabel(key) {
    var parts = key.split('-');
    return new Date(Number(parts[0]), Number(parts[1]) - 1, 1).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });
  }

  function addMonths(date, count) {
    return new Date(date.getFullYear(), date.getMonth() + count, 1);
  }

  function sheetNameFor(date) {
    var month = date.toLocaleDateString('en-US', { month: 'short' });
    return sheetPrefix + month + ' ' + String(date.getFullYear()).slice(-2);
  }

  function endpointFor(date) {
    var sheetName = sheetNameFor(date);
    if (endpointTemplate) return endpointTemplate.replace(/\{sheet\}/g, encodeURIComponent(sheetName));
    if (!spreadsheetId) return '';
    return 'https://docs.google.com/spreadsheets/d/' + encodeURIComponent(spreadsheetId) + '/gviz/tq?tqx=out:csv&sheet=' + encodeURIComponent(sheetName);
  }

  function datedRecords(records) {
    return records.map(function (item) {
      var copy = Object.assign({}, item);
      copy._date = parseDate(copy['camp date'] || copy.date || copy['opd date']);
      return copy;
    }).filter(function (item) { return item._date; });
  }

  function formatDate(date) {
    return String(date.getDate()).padStart(2, '0') + ' ' + date.toLocaleDateString('en-IN', { month: 'short', year: 'numeric' });
  }

  function daysLabel(date) { return date.toLocaleDateString('en-IN', { weekday: 'long' }); }

  function doctorImage(name) {
    var normalized = String(name || '').toLowerCase();
    var match = Object.keys(doctorImages).filter(function (key) { return normalized.indexOf(key) === 0; })[0];
    return match ? doctorImages[match] : '';
  }

  function renderRows(body, records) {
    if (!body) return;
    body.innerHTML = records.map(function (item) {
      var doctor = item['doctor name'] || 'Bankers Vascular team';
      var address = item.address || 'Address will be updated soon.';
      var map = mapUrlFor(item, address);
      var booking = safeBookingUrl(item['booking link']);
      var image = doctorImage(doctor);
      var photo = image ? '<img src="' + escapeText(image) + '" alt="' + escapeText(doctor) + '">' : '<span class="services-opd-location-photo-fallback" aria-hidden="true">👨‍⚕️</span>';
      var mapAction = map ? '<a href="' + escapeText(map) + '" target="_blank" rel="noopener">📍 Location</a>' : '';
      return '<tr><td>' + escapeText(formatDate(item._date)) + '</td><td>' + escapeText(item.city) + '</td><td>' + escapeText(doctor) + '</td><td class="services-opd-hospital"><button type="button" class="services-opd-location" aria-expanded="false"><span class="services-opd-location-icon" aria-hidden="true">📍</span>' + escapeText(item['hospital name']) + '</button><span class="services-opd-location-popover" role="tooltip">' + photo + '<span class="services-opd-location-popover-body"><strong>' + escapeText(item['hospital name']) + '</strong><small>' + escapeText(item.city) + '</small><p>📍 ' + escapeText(address) + '</p><p>📅 ' + escapeText(formatDate(item._date)) + ' · ' + escapeText(daysLabel(item._date)) + '</p><p>🕒 ' + escapeText(item['camp time'] || 'Time to be announced') + '</p><p>👨‍⚕️ ' + escapeText(doctor) + '</p><span class="services-opd-location-actions">' + mapAction + '<a href="' + booking + '" target="_blank" rel="noopener">Book appointment</a></span></span></span></td><td class="services-opd-address"><span>' + escapeText(address) + '</span><a href="' + escapeText(map) + '" target="_blank" rel="noopener">View map ↗</a></td></tr>';
    }).join('');
  }

  function bindLocationTriggers() {
    section.querySelectorAll('.services-opd-location').forEach(function (trigger) {
      if (trigger.dataset.bound) return;
      trigger.dataset.bound = 'true';
      trigger.addEventListener('click', function () {
        var open = trigger.getAttribute('aria-expanded') === 'true';
        section.querySelectorAll('.services-opd-location[aria-expanded="true"]').forEach(function (other) { other.setAttribute('aria-expanded', 'false'); });
        trigger.setAttribute('aria-expanded', open ? 'false' : 'true');
      });
    });
  }

  function renderPlans(currentRecords, nextRecords, isFallback) {
    var today = new Date();
    today.setHours(0, 0, 0, 0);
    var currentDated = datedRecords(currentRecords);
    var nextDated = datedRecords(nextRecords);
    var combined = currentDated.concat(nextDated);
    var selectedKey = monthKey(today);
    if (!combined.some(function (item) { return monthKey(item._date) === selectedKey; })) {
      var firstFuture = combined.filter(function (item) { return item._date >= today; }).sort(function (a, b) { return a._date - b._date; })[0];
      if (firstFuture) selectedKey = monthKey(firstFuture._date);
    }
    var nextKey = monthKey(addMonths(new Date(Number(selectedKey.slice(0, 4)), Number(selectedKey.slice(5)) - 1, 1), 1));
    var currentPlan = combined.filter(function (item) { return monthKey(item._date) === selectedKey; }).sort(function (a, b) { return a._date - b._date; });
    var nextPlan = combined.filter(function (item) { return monthKey(item._date) === nextKey; }).sort(function (a, b) { return a._date - b._date; });
    if (!currentPlan.length) currentPlan = datedRecords(fallbackRecords).sort(function (a, b) { return a._date - b._date; });
    if (!nextPlan.length) nextPlan = datedRecords(fallbackUpcomingRecords).filter(function (item) { return monthKey(item._date) === nextKey; }).sort(function (a, b) { return a._date - b._date; });
    renderRows(currentBody, currentPlan);
    renderRows(upcomingBody, nextPlan);
    if (heading) heading.textContent = monthLabel(selectedKey) + ' OPD Plan';
    if (comingHeading) comingHeading.textContent = monthLabel(nextKey) + ' Coming Soon';
    if (comingSoon) comingSoon.hidden = !nextPlan.length;
    if (updateBadge) updateBadge.textContent = isFallback ? 'Monthly updates' : 'Live sheet • auto-updated';
    bindLocationTriggers();
    document.dispatchEvent(new CustomEvent('services-opd-updated'));
  }

  function fetchCsv(url) {
    if (!url) return Promise.resolve('');
    var separator = url.indexOf('?') >= 0 ? '&' : '?';
    return fetch(url + separator + 'ts=' + Date.now(), { cache: 'no-store' }).then(function (response) {
      if (!response.ok) throw new Error('Sheet request failed');
      return response.text();
    });
  }

  function load() {
    var today = new Date();
    var nextMonth = addMonths(today, 1);
    var currentUrl = endpointFor(today);
    var nextUrl = endpointFor(nextMonth);
    if (!currentUrl) {
      renderPlans(fallbackRecords, fallbackUpcomingRecords, true);
      return;
    }
    Promise.all([fetchCsv(currentUrl), fetchCsv(nextUrl)]).then(function (texts) {
      var currentRecords = parseCsv(texts[0]);
      var nextRecords = parseCsv(texts[1]);
      renderPlans(currentRecords.length ? currentRecords : fallbackRecords, nextRecords.length ? nextRecords : fallbackUpcomingRecords, false);
    }).catch(function () {
      renderPlans(fallbackRecords, fallbackUpcomingRecords, true);
    });
  }

  bindLocationTriggers();
  load();
  window.setInterval(load, 300000);
}());
